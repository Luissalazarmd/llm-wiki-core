#!/usr/bin/env python3
"""Original scoped library mapper and personal-config adapter; read-only."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib
import json
import os
import posixpath
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
knowledge = importlib.import_module('knowledge')


def contained(root: Path, relative: str) -> Path:
    """Resolve a visible relative location without following any symbolic link."""
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('Path must be a nonempty relative string')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('Path must remain inside the library; root scope is not permitted')
    current = root
    for part in path.parts:
        if part.startswith('.'):
            raise ValueError('Hidden paths are not permitted')
        current /= part
        if current.is_symlink():
            raise ValueError('Symlink path rejected')
    if not current.exists():
        raise ValueError('Selected path does not exist')
    if not current.is_dir() and not current.is_file():
        raise ValueError('Only regular files and directories are supported')
    return current


PROPOSAL_STATUSES = ('pending', 'accepted', 'rejected', 'withdrawn')
PARKED_LABELS = {
    'es': {'title': '# Propuesta en custodia', 'history': '## Historial', 'text': '## Texto propuesto',
           'notice': '> Custodia, no aceptación: texto literal recibido de su origen, sin revisar ni aprobar.',
           'received': 'pendiente · recibida de'},
    'en': {'title': '# Parked proposal', 'history': '## History', 'text': '## Proposed text',
           'notice': '> Custody, not acceptance: literal text received from its origin, neither reviewed nor approved.',
           'received': 'pending · received from'},
}


def overlaps(root: Path, first: str, second: str) -> bool:
    """True when two selections share any location, by spelling or filesystem identity."""
    a, b = root / first, root / second
    if a == b or a.is_relative_to(b) or b.is_relative_to(a):
        return True
    for inner, outer in ((a, b), (b, a)):
        for candidate in (inner, *inner.parents):
            if candidate == root or not candidate.is_relative_to(root):
                break
            try:
                if os.path.samefile(candidate, outer):
                    return True
            except OSError:
                continue
    return False


def in_proposals(settings: dict, path: Path) -> bool:
    """Strictly inside a declared proposals folder, by spelling only: a mismatch refuses."""
    root = Path(settings['library_root'])
    return '..' not in path.parts and any(path != root / selected and path.is_relative_to(root / selected)
                                          for selected in settings.get('layers', {}).get('proposals', []))


def parked_parts(text: str):
    """Split a parked proposal into (metadata, header, literal text); None when it is not one."""
    try:
        metadata = knowledge.metadata_from(text)
    except (ValueError, RecursionError):
        return None
    if 'proposal_status' not in metadata:
        return None
    found = [(index, len(marker)) for marker in (f"\n{labels['text']}\n\n" for labels in PARKED_LABELS.values())
             if (index := text.find(marker)) != -1]
    if not found:
        return None
    index, length = min(found)
    return metadata, text[:index], text[index + length:]


def parked_note(language: str, text: str, origin: str, proposed_target: str, received: str,
                conversation: str | None = None, evidence: list[dict] | None = None) -> str:
    """Wrap literal proposal text in the minimal parked format; the text itself is never edited."""
    fields = {'origin': origin, 'proposed_target': proposed_target, 'received': received,
              **({'conversation': conversation} if conversation is not None else {})}
    for name, value in fields.items():
        if (not isinstance(value, str) or not value.strip() or len(value) > 512
                or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValueError(f'Parked proposal {name} must be one nonempty line of at most 512 characters')
    if not text.strip():
        raise ValueError('Parked proposal text must be nonempty')
    labels = PARKED_LABELS[language]
    quote = lambda value: json.dumps(value, ensure_ascii=False)  # A JSON string is a YAML scalar.
    lines = ['---', 'proposal_status: pending', 'origin: ' + quote(origin)]
    if conversation is not None:
        lines.append('conversation: ' + quote(conversation))
    lines += ['received: ' + quote(received), 'proposed_target: ' + quote(proposed_target)]
    if evidence:
        lines.append('evidence:')
        for item in evidence:
            lines += [f'  - {key}: {quote(value)}' if position == 0 else f'    {key}: {quote(value)}'
                      for position, (key, value) in enumerate(item.items())]
    lines += ['text_sha256: ' + quote(hashlib.sha256(text.encode('utf-8')).hexdigest()), '---',
              labels['title'], '', labels['notice'], '', labels['history'], '',
              f"- {received} · {labels['received']} {origin}", '', labels['text'], '']
    return '\n'.join(lines) + '\n' + text


def check_custody(settings: dict, path: Path, packet: dict) -> None:
    """Writer-side custody boundary: declared proposals layer and literal pending format only."""
    if not in_proposals(settings, path):
        raise ValueError('Custody is only available inside the declared layers.proposals; '
                         'every other location requires the complete review loop')
    parts = parked_parts(packet['draft'])
    if parts is None:
        raise ValueError('Custody requires the parked-proposal format')
    metadata, _, literal = parts
    if metadata['proposal_status'] != 'pending':
        raise ValueError('Custody can only park a pending proposal; closing one is a reviewed update')
    if set(metadata) & {'role', 'maturity', 'review'}:
        raise ValueError('A parked proposal declares no role, maturity or review of its own')
    if (not all(isinstance(metadata.get(key), str) and metadata[key].strip()
                for key in ('origin', 'received', 'proposed_target'))
            or not literal.strip()
            or metadata.get('text_sha256') != hashlib.sha256(literal.encode('utf-8')).hexdigest()):
        raise ValueError('Parked proposal requires origin, received, proposed_target and its exact bound text')


def check_owner_seed(settings: dict, target: str, draft: str) -> None:
    """Writer-side boundary for a seed declared as the owner's: retained knowledge only, exact shape."""
    root, layers = Path(settings['library_root']), settings.get('layers', {})
    if any(overlaps(root, target, other) for layer in ('sources', 'proposals') for other in layers.get(layer, [])):
        raise ValueError('An owner-authored seed never lands in layers.sources or layers.proposals; '
                         'a proposal received from anyone else is parked with --park')
    retained = [*layers.get('knowledge', []), *layers.get('drafts', [])]
    if retained and not any((root / target).is_relative_to(root / selected) for selected in retained):
        raise ValueError('An owner-authored seed must be inside the declared layers.knowledge or layers.drafts')
    problem = knowledge.owner_seed_problem(draft)
    if problem:
        raise ValueError(problem)


