#!/usr/bin/env python3
"""Prepare only the bundled synthetic Obsidian example; never deploy a library."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import knowledge

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples' / 'obsidian'


def reading_view(identity: str) -> str:
    """Resolve fixture IDs using the original projector, without changing notes."""
    selected = knowledge.focus(knowledge.catalog(EXAMPLE), identity)
    selected['notes'] = [{**note, 'path': 'examples/obsidian/' + note['path']}
                         for note in selected['notes']]
    return knowledge.markdown(selected, typed_navigation=True)


def materialize(destination: Path, identity: str = 'demo:idea:synthesis') -> Path:
    """Create an explicit new synthetic workbench, never overlay an existing vault."""
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination exists; preserve it and choose a new path')
    if any(parent.is_symlink() for parent in destination.parents):
        raise ValueError('Symlink destination ancestor rejected')
    destination = destination.resolve()
    if destination.is_relative_to(ROOT) or not destination.parent.is_dir():
        raise ValueError('Destination must be outside Core with an existing parent')
    patterns = ('README.md', 'AGENTS.md', 'Librarian Profile.md', 'requirements.txt',
                'docs/**/*.md', 'Agents/**/*.md', 'skills/**/SKILL.md',
                'scripts/*.py', 'tests/*.py', 'config/ontology.json',
                'config/personal.example.json', 'examples/obsidian/**/*')
    sources = set()
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            relative = path.relative_to(ROOT)
            if any(part.startswith('.') for part in relative.parts):
                continue
            if path.is_symlink() or any(p.is_symlink() for p in path.parents if p.is_relative_to(ROOT)):
                raise ValueError('Symlink example input rejected')
            if path.is_file():
                sources.add(path)
    view = reading_view(identity)
    destination.mkdir(mode=0o700)
    for source in sorted(sources):
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    navigation = destination / 'examples/obsidian/Navigation/Lectura.md'
    navigation.parent.mkdir(parents=True, exist_ok=True)
    navigation.write_text(view, encoding='utf-8')
    settings = destination / '.obsidian'
    settings.mkdir()
    (settings / 'app.json').write_text(json.dumps({'showInlineTitle': False,
                                                 'propertiesInDocument': 'hidden'}))
    (settings / 'core-plugins.json').write_text(json.dumps({name: True for name in
        ('file-explorer', 'global-search', 'switcher', 'graph', 'backlink', 'canvas',
         'outgoing-link', 'properties', 'command-palette', 'page-preview', 'outline', 'bases')}))
    (settings / 'appearance.json').write_text(json.dumps({'theme': 'obsidian',
                                                         'enabledCssSnippets': ['core-home']}))
    css = EXAMPLE / 'core-home.css'
    if css.is_file():
        (settings / 'snippets').mkdir()
        shutil.copy2(css, settings / 'snippets/core-home.css')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--focus', default='demo:idea:synthesis')
    parser.add_argument('--output', type=Path, help='explicit absent directory outside Core')
    args = parser.parse_args()
    try:
        if args.output:
            print(json.dumps({'workbench': str(materialize(args.output, args.focus)),
                              'home': 'examples/obsidian/Home.md',
                              'synthetic': True, 'plugins_installed': False}))
        else:
            print(reading_view(args.focus), end='')
    except (ValueError, OSError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        raise SystemExit(2)
