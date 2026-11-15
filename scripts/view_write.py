#!/usr/bin/env python3
"""Optional writer for views (.canvas, .base, Markdown declaring role: view): navigation, never knowledge; NOT an approval engine."""
import argparse
import datetime
import difflib
import json
import os
import re
import stat
import sys
import uuid
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
import capture_write
import library
import note_write
import numbering

FORMAT = 'view-v1'
KINDS = {'.canvas': 'canvas', '.base': 'base', '.md': 'markdown'}
# Instruction files an agent host may load: never written here, whatever they declare.
RULES = frozenset(('agents.md', 'skill.md', 'claude.md', 'gemini.md', 'soul.md', 'copilot-instructions.md'))
PART = re.compile(r'[^\x00-\x1f\x7f/\\\[\]|#^:*?"<>%]{1,120}')
CONTENT = ('sources', 'proposals', 'knowledge', 'drafts')
# Declarations that belong to retained knowledge or custody; a view carrying one is a note in disguise.
KNOWLEDGE_KEYS = ('maturity', 'origin', 'proposal_status', 'primary_moc', 'address', 'former_addresses',
                  'map_kind', 'review')
SIDES, ENDS = ('top', 'right', 'bottom', 'left'), ('none', 'arrow')
NODE_KEYS = {'id', 'type', 'x', 'y', 'width', 'height', 'color', 'text', 'file', 'subpath', 'url', 'label',
             'background', 'backgroundStyle'}
EDGE_KEYS = {'id', 'fromNode', 'fromSide', 'fromEnd', 'toNode', 'toSide', 'toEnd', 'color', 'label'}
BASE_KEYS = ('filters', 'formulas', 'properties', 'summaries', 'views')


def in_views(settings, path):
    """Strictly inside a folder the owner declared in layers.views, by spelling only."""
    root = Path(settings['library_root'])
    return any(path != root / folder and path.is_relative_to(root / folder)
               for folder in settings['layers'].get('views', []))


def selected(settings, path):
    """Inside what the owner's settings select as library content for the other helpers."""
    root = Path(settings['library_root'])
    return any(path == root / scope or path.is_relative_to(root / scope) for scope in settings['authorized_paths'])


def target(settings, relative):
    """A view file directly in the library root or inside a declared views folder; never library content."""
    root = Path(settings['library_root'])
    path = Path(relative) if isinstance(relative, str) else None
    if (path is None or not relative or path.is_absolute() or path.as_posix() != relative or '..' in path.parts
            or any(not PART.fullmatch(part) or part.startswith('.') or part != part.strip() for part in path.parts)):
        raise ValueError('View target must be a visible relative path inside the library, without traversal, '
                         f'hidden folders or link characters: {relative!r}')
    if path.suffix not in KINDS or not path.stem:
        raise ValueError(f'A view is a .canvas, .base or .md file: {relative!r}')
    if path.name.casefold() in RULES:
        raise ValueError(f'This helper never writes agent instruction or rules files: {path.name}')
    current = root
    for part in path.parts[:-1]:
        current /= part
        if current.is_symlink() or not current.is_dir():
            raise ValueError(f'View folder must be an existing real directory, not a symlink: {relative}')
    path = current / path.name
    declared = in_views(settings, path)
    if len(Path(relative).parts) != 1 and not declared:
        raise ValueError(f'Views live directly in the library root or inside a folder declared in layers.views: '
                         f'{relative}. Notes, sources and proposals keep their own reviewed writers')
    for layer in CONTENT:
        if any(library.overlaps(root, relative, other) for other in settings['layers'].get(layer, [])):
            raise ValueError(f'View target is inside layers.{layer}: {relative}. A view is navigation, never an '
                             'original, a proposal or retained knowledge')
    if numbering.in_scope(settings, relative):
        raise ValueError(f'View target is inside a numbered living-synthesis scope: {relative}')
    kind = KINDS[path.suffix]
    if kind == 'markdown' and not declared and selected(settings, path):
        raise ValueError(f'{relative} is selected as library content in authorized_paths: save it as a note through '
                         'library.py proposal and note_write.py, or declare its folder in layers.views')
    if os.path.lexists(path):
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f'View is not a regular non-symlink file: {relative}')
    else:
        for other in path.parent.iterdir():
            if other.name.casefold() == path.name.casefold():
                raise ValueError(f'A file differing only by case already exists: {other.relative_to(root).as_posix()}')
    return relative, path, kind