def check_closure(previous: str, draft: str) -> None:
    """Updating a parked proposal keeps its origin, literal text and history lines."""
    before = parked_parts(previous)
    if before is None:
        return
    after = parked_parts(draft)
    if after is None or after[0]['proposal_status'] not in PROPOSAL_STATUSES:
        raise ValueError('A parked proposal stays a parked proposal: keep its format and use a status of '
                         + ', '.join(PROPOSAL_STATUSES))
    if after[2] != before[2] or any(after[0].get(key) != before[0].get(key)
                                    for key in ('origin', 'received', 'conversation', 'text_sha256')):
        raise ValueError('Closing a parked proposal must keep its origin and exact proposed text')
    kept = after[1].splitlines()
    if any(line not in kept for line in before[1].splitlines() if line.startswith('- ')):
        raise ValueError('Closing a parked proposal must keep its history lines; append, never erase')


def load_config(path: Path) -> dict:
    """Validate personal settings; relative library root is relative to this file."""
    if path.is_symlink():
        raise ValueError(f'Configuration file is a symlink: {path}; retry with {os.path.realpath(path)} '
                         'if that is the intended configuration')
    if knowledge.linked_ancestor(path.absolute().parent) is not None:
        raise knowledge.symlink_refusal('Symlink configuration ancestor', path.absolute(), 'configuration')
    if not path.exists():
        raise ValueError(
            'Configuration file not found. Continue authorized reading and proposals through host tools, '
            'or explicitly configure the existing library under its rules. '
            'This helper does not install tools, create configuration or enable writing.')
    if not path.is_file():
        raise ValueError('Configuration must be a regular non-symlink file')
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Configuration exceeds byte limit')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate configuration key')
            result[key] = value
        return result
    try:
        data = json.loads(raw, object_pairs_hook=unique)
    except json.JSONDecodeError as exc:
        raise ValueError(str(exc)) from exc
    legacy = {'objectives', 'organization', 'initiative'}  # Accepted and ignored for compatibility; never a control.
    keys = {'version', 'library_root', 'authorized_paths', 'language', 'layers', 'write_policy',
            'recovery_directory', 'capture_policy', 'living_synthesis', *legacy}
    if not isinstance(data, dict) or set(data) - keys:
        raise ValueError('Unknown configuration fields; no credentials or runtime settings allowed')
    if type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Unsupported configuration version')
    if not isinstance(data.get('library_root'), str) or not data['library_root']:
        raise ValueError('library_root is required')
    root = Path(data['library_root'])
    if not root.is_absolute():
        root = path.resolve().parent / root
    # Resolve parents only after rejecting symlinks in the configured root chain.
    if knowledge.linked_ancestor(root) is not None:
        raise knowledge.symlink_refusal('Symlink library root', root, 'library')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('library_root must be a directory')
    allowed = data.get('authorized_paths')
    if not isinstance(allowed, list) or not allowed or len(allowed) > 100:
        raise ValueError('authorized_paths requires 1 to 100 selected paths')
    for relative in allowed:
        contained(root, relative)
    if data.get('language', 'es') not in ('es', 'en'):
        raise ValueError('Supported languages: es, en')
    layers = data.get('layers', {})
    if not isinstance(layers, dict) or set(layers) - {'sources', 'drafts', 'knowledge', 'proposals', 'views'}:
        raise ValueError('Invalid layer correspondence')
    for layer, selections in layers.items():
        if not isinstance(selections, list) or len(selections) > 100:
            raise ValueError('Layer correspondence must contain path lists')
        for relative in selections:
            if layer != 'views':
                authorize(root, allowed, relative)
    for relative in layers.get('views', []):
        # Navigation folders for view_write.py only: never originals, proposals or retained knowledge.
        selected = contained(root, relative)
        if not selected.is_dir() or selected.relative_to(root).as_posix() != relative:
            raise ValueError('layers.views entries must be exact existing directories')
        for layer in ('sources', 'proposals', 'knowledge', 'drafts'):
            if any(overlaps(root, relative, other) for other in layers.get(layer, [])):
                raise ValueError(f'layers.views must not overlap layers.{layer}')
    if 'proposals' in layers:
        # Custody may create files here without review, so the layer must be unmistakable.
        if 'sources' not in layers or 'knowledge' not in layers:
            raise ValueError('layers.proposals requires explicit layers.sources and layers.knowledge: declare '
                             'the originals and the retained knowledge that custody must never touch')
        for relative in layers['proposals']:
            selected = contained(root, relative)
            if not selected.is_dir() or selected.relative_to(root).as_posix() != relative:
                raise ValueError('layers.proposals entries must be exact existing directories')
            for layer in ('sources', 'knowledge'):
                if any(overlaps(root, relative, other) for other in layers[layer]):
                    raise ValueError(f'layers.proposals must not overlap layers.{layer}')
    if 'capture_policy' in data:
        policy = data['capture_policy']
        if (not isinstance(policy, dict) or set(policy) - {'roots', 'taxonomy_path', 'fields'}
                or not isinstance(policy.get('roots'), list) or not 1 <= len(policy['roots']) <= 20
                or not isinstance(policy.get('taxonomy_path'), str)):
            raise ValueError('Invalid capture_policy; explicit roots and taxonomy_path are required')
        for relative in [*policy['roots'], policy['taxonomy_path']]:
            selected = authorize(root, allowed, relative)
            if selected.suffix != '.md' or not selected.is_file() or selected.relative_to(root).as_posix() != relative:
                raise ValueError('Capture policy paths must be exact regular Markdown paths')
        if len(set(policy['roots'])) != len(policy['roots']):
            raise ValueError('Duplicate capture roots')
        fields = policy.get('fields', {})
        if (not isinstance(fields, dict) or set(fields) - {'moc', 'parent', 'role', 'tags', 'taxonomy_tags'}
                or any(not isinstance(v, str) or not v.strip() or len(v) > 64 for v in fields.values())):
            raise ValueError('Invalid capture field mapping')
        effective = {'moc': 'moc', 'parent': 'parent', 'role': 'role', 'tags': 'tags', **fields}
        if len({effective[k].casefold() for k in ('moc', 'parent', 'role', 'tags')}) != 4:
            raise ValueError('Capture fields for MOC, parent, role and tags must be distinct')
    if 'living_synthesis' in data:
        profile = data['living_synthesis']
        if (not isinstance(profile, dict) or not {'scopes', 'history_complete'} <= set(profile)
                or set(profile) - {'scopes', 'history_complete', 'references_complete'}
                or ('references_complete' in profile and type(profile['references_complete']) is not bool)
                or profile['history_complete'] is not True or not isinstance(profile['scopes'], list)
                or not 1 <= len(profile['scopes']) <= 20
                or any(not isinstance(s, str) for s in profile['scopes'])
                or len(set(profile['scopes'])) != len(profile['scopes'])):
            raise ValueError('Living synthesis requires bounded scopes and explicit complete history')
        for scope in profile['scopes']:
            selected = authorize(root, allowed, scope)
            if selected.relative_to(root).as_posix() != scope:
                raise ValueError('Numbering scopes must be exact authorized paths')
    if data.get('write_policy', 'read_only') not in ('read_only', 'canonical_engine', 'plain_files'):
        raise ValueError('Invalid write_policy')
    recovery = data.get('recovery_directory')
    if recovery is not None:
        if not isinstance(recovery, str) or not recovery:
            raise ValueError('Invalid recovery_directory')
        recovery_path = Path(recovery)
        if not recovery_path.is_absolute():
            recovery_path = path.resolve().parent / recovery_path
        if knowledge.linked_ancestor(recovery_path) is not None:
            raise knowledge.symlink_refusal('Symlink recovery directory', recovery_path, 'recovery directory')
        recovery_path = recovery_path.resolve(strict=True)
        if not recovery_path.is_dir() or recovery_path.is_relative_to(root):
            raise ValueError('Recovery directory must exist outside the library')
        if recovery_path.is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError('Recovery directory is inside the Core checkout: recovery records contain '
                             'private notes and this checkout is a public repository; pick a location outside')
        data['recovery_directory'] = str(recovery_path)
    if data.get('write_policy') == 'plain_files' and recovery is None:
        raise ValueError('plain_files requires an authorized recovery_directory')
    if data.get('write_policy') == 'plain_files' and 'sources' not in layers:
        raise ValueError('plain_files requires layers.sources: declare the existing original locations '
                         'the writer must never touch, or "sources": [] to declare none')
    return {**{k: v for k, v in data.items() if k not in legacy}, 'library_root': str(root),
            'language': data.get('language', 'es'), 'layers': layers}


