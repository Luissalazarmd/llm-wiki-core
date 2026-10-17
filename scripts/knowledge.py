#!/usr/bin/env python3
"""Original read-only Markdown catalog; never authorizes canonical mutations."""
from __future__ import annotations

import hashlib
import argparse
import difflib
import json
import os
import posixpath
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
import yaml

ONTOLOGY = json.loads((Path(__file__).resolve().parents[1] / 'config/ontology.json').read_text())
LEGACY_ROLES = {'concept': 'note', 'entity': 'note', 'project': 'note', 'diagram': 'note'}
LEGACY_RELATIONS = {'groups', 'related', 'supported_by', 'contradicts', 'extends'}


def metadata_from(text: str) -> dict:
    """Parse bounded safe YAML, rejecting ambiguous or duplicate top-level fields."""
    text = text.replace('\r\n', '\n')  # Parsing only; hashes/writes retain original bytes.
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
                    if not (Path(current) / name).is_file():
                        raise ValueError('Only regular Markdown files are supported')
                    count += 1
                    if count > max_notes:
                        raise ValueError('Catalog exceeds note limit')
                    yield stage, Path(current) / name


def library_root(root: Path) -> Path:
    """Reject linked root/ancestors before resolving, consistently across helpers."""
    root = root.absolute()
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError('Symlink library root rejected')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Library root must be a directory')
    return root


def catalog(root: Path, max_file_bytes: int = 262144, max_notes: int = 2000, allow_empty: bool = False) -> dict:
    """Project source identities and versions without editing captured files."""
    root = library_root(root)
    if not any(os.path.lexists(root / stage) for stage in ('Raw', 'Wiki')):
        raise ValueError('Strict mode requires Raw/ or Wiki/; use --mode existing with an explicit --scope for this library')
    notes = []
    edges = []
    seen = set()
    organization = []
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
        declared_role = metadata.get('role', 'source' if stage == 'Raw' else 'note')
        if not isinstance(declared_role, str):
            raise ValueError('Invalid roles')
        role = LEGACY_ROLES.get(declared_role, declared_role)
        identity = metadata.get('id') or reference
        if identity is None and role in ('note', 'map'):
            identity = 'path:' + relative
        if 'id' in metadata and (not isinstance(metadata['id'], str) or not metadata['id'].strip()):
            raise ValueError('Explicit id must be a nonempty string')
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError('Note requires stable identity: id or Reference')

        declared_maturity = metadata.get('maturity')
        maturity = 'synthesis' if declared_maturity == 'developing' else metadata.get('maturity', 'unknown')
        for key, value in [('roles', role), ('maturity', maturity)]:
            if key == 'maturity' and 'maturity' not in metadata:
                continue
            if value not in ONTOLOGY[key]:
                raise ValueError('Invalid ' + key)
        if stage == 'Raw' and role != 'source':
            raise ValueError('Raw accepts source roles only')
        note_id = metadata.get('id') or ('source:' + hashlib.sha256(identity.encode()).hexdigest() if reference else identity)
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
            if not isinstance(relation, dict) or relation.get('kind') not in LEGACY_RELATIONS:
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
                'role': role, 'declared_role': declared_role,
                'maturity': maturity if role == 'note' else 'unknown',
                'declared_maturity': declared_maturity,
                'declared_review': metadata.get('review'),
                'review': 'unverified',
                'approval_available': False,
                'sha256': hashlib.sha256(raw).hexdigest(),
        })
        field = 'moc' if role == 'source' else 'parent' if role == 'map' else None
        if field and field in metadata and metadata[field] is not None:
            organization.append((note_id, relative, field, metadata[field]))
    if not notes and not allow_empty:
        raise ValueError('No notes in strict Raw/Wiki scope; use --mode existing with explicit --scope, or --allow-empty-strict only for an intentionally empty stage layout')
    ids = {note['id']: note for note in notes}
    paths = {note['path']: note for note in notes}
    grouped = {(edge['source'], edge['target']) for edge in edges if edge['kind'] == 'groups'}
    primary_parents = {}
    for child, declared_in, field, parent_path in organization:
        if (not isinstance(parent_path, str) or not parent_path.endswith('.md') or
                parent_path.startswith('/') or any(part in ('', '.', '..') for part in parent_path.split('/'))):
            raise ValueError('Primary organization requires an exact relative Markdown path')
        parent = paths.get(parent_path)
        if parent is None or parent['role'] != 'map':
            raise ValueError('Primary organization must resolve to a catalogued map')
        pair = (parent['id'], child)
        primary_parents[child] = parent['id']
        if pair not in grouped:
            edges.append({'source': parent['id'], 'target': child, 'kind': 'groups',
                          'reason': 'Primary organization; no scientific support implied.',
                          'declared_in': declared_in, 'declared_field': field,
                          'basis': 'primary_organization', 'review': 'unverified', 'evidence': []})
            grouped.add(pair)
    for child in primary_parents:
        visited = set()
        current = child
        while current in primary_parents:
            if current in visited or len(visited) >= 32:
                raise ValueError('Invalid or cyclic primary organization (maximum 32 ancestors)')
            visited.add(current)
            current = primary_parents[current]
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
    # Collapse only equivalent symmetric declarations, retaining their provenance.
    unique = []
    related = {}
    for edge in edges:
        if edge['kind'] != 'related':
            unique.append(edge)
            continue
        key = (tuple(sorted((edge['source'], edge['target']))), edge['reason'],
               json.dumps(edge['evidence'], sort_keys=True, ensure_ascii=False))
        if key in related:
            previous = related[key]
            if edge['declared_in'] != previous['declared_in']:
                previous.setdefault('also_declared_in', []).append(edge['declared_in'])
        else:
            related[key] = edge
            unique.append(edge)
    return {'notes': notes, 'edges': unique, 'mode': 'read_only', 'approval_available': False}


