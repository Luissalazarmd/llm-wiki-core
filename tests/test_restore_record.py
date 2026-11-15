"""A restore keeps its own private record, so it can be reversed and audited. Synthetic data only."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import support  # noqa: F401  real temp dir for symlink-refusing helpers

BASE = Path(__file__).resolve().parents[1]
SCRIPTS = BASE / 'scripts'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class RestoreRecordCase(unittest.TestCase):
    profile = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='restore-record-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'library'
        (self.root / 'Notes').mkdir(parents=True)
        (self.root / 'Sources').mkdir()
        self.recovery = self.base / 'recovery'
        self.recovery.mkdir()
        (self.root / 'Sources/a.md').write_text('# Fictional source\nSynthetic paragraph only.\n')
        self.settings = {'version': 1, 'library_root': 'library', 'authorized_paths': ['Notes', 'Sources'],
                         'layers': {'sources': ['Sources']}, 'write_policy': 'plain_files',
                         'recovery_directory': 'recovery'}
        if self.profile:
            self.settings['living_synthesis'] = self.profile
        self.config = self.base / 'personal.json'
        self.configure()
        self.note = self.root / 'Notes/one.md'

    def configure(self):
        self.config.write_text(json.dumps(self.settings))

    def cli(self, script, *args, draft=None):
        return subprocess.run([sys.executable, str(SCRIPTS / script), '--config', str(self.config), *args],
                              input=draft, text=True, capture_output=True, timeout=10,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def save_update(self, draft):
        packet = self.cli('library.py', 'proposal', '--target', 'Notes/one.md', '--evidence', 'Sources/a.md',
                          draft=draft)
        self.assertEqual(packet.returncode, 0, packet.stderr)
        path = self.base / 'packet.json'
        path.write_text(packet.stdout)
        saved = self.cli('note_write.py', 'save', '--packet', str(path))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        return json.loads(saved.stdout)['record']

    def restore(self, record):
        return self.cli('note_write.py', 'restore', '--record', str(record))

    def restored(self, record):
        result = self.restore(record)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def records(self):
        return {p.name: p.read_bytes() for p in self.recovery.iterdir()}

    def module(self):
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location('note_write_restore_record', SCRIPTS / 'note_write.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class RestoreRecordTests(RestoreRecordCase):
    def setUp(self):
        super().setUp()
        self.note.write_text('# One\nOriginal fictional interpretation.\n')
        self.original = self.note.read_bytes()
        self.save_record = self.save_update('# One\nProposed fictional comparison [Sources/a.md, paragraph 1].\n')
        self.saved = self.note.read_bytes()

    def test_round_trip_returns_to_the_saved_state(self):
        first = self.restored(self.save_record)
        self.assertEqual(self.note.read_bytes(), self.original)
        second = self.restored(first['record'])
        self.assertEqual(self.note.read_bytes(), self.saved)
        self.assertEqual(second['sha256'], sha(self.saved))
        self.assertEqual(second['previous_sha256'], sha(self.original))

    def test_output_names_the_new_record_and_nothing_reaches_the_library(self):
        library_before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        result = self.restored(self.save_record)
        self.assertEqual(set(result), {'status', 'sha256', 'previous_sha256', 'record', 'restored_from',
                                       'human_authentication_verified'})
        self.assertEqual(result['status'], 'plain_file_restored')
        self.assertEqual(result['sha256'], sha(self.original))
        self.assertEqual(result['previous_sha256'], sha(self.saved))
        self.assertEqual(result['restored_from'], self.save_record)
        self.assertIs(result['human_authentication_verified'], False)
        record_path = Path(result['record'])
        self.assertEqual(record_path.parent, self.recovery.resolve())
        self.assertNotEqual(str(record_path), self.save_record)
        self.assertEqual(stat.S_IMODE(record_path.stat().st_mode), 0o600)
        self.assertEqual(len(self.records()), 2)
        self.assertEqual(sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')), library_before)
        self.assertNotIn(record_path.name, self.note.read_text())

    def test_record_holds_the_displaced_bytes_and_its_origin_without_a_proposal(self):
        source_bytes = Path(self.save_record).read_bytes()
        record = json.loads(Path(self.restored(self.save_record)['record']).read_text())
        self.assertEqual(record['format'], 'plain-note-recovery-v1')
        self.assertEqual(record['operation'], 'restore')
        self.assertEqual(record['target'], 'Notes/one.md')
        self.assertIs(record['before_exists'], True)
        self.assertEqual(base64.b64decode(record['before_base64']), self.saved)
        self.assertEqual(record['before_sha256'], sha(self.saved))
        self.assertEqual(record['after_sha256'], sha(self.original))
        self.assertEqual(record['restored_from'], {'record': Path(self.save_record).name,
                                                   'record_sha256': sha(source_bytes)})
        self.assertIs(record['numbered'], False)
        self.assertIs(record['human_authentication_verified'], False)
        self.assertNotIn('proposal', record)
        self.assertEqual(Path(self.save_record).read_bytes(), source_bytes)

    def test_a_restore_of_a_restore_is_itself_recorded_and_reversible(self):
        first = self.restored(self.save_record)
        second = self.restored(first['record'])
        third = self.restored(second['record'])
        self.assertEqual(self.note.read_bytes(), self.original)
        self.assertEqual(len({self.save_record, first['record'], second['record'], third['record']}), 4)
        self.assertEqual(len(self.records()), 4)
        chain = json.loads(Path(third['record']).read_text())['restored_from']
        self.assertEqual(chain['record'], Path(second['record']).name)
        self.assertEqual(chain['record_sha256'], sha(Path(second['record']).read_bytes()))
        # A record applies only while the note holds the version it produced.
        for spent in (second['record'], self.save_record):
            replay = self.restore(spent)
            self.assertEqual(replay.returncode, 2)
            self.assertIn('Note changed since save', json.loads(replay.stderr)['error'])
        self.assertEqual(self.note.read_bytes(), self.original)
        self.assertEqual(len(self.records()), 4)

    def test_owner_edit_after_a_restore_is_never_overwritten(self):
        first = self.restored(self.save_record)
        self.note.write_text('Later owner edit')
        before = self.records()
        for record in (first['record'], self.save_record):
            refused = self.restore(record)
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(refused.stdout, '')
            self.assertIn('Note changed since save', json.loads(refused.stderr)['error'])
        self.assertEqual(self.note.read_text(), 'Later owner edit')
        self.assertEqual(self.records(), before)

    def test_refusals_write_no_record(self):
        before = self.records()
        self.note.write_text('Later owner edit')
        self.assertEqual(self.restore(self.save_record).returncode, 2)
        self.note.write_bytes(self.saved)
        (self.root / '.wanderloots-llm-wiki').mkdir()
        self.assertEqual(self.restore(self.save_record).returncode, 2)
        self.assertEqual(self.records(), before)
        self.assertEqual(self.note.read_bytes(), self.saved)

    def test_record_write_failure_leaves_the_note_untouched(self):
        module = self.module()
        settings = module.library.load_config(self.config)
        before = self.records()

        def partial_then_fail(path, record):
            Path(path).write_text('{"incomplete":')
            raise OSError('Injected record failure')
        for failure in (partial_then_fail, OSError('Injected record failure')):
            with self.subTest(failure=failure):
                with patch.object(module, 'write_record', side_effect=failure), \
                        patch.object(module.os, 'replace', side_effect=AssertionError('must not replace')), \
                        self.assertRaises(module.RestoreError) as caught:
                    module.restore(settings, Path(self.save_record))
                result = caught.exception.result
                self.assertEqual(result['status'], 'restore_not_done')
                self.assertIs(result['note_unchanged'], True)
                self.assertIsNone(result['record'])
                self.assertIsNone(result['unused_record'])
                self.assertIn('could not be written, so the note was not replaced', result['error'])
                self.assertIs(result['human_authentication_verified'], False)
                self.assertEqual(self.note.read_bytes(), self.saved)
                self.assertEqual(self.records(), before)
                self.assertEqual(list((self.root / 'Notes').glob('.core-note-*')), [])
        # The original record still works afterwards.
        self.restored(self.save_record)
        self.assertEqual(self.note.read_bytes(), self.original)

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root ignores directory permissions')
    def test_unwritable_recovery_directory_reports_through_the_command(self):
        before = self.records()
        self.recovery.chmod(0o500)
        self.addCleanup(self.recovery.chmod, 0o700)
        result = self.restore(self.save_record)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        report = json.loads(result.stderr)
        self.assertEqual(report['status'], 'restore_not_done')
        self.assertIs(report['note_unchanged'], True)
        self.assertIsNone(report['record'])
        self.assertEqual(self.note.read_bytes(), self.saved)
        self.assertEqual(self.records(), before)

    def test_an_existing_entry_at_the_record_name_is_not_removed(self):
        module = self.module()
        settings = module.library.load_config(self.config)
        occupied = self.recovery / ('0' * 32 + '.json')
        occupied.write_text('{"someone":"else"}')

        class Fixed:
            hex = '0' * 32
        with patch.object(module.uuid, 'uuid4', return_value=Fixed()), self.assertRaises(module.RestoreError) as caught:
            module.restore(settings, Path(self.save_record))
        self.assertEqual(caught.exception.result['status'], 'restore_not_done')
        self.assertEqual(occupied.read_text(), '{"someone":"else"}')
        self.assertEqual(self.note.read_bytes(), self.saved)

    def test_replace_failure_reports_an_unchanged_note_and_removes_the_unused_record(self):
        module = self.module()
        settings = module.library.load_config(self.config)
        before = self.records()
        with patch.object(module.os, 'replace', side_effect=OSError('Injected replace failure')), \
                self.assertRaises(module.RestoreError) as caught:
            module.restore(settings, Path(self.save_record))
        result = caught.exception.result
        self.assertEqual(result['status'], 'restore_not_done')
        self.assertIs(result['note_unchanged'], True)
        self.assertIsNone(result['record'])
        self.assertIsNone(result['unused_record'])
        self.assertEqual(result['restored_from'], self.save_record)
        self.assertIn('The note was not replaced and keeps the bytes it had', result['error'])
        self.assertIn('Injected replace failure', result['error'])
        self.assertIn('original record remains usable', result['error'])
        self.assertEqual(self.note.read_bytes(), self.saved)
        self.assertEqual(self.records(), before)
        self.assertEqual(list((self.root / 'Notes').glob('.core-note-*')), [])
        self.restored(self.save_record)
        self.assertEqual(self.note.read_bytes(), self.original)

    def test_replace_failure_names_a_record_that_could_not_be_removed(self):
        module = self.module()
        settings = module.library.load_config(self.config)
        with patch.object(module.os, 'replace', side_effect=OSError('Injected replace failure')), \
                patch.object(module.Path, 'unlink', side_effect=OSError('Injected unlink failure')), \
                self.assertRaises(module.RestoreError) as caught:
            module.restore(settings, Path(self.save_record))
        result = caught.exception.result
        self.assertEqual(result['status'], 'restore_not_done')
        self.assertIs(result['note_unchanged'], True)
        self.assertIsNone(result['record'])
        self.assertTrue(Path(result['unused_record']).is_file())
        self.assertIn('could not be removed', result['error'])
        self.assertEqual(self.note.read_bytes(), self.saved)

    def test_owner_edit_during_the_restore_is_kept_and_leaves_no_record(self):
        module = self.module()
        settings = module.library.load_config(self.config)
        before = self.records()
        real = module.write_record

        def write_then_edit(path, record):
            real(path, record)
            self.note.write_text('Edit made while restoring')
        with patch.object(module, 'write_record', side_effect=write_then_edit), \
                self.assertRaises(module.RestoreError) as caught:
            module.restore(settings, Path(self.save_record))
        self.assertEqual(caught.exception.result['status'], 'restore_not_done')
        self.assertIn('Note changed before save', caught.exception.result['error'])
        self.assertEqual(self.note.read_text(), 'Edit made while restoring')
        self.assertEqual(self.records(), before)

    def test_unverified_readback_keeps_and_names_the_record(self):
        module = self.module()
        settings = module.library.load_config(self.config)
        real_replace = os.replace

        def replace_then_corrupt(src, dst):
            real_replace(src, dst)
            Path(dst).write_bytes(b'bytes differing from the restored ones')
        with patch.object(module.os, 'replace', side_effect=replace_then_corrupt), \
                self.assertRaises(module.RestoreError) as caught:
            module.restore(settings, Path(self.save_record))
        result = caught.exception.result
        self.assertEqual(result['status'], 'restore_unverified')
        self.assertIs(result['note_unchanged'], False)
        record = json.loads(Path(result['record']).read_text())
        self.assertEqual(base64.b64decode(record['before_base64']), self.saved)
        self.assertEqual(len(self.records()), 2)

    def test_failure_reports_exit_two_with_json_on_stderr(self):
        script = ('import json, sys; from pathlib import Path; from unittest.mock import patch\n'
                  f'sys.path.insert(0, {str(SCRIPTS)!r}); import note_write\n'
                  f'sys.argv = ["note_write.py", "--config", {str(self.config)!r}, "restore", "--record", '
                  f'{self.save_record!r}]\n'
                  'with patch.object(note_write.os, "replace", side_effect=OSError("Injected")):\n'
                  '    raise SystemExit(note_write.main())\n')
        result = subprocess.run([sys.executable, '-c', script], text=True, capture_output=True, timeout=10,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, '')
        report = json.loads(result.stderr)
        self.assertEqual(report['status'], 'restore_not_done')
        self.assertIs(report['note_unchanged'], True)
        self.assertEqual(self.note.read_bytes(), self.saved)

    def test_restore_record_from_another_library_or_altered_bytes_is_refused(self):
        first = self.restored(self.save_record)
        path = Path(first['record'])
        genuine = path.read_text()
        before_note = self.note.read_bytes()
        for change in ({'library_root': str(self.base / 'elsewhere')},
                       {'before_base64': base64.b64encode(b'other bytes').decode()},
                       {'numbered': 'yes'}):
            with self.subTest(change=change):
                path.write_text(json.dumps({**json.loads(genuine), **change}))
                self.assertEqual(self.restore(path).returncode, 2)
                self.assertEqual(self.note.read_bytes(), before_note)
        path.write_text(genuine)
        self.restored(path)
        self.assertEqual(self.note.read_bytes(), self.saved)


class NumberedRestoreRecordTests(RestoreRecordCase):
    profile = {'scopes': ['Notes'], 'history_complete': True, 'references_complete': True}

    def setUp(self):
        super().setUp()
        (self.root / 'Notes/m1.md').write_text('---\nid: map-one\nrole: map\nmap_kind: thematic\n'
                                               'address: "001"\nformer_addresses: []\n---\n# Map\n')
        self.note.write_text('---\nid: note-one\nrole: note\nmaturity: synthesis\nprimary_moc: "Notes/m1.md"\n'
                             'address: "001-01"\nformer_addresses: []\n---\n# Argument\n')
        self.original = self.note.read_bytes()
        self.save_record = self.save_update(self.original.decode() + 'More argument.\n')
        self.saved = self.note.read_bytes()

    def test_numbered_round_trip_carries_the_binding_forward(self):
        first = self.restored(self.save_record)
        self.assertEqual(self.note.read_bytes(), self.original)
        self.assertIs(json.loads(Path(first['record']).read_text())['numbered'], True)
        second = self.restored(first['record'])
        self.assertEqual(self.note.read_bytes(), self.saved)
        self.assertIs(json.loads(Path(second['record']).read_text())['numbered'], True)

    def test_reversal_is_refused_when_the_numbering_profile_is_gone(self):
        first = self.restored(self.save_record)
        profile = self.settings.pop('living_synthesis')
        self.configure()
        before = self.records()
        refused = self.restore(first['record'])
        self.assertEqual(refused.returncode, 2)
        self.assertIn('Numbering profile or scope changed', json.loads(refused.stderr)['error'])
        self.assertEqual(self.note.read_bytes(), self.original)
        self.assertEqual(self.records(), before)
        self.settings['living_synthesis'] = profile
        self.configure()
        self.restored(first['record'])
        self.assertEqual(self.note.read_bytes(), self.saved)

    def test_reversal_cannot_release_or_replace_an_address_in_either_direction(self):
        first = self.restored(self.save_record)
        path = Path(first['record'])
        genuine = json.loads(path.read_text())
        before_note = self.note.read_bytes()
        for old, new in (('address: "001-01"', 'address: "001-02"'), ('id: note-one', 'id: other'),
                         ('former_addresses: []\n', '')):
            with self.subTest(change=new):
                altered = self.saved.replace(old.encode(), new.encode())
                path.write_text(json.dumps({**genuine, 'before_base64': base64.b64encode(altered).decode(),
                                            'before_sha256': sha(altered)}))
                before = self.records()
                refused = self.restore(path)
                self.assertEqual(refused.returncode, 2)
                self.assertIn('Restore would release or replace', json.loads(refused.stderr)['error'])
                self.assertEqual(self.note.read_bytes(), before_note)
                self.assertEqual(self.records(), before)

    def test_scope_change_between_record_and_replace_is_refused_and_leaves_no_record(self):
        module = self.module()
        settings = module.library.load_config(self.config)
        before = self.records()
        real = module.write_record

        def write_then_collide(path, record):
            real(path, record)
            (self.root / 'Notes/two.md').write_bytes(self.original.replace(b'id: note-one', b'id: note-two'))
        with patch.object(module, 'write_record', side_effect=write_then_collide), \
                self.assertRaises(module.RestoreError) as caught:
            module.restore(settings, Path(self.save_record))
        self.assertEqual(caught.exception.result['status'], 'restore_not_done')
        self.assertIs(caught.exception.result['note_unchanged'], True)
        self.assertEqual(self.note.read_bytes(), self.saved)
        self.assertEqual(self.records(), before)


if __name__ == '__main__':
    unittest.main()