def authorize(root: Path, allowed: list[str], relative: str, create: bool = False) -> Path:
    """A config restricts Core operations; it cannot grant host permissions."""
    target = knowledge.new_target_path(root, relative) if create else contained(root, relative)
    for scope in allowed:
        boundary = contained(root, scope)
        if target == boundary or (boundary.is_dir() and target.is_relative_to(boundary)):
            return target
    raise ValueError('Selection is outside authorized_paths')


def inventory(root: Path, scopes: list[str], max_entries: int = 500) -> list[Path]:
    """List visible selected entries, including attachments, without reading binary bytes."""
    paths = set()
    for scope in scopes:
        selected = contained(root, scope)
        paths.add(selected)
        if selected.is_dir():
            for directory, dirs, files in os.walk(selected, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
                for name in dirs + sorted(f for f in files if not f.startswith('.')):
                    item = Path(directory) / name
                    if item.is_symlink():
                        raise ValueError('Symlink in selection rejected: ' + item.relative_to(root).as_posix())
                    if not item.is_dir() and not item.is_file():
                        raise ValueError('Only regular files and directories are supported: '
                                         + item.relative_to(root).as_posix())
                    paths.add(item)
                    if len(paths) > max_entries:
                        raise ValueError(f'Inventory exceeds entry limit ({max_entries}) at {scope}; narrow scope')
        if len(paths) > max_entries:
            raise ValueError(f'Inventory exceeds entry limit ({max_entries}) at {scope}; narrow scope')
    return sorted(paths)


def map_library(root: Path, scopes: list[str], layers: dict) -> dict:
    """Return observations and declared mapping, never semantic classification or migration."""
    entries = inventory(root, scopes)
    note_paths = [p.relative_to(root).as_posix() for p in entries if p.is_file() and p.suffix == '.md']
    data = knowledge.discover(root, note_paths) if note_paths else {
        'notes': [], 'edges': [], 'issues': [], 'approval_available': False}
    folders = [p.relative_to(root).as_posix() for p in entries if p.is_dir()]
    attachments = [{'path': p.relative_to(root).as_posix(), 'extension': p.suffix,
                    'bytes': p.stat().st_size, 'content_read': False}
                   for p in entries if p.is_file() and p.suffix != '.md']
    keys, without_metadata, attachment_links = set(), 0, []
    attachment_paths = {item['path'] for item in attachments}
    skipped = {issue['path'] for issue in data['issues'] if issue['kind'] in knowledge.SKIPPED_NOTE_KINDS}
    for relative in note_paths:
        if relative in skipped:
            continue
        with (root / relative).open('rb') as stream:
            text = stream.read(262145).decode('utf-8')
        body = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', text)
        body = re.sub(r'`+[^`\n]*`+', '', body)
        for target in sorted(set(re.findall(r'!\[\[([^\]|#\n]+)', body))):
            if target.startswith(('./', '../')):
                target = posixpath.normpath(posixpath.join(posixpath.dirname(relative), target))
            matches = [p for p in attachment_paths if p == target or Path(p).name == target]
            if not matches and '/' in target:
                relative_target = posixpath.normpath(posixpath.join(posixpath.dirname(relative), target))
                matches = [relative_target] if relative_target in attachment_paths else []
            if len(matches) == 1:
                attachment_links.append({'source': relative, 'target': matches[0],
                                         'kind': 'embed', 'review': 'unverified'})
            else:
                data['issues'].append({'path': relative, 'kind': 'unresolved_or_ambiguous_attachment',
                                       'target': target})
        try:
            metadata = knowledge.metadata_from(text)
        except (ValueError, RecursionError):
            continue
        keys.update(metadata)
        if not metadata:
            without_metadata += 1
    rules = set()
    for path in entries:
        for parent in [path.parent, *path.parents]:
            if not parent.is_relative_to(root):
                continue
            rule = parent / 'AGENTS.md'
            if rule.is_file() and not rule.is_symlink():
                rules.add(rule.relative_to(root).as_posix())
    proposal = []
    for layer in ('sources', 'drafts', 'knowledge', 'proposals'):
        if layer == 'proposals' and layer not in layers:
            continue
        selected = [p for p in layers.get(layer, [])
                    if any((root / p).is_relative_to(root / s) or (root / s).is_relative_to(root / p)
                           for s in scopes)]
        proposal.append({'layer': layer, 'paths': selected,
                         'basis': 'personal_configuration' if selected else 'human_or_agent_review_needed',
                         'status': 'declared_not_verified' if selected else 'unassigned'})
    return {**data, 'mode': 'scoped_library_map_read_only', 'folders': folders,
            'attachments': attachments, 'attachment_links': attachment_links, 'rule_paths': sorted(rules),
            'conventions': {'metadata_keys': sorted(keys), 'notes_without_metadata': without_metadata,
                            'link_parser': 'limited_wikilinks', 'classification_inferred': False},
            'layer_proposal': proposal,
            'summary': {'notes': len(data['notes']), 'attachments': len(attachments),
                        'folders': len(folders), 'links': len(data['edges'])},
            'migration_performed': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('map', 'read'):
        command = sub.add_parser(action)
        command.add_argument('--scope', action='append', required=True)
        if action == 'read':
            command.add_argument('--focus')
            command.add_argument('--format', choices=['json', 'markdown'], default='json')
    proposal = sub.add_parser('proposal')
    proposal.add_argument('--target', required=True)
    proposal.add_argument('--create', action='store_true', help='propose an absent derived-note target')
    proposal.add_argument('--evidence', action='append', default=[])
    proposal.add_argument('--move-primary', action='store_true', help='prepare a reviewed primary-MOC move with reserved history and map companion edits')
    proposal.add_argument('--park', action='store_true',
                          help='custody, not acceptance: wrap literal stdin as a pending proposal at an absent '
                               'target inside layers.proposals; evidence is optional')
    proposal.add_argument('--owner-authored', action='store_true',
                          help='with --create: the agent declares that the library owner authored this new seed in '
                               'conversation, so it has no library evidence; the draft itself must declare role: '
                               'note, maturity: seed and origin: owner. Not proof of authorship, not approval')
    proposal.add_argument('--origin', help='with --park: who authored the proposal (agent or person)')
    proposal.add_argument('--conversation', help='with --park: where it was received')
    proposal.add_argument('--proposed-target', help='with --park: the destination the origin proposes')
    proposal.add_argument('--received', help='with --park: ISO date, default today')
    proposal.add_argument('--external-evidence', action='append', default=[],
                          help='with --park: a reference or version stated by the origin, recorded unverified')
    batch = sub.add_parser('proposal-batch', help='prepare up to 20 scoped numbered changes from a JSON array on stdin; not approval')
    batch.add_argument('--evidence', action='append', default=[])
    args = parser.parse_args()
    try:
        settings = load_config(args.config)
        root = Path(settings['library_root'])
        paths = ([args.target, *args.evidence] if args.action == 'proposal'
                 else args.evidence if args.action == 'proposal-batch' else args.scope)
        for path in paths:
            authorize(root, settings['authorized_paths'], path,
                      create=args.action == 'proposal' and (args.create or args.park) and path == args.target)
        if args.action == 'map':
            data = map_library(root, args.scope, settings['layers'])
        elif args.action == 'read':
            data = knowledge.discover(root, args.scope)
            if args.focus:
                data = knowledge.focus(data, args.focus)
            if args.format == 'markdown':
                if not args.focus:
                    raise ValueError('Markdown requires an explicit focus')
                print(knowledge.markdown(data, settings['language']), end='')
                return 0
        else:
            draft = sys.stdin.buffer.read(262145)
            if len(draft) > 262144:
                raise ValueError('Draft exceeds byte limit')
            numbering = importlib.import_module('numbering')
            text = draft.decode('utf-8')
            binding = None
            if args.action == 'proposal-batch':
                data = numbering.prepare_batch(settings, json.loads(text), args.evidence)
                print(json.dumps(data, ensure_ascii=False, indent=2))
                return 0
            park_only = (args.origin, args.conversation, args.proposed_target, args.received)
            if args.action == 'proposal' and not args.park and (any(v is not None for v in park_only)
                                                                or args.external_evidence):
                raise ValueError('origin, conversation, proposed-target, received and external-evidence need --park')
            if args.owner_authored:
                if not args.create or args.park or args.move_primary or args.evidence:
                    raise ValueError('--owner-authored is one narrow creation: use it with --create only, without '
                                     '--evidence, --park or --move-primary')
                check_owner_seed(settings, args.target, text)
            if args.action == 'proposal' and args.park:
                if args.create or args.move_primary:
                    raise ValueError('--park is its own operation; do not combine it with --create or --move-primary')
                if args.origin is None or args.proposed_target is None:
                    raise ValueError('--park requires --origin and --proposed-target')
                if not in_proposals(settings, root / args.target):
                    raise ValueError('Custody is only available inside the declared layers.proposals; '
                                     'every other location requires the complete review loop')
                if numbering.in_scope(settings, args.target):
                    raise ValueError('Custody is unavailable inside a numbered scope')
                received = args.received or datetime.date.today().isoformat()
                datetime.date.fromisoformat(received)
                bound = knowledge.discover(root, args.evidence)['notes'] if args.evidence else []
                hashes = {note['path']: note['sha256'] for note in bound}
                evidence = ([{'path': p, 'sha256': hashes[p]} for p in sorted(set(args.evidence)) if p in hashes]
                            + [{'reference': r, 'verified': 'no'} for r in args.external_evidence])
                text = parked_note(settings['language'], text, args.origin, args.proposed_target, received,
                                   args.conversation, evidence)
                data = knowledge.prepare_proposal(root, args.target, text, args.evidence, custody=True)
                print(json.dumps(data, ensure_ascii=False, indent=2))
                return 0
            if args.move_primary:
                data = numbering.prepare_batch(settings, [{'target': args.target, 'draft': text,
                    'create': args.create, 'move_primary': True}], args.evidence)
                print(json.dumps(data, ensure_ascii=False, indent=2))
                return 0
            if numbering.in_scope(settings, args.target):
                text, binding = numbering.candidate(settings, args.target, text, args.create)
            data = knowledge.prepare_proposal(root, args.target, text, args.evidence, args.create,
                                              owner_authored=args.owner_authored)
            if binding is not None:
                numbering.bind_packet(data, binding)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