def library_file(settings, relative, label):
    """An existing regular file inside the library, reached without hidden parts or symlinks. Read-only."""
    path = Path(relative) if isinstance(relative, str) else None
    if (path is None or not relative or '\\' in relative or path.is_absolute() or '..' in path.parts
            or path.as_posix() != relative or any(part.startswith('.') for part in path.parts)):
        raise ValueError(f'{label} must be a visible library-relative path: {relative!r}')
    current = Path(settings['library_root'])
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f'{label} passes through a symlink: {relative}')
    if not os.path.lexists(current) or not stat.S_ISREG(current.lstat().st_mode):
        raise ValueError(f'{label} points to a missing library file: {relative}')
    return current


def check_subpath(settings, relative, path, subpath, label):
    """A #Heading or #^block that exists in a Markdown file the settings let this helper read."""
    if not isinstance(subpath, str) or not subpath.startswith('#') or len(subpath) < 2:
        raise ValueError(f'{label} subpath must be a string starting with #')
    if path.suffix != '.md':
        return False  # A PDF page or similar: Obsidian's own syntax, not verified here.
    if not (len(Path(relative).parts) == 1 or in_views(settings, path) or selected(settings, path)):
        raise ValueError(f'{label} subpath cannot be verified: {relative} is outside authorized_paths and the view '
                         'locations; link the file without a subpath')
    text = note_write.read_bytes(path).decode('utf-8')
    fold = lambda value: ' '.join(value.split()).casefold()
    headings = {fold(m[1]) for line in library.knowledge.visible_body(text)
                if (m := re.match(r'^#{1,6} (.+?)(?:\s+#+)?\s*$', line))}
    for part in subpath[1:].split('#'):
        found = (re.search(rf'(?m)(?:^|\s)\^{re.escape(part[1:])}[ \t]*$', text) if part.startswith('^')
                 else fold(part) in headings)
        if not part or not found:
            raise ValueError(f'{label} subpath does not exist in {relative}: {subpath}')
    return True


