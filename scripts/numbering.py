"""Bounded, file-derived numbering for the optional living-synthesis profile."""
import hashlib
import json
import re
from pathlib import Path

import knowledge
import library

LIMIT = 262144
BATCH = 'living-synthesis-batch-v1'


def in_scope(settings, target):
    profile = settings.get('living_synthesis')
    if not profile:
        return False
    root = Path(settings['library_root'])
    path = root / target
    return any(path == root / scope or path.is_relative_to(root / scope) for scope in profile['scopes'])


def read(path):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Numbering scope file exceeds byte limit')
    return raw


def snapshot(settings):
    root = Path(settings['library_root'])
    entries = library.inventory(root, settings['living_synthesis']['scopes'])
    files, metadata, total = {}, {}, 0
    for path in entries:
        if path.is_file():
            raw = read(path)
            total += len(raw)
            if total > 8 * 1024 * 1024:
                raise ValueError('Numbering scope exceeds byte limit')
            name = path.relative_to(root).as_posix()
            files[name] = hashlib.sha256(raw).hexdigest()
            if path.suffix == '.md':
                metadata[name] = knowledge.metadata_from(raw.decode('utf-8'))
    members = [p.relative_to(root).as_posix() + ('/' if p.is_dir() else '') for p in entries]
    return {'settings': settings, 'members': members, 'files': files}, metadata


def validate(metadata):
    ids, addresses, maps, notes = {}, {}, {}, []
    for path, data in metadata.items():
        identity = data.get('id')
        if identity is not None:
            if not isinstance(identity, str) or not identity.strip() or identity in ids:
                raise ValueError('Invalid or duplicate stable ID')
            ids[identity] = path
        role, kind = data.get('role'), data.get('map_kind')
        if role in ('note', 'map') and not identity:
            raise ValueError('Notes and maps require an explicit stable ID')
        if role != 'note' and 'maturity' in data:
            raise ValueError('Maturity is only valid for notes')
        if role == 'note' and data.get('maturity') not in ('seed', 'synthesis', 'developing', 'evergreen'):
            raise ValueError('Invalid note maturity')
        address, history = data.get('address'), data.get('former_addresses', [])
        if not isinstance(history, list) or any(not isinstance(v, str) for v in history):
            raise ValueError('Invalid former address history')
        if role == 'map' and kind == 'thematic':
            pattern = r'[0-9]{3}'
            if not isinstance(address, str) or not re.fullmatch(pattern, address) or address == '000':
                raise ValueError('Thematic MOC requires stable ID and three-digit address')
            maps[path] = address
        elif role == 'note' and data.get('maturity') != 'seed':
            pattern = r'[0-9]{3}-[0-9]{2}'
            if not isinstance(data.get('primary_moc'), str) or not data['primary_moc']:
                raise ValueError('Synthesis requires ID, maturity and primary MOC')
            if not isinstance(address, str) or not re.fullmatch(pattern, address) or address.endswith('-00'):
                raise ValueError('Synthesis requires a valid address')
            notes.append(data)
        else:
            if address is not None or history:
                raise ValueError('Seeds and non-thematic objects cannot have addresses')
            continue
        if 'former_addresses' not in data:
            raise ValueError('Allocated objects require explicit former address history')
        for item in [address, *history]:
            if not re.fullmatch(pattern, item) or item.startswith('000') or item.endswith('-00'):
                raise ValueError('Invalid reserved address')
            if item in addresses:
                raise ValueError('Duplicate address reservation')
            addresses[item] = path
    for data in notes:
        moc = data['primary_moc']
        if moc not in maps or not data['address'].startswith(maps[moc] + '-'):
            raise ValueError('Primary MOC missing, non-thematic or inconsistent with address')
    map_nums = sorted(int(a) for a in addresses if len(a) == 3)
    if map_nums != list(range(1, len(map_nums) + 1)):
        raise ValueError('Incomplete or gapped MOC reservations')
    for prefix in {a[:3] for a in addresses if len(a) > 3}:
        if prefix not in addresses:
            raise ValueError('Synthesis reservation has no MOC reservation')
        numbers = sorted(int(a[4:]) for a in addresses if a.startswith(prefix + '-'))
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError('Incomplete or gapped synthesis reservations')
    return maps, addresses


