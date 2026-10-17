"""Structural acceptance of the synthetic candidate, not K-Plex integration."""
from pathlib import Path
import json
import importlib.util
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/kplex-minimal'


class MinimalKplexTests(unittest.TestCase):
    def setUp(self):
        self.notes = {}
        for folder in ('Raw', 'Wiki'):
            for path in (FIXTURE / folder).glob('*.md'):
                text = path.read_text()
                self.notes[path] = (yaml.safe_load(text.split('---', 2)[1]), text)

    def test_runtime_reads_the_native_fixture_without_a_generated_view(self):
        spec = importlib.util.spec_from_file_location('minimal_reader', ROOT / 'scripts/knowledge.py')
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        before = {p: p.read_bytes() for p in self.notes}
        data = api.catalog(FIXTURE, link_prefix='examples/kplex-minimal')
        self.assertCountEqual([e['kind'] for e in data['edges']],
                              ['supported_by', 'supported_by', 'contradicts', 'groups', 'groups'])
        selected = api.focus(data, 'path:Wiki/Explicacion.md')
        self.assertEqual(len(selected['notes']), 4)
        self.assertFalse(data['approval_available'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.notes})

    def test_roles_and_unknown_maturity_remain_distinct(self):
        self.assertEqual(len(self.notes), 4)
        roles = [meta['role'] for meta, _ in self.notes.values()]
        self.assertCountEqual(roles, ['source', 'note', 'note', 'map'])
        maturities = []
        for meta, _ in self.notes.values():
            self.assertNotIn('relations', meta)
            self.assertNotIn('review', meta)
            if meta['role'] == 'note':
                maturities.append(meta.get('maturity', 'unknown'))
            else:
                self.assertNotIn('maturity', meta)
        self.assertCountEqual(maturities, ['synthesis', 'unknown'])

    def test_every_wikilink_and_exact_heading_resolves_within_fixture(self):
        links = []
        for _, text in self.notes.values():
            links.extend(re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', text))
        self.assertEqual(len(links), 5)
        for link in links:
            target, _, heading = link.partition('#')
            path = ROOT / (target + '.md')
            self.assertIn(path, self.notes, link)
            if heading:
                headings = re.findall(r'^#{1,6} (.+)$', self.notes[path][1], re.M)
                self.assertIn(heading, headings, link)

    def test_single_declarations_cover_map_evidence_and_tension(self):
        settings = json.loads((FIXTURE / 'kplex.example.json').read_text())
        hierarchy = settings['hierarchy']
        self.assertIn('up', hierarchy['parents'])
        self.assertIn('Evidence', hierarchy['leftFriends'])
        self.assertIn('Contrasts', hierarchy['rightFriends'])
        edges = []
        for path, (meta, text) in self.notes.items():
            if 'up' in meta:
                edges.append((path, 'up', meta['up']))
            for kind, target in re.findall(r'^(Evidence|Contrasts):: (.+)$', text, re.M):
                edges.append((path, kind, target))
        self.assertCountEqual([kind for _, kind, _ in edges],
                              ['up', 'up', 'Evidence', 'Evidence', 'Contrasts'])
        pairs = set()
        for path, kind, target in edges:
            target_path = ROOT / (target[2:-2].split('#')[0] + '.md')
            role = self.notes[target_path][0]['role']
            self.assertEqual(role, {'up': 'map', 'Evidence': 'source', 'Contrasts': 'note'}[kind])
            pair = frozenset((path, target_path))
            self.assertNotIn(pair, pairs, 'Duplicate or reciprocal declaration')
            pairs.add(pair)


if __name__ == '__main__':
    unittest.main()
