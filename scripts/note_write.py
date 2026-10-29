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


def read_json(path):
    def unique(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError('Duplicate JSON key')
            data[key] = value
        return data
    try:
        return json.loads(read_bytes(path, 2097152), object_pairs_hook=unique)
    except json.JSONDecodeError as exc:
        raise ValueError(str(exc)) from exc


def target_path(settings, relative, create=False):
    root = Path(settings['library_root'])
    if settings.get('write_policy', 'read_only') != 'plain_files':
        raise ValueError('Plain writing is disabled; use the library permitted writer')
    # Compatibility refusal signals only: no vendor imports, installs or calls.
    if any(os.path.lexists(root / marker) for marker in ('.wanderloots-llm-wiki', '.private-engine-install.json')):
        raise ValueError('Managed library requires its library-permitted writer; Core does not install it')
    path = library.authorize(root, settings['authorized_paths'], relative, create=create)
    if path.suffix != '.md' or (not create and not path.is_file()):
        raise ValueError('Target must be an existing Markdown file')
    for source in settings.get('layers', {}).get('sources', []):
        boundary = root / source
        if path == boundary or path.is_relative_to(boundary):
            raise ValueError('Captured sources are immutable')
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
    if operation not in ('update', 'create'):
        raise ValueError('Unsupported proposal operation')
    create = operation == 'create'
    if create and (packet['target'].get('expected_absent') is not True
                   or packet['target'].get('base_sha256') is not None
                   or not packet['evidence'] or not packet['draft'].strip()):
        raise ValueError('Creation requires an absent-target binding and explicit evidence')
    path = target_path(settings, packet['target']['path'], create=create)
    previous = None if create else read_bytes(path)
    if not create and digest(previous) != packet['target']['base_sha256']:
        raise ValueError('Stale proposal base; preserve current note and review again')
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
    fd = os.open(record_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(record, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
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
    return {'status': 'plain_file_created' if previous is None else 'plain_file_saved',
            'record': str(record_path), 'sha256': digest(draft),
            'human_authentication_verified': False}


def restore(settings, record_path):
    directory = Path(settings['recovery_directory'])
    if record_path.parent.resolve() != directory or record_path.is_symlink():
        raise ValueError('Record must be directly inside the configured recovery directory')
    record = read_json(record_path)
    if record.get('format') != 'plain-note-recovery-v1' or record['library_root'] != settings['library_root']:
        raise ValueError('Recovery record belongs to a different library')
    if record.get('before_exists') is False:
        raise ValueError('Creation has no previous bytes; deletion requires separate review and is unsupported')
    path = target_path(settings, record['target'])
    current = read_bytes(path)
    if digest(current) != record['after_sha256']:
        raise ValueError('Note changed since save; restore would overwrite subsequent work')
    previous = base64.b64decode(record['before_base64'], validate=True)
    if len(previous) > LIMIT or digest(previous) != record['before_sha256']:
        raise ValueError('Invalid previous-content binding')
    if record.get('proposal', {}).get('living_synthesis') is not None and not numbering.in_scope(settings, record['target']):
        raise ValueError('Numbering profile or scope changed; restore refused')
    numbering.check_restore(settings, record['target'], current, previous)
    replace_checked(path, current, previous)
    if read_bytes(path) != previous:
        raise ValueError('Restored output not verified')
    return {'status': 'plain_file_restored', 'sha256': digest(previous),
            'human_authentication_verified': False}


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
    except BatchSaveError as exc:
        print(json.dumps(exc.result), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
