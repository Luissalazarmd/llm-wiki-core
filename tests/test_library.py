"""First-cut tools on synthetic libraries only; no vendor or personal data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts/library.py'


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='core-first-cut-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'library'
        (self.root / 'Material').mkdir(parents=True)
        (self.root / 'Material/a.md').write_text('---\nstatus: growing\n---\n# A\n[[b]]\n![[chart.png]]\n')
        (self.root / 'Material/b.md').write_text('# B\nNo metadata.\n')
        (self.root / 'Material/chart.png').write_bytes(b'Synthetic attachment, never decoded')
        (self.root / 'Material/AGENTS.md').write_text('Synthetic local rules')
        (self.root / 'private.md').write_text('Synthetic unselected note')
        self.config = self.base / 'personal.json'
        self.settings = {'version': 1, 'library_root': 'library', 'authorized_paths': ['Material'],
                         'objectives': ['Compare fictional methods'], 'language': 'en',
                         'organization': 'preserve', 'initiative': 'on_request',
                         'layers': {'sources': ['Material']}}
        self.config.write_text(json.dumps(self.settings))

    def run_cli(self, *args, draft=None):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')

        return subprocess.run([sys.executable, str(CLI), '--config', str(self.config), *args],
                              input=draft, text=True, capture_output=True, env=env, timeout=3)

    def test_map_loads_personal_config_and_inventories_without_moving(self):
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        result = self.run_cli('map', '--scope', 'Material')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['summary']['notes'], 3)
        self.assertEqual(data['summary']['attachments'], 1)
        self.assertEqual(data['folders'], ['Material'])
        self.assertEqual(data['attachments'][0]['path'], 'Material/chart.png')
        self.assertIn('status', data['conventions']['metadata_keys'])
        self.assertEqual(data['layer_proposal'][0]['basis'], 'personal_configuration')
        self.assertEqual(data['layer_proposal'][0]['status'], 'declared_not_verified')
        self.assertEqual(data['rule_paths'], ['Material/AGENTS.md'])
        self.assertNotIn('private.md', result.stdout)
        self.assertNotIn('Synthetic attachment', result.stdout)
        self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                                 for p in self.root.rglob('*') if p.is_file()})

    def test_attachment_links_are_observed_without_loading_contents(self):
        result = self.run_cli('map', '--scope', 'Material')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['attachment_links'], [{'source': 'Material/a.md',
                         'target': 'Material/chart.png', 'kind': 'embed', 'review': 'unverified'}])

    def test_attachment_subpath_resolves_relative_to_note(self):
        (self.root / 'Material/assets').mkdir()
        (self.root / 'Material/assets/figure.svg').write_text('Synthetic attachment')
        (self.root / 'Material/a.md').write_text('![[assets/figure.svg]]')
        result = self.run_cli('map', '--scope', 'Material')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['attachment_links'][0]['target'], 'Material/assets/figure.svg')

    def test_personal_config_applies_language_to_navigation_and_prepares_diff(self):
        result = self.run_cli('read', '--scope', 'Material', '--focus', 'path:Material/a.md', '--format', 'markdown')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('# Reading selection', result.stdout)
        packet = self.run_cli('proposal', '--target', 'Material/a.md', '--evidence', 'Material/b.md',
                              draft='# A\nProposed fictional comparison.\n')
        self.assertEqual(packet.returncode, 0, packet.stderr)
        self.assertFalse(json.loads(packet.stdout)['apply_available'])

    def test_every_action_rejects_outside_authorized_paths(self):
        for args in [('map', '--scope', 'private.md'), ('read', '--scope', '.'),
                     ('proposal', '--target', 'Material/a.md', '--evidence', 'private.md'),
                     ('map', '--scope', '../personal.json')]:
            result = self.run_cli(*args, draft='draft')
            self.assertEqual(result.returncode, 2, result.stdout)

    def test_mapping_without_declarations_requires_review_not_folder_guess(self):
        self.settings.pop('layers')
        self.config.write_text(json.dumps(self.settings))
        result = self.run_cli('map', '--scope', 'Material')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(layer['status'] == 'unassigned' for layer in json.loads(result.stdout)['layer_proposal']))

    def test_binary_only_scope_is_mappable_and_symlinks_fail(self):
        result = self.run_cli('map', '--scope', 'Material/chart.png')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['summary']['notes'], 0)
        (self.root / 'Material/escape').symlink_to(self.root / 'private.md')
        self.assertEqual(self.run_cli('map', '--scope', 'Material').returncode, 2)

    def test_invalid_configuration_is_not_silently_repaired(self):
        for field, value in [('version', True), ('language', 'xx'), ('initiative', 'background'),
                             ('organization', 'automatic-migration'), ('authorized_paths', ['.']),
                             ('password', 'synthetic-not-a-secret'), ('objectives', 'not a list'),
                             ('layers', {'sources': ['private.md']})]:
            self.config.write_text(json.dumps({**self.settings, field: value}))
            self.assertEqual(self.run_cli('map', '--scope', 'Material').returncode, 2, field)
        self.config.write_text('{"version":1,"version":1}')
        self.assertEqual(self.run_cli('map', '--scope', 'Material').returncode, 2)

    def test_inventory_entry_limit_covers_attachments(self):
        for n in range(501):
            (self.root / 'Material' / f'{n}.bin').write_bytes(b'fictional')
        self.assertEqual(self.run_cli('map', '--scope', 'Material').returncode, 2)

    def test_ambiguous_attachment_does_not_invent_a_target(self):
        (self.root / 'Material/nested').mkdir()
        (self.root / 'Material/nested/chart.png').write_bytes(b'fictional')
        result = self.run_cli('map', '--scope', 'Material')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['attachment_links'], [])
        self.assertIn('unresolved_or_ambiguous_attachment', {i['kind'] for i in data['issues']})

    def test_special_file_rejected_without_blocking(self):
        os.mkfifo(self.root / 'Material/pipe.md')
        result = self.run_cli('map', '--scope', 'Material')
        self.assertEqual(result.returncode, 2)
        result = self.run_cli('read', '--scope', 'Material/pipe.md')
        self.assertEqual(result.returncode, 2)
        result = self.run_cli('read', '--scope', 'Material')
        self.assertEqual(result.returncode, 2)

    def test_symlink_or_special_config_rejected_before_open(self):
        linked = self.base / 'linked.json'
        linked.symlink_to(self.config)
        self.config = linked
        self.assertEqual(self.run_cli('map', '--scope', 'Material').returncode, 2)
        self.config = self.base / 'pipe.json'
        os.mkfifo(self.config)
        self.assertEqual(self.run_cli('map', '--scope', 'Material').returncode, 2)

    def test_reproducible_demo_runs_without_private_engine(self):
        result = subprocess.run([sys.executable, str(CLI.parents[1] / 'tests/demo_existing_library.py'),
                                 '--output-parent', str(self.base)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        receipt = json.loads((Path(data['artifacts']) / 'verification.json').read_text())
        self.assertEqual(receipt['before'], receipt['after'])
        self.assertTrue(receipt['out_of_scope_denied'])
        self.assertFalse(receipt['private_engine_present'])


if __name__ == '__main__':
    unittest.main()
