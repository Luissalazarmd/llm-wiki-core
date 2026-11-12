#!/usr/bin/env python3
"""Optional create-only capture writer and owner-exception retirement; NOT an approval engine."""
import argparse
import datetime
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import sys
import tempfile
import urllib.parse
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
import capture_check
import library
import note_write

FORMAT = 'capture-v1'
MAX_ATTACHMENTS = 8
MAX_ATTACHMENT_BYTES = 134217728
# Admitted binary types: extension plus leading signature. A sanity bound, never content validation.
TYPES = {
    '.pdf': lambda head: b'%PDF-' in head,
    '.png': lambda head: head.startswith(b'\x89PNG\r\n\x1a\n'),
    '.jpg': lambda head: head.startswith(b'\xff\xd8\xff'),
    '.jpeg': lambda head: head.startswith(b'\xff\xd8\xff'),
    '.gif': lambda head: head[:6] in (b'GIF87a', b'GIF89a'),
    '.webp': lambda head: head[:4] == b'RIFF' and head[8:12] == b'WEBP',
    '.epub': lambda head: head.startswith(b'PK\x03\x04'),
    '.mp3': lambda head: head.startswith(b'ID3') or (len(head) > 1 and head[0] == 0xff and head[1] & 0xe0 == 0xe0),
    '.m4a': lambda head: head[4:8] == b'ftyp',
    '.ogg': lambda head: head.startswith(b'OggS'),
    '.opus': lambda head: head.startswith(b'OggS'),
    '.wav': lambda head: head[:4] == b'RIFF' and head[8:12] == b'WAVE',
    '.flac': lambda head: head.startswith(b'fLaC'),
}
RULE = 'Capture is create-only: never edit, move, rename or delete a captured original'
EXCEPTION = ('Owner exception to create-only custody: this captured original leaves the library only because '
             'its owner explicitly asked for it in the current conversation, after being told which rule is '
             'excepted. It is never routine, and it is not evidence of that request.')
WIKI = re.compile(r'!?\[\[([^\[\]|#\n]+)(?:#[^\[\]|\n]*)?(?:\|[^\[\]\n]*)?\]\]')
MARKDOWN = re.compile(r'!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^()\s]+)(?:\s+"[^"\n]*")?\s*\)')
PLACEHOLDER = re.compile(r'\{\{\s*(?:title|date|time)(?::[^}\n]*)?\s*\}\}')


class CaptureError(ValueError):
    """A failed multi-file operation reports exactly what stayed behind."""
    def __init__(self, result):
        super().__init__(result['error'])
        self.result = result


def canonical(data):
    return note_write.digest(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def writable(settings):
    note_write.check_policy(settings)
    note_write.check_unmanaged(Path(settings['library_root']))


def in_sources(settings, path):
    root = Path(settings['library_root'])
    return any(path.is_relative_to(root / source) for source in settings['layers'].get('sources', []))


def measure(path, limit=None):
    """Hash a regular non-symlink file completely; return (sha256, bytes, leading bytes, identity)."""
    if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f'Not a regular non-symlink file: {path}')
    digester, size, head = hashlib.sha256(), 0, b''
    with path.open('rb') as stream:
        status = os.fstat(stream.fileno())
        for chunk in iter(lambda: stream.read(65536), b''):
            head = head or chunk[:1024]
            size += len(chunk)
            if limit is not None and size > limit:
                raise ValueError(f'Attachment exceeds byte limit ({limit} bytes): {path}')
            digester.update(chunk)
    return digester.hexdigest(), size, head, (status.st_ino, status.st_size, status.st_mtime_ns)


