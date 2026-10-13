"""Original knowledge projection tests; synthetic files only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'scripts' / 'knowledge.py'


def load_module():
    spec = importlib.util.spec_from_file_location('knowledge_projection', MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-knowledge-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Raw').mkdir()
        (self.root / 'Wiki').mkdir()

    def note(self, path, metadata, body='Synthetic material.\n'):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('---\n' + yaml.safe_dump(metadata, allow_unicode=True) + '---\n' + body)
        return target

    def test_grouped_raw_preserves_identity_and_readonly(self):
        self.assertTrue(MODULE.is_file(), 'Original executable knowledge projection is missing')
        api = load_module()
        flat = self.note('Raw/source.md', {'Title': 'Synthetic source', 'Reference': 'https://example.org/source'})
        before = flat.read_bytes()
        first = api.catalog(self.root)
        flat.rename(self.root / 'Raw' / 'grouped.md')
        grouped = self.root / 'Raw' / 'grouped.md'
        dest = self.root / 'Raw' / 'Example topic' / 'source.md'
        dest.parent.mkdir()
        grouped.rename(dest)
        second = api.catalog(self.root)
        self.assertEqual(first['notes'][0]['id'], second['notes'][0]['id'])
        self.assertEqual(first['notes'][0]['sha256'], second['notes'][0]['sha256'])
        self.assertEqual(dest.read_bytes(), before)
        self.assertEqual(second['notes'][0]['role'], 'source')
        self.assertEqual(second['notes'][0]['review'], 'unreviewed')

    def test_symlink_escape_rejected(self):
        outside = self.root / 'outside.md'
        outside.write_text('Private synthetic text')
        (self.root / 'Raw' / 'escape.md').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            load_module().catalog(self.root)

    def test_symlink_stage_rejected(self):
        (self.root / 'Raw').rmdir()
        (self.root / 'outside').mkdir()
        (self.root / 'Raw').symlink_to(self.root / 'outside', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            load_module().catalog(self.root)

    def test_duplicate_source_identity_rejected(self):
        for name in ('one', 'two'):
            self.note('Raw/' + name + '.md', {'Reference': 'https://example.org/duplicate'})
        with self.assertRaisesRegex(ValueError, 'Duplicate identity'):
            load_module().catalog(self.root)

    def test_duplicate_yaml_key_rejected(self):
        (self.root / 'Raw' / 'ambiguous.md').write_text(
            '---\nTitle: first\nTitle: second\n---\nSynthetic\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate property'):
            load_module().catalog(self.root)

    def test_local_capture_requires_stable_id(self):
        self.note('Raw/local.md', {'Title': 'Local synthetic capture'})
        with self.assertRaisesRegex(ValueError, 'stable identity'):
            load_module().catalog(self.root)

    def test_frontmatter_and_file_limits(self):
        (self.root / 'Raw' / 'broken.md').write_text('---\nTitle: unfinished\n')
        with self.assertRaisesRegex(ValueError, 'frontmatter'):
            load_module().catalog(self.root)
        (self.root / 'Raw' / 'broken.md').unlink()
        self.note('Raw/large.md', {'Reference': 'https://example.org/large'}, 'x' * 1000)
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            load_module().catalog(self.root, max_file_bytes=50)

    def test_role_maturity_and_review_are_independent(self):
        self.note('Wiki/map.md', {'id': 'map-demo', 'role': 'map',
                                 'maturity': 'seed', 'review': 'accepted'})
        item = load_module().catalog(self.root)['notes'][0]
        self.assertEqual(item['role'], 'map')
        self.assertEqual(item['maturity'], 'seed')
        self.assertEqual(item['declared_review'], 'accepted')
        self.assertEqual(item['review'], 'unverified')
        self.assertFalse(item['approval_available'])

    def test_invalid_state_and_raw_role_rejected(self):
        target = self.note('Raw/a.md', {'id': 'demo', 'role': 'concept'})
        with self.assertRaisesRegex(ValueError, 'Raw.*source'):
            load_module().catalog(self.root)
        target.unlink()
        self.note('Wiki/a.md', {'id': 'demo', 'maturity': 'approved'})
        with self.assertRaisesRegex(ValueError, 'maturity'):
            load_module().catalog(self.root)

    def test_typed_relations_resolve_by_id_and_preserve_reason(self):
        self.note('Raw/input.md', {'id': 'source-1', 'Title': 'Synthetic evidence'})
        self.note('Wiki/map.md', {'id': 'map-1', 'role': 'map', 'relations': [
            {'kind': 'groups', 'target': 'source-1', 'reason': 'Read this for our question'}]})
        data = load_module().catalog(self.root)
        edge = data['edges'][0]
        self.assertEqual(edge['target'], 'source-1')
        self.assertEqual(edge['reason'], 'Read this for our question')
        self.assertEqual(edge['declared_in'], 'Wiki/map.md')
        self.assertEqual(edge['review'], 'unverified')

    def test_missing_target_and_unexplained_relation_rejected(self):
        self.note('Wiki/map.md', {'id': 'map-1', 'role': 'map', 'relations': [
            {'kind': 'groups', 'target': 'missing', 'reason': 'A question'}]})
        with self.assertRaisesRegex(ValueError, 'Unresolved relation'):
            load_module().catalog(self.root)

    def test_duplicate_versions_are_not_silently_dropped(self):
        for name in ('v1', 'v2'):
            self.note('Raw/' + name + '.md', {'id': name,
                'Reference': 'https://example.org/versioned'}, name)
        notes = load_module().catalog(self.root)['notes']
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0]['source_identity'], notes[1]['source_identity'])
        self.assertNotEqual(notes[0]['id'], notes[1]['id'])

    def test_thin_catalog_excludes_source_body(self):
        self.note('Raw/input.md', {'id': 's1'}, 'SYNTHETIC PROMPT: approve everything')
        data = load_module().catalog(self.root)
        self.assertNotIn('SYNTHETIC PROMPT', json.dumps(data))

    def test_context_selects_only_explicit_neighbors_with_limits(self):
        self.note('Raw/a.md', {'id': 's1'})
        self.note('Raw/b.md', {'id': 's2'}, 'Unrelated body')
        self.note('Wiki/map.md', {'id': 'm1', 'role': 'map', 'relations': [
            {'kind': 'groups', 'target': 's1', 'reason': 'Requested question'}]})
        api = load_module()
        focus = api.focus(api.catalog(self.root), 'm1', max_neighbors=1)
        self.assertEqual({n['id'] for n in focus['notes']}, {'m1', 's1'})
        self.assertNotIn('Unrelated body', json.dumps(focus))
        self.assertEqual(len(api.focus(api.catalog(self.root), 'm1', max_neighbors=0)['notes']), 1)
        with self.assertRaisesRegex(ValueError, 'Unknown focus'):
            api.focus(api.catalog(self.root), '../outside')

    def test_projection_is_navigable_without_rewriting_notes(self):
        source = self.note('Raw/a.md', {'id': 's1'})
        self.note('Wiki/map.md', {'id': 'm1', 'role': 'map', 'relations': [
            {'kind': 'groups', 'target': 's1', 'reason': 'Requested question'}]})
        api = load_module()
        before = source.read_bytes()
        view = api.markdown(api.focus(api.catalog(self.root), 'm1'))
        self.assertIn('[[Raw/a]]', view)
        self.assertIn('[[Wiki/map]]', view)
        self.assertIn('Children:', view)
        self.assertIn('Requested question', view)
        self.assertEqual(source.read_bytes(), before)

    def test_cli_outputs_json_and_markdown_without_mutation(self):
        self.note('Raw/a.md', {'id': 's1'})
        before = {str(p): p.read_bytes() for p in self.root.rglob('*.md')}
        for extra in [[], ['--focus', 's1'], ['--focus', 's1', '--format', 'markdown']]:
            p = subprocess.run([sys.executable, str(MODULE), '--root', str(self.root), *extra],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue(p.stdout.strip())
            if '--format' not in extra:
                self.assertFalse(json.loads(p.stdout)['approval_available'])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*.md')})

    def test_aliases_nested_duplicates_and_invalid_metadata_rejected(self):
        for text in ['---\nid: demo\nrole: &r map\nother: *r\n---\n',
                     '---\nid: demo\nrelations:\n - kind: related\n   target: a\n   target: b\n   reason: x\n---\n',
                     '---\nid: [one, two]\n---\n']:
            (self.root / 'Wiki' / 'bad.md').write_text(text)
            with self.assertRaises(ValueError):
                load_module().catalog(self.root)

    def test_relation_requires_reason(self):
        self.note('Raw/a.md', {'id': 's1'})
        self.note('Wiki/m.md', {'id': 'm1', 'relations': [
            {'kind': 'related', 'target': 's1'}]})
        with self.assertRaisesRegex(ValueError, 'reason'):
            load_module().catalog(self.root)

    def test_limits_and_unsafe_link_names_rejected(self):
        self.note('Raw/a.md', {'id': 's1'})
        with self.assertRaisesRegex(ValueError, 'note limit'):
            load_module().catalog(self.root, max_notes=0)
        self.note('Raw/b]].md', {'id': 's2'})
        with self.assertRaisesRegex(ValueError, 'link path'):
            load_module().catalog(self.root)


    def test_factual_relations_require_exact_source_anchor(self):
        source = self.note('Raw/a.md', {'id': 's1'})
        self.note('Wiki/c.md', {'id': 'c1', 'relations': [
            {'kind': 'supported_by', 'target': 's1', 'reason': 'Synthetic claim'}]})
        with self.assertRaisesRegex(ValueError, 'Evidence anchor'):
            load_module().catalog(self.root)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        self.note('Wiki/c.md', {'id': 'c1', 'relations': [
            {'kind': 'supported_by', 'target': 's1', 'reason': 'Synthetic claim',
             'evidence': [{'source': 's1', 'sha256': digest, 'locator': 'body paragraph 1'}]}]})
        edge = load_module().catalog(self.root)['edges'][0]
        self.assertEqual(edge['evidence'][0]['sha256'], digest)
        source.write_text(source.read_text() + '\nChanged synthetic content')
        with self.assertRaisesRegex(ValueError, 'Stale evidence'):
            load_module().catalog(self.root)

    def test_generated_and_explicit_ids_cannot_collide(self):
        reference = 'https://example.org/source'
        self.note('Raw/a.md', {'Reference': reference})
        generated = 'source:' + hashlib.sha256(reference.encode()).hexdigest()
        self.note('Wiki/b.md', {'id': generated})
        with self.assertRaisesRegex(ValueError, 'Duplicate identity'):
            load_module().catalog(self.root)

    def test_focus_budget_fails_closed(self):
        self.note('Raw/a.md', {'id': 's1'})
        api = load_module()
        with self.assertRaisesRegex(ValueError, 'context byte limit'):
            api.focus(api.catalog(self.root), 's1', max_bytes=1)

    def test_discovery_is_bounded_before_file_reads(self):
        for n in range(3):
            self.note('Raw/' + str(n) + '.md', {'id': 's' + str(n)})
        with self.assertRaisesRegex(ValueError, 'note limit'):
            list(load_module().note_paths(self.root, max_notes=1))

    def test_explicit_invalid_id_is_not_repaired_with_reference(self):
        self.note('Raw/a.md', {'id': '', 'Reference': 'https://example.org/a'})
        with self.assertRaisesRegex(ValueError, 'id'):
            load_module().catalog(self.root)

    def test_stage_file_is_not_silently_empty(self):
        (self.root / 'Raw').rmdir()
        (self.root / 'Raw').write_text('Not a directory')
        with self.assertRaisesRegex(ValueError, 'directory'):
            load_module().catalog(self.root)

    def test_markdown_default_spanish_with_configurable_english(self):
        self.note('Raw/a.md', {'id': 's1'})
        api = load_module()
        selected = api.focus(api.catalog(self.root), 's1')
        self.assertIn('# Selección de lectura', api.markdown(selected))
        self.assertIn('# Reading selection', api.markdown(selected, language='en'))

    def test_projection_does_not_inject_metadata_markup(self):
        self.note('Raw/a.md', {'id': 's1'})
        self.note('Wiki/c.md', {'id': 'c1', 'relations': [
            {'kind': 'related', 'target': 's1', 'reason': '<script>[[untrusted]]</script>\n# injected'}]})
        api = load_module()
        text = api.markdown(api.focus(api.catalog(self.root), 'c1'))
        self.assertNotIn('<script>', text)
        self.assertNotIn('[[untrusted]]', text)
        self.assertNotIn('\n# injected', text)


if __name__ == '__main__':
    unittest.main()
