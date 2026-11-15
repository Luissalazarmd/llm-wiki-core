#!/usr/bin/env python3
"""Optional plain-file save/recovery helper, NOT an approval or canonical engine."""
import argparse
import base64
import difflib
import hashlib
import importlib
import json
import os
import stat
import sys
import tempfile
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
library = importlib.import_module('library')
numbering = importlib.import_module('numbering')

LIMIT = 262144


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bytes(path, limit=LIMIT):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Input must be a regular non-symlink file')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Input exceeds byte limit')
    return raw


def parse_json(raw):
    def unique(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError('Duplicate JSON key')
            data[key] = value
        return data
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except json.JSONDecodeError as exc:
        raise ValueError(str(exc)) from exc


def read_json(path):
    return parse_json(read_bytes(path, 2097152))


def write_record(path, record):
    """Create one private record: never overwrites, 0600, flushed to disk before returning."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(record, stream)  # ASCII escapes keep non-UTF-8 locale paths writable.
        stream.flush()
        os.fsync(stream.fileno())


def check_policy(settings):
    if settings.get('write_policy', 'read_only') != 'plain_files':
        if settings.get('write_policy', 'read_only') == 'canonical_engine':
            raise ValueError(
                'Plain writing is disabled; use the library permitted writer. '
                'canonical_engine requires the existing permitted canonical writer; '
                'if unavailable, continue authorized reading and proposals through host tools.')
        raise ValueError(
            'Plain writing is disabled; read_only means proposal-only. '
            'Continue authorized reading and proposals through host tools. '
            'Plain-file saving requires explicit library permission, exact human confirmation '
            'and recovery; this helper does not enable writing.')


def check_unmanaged(root):
    # Compatibility refusal signals only: no vendor imports, installs or calls.
    if any(os.path.lexists(root / marker) for marker in ('.wanderloots-llm-wiki', '.private-engine-install.json')):
        raise ValueError('Managed library requires its library-permitted writer; Core does not install it')


def target_path(settings, relative, create=False, restoring=False):
    root = Path(settings['library_root'])
    check_policy(settings)
    check_unmanaged(root)
    path = library.authorize(root, settings['authorized_paths'], relative, create=create)
    if path.suffix != '.md' or (not create and not path.is_file()):
        raise ValueError('Target must be an existing Markdown file')
    for source in settings.get('layers', {}).get('sources', []):
        boundary = root / source
        if path == boundary or path.is_relative_to(boundary):
            raise ValueError('Captured sources are immutable')
        # Lexical comparison misses case/normalization-insensitive filesystems; compare identities.
        for candidate in (path, *path.parents):
            if candidate == root or not candidate.is_relative_to(root):
                break
            try:
                same = os.path.samefile(candidate, boundary)
            except OSError:
                same = False
            if same:
                raise ValueError('Captured sources are immutable')
    # Restore is proven by the record's after_sha256 and must stay available.
    if not create and not restoring:
        try:
            role = library.knowledge.metadata_from(read_bytes(path).decode('utf-8')).get('role')
        except (ValueError, RecursionError):
            role = None
        if role == 'source':
            raise ValueError('Target declares role: source; captured sources are immutable')
    if path.name.casefold() in ('agents.md', 'skill.md', 'claude.md'):
        raise ValueError('This helper does not write known agent instruction files (AGENTS.md, SKILL.md, CLAUDE.md)')
    return path


def check_packet(settings, packet, *, numbered=True):
    if not isinstance(packet, dict) or packet.get('status') != 'prepared_not_approved':
        raise ValueError('Expected an unapplied proposal packet')
    declared = packet.get('packet_sha256')
    unsigned = {k: v for k, v in packet.items() if k != 'packet_sha256'}
    actual = digest(json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())
    if declared != actual:
        raise ValueError('Packet content changed')
    if packet.get('format') == numbering.BATCH:
        if not numbered:
            raise ValueError('Nested batches are unsupported')
        numbering.check_batch(settings, packet)
        for child in packet['proposals']:
            check_packet(settings, child, numbered=False)
        return None
    if packet.get('format') is not None:
        raise ValueError('Unsupported proposal format')
    draft = packet['draft'].encode('utf-8')
    if len(draft) > LIMIT or digest(draft) != packet['draft_sha256']:
        raise ValueError('Invalid draft binding')
    operation = packet['target'].get('operation', 'update')
    if operation not in ('update', 'create', 'park'):
        raise ValueError('Unsupported proposal operation')
    create = operation in ('create', 'park')
    owner_authored = 'authorship' in packet
    if owner_authored and (packet['authorship'] != library.knowledge.OWNER_AUTHORED or operation != 'create'
                           or packet['evidence']):
        raise ValueError('Only the evidence-free creation of a seed carries an owner-authorship declaration')
    if create and (packet['target'].get('expected_absent') is not True
                   or packet['target'].get('base_sha256') is not None
                   or (operation == 'create' and not packet['evidence'] and not owner_authored)
                   or not packet['draft'].strip()):
        raise ValueError('Creation requires an absent-target binding and explicit evidence')
    if packet.get('custody') != (library.knowledge.CUSTODY if operation == 'park' else None):
        raise ValueError('Only a custody packet parks, and it parks only')
    path = target_path(settings, packet['target']['path'], create=create)
    if operation == 'park':
        # Custody, not acceptance: literal pending text, only inside the declared proposals layer.
        library.check_custody(settings, path, packet)
    if owner_authored:
        # The agent's declaration, not proof: a seed only, outside originals and the proposals layer.
        library.check_owner_seed(settings, packet['target']['path'], packet['draft'])
    try:
        declared_role = library.knowledge.metadata_from(packet['draft']).get('role')
    except (ValueError, RecursionError):
        declared_role = None
    if declared_role == 'source':
        raise ValueError('Draft declares role: source; this writer saves notes only. '
                         'Capture sources with capture_write.py or the host create-only tool')
    previous = None if create else read_bytes(path)
    if not create and digest(previous) != packet['target']['base_sha256']:
        raise ValueError('Stale proposal base; preserve current note and review again')
    if not create and library.in_proposals(settings, path):
        library.check_closure(previous.decode('utf-8'), packet['draft'])
    if not create:
        library.knowledge.check_owner_seed_kept(previous.decode('utf-8'), packet['draft'], packet['evidence'])
    expected_diff = ''.join(difflib.unified_diff((previous or b'').decode('utf-8').splitlines(keepends=True),
                                               packet['draft'].splitlines(keepends=True),
                                               fromfile='/dev/null' if create else packet['target']['path'],
                                               tofile=packet['target']['path'] + ' (proposed)'))
    if packet.get('diff') != expected_diff:
        raise ValueError('Proposal diff does not match the current base and draft')
    for anchor in packet['evidence']:
        evidence = library.authorize(Path(settings['library_root']), settings['authorized_paths'], anchor['path'])
        if evidence.suffix != '.md' or digest(read_bytes(evidence)) != anchor['sha256']:
            raise ValueError('Stale evidence; review again')
    if numbered:
        numbering.check(settings, packet)
    return path, previous, draft


def replace_checked(path, expected, replacement, before_publish=None):
    """Atomic single-file replacement for a cooperative single-writer local session."""
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, temporary = tempfile.mkstemp(prefix='.core-note-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(replacement)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        if before_publish is not None:
            before_publish()
        if read_bytes(path) != expected:
            raise ValueError('Note changed before save; preserve and review again')
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def create_checked(path, draft, before_publish=None):
    """Publish complete bytes with a no-clobber hard link in the same directory."""
    fd, temporary = tempfile.mkstemp(prefix='.core-note-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(draft)
            stream.flush()
            os.fsync(stream.fileno())
        mask = os.umask(0)  # mkstemp leaves 0600; give a note the process default mode.
        os.umask(mask)
        os.chmod(temporary, 0o666 & ~mask)
        if before_publish is not None:
            before_publish()
        os.link(temporary, path)  # Atomic absence requirement; never replace a competing entry.
    finally:
        Path(temporary).unlink()


class BatchSaveError(ValueError):
    """A sequential batch may leave verified saves and private recovery records."""
    def __init__(self, result):
        super().__init__(result['error'])
        self.result = result


def save_batch(settings, packet):
    check_packet(settings, packet)  # Every target, byte, diff and postimage before any write.
    expected = packet['living_synthesis']
    completed = []
    recovery = Path(settings['recovery_directory'])
    prior_records = set(recovery.iterdir())
    try:
        for child in packet['proposals']:
            current, _ = numbering.snapshot(settings)
            if current != expected:
                raise ValueError('Numbering scope changed during sequential save; preserve partial work')
            result = save(settings, child, numbered=False, expected_scope=expected)
            completed.append({'target': child['target']['path'], **result})
            expected = numbering.after_save(expected, child)
        current, _ = numbering.snapshot(settings)
        if current != expected:
            raise ValueError('Numbering scope changed before final readback; preserve partial work')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise BatchSaveError({'status': 'plain_batch_partial', 'error': str(exc),
            'completed': completed, 'recovery_records': sorted(str(p) for p in set(recovery.iterdir()) - prior_records),
            'human_authentication_verified': False}) from exc
    return {'status': 'plain_batch_saved', 'completed': completed, 'human_authentication_verified': False}


def save(settings, packet, *, numbered=True, expected_scope=None):
    if packet.get('format') == numbering.BATCH:
        return save_batch(settings, packet)
    checked = check_packet(settings, packet, numbered=numbered)
    if checked is None:
        raise ValueError('Expected a single-file proposal')
    path, previous, draft = checked
    record = {'format': 'plain-note-recovery-v1', 'library_root': settings['library_root'],
              'target': packet['target']['path'], 'before_exists': previous is not None,
              'before_sha256': digest(previous) if previous is not None else None,
              'after_sha256': digest(draft),
              'before_base64': base64.b64encode(previous).decode() if previous is not None else None,
              'proposal': packet, 'human_authentication_verified': False}
    record_path = Path(settings['recovery_directory']) / (uuid.uuid4().hex + '.json')
    # Persist previous bytes and provenance BEFORE replacing the note. Not an apply receipt.
    write_record(record_path, record)
    def before_publish():
        check_packet(settings, packet, numbered=numbered)
        if expected_scope is not None:
            current, _ = numbering.snapshot(settings)
            if current != expected_scope:
                raise ValueError('Numbering scope changed before publication; preserve partial work')

    before_publish()  # Recovery persistence itself may have exposed changed inputs.
    if previous is None:
        create_checked(path, draft, before_publish)
    else:
        replace_checked(path, previous, draft, before_publish)
    if read_bytes(path) != draft:
        raise ValueError('Saved output not verified; preserve recovery record')
    if packet['target'].get('operation') == 'park':
        return {'status': 'proposal_parked', 'custody_only': True, 'accepted': False,
                'record': str(record_path), 'sha256': digest(draft),
                'human_authentication_verified': False}
    return {'status': 'plain_file_created' if previous is None else 'plain_file_saved',
            'record': str(record_path), 'sha256': digest(draft),
            **({'authorship': packet['authorship']} if 'authorship' in packet else {}),
            'human_authentication_verified': False}


class RestoreError(ValueError):
    """A restore that began writing: reports what the note and the recovery directory now hold."""
    def __init__(self, result):
        super().__init__(result['error'])
        self.result = result


def restore(settings, record_path):
    try:
        check_policy(settings)
    except ValueError as exc:
        raise ValueError(f'{exc} Recovery requires write_policy plain_files with an existing private '
                         'recovery_directory.') from None
    directory = Path(settings['recovery_directory'])
    if record_path.parent.resolve() != directory or record_path.is_symlink():
        raise ValueError('Record must be directly inside the configured recovery directory')
    record_raw = read_bytes(record_path, 2097152)
    record = parse_json(record_raw)
    if record.get('format') != 'plain-note-recovery-v1' or record['library_root'] != settings['library_root']:
        raise ValueError('Recovery record belongs to a different library')
    if record.get('before_exists') is False:
        raise ValueError('Creation has no previous bytes; deletion requires separate review and is unsupported')
    path = target_path(settings, record['target'], restoring=True)
    current = read_bytes(path)
    if digest(current) != record['after_sha256']:
        raise ValueError('Note changed since save; restore would overwrite subsequent work')
    previous = base64.b64decode(record['before_base64'], validate=True)
    if len(previous) > LIMIT or digest(previous) != record['before_sha256']:
        raise ValueError('Invalid previous-content binding')
    # A save record carries its numbered binding in the proposal; a restore record carries the flag forward.
    numbered = record.get('numbered', (record.get('proposal') or {}).get('living_synthesis') is not None)
    if numbered is not True and numbered is not False:
        raise ValueError('Invalid numbering binding in recovery record')

    def check_numbering():
        if numbered and not numbering.in_scope(settings, record['target']):
            raise ValueError('Numbering profile or scope changed; restore refused')
        numbering.check_restore(settings, record['target'], current, previous)

    check_numbering()
    # The same record shape, in the opposite direction: the bytes this restore displaces become
    # the previous bytes, so `restore --record` on the new record reverses it under the same checks.
    reversal = {'format': 'plain-note-recovery-v1', 'library_root': settings['library_root'],
                'target': record['target'], 'before_exists': True,
                'before_sha256': digest(current), 'after_sha256': digest(previous),
                'before_base64': base64.b64encode(current).decode(),
                'operation': 'restore', 'numbered': numbered,
                'restored_from': {'record': record_path.name, 'record_sha256': digest(record_raw)},
                'human_authentication_verified': False}
    reversal_path = directory / (uuid.uuid4().hex + '.json')
    untouched = {'status': 'restore_not_done', 'note_unchanged': True, 'record': None,
                 'restored_from': str(record_path), 'human_authentication_verified': False}
    # Persist the displaced bytes BEFORE replacing the note: without the record, nothing is replaced.
    try:
        write_record(reversal_path, reversal)
    except OSError as exc:
        # An entry this command did not create is never removed.
        left = None if isinstance(exc, FileExistsError) else discard(reversal_path)
        raise RestoreError({**untouched, 'unused_record': left, 'error':
            f'The record of this restore could not be written, so the note was not replaced: {exc}'}) from exc
    try:
        replace_checked(path, current, previous, check_numbering)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        # replace_checked raises only before its atomic replace: this command did not change the note.
        left = discard(reversal_path)
        raise RestoreError({**untouched, 'unused_record': left, 'error':
            f'The note was not replaced and keeps the bytes it had: {exc}. The original record remains usable'
            + ('; the record of this restore describes nothing that happened and could not be removed.'
               if left else '; the record of this restore was removed.')}) from exc
    try:
        verified = read_bytes(path) == previous
        problem = 'the note does not hold the restored bytes'
    except (OSError, ValueError) as exc:
        verified, problem = False, str(exc)
    if not verified:
        raise RestoreError({'status': 'restore_unverified', 'note_unchanged': False, 'record': str(reversal_path),
            'restored_from': str(record_path), 'human_authentication_verified': False, 'error':
            f'The note was replaced but readback failed: {problem}. Inspect the note; the record of this '
            'restore holds the bytes it displaced.'})
    return {'status': 'plain_file_restored', 'sha256': digest(previous), 'previous_sha256': digest(current),
            'record': str(reversal_path), 'restored_from': str(record_path),
            'human_authentication_verified': False}


def discard(record_path):
    """Remove a record that describes nothing; return its path if it remains."""
    try:
        record_path.unlink(missing_ok=True)
    except OSError:
        pass
    return str(record_path) if os.path.lexists(record_path) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('check', 'save'):
        command = sub.add_parser(action)
        command.add_argument('--packet', type=Path, required=True)
    command = sub.add_parser('restore')
    command.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    try:
        settings = library.load_config(args.config)
        if args.action == 'restore':
            result = restore(settings, args.record)
        else:
            packet = read_json(args.packet)
            if args.action == 'check':
                check_packet(settings, packet)
                result = {'status': 'base_and_evidence_current', 'human_authentication_verified': False}
            else:
                result = save(settings, packet)
        print(json.dumps(result))
        return 0
    except (BatchSaveError, RestoreError) as exc:
        print(json.dumps(exc.result), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
