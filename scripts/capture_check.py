#!/usr/bin/env python3
"""Read-only Raw admission check; no capture, approval or source mutation."""
import argparse
import hashlib
import json
import re
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
        raise ValueError('Capture dependencies must be exact regular Markdown files')
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Capture dependency exceeds byte limit')
    return raw, knowledge.metadata_from(raw.decode('utf-8').replace('\r\n', '\n'))


def hierarchy(settings, metadata):
    """Honor an explicitly configured stronger library policy; never require one."""
    policy = settings['capture_policy']
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
    return {'chain': chain, 'tags': tags, 'dependencies': dependencies, 'policy': policy}


def connection(settings, body, target):
    """Bind real outgoing note links or persist chat context in the capture itself."""
    dependencies, links = [], []
    text = '\n'.join(body)
    for match in re.finditer(r'(?<!!)\[\[[^\]\n]+\]\]', text):
        if len(links) >= 50:
            raise ValueError('Capture connection exceeds 50 links; narrow the draft or use a verified equivalent')
        link = match[0]
        destination = link[2:-2].split('|', 1)[0].split('#', 1)[0]
        relative = destination if destination.endswith('.md') else destination + '.md'
        if relative == target:
            raise ValueError('A capture cannot connect only to itself')
        raw, _ = read_note(settings, relative)
        note = {'id': relative, 'path': relative}
        knowledge.resolve_native_link(link, {relative: note},
                                      {relative: knowledge.visible_body(raw.decode('utf-8'))}, '')
        dependencies.append({'path': relative, 'sha256': digest(raw)})
        links.append(link)
    if links:
        return {'kind': 'existing_notes', 'links': links}, dependencies
    # Context is authored annotation, separated from the preserved original.
    for index, line in enumerate(body):
        if line not in ('## Capture context', '## Contexto de captura'):
            continue
        paragraph = []
        for following in body[index + 1:]:
            if following.startswith('#'):
                break
            paragraph.append(following)
        context = '\n'.join(paragraph).strip()
        if context and re.search(r'[^\W\d_]', context):
            return {'kind': 'persisted_question', 'context': context}, []
    raise ValueError('Capture requires an existing note link or a persistent capture-context question and contribution')


def source_inventory(settings, target, reference, version, identifier):
    root = Path(settings['library_root'])
    scopes = settings['layers'].get('sources', [])
    if not scopes:
        raise ValueError('Declare the authorized source locations before checking duplicates')
    entries = library.inventory(root, scopes, max_entries=2000)
    inventory, total = [], 0
    for path in entries:
        relative = path.relative_to(root).as_posix()
        if path.is_dir() or path.suffix != '.md' or relative == target:
            continue
        raw, metadata = read_note(settings, relative)
        total += len(raw)
        if total > 16777216:
            raise ValueError('Capture duplicate search exceeds total byte limit; use a verified library equivalent')
        previous_ref, previous_version = knowledge.source_reference(
            metadata, knowledge.visible_body(raw.decode('utf-8')))
        if identifier is not None and metadata.get('id') == identifier:
            raise ValueError('Duplicate source id at ' + relative + '; preserve existing identity')
        if previous_ref == reference:
            if previous_version == version or previous_version is None or version is None:
                raise ValueError('Duplicate reference/version or unknown version at ' + relative + '; reuse or reconcile')
        inventory.append({'path': relative, 'sha256': digest(raw)})
    return inventory


def check(settings, target, draft, saved=False, expected=None):
    root = Path(settings['library_root'])
    destination = (library.authorize(root, settings['authorized_paths'], target) if saved else
                   library.authorize(root, settings['authorized_paths'], target, create=True))
    if (destination.relative_to(root).as_posix() != target or destination.suffix != '.md'
            or not any(destination.is_relative_to(root / source)
                       for source in settings['layers'].get('sources', []))):
        raise ValueError('Capture target must be an exact path within a declared source location')
    if destination.name.casefold() in ('agents.md', 'skill.md', 'claude.md'):
        raise ValueError('Capture cannot create agent instructions')
    if len(draft) > LIMIT or not draft.strip():
        raise ValueError('Capture draft must be nonempty and bounded')
    text = draft.decode('utf-8')
    metadata = knowledge.metadata_from(text)
    if metadata.get('role', 'source') != 'source':
        raise ValueError('A capture preserves an original source, not a derived note')
    body = knowledge.visible_body(text)
    reference, version = knowledge.source_reference(metadata, body)
    identifier = metadata.get('id')
    if 'id' in metadata and (not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 2048):
        raise ValueError('Explicit id must be a bounded nonempty string')
    title = metadata.get('title', metadata.get('Title'))
    if title is None:
        title = next((line[2:].strip() for line in body if line.startswith('# ')), None)
    if not reference or not isinstance(title, str) or not title.strip() or len(title) > 512:
        raise ValueError('Capture identity requires a title and Reference')
    connected, dependencies = connection(settings, body, target)
    inventory = source_inventory(settings, target, reference, version, identifier)
    stronger = hierarchy(settings, metadata) if settings.get('capture_policy') is not None else {}
    binding = {'target': target, 'draft_sha256': digest(draft),
               'identity': {'title': title, 'reference': reference, 'version': version},
               'connection': connected, 'dependencies': dependencies, 'source_inventory': inventory,
               'scope': {'root': str(root), 'sources': settings['layers']['sources'],
                         'authorized_paths': settings['authorized_paths']}, 'stronger_policy': stronger}
    check_hash = digest(json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())
    if expected is not None and expected != check_hash:
        raise ValueError('Capture draft, connection, duplicate scope or policy changed; review again')
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
