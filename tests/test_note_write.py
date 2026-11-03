"""Synthetic plain-file writes; never tests or claims human authentication."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support  # noqa: F401  real temp dir for symlink-refusing helpers

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


    def test_restore_under_read_only_policy_explains_instead_of_key_error(self):
        saved = self.call('save', '--packet', str(self.packet))
        record = json.loads(saved.stdout)['record']
        self.config.write_text(json.dumps({k: v for k, v in self.settings.items()
                                           if k not in ('write_policy', 'recovery_directory')}))
        result = self.call('restore', '--record', record)
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(result.stderr.strip(), json.dumps({'error': 'recovery_directory'}))
        self.assertIn('read_only means proposal-only', result.stderr)
        self.assertIn('plain_files with an existing private recovery_directory', result.stderr)
        self.assertIn('Proposed fictional', (self.root / 'Notes/one.md').read_text())

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
            result = self.call('save', '--packet', str(self.packet))
            self.assertEqual(result.returncode, 2)
            if policy == 'canonical_engine':
                self.assertIn('existing permitted canonical writer', result.stderr)
                self.assertNotIn('plain_files', result.stderr)
            else:
                self.assertIn('read_only means proposal-only', result.stderr)
                self.assertIn('exact human confirmation', result.stderr)
            self.assertEqual(list((self.base / 'recovery').iterdir()), [])
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

    def writer(self):
        import importlib.util
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('note_write', WRITER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def rebound(self, data):
        import hashlib
        data = {k: v for k, v in data.items() if k != 'packet_sha256'}
        data['packet_sha256'] = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                                        separators=(',', ':')).encode()).hexdigest()
        return data

    def create_packet(self, draft='# New\nFictional derived note [[Sources/a]].\n'):
        result = subprocess.run([sys.executable, str(BASE / 'scripts/library.py'), '--config', str(self.config),
            'proposal', '--create', '--target', 'Notes/new.md', '--evidence', 'Sources/a.md'],
            input=draft, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_failed_replace_keeps_previous_note_and_recovery_bytes(self):
        from unittest.mock import patch
        module = self.writer()
        settings = module.library.load_config(self.config)
        original = (self.root / 'Notes/one.md').read_bytes()
        with patch.object(module.os, 'replace', side_effect=OSError('Injected replace failure')):
            with self.assertRaises(OSError):
                module.save(settings, json.loads(self.packet.read_text()))
        self.assertEqual((self.root / 'Notes/one.md').read_bytes(), original)
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)
        self.assertEqual(list((self.root / 'Notes').glob('.core-note-*')), [])

    # Custody hardening regressions.

    def test_plain_files_requires_declared_sources_layer(self):
        module = self.writer()
        original = (self.root / 'Notes/one.md').read_bytes()
        for layers in (None, {}, {'drafts': ['Notes']}):
            settings = {k: v for k, v in self.settings.items() if k != 'layers'}
            if layers is not None:
                settings['layers'] = layers
            self.config.write_text(json.dumps(settings))
            with self.assertRaisesRegex(ValueError, r'layers\.sources.*"sources": \[\]'):
                module.library.load_config(self.config)
            result = self.call('save', '--packet', str(self.packet))
            self.assertEqual(result.returncode, 2)
            self.assertIn('"sources": []', json.loads(result.stderr)['error'])
        self.assertEqual((self.root / 'Notes/one.md').read_bytes(), original)
        self.config.write_text(json.dumps({**self.settings, 'layers': {'sources': []}}))
        self.assertEqual(module.library.load_config(self.config)['layers'], {'sources': []})

    def test_note_declaring_role_source_is_refused_outside_sources_layer(self):
        note = self.root / 'Notes/one.md'
        for text, refused in (('---\nrole: source\n---\n# One\nCaptured original.\n', True),
                              ('---\nrole: [\n---\n# One\nUnparsable metadata.\n', False),
                              ('---\nrole: note\n---\n# One\nDerived note.\n', False)):
            note.write_text(text)
            result = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root),
                '--proposal-target', 'Notes/one.md', '--evidence', 'Sources/a.md'],
                input=text + 'Proposed addition.\n', capture_output=True, text=True, check=True)
            self.packet.write_text(result.stdout)
            saved = self.call('save', '--packet', str(self.packet))
            if refused:
                self.assertEqual(saved.returncode, 2)
                self.assertIn('role: source', saved.stderr)
                self.assertEqual(note.read_text(), text)
            else:
                self.assertEqual(saved.returncode, 0, saved.stderr)
                self.assertEqual(note.read_text(), text + 'Proposed addition.\n')

    def test_source_boundary_uses_filesystem_identity_not_spelling(self):
        from unittest.mock import patch
        module = self.writer()
        (self.root / 'sources').mkdir()
        (self.root / 'sources/a.md').write_text('# Same original under another spelling\n')
        original = (self.root / 'sources/a.md').read_bytes()
        result = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root),
            '--proposal-target', 'sources/a.md', '--evidence', 'Sources/a.md'],
            input='# Rewritten original\n', capture_output=True, text=True, check=True)
        packet = json.loads(result.stdout)

        def insensitive(first, second):  # Simulates APFS-style identity; Linux directories differ.
            return os.fspath(first).casefold() == os.fspath(second).casefold()
        for sources in (['Sources'], ['Sources/a.md']):
            self.config.write_text(json.dumps({**self.settings, 'authorized_paths': ['Notes', 'Sources', 'sources'],
                                               'layers': {'sources': sources}}))
            settings = module.library.load_config(self.config)
            with patch.object(module.os.path, 'samefile', side_effect=insensitive):
                with self.assertRaisesRegex(ValueError, 'immutable'):
                    module.save(settings, packet)
            self.assertEqual((self.root / 'sources/a.md').read_bytes(), original)
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_recovery_directory_inside_core_checkout_is_refused(self):
        module = self.writer()
        self.config.write_text(json.dumps({**self.settings, 'recovery_directory': str(BASE / 'tests')}))
        with self.assertRaisesRegex(ValueError, 'public repository'):
            module.library.load_config(self.config)
        self.assertEqual(self.call('save', '--packet', str(self.packet)).returncode, 2)
        self.assertEqual(list((BASE / 'tests').glob('*.json')), [])

    def test_created_note_gets_process_default_mode_and_record_stays_private(self):
        import stat
        module = self.writer()
        previous = os.umask(0o027)
        self.addCleanup(os.umask, previous)
        settings = module.library.load_config(self.config)
        saved = module.save(settings, self.create_packet())
        self.assertEqual(stat.S_IMODE((self.root / 'Notes/new.md').stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(Path(saved['record']).stat().st_mode), 0o600)

    def test_recovery_record_is_utf8_under_non_utf8_locale(self):
        (self.root / 'Notes/one.md').write_text('# Uno\nInterpretación original ñ.\n', encoding='utf-8')
        result = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root),
            '--proposal-target', 'Notes/one.md', '--evidence', 'Sources/a.md'],
            input='# Uno\nComparación propuesta ñ [Sources/a.md].\n', capture_output=True, text=True,
            check=True, encoding='utf-8')
        self.packet.write_text(result.stdout, encoding='utf-8')
        env = {k: v for k, v in os.environ.items() if k not in ('LC_ALL', 'LC_CTYPE', 'LANG', 'PYTHONUTF8')}
        env.update(PYTHONDONTWRITEBYTECODE='1', LC_ALL='C', LANG='C', PYTHONUTF8='0', PYTHONCOERCECLOCALE='0')
        saved = subprocess.run([sys.executable, str(WRITER), '--config', str(self.config), 'save',
                                '--packet', str(self.packet)], capture_output=True, text=True, timeout=5,
                               env=env, encoding='utf-8')
        self.assertEqual(saved.returncode, 0, saved.stderr)
        record = json.loads(Path(json.loads(saved.stdout)['record']).read_text(encoding='utf-8'))
        self.assertEqual(record['proposal']['draft'], '# Uno\nComparación propuesta ñ [Sources/a.md].\n')
        self.assertEqual((self.root / 'Notes/one.md').read_text(encoding='utf-8'),
                         '# Uno\nComparación propuesta ñ [Sources/a.md].\n')

    # Existing guards pinned so their removal fails the suite.

    def test_symlinked_directory_under_authorized_scope_is_refused(self):
        module = self.writer()
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'x.md').write_text('# Outside the library\n')
        original = (outside / 'x.md').read_bytes()
        (self.root / 'Notes/out').symlink_to(outside)
        import difflib
        data = json.loads(self.packet.read_text())
        data['target'] = {**data['target'], 'path': 'Notes/out/x.md', 'base_sha256': module.digest(original)}
        data['diff'] = ''.join(difflib.unified_diff(original.decode().splitlines(keepends=True),
                                                    data['draft'].splitlines(keepends=True),
                                                    fromfile='Notes/out/x.md', tofile='Notes/out/x.md (proposed)'))
        packet = self.rebound(data)
        settings = module.library.load_config(self.config)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            module.save(settings, packet)
        self.assertEqual((outside / 'x.md').read_bytes(), original)
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_evidence_changing_after_first_check_blocks_publication(self):
        from unittest.mock import patch
        module = self.writer()
        settings = module.library.load_config(self.config)
        evidence = self.root / 'Sources/a.md'
        source = evidence.read_bytes()
        real_fsync = os.fsync
        for packet, target in ((json.loads(self.packet.read_text()), self.root / 'Notes/one.md'),
                               (self.create_packet(), self.root / 'Notes/new.md')):
            before = target.read_bytes() if target.exists() else None

            def fsync_then_change_evidence(fd):  # The recovery record fsync runs after the first check.
                real_fsync(fd)
                evidence.write_text('# Fictional source\nChanged after the first check.\n')
            with patch.object(module.os, 'fsync', side_effect=fsync_then_change_evidence):
                with self.assertRaisesRegex(ValueError, 'Stale evidence'):
                    module.save(settings, packet)
            self.assertEqual(target.read_bytes() if target.exists() else None, before)
            evidence.write_bytes(source)

    def test_replace_checked_refuses_note_changed_inside_before_publish(self):
        module = self.writer()
        note = self.root / 'Notes/one.md'
        expected = note.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Note changed before save'):
            module.replace_checked(note, expected, b'replacement',
                                   before_publish=lambda: note.write_bytes(b'concurrent edit'))
        self.assertEqual(note.read_bytes(), b'concurrent edit')
        self.assertEqual(list((self.root / 'Notes').glob('.core-note-*')), [])

    def test_readback_reports_unverified_saved_bytes(self):
        from unittest.mock import patch
        module = self.writer()
        settings = module.library.load_config(self.config)
        real_replace = os.replace

        def replace_then_corrupt(src, dst):
            real_replace(src, dst)
            Path(dst).write_bytes(b'bytes differing from the draft')
        with patch.object(module.os, 'replace', side_effect=replace_then_corrupt):
            with self.assertRaisesRegex(ValueError, 'not verified'):
                module.save(settings, json.loads(self.packet.read_text()))
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)

    def test_unbound_packet_field_change_is_detected(self):
        original = (self.root / 'Notes/one.md').read_bytes()
        data = json.loads(self.packet.read_text())
        data['comment'] = 'Added after binding'
        self.packet.write_text(json.dumps(data))
        for action in ('check', 'save'):
            result = self.call(action, '--packet', str(self.packet))
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn('Packet content changed', result.stderr)
        self.assertEqual((self.root / 'Notes/one.md').read_bytes(), original)
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