def strict_json(text):
    def unique(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError(f'Duplicate JSON key: {key}')
            data[key] = value
        return data

    def constant(name):
        raise ValueError(f'Non-finite JSON number: {name}')
    try:
        return json.loads(text, object_pairs_hook=unique, parse_constant=constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Canvas is not valid JSON: {exc}') from None


def canvas(settings, text):
    """JSON Canvas 1.0 structure whose file cards resolve inside the library. Read-only."""
    data = strict_json(text)
    if not isinstance(data, dict) or any(not isinstance(data.get(key, []), list) for key in ('nodes', 'edges')):
        raise ValueError('Canvas must be a JSON object whose "nodes" and "edges" are arrays')
    unknown = {key for key in data if key not in ('nodes', 'edges')}
    ids, files, links, unverified, characters, texts = set(), [], [], [], 0, 0

    def identity(item, label):
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']:
            raise ValueError(f'Every canvas {label} is an object with a nonempty string "id"')
        if item['id'] in ids:
            raise ValueError(f'Duplicate canvas id (ids are unique across nodes and edges): {item["id"]}')
        ids.add(item['id'])
        if 'color' in item and not (isinstance(item['color'], str)
                                    and re.fullmatch(r'[1-6]|#[0-9a-fA-F]{6}', item['color'])):
            raise ValueError(f'Canvas {label} {item["id"]}: color is a preset "1" to "6" or a hex such as "#FF0000"')
        return f'Canvas {label} {item["id"]}'

    def text_of(item, key, label, required=False):
        if (required or key in item) and not isinstance(item.get(key), str):
            raise ValueError(f'{label}: "{key}" must be a string')
        return item.get(key)

    for node in data.get('nodes', []):
        label = identity(node, 'node')
        if node.get('type') not in ('text', 'file', 'link', 'group'):
            raise ValueError(f'{label}: type must be text, file, link or group')
        for key in ('x', 'y', 'width', 'height'):
            if type(node.get(key)) is not int:
                raise ValueError(f'{label}: "{key}" must be an integer')
        if node['width'] <= 0 or node['height'] <= 0:
            raise ValueError(f'{label}: width and height must be positive')
        unknown |= set(node) - NODE_KEYS
        if node['type'] == 'text':
            characters += len(text_of(node, 'text', label, True))
            texts += 1
        elif node['type'] == 'file':
            relative = text_of(node, 'file', label, True)
            path = library_file(settings, relative, label + ' file')
            if 'subpath' in node and not check_subpath(settings, relative, path, node['subpath'], label):
                unverified.append(relative + node['subpath'])
            files.append(relative + node.get('subpath', ''))
        elif node['type'] == 'link':
            url = text_of(node, 'url', label, True)
            if not re.fullmatch(r'https?://[^\s<>"\\]+', url):
                raise ValueError(f'{label}: url must be an http or https address')
            links.append(url)
        else:
            text_of(node, 'label', label)
            if text_of(node, 'background', label) is not None:
                library_file(settings, node['background'], label + ' background')
                files.append(node['background'])
            if node.get('backgroundStyle', 'cover') not in ('cover', 'ratio', 'repeat'):
                raise ValueError(f'{label}: backgroundStyle must be cover, ratio or repeat')
    nodes = set(ids)
    for edge in data.get('edges', []):
        label = identity(edge, 'edge')
        for key in ('fromNode', 'toNode'):
            if not isinstance(edge.get(key), str) or edge[key] not in nodes:
                raise ValueError(f'{label}: "{key}" must be the id of a node in this canvas')
        for key, allowed in (('fromSide', SIDES), ('toSide', SIDES), ('fromEnd', ENDS), ('toEnd', ENDS)):
            if key in edge and edge[key] not in allowed:
                raise ValueError(f'{label}: "{key}" must be one of ' + ', '.join(allowed))
        text_of(edge, 'label', label)
        unknown |= set(edge) - EDGE_KEYS
    return {'nodes': len(nodes), 'edges': len(ids) - len(nodes), 'file_cards': sorted(set(files)),
            'unverified_subpaths': sorted(set(unverified)), 'link_urls': sorted(set(links)),
            'text_cards': texts, 'text_characters': characters, 'unknown_keys': sorted(unknown)}


def base(text):
    """YAML with the top-level shape of an Obsidian Base; filters, formulas and view options are not interpreted."""
    def plain(node, seen):
        if id(node) in seen:
            raise ValueError('Base YAML must not use aliases')
        seen.add(id(node))
        if isinstance(node, yaml.MappingNode):
            keys = [key.value if isinstance(key, yaml.ScalarNode) else None for key, _ in node.value]
            if None in keys or len(keys) != len(set(keys)):
                raise ValueError('Base YAML keys must be plain and unique within their mapping')
            for _, value in node.value:
                plain(value, seen)
        elif isinstance(node, yaml.SequenceNode):
            for value in node.value:
                plain(value, seen)
    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
        if not isinstance(node, yaml.MappingNode):
            raise ValueError('Base must be a YAML mapping')
        plain(node, set())
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f'Base is not valid YAML: {" ".join(str(exc).split())}') from None
    shapes = {'filters': (str, dict), 'formulas': dict, 'properties': dict, 'summaries': dict, 'views': list}
    for key, shape in shapes.items():
        if key in data and not isinstance(data[key], shape):
            raise ValueError(f'Base "{key}" has the wrong shape')
    for key in ('formulas', 'summaries'):
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in data.get(key, {}).items()):
            raise ValueError(f'Base "{key}" maps names to expression strings')
    if any(not isinstance(v, dict) for v in data.get('properties', {}).values()):
        raise ValueError('Base "properties" maps each property to its settings')
    for view in data.get('views', []):
        if (not isinstance(view, dict) or not isinstance(view.get('type'), str)
                or not isinstance(view.get('name', ''), str)):
            raise ValueError('Every Base view is a mapping with a string "type" and, when present, a string "name"')
    return {'views': [view.get('name') for view in data.get('views', [])],
            'unknown_keys': sorted(str(key) for key in data if key not in BASE_KEYS)}