def stage(source, directory, sha256, mode=None):
    """Write an independent, verified copy as a hidden temporary beside its destination."""
    fd, temporary = tempfile.mkstemp(prefix='.core-capture-', dir=directory)
    try:
        digester = hashlib.sha256()
        with os.fdopen(fd, 'wb') as output:
            if isinstance(source, bytes):
                digester.update(source)
                output.write(source)
            else:
                if source.is_symlink() or not stat.S_ISREG(source.lstat().st_mode):
                    raise ValueError(f'Not a regular non-symlink file: {source}')
                with source.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(65536), b''):
                        digester.update(chunk)
                        output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if digester.hexdigest() != sha256:
            raise ValueError(f'Bytes changed while copying; nothing was published: {source}')
        if mode is None:
            mask = os.umask(0)  # mkstemp leaves 0600; give a library file the process default mode.
            os.umask(mask)
            mode = 0o666 & ~mask
        os.chmod(temporary, mode)
    except BaseException:
        Path(temporary).unlink()
        raise
    return Path(temporary)


def candidates(destination, folder):
    """Library paths a relative link may name: a vault path first, then one relative to the linking note."""
    if not destination or destination.startswith('/') or '\\' in destination:
        return None
    found = [posixpath.normpath(path) for path in (destination, posixpath.join(folder, destination))]
    return list(dict.fromkeys(path for path in found if path.split('/')[0] not in ('..', '.'))) or None


def local_links(lines, folder):
    """Yield (written link, destination, candidate paths) for wikilinks, embeds and local Markdown links."""
    for line in lines:
        for match in WIKI.finditer(line):
            destination = match[1].strip()
            yield match[0], destination, candidates(destination, folder)
        for match in MARKDOWN.finditer(line):
            destination = match[1].strip('<>')
            scheme = re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', destination)
            if scheme and scheme[0].lower() != 'file:':
                continue  # An external reference, not a library file.
            destination = urllib.parse.unquote(destination.split('#', 1)[0].split('?', 1)[0])
            yield match[0], destination, None if scheme else candidates(destination, folder)


def admitted(destination):
    return posixpath.splitext(destination)[1].casefold() in TYPES


def attachment_target(settings, relative):
    """Validate an absent attachment leaf strictly inside a declared source directory."""
    root = Path(settings['library_root'])
    path = Path(relative) if isinstance(relative, str) else Path()
    if (not isinstance(relative, str) or path.is_absolute() or len(path.parts) < 2
            or path.as_posix() != relative or any(part.startswith('.') for part in path.parts)
            or any(char in relative for char in '[]|#%\n\r\\')):
        raise ValueError(f'Attachment target must be a safe relative path inside a source folder: {relative}')
    parent = library.authorize(root, settings['authorized_paths'], path.parent.as_posix())
    target = parent / path.name
    if not parent.is_dir() or not any(parent.is_relative_to(root / source) and (root / source).is_dir()
                                      for source in settings['layers'].get('sources', [])):
        raise ValueError(f'Attachment target must be inside a declared source folder: {relative}')
    if os.path.lexists(target):
        raise ValueError(f'Attachment target already exists; preserve it and review again: {relative}')
    return target


