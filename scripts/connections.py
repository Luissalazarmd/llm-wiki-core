#!/usr/bin/env python3
"""Versioned, read-only activity and explicit-link measurement. No approval authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import sys
from datetime import datetime

sys.dont_write_bytecode = True
import knowledge

VERSION = 1
FRONT = re.compile(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', re.S)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def visible(text):
    """Mask excluded text while retaining line numbers; a bounded Markdown subset."""
    text = text.replace('\r\n', '\n')
    blank = lambda m: '\n' * m[0].count('\n')
    text = FRONT.sub(blank, text, count=1)
    text = re.sub(r'<!--.*?(?:-->|\Z)|%%.*?(?:%%|\Z)', blank, text, flags=re.S)
    lines, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            lines.append('')
        elif marker:
            fence = marker[1]
            lines.append('')
        elif line.startswith(('    ', '\t')):
            lines.append('')
        else:
            lines.append(line)
    text = '\n'.join(lines)
    return re.sub(r'(?<!`)(`+)(?!`)(.*?)\1(?!`)', blank, text, flags=re.S).splitlines()


def activity(text, properties):
    """Read the existing v1 history without starting, repairing or extending it."""
    data = properties.get('iteration_tracking')
    if 'iteration_tracking' not in properties:
        return {'count': None, 'status': 'unknown'}
    try:
        import yaml
        if not isinstance(data, dict) or set(data) != {'version', 'started_at', 'baseline_sha256', 'events'}:
            raise ValueError()
        if type(data['version']) is not int or data['version'] != 1 or not isinstance(data['events'], list):
            raise ValueError()
        def stamp(value):
            date = datetime.fromisoformat(value)
            if date.tzinfo is None:
                raise ValueError()
            return date
        previous = stamp(data['started_at'])
        expected = data['baseline_sha256']
        ids = set()
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError()
        for event in data['events']:
            if not isinstance(event, dict) or set(event) != {'id', 'at', 'content_sha256', 'via', 'change'}:
                raise ValueError()
            if not isinstance(event['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', event['id']) or event['id'] in ids:
                raise ValueError()
            at = stamp(event['at'])
            if at < previous or event['via'] not in ('host', 'external_observed'):
                raise ValueError()
            value = event['content_sha256']
            if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value) or value == expected:
                raise ValueError()
            if not isinstance(event['change'], str) or not event['change'].strip() or len(event['change']) > 240 or '\n' in event['change'] or '\r' in event['change']:
                raise ValueError()
            ids.add(event['id'])
            previous, expected = at, value
        match = FRONT.match(text)
        node = yaml.compose(match[1], Loader=yaml.SafeLoader)
        if node.flow_style:
            raise ValueError()
        keys = [key for key, _ in node.value]
        index = next(i for i, key in enumerate(keys) if key.value == 'iteration_tracking')
        if any(key.start_mark.column != 0 for key in keys):
            raise ValueError()
        lines = text.splitlines(keepends=True)
        start = keys[index].start_mark.line + 1
        end = keys[index + 1].start_mark.line + 1 if index + 1 < len(keys) else len(match[1].splitlines()) + 1
        if not re.fullmatch(r'iteration_tracking:[ \t]*(?:\r?\n)?', lines[start]):
            raise ValueError()
        payload = ''.join(lines[:start] + lines[end:])
        return {'count': len(data['events']), 'status': 'recorded',
                'unrecorded_changes': digest(payload.encode()) != expected}
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration):
        return {'count': None, 'status': 'invalid'}


def inventory(root, scopes):
    paths = set()
    for scope in sorted(set(scopes)):
        relative = Path(scope)
        if relative.is_absolute() or not relative.parts or relative.parts[0] != 'Wiki' or any(p in ('.', '..') or p.startswith('.') for p in relative.parts):
            raise ValueError('Select explicit Wiki files or folders')
        current = root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise ValueError('Symlink scope rejected')
        if current.is_file() and current.suffix == '.md':
            paths.add(current)
        elif current.is_dir():
            for directory, dirs, files in os.walk(current, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
                for name in dirs + files:
                    if (Path(directory) / name).is_symlink():
                        raise ValueError('Symlink in selection rejected')
                for name in files:
                    path = Path(directory) / name
                    if not name.startswith('.') and path.suffix == '.md':
                        if not path.is_file():
                            raise ValueError('Regular files required')
                        paths.add(path)
                        if len(paths) > 2000:
                            raise ValueError('Selection exceeds 2000 files')
        else:
            raise ValueError('Scope must exist and select Markdown')
        if len(paths) > 2000:
            raise ValueError('Selection exceeds 2000 files')
    return sorted(paths)


def measure(root, scopes):
    root = knowledge.library_root(Path(root))
    if not scopes:
        raise ValueError('Explicit scope required')
    scopes = sorted(set(scopes))
    paths = inventory(root, scopes)
    snapshots, notes, issues = {}, {}, []
    total = 0
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if any(c in relative for c in '[]|#\n\r\\'):
            raise ValueError('Unsafe note path')
        with path.open('rb') as stream:
            raw = stream.read(262145)
        total += len(raw)
        if len(raw) > 262144 or total > 16777216:
            raise ValueError('Selection exceeds byte limits')
        snapshots[relative] = digest(raw)
        text = raw.decode('utf-8')
        properties = knowledge.metadata_from(text)
        if properties.get('role') not in ('note', 'concept'):
            continue
        notes[relative] = {'path': relative, 'activity': activity(text, properties),
                           'incoming': set(), 'outgoing': set(), '_body': visible(text)}
    for source, note in notes.items():
        for number, line in enumerate(note['_body'], 1):
            for match in re.finditer(r'(?<!!)(?<!\\)\[\[([^\[\]\n]+)\]\]|(?<!!)(?<!\\)\[[^\]\n]*\]\(([^\s)]+)\)', line):
                target = match[1].split('|', 1)[0] if match[1] else match[2]
                target = target.split('#', 1)[0]
                if not target:
                    continue  # Same-file section.
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                    continue
                reason = None
                if '%' in target or '\\' in target or target.startswith('/'):
                    reason = 'unsupported_target'
                elif '/' not in target:
                    reason = 'explicit_path_required'
                else:
                    if target.startswith(('./', '../')):
                        target = posixpath.normpath(posixpath.join(posixpath.dirname(source), target))
                    if not target.endswith('.md'):
                        target += '.md'
                    if target == source:
                        continue
                    if target in notes:
                        note['outgoing'].add(target)
                        notes[target]['incoming'].add(source)
                    else:
                        reason = 'excluded_role' if target in snapshots else 'outside_selection_or_unresolved'
                if reason:
                    issues.append({'path': source, 'line': number, 'target': target, 'reason': reason})
        del note['_body']
    # Cooperative drift check, not an atomic snapshot or a writer lock.
    if inventory(root, scopes) != paths:
        raise ValueError('Selection changed during calculation; discard result')
    for relative, expected in snapshots.items():
        path = root / relative
        with path.open('rb') as stream:
            current = stream.read(262145)
        if path.is_symlink() or digest(current) != expected:
            raise ValueError('Input changed during calculation; discard result')
    for note in notes.values():
        note['neighbors'] = sorted(note['incoming'] | note['outgoing'])
        note['incoming'] = sorted(note['incoming'])
        note['outgoing'] = sorted(note['outgoing'])
        note['counts'] = {key: len(note[key]) for key in ('incoming', 'outgoing', 'neighbors')}
    return {'algorithm': 'explicit-note-connections', 'version': VERSION, 'scope': scopes,
            'coverage': 'within_selection', 'inputs': snapshots, 'notes': list(notes.values()),
            'issues': sorted(issues, key=lambda item: (item['path'], item['line'], item['target'], item['reason']))}


def markdown(data, order='connections'):
    labels = lambda paths: ', '.join('[[' + p[:-3] + ']]' for p in paths) or '—'
    key = (lambda n: (-n['counts']['neighbors'], n['path'])) if order == 'connections' else (lambda n: (-(n['activity']['count'] if n['activity']['count'] is not None else -1), n['path']))
    lines = ['# Trabajo y conexiones', '',
             'Vista derivada; conexiones dentro de la selección. No mide calidad, madurez ni aceptación.', '',
             'Reglas: v' + str(data['version']) + '. Selección: ' + ', '.join(data['scope']) + '.',
             'Instantánea: `' + digest(json.dumps(data['inputs'], sort_keys=True).encode()) + '`.', '', '## Resumen', '',
             '| Nota | Iteraciones | Entrantes | Salientes | Conexiones únicas |',
             '|---|---:|---:|---:|---:|']
    for note in sorted(data['notes'], key=key):
        a, c = note['activity'], note['counts']
        count = str(a['count']) if a['count'] is not None else ('Historial inválido' if a['status'] == 'invalid' else 'Sin seguimiento')
        if a.get('unrecorded_changes'):
            count += ' (cambios sin registrar)'
        lines.append(f"| {labels([note['path']])} | {count} | {c['incoming']} | {c['outgoing']} | {c['neighbors']} |")
    lines += ['', '## Notas detrás de los números', '']
    for note in data['notes']:
        lines += [labels([note['path']]), '', 'Entrantes: ' + labels(note['incoming']), '', 'Salientes: ' + labels(note['outgoing']), '']
    lines += ['## Cobertura y exclusiones', '', f"{len(data['issues'])} enlaces excluidos o pendientes de resolución.", '']
    reasons = {'excluded_role': 'Mapa u otro rol excluido',
               'outside_selection_or_unresolved': 'Fuera de la selección o sin resolver',
               'explicit_path_required': 'Requiere ruta explícita',
               'unsupported_target': 'Formato de destino no admitido'}
    for issue in data['issues']:
        target = issue['target'].replace('`', '').replace('<', '&lt;').replace('>', '&gt;')
        lines.append(f"- {labels([issue['path']])}, línea {issue['line']}: {reasons[issue['reason']]} — `{target}`.")
    lines += ['', 'Las iteraciones son historia registrada; las conexiones son el estado de esta selección.',
              'Actualización explícita; esta vista guardada no se refresca por sí sola.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--scope', action='append', required=True)
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    parser.add_argument('--sort', choices=('connections', 'iterations'), default='connections')
    args = parser.parse_args()
    try:
        result = measure(args.root, args.scope)
        print(markdown(result, args.sort) if args.format == 'markdown' else json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
