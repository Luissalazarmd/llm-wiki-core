#!/usr/bin/env python3
"""Original read-only Markdown catalog; never authorizes canonical mutations."""
from __future__ import annotations

import hashlib
import argparse
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
import yaml

ONTOLOGY = json.loads((Path(__file__).resolve().parents[1] / 'config/ontology.json').read_text())


def metadata_from(text: str) -> dict:
    """Parse bounded safe YAML, rejecting ambiguous or duplicate top-level fields."""
    if not text.startswith('---\n'):
        return {}
    match = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
    if not match:
        raise ValueError('Unclosed frontmatter')
    try:
        node = yaml.compose(match[1], Loader=yaml.SafeLoader)
        if node is None:
            return {}
        if not isinstance(node, yaml.MappingNode):
            raise ValueError('frontmatter must be a mapping')
        validate_yaml_node(node, set())
        return yaml.safe_load(match[1])
    except yaml.YAMLError as exc:
        raise ValueError('Invalid frontmatter') from exc


def validate_yaml_node(node, seen: set) -> None:
    """Reject YAML aliases, merge keys, complex keys and duplicate properties."""
    if id(node) in seen:
        raise ValueError('YAML aliases are not supported')
    seen.add(id(node))
    if isinstance(node, yaml.MappingNode):
        keys = []
        for key, value in node.value:
            if not isinstance(key, yaml.ScalarNode) or key.tag != 'tag:yaml.org,2002:str':
                raise ValueError('Property keys must be strings, without YAML merges')
            keys.append(key.value.casefold())
            validate_yaml_node(value, seen)
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate property in frontmatter')
    elif isinstance(node, yaml.SequenceNode):
        for value in node.value:
            validate_yaml_node(value, seen)


def note_paths(root: Path, max_notes: int = 2000):
    """Discover Markdown without following symbolic links or leaving a stage."""
    count = 0
    for stage in ('Raw', 'Wiki'):
        folder = root / stage
        if folder.is_symlink():
            raise ValueError('Symlink stage rejected')
        if not folder.exists():
            continue
        if not folder.is_dir():
            raise ValueError('Knowledge stage must be a directory')
        for current, directories, files in os.walk(folder, followlinks=False):
            for name in directories + files:
                if (Path(current) / name).is_symlink():
                    raise ValueError('Symlink inside knowledge stage rejected')
            for name in sorted(files):
                if name.endswith('.md'):
                    count += 1
                    if count > max_notes:
                        raise ValueError('Catalog exceeds note limit')
                    yield stage, Path(current) / name


def catalog(root: Path, max_file_bytes: int = 262144, max_notes: int = 2000) -> dict:
    """Project source identities and versions without editing captured files."""
    root = root.resolve(strict=True)
    notes = []
    edges = []
    seen = set()
    total_bytes = 0
    for stage, path in sorted(note_paths(root, max_notes)):
        if len(notes) >= max_notes:
            raise ValueError('Catalog exceeds note limit')
        relative = path.relative_to(root).as_posix()
        if any(char in relative for char in '[]|#\n\r\\'):
            raise ValueError('Unsafe Markdown link path')
        with path.open('rb') as stream:
            raw = stream.read(max_file_bytes + 1)
        if len(raw) > max_file_bytes:
            raise ValueError('Note exceeds byte limit')
        total_bytes += len(raw)
        if total_bytes > 16777216:
            raise ValueError('Catalog exceeds total byte limit')
        text = raw.decode('utf-8')
        metadata = metadata_from(text)
        reference = metadata.get('Reference')
        if reference is not None and (not isinstance(reference, str) or len(reference) > 2048):
            raise ValueError('Invalid Reference')
        identity = metadata.get('id') or reference
        if 'id' in metadata and (not isinstance(metadata['id'], str) or not metadata['id'].strip()):
            raise ValueError('Explicit id must be a nonempty string')
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError('Note requires stable identity: id or Reference')

        role = metadata.get('role', 'source' if stage == 'Raw' else 'concept')
        maturity = metadata.get('maturity', 'seed')
        declared = metadata.get('review', 'unreviewed')
        for key, value in [('roles', role), ('maturity', maturity), ('review', declared)]:
            if value not in ONTOLOGY[key]:
                raise ValueError('Invalid ' + key)
        if stage == 'Raw' and role != 'source':
            raise ValueError('Raw accepts source roles only')
        note_id = metadata.get('id') or 'source:' + hashlib.sha256(identity.encode()).hexdigest()
        if note_id in seen:
            raise ValueError('Duplicate identity; reconcile rather than overwrite')
        seen.add(note_id)
        if len(note_id) > 2048:
            raise ValueError('Identity exceeds limit')
        title = metadata.get('title', metadata.get('Title', path.stem))
        if not isinstance(title, str) or len(title) > 512 or '\n' in title:
            raise ValueError('Invalid title')
        relations = metadata.get('relations', [])
        if not isinstance(relations, list):
            raise ValueError('relations must be a list')
        for relation in relations:
            if not isinstance(relation, dict) or relation.get('kind') not in ONTOLOGY['relations']:
                raise ValueError('Invalid relation kind')
            if not all(isinstance(relation.get(k), str) and relation[k].strip() for k in ('target', 'reason')):
                raise ValueError('Relation requires target and reason')
            if len(relation['reason']) > 1024:
                raise ValueError('Relation reason exceeds limit')
            edges.append({'source': note_id, **{k: relation[k] for k in ('kind', 'target', 'reason')},
                          'declared_in': path.relative_to(root).as_posix(), 'review': 'unverified',
                          'evidence': relation.get('evidence', [])})
        notes.append({
                'id': note_id,
                'source_identity': reference if stage == 'Raw' else None,
                'path': path.relative_to(root).as_posix(),
                'title': title,
                'role': role, 'maturity': maturity,
                'declared_review': declared,
                'review': 'unreviewed' if declared == 'unreviewed' else 'unverified',
                'approval_available': False,
                'sha256': hashlib.sha256(raw).hexdigest(),
        })
    ids = {note['id']: note for note in notes}
    for edge in edges:
        if edge['target'] not in ids:
            raise ValueError('Unresolved relation target: ' + edge['target'])
        anchors = edge['evidence']
        if not isinstance(anchors, list) or (edge['kind'] in ('supported_by', 'contradicts', 'extends') and not anchors):
            raise ValueError('Evidence anchor required for factual relation')
        for anchor in anchors:
            if not isinstance(anchor, dict) or not all(isinstance(anchor.get(k), str) and anchor[k].strip()
                                                       for k in ('source', 'sha256', 'locator')):
                raise ValueError('Evidence anchor requires source, sha256 and locator')
            evidence = ids.get(anchor['source'])
            if evidence is None or evidence['role'] != 'source':
                raise ValueError('Evidence anchor must resolve to a source')
            if anchor['sha256'] != evidence['sha256']:
                raise ValueError('Stale evidence anchor')
    return {'notes': notes, 'edges': edges, 'mode': 'read_only', 'approval_available': False}