def prepare(settings, target, draft, pairs, capture_id=None, expected=None):
    """Bind wrapper bytes, absent targets and each attachment original; never write."""
    writable(settings)
    root = Path(settings['library_root'])
    checked = capture_check.check(settings, target, draft, expected=expected)
    text = draft.decode('utf-8')
    front = re.match(r'\A---\r?\n.*?\n---', text, re.S)
    lines = capture_check.knowledge.visible_body(text)
    if PLACEHOLDER.search((front[0] if front else '') + '\n' + '\n'.join(lines)):
        raise ValueError('Template placeholder left unfilled ({{title}}, {{date}} or {{time}}); '
                         'fill the wrapper before checking it')
    if len(pairs) > MAX_ATTACHMENTS:
        raise ValueError(f'A capture holds at most {MAX_ATTACHMENTS} attachments')
    attachments, declared = [], set()
    for original, relative in pairs:
        attachment_target(settings, relative)
        extension = posixpath.splitext(relative)[1].casefold()
        if extension not in TYPES:
            raise ValueError(f'Attachment type is not admitted ({", ".join(sorted(TYPES))}): {relative}')
        if relative.casefold() in declared:
            raise ValueError(f'Duplicate attachment target: {relative}')
        declared.add(relative.casefold())
        source = Path(os.path.abspath(original))
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Attachment original must be a regular non-symlink file: {original}')
        source = source.resolve(strict=True)
        if source.is_relative_to(root):
            raise ValueError(f'Attachment original must be outside the library; captures admit external '
                             f'originals: {original}')
        if source.suffix.casefold() != extension:
            raise ValueError(f'Attachment target must keep the extension of its original: {relative}')
        sha256, size, head, _ = measure(source, MAX_ATTACHMENT_BYTES)
        if not size or not TYPES[extension](head):
            raise ValueError(f'Attachment bytes do not start like {extension}: {original}')
        attachments.append({'source': str(source), 'target': relative, 'sha256': sha256, 'bytes': size,
                            'type': extension})
    targets, linked = {item['target'] for item in attachments}, set()
    for written, destination, found in local_links(lines, posixpath.dirname(target)):
        if not admitted(destination):
            continue
        if found is None:
            raise ValueError(f'Attachment link {written} must be relative, inside the library')
        if not targets.intersection(found):
            raise ValueError(f'Attachment link {written} does not point to a declared attachment target')
        linked |= targets.intersection(found)
    if targets - linked:
        raise ValueError('Every attachment must be linked from the wrapper, by library path or relative to it: '
                         + ', '.join(sorted(targets - linked)))
    packet = {'format': FORMAT, 'status': 'prepared_not_approved', 'capture_id': capture_id or uuid.uuid4().hex,
              'target': target, 'draft': text, 'draft_sha256': checked['draft_sha256'],
              'check_sha256': checked['check_sha256'], 'identity': checked['identity'],
              'attachments': attachments, 'approval_available': False}
    return {**packet, 'packet_sha256': canonical(packet)}


def check_packet(settings, packet):
    """Rederive the whole binding from current inputs; any difference means review again."""
    if (not isinstance(packet, dict) or packet.get('format') != FORMAT
            or packet.get('status') != 'prepared_not_approved'):
        raise ValueError('Expected an unapplied capture packet from capture_write.py prepare')
    if packet.get('packet_sha256') != canonical({k: v for k, v in packet.items() if k != 'packet_sha256'}):
        raise ValueError('Packet content changed')
    if not re.fullmatch(r'[0-9a-f]{32}', str(packet['capture_id'])):
        raise ValueError('Invalid capture_id')
    current = prepare(settings, packet['target'], packet['draft'].encode('utf-8'),
                      [(item['source'], item['target']) for item in packet['attachments']],
                      capture_id=packet['capture_id'], expected=packet['check_sha256'])
    for before, now in zip(packet['attachments'], current['attachments']):
        if before != now:
            raise ValueError(f"Attachment original changed since prepare; do not save, review again: "
                             f"{before['source']}")
    if current != packet:
        raise ValueError('Capture inputs changed since prepare; do not save, review again')
    return current


def write_record(path, record):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(record, stream)  # ASCII escapes keep non-UTF-8 locale paths writable.
        stream.flush()
        os.fsync(stream.fileno())


def fail(clean, partial, exc, recovery, name, record_path, record_created, left, **details):
    """Leave the library as it was, or record and report precisely what differs."""
    result = {'status': partial if left else clean, 'error': str(exc), 'library_unchanged': not left, **details,
              'human_authentication_verified': False}
    if not left:
        if record_created:
            record_path.unlink()
        return CaptureError(result)
    result['record'] = str(record_path) if record_created else None
    partial = recovery / (name + '.partial.json')
    try:
        write_record(partial, result)
        result['partial_record'] = str(partial)
    except OSError as second:
        result['partial_record'] = None
        result['partial_record_error'] = str(second)
    return CaptureError(result)