def set_field(text, key, value):
    """Replace just one YAML value, retaining unrelated metadata and the exact body."""
    knowledge.metadata_from(text)  # Reject duplicate/aliased/ambiguous YAML first.
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        raise ValueError('Explicit frontmatter is required')
    header = match[1]
    node = knowledge.yaml.compose(header, Loader=knowledge.yaml.SafeLoader)
    encoded = json.dumps(value, ensure_ascii=False)
    for name, current in node.value:
        if name.value == key:
            header = header[:name.start_mark.index] + key + ': ' + encoded + header[current.end_mark.index:]
            break
    else:
        newline = '\r\n' if text.startswith('---\r\n') else '\n'
        header += newline + key + ': ' + encoded
    result = text[:match.start(1)] + header + text[match.end(1):]
    knowledge.metadata_from(result)
    return result


def next_address(reservations, prefix=''):
    width = 2 if prefix else 3
    numbers = [int(a[len(prefix):]) for a in reservations
               if a.startswith(prefix) and len(a) == len(prefix) + width]
    number = max(numbers, default=0) + 1
    if number > (99 if prefix else 999):
        raise ValueError('Address sequence exhausted')
    return prefix + format(number, '02' if prefix else '03')


def reconcile_references(settings, changes, moved):
    """Stable paths avoid renames; only explicit vault-path wikilinks are supported."""
    if not moved:
        return
    if settings['living_synthesis'].get('references_complete') is not True:
        raise ValueError('Primary moves require an explicitly complete reference scope')
    _, metadata = snapshot(settings)
    root = Path(settings['library_root'])
    texts = {p: read(root / p).decode('utf-8') for p in metadata}
    texts.update({p: change['draft'] for p, change in changes.items()})
    paths = {p: {'id': p} for p in texts}
    bodies = {p: knowledge.visible_body(text) for p, text in texts.items()}
    for text in texts.values():
        body = '\n'.join(knowledge.visible_body(text))
        for link in re.findall(r'\[\[[^\]\n]+\]\]', body):
            target = link[2:-2].split('|', 1)[0].split('#', 1)[0]
            for path in moved:
                if target in (path, path[:-3]):
                    knowledge.resolve_native_link(link, paths, bodies, '')
                elif target in (Path(path).stem, Path(path).name) or target.startswith(('./', '../')):
                    raise ValueError('Move requires explicit vault-path references; reconcile unsupported links')
        for path in moved:
            if re.search(r'\]\([^\n)]*' + re.escape(Path(path).stem), body):
                raise ValueError('Move requires explicit wikilinks; reconcile Markdown references first')


