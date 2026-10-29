#!/usr/bin/env python3
"""Original scoped library mapper and personal-config adapter; read-only."""
from __future__ import annotations

import argparse
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


def load_config(path: Path) -> dict:
    """Validate personal settings; relative library root is relative to this file."""
    if any(p.is_symlink() for p in [path, *path.absolute().parents]) or not path.is_file():
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
    keys = {'version', 'library_root', 'authorized_paths', 'objectives', 'language',
            'organization', 'initiative', 'layers', 'write_policy', 'recovery_directory', 'capture_policy',
            'living_synthesis'}
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
    if any(p.is_symlink() for p in [root, *root.parents]):
        raise ValueError('Symlink library root rejected')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('library_root must be a directory')
    allowed = data.get('authorized_paths')
    if not isinstance(allowed, list) or not allowed or len(allowed) > 100:
        raise ValueError('authorized_paths requires 1 to 100 selected paths')
    for relative in allowed:
        contained(root, relative)
    objectives = data.get('objectives', [])
    if not isinstance(objectives, list) or len(objectives) > 20 or any(
            not isinstance(v, str) or not v.strip() or len(v) > 1024 for v in objectives):
        raise ValueError('Invalid objectives')
    if data.get('language', 'es') not in ('es', 'en'):
        raise ValueError('Supported languages: es, en')
    if data.get('organization', 'preserve') not in ('preserve', 'flat', 'grouped'):
        raise ValueError('Invalid organization preference')
    if data.get('initiative', 'within_focus') not in ('on_request', 'within_focus'):
        raise ValueError('Invalid initiative preference; no background mode')
    layers = data.get('layers', {})
    if not isinstance(layers, dict) or set(layers) - {'sources', 'drafts', 'knowledge'}:
        raise ValueError('Invalid layer correspondence')
    for selections in layers.values():
        if not isinstance(selections, list) or len(selections) > 100:
            raise ValueError('Layer correspondence must contain path lists')
        for relative in selections:
            authorize(root, allowed, relative)
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
        if any(p.is_symlink() for p in [recovery_path, *recovery_path.parents]):
            raise ValueError('Symlink recovery directory rejected')
        recovery_path = recovery_path.resolve(strict=True)
        if not recovery_path.is_dir() or recovery_path.is_relative_to(root):
            raise ValueError('Recovery directory must exist outside the library')
        data['recovery_directory'] = str(recovery_path)
    if data.get('write_policy') == 'plain_files' and recovery is None:
        raise ValueError('plain_files requires an authorized recovery_directory')
    return {**data, 'library_root': str(root), 'language': data.get('language', 'es'),
            'organization': data.get('organization', 'preserve'),
            'initiative': data.get('initiative', 'within_focus'), 'layers': layers}


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
                        raise ValueError('Symlink in selection rejected')
                    if not item.is_dir() and not item.is_file():
                        raise ValueError('Only regular files and directories are supported')
                    paths.add(item)
                    if len(paths) > max_entries:
                        raise ValueError('Inventory exceeds entry limit; narrow scope')
        if len(paths) > max_entries:
            raise ValueError('Inventory exceeds entry limit; narrow scope')
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
    for relative in note_paths:
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
    for layer in ('sources', 'drafts', 'knowledge'):
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
                      create=args.action == 'proposal' and args.create and path == args.target)
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
            if args.move_primary:
                data = numbering.prepare_batch(settings, [{'target': args.target, 'draft': text,
                    'create': args.create, 'move_primary': True}], args.evidence)
                print(json.dumps(data, ensure_ascii=False, indent=2))
                return 0
            if numbering.in_scope(settings, args.target):
                text, binding = numbering.candidate(settings, args.target, text, args.create)
            data = knowledge.prepare_proposal(root, args.target, text, args.evidence, args.create)
            if binding is not None:
                numbering.bind_packet(data, binding)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
