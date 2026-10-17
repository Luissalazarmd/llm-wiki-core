"""Synthetic Raw admission preflight; no actual capture or approval."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


class CaptureCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='capture-check-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'library'
        for folder in ('Inputs', 'Maps', 'Rules'):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        (self.root / 'Maps/home.md').write_text('---\nrole: map\n---\n# Synthetic home\n')
        (self.root / 'Maps/topic.md').write_text('---\nrole: map\nparent: Maps/home.md\n---\n# Synthetic topic\n')
        (self.root / 'Rules/taxonomy.md').write_text('---\ntags: [methods, synthetic]\n---\n# Synthetic taxonomy\n')
        self.settings = {'version': 1, 'library_root': 'library',
                         'authorized_paths': ['Inputs', 'Maps', 'Rules'],
                         'layers': {'sources': ['Inputs']},
                         'capture_policy': {'roots': ['Maps/home.md'], 'taxonomy_path': 'Rules/taxonomy.md'}}
        self.config = self.base / 'personal.json'
        self.config.write_text(json.dumps(self.settings))
        self.draft = '---\nReference: synthetic:source-a\nmoc: Maps/topic.md\ntags: [methods]\n---\n# Fictional source\nPreserved invented input.\n\n## Contexto de captura\nPregunta: ¿qué método describe? Contribuye una descripción para compararlo.\n'

    def call(self, *args, draft=None):
        return subprocess.run([sys.executable, str(BASE / 'scripts/capture_check.py'),
                               '--config', str(self.config), '--target', 'Inputs/a.md', *args],
                              input=self.draft if draft is None else draft, text=True, capture_output=True,
                              timeout=5, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def test_hierarchy_depth_accepts_32_nodes_and_rejects_33(self):
        for count in (32, 33):
            for index in range(count):
                parent = f'parent: Maps/n{index + 1}.md\n' if index < count - 1 else ''
                (self.root / f'Maps/n{index}.md').write_text('---\nrole: map\n' + parent + '---\n')
            self.settings['capture_policy']['roots'] = [f'Maps/n{count - 1}.md']
            self.config.write_text(json.dumps(self.settings))
            result = self.call(draft=self.draft.replace('Maps/topic.md', 'Maps/n0.md'))
            self.assertEqual(result.returncode, 0 if count == 32 else 2, result.stderr)
            if count == 32:
                self.assertEqual(len(json.loads(result.stdout)['stronger_policy']['chain']), 32)
            else:
                self.assertIn('32 nodes', result.stderr)

    def test_missing_moc_tags_or_unknown_taxonomy_tag_is_rejected(self):
        for draft in (self.draft.replace('moc: Maps/topic.md\n', ''),
                      self.draft.replace('tags: [methods]', 'tags: []'),
                      self.draft.replace('tags: [methods]', 'tags: [invented]'),
                      self.draft.replace('tags: [methods]', 'tags: [methods, methods]')):
            result = self.call(draft=draft)
            self.assertEqual(result.returncode, 2, draft)
        self.assertFalse((self.root / 'Inputs/a.md').exists())

    def test_cycles_missing_parent_wrong_role_and_root_parent_are_rejected(self):
        topic = self.root / 'Maps/topic.md'
        for text in ('---\nrole: map\nparent: Maps/topic.md\n---\n',
                     '---\nrole: map\nparent: Maps/missing.md\n---\n',
                     '---\nrole: concept\nparent: Maps/home.md\n---\n',
                     '---\nrole: map\n---\n'):
            topic.write_text(text)
            self.assertEqual(self.call().returncode, 2, text)
        topic.write_text('---\nrole: map\nparent: Maps/home.md\n---\n')
        (self.root / 'Maps/home.md').write_text('---\nrole: map\nparent: Maps/topic.md\n---\n')
        self.assertEqual(self.call().returncode, 2)

    def test_dependency_draft_and_policy_drift_invalidates_check(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = json.loads(result.stdout)['check_sha256']
        for relative in ('Maps/topic.md', 'Maps/home.md', 'Rules/taxonomy.md'):
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(original + b'Changed description\n')
            self.assertEqual(self.call('--expected-sha256', expected).returncode, 2)
            path.write_bytes(original)
        self.assertEqual(self.call('--expected-sha256', expected, draft=self.draft + 'New content\n').returncode, 2)
        self.settings['capture_policy']['roots'].append('Maps/topic.md')
        self.config.write_text(json.dumps(self.settings))
        self.assertEqual(self.call('--expected-sha256', expected).returncode, 2)

    def test_saved_readback_rejects_changed_source_bytes(self):
        result = self.call()
        expected = json.loads(result.stdout)['check_sha256']
        (self.root / 'Inputs/a.md').write_text('Other bytes')
        self.assertEqual(self.call('--saved', '--expected-sha256', expected).returncode, 2)
        self.assertEqual((self.root / 'Inputs/a.md').read_text(), 'Other bytes')

    def test_out_of_scope_symlink_hierarchy_and_non_source_destination_rejected(self):
        (self.root / 'Outside').mkdir()
        (self.root / 'Outside/map.md').write_text('---\nrole: map\nparent: Maps/home.md\n---\n')
        self.assertEqual(self.call(draft=self.draft.replace('Maps/topic.md', 'Outside/map.md')).returncode, 2)
        topic = self.root / 'Maps/topic.md'
        topic.unlink()
        topic.symlink_to(self.root / 'Maps/home.md')
        self.assertEqual(self.call().returncode, 2)
        topic.unlink()
        topic.write_text('---\nrole: map\nparent: Maps/home.md\n---\n')
        self.settings['layers']['sources'] = ['Rules']
        self.config.write_text(json.dumps(self.settings))
        self.assertEqual(self.call().returncode, 2)

    def test_field_mapping_and_crlf_keep_existing_schema_and_exact_bytes(self):
        self.settings['capture_policy']['fields'] = {'moc': 'MOC', 'parent': 'Parent', 'role': 'type',
                                                    'tags': 'labels', 'taxonomy_tags': 'allowed'}
        self.config.write_text(json.dumps(self.settings))
        (self.root / 'Maps/topic.md').write_bytes(b'---\r\ntype: map\r\nParent: Maps/home.md\r\n---\r\n')
        (self.root / 'Maps/home.md').write_bytes(b'---\r\ntype: map\r\n---\r\n')
        (self.root / 'Rules/taxonomy.md').write_text('---\nallowed: [methods]\n---\n')
        draft = self.draft.replace('moc:', 'MOC:').replace('tags:', 'labels:').replace('\n', '\r\n')
        result = self.call(draft=draft)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = json.loads(result.stdout)['check_sha256']
        (self.root / 'Inputs/a.md').write_bytes(draft.encode())
        self.assertEqual(self.call('--saved', '--expected-sha256', expected, draft=draft).returncode, 0)

    def test_capture_preflight_accepts_missing_policy_but_requires_absent_destination(self):
        (self.root / 'Inputs/a.md').symlink_to(self.base / 'missing')
        self.assertEqual(self.call().returncode, 2)
        (self.root / 'Inputs/a.md').unlink()
        self.settings.pop('capture_policy')
        self.config.write_text(json.dumps(self.settings))
        self.assertEqual(self.call().returncode, 0)

    def test_hierarchy_paths_must_be_exact_not_alias_or_wikilink(self):
        for moc in ('Maps/./topic.md', 'Maps//topic.md', '[[Maps/topic]]'):
            self.assertEqual(self.call(draft=self.draft.replace('moc: Maps/topic.md', 'moc: "' + moc + '"')).returncode, 2)

    def test_malformed_capture_policy_is_rejected_by_config_loader(self):
        for policy in ({}, {'roots': [], 'taxonomy_path': 'Rules/taxonomy.md'},
                       {'roots': ['Maps/home.md'], 'taxonomy_path': 'Rules/taxonomy.md', 'invented': True},
                       {'roots': ['Maps/home.md'], 'taxonomy_path': 'Rules/taxonomy.md', 'fields': {'moc': ''}},
                       {'roots': ['Maps/home.md'], 'taxonomy_path': 'Rules/taxonomy.md', 'fields': {'moc': 'tags'}}):
            self.config.write_text(json.dumps({**self.settings, 'capture_policy': policy}))
            result = subprocess.run([sys.executable, str(BASE / 'scripts/library.py'), '--config',
                                     str(self.config), 'map', '--scope', 'Inputs'],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, policy)

    def test_capture_preflight_binds_draft_and_existing_hierarchy_without_writing(self):
        before = {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob('*.md')}
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['stronger_policy']['chain'], ['Maps/topic.md', 'Maps/home.md'])
        self.assertEqual(data['stronger_policy']['tags'], ['methods'])
        self.assertEqual(data['status'], 'capture_structure_checked_not_saved')
        self.assertFalse(data['approval_available'])
        self.assertFalse((self.root / 'Inputs/a.md').exists())
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                                 for p in self.root.rglob('*.md')})
        rechecked = self.call('--expected-sha256', data['check_sha256'])
        self.assertEqual(rechecked.returncode, 0, rechecked.stderr)
        (self.root / 'Inputs/a.md').write_bytes(self.draft.encode())
        verified = self.call('--saved', '--expected-sha256', data['check_sha256'])
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)['status'], 'capture_structure_and_saved_bytes_verified')

    def simple(self, body='Related:: [[Maps/topic]]\nUseful route to the motivating question.'):
        self.settings.pop('capture_policy', None)
        self.config.write_text(json.dumps(self.settings))
        return '---\ntitle: Fuente ficticia\n---\nReference:: fixture:one\nVersion:: v1\n\n' + body + '\n'

    def test_simple_capture_needs_no_moc_taxonomy_or_new_notes(self):
        draft = self.simple()
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*.md')}
        result = self.call(draft=draft)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['connection']['kind'], 'existing_notes')
        self.assertEqual(data['identity']['version'], 'v1')
        self.assertEqual(data['stronger_policy'], {})
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})
        (self.root / 'Inputs/a.md').write_bytes(draft.encode())
        self.assertEqual(self.call('--saved', '--expected-sha256', data['check_sha256'], draft=draft).returncode, 0)

    def test_chat_question_persists_in_capture_without_placeholder(self):
        draft = self.simple('## Contexto de captura\n¿El horario cambia la comparación? '
                            'Este informe aporta el método, todavía no una respuesta.\n\n## Original\nTexto ficticio.')
        result = self.call(draft=draft)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['connection']['kind'], 'persisted_question')
        for body in ('', '## Contexto de captura\n', '```md\nRelated:: [[Maps/topic]]\n```',
                     '<!-- [[Maps/topic]] -->', '[[Inputs/a]]', '[[Maps/missing]]',
                     '[[Maps/topic#Missing]]', '[[Maps/../topic]]', '[[topic]]'):
            with self.subTest(body=body):
                self.assertEqual(self.call(draft=self.simple(body)).returncode, 2)

    def test_identity_and_duplicate_reference_version_are_checked(self):
        draft = self.simple()
        for invalid in (draft.replace('title: Fuente ficticia', ''), draft.replace('Reference:: fixture:one', ''),
                        draft.replace('Version:: v1', 'Version::'),
                        draft.replace('Reference:: fixture:one', 'Reference:: fixture:one\nReference:: other')):
            self.assertEqual(self.call(draft=invalid).returncode, 2)
        other = self.root / 'Inputs/other.md'
        for version in ('v1', None, 'v2'):
            other.write_text('---\nid: distinct-id\nReference: fixture:one\n' +
                             ('Version: ' + version + '\n' if version else '') + '---\nOld version')
            result = self.call(draft=draft)
            self.assertEqual(result.returncode, 0 if version == 'v2' else 2, result.stderr)
        self.assertEqual(self.call(draft=draft.replace('Version:: v1\n', '')).returncode, 2)

    def test_duplicate_scope_and_connection_drift_require_new_check(self):
        draft = self.simple()
        expected = json.loads(self.call(draft=draft).stdout)['check_sha256']
        other = self.root / 'Inputs/other.md'
        other.write_text('Reference:: fixture:other\n')
        self.assertEqual(self.call('--expected-sha256', expected, draft=draft).returncode, 2)
        other.unlink()
        topic = self.root / 'Maps/topic.md'
        topic.write_bytes(topic.read_bytes() + b'Later work\n')
        self.assertEqual(self.call('--expected-sha256', expected, draft=draft).returncode, 2)

    def test_duplicate_search_is_bounded_scoped_and_refuses_symlinks(self):
        draft = self.simple()
        outside = self.root / 'private.md'
        outside.write_text('Reference:: fixture:one\nVersion:: v1\n')
        self.assertEqual(self.call(draft=draft).returncode, 0)
        (self.root / 'Inputs/linked.md').symlink_to(outside)
        self.assertEqual(self.call(draft=draft).returncode, 2)
        (self.root / 'Inputs/linked.md').unlink()
        (self.root / 'Inputs/huge.md').write_bytes(b'x' * 262145)
        self.assertEqual(self.call(draft=draft).returncode, 2)

    def test_capture_connection_reads_have_a_fixed_link_limit(self):
        for count in (50, 51):
            result = self.call(draft=self.simple('[[Maps/topic]]\n' * count))
            self.assertEqual(result.returncode, 0 if count == 50 else 2, result.stderr)

    def test_existing_source_ids_and_capture_role_are_preserved(self):
        draft = self.simple().replace('title: Fuente ficticia', 'id: "012"\ntitle: Fuente ficticia')
        (self.root / 'Inputs/prior.md').write_text('---\nid: "012"\nReference: other:source\n---\n')
        self.assertEqual(self.call(draft=draft).returncode, 2)
        for invalid in (draft.replace('id: "012"', 'id: 12'), draft.replace('id: "012"', 'id: ""'),
                        draft.replace('title: Fuente ficticia', 'role: note\ntitle: Fuente ficticia')):
            self.assertEqual(self.call(draft=invalid).returncode, 2)

    def test_source_removal_and_scope_change_invalidate_recheck(self):
        draft = self.simple()
        source = self.root / 'Inputs/another.md'
        source.write_text('Reference:: fixture:another\n')
        expected = json.loads(self.call(draft=draft).stdout)['check_sha256']
        source.unlink()
        self.assertEqual(self.call('--expected-sha256', expected, draft=draft).returncode, 2)
        source.write_text('Reference:: fixture:another\n')
        self.settings['authorized_paths'].append('Maps/topic.md')
        self.config.write_text(json.dumps(self.settings))
        self.assertEqual(self.call('--expected-sha256', expected, draft=draft).returncode, 2)


if __name__ == '__main__':
    unittest.main()
