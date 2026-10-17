"""Native relation projection, compatibility and scope refusal on synthetic files."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_knowledge', ROOT / 'scripts/knowledge.py')
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


class NativeKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write('Raw/source.md', 'role: source', 'Reference:: demo:v1\n\n## Results\nInvented.')
        self.write('Wiki/map.md', 'role: map', '# Route')
        self.write('Wiki/idea.md', 'role: note\nmaturity: synthesis\nup: "[[Wiki/map]]"',
                   'Evidence:: [[Raw/source#Results]]\n\nAn explicitly fictional argument.')

    def write(self, path, front, body):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('---\n' + front + '\n---\n' + body + '\n')
        return target

    def test_native_projection_binds_actual_source_and_declaration_without_writing(self):
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*.md')}
        data = API.catalog(self.root)
        self.assertEqual({n['role'] for n in data['notes']}, {'source', 'note', 'map'})
        edge = next(e for e in data['edges'] if e['kind'] == 'supported_by')
        self.assertEqual(edge['evidence'][0]['sha256'], hashlib.sha256(before[self.root / 'Raw/source.md'][0]).hexdigest())
        self.assertEqual(edge['target_locator'], '#Results')
        self.assertEqual(edge['declared_line'], 6)
        self.assertEqual(edge['reason'], 'An explicitly fictional argument.')
        self.assertEqual(edge['review'], 'unverified')
        self.assertEqual(len([e for e in data['edges'] if e['kind'] == 'groups']), 1)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})

    def test_legacy_roles_and_maturity_are_normalized_only_in_projection(self):
        for role in ('concept', 'entity', 'project', 'diagram'):
            self.write('Wiki/' + role + '.md', f'id: {role}\nrole: {role}\nmaturity: developing', '# Legacy')
        legacy = [n for n in API.catalog(self.root)['notes'] if n['id'] in API.LEGACY_ROLES]
        self.assertEqual(len(legacy), 4)
        for note in legacy:
            self.assertEqual(note['role'], 'note')
            self.assertEqual(note['maturity'], 'synthesis')
            self.assertEqual(note['declared_maturity'], 'developing')
            self.assertEqual(note['declared_role'], note['id'])
            self.assertIn('maturity: developing', (self.root / note['path']).read_text())

    def test_broken_unsafe_out_of_scope_and_ambiguous_anchors_fail(self):
        for target in ('Raw/missing', '../outside', '/Raw/source', 'source',
                       'Raw/%2e%2e/source', 'Raw/source#Missing', 'Raw/source#', 'Raw/source#^block'):
            with self.subTest(target=target):
                self.write('Wiki/idea.md', 'role: note', f'Evidence:: [[{target}]]')
                with self.assertRaises(ValueError):
                    API.catalog(self.root)
        self.write('Raw/source.md', 'role: source', 'Reference:: demo:v1\n## Results\nA\n## Results\nB')
        self.write('Wiki/idea.md', 'role: note', 'Evidence:: [[Raw/source#Results]]')
        with self.assertRaisesRegex(ValueError, 'ambiguous native heading'):
            API.catalog(self.root)
        self.write('Raw/source.md', 'role: source', 'Reference:: demo:v1\n## Results `code`\nA')
        with self.assertRaisesRegex(ValueError, 'native heading'):
            API.catalog(self.root)

    def test_code_comments_and_frontmatter_examples_do_not_create_edges(self):
        self.write('Wiki/idea.md', 'role: note\ntitle: "Evidence:: [[Raw/missing]]"',
                   '```md\nEvidence:: [[Raw/missing]]\n```\n'
                   '<!--\nEvidence:: [[Raw/missing]]\n-->\n'
                   '`Evidence:: [[Raw/missing]]`\n    Evidence:: [[Raw/missing]]\n'
                   'Evidence:: [[Raw/source#Results]]')
        self.assertEqual(len(API.catalog(self.root)['edges']), 1)

    def test_sources_and_native_evidence_require_sources_not_other_notes(self):
        self.write('Wiki/idea.md', 'role: note\nsources: ["[[Raw/source#Results]]"]', '# Idea')
        self.assertEqual(API.catalog(self.root)['edges'][0]['kind'], 'supported_by')
        self.assertEqual(API.catalog(self.root)['edges'][0]['declared_field'], 'sources')
        self.assertIsNone(API.catalog(self.root)['edges'][0]['declared_line'])
        for front, body in [('role: note\nsources: invalid', '# Idea'),
                            ('role: note', 'Evidence:: [[Wiki/map]]'),
                            ('role: note', 'Evidence:: not-a-link'),
                            ('role: note\nup: ["[[Wiki/map]]"]', '# Idea')]:
            self.write('Wiki/idea.md', front, body)
            with self.assertRaises(ValueError):
                API.catalog(self.root)

    def test_cycle_and_duplicate_primary_declaration_are_rejected(self):
        self.write('Wiki/map.md', 'role: map\nup: "[[Wiki/map]]"', '# Route')
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            API.catalog(self.root)
        self.write('Wiki/map.md', 'role: map\nparent: Wiki/map.md\nup: "[[Wiki/map]]"', '# Route')
        with self.assertRaisesRegex(ValueError, 'one declaration'):
            API.catalog(self.root)

    def test_multiple_meanings_are_preserved_and_reported_at_focus(self):
        self.write('Wiki/other.md', 'role: note', '# Other')
        self.write('Wiki/idea.md', 'role: note', 'Related:: [[Wiki/other]]\n\nRelevant.\n'
                   'Contrasts:: [[Wiki/other]]\n\nDisagreement.\n'
                   'BuildsOn:: [[Wiki/other]]\n\nDevelopment.')
        data = API.focus(API.catalog(self.root), 'path:Wiki/idea.md')
        self.assertEqual({e['kind'] for e in data['edges']}, {'related', 'contradicts', 'extends'})
        self.assertEqual(data['issues'][0]['kind'], 'multiple_relation_kinds')
        self.assertEqual(data['notes'][0]['maturity'], 'unknown')
        self.assertIn('Varias relaciones', API.markdown(data))
        self.assertEqual(API.focus(API.catalog(self.root), 'path:Wiki/idea.md', max_neighbors=0)['issues'], [])

    def test_prefix_is_explicit_and_does_not_expand_catalog_scope(self):
        self.write('Wiki/idea.md', 'role: note', 'Evidence:: [[demo/Raw/source#Results]]')
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            API.catalog(self.root)
        self.assertEqual(len(API.catalog(self.root, link_prefix='demo')['edges']), 1)
        with self.assertRaises(ValueError):
            API.catalog(self.root, link_prefix='../demo')

    def test_native_related_keeps_separate_heading_locators_with_same_argument(self):
        self.write('Wiki/other.md', 'role: note', '## First\nOne\n## Second\nTwo')
        self.write('Wiki/idea.md', 'role: note',
                   'Related:: [[Wiki/other#First]]\n\nSame reason.\n\n'
                   'Related:: [[Wiki/other#Second]]\n\nSame reason.')
        edges = API.catalog(self.root)['edges']
        self.assertEqual([edge['target_locator'] for edge in edges], ['#First', '#Second'])
        self.assertNotEqual(edges[0]['declared_line'], edges[1]['declared_line'])

    def test_source_versions_coexist_without_changing_existing_ids(self):
        original = (self.root / 'Raw/source.md').read_bytes()
        old_id = next(n['id'] for n in API.catalog(self.root)['notes'] if n['role'] == 'source')
        self.write('Raw/versioned.md', 'id: explicit-id\nrole: source',
                   'Reference:: demo:versioned\nVersion:: v1')
        self.write('Raw/later.md', 'role: source', 'Reference:: demo:versioned\nVersion:: v2')
        data = API.catalog(self.root)
        self.assertEqual(len([n for n in data['notes'] if n['role'] == 'source']), 3)
        self.assertIn(old_id, {n['id'] for n in data['notes']})
        self.assertEqual((self.root / 'Raw/source.md').read_bytes(), original)
        self.write('Raw/later.md', 'id: another-explicit-id\nrole: source',
                   'Reference:: demo:versioned\nVersion:: v1')
        with self.assertRaisesRegex(ValueError, 'Duplicate identity'):
            API.catalog(self.root)

    def test_legacy_review_is_data_while_new_notes_require_no_review_metadata(self):
        before = (self.root / 'Wiki/idea.md').read_bytes()
        idea = next(n for n in API.catalog(self.root)['notes'] if n['path'] == 'Wiki/idea.md')
        self.assertIsNone(idea['declared_review'])
        self.assertEqual(idea['review'], 'unverified')
        self.assertFalse(idea['approval_available'])
        self.assertEqual((self.root / 'Wiki/idea.md').read_bytes(), before)
        self.write('Wiki/legacy.md', 'role: note\nreview: accepted', '# Legacy')
        legacy = next(n for n in API.catalog(self.root)['notes'] if n['path'] == 'Wiki/legacy.md')
        self.assertEqual(legacy['declared_review'], 'accepted')
        self.assertEqual(legacy['review'], 'unverified')
        self.assertFalse(legacy['approval_available'])


if __name__ == '__main__':
    unittest.main()
