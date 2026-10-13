"""Synthetic existing-library tests, independent of any licensed engine."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json
import subprocess
import sys
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts/knowledge.py'


def api():
    spec = importlib.util.spec_from_file_location('core_knowledge', MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExistingLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-existing-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Reading').mkdir()
        (self.root / 'AGENTS.md').write_text('Synthetic existing library rules: preserve all inputs.')
        (self.root / 'Reading' / 'one.md').write_text('# One\nAn existing note without metadata.\n[[Reading/two]]\n')
        (self.root / 'Reading' / 'two.md').write_text('---\ntitle: Two\nstatus: growing\n---\nUnrelated schema.\n')
        (self.root / 'private.md').write_text('Synthetic out-of-scope material')

    def test_existing_library_reads_only_selected_scope_without_migration(self):
        module = api()
        self.assertTrue(hasattr(module, 'discover'), 'Existing-library discovery is missing')
        before = {str(p): p.read_bytes() for p in self.root.rglob('*.md')}
        data = module.discover(self.root, ['Reading'])
        self.assertEqual({n['path'] for n in data['notes']}, {'Reading/one.md', 'Reading/two.md'})
        self.assertEqual(data['library_rules_path'], 'AGENTS.md')
        self.assertTrue(all(n['role'] == 'unknown' and n['maturity'] == 'unknown' for n in data['notes']))
        self.assertTrue(all(n['identity_scope'] == 'path_locator_not_persistent' for n in data['notes']))
        self.assertEqual(data['edges'][0]['kind'], 'link')
        self.assertNotIn('Unrelated schema.', str(data))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*.md')})
        self.assertFalse(data['approval_available'])

    def test_discovery_reports_applicable_nested_rules_without_root_rules(self):
        (self.root / 'AGENTS.md').unlink()
        (self.root / 'Reading/AGENTS.md').write_text('Synthetic reading rules')
        (self.root / 'Reading/nested').mkdir()
        (self.root / 'Reading/nested/AGENTS.md').write_text('Synthetic nested rules')
        (self.root / 'Reading/nested/note.md').write_text('Synthetic selected note')
        (self.root / 'Other').mkdir()
        (self.root / 'Other/AGENTS.md').write_text('Unselected instructions')
        before = {str(p): p.read_bytes() for p in self.root.rglob('*.md')}
        data = api().discover(self.root, ['Reading/nested/note.md'])
        self.assertIsNone(data['library_rules_path'])
        self.assertEqual(data['rule_paths'], ['Reading/AGENTS.md', 'Reading/nested/AGENTS.md'])
        self.assertNotIn('Synthetic nested rules', json.dumps(data))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*.md')})

    def test_strict_mode_rejects_foreign_layout_instead_of_empty_success(self):
        for mode in ([], ['--mode', 'strict']):
            result = subprocess.run([sys.executable, str(MODULE), '--root', str(self.root), *mode],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn('--mode existing', result.stderr)
            self.assertEqual(result.stdout, '')
        (self.root / 'Raw').mkdir()
        with self.assertRaisesRegex(ValueError, '--mode existing'):
            api().catalog(self.root)

    def test_scope_boundary_hidden_paths_and_symlinks(self):
        module = api()
        for scope in [[], ['.'], ['../elsewhere'], ['/absolute'], ['.obsidian']]:
            with self.assertRaises(ValueError):
                module.discover(self.root, scope)
        (self.root / 'Reading' / 'escape.md').symlink_to(self.root / 'private.md')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            module.discover(self.root, ['Reading'])

    def test_ambiguous_links_and_bad_metadata_are_reported_not_guessed(self):
        (self.root / 'Reading/one.md').write_text('[[two]]')
        (self.root / 'Reading' / 'nested').mkdir()
        (self.root / 'Reading' / 'nested' / 'two.md').write_text('# Duplicate basename')
        (self.root / 'Reading' / 'bad.md').write_text('---\nrole: map\nrole: source\n---\n[[outside]]')
        data = api().discover(self.root, ['Reading'])
        self.assertEqual(data['edges'], [])
        self.assertIn('unparsed_frontmatter', {i['kind'] for i in data['issues']})
        self.assertIn('basename_link_requires_explicit_path', {i['kind'] for i in data['issues']})

    def test_code_examples_are_not_graph_edges(self):
        (self.root / 'Reading' / 'one.md').write_text('# One\n```md\n[[two]]\n```\n`[[two]]`\n')
        self.assertEqual(api().discover(self.root, ['Reading'])['edges'], [])

    def test_bounds_and_overlapping_scopes(self):
        module = api()
        with self.assertRaisesRegex(ValueError, 'note limit'):
            module.discover(self.root, ['Reading'], max_notes=1)
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            module.discover(self.root, ['Reading'], max_file_bytes=10)
        self.assertEqual(len(module.discover(self.root, ['Reading', 'Reading/one.md'])['notes']), 2)

    def test_cli_existing_mode_focus_and_markdown(self):
        for extra in [[], ['--focus', 'path:Reading/one.md', '--format', 'markdown']]:
            p = subprocess.run([sys.executable, str(MODULE), '--root', str(self.root),
                '--mode', 'existing', '--scope', 'Reading', *extra], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            if not extra:
                self.assertEqual(json.loads(p.stdout)['mode'], 'existing_library_read_only')
            else:
                self.assertIn('[[Reading/two]]', p.stdout)

    def test_prepare_bound_proposal_without_engine_or_writes(self):
        module = api()
        self.assertTrue(hasattr(module, 'prepare_proposal'), 'Vendor-independent proposal preparation is missing')
        before = {str(p): p.read_bytes() for p in self.root.rglob('*.md')}
        result = module.prepare_proposal(self.root, 'Reading/one.md',
                                         '# One\nProposed synthetic interpretation.\n', ['Reading/two.md'])
        self.assertEqual(result['status'], 'prepared_not_approved')
        self.assertFalse(result['apply_available'])
        self.assertIn('Proposed synthetic interpretation', result['diff'])
        self.assertEqual(result['target']['path'], 'Reading/one.md')
        self.assertEqual(result['evidence'][0]['path'], 'Reading/two.md')
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*.md')})
        changed = module.prepare_proposal(self.root, 'Reading/one.md', 'Different draft', ['Reading/two.md'])
        self.assertNotEqual(changed['packet_sha256'], result['packet_sha256'])

    def test_proposal_rejects_escape_and_oversized_draft(self):
        module = api()
        with self.assertRaises(ValueError):
            module.prepare_proposal(self.root, '../outside.md', 'draft', [])
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            module.prepare_proposal(self.root, 'Reading/one.md', 'x' * 300000, [])

    def test_focused_context_drops_unrelated_diagnostics(self):
        (self.root / 'Reading' / 'unrelated.md').write_text('[[private-sensitive-name]]')
        module = api()
        result = module.focus(module.discover(self.root, ['Reading']), 'path:Reading/one.md')
        self.assertNotIn('private-sensitive-name', json.dumps(result))

    def test_basename_link_is_not_a_neighbor_even_with_one_scoped_match(self):
        (self.root / 'Reading/one.md').write_text('[[two]]')
        (self.root / 'Outside').mkdir()
        (self.root / 'Outside/two.md').write_text('Unselected homonym')
        module = api()
        data = module.discover(self.root, ['Reading'])
        self.assertEqual(data['edges'], [])
        self.assertIn('basename_link_requires_explicit_path', {i['kind'] for i in data['issues']})
        self.assertEqual(len(module.focus(data, 'path:Reading/one.md')['notes']), 1)
        self.assertNotIn('Outside/two.md', json.dumps(data))
        (self.root / 'Reading/one.md').write_text('[[Reading/two]]\n[[./two]]\n[[Outside/two]]')
        explicit = module.discover(self.root, ['Reading'])
        self.assertTrue(all(e['target'] == 'path:Reading/two.md' for e in explicit['edges']))
        self.assertEqual(len(explicit['edges']), 2)

    def test_relative_links_resolve_inside_scope_only(self):
        (self.root / 'Reading' / 'one.md').write_text('[[./two]]\n[[../private]]')
        data = api().discover(self.root, ['Reading'])
        self.assertEqual(len(data['edges']), 1)
        self.assertEqual(data['edges'][0]['target'], 'path:Reading/two.md')
        self.assertEqual(len(data['notes']), 2)

    def test_cli_proposal_is_bound_to_actual_base(self):
        p = subprocess.run([sys.executable, str(MODULE), '--root', str(self.root),
            '--proposal-target', 'Reading/one.md', '--evidence', 'Reading/two.md'],
            input='# One\nRevised fictional interpretation\n', capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertFalse(data['apply_available'])
        first = data['packet_sha256']
        (self.root / 'Reading' / 'two.md').write_text('Changed evidence')
        q = subprocess.run([sys.executable, str(MODULE), '--root', str(self.root),
            '--proposal-target', 'Reading/one.md', '--evidence', 'Reading/two.md'],
            input='# One\nRevised fictional interpretation\n', capture_output=True, text=True)
        self.assertNotEqual(first, json.loads(q.stdout)['packet_sha256'])

    def test_proposal_rejects_directory_target_before_reading(self):
        with self.assertRaisesRegex(ValueError, 'Markdown file'):
            api().prepare_proposal(self.root, 'Reading', 'draft', [])


    def test_proposal_base_changed_during_preparation_fails(self):
        module = api()
        discover = module.discover
        def change_after_scan(*args, **kwargs):
            result = discover(*args, **kwargs)
            (self.root / 'Reading/one.md').write_text('Concurrent synthetic edit')
            return result
        with patch.object(module, 'discover', side_effect=change_after_scan):
            with self.assertRaisesRegex(ValueError, 'changed'):
                module.prepare_proposal(self.root, 'Reading/one.md', 'draft', [])

    def test_cli_does_not_ignore_unrelated_evidence_argument(self):
        result = subprocess.run([sys.executable, str(MODULE), '--root', str(self.root),
            '--mode', 'existing', '--scope', 'Reading', '--evidence', 'private.md'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_nonmarkdown_scope_rejected(self):
        (self.root / 'capture.pdf').write_text('Synthetic binary placeholder')
        with self.assertRaisesRegex(ValueError, 'Markdown'):
            api().discover(self.root, ['capture.pdf'])

    def test_proposal_preserves_crlf_byte_binding(self):
        import hashlib
        original = b'# One\r\nSynthetic Windows note.\r\n'
        (self.root / 'Reading/one.md').write_bytes(original)
        result = api().prepare_proposal(self.root, 'Reading/one.md', '# One\nDraft\n', [])
        self.assertEqual(result['target']['base_sha256'], hashlib.sha256(original).hexdigest())

    def test_special_markdown_files_fail_before_reading(self):
        import os
        os.mkfifo(self.root / 'Reading/pipe.md')
        module = api()
        with self.assertRaisesRegex(ValueError, 'regular'):
            module.discover(self.root, ['Reading'])
        with self.assertRaisesRegex(ValueError, 'regular'):
            module.discover(self.root, ['Reading/pipe.md'])
        (self.root / 'Raw').mkdir()
        os.mkfifo(self.root / 'Raw/pipe.md')
        with self.assertRaisesRegex(ValueError, 'regular'):
            module.catalog(self.root)


if __name__ == '__main__':
    unittest.main()
