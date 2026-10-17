"""Original optional Obsidian example checks; no private library input."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples' / 'obsidian'


class ObsidianExampleTests(unittest.TestCase):
    def demo_api(self):
        path = ROOT / 'scripts/obsidian_demo.py'
        self.assertTrue(path.is_file(), 'Synthetic workbench helper is missing')
        spec = importlib.util.spec_from_file_location('obsidian_demo', path)
        assert spec is not None and spec.loader is not None
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        return api

    def test_entry_is_native_navigable_and_not_a_static_inventory(self):
        home = EXAMPLE / 'Home.md'
        self.assertTrue(home.is_file(), 'Native Home is missing')
        text = home.read_text()
        self.assertIn('Biblioteca.base#Panorama', text)
        self.assertIn('Arquitectura.canvas', text)
        self.assertIn('K-Plex', text)
        self.assertIn('datos ficticios', text.lower())
        self.assertNotRegex(text, r'Capturas:\s*\*?\d+')

    def test_native_base_separates_scope_category_and_idea_maturity(self):
        path = EXAMPLE / 'Biblioteca.base'
        self.assertTrue(path.is_file(), 'Native Base is missing')
        base = yaml.safe_load(path.read_text())
        names = {view['name']: view for view in base['views']}
        self.assertTrue({'Panorama', 'Atencion', 'Recientes', 'Madurez',
                         'Capturas', 'Inventario', 'Incorporaciones'} <= names.keys())
        self.assertIn('examples/obsidian/Review/Inbox', base['formulas']['categoria'])
        self.assertEqual(names['Panorama']['summaries']['formula.unidad'], 'Sum')
        self.assertNotIn('limit', names['Panorama'])
        self.assertEqual(names['Recientes']['limit'], 5)
        self.assertIn('formula.categoria == "Conceptos"', str(names['Madurez']['filters']))
        self.assertIn('Desconocida', base['formulas']['madurez'])
        self.assertIn('Conflicto', base['formulas']['fecha_estado'])

    def test_attention_is_complete_and_not_a_queue_of_retained_stale_notes(self):
        base = yaml.safe_load((EXAMPLE / 'Biblioteca.base').read_text())
        view = next(v for v in base['views'] if v['name'] == 'Atencion')
        self.assertNotIn('limit', view)
        self.assertIn('Review/Inbox', str(view['filters']))
        self.assertNotIn('file.mtime', str(view['sort']))
        self.assertIn('accepted', str(view['filters']))

    def test_collection_formulas_do_not_confuse_capture_custody_with_idea_development(self):
        formulas = yaml.safe_load((EXAMPLE / 'Biblioteca.base').read_text())['formulas']
        self.assertNotIn('Sources") && role', formulas['categoria'])
        self.assertIn('Mapas e índices', formulas['categoria'])
        self.assertIn('project', formulas['categoria'])
        self.assertIn('diagram', formulas['categoria'])
        self.assertIn('formula.categoria != "Conceptos"', formulas['madurez'])
        self.assertNotIn('Desactualizada', formulas['revision'])

    def test_synthetic_custody_and_orthogonal_states_have_exact_partitions(self):
        files = sorted((EXAMPLE / 'Raw').rglob('*.md')) + sorted((EXAMPLE / 'Wiki').rglob('*.md'))
        self.assertTrue(files, 'Synthetic notes are missing')
        spec = importlib.util.spec_from_file_location('example_knowledge', ROOT / 'scripts/knowledge.py')
        assert spec is not None and spec.loader is not None
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        data = api.catalog(EXAMPLE)
        self.assertEqual(Counter(n['role'] for n in data['notes']),
                         {'source': 2, 'note': 5, 'map': 2})
        concepts = [n for n in data['notes'] if n['role'] == 'note']
        self.assertEqual(Counter(n['maturity'] for n in concepts),
                         {'seed': 2, 'synthesis': 1, 'evergreen': 1, 'unknown': 1})
        self.assertTrue(any(n['maturity'] == 'seed' and n['declared_review'] == 'accepted' for n in concepts))
        self.assertTrue(any(n['maturity'] == 'evergreen' and n['declared_review'] == 'stale' for n in concepts))
        self.assertTrue(all(not n['approval_available'] for n in data['notes']))
        proposals = list((EXAMPLE / 'Review/Inbox').glob('*.md'))
        self.assertEqual(len(proposals), 2)
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})

    def test_proposals_have_distinct_identities_and_resolve_retained_targets(self):
        api = self.demo_api().knowledge
        identities = {}
        for stage in ('Raw', 'Wiki', 'Review'):
            for path in (EXAMPLE / stage).rglob('*.md'):
                metadata = api.metadata_from(path.read_text())
                identity = metadata['id']
                self.assertNotIn(identity, identities,
                                 f'{path} reuses the identity of {identities.get(identity)}')
                identities[identity] = path
                if stage == 'Review':
                    target = EXAMPLE / metadata['proposed_target']
                    self.assertTrue(target.is_file())
                    self.assertTrue(target.is_relative_to(EXAMPLE / 'Wiki'))
                    self.assertNotEqual(identity, api.metadata_from(target.read_text())['id'])
        self.assertEqual(len(identities), 11)

    def test_canvas_has_six_contained_groups_and_resolving_file_cards(self):
        path = EXAMPLE / 'Arquitectura.canvas'
        self.assertTrue(path.is_file(), 'Architecture Canvas is missing')
        canvas = json.loads(path.read_text())
        nodes = {n['id']: n for n in canvas['nodes']}
        self.assertEqual(len(nodes), len(canvas['nodes']))
        groups = [n for n in nodes.values() if n['type'] == 'group']
        self.assertEqual(len(groups), 6)
        for node in nodes.values():
            for key in ('x', 'y', 'width', 'height'):
                self.assertIsInstance(node[key], int)
            if node['type'] != 'group':
                self.assertTrue(any(g['x'] <= node['x'] and g['y'] <= node['y'] and
                                    node['x'] + node['width'] <= g['x'] + g['width'] and
                                    node['y'] + node['height'] <= g['y'] + g['height'] for g in groups))
            if node['type'] == 'file':
                target = ROOT / node['file']
                self.assertTrue(target.is_file(), node['file'])
                if node.get('subpath'):
                    self.assertIn(node['subpath'][1:], target.read_text(), node['subpath'])
        edges = canvas['edges']
        self.assertEqual(len({e['id'] for e in edges}), len(edges))
        for edge in edges:
            self.assertIn(edge['fromNode'], nodes)
            self.assertIn(edge['toNode'], nodes)
            self.assertTrue(edge.get('label'))

    def test_id_projection_has_explicit_paths_and_preserves_original_bytes(self):
        api = self.demo_api()
        paths = list((EXAMPLE / 'Raw').rglob('*.md')) + list((EXAMPLE / 'Wiki').rglob('*.md'))
        before = {p: p.read_bytes() for p in paths}
        text = api.reading_view('demo:idea:synthesis')
        self.assertIn('[[examples/obsidian/Raw/Sources/Informe-A]]', text)
        self.assertIn('supported_by', text)
        self.assertIn('extends', text)
        self.assertIn('Evidence:', text)
        self.assertEqual(before, {p: p.read_bytes() for p in paths})

    def test_demo_projects_typed_fields_instead_of_children_for_all_neighbors(self):
        api = self.demo_api()
        view = api.knowledge.metadata_from(api.reading_view('demo:idea:synthesis'))
        self.assertNotIn('Children', view)
        self.assertEqual(view['Evidence'], ['[[examples/obsidian/Raw/Sources/Informe-A]]'])
        self.assertEqual(view['BuildsOn'], ['[[examples/obsidian/Wiki/Concepts/Pregunta]]'])
        self.assertEqual(view['Parent'], ['[[examples/obsidian/Wiki/Maps/Sombras]]'])

    def test_materialization_is_new_only_and_excludes_private_or_third_party_state(self):
        api = self.demo_api()
        self.assertTrue(callable(getattr(api, 'materialize', None)), 'Materializer is missing')
        with tempfile.TemporaryDirectory(prefix='core-obsidian-test-') as directory:
            target = Path(directory) / 'demo'
            api.materialize(target)
            self.assertTrue((target / 'examples/obsidian/Home.md').is_file())
            self.assertTrue((target / 'examples/obsidian/Navigation/Lectura.md').is_file())
            self.assertTrue((target / 'docs/architecture.md').is_file())
            self.assertFalse((target / '.git').exists())
            self.assertFalse((target / '.obsidian/plugins').exists())
            before = (target / 'examples/obsidian/Home.md').read_bytes()
            with self.assertRaisesRegex(ValueError, 'exists'):
                api.materialize(target)
            self.assertEqual(before, (target / 'examples/obsidian/Home.md').read_bytes())

    def test_materialization_refuses_symlink_ancestors_and_source_tree_destinations(self):
        api = self.demo_api()
        with tempfile.TemporaryDirectory(prefix='core-obsidian-safety-') as directory:
            parent = Path(directory)
            real = parent / 'real'
            real.mkdir()
            linked = parent / 'linked'
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                api.materialize(linked / 'new')
            self.assertEqual(list(real.iterdir()), [])
        with self.assertRaisesRegex(ValueError, 'outside Core'):
            api.materialize(EXAMPLE / 'must-not-be-created')
        disguised = ROOT.parent / '..' / ROOT.parent.name / ROOT.name / 'must-not-be-created'
        with self.assertRaisesRegex(ValueError, 'outside Core'):
            api.materialize(disguised)

    def test_unknown_focus_cli_fails_without_publishing_a_view(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/obsidian_demo.py'),
                                 '--focus', 'not-a-fixture-id'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertIn('Unknown focus', json.loads(result.stderr)['error'])

    def test_invalid_focus_with_output_never_creates_a_workbench(self):
        with tempfile.TemporaryDirectory(prefix='core-obsidian-focus-') as directory:
            target = Path(directory) / 'absent'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/obsidian_demo.py'),
                                     '--focus', 'not-a-fixture-id', '--output', str(target)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(target.exists())

    def test_fixture_contrast_keeps_its_kind_and_original_version(self):
        api = self.demo_api()
        data = api.knowledge.catalog(EXAMPLE)
        contrasts = [e for e in data['edges'] if e['kind'] == 'contradicts']
        self.assertEqual(len(contrasts), 1)
        self.assertEqual(contrasts[0]['evidence'][0]['sha256'],
                         hashlib.sha256((EXAMPLE / 'Raw/Sources/Informe-A.md').read_bytes()).hexdigest())
        fields = api.knowledge.metadata_from(api.reading_view('demo:idea:synthesis'))
        self.assertEqual(fields['Contrasts'], ['[[examples/obsidian/Wiki/Concepts/Explicacion]]'])
        self.assertNotIn('Related', fields)
        self.assertIn('related', api.reading_view('demo:idea:synthesis'))

    def test_kplex_settings_match_the_typed_navigation_bridge(self):
        settings = json.loads((EXAMPLE / 'kplex.example.json').read_text())
        self.assertIn('Evidence', settings['hierarchy']['leftFriends'])
        self.assertIn('EvidenceFor', settings['hierarchy']['leftFriends'])
        self.assertIn('BuildsOn', settings['hierarchy']['previous'])
        self.assertIn('DevelopedBy', settings['hierarchy']['next'])
        self.assertIn('Contrasts', settings['hierarchy']['rightFriends'])
        self.assertIn('relations', settings['hierarchy']['exclusions'])

    def test_all_explicit_example_wikilinks_resolve_and_settings_are_non_executable(self):
        for path in EXAMPLE.rglob('*.md'):
            for target in re.findall(r'\[\[([^\]|#\n]+)', path.read_text()):
                candidate = ROOT / target
                if not candidate.suffix:
                    candidate = candidate.with_suffix('.md')
                self.assertTrue(candidate.is_file(), f'{path}: {target}')
        settings = json.loads((EXAMPLE / 'kplex.example.json').read_text())
        self.assertEqual(settings['noteTypeField'], 'role')
        self.assertIn('title', settings['nameFields'])
        self.assertFalse(settings['allowOntologySuggester'])
        self.assertNotIn('nodeTitleScript', settings)
        self.assertTrue(all(lens['scope'] == 'node' for lens in settings['graphLenses']))
        for path in EXAMPLE.rglob('*'):
            if path.is_file():
                text = path.read_text()
                self.assertNotIn('/home/', text, path)
                self.assertNotIn('dataviewjs', text, path)


if __name__ == '__main__':
    unittest.main()