def save(settings, packet):
    """Create the wrapper and its attachments no-clobber, as independent copies, or leave none of them."""
    check_packet(settings, packet)
    root, recovery = Path(settings['library_root']), Path(settings['recovery_directory'])
    draft = packet['draft'].encode('utf-8')
    name = 'capture-' + packet['capture_id']
    record_path = recovery / (name + '.json')
    # Attachments first: the wrapper names them, so it is published last.
    items = [(Path(item['source']), root / item['target'], item['sha256']) for item in packet['attachments']]
    items.append((draft, root / packet['target'], packet['draft_sha256']))
    staged, published, record_created = [], [], False
    try:
        try:
            try:
                # Persist provenance BEFORE publishing. One record per packet: a packet is saved once.
                write_record(record_path, {
                    'format': 'capture-recovery-v1', 'library_root': settings['library_root'],
                    'recorded': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
                    'note': 'Written before publication; not an apply receipt or an approval.',
                    'packet': packet, 'human_authentication_verified': False})
            except FileExistsError:
                raise ValueError('This packet was already used for a save. A decision covers one capture: after a '
                                 'retired, deleted or partial capture, prepare again and show the wrapper again '
                                 f'({record_path})') from None
            record_created = True
            for source, final, sha256 in items:
                staged.append((stage(source, final.parent, sha256), final))
            check_packet(settings, packet)  # Recording and staging may have exposed changed inputs.
            for temporary, final in staged:
                os.link(temporary, final)  # Atomic absence requirement; never replace a competing entry.
                published.append((temporary, final))
            if note_write.read_bytes(root / packet['target']) != draft:
                raise ValueError('Saved wrapper bytes do not match the reviewed draft')
            for item in packet['attachments']:
                sha256, size, _, _ = measure(root / item['target'])
                if (sha256, size) != (item['sha256'], item['bytes']):
                    raise ValueError('Saved attachment does not match its bound hash: ' + item['target'])
                if os.path.exists(item['source']) and os.path.samefile(item['source'], root / item['target']):
                    raise ValueError('Saved attachment is a hard link to the original, not an independent copy: '
                                     + item['target'])
            capture_check.check(settings, packet['target'], draft, saved=True, expected=packet['check_sha256'])
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
            left = []
            for temporary, final in reversed(published):
                try:
                    # Remove only the entry this run published: the same inode as its own temporary.
                    if os.path.samefile(temporary, final):
                        final.unlink()
                    else:
                        left.append(final.relative_to(root).as_posix())
                except OSError:
                    if os.path.lexists(final):
                        left.append(final.relative_to(root).as_posix())
            raise fail('capture_not_saved', 'capture_partial', exc, recovery, name, record_path, record_created, left,
                       remaining=left) from exc
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
    return {'status': 'capture_saved', 'capture_id': packet['capture_id'], 'target': packet['target'],
            'sha256': packet['draft_sha256'], 'check_sha256': packet['check_sha256'],
            'attachments': [{k: item[k] for k in ('target', 'sha256', 'bytes')} for item in packet['attachments']],
            'record': str(record_path), 'semantic_validation': False, 'human_authentication_verified': False}


def linked_from(settings, retiring, wrapper):
    """Report notes that link to the retiring files. Read-only: those notes are never edited."""
    root = Path(settings['library_root'])
    names = {posixpath.basename(path) for path in retiring} | {posixpath.basename(wrapper)[:-3]}
    found, not_checked = [], []
    for path in library.inventory(root, settings['authorized_paths'], max_entries=2000):
        relative = path.relative_to(root).as_posix()
        if path.is_dir() or path.suffix != '.md' or relative == wrapper:
            continue
        try:
            text = note_write.read_bytes(path).decode('utf-8')
        except (ValueError, OSError) as exc:
            not_checked.append({'path': relative, 'reason': str(exc)})
            continue
        links, hit = [], set()
        for written, destination, paths in local_links(text.splitlines(), posixpath.dirname(relative)):
            paths = {candidate + suffix for candidate in paths or () for suffix in ('', '.md')}
            if '/' not in destination and destination in names:
                # A bare name may resolve by basename in the host; report it as possible, never certain.
                paths |= {path for path in retiring if posixpath.basename(path) in (destination, destination + '.md')}
            if paths & retiring:
                links.append(written)
                hit |= paths & retiring
        if links:
            found.append({'path': relative, 'links': sorted(set(links)), 'targets': sorted(hit),
                          'in_sources': in_sources(settings, path)})
    return found, not_checked


