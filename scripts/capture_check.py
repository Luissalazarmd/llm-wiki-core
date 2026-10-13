#!/usr/bin/env python3
"""Read-only Raw admission check; no capture, approval or source mutation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import library
import knowledge

LIMIT = 262144


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_note(settings, relative):
    path = library.authorize(Path(settings['library_root']), settings['authorized_paths'], relative)
    if (path.suffix != '.md' or not path.is_file()
            or path.relative_to(Path(settings['library_root'])).as_posix() != relative):
        raise ValueError('Hierarchy and taxonomy must be regular Markdown files')
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Hierarchy or taxonomy file exceeds byte limit')
    return raw, knowledge.metadata_from(raw.decode('utf-8').replace('\r\n', '\n'))


def check(settings, target, draft, saved=False, expected=None):
    policy = settings.get('capture_policy')
    if policy is None:
        raise ValueError('Capture requires an explicit hierarchy and taxonomy policy')
    root = Path(settings['library_root'])
    destination = (library.authorize(root, settings['authorized_paths'], target) if saved else
                   library.authorize(root, settings['authorized_paths'], target, create=True))
    if destination.suffix != '.md' or not any(
            destination.is_relative_to(root / source) for source in settings['layers'].get('sources', [])):
        raise ValueError('Capture target must be within a declared source location')
    if destination.name == 'AGENTS.md':
        raise ValueError('Capture cannot create agent instructions')
    if len(draft) > LIMIT or not draft.strip():
        raise ValueError('Capture draft must be nonempty and bounded')
    metadata = knowledge.metadata_from(draft.decode('utf-8').replace('\r\n', '\n'))
    fields = {'moc': 'moc', 'parent': 'parent', 'role': 'role', 'tags': 'tags', 'taxonomy_tags': 'tags',
              **policy.get('fields', {})}
    moc = metadata.get(fields['moc'])
    tags = metadata.get(fields['tags'])
    if not isinstance(moc, str) or not moc.strip():
        raise ValueError('Raw capture requires an explicit MOC path')
    if (not isinstance(tags, list) or not tags or len(tags) > 50 or
            any(not isinstance(tag, str) or not tag.strip() or len(tag) > 128 for tag in tags) or
            len(set(tags)) != len(tags)):
        raise ValueError('Raw capture requires distinct nonempty taxonomy tags')
    taxonomy_raw, taxonomy = read_note(settings, policy['taxonomy_path'])
    vocabulary = taxonomy.get(fields['taxonomy_tags'])
    if (not isinstance(vocabulary, list) or not vocabulary or len(vocabulary) > 1000 or
            any(not isinstance(tag, str) or not tag.strip() or len(tag) > 128 for tag in vocabulary) or
            len(set(vocabulary)) != len(vocabulary)):
        raise ValueError('Taxonomy must declare a bounded distinct tag vocabulary')
    if not set(tags).issubset(vocabulary):
        raise ValueError('Capture tags are not in the declared taxonomy')
    dependencies = [{'path': policy['taxonomy_path'], 'sha256': digest(taxonomy_raw)}]
    chain = []
    current = moc
    while True:
        if not isinstance(current, str) or current in chain:
            raise ValueError('Invalid or cyclic MOC hierarchy')
        if len(chain) >= 32:
            raise ValueError('MOC hierarchy exceeds 32 nodes')
        raw, node = read_note(settings, current)
        if node.get(fields['role']) != 'map':
            raise ValueError('Every hierarchy node must be an explicitly declared map')
        chain.append(current)
        dependencies.append({'path': current, 'sha256': digest(raw)})
        parent = node.get(fields['parent'])
        if current in policy['roots']:
            if parent is not None:
                raise ValueError('A configured root must not declare a parent')
            break
        if not isinstance(parent, str) or not parent.strip():
            raise ValueError('MOC hierarchy must reach an explicit configured root')
        current = parent
    binding = {'target': target, 'draft_sha256': digest(draft), 'chain': chain,
               'tags': tags, 'dependencies': dependencies, 'policy': policy}
    check_hash = digest(json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())
    if expected is not None and expected != check_hash:
        raise ValueError('Capture draft, hierarchy, taxonomy or policy changed; review again')
    if saved:
        if expected is None:
            raise ValueError('Saved capture verification requires the pre-write check hash')
        raw, _ = read_note(settings, target)
        if raw != draft:
            raise ValueError('Saved capture bytes do not match the reviewed draft')
    return {**binding, 'check_sha256': check_hash, 'approval_available': False,
            'capture_available': False, 'semantic_validation': False,
            'status': 'capture_structure_and_saved_bytes_verified' if saved else 'capture_structure_checked_not_saved'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--expected-sha256')
    parser.add_argument('--saved', action='store_true')
    args = parser.parse_args()
    try:
        settings = library.load_config(args.config)
        draft = sys.stdin.buffer.read(LIMIT + 1)
        result = check(settings, args.target, draft, args.saved, args.expected_sha256)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