def discover(root: Path, scopes: list[str], max_notes: int = 200,
             max_file_bytes: int = 262144) -> dict:
    """Read explicitly selected existing-library Markdown; infer no persistent state."""
    root = library_root(root)
    if not scopes:
        raise ValueError('Existing-library discovery requires an explicit scope')
    paths = set()
    for scope in scopes:
        relative = Path(scope)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Scope must be a contained relative file or directory')
        current = root
        for part in relative.parts:
            if part.startswith('.'):
                raise ValueError('Hidden scope is not permitted')
            current = current / part
            if current.is_symlink():
                raise ValueError('Symlink scope rejected')
        if not current.exists():
            raise ValueError('Scope does not exist')
        if not current.is_dir() and not current.is_file():
            raise ValueError('Only regular files and directories are supported')
        if current.is_file() and current.suffix != '.md':
            raise ValueError('Scope must select a Markdown file or directory')
        candidates = [current] if current.is_file() else []
        if current.is_dir():
            for directory, dirs, files in os.walk(current, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
                for name in dirs + files:
                    if (Path(directory) / name).is_symlink():
                        raise ValueError('Symlink in scope rejected')
                for name in files:
                    if not name.startswith('.') and name.endswith('.md'):
                        if not (Path(directory) / name).is_file():
                            raise ValueError('Only regular Markdown files are supported')
                        candidates.append(Path(directory) / name)
                        if len(candidates) > max_notes:
                            raise ValueError('Discovery exceeds note limit; narrow scope')
        paths.update(p for p in candidates if p.suffix == '.md')
        if len(paths) > max_notes:
            raise ValueError('Discovery exceeds note limit; narrow scope')
    notes, issues, bodies = [], [], {}
    total = 0
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if any(char in relative for char in '[]|#\n\r\\'):
            raise ValueError('Unsafe Markdown link path')
        with path.open('rb') as stream:
            raw = stream.read(max_file_bytes + 1)
        if len(raw) > max_file_bytes:
            raise ValueError('Note exceeds byte limit')
        total += len(raw)
        if total > 16777216:
            raise ValueError('Discovery exceeds total byte limit')
        text = raw.decode('utf-8')
        try:
            properties = metadata_from(text)
        except (ValueError, RecursionError):
            properties = {}
            issues.append({'path': relative, 'kind': 'unparsed_frontmatter'})
        title = properties.get('title', properties.get('Title', path.stem))
        if not isinstance(title, str) or len(title) > 512 or '\n' in title:
            title = path.stem
            issues.append({'path': relative, 'kind': 'unsupported_title'})
        note_id = 'path:' + relative
        declared_maturity = properties.get('maturity')
        if not isinstance(declared_maturity, str) or declared_maturity not in (*ONTOLOGY['maturity'], 'developing'):
            if 'maturity' in properties:
                issues.append({'path': relative, 'kind': 'unsupported_maturity'})
            declared_maturity = None
        notes.append({'id': note_id, 'path': relative, 'title': title,
                      'identity_scope': 'path_locator_not_persistent',
                      'role': 'unknown', 'maturity': 'unknown', 'review': 'unverified',
                      'declared_maturity': declared_maturity,
                      'sha256': hashlib.sha256(raw).hexdigest(), 'approval_available': False})
        bodies[note_id] = text
    by_path = {n['path'][:-3]: n['id'] for n in notes}
    edges = []
    for note in notes:
        body = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', bodies[note['id']])
        body = re.sub(r'`+[^`\n]*`+', '', body)
        for target in sorted(set(re.findall(r'(?<!!)\[\[([^\]|#\n]+)', body))):
            target = target.removesuffix('.md')
            if '/' not in target:
                issues.append({'path': note['path'], 'kind': 'basename_link_requires_explicit_path',
                               'target': target})
                continue
            if target.startswith(('./', '../')):
                target = posixpath.normpath(posixpath.join(posixpath.dirname(note['path']), target))
            candidates = [by_path[target]] if target in by_path else []
            if len(candidates) != 1:
                issues.append({'path': note['path'], 'kind': 'unresolved_or_ambiguous_link',
                               'target': target})
                continue
            edges.append({'source': note['id'], 'target': candidates[0], 'kind': 'link',
                          'reason': 'Existing wikilink; no scientific relationship inferred',
                          'declared_in': note['path'], 'review': 'unverified'})
    rules = root / 'AGENTS.md'
    rule_paths = set()
    for selected in [*paths, *(root / scope for scope in scopes)]:
        directory = selected if selected.is_dir() else selected.parent
        for parent in [directory, *directory.parents]:
            if not parent.is_relative_to(root):
                continue
            candidate = parent / 'AGENTS.md'
            if candidate.is_file() and not candidate.is_symlink():
                rule_paths.add(candidate.relative_to(root).as_posix())
    return {'notes': notes, 'edges': edges, 'issues': issues,
            'library_rules_path': 'AGENTS.md' if rules.is_file() and not rules.is_symlink() else None,
            'rule_paths': sorted(rule_paths),
            'mode': 'existing_library_read_only', 'approval_available': False}


def new_target_path(root: Path, target: str) -> Path:
    """Validate an absent Markdown leaf under existing visible directories."""
    root = library_root(root)
    relative = Path(target)
    if (relative.is_absolute() or not relative.parts or '..' in relative.parts
            or relative.as_posix() != target or relative.suffix != '.md'
            or any(p.startswith('.') for p in relative.parts)
            or any(c in target for c in '[]|#\n\r\\')):
        raise ValueError('New target must be a safe relative Markdown path')
    current = root
    for part in relative.parts[:-1]:
        current /= part
        if current.is_symlink() or not current.is_dir():
            raise ValueError('New target parent must be an existing non-symlink directory')
    path = current / relative.name
    if os.path.lexists(path):
        raise ValueError('New target already exists; preserve it and review again')
    return path


def prepare_proposal(root: Path, target: str, draft: str, evidence: list[str], create: bool = False) -> dict:
    """Bind an existing base or absent destination and evidence; never write."""
    if len(draft.encode('utf-8')) > 262144:
        raise ValueError('Draft exceeds byte limit')
    # Discovery enforces path containment, link safety and bounded input reads.
    if create:
        new_target_path(root, target)
        if not draft.strip():
            raise ValueError('New derived note draft must be nonempty')
        if not evidence:
            raise ValueError('New derived notes require explicit evidence')
    data = discover(root, evidence if create else [target, *evidence])
    notes = {n['path']: n for n in data['notes']}
    if (not create and target not in notes) or any(path not in notes for path in evidence):
        raise ValueError('Proposal target and evidence must be existing Markdown files')
    original_bytes = b''
    if not create:
        with (root.resolve(strict=True) / target).open('rb') as stream:
            original_bytes = stream.read(262145)
        if len(original_bytes) > 262144 or hashlib.sha256(original_bytes).hexdigest() != notes[target]['sha256']:
            raise ValueError('Proposal base changed during preparation')
    target_binding = ({'path': target, 'operation': 'create', 'expected_absent': True, 'base_sha256': None}
                      if create else {'path': target, 'base_sha256': notes[target]['sha256']})
    original = original_bytes.decode('utf-8')
    packet = {'status': 'prepared_not_approved', 'approval_available': False,
              'apply_available': False, 'binding': 'content_only_not_authenticated',
              'target': target_binding,
              'draft': draft, 'draft_sha256': hashlib.sha256(draft.encode()).hexdigest(),
              'evidence': [{'path': p, 'sha256': notes[p]['sha256']} for p in sorted(set(evidence))],
              'diff': ''.join(difflib.unified_diff(original.splitlines(keepends=True),
                                                 draft.splitlines(keepends=True),
                                                 fromfile='/dev/null' if create else target,
                                                 tofile=target + ' (proposed)'))}
    packet['packet_sha256'] = hashlib.sha256(json.dumps(packet, sort_keys=True,
        ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    return packet


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
    if 'issues' in data:
        selected_paths = {n['path'] for n in result['notes']}
        result['issues'] = [issue for issue in data['issues'] if issue.get('path') in selected_paths]
    if len(json.dumps(result, ensure_ascii=False).encode()) > max_bytes:
        raise ValueError('Selection exceeds context byte limit; narrow the focus')
    return result


def markdown(data: dict, language: str = 'es', typed_navigation: bool = False) -> str:
    """Render a disposable navigation view, not canonical knowledge or approval."""
    notes = {n['id']: n for n in data['notes']}
    if language not in ('es', 'en'):
        raise ValueError('Projection language must be es or en')
    center = data.get('focus')
    links = [f'[[{n["path"][:-3]}]]' for n in data['notes'] if n['id'] != center]
    lines = ['---', 'view: read-only-projection']
    if typed_navigation:
        if center not in notes:
            raise ValueError('Typed navigation requires an explicit focus')
        label = 'Lectura' if language == 'es' else 'Reading'
        lines.append('title: ' + json.dumps(label + ' · ' + notes[center]['title'], ensure_ascii=False))
        fields = {}
        outgoing = {'groups': 'Children', 'related': 'Related', 'supported_by': 'Evidence',
                    'contradicts': 'Contrasts', 'extends': 'BuildsOn'}
        incoming = {'groups': 'Parent', 'related': 'Related', 'supported_by': 'EvidenceFor',
                    'contradicts': 'Contrasts', 'extends': 'DevelopedBy'}
        for edge in data['edges']:
            if edge['source'] == center:
                other, field = edge['target'], outgoing.get(edge['kind'])
            elif edge['target'] == center:
                other, field = edge['source'], incoming.get(edge['kind'])
            else:
                continue
            if field:
                fields.setdefault(field, set()).add(f'[[{notes[other]["path"][:-3]}]]')
        # Prefer a specific visual role over a generic friend for the same node.
        # All original kinds and reasons remain in the explanatory text below.
        if 'Related' in fields:
            specific = set().union(*(targets for key, targets in fields.items() if key != 'Related'))
            fields['Related'] -= specific
            if not fields['Related']:
                del fields['Related']
        for field, targets in sorted(fields.items()):
            lines.extend([field + ':', *['  - ' + json.dumps(link, ensure_ascii=False)
                                        for link in sorted(targets)]])
    elif links:
        # K-Plex default field; this groups the view, not scientific conclusions.
        lines.extend(['Children:', *['  - ' + json.dumps(link, ensure_ascii=False) for link in links]])
    heading = '# Selección de lectura' if language == 'es' else '# Reading selection'
    notice = ('Vista temporal. Relaciones y estados declarados no verificados; no es una aprobación.'
              if language == 'es' else
              'Disposable view. Declared relations and states are unverified; this is not approval.')
    lines.extend(['---', '', heading, '', notice, ''])
    if typed_navigation:
        focal_label = 'Objeto focal' if language == 'es' else 'Focal object'
        legend = ('Parent/Children organiza; Evidence enlaza apoyo; Contrasts enlaza contraste; '
                  'BuildsOn/DevelopedBy muestra desarrollo. Son declaraciones, no validación científica.'
                  if language == 'es' else
                  'Parent/Children organizes; Evidence links support; Contrasts links tension; '
                  'BuildsOn/DevelopedBy shows development. These are declarations, not scientific validation.')
        lines.extend([f'{focal_label}: [[{notes[center]["path"][:-3]}]].', '', legend, ''])
    maturity_labels = ({'seed': 'Semilla', 'developing': 'Síntesis', 'synthesis': 'Síntesis', 'evergreen': 'Evergreen',
                        'unknown': 'Desconocida'} if language == 'es' else
                       {'seed': 'Seed', 'developing': 'Synthesis', 'synthesis': 'Synthesis', 'evergreen': 'Evergreen',
                        'unknown': 'Unknown'})
    for note in data['notes']:
        if note['role'] in ('source', 'map'):
            lines.append(f'- [[{note["path"][:-3]}]] — {note["role"]}; {note["review"]}')
            continue
        maturity = maturity_labels[note['maturity']]
        declared_maturity = note.get('declared_maturity')
        if data.get('mode') == 'existing_library_read_only' and declared_maturity in maturity_labels:
            label = maturity_labels[declared_maturity]
            maturity = (f'madurez declarada: {label} — no verificada' if language == 'es' else
                        f'declared maturity: {label} — unverified')
        lines.append(f'- [[{note["path"][:-3]}]] — {note["role"]}; {maturity}; {note["review"]}')
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
    parser.add_argument('--mode', choices=['strict', 'existing'], default='strict')
    parser.add_argument('--allow-empty-strict', action='store_true', help='explicitly permit an empty Raw/Wiki-only projection')
    parser.add_argument('--scope', action='append', default=[])
    parser.add_argument('--proposal-target', help='relative Markdown target; draft from stdin')
    parser.add_argument('--create', action='store_true', help='propose a new derived note at an absent target')
    parser.add_argument('--evidence', action='append', default=[])
    parser.add_argument('--focus')
    parser.add_argument('--neighbors', type=int, default=8)
    parser.add_argument('--format', choices=['json', 'markdown'], default='json')
    parser.add_argument('--language', choices=['es', 'en'], default='es')
    parser.add_argument('--typed-navigation', action='store_true', help='typed fields for a disposable focal view')
    args = parser.parse_args()
    try:
        if args.typed_navigation and (not args.focus or args.format != 'markdown' or args.proposal_target):
            raise ValueError('Typed navigation requires focus and Markdown, not a proposal')
        if args.allow_empty_strict and (args.mode != 'strict' or args.proposal_target):
            raise ValueError('allow-empty-strict is only available for strict projection')
        if args.create and not args.proposal_target:
            raise ValueError('create requires proposal-target')
        if args.evidence and not args.proposal_target:
            raise ValueError('evidence requires proposal-target')
        if args.proposal_target:
            if args.focus or args.scope or args.format != 'json':
                raise ValueError('Proposal output is JSON; do not combine with focus/scope/Markdown')
            draft = sys.stdin.buffer.read(262145)
            if len(draft) > 262144:
                raise ValueError('Draft exceeds byte limit')
            data = prepare_proposal(args.root, args.proposal_target, draft.decode('utf-8'), args.evidence, args.create)
        elif args.mode == 'existing':
            data = discover(args.root, args.scope)
        else:
            if args.scope or args.evidence:
                raise ValueError('scope is only available in existing mode; evidence needs proposal-target')
            data = catalog(args.root, allow_empty=args.allow_empty_strict)
        if args.focus:
            data = focus(data, args.focus, args.neighbors)
        if args.format == 'markdown' and not args.focus:
            raise ValueError('Markdown projection requires an explicit focus')
        print(markdown(data, args.language, args.typed_navigation) if args.format == 'markdown'
              else json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RecursionError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