def focus(data: dict, identity: str, max_neighbors: int = 8, max_bytes: int = 16384) -> dict:
    """Return the requested identity and one bounded hop, with no source bodies."""
    if not 0 <= max_neighbors <= 50:
        raise ValueError('Neighbor limit must be between 0 and 50')
    if identity not in {note['id'] for note in data['notes']}:
        raise ValueError('Unknown focus identity')
    adjacent = sorted({e['target'] if e['source'] == identity else e['source']
                       for e in data['edges'] if identity in (e['source'], e['target'])} - {identity})
    selected = {identity, *adjacent[:max_neighbors]}
    result = {**data, 'focus': identity,
            'notes': [n for n in data['notes'] if n['id'] in selected],
            'edges': [e for e in data['edges'] if e['source'] in selected and e['target'] in selected],
            'neighbors_omitted': max(0, len(adjacent) - max_neighbors)}
    if len(json.dumps(result, ensure_ascii=False).encode()) > max_bytes:
        raise ValueError('Selection exceeds context byte limit; narrow the focus')
    return result


def markdown(data: dict, language: str = 'es') -> str:
    """Render a disposable navigation view, not canonical knowledge or approval."""
    notes = {n['id']: n for n in data['notes']}
    if language not in ('es', 'en'):
        raise ValueError('Projection language must be es or en')
    center = data.get('focus')
    links = [f'[[{n["path"][:-3]}]]' for n in data['notes'] if n['id'] != center]
    lines = ['---', 'view: read-only-projection']
    if links:
        # K-Plex default field; this groups the view, not scientific conclusions.
        lines.extend(['Children:', *['  - ' + json.dumps(link, ensure_ascii=False) for link in links]])
    heading = '# Selección de lectura' if language == 'es' else '# Reading selection'
    notice = ('Vista temporal. Relaciones y estados declarados no verificados; no es una aprobación.'
              if language == 'es' else
              'Disposable view. Declared relations and states are unverified; this is not approval.')
    lines.extend(['---', '', heading, '', notice, ''])
    for note in data['notes']:
        lines.append(f'- [[{note["path"][:-3]}]] — {note["role"]}; {note["maturity"]}; {note["review"]}')
    lines.extend(['', '## Conexiones declaradas' if language == 'es' else '## Declared connections', ''])
    for edge in data['edges']:
        # Prevent metadata from injecting Markdown headings/HTML in generated output.
        reason = edge['reason'].replace('\n', ' ').replace('\r', ' ')
        reason = reason.replace('<', '&lt;').replace('>', '&gt;').replace('[', '\\[').replace(']', '\\]')
        lines.append(f'- [[{notes[edge["source"]]["path"][:-3]}]] → {edge["kind"]} → '
                     f'[[{notes[edge["target"]]["path"][:-3]}]]: {reason}')
    return '\n'.join(lines) + '\n'


def main() -> int:
    """Run validation/projection with JSON errors and no filesystem writes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--focus')
    parser.add_argument('--neighbors', type=int, default=8)
    parser.add_argument('--format', choices=['json', 'markdown'], default='json')
    parser.add_argument('--language', choices=['es', 'en'], default='es')
    args = parser.parse_args()
    try:
        data = catalog(args.root)
        if args.focus:
            data = focus(data, args.focus, args.neighbors)
        if args.format == 'markdown' and not args.focus:
            raise ValueError('Markdown projection requires an explicit focus')
        print(markdown(data, args.language) if args.format == 'markdown' else json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RecursionError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