def markdown(text):
    """A Markdown file that declares itself a view and nothing that belongs to retained knowledge."""
    metadata = library.knowledge.metadata_from(text)
    if metadata.get('role') != 'view':
        raise ValueError('A Markdown view declares role: view in its frontmatter. A note, map or source is saved '
                         'through its own reviewed writer (library.py proposal and note_write.py, or '
                         'capture_write.py)')
    kept = sorted(key for key in metadata if key in KNOWLEDGE_KEYS)
    if kept:
        raise ValueError('A view declares no ' + ', '.join(kept) + ': those belong to notes and proposals')
    return {'role': 'view', 'evidence_bound': False}


def validate(settings, kind, draft):
    if len(draft) > note_write.LIMIT or not draft.strip():
        raise ValueError(f'View must be nonempty and at most {note_write.LIMIT} bytes')
    text = draft.decode('utf-8')
    facts = canvas(settings, text) if kind == 'canvas' else base(text) if kind == 'base' else markdown(text)
    return {'kind': kind, 'lines': len(text.splitlines()), **facts}


def current_version(path, kind, relative):
    """The existing file's bytes; an existing Markdown file is replaceable only if it is not something else."""
    if not os.path.lexists(path):
        return None
    previous = note_write.read_bytes(path)
    if kind == 'markdown':
        try:
            metadata = library.knowledge.metadata_from(previous.decode('utf-8'))
        except (ValueError, RecursionError):
            metadata = {'role': 'unreadable'}
        if metadata.get('role', 'view') != 'view' or any(key in metadata for key in KNOWLEDGE_KEYS):
            raise ValueError(f'{relative} is not a view: it declares another role or knowledge metadata, or its '
                             'frontmatter cannot be read. This helper replaces only a file that declares role: '
                             'view or declares no role at all')
    return previous


def check(settings, relative, draft):
    relative, path, kind = target(settings, relative)
    facts = validate(settings, kind, draft)
    previous = current_version(path, kind, relative)
    return {'status': 'view_structure_checked_not_saved', 'target': relative, 'exists': previous is not None,
            'current_sha256': None if previous is None else note_write.digest(previous),
            'draft_sha256': note_write.digest(draft), **facts,
            'semantic_validation': False, 'approval_available': False}


def prepare(settings, relative, draft, expected=None, view_id=None):
    """Bind the exact view text and its absent target or current version; never write."""
    capture_write.writable(settings)
    relative, path, kind = target(settings, relative)
    facts = validate(settings, kind, draft)
    previous = current_version(path, kind, relative)
    if previous is None and expected is not None:
        raise ValueError(f'No view at {relative}: a new view takes no --expected-sha256')
    if previous is not None:
        if expected is None:
            raise ValueError(f'View already exists: {relative}. Changing it requires --expected-sha256 of the '
                             'current file; an existing view is never overwritten or deleted without it')
        if note_write.digest(previous) != expected:
            raise ValueError(f'View changed, or this is not the sha256 of the current file: {relative}; '
                             'read it again and show the change again')
        if previous == draft:
            raise ValueError('View already has exactly this text; nothing to change')
    text = draft.decode('utf-8')
    diff = ''.join(difflib.unified_diff((previous or b'').decode('utf-8', 'replace').splitlines(keepends=True),
                                        text.splitlines(keepends=True),
                                        fromfile='/dev/null' if previous is None else relative,
                                        tofile=relative + ' (proposed)'))
    packet = {'format': FORMAT, 'status': 'prepared_not_approved', 'view_id': view_id or uuid.uuid4().hex,
              'operation': 'create' if previous is None else 'replace', 'target': relative, 'draft': text,
              'draft_sha256': note_write.digest(draft), 'base_sha256': expected, 'diff': diff, 'facts': facts,
              'approval_available': False}
    return {**packet, 'packet_sha256': capture_write.canonical(packet)}