def plan(settings, entries):
    """Compute one complete postimage; preparation and validation share this allocator."""
    if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
        raise ValueError('Numbered candidates require 1 to 20 changes')
    if not settings.get('living_synthesis'):
        raise ValueError('Numbered candidates require an optional living-synthesis profile')
    binding, existing = snapshot(settings)
    maps, reservations = validate(existing)
    changes, moved, new_maps = {}, set(), set()
    root = Path(settings['library_root'])
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) - {'target', 'draft', 'create', 'move_primary'}
                or not isinstance(entry.get('target'), str) or not isinstance(entry.get('draft'), str)
                or type(entry.get('create', False)) is not bool or type(entry.get('move_primary', False)) is not bool):
            raise ValueError('Invalid numbered candidate entry')
        target = entry['target']
        library.authorize(root, settings['authorized_paths'], target, create=entry.get('create', False))
        if not in_scope(settings, target) or target in changes:
            raise ValueError('Numbered candidate target is duplicate or outside profile scope')
        changes[target] = {**entry, 'create': entry.get('create', False), 'move_primary': entry.get('move_primary', False)}
    # MOCs are assigned before notes, preserving caller order within each category.
    ordered = sorted(changes, key=lambda p: knowledge.metadata_from(changes[p]['draft']).get('role') != 'map')
    for target in ordered:
        change = changes[target]
        data = knowledge.metadata_from(change['draft'])
        old = existing.get(target) if not change['create'] else None
        is_move = old is not None and old.get('primary_moc') != data.get('primary_moc') and bool(old.get('address'))
        if change['move_primary'] != is_move:
            raise ValueError('Primary association change requires an explicit primary move')
        if old is not None:
            protected = ('id', 'author', 'authors', 'role', 'map_kind')
            if not is_move:
                protected += ('address', 'primary_moc', 'former_addresses')
            if any(k in old and data.get(k) != old[k] for k in protected):
                raise ValueError('Identity, authorship, address, primary association or history changed')
            if old.get('address') and data.get('maturity') == 'seed':
                raise ValueError('Cannot release an allocated address')
        thematic = data.get('role') == 'map' and data.get('map_kind') == 'thematic'
        synthesis = data.get('role') == 'note' and data.get('maturity') != 'seed'
        allocate = (old is None or not old.get('address')) and (thematic or synthesis)
        if allocate or is_move:
            if thematic:
                desired = next_address(reservations)
                new_maps.add(target)
            else:
                moc = data.get('primary_moc')
                if not isinstance(moc, str) or moc not in maps:
                    raise ValueError('Primary MOC must be an existing thematic map in scope')
                desired = next_address(reservations, maps[moc] + '-')
            if is_move and old is not None:
                if (old['id'] == old['address'] or Path(target).stem.startswith(old['address'])):
                    raise ValueError('Address-based identity or filename cannot be recoded without a permitted rename')
                history = [*old.get('former_addresses', []), old['address']]
                if data.get('former_addresses') not in (old.get('former_addresses', []), history):
                    raise ValueError('Primary move must preserve all former reservations')
                if data.get('address') not in (old['address'], desired, '', None):
                    raise ValueError('Primary move address is not the next destination reservation')
                change['draft'] = set_field(change['draft'], 'former_addresses', history)
                moved.add(target)
            elif data.get('address') not in ('', None, desired) or data.get('former_addresses', []):
                raise ValueError('New address is not the next available reservation')
            change['draft'] = set_field(change['draft'], 'address', desired)
            if 'former_addresses' not in knowledge.metadata_from(change['draft']):
                change['draft'] = set_field(change['draft'], 'former_addresses', [])
            reservations[desired] = target
        data = knowledge.metadata_from(change['draft'])
        if thematic:
            maps[target] = data.get('address')
    proposed = {**existing, **{p: knowledge.metadata_from(c['draft']) for p, c in changes.items()}}
    validate(proposed)
    for moc in new_maps:
        if not any(d.get('primary_moc') == moc and d.get('address') for d in proposed.values()):
            raise ValueError('New thematic MOC must be proposed with a retained synthesis')
    # Propose destination reading links as visible companion edits, never hidden writes.
    for target in [p for p in changes if p in moved or changes[p]['create']]:
        data = proposed[target]
        if not data.get('primary_moc') or not data.get('address'):
            continue
        moc = data['primary_moc']
        if moc not in changes and target not in moved:
            continue  # Existing-MOC single-file preparation retains its original shape.
        if moc not in changes:
            changes[moc] = {'target': moc, 'draft': read(root / moc).decode('utf-8'), 'create': False, 'move_primary': False}
        link = '[[' + target[:-3] + ']]'
        if not re.search(r'\[\[' + re.escape(target[:-3]) + r'(?:\.md)?(?:[#|]|\]\])', changes[moc]['draft']):
            changes[moc]['draft'] += '\n- ' + link + '\n'
    if len(changes) > 20:
        raise ValueError('Numbered candidate including map companions exceeds 20 changes')
    reconcile_references(settings, changes, moved)
    ordered = sorted(changes, key=lambda p: knowledge.metadata_from(changes[p]['draft']).get('role') != 'map')
    return [changes[p] for p in ordered], binding


