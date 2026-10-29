"""Synthetic public-interface contracts for the optional numbering profile."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class LivingSynthesisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='living-synthesis-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.library = self.base / 'library'
        (self.library / 'Notes').mkdir(parents=True)
        (self.library / 'Sources').mkdir()
        (self.base / 'recovery').mkdir()
        (self.library / 'Sources/source.md').write_text('# Source\nSynthetic evidence.\n')
        self.config = self.base / 'config.json'
        self.settings = {'version': 1, 'library_root': 'library',
                         'authorized_paths': ['Notes', 'Sources'],
                         'layers': {'sources': ['Sources']}, 'write_policy': 'plain_files',
                         'recovery_directory': 'recovery',
                         'living_synthesis': {'scopes': ['Notes'], 'history_complete': True, 'references_complete': True}}
        self.configure()
        self.packet = self.base / 'packet.json'

    def configure(self):
        self.config.write_text(json.dumps(self.settings))

    def cli(self, script, *args, draft=None):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), '--config',
                               str(self.config), *args], input=draft, text=True,
                              capture_output=True, timeout=5,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def put(self, name, text):
        (self.library / 'Notes' / (name + '.md')).write_text(text)

    def moc(self, identity, address, kind='thematic'):
        return (f'---\nid: {identity}\nrole: map\nmap_kind: {kind}\n'
                f'address: "{address}"\nformer_addresses: []\n---\n# Map\n')

    def note(self, identity, address, primary='Notes/m1.md', maturity='synthesis', extra=''):
        return (f'---\nid: {identity}\nrole: note\nmaturity: {maturity}\n'
                f'primary_moc: "{primary}"\naddress: "{address}"\n'
                f'former_addresses: []\n---\n# Argument\n{extra}')

    def propose(self, name, draft, create=True, *options):
        args = ['proposal', '--target', 'Notes/' + name + '.md',
                '--evidence', 'Sources/source.md', *options]
        if create:
            args.append('--create')
        return self.cli('library.py', *args, draft=draft)

    def prepared(self, name, draft, create=True, *options):
        result = self.propose(name, draft, create, *options)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        self.packet.write_text(result.stdout)
        return packet

    def write(self, action='save'):
        return self.cli('note_write.py', action, '--packet', str(self.packet))

    def assert_refused_without_mutation(self, result, before, cause=None):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout, '')
        error = json.loads(result.stderr)['error']
        self.assertTrue(error)
        if cause is not None:
            self.assertEqual(error, cause)
        self.assertEqual(self.snapshot(), before)

    def snapshot(self):
        return {str(p.relative_to(self.base)): p.read_bytes()
                for root in (self.library, self.base / 'recovery')
                for p in root.rglob('*') if p.is_file()}

    def test_invalid_note_maturity_is_refused(self):
        self.put('m1', self.moc('map-one', '001'))
        before = self.snapshot()
        for maturity in ('imaginary', ''):
            self.assert_refused_without_mutation(
                self.propose('invalid', self.note('invalid', '', maturity=maturity)), before,
                'Invalid note maturity')
        self.prepared('valid', self.note('valid', '', maturity='developing'))

    def test_independent_sequences_and_successive_addresses(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('m2', self.moc('map-two', '002'))
        self.put('first', self.note('note-one', '001-01'))
        draft = self.note('note-two', '', 'Notes/m1.md')
        packet = self.prepared('second', draft)
        self.assertIn('address: "001-02"', packet['draft'])
        self.assertFalse((self.library / 'Notes/second.md').exists())
        self.assertIn('address: "002-01"', self.prepared('other', self.note('note-other', '', 'Notes/m2.md'))['draft'])

    def test_seed_and_catalog_are_not_numbered(self):
        self.put('m1', self.moc('map-one', '001'))
        seed = '---\nid: seed-one\nrole: note\nmaturity: seed\n---\n# Seed\n'
        self.assertNotIn('address:', self.prepared('seed', seed)['draft'])
        catalog = '---\nid: catalog-one\nrole: map\nmap_kind: catalog\n---\n# Catalog\n'
        self.assertNotIn('address:', self.prepared('catalog', catalog)['draft'])

    def test_maturity_and_secondary_reference_preserve_identity_and_address(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('m2', self.moc('map-two', '002'))
        old = self.note('note-one', '001-01')
        self.put('one', old)
        draft = old.replace('maturity: synthesis', 'maturity: evergreen') + '[[Notes/m2]]\n'
        packet = self.prepared('one', draft, False)
        self.assertEqual(packet['draft'], draft)
        self.assertEqual(self.write().returncode, 0)
        self.assertEqual((self.library / 'Notes/one.md').read_text(), draft)

    def test_move_requires_intent_and_reserves_old_address(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('m2', self.moc('map-two', '002'))
        old = self.note('note-one', '001-01')
        self.put('one', old)
        draft = old.replace('Notes/m1.md', 'Notes/m2.md')
        before = self.snapshot()
        self.assert_refused_without_mutation(self.propose('one', draft, False), before)
        self.put('incoming', '[[Notes/one#Argument|001-01]]\n')
        packet = self.prepared('one', draft, False, '--move-primary')
        moved = next(p['draft'] for p in packet['proposals'] if p['target']['path'] == 'Notes/one.md')
        meta = yaml.safe_load(moved.split('---', 2)[1])
        self.assertEqual(meta['address'], '002-01')
        self.assertEqual(meta['former_addresses'], ['001-01'])
        self.assertEqual(meta['id'], 'note-one')
        checked = self.write('check')
        self.assertEqual(checked.returncode, 0, checked.stderr)
        saved = self.write()
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(saved.stderr, '')
        self.assertEqual((self.library / 'Notes/one.md').read_text(), moved)
        self.assertEqual((self.library / 'Notes/incoming.md').read_text(), '[[Notes/one#Argument|001-01]]\n')
        self.assertIn('[[Notes/one]]', (self.library / 'Notes/m2.md').read_text())
        following = self.prepared('next', self.note('next', '', 'Notes/m1.md'))
        self.assertEqual(yaml.safe_load(following['draft'].split('---', 2)[1])['address'], '001-02')

    def test_identity_author_and_history_loss_rejected(self):
        self.put('m1', self.moc('map-one', '001'))
        original = self.note('note-one', '001-01').replace('role: note', 'author: Ada\nrole: note')
        self.put('one', original)
        self.prepared('one', original + 'Valid change.\n', False)
        before = self.snapshot()
        for draft in (original.replace('note-one', 'note-other'),
                      original.replace('author: Ada\n', ''),
                      original.replace('former_addresses: []\n', '')):
            self.assert_refused_without_mutation(self.propose('one', draft, False), before)

    def test_collision_and_incomplete_history_are_refused(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('one', self.note('note-one', '001-01'))
        self.prepared('next', self.note('note-three', ''))
        self.put('duplicate', self.note('note-two', '001-01'))
        before = self.snapshot()
        self.assert_refused_without_mutation(self.propose('next', self.note('note-three', '')), before)
        self.put('duplicate', self.note('note-two', '001-03'))
        before = self.snapshot()
        self.assert_refused_without_mutation(self.propose('next', self.note('note-three', '')), before)

    def test_invalid_scope_and_incomplete_history_declaration_are_refused(self):
        self.put('m1', self.moc('map-one', '001'))
        self.prepared('next', self.note('note-one', ''))
        self.settings['living_synthesis']['history_complete'] = False
        self.configure()
        before = self.snapshot()
        self.assert_refused_without_mutation(self.propose('next', self.note('note-one', '')), before)
        self.settings['living_synthesis'] = {'scopes': ['../outside'], 'history_complete': True}
        self.configure()
        self.assert_refused_without_mutation(self.propose('next', self.note('note-one', '')), before)

    def test_new_scope_member_invalidates_reviewed_packet(self):
        self.put('m1', self.moc('map-one', '001'))
        self.prepared('next', self.note('note-one', ''))
        self.put('other', '---\nid: seed-other\nrole: note\nmaturity: seed\n---\n# Seed\n')
        before = self.snapshot()
        self.assert_refused_without_mutation(self.write(), before)

    def test_stale_configuration_base_and_evidence_refused(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('one', self.note('note-one', '001-01'))
        for change in ('config', 'base', 'evidence'):
            old = (self.library / 'Notes/one.md').read_bytes()
            source = self.library / 'Sources/source.md'
            source_old = source.read_bytes()
            self.prepared('one', old.decode() + 'More.\n', False)
            if change == 'config':
                self.settings['language'] = 'en'
                self.configure()
            elif change == 'base':
                (self.library / 'Notes/one.md').write_bytes(old + b'Concurrent edit\n')
            else:
                source.write_bytes(source_old + b'Changed\n')
            before = self.snapshot()
            self.assert_refused_without_mutation(self.write(), before)
            self.settings.pop('language', None)
            self.configure()
            (self.library / 'Notes/one.md').write_bytes(old)
            source.write_bytes(source_old)

    def test_plain_packet_cannot_bypass_numbered_scope(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('one', self.note('note-one', '001-01'))
        self.prepared('one', self.note('note-one', '001-01') + 'Valid change.\n', False)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/knowledge.py'), '--root',
                                 str(self.library), '--proposal-target', 'Notes/one.md'],
                                input='# Removed numbering\n', text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.packet.write_text(result.stdout)
        before = self.snapshot()
        self.assert_refused_without_mutation(self.write(), before)

    def test_read_only_and_managed_prepare_but_cannot_save(self):
        self.put('m1', self.moc('map-one', '001'))
        for policy in ('read_only', 'canonical_engine'):
            self.settings['write_policy'] = policy
            self.configure()
            self.prepared('next', self.note('note-one', ''))
            before = self.snapshot()
            self.assert_refused_without_mutation(self.write(), before)

    def test_numbered_restore_cannot_release_reservation(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('m2', self.moc('map-two', '002'))
        old = self.note('note-one', '001-01')
        self.put('one', old)
        self.prepared('one', old.replace('Notes/m1.md', 'Notes/m2.md'), False, '--move-primary')
        saved = self.write()
        self.assertEqual(saved.returncode, 0, saved.stderr)
        before = self.snapshot()
        records = json.loads(saved.stdout)['completed']
        record = next(r['record'] for r in records if r['target'] == 'Notes/one.md')
        result = self.cli('note_write.py', 'restore', '--record', record)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_coproposal_contains_full_map_and_synthesis_before_save(self):
        drafts = [{'target': 'Notes/new-map.md', 'create': True,
                   'draft': '---\nid: new-map\nrole: map\nmap_kind: thematic\n---\n# Map\n'},
                  {'target': 'Notes/new-note.md', 'create': True,
                   'draft': self.note('new-note', '', 'Notes/new-map.md')}]
        result = self.cli('library.py', 'proposal-batch', '--evidence', 'Sources/source.md',
                          draft=json.dumps(drafts))
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        self.assertEqual(len(packet['proposals']), 2)
        self.assertIn('001', packet['proposals'][0]['draft'])
        self.assertIn('001-01', packet['proposals'][1]['draft'])
        self.assertFalse((self.library / 'Notes/new-map.md').exists())
        self.assertFalse((self.library / 'Notes/new-note.md').exists())
        self.packet.write_text(result.stdout)
        self.assertEqual(self.write('check').returncode, 0)
        saved = self.write()
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(saved.stderr, '')
        self.assertEqual(json.loads(saved.stdout)['status'], 'plain_batch_saved')
        for proposal in packet['proposals']:
            self.assertEqual((self.library / proposal['target']['path']).read_text(), proposal['draft'])
        self.assertIn('[[Notes/new-note]]', (self.library / 'Notes/new-map.md').read_text())

    def test_secondary_moc_references_same_note_without_recoding(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('m2', self.moc('map-two', '002'))
        self.put('one', self.note('note-one', '001-01'))
        original = (self.library / 'Notes/one.md').read_bytes()
        self.prepared('m2', self.moc('map-two', '002') + '[[Notes/one#Argument]]\n', False)
        result = self.write()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual((self.library / 'Notes/one.md').read_bytes(), original)
        self.assertEqual(len(list((self.library / 'Notes').glob('one.md'))), 1)

    def test_move_requires_complete_references_and_preserves_headings(self):
        self.put('m1', self.moc('map-one', '001'))
        self.put('m2', self.moc('map-two', '002'))
        old = self.note('note-one', '001-01')
        self.put('one', old)
        self.put('incoming', '[[Notes/one#Argument]]\n')
        draft = old.replace('Notes/m1.md', 'Notes/m2.md')
        self.settings['living_synthesis']['references_complete'] = False
        self.configure()
        before = self.snapshot()
        self.assert_refused_without_mutation(self.propose('one', draft, False, '--move-primary'), before,
                                            'Primary moves require an explicitly complete reference scope')
        self.settings['living_synthesis']['references_complete'] = True
        self.configure()
        before = self.snapshot()
        self.assert_refused_without_mutation(
            self.propose('one', draft.replace('# Argument', '# Renamed'), False, '--move-primary'), before,
            'Unresolved or ambiguous native heading: Notes/one#Argument')

    def test_batch_preflight_collision_preserves_all_state(self):
        drafts = [{'target': 'Notes/map.md', 'create': True,
                   'draft': '---\nid: new-map\nrole: map\nmap_kind: thematic\n---\n# Route\n'},
                  {'target': 'Notes/note.md', 'create': True,
                   'draft': self.note('new-note', '', 'Notes/map.md')}]
        result = self.cli('library.py', 'proposal-batch', '--evidence', 'Sources/source.md', draft=json.dumps(drafts))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.packet.write_text(result.stdout)
        self.put('note', 'Competing content\n')
        before = self.snapshot()
        self.assert_refused_without_mutation(self.write(), before,
                                            'Numbering scope or configuration changed; review again')
        self.assertFalse((self.library / 'Notes/map.md').exists())

    def test_batch_io_failure_reports_exact_partial_state(self):
        drafts = [{'target': 'Notes/map.md', 'create': True,
                   'draft': '---\nid: new-map\nrole: map\nmap_kind: thematic\n---\n# Route\n'},
                  {'target': 'Notes/note.md', 'create': True,
                   'draft': self.note('new-note', '', 'Notes/map.md')}]
        result = self.cli('library.py', 'proposal-batch', '--evidence', 'Sources/source.md', draft=json.dumps(drafts))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.packet.write_text(result.stdout)
        # Fault injection wraps the public CLI entry point; assertions observe only its
        # output and the actual library/recovery files, not private allocator internals.
        launcher = '''import os, runpy, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
script, config, packet = sys.argv[2:]
original = os.link
def publish(source, target):
    if str(target).endswith('/note.md'):
        raise OSError('Injected second publication failure')
    return original(source, target)
sys.argv = [script, '--config', config, 'save', '--packet', packet]
with patch('os.link', side_effect=publish):
    runpy.run_path(script, run_name='__main__')
'''
        failed = subprocess.run([sys.executable, '-c', launcher, str(ROOT / 'scripts'),
                                 str(ROOT / 'scripts/note_write.py'), str(self.config), str(self.packet)],
                                capture_output=True, text=True, timeout=5,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, '')
        report = json.loads(failed.stderr)
        self.assertEqual(report['status'], 'plain_batch_partial')
        self.assertEqual(report['error'], 'Injected second publication failure')
        self.assertEqual([p['target'] for p in report['completed']], ['Notes/map.md'])
        self.assertFalse(report['human_authentication_verified'])
        self.assertEqual(len(report['recovery_records']), 2)
        self.assertTrue(all(Path(p).is_file() for p in report['recovery_records']))
        self.assertEqual((self.library / 'Notes/map.md').read_text(), json.loads(result.stdout)['proposals'][0]['draft'])
        self.assertFalse((self.library / 'Notes/note.md').exists())
        self.assertEqual(list((self.library / 'Notes').glob('.core-note-*')), [])
        self.assertEqual((self.library / 'Sources/source.md').read_text(), '# Source\nSynthetic evidence.\n')
        remaining = self.prepared('note', self.note('new-note', '', 'Notes/map.md'))
        self.assertEqual(yaml.safe_load(remaining['draft'].split('---', 2)[1])['address'], '001-01')

    def test_batch_rechecks_reservation_after_recovery_and_staging(self):
        self.put('m1', self.moc('map-one', '001'))
        drafts = [{'target': 'Notes/new.md', 'create': True, 'draft': self.note('new-note', '')}]
        prepared = self.cli('library.py', 'proposal-batch', '--evidence', 'Sources/source.md', draft=json.dumps(drafts))
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.packet.write_text(prepared.stdout)
        collision = self.library / 'Notes/collision.md'
        collision_text = self.note('competing-note', '001-01')
        map_before = (self.library / 'Notes/m1.md').read_bytes()
        launcher = '''import os, runpy, sys
from pathlib import Path
from unittest.mock import patch
scripts, config, packet, collision, text, injection = sys.argv[1:]
sys.path.insert(0, scripts)
original = os.fsync
count = 0
def persist(fd):
    global count
    original(fd)
    count += 1
    if count == int(injection):
        Path(collision).write_text(text)
sys.argv = [scripts + '/note_write.py', '--config', config, 'save', '--packet', packet]
with patch('os.fsync', side_effect=persist):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''
        for injection in (1, 2):
            with self.subTest(fsync=injection):
                result = subprocess.run([sys.executable, '-c', launcher, str(ROOT / 'scripts'),
                    str(self.config), str(self.packet), str(collision), collision_text, str(injection)],
                    capture_output=True, text=True, timeout=5,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(result.stdout, '')
                report = json.loads(result.stderr)
                self.assertEqual(report['status'], 'plain_batch_partial')
                self.assertEqual(report['completed'], [])
                self.assertEqual(report['error'], 'Numbering scope changed before publication; preserve partial work')
                self.assertFalse((self.library / 'Notes/new.md').exists())
                self.assertEqual(collision.read_text(), collision_text)
                self.assertEqual((self.library / 'Notes/m1.md').read_bytes(), map_before)
                self.assertEqual(list((self.library / 'Notes').glob('.core-note-*')), [])
                collision.unlink()

    def test_profile_eligibility_and_known_scope_boundaries(self):
        self.put('m1', self.moc('map-one', '001'))
        before = self.snapshot()
        for draft in (self.note('missing', '').replace('primary_moc: "Notes/m1.md"\n', ''),
                      self.note('seed', '001-01', maturity='seed')):
            self.assert_refused_without_mutation(self.propose('invalid', draft), before)
        (self.library / 'Other').mkdir()
        rejected = self.cli('library.py', 'proposal', '--create', '--target', 'Other/new.md',
                            '--evidence', 'Sources/source.md', draft=self.note('outside', ''))
        self.assert_refused_without_mutation(rejected, self.snapshot(), 'Selection is outside authorized_paths')
        orphan = [{'target': 'Notes/new-map.md', 'create': True,
                   'draft': '---\nid: empty-map\nrole: map\nmap_kind: thematic\n---\n# Empty\n'}]
        rejected = self.cli('library.py', 'proposal-batch', '--evidence', 'Sources/source.md', draft=json.dumps(orphan))
        self.assert_refused_without_mutation(rejected, before, 'New thematic MOC must be proposed with a retained synthesis')


if __name__ == '__main__':
    unittest.main()
