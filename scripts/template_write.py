#!/usr/bin/env python3
"""Optional writer for source-wrapper templates: blank shapes, never sources; NOT an approval engine."""
import argparse
import datetime
import difflib
import json
import os
import posixpath
import re
import stat
import sys
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
import capture_check
import capture_write
import library
import note_write

FORMAT = 'template-v1'
DEFAULT_FOLDER = '_templates'
SETTING = '.obsidian/templates.json'
HEADINGS = ('## Contexto de captura', '## Capture context')
# Obsidian's core Templates plugin fills exactly these; anything else would reach a capture unfilled.
ALLOWED = re.compile(r'\{\{(?:title|date|time|(?:date|time):[^{}\n]{1,64})\}\}')
NAME = re.compile(r'[^\x00-\x1f\x7f/\\\[\]|#^:*?"<>%]{1,120}\.md')
BLANK_IDENTITY = ('Reference', 'Version', 'id')


def templates_folder(settings):
    """The library's own templates folder: Obsidian's setting when present, else _templates. Never written here."""
    root = Path(settings['library_root'])
    relative = DEFAULT_FOLDER
    setting = root / SETTING
    if setting.parent.is_symlink() or setting.is_symlink():
        raise ValueError(f'Symlink rejected: {SETTING}')
    if os.path.lexists(setting):
        data = note_write.read_json(setting)
        relative = data.get('folder', DEFAULT_FOLDER) if isinstance(data, dict) else None
        if not isinstance(relative, str):
            raise ValueError(f'{SETTING} must be an object whose "folder" is a string')
        relative = relative.rstrip('/')  # Obsidian may store a trailing slash; a bare "/" is the root.
    path = Path(relative)
    if (not relative or '\\' in relative or path.is_absolute() or '..' in path.parts
            or path.as_posix() != relative or any(part.startswith('.') for part in path.parts)
            or any(ord(char) < 32 or ord(char) == 127 for char in relative)):
        raise ValueError(f'Templates folder must be a visible folder inside the library, not its root: {relative!r}')
    current = root
    for part in path.parts:
        current /= part
        if current.is_symlink() or (os.path.lexists(current) and not current.is_dir()):
            raise ValueError(f'Templates folder must be a real directory, not a symlink or a file: {relative}')
    scoped = [*settings['authorized_paths'], *(p for paths in settings['layers'].values() for p in paths)]
    if any(library.overlaps(root, relative, other) for other in scoped):
        raise ValueError(f'Templates folder {relative} overlaps authorized_paths or a layer: templates are shapes, '
                         'never library content; the owner keeps them outside Raw, Review and Wiki')
    return relative, current


def target(settings, name):
    """A plain Markdown filename directly inside the templates folder; never a path."""
    relative, folder = templates_folder(settings)
    if (not isinstance(name, str) or not NAME.fullmatch(name) or name.startswith('.') or name != name.strip()
            or name.casefold() in ('agents.md', 'skill.md', 'claude.md')):
        raise ValueError('Template name must be a plain .md filename directly in the templates folder, without '
                         f'folders, traversal or link characters: {name!r}')
    path = folder / name
    if os.path.lexists(path):
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f'Template is not a regular non-symlink file: {relative}/{name}')
    elif folder.is_dir():
        for other in folder.iterdir():
            if other.name.casefold() == name.casefold():
                raise ValueError(f'A template differing only by case already exists: {relative}/{other.name}')
    return posixpath.join(relative, name), path


def filled(text, token):
    """What a capture would look like: the placeholders, identity and context a person or agent fills in."""
    text = ALLOWED.sub(lambda m: 'Plantilla de prueba' if m[0] == '{{title}}' else
                       '00:00' if m[0].startswith('{{time') else '2000-01-01', text)
    front = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
    head = front[1]
    for field, value in (('Reference', 'core-template-check:' + token), ('Title', 'Plantilla de prueba')):
        if capture_check.knowledge.metadata_from(text).get(field) in (None, ''):
            head, count = re.subn(rf'(?m)^{field}:.*$', f'{field}: "{value}"', head, count=1)
            if not count:
                raise ValueError(f'Write {field} as its own plain frontmatter line')
    lines = (text[:front.start(1)] + head + text[front.end(1):]).splitlines()
    body = capture_check.knowledge.visible_body('\n'.join(lines))
    if capture_check.capture_context(body) is None:
        lines.insert(next(i for i, line in enumerate(body) if line in HEADINGS) + 1, 'Comprobación de forma.')
    return '\n'.join(lines) + '\n'