def candidate(settings, target, draft, create):
    changes, binding = plan(settings, [{'target': target, 'draft': draft, 'create': create}])
    return changes[0]['draft'], binding


def seal(packet):
    packet.pop('packet_sha256', None)
    packet['packet_sha256'] = hashlib.sha256(json.dumps(packet, sort_keys=True, ensure_ascii=False,
                                                        separators=(',', ':')).encode()).hexdigest()


def bind_packet(packet, binding):
    packet['living_synthesis'] = binding
    seal(packet)


def prepare_batch(settings, entries, evidence):
    changes, binding = plan(settings, entries)
    if set(evidence) & {c['target'] for c in changes}:
        raise ValueError('Batch evidence must not also be a changed target')
    proposals = []
    for change in changes:
        packet = knowledge.prepare_proposal(Path(settings['library_root']), change['target'], change['draft'], evidence, change['create'])
        bind_packet(packet, binding)
        proposals.append(packet)
    result = {'format': BATCH, 'status': 'prepared_not_approved', 'approval_available': False,
              'human_authentication_verified': False, 'proposals': proposals,
              'moves': [c['target'] for c in changes if c['move_primary']], 'living_synthesis': binding}
    seal(result)
    if len(json.dumps(result, ensure_ascii=False, indent=2).encode()) + 1 > 2097152:
        raise ValueError('Numbered packet exceeds byte limit; narrow the candidate')
    return result


def check(settings, packet):
    target, binding = packet['target']['path'], packet.get('living_synthesis')
    if not in_scope(settings, target):
        if binding is not None:
            raise ValueError('Numbering profile or scope changed')
        return
    if binding is None:
        raise ValueError('Numbered scope requires a bound numbering proposal')
    current, _ = snapshot(settings)
    if current != binding:
        raise ValueError('Numbering scope or configuration changed; review again')
    draft, _ = candidate(settings, target, packet['draft'], packet['target'].get('operation') == 'create')
    if draft != packet['draft']:
        raise ValueError('Numbered candidate changed; review again')


def check_batch(settings, packet):
    if not settings.get('living_synthesis'):
        raise ValueError('Numbering profile or scope changed')
    current, _ = snapshot(settings)
    if packet.get('living_synthesis') != current:
        raise ValueError('Numbering scope or configuration changed; review again')
    proposals = packet.get('proposals')
    moves = packet.get('moves')
    if not isinstance(proposals, list) or not isinstance(moves, list):
        raise ValueError('Invalid numbered batch')
    entries = [{'target': p['target']['path'], 'draft': p['draft'],
                'create': p['target'].get('operation') == 'create', 'move_primary': p['target']['path'] in moves}
               for p in proposals]
    changes, _ = plan(settings, entries)
    if ([c['target'] for c in changes] != [e['target'] for e in entries]
            or any(c['draft'] != e['draft'] for c, e in zip(changes, entries, strict=True))
            or set(moves) != {c['target'] for c in changes if c['move_primary']}
            or any(p.get('living_synthesis') != current for p in proposals)):
        raise ValueError('Numbered batch candidate changed; review again')


def after_save(binding, packet):
    """Expected snapshot advances only by this batch's own exact saved bytes."""
    path = packet['target']['path']
    return {**binding, 'members': sorted(set(binding['members']) | {path}, key=lambda p: Path(p.rstrip('/'))),
            'files': {**binding['files'], path: packet['draft_sha256']}}


def check_restore(settings, target, current, previous):
    if not in_scope(settings, target):
        return
    before = knowledge.metadata_from(current.decode('utf-8'))
    after = knowledge.metadata_from(previous.decode('utf-8'))
    for key in ('id', 'address', 'primary_moc', 'former_addresses'):
        if key in before and before[key] != after.get(key):
            raise ValueError('Restore would release or replace identity, address, primary association or history')
    _, metadata = snapshot(settings)
    validate(metadata)
    metadata[target] = after
    validate(metadata)
    if settings['living_synthesis'].get('references_complete'):
        reconcile_references(settings, {target: {'draft': previous.decode('utf-8')}}, {target})