def check_packet(settings, packet):
    """Rederive the whole binding from the current library; any difference means review again."""
    if (not isinstance(packet, dict) or packet.get('format') != FORMAT
            or packet.get('status') != 'prepared_not_approved'):
        raise ValueError('Expected an unapplied view packet from view_write.py prepare')
    if packet.get('packet_sha256') != capture_write.canonical({k: v for k, v in packet.items()
                                                               if k != 'packet_sha256'}):
        raise ValueError('Packet content changed')
    if not re.fullmatch(r'[0-9a-f]{32}', str(packet['view_id'])):
        raise ValueError('Invalid view_id')
    if prepare(settings, packet['target'], packet['draft'].encode('utf-8'), packet['base_sha256'],
               packet['view_id']) != packet:
        raise ValueError('View inputs changed since prepare; do not save, review again')


def save(settings, packet):
    """Create a new view no-clobber, or replace the bound version after keeping it in private recovery."""
    check_packet(settings, packet)
    root, recovery = Path(settings['library_root']), Path(settings['recovery_directory'])
    draft, sha256 = packet['draft'].encode('utf-8'), packet['draft_sha256']
    name = 'view-' + packet['view_id']
    record_path, path = recovery / (name + '.json'), root / packet['target']
    replacing = packet['operation'] == 'replace'
    copy = recovery / (name + '.previous' + path.suffix) if replacing else None
    record_created = copied = published = False
    temporary = None
    try:
        try:
            try:
                # Persist provenance BEFORE publishing. One record per packet: a packet is saved once.
                capture_write.write_record(record_path, {
                    'format': 'view-recovery-v1', 'library_root': settings['library_root'],
                    'recorded': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
                    'note': 'Written before publication; not an apply receipt or an approval.',
                    'packet': packet, 'previous_copy': str(copy) if replacing else None,
                    'human_authentication_verified': False})
            except FileExistsError:
                raise ValueError('This packet was already used for a save. A decision covers one write: prepare '
                                 f'again and show the view again ({record_path})') from None
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
            temporary = capture_write.stage(draft, path.parent, sha256, mode)
            check_packet(settings, packet)  # Recording and staging may have exposed changed inputs.
            if replacing:
                os.replace(temporary, path)  # Atomic; the bound previous bytes were verified just above.
            else:
                os.link(temporary, path)  # Atomic absence requirement; never replace a competing entry.
            published = True
            if note_write.read_bytes(path) != draft:
                raise ValueError('Saved view bytes do not match the reviewed text')
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
            raise capture_write.fail('view_not_saved', 'view_partial', exc, recovery, name, record_path,
                                     record_created, left, remaining=left,
                                     previous_copy=str(copy) if copied and left else None) from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'status': 'view_replaced' if replacing else 'view_created', 'view_id': packet['view_id'],
            'target': packet['target'], 'kind': packet['facts']['kind'], 'sha256': sha256,
            'previous_sha256': packet['base_sha256'], 'previous_copy': str(copy) if replacing else None,
            'record': str(record_path), 'semantic_validation': False, 'human_authentication_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    command = sub.add_parser('check', help='validate the view on stdin, or recheck a packet; writes nothing')
    choice = command.add_mutually_exclusive_group(required=True)
    choice.add_argument('--target', help='library-relative .canvas, .base or .md path')
    choice.add_argument('--packet', type=Path)
    command = sub.add_parser('prepare', help='bind the exact view on stdin; writes nothing')
    command.add_argument('--target', required=True, help='library-relative .canvas, .base or .md path')
    command.add_argument('--expected-sha256', help='sha256 of the current file; required to change a view')
    command = sub.add_parser('save')
    command.add_argument('--packet', type=Path, required=True)
    args = parser.parse_args()
    try:
        settings = library.load_config(args.config)
        if args.action == 'prepare':
            result = prepare(settings, args.target, sys.stdin.buffer.read(note_write.LIMIT + 1),
                             args.expected_sha256)
        elif args.packet is None:
            result = check(settings, args.target, sys.stdin.buffer.read(note_write.LIMIT + 1))
        elif args.action == 'check':
            check_packet(settings, note_write.read_json(args.packet))
            result = {'status': 'view_inputs_current', 'human_authentication_verified': False}
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