def retire_plan(settings, target, reason, extra):
    """Describe one retirement completely; never write."""
    writable(settings)
    root = Path(settings['library_root'])
    if (not isinstance(reason, str) or not reason.strip() or len(reason) > 512
            or any(ord(char) < 32 or ord(char) == 127 for char in reason)):
        raise ValueError('Retirement requires the owner\'s reason as one nonempty line of at most 512 characters')
    wrapper = library.authorize(root, settings['authorized_paths'], target)
    if (wrapper.relative_to(root).as_posix() != target or wrapper.suffix != '.md' or not wrapper.is_file()
            or not in_sources(settings, wrapper)):
        raise ValueError('Retirement target must be the exact Markdown wrapper of a capture inside a declared '
                         'source location; nothing else is retired by this helper')
    raw, metadata = capture_check.parse_note(wrapper, target)
    if metadata.get('role', 'source') != 'source':
        raise ValueError('Retirement target does not declare a captured source')
    paths = [target]

    def attachment(relative, origin):
        try:
            path = library.authorize(root, settings['authorized_paths'], relative)
        except ValueError:
            return False
        if path.relative_to(root).as_posix() != relative or not path.is_file() or not in_sources(settings, path):
            return False
        if path.suffix == '.md':
            raise ValueError(f'{origin} names a Markdown file; another wrapper is retired on its own: {relative}')
        if relative not in paths:
            paths.append(relative)
        return True

    lines = capture_check.knowledge.visible_body(raw.decode('utf-8'))
    for written, destination, found in local_links(lines, posixpath.dirname(target)):
        if admitted(destination) and not any(attachment(candidate, written) for candidate in found or ()):
            raise ValueError(f'Dangling attachment link {written}: the wrapper names a file that is not in the '
                             'source locations; reconcile it with the owner instead of retiring half a capture')
    for relative in extra:
        if not attachment(relative, '--attachment'):
            raise ValueError(f'--attachment must be an exact existing file inside a source location: {relative}')
    files = []
    for relative in paths:
        sha256, size, _, _ = measure(root / relative)
        files.append({'path': relative, 'sha256': sha256, 'bytes': size})
    siblings = sorted(p.relative_to(root).as_posix() for p in wrapper.parent.iterdir()
                      if p.stem == wrapper.stem and not p.name.startswith('.')
                      and p.relative_to(root).as_posix() not in paths)
    found, not_checked = linked_from(settings, set(paths), target)
    for note in found:
        if note['in_sources'] and set(note['targets']) - {target}:
            raise ValueError(f"Another capture links to an attachment being retired: {note['path']}; it would be "
                             'left dangling')
    plan = {'operation': 'retire_captured_original', 'library_root': settings['library_root'], 'target': target,
            'files': files, 'unlinked_siblings': siblings, 'linked_from': found,
            'link_scan': {'scope': settings['authorized_paths'], 'not_checked': not_checked},
            'reason': reason, 'rule_excepted': RULE, 'exception': EXCEPTION}
    return {**plan, 'plan_sha256': canonical(plan)}


