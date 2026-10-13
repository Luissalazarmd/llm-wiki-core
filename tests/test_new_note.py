"""First derived-note proposal and create-only CLI; synthetic inputs only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


class NewNoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='new-note-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'library'
        (self.root / 'Notes').mkdir(parents=True)
        (self.root / 'Sources').mkdir()
        (self.base / 'recovery').mkdir()
        (self.root / 'Sources/a.md').write_text('# Synthetic source\nFictional measurement method.\n')
        self.config = self.base / 'personal.json'
        self.settings = {'version': 1, 'library_root': 'library',
                         'authorized_paths': ['Notes', 'Sources'],
                         'layers': {'sources': ['Sources']}, 'write_policy': 'plain_files',
                         'recovery_directory': 'recovery'}
        self.config.write_text(json.dumps(self.settings))
        self.draft = '# Fictional comparison\nOnly method descriptions are compared.\n[[Sources/a]]\n'
        self.packet = self.base / 'proposal.json'
        self.target = self.root / 'Notes/new.md'

    def cli(self, script, *args, draft=None):
        return subprocess.run([sys.executable, str(BASE / 'scripts' / script), *args],
                              input=draft, text=True, capture_output=True, timeout=5,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def propose(self, target='Notes/new.md'):
        result = self.cli('library.py', '--config', str(self.config), 'proposal',
                          '--create', '--target', target, '--evidence', 'Sources/a.md', draft=self.draft)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.packet.write_text(result.stdout)
        return json.loads(result.stdout)

    def write(self, action='save'):
        return self.cli('note_write.py', '--config', str(self.config), action,
                        '--packet', str(self.packet))

    def test_existing_or_dangling_target_blocks_proposal_and_save(self):
        self.propose()
        for entry in ('file', 'directory', 'symlink'):
            if entry == 'file':
                self.target.write_text('Prior work')
            elif entry == 'directory':
                self.target.mkdir()
            else:
                self.target.symlink_to(self.base / 'missing')
            self.assertEqual(self.write().returncode, 2)
            rejected = self.cli('knowledge.py', '--root', str(self.root), '--create',
                                '--proposal-target', 'Notes/new.md', '--evidence', 'Sources/a.md', draft=self.draft)
            self.assertEqual(rejected.returncode, 2)
            if entry == 'directory':
                self.target.rmdir()
            else:
                if entry == 'file':
                    self.assertEqual(self.target.read_text(), 'Prior work')
                self.target.unlink()
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_stale_evidence_or_rehashed_misleading_diff_blocks_creation(self):
        import hashlib
        packet = self.propose()
        source = self.root / 'Sources/a.md'
        original = source.read_bytes()
        source.write_text('Later source version')
        self.assertEqual(self.write().returncode, 2)
        source.write_bytes(original)
        packet['diff'] = 'Not the proposed creation'
        del packet['packet_sha256']
        packet['packet_sha256'] = hashlib.sha256(json.dumps(packet, sort_keys=True, ensure_ascii=False,
                                                          separators=(',', ':')).encode()).hexdigest()
        self.packet.write_text(json.dumps(packet))
        self.assertEqual(self.write('check').returncode, 2)
        self.assertEqual(self.write().returncode, 2)
        self.assertFalse(self.target.exists())
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_create_cannot_bypass_policy_sources_instructions_or_scope(self):
        self.propose()
        for policy in ('read_only', 'canonical_engine'):
            self.config.write_text(json.dumps({**self.settings, 'write_policy': policy}))
            self.assertEqual(self.write().returncode, 2)
        self.config.write_text(json.dumps(self.settings))
        for marker in ('.wanderloots-llm-wiki', '.private-engine-install.json'):
            path = self.root / marker
            path.symlink_to(self.base / 'missing')
            self.assertEqual(self.write().returncode, 2)
            path.unlink()
        for target in ('Sources/new.md', 'Notes/AGENTS.md', 'Notes/SKILL.md', 'Notes/CLAUDE.md', 'Notes/skill.md'):
            self.propose(target)
            self.assertEqual(self.write().returncode, 2)
            self.assertFalse((self.root / target).exists())
        for target in ('../outside.md', '.hidden/new.md', 'Missing/new.md', 'Notes/a.txt'):
            rejected = self.cli('library.py', '--config', str(self.config), 'proposal', '--create',
                                '--target', target, '--evidence', 'Sources/a.md', draft=self.draft)
            self.assertEqual(rejected.returncode, 2, target)
        (self.root / 'Other').mkdir()
        rejected = self.cli('library.py', '--config', str(self.config), 'proposal', '--create',
                            '--target', 'Other/new.md', '--evidence', 'Sources/a.md', draft=self.draft)
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse((self.root / 'Other/new.md').exists())
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_no_evidence_and_symlink_parent_are_rejected(self):
        rejected = self.cli('knowledge.py', '--root', str(self.root), '--create',
                            '--proposal-target', 'Notes/new.md', draft=self.draft)
        self.assertEqual(rejected.returncode, 2)
        (self.root / 'Notes/alias').symlink_to(self.root / 'Sources', target_is_directory=True)
        rejected = self.cli('knowledge.py', '--root', str(self.root), '--create',
                            '--proposal-target', 'Notes/alias/new.md', '--evidence', 'Sources/a.md', draft=self.draft)
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse((self.root / 'Sources/new.md').exists())

    def test_competing_entry_at_publish_is_preserved_and_temporary_is_removed(self):
        import importlib.util
        from unittest.mock import patch
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('new_note_writer', BASE / 'scripts/note_write.py')
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        packet = self.propose()
        settings = module.library.load_config(self.config)
        link = module.os.link
        def competing_link(temporary, target):
            target.write_text('Competing writer')
            link(temporary, target)
        with patch.object(module.os, 'link', side_effect=competing_link):
            with self.assertRaises(FileExistsError):
                module.save(settings, packet)
        self.assertEqual(self.target.read_text(), 'Competing writer')
        self.assertEqual(list(self.target.parent.glob('.core-note-*')), [])
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)

    def test_failed_publication_leaves_no_partial_target(self):
        import importlib.util
        from unittest.mock import patch
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('failed_new_note_writer', BASE / 'scripts/note_write.py')
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        packet = self.propose()
        settings = module.library.load_config(self.config)
        with patch.object(module.os, 'link', side_effect=OSError('Unsupported hard links')):
            with self.assertRaises(OSError):
                module.save(settings, packet)
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.target.parent.glob('.core-note-*')), [])
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)

    def test_empty_new_note_is_not_a_reviewable_proposal(self):
        result = self.cli('library.py', '--config', str(self.config), 'proposal', '--create',
                          '--target', 'Notes/new.md', '--evidence', 'Sources/a.md', draft='')
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.target.exists())

    def test_maturity_journey_binds_selected_seeds_and_originals_without_auto_promotion(self):
        import yaml
        originals = (self.root / 'Sources/a.md').read_bytes()
        for name, question in (('seed-a', 'What time was the method applied?'),
                               ('seed-b', 'Does method similarity prove effect equivalence?')):
            (self.root / f'Notes/{name}.md').write_text(
                f'---\nmaturity: seed\n---\n# Synthetic seed\n{question}\n[[Sources/a]]\n')
        seed_bytes = {p.name: p.read_bytes() for p in (self.root / 'Notes').glob('seed-*.md')}
        synthesis = ('---\nmaturity: developing\n---\n# Fictional methods synthesis\n'
                     'Emergent argument: similar method descriptions alone do not establish comparable effects.\n'
                     'Lineage: [[Notes/seed-a]], [[Notes/seed-b]], [[Sources/a]].\n'
                     'Original locator: Sources/a.md, paragraph 1; describes method only.\n'
                     'Unresolved: measurement conditions and effects are not specified.\n')
        def proposal(draft, create=False):
            args = ['--config', str(self.config), 'proposal', '--target', 'Notes/new.md']
            if create:
                args.append('--create')
            for evidence in ('Notes/seed-a.md', 'Notes/seed-b.md', 'Sources/a.md'):
                args.extend(['--evidence', evidence])
            result = self.cli('library.py', *args, draft=draft)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.packet.write_text(result.stdout)
            return json.loads(result.stdout)
        packet = proposal(synthesis, create=True)
        self.assertFalse(self.target.exists())
        self.assertEqual(len(packet['evidence']), 3)
        seed = self.root / 'Notes/seed-a.md'
        seed.write_bytes(seed_bytes['seed-a.md'] + b'Changed idea\n')
        self.assertEqual(self.write().returncode, 2)
        self.assertFalse(self.target.exists())
        seed.write_bytes(seed_bytes['seed-a.md'])
        saved = self.write()
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(self.target.read_bytes(), synthesis.encode())
        evergreen = synthesis.replace('maturity: developing', 'maturity: evergreen') + (
            'Reviewed bounded scope: this explanation concerns method descriptions, not measured outcomes.\n'
            'No new effect claim or publication permission follows from this classification.\n')
        mature_packet = proposal(evergreen)
        self.assertIn('-maturity: developing', mature_packet['diff'])
        self.assertIn('+maturity: evergreen', mature_packet['diff'])
        self.assertEqual(self.write('check').returncode, 0)
        self.assertEqual(self.target.read_bytes(), synthesis.encode())
        matured = self.write()
        self.assertEqual(matured.returncode, 0, matured.stderr)
        self.assertEqual(yaml.safe_load(self.target.read_text().split('---', 2)[1])['maturity'], 'evergreen')
        restored = self.cli('note_write.py', '--config', str(self.config), 'restore',
                            '--record', json.loads(matured.stdout)['record'])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(self.target.read_bytes(), synthesis.encode())
        self.assertEqual(originals, (self.root / 'Sources/a.md').read_bytes())
        self.assertEqual(seed_bytes, {p.name: p.read_bytes() for p in (self.root / 'Notes').glob('seed-*.md')})
        # The test supplies maturity judgments; no semantic or human approval is simulated as real.
        self.assertFalse(json.loads(matured.stdout)['human_authentication_verified'])

    def test_new_note_is_proposed_and_checked_before_first_creation(self):
        source = (self.root / 'Sources/a.md').read_bytes()
        packet = self.propose()
        self.assertFalse(self.target.exists())
        self.assertEqual(packet['target']['operation'], 'create')
        self.assertIsNone(packet['target']['base_sha256'])
        self.assertTrue(packet['target']['expected_absent'])
        self.assertIn('--- /dev/null', packet['diff'])
        self.assertFalse(packet['approval_available'])
        checked = self.write('check')
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertFalse(self.target.exists())
        saved = self.write()
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual(result['status'], 'plain_file_created')
        self.assertEqual(self.target.read_bytes(), self.draft.encode())
        self.assertFalse(result['human_authentication_verified'])
        record = json.loads(Path(result['record']).read_text())
        self.assertFalse(record['before_exists'])
        self.assertIsNone(record['before_base64'])
        self.assertEqual(record['proposal'], packet)
        self.assertEqual((self.root / 'Sources/a.md').read_bytes(), source)
        self.assertEqual(self.write().returncode, 2)
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)
        restored = self.cli('note_write.py', '--config', str(self.config), 'restore', '--record', result['record'])
        self.assertEqual(restored.returncode, 2)
        self.assertEqual(self.target.read_bytes(), self.draft.encode())
        correction = self.draft + 'A corrected fictional interpretation.\n'
        updated = self.cli('library.py', '--config', str(self.config), 'proposal',
                           '--target', 'Notes/new.md', '--evidence', 'Sources/a.md', draft=correction)
        self.assertEqual(updated.returncode, 0, updated.stderr)
        self.packet.write_text(updated.stdout)
        saved_update = self.write()
        self.assertEqual(saved_update.returncode, 0, saved_update.stderr)
        self.assertEqual(self.target.read_bytes(), correction.encode())
        update_record = json.loads(saved_update.stdout)['record']
        restored_update = self.cli('note_write.py', '--config', str(self.config), 'restore',
                                  '--record', update_record)
        self.assertEqual(restored_update.returncode, 0, restored_update.stderr)
        self.assertEqual(self.target.read_bytes(), self.draft.encode())


if __name__ == '__main__':
    unittest.main()