def validate(settings, draft):
    """A blank source-wrapper shape that still fills into a valid capture; never a source itself. Read-only."""
    if len(draft) > capture_check.LIMIT or not draft.strip():
        raise ValueError(f'Template must be nonempty and at most {capture_check.LIMIT} bytes')
    text = draft.decode('utf-8').replace('\r\n', '\n')
    metadata = capture_check.knowledge.metadata_from(text)
    if metadata.get('role') != 'source' or 'Title' not in metadata or 'Reference' not in metadata:
        raise ValueError('Template frontmatter must declare role: source and the keys Title and Reference')
    if metadata['Title'] not in (None, '', '{{title}}'):
        raise ValueError('Template Title must be empty or {{title}}; a concrete title belongs to a source')
    for field in BLANK_IDENTITY:
        if metadata.get(field) not in (None, ''):
            raise ValueError(f'Template {field} must be empty: a concrete value is a source in disguise; '
                             'capture it with capture_write.py instead')
    body = capture_check.knowledge.visible_body(text)
    if not any(line in HEADINGS for line in body):
        raise ValueError('Template requires a "## Contexto de captura" (or "## Capture context") section')
    placeholders = sorted(set(ALLOWED.findall(text)))
    rest = ALLOWED.sub('', text)
    if '{{' in rest or '}}' in rest or '<%' in rest:
        raise ValueError('Template may use only the Obsidian core placeholders {{title}}, {{date}}, {{time}}, '
                         '{{date:FORMAT}} and {{time:FORMAT}}, written exactly; no plugin syntax')
    for written, destination, _ in capture_write.local_links(body, ''):
        if capture_write.admitted(destination) or destination.lower().startswith('file:'):
            raise ValueError(f'Template links an attachment or local file ({written}); that belongs to a capture')
    root = Path(settings['library_root'])
    sources = [source for source in settings['layers'].get('sources', []) if (root / source).is_dir()]
    if not sources:
        raise ValueError('Template check needs a declared source folder (layers.sources) to prove the filled wrapper')
    token = uuid.uuid4().hex
    try:
        # The existing wrapper check, on an absent probe target; a stronger capture_policy is per capture.
        capture_check.check({**settings, 'capture_policy': None},
                            posixpath.join(sources[0], f'core-template-check-{token}.md'),
                            filled(text, token).encode('utf-8'))
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError(f'Template does not fill into a valid capture wrapper: {exc}') from None
    return {'draft_sha256': note_write.digest(draft), 'placeholders': placeholders,
            'fills_into_capture_wrapper': True, 'capture_policy_checked': False}


def check(settings, name, draft):
    relative, path = target(settings, name)
    facts = validate(settings, draft)
    current = note_write.digest(note_write.read_bytes(path)) if os.path.lexists(path) else None
    return {'status': 'template_structure_checked_not_saved', 'target': relative, 'exists': current is not None,
            'current_sha256': current, **facts, 'semantic_validation': False, 'approval_available': False}


def prepare(settings, name, draft, expected=None, template_id=None):
    """Bind the exact template text and its absent target or current version; never write."""
    capture_write.writable(settings)
    relative, path = target(settings, name)
    facts = validate(settings, draft)
    previous = note_write.read_bytes(path) if os.path.lexists(path) else None
    if previous is None and expected is not None:
        raise ValueError(f'No template at {relative}: a new template takes no --expected-sha256')
    if previous is not None:
        if expected is None:
            raise ValueError(f'Template already exists: {relative}. Changing it requires --expected-sha256 of the '
                             'current file; an owner template is never overwritten or deleted without it')
        if note_write.digest(previous) != expected:
            raise ValueError(f'Template changed, or this is not the sha256 of the current file: {relative}; '
                             'read it again and show the change again')
        if previous == draft:
            raise ValueError('Template already has exactly this text; nothing to change')
    text = draft.decode('utf-8')
    diff = ''.join(difflib.unified_diff((previous or b'').decode('utf-8', 'replace').splitlines(keepends=True),
                                        text.splitlines(keepends=True),
                                        fromfile='/dev/null' if previous is None else relative,
                                        tofile=relative + ' (proposed)'))
    packet = {'format': FORMAT, 'status': 'prepared_not_approved', 'template_id': template_id or uuid.uuid4().hex,
              'operation': 'create' if previous is None else 'replace', 'target': relative, 'name': name,
              'draft': text, 'draft_sha256': facts['draft_sha256'], 'base_sha256': expected, 'diff': diff,
              'placeholders': facts['placeholders'], 'approval_available': False}
    return {**packet, 'packet_sha256': capture_write.canonical(packet)}


def check_packet(settings, packet):
    """Rederive the whole binding from the current library; any difference means review again."""
    if (not isinstance(packet, dict) or packet.get('format') != FORMAT
            or packet.get('status') != 'prepared_not_approved'):
        raise ValueError('Expected an unapplied template packet from template_write.py prepare')
    if packet.get('packet_sha256') != capture_write.canonical({k: v for k, v in packet.items()
                                                               if k != 'packet_sha256'}):
        raise ValueError('Packet content changed')
    if not re.fullmatch(r'[0-9a-f]{32}', str(packet['template_id'])):
        raise ValueError('Invalid template_id')
    if prepare(settings, packet['name'], packet['draft'].encode('utf-8'), packet['base_sha256'],
               packet['template_id']) != packet:
        raise ValueError('Template inputs changed since prepare; do not save, review again')