def retire(settings, target, reason, extra, expected):
    """Copy a capture to private recovery, verify, then remove it from the library; or change nothing."""
    plan = retire_plan(settings, target, reason, extra)
    if expected != plan['plan_sha256']:
        raise ValueError('Capture, linking notes or reason changed, or this is not its plan_sha256; '
                         'nothing was retired, show the plan again')
    root, recovery = Path(settings['library_root']), Path(settings['recovery_directory'])
    name = 'retired-' + uuid.uuid4().hex
    holding, record_path = recovery / name, recovery / (name + '.json')
    os.mkdir(holding, 0o700)
    removed, record_created, left = [], False, []
    try:
        identities = {}
        for item in plan['files']:
            copy = holding / item['path']
            copy.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            sha256, _, _, identities[item['path']] = measure(root / item['path'])
            temporary = stage(root / item['path'], copy.parent, sha256, mode=0o600)
            os.replace(temporary, copy)
            if sha256 != item['sha256'] or measure(copy)[0] != item['sha256']:
                raise ValueError('Recovery copy does not match the planned bytes: ' + item['path'])
        write_record(record_path, {
            'format': 'capture-retirement-v1', **plan,
            'date': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            'recovery_copies': {item['path']: str(holding / item['path']) for item in plan['files']},
            'note': 'Written before removal; not proof of the owner\'s request.',
            'human_authentication_verified': False})
        record_created = True
        for item in plan['files']:  # The wrapper first: no source note is left naming removed files.
            path = root / item['path']
            status = path.lstat()
            if (status.st_ino, status.st_size, status.st_mtime_ns) != identities[item['path']]:
                raise ValueError('Captured file changed during retirement: ' + item['path'])
            path.unlink()
            removed.append(item)
        for item in plan['files']:
            if os.path.lexists(root / item['path']):
                raise ValueError('Retired file is still in the library: ' + item['path'])
            if measure(holding / item['path'])[0] != item['sha256']:
                raise ValueError('Recovery copy does not match the retired bytes: ' + item['path'])
    except (OSError, ValueError) as exc:
        for item in removed:
            path = root / item['path']
            try:
                temporary = stage(holding / item['path'], path.parent, item['sha256'])
                try:
                    os.link(temporary, path)
                finally:
                    temporary.unlink()
            except (OSError, ValueError):
                left.append(item['path'])
        error = fail('retirement_not_done', 'retirement_partial', exc, recovery, name, record_path, record_created, left,
                     removed_and_not_restored=left, recovery_copies=str(holding) if left else None)
        if not left:
            shutil.rmtree(holding)
        raise error from exc
    return {'status': 'capture_retired', 'target': target, 'files': plan['files'], 'record': str(record_path),
            'recovery_copies': str(holding), 'linked_from': plan['linked_from'],
            'unlinked_siblings': plan['unlinked_siblings'], 'rule_excepted': RULE, 'exception': EXCEPTION,
            'human_authentication_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    command = sub.add_parser('prepare', help='bind the wrapper on stdin and its attachments; writes nothing')
    command.add_argument('--target', required=True)
    command.add_argument('--attach', nargs=2, action='append', default=[], metavar=('ORIGINAL', 'TARGET'),
                         help='an original file outside the library and its target inside a source folder')
    for action in ('check', 'save'):
        command = sub.add_parser(action)
        command.add_argument('--packet', type=Path, required=True)
    command = sub.add_parser('retire', help='owner exception to create-only custody; without --expected-sha256 '
                                            'it only prints the plan')
    command.add_argument('--target', required=True)
    command.add_argument('--reason', required=True)
    command.add_argument('--attachment', action='append', default=[],
                         help='a captured file the wrapper does not link, named explicitly')
    command.add_argument('--expected-sha256')
    args = parser.parse_args()
    try:
        settings = library.load_config(args.config)
        if args.action == 'prepare':
            draft = sys.stdin.buffer.read(capture_check.LIMIT + 1)
            result = prepare(settings, args.target, draft, args.attach)
        elif args.action == 'retire':
            if args.expected_sha256 is None:
                result = {**retire_plan(settings, args.target, args.reason, args.attachment),
                          'status': 'retirement_planned_nothing_changed', 'human_authentication_verified': False}
            else:
                result = retire(settings, args.target, args.reason, args.attachment, args.expected_sha256)
        else:
            packet = note_write.read_json(args.packet)
            if args.action == 'check':
                check_packet(settings, packet)
                result = {'status': 'capture_inputs_current', 'human_authentication_verified': False}
            else:
                result = save(settings, packet)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except CaptureError as exc:
        print(json.dumps(exc.result), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
