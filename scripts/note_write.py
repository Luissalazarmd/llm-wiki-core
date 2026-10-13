#!/usr/bin/env python3
"""Optional plain-file save/recovery helper, NOT an approval or canonical engine."""
import argparse
import base64
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
import library

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
    return json.loads(read_bytes(path, 2097152), object_pairs_hook=unique)


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


def check_packet(settings, packet):
    if not isinstance(packet, dict) or packet.get('status') != 'prepared_not_approved':
        raise ValueError('Expected an unapplied proposal packet')
    declared = packet.get('packet_sha256')
    unsigned = {k: v for k, v in packet.items() if k != 'packet_sha256'}
    actual = digest(json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())
    if declared != actual:
        raise ValueError('Packet content changed')
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
    return path, previous, draft


def replace_checked(path, expected, replacement):
    """Atomic single-file replacement for a cooperative single-writer local session."""
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, temporary = tempfile.mkstemp(prefix='.core-note-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(replacement)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        if read_bytes(path) != expected:
            raise ValueError('Note changed before save; preserve and review again')
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def create_checked(path, draft):
    """Publish complete bytes with a no-clobber hard link in the same directory."""
    fd, temporary = tempfile.mkstemp(prefix='.core-note-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(draft)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Atomic absence requirement; never replace a competing entry.
    finally:
        Path(temporary).unlink()


def save(settings, packet):
    path, previous, draft = check_packet(settings, packet)
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
    check_packet(settings, packet)
    if previous is None:
        create_checked(path, draft)
    else:
        replace_checked(path, previous, draft)
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
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