def save(settings, packet):
    """Create a new template no-clobber, or replace the bound version after keeping it in private recovery."""
    check_packet(settings, packet)
    root, recovery = Path(settings['library_root']), Path(settings['recovery_directory'])
    draft = packet['draft'].encode('utf-8')
    name = 'template-' + packet['template_id']
    record_path, path = recovery / (name + '.json'), root / packet['target']
    replacing = packet['operation'] == 'replace'
    copy = recovery / (name + '.previous.md') if replacing else None
    record_created = copied = published = False
    created, temporary = [], None
    try:
        try:
            try:
                # Persist provenance BEFORE publishing. One record per packet: a packet is saved once.
                capture_write.write_record(record_path, {
                    'format': 'template-recovery-v1', 'library_root': settings['library_root'],
                    'recorded': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
                    'note': 'Written before publication; not an apply receipt or an approval.',
                    'packet': packet, 'previous_copy': str(copy) if replacing else None,
                    'human_authentication_verified': False})
            except FileExistsError:
                raise ValueError('This packet was already used for a save. A decision covers one write: prepare '
                                 f'again and show the template again ({record_path})') from None
            record_created = True
            mode = None
            if replacing:
                # The previous version leaves the library only as a verified private copy, made first.
                staged = capture_write.stage(path, recovery, packet['base_sha256'], mode=0o600)
                try:
                    os.link(staged, copy)
                finally:
                    staged.unlink()
                copied = True
                mode = stat.S_IMODE(path.stat().st_mode)
            for directory in reversed([p for p in (path.parent, *path.parent.parents)
                                       if p != root and p.is_relative_to(root) and not os.path.lexists(p)]):
                os.mkdir(directory)  # The first approved save may create the folder Obsidian already names.
                created.append(directory)
            temporary = capture_write.stage(draft, path.parent, packet['draft_sha256'], mode)
            check_packet(settings, packet)  # Recording and staging may have exposed changed inputs.
            if replacing:
                os.replace(temporary, path)  # Atomic; the bound previous bytes were verified just above.
            else:
                os.link(temporary, path)  # Atomic absence requirement; never replace a competing entry.
            published = True
            if note_write.read_bytes(path) != draft:
                raise ValueError('Saved template bytes do not match the reviewed text')
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
            left = []
            if published:
                try:
                    # Remove only the entry this run created: the same inode as its own temporary.
                    if not replacing and os.path.samefile(temporary, path):
                        path.unlink()
                    else:
                        left.append(packet['target'])
                except OSError:
                    left.append(packet['target'])
            if not left:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
                if copied:
                    copy.unlink(missing_ok=True)
                for directory in reversed(created):
                    try:
                        directory.rmdir()
                    except OSError:
                        left.append(directory.relative_to(root).as_posix())
            raise capture_write.fail('template_not_saved', 'template_partial', exc, recovery, name, record_path,
                                     record_created, left, remaining=left,
                                     previous_copy=str(copy) if copied and left else None) from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'status': 'template_replaced' if replacing else 'template_created',
            'template_id': packet['template_id'], 'target': packet['target'], 'sha256': packet['draft_sha256'],
            'previous_sha256': packet['base_sha256'], 'previous_copy': str(copy) if replacing else None,
            'folder_created': bool(created), 'record': str(record_path), 'semantic_validation': False,
            'human_authentication_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    command = sub.add_parser('check', help='validate the template on stdin, or recheck a packet; writes nothing')
    choice = command.add_mutually_exclusive_group(required=True)
    choice.add_argument('--name', help='plain .md filename in the templates folder')
    choice.add_argument('--packet', type=Path)
    command = sub.add_parser('prepare', help='bind the exact template on stdin; writes nothing')
    command.add_argument('--name', required=True, help='plain .md filename in the templates folder')
    command.add_argument('--expected-sha256', help='sha256 of the current file; required to change a template')
    command = sub.add_parser('save')
    command.add_argument('--packet', type=Path, required=True)
    args = parser.parse_args()
    try:
        settings = library.load_config(args.config)
        if args.action == 'prepare':
            result = prepare(settings, args.name, sys.stdin.buffer.read(capture_check.LIMIT + 1),
                             args.expected_sha256)
        elif args.packet is None:
            result = check(settings, args.name, sys.stdin.buffer.read(capture_check.LIMIT + 1))
        elif args.action == 'check':
            check_packet(settings, note_write.read_json(args.packet))
            result = {'status': 'template_inputs_current', 'human_authentication_verified': False}
        else:
            result = save(settings, note_write.read_json(args.packet))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except capture_write.CaptureError as exc:
        print(json.dumps(exc.result), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
