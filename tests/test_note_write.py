"""Synthetic plain-file writes; never tests or claims human authentication."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
WRITER = BASE / 'scripts/note_write.py'


class NoteWriteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='plain-notes-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'library'
        (self.root / 'Notes').mkdir(parents=True)
        (self.root / 'Sources').mkdir()
        (self.base / 'recovery').mkdir()
        (self.root / 'Notes/one.md').write_text('# One\nOriginal fictional interpretation.\n')
        (self.root / 'Sources/a.md').write_text('# Fictional source\nSynthetic paragraph only.\n')
        self.settings = {'version': 1, 'library_root': 'library',
                         'authorized_paths': ['Notes', 'Sources'],
                         'layers': {'sources': ['Sources']},
                         'write_policy': 'plain_files', 'recovery_directory': 'recovery'}
        self.config = self.base / 'personal.json'
        self.config.write_text(json.dumps(self.settings))
        result = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root),
            '--proposal-target', 'Notes/one.md', '--evidence', 'Sources/a.md'],
            input='# One\nProposed fictional comparison [Sources/a.md, paragraph 1].\n',
            capture_output=True, text=True, check=True)
        self.packet = self.base / 'proposal.json'
        self.packet.write_text(result.stdout)

    def call(self, action, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run([sys.executable, str(WRITER), '--config', str(self.config), action, *args],
                              text=True, capture_output=True, timeout=5, env=env)

    def test_plain_save_checks_version_and_restores_saved_previous_bytes(self):
        original = (self.root / 'Notes/one.md').read_bytes()
        checked = self.call('check', '--packet', str(self.packet))
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual((self.root / 'Notes/one.md').read_bytes(), original)
        saved = self.call('save', '--packet', str(self.packet))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        data = json.loads(saved.stdout)
        self.assertFalse(data['human_authentication_verified'])
        self.assertIn('Proposed fictional', (self.root / 'Notes/one.md').read_text())
        restored = self.call('restore', '--record', data['record'])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual((self.root / 'Notes/one.md').read_bytes(), original)


    def test_rehashed_packet_with_misleading_diff_is_rejected(self):
        import hashlib
        original = (self.root / 'Notes/one.md').read_bytes()
        data = json.loads(self.packet.read_text())
        data['diff'] = 'Harmless displayed change; actual draft hidden.'
        del data['packet_sha256']
        data['packet_sha256'] = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                                        separators=(',', ':')).encode()).hexdigest()
        self.packet.write_text(json.dumps(data))
        for action in ('check', 'save'):
            result = self.call(action, '--packet', str(self.packet))
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn('diff', result.stderr.lower())
        self.assertEqual((self.root / 'Notes/one.md').read_bytes(), original)
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_stale_note_or_evidence_rejected_without_overwrite(self):
        for relative in ('Notes/one.md', 'Sources/a.md'):
            path = self.root / relative
            original = path.read_bytes()
            path.write_text('Subsequent synthetic edit')
            result = self.call('save', '--packet', str(self.packet))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_text(), 'Subsequent synthetic edit')
            self.assertEqual(list((self.base / 'recovery').iterdir()), [])
            path.write_bytes(original)

    def test_default_and_managed_policies_cannot_use_plain_writer(self):
        for policy in ('read_only', 'canonical_engine'):
            self.config.write_text(json.dumps({**self.settings, 'write_policy': policy}))
            self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)
        self.config.write_text(json.dumps(self.settings))
        (self.root / '.wanderloots-llm-wiki').mkdir()
        self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)

    def test_restore_preserves_later_edits_and_replay_is_rejected(self):
        result = self.call('save', '--packet', str(self.packet))
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)['record']
        saved = (self.root / 'Notes/one.md').read_bytes()
        (self.root / 'Notes/one.md').write_text('Later human edit')
        self.assertEqual(self.call('restore', '--record', record).returncode, 2)
        self.assertEqual((self.root / 'Notes/one.md').read_text(), 'Later human edit')
        (self.root / 'Notes/one.md').write_bytes(saved)
        self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)
        self.assertEqual(self.call('restore', '--record', record).returncode, 0)
        self.assertEqual(self.call('restore', '--record', record).returncode, 2)

    def test_dangling_managed_markers_block_check_save_and_restore(self):
        saved = self.call('save', '--packet', str(self.packet))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        record = json.loads(saved.stdout)['record']
        current = (self.root / 'Notes/one.md').read_bytes()
        for name in ('.wanderloots-llm-wiki', '.private-engine-install.json'):
            marker = self.root / name
            marker.symlink_to(self.base / 'missing-engine')
            for action, flag, path in (('check', '--packet', str(self.packet)),
                                      ('save', '--packet', str(self.packet)),
                                      ('restore', '--record', record)):
                result = self.call(action, flag, path)
                self.assertEqual(result.returncode, 2)
                self.assertIn('library-permitted writer', result.stderr)
            self.assertEqual((self.root / 'Notes/one.md').read_bytes(), current)
            marker.unlink()

    def test_tampered_packet_and_out_of_scope_target_fail(self):
        import hashlib
        data = json.loads(self.packet.read_text())
        data['draft'] = 'Changed without rebinding'
        self.packet.write_text(json.dumps(data))
        self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)
        data['target']['path'] = '../outside.md'
        data['draft_sha256'] = hashlib.sha256(data['draft'].encode()).hexdigest()
        del data['packet_sha256']
        data['packet_sha256'] = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                                        separators=(',', ':')).encode()).hexdigest()
        self.packet.write_text(json.dumps(data))
        self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)

    def test_sources_and_instructions_are_not_editable(self):
        for relative in ('Sources/a.md', 'Notes/AGENTS.md', 'Notes/SKILL.md', 'Notes/CLAUDE.md'):
            path = self.root / relative
            if not path.exists():
                path.write_text('Synthetic trusted policy')
            result = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root),
                '--proposal-target', relative], input='draft', capture_output=True, text=True, check=True)
            self.packet.write_text(result.stdout)
            original = path.read_bytes()
            self.assertEqual(self.call('check', '--packet', str(self.packet)).returncode, 2)
            self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)
            self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_recovery_directory_cannot_be_inside_library(self):
        (self.root / 'Recovery').mkdir()
        self.config.write_text(json.dumps({**self.settings, 'recovery_directory': 'library/Recovery'}))
        self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)

    def test_failed_replace_keeps_previous_note_and_recovery_bytes(self):
        import importlib.util
        from unittest.mock import patch
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('note_write', WRITER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        settings = module.library.load_config(self.config)
        original = (self.root / 'Notes/one.md').read_bytes()
        with patch.object(module.os, 'replace', side_effect=OSError('Injected replace failure')):
            with self.assertRaises(OSError):
                module.save(settings, json.loads(self.packet.read_text()))
        self.assertEqual((self.root / 'Notes/one.md').read_bytes(), original)
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)
        self.assertEqual(list((self.root / 'Notes').glob('.core-note-*')), [])


if __name__ == '__main__':
    unittest.main()
