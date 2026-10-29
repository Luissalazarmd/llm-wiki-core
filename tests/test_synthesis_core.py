"""Public CLI tests for the bounded existing-MOC numbering slice."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class SynthesisCore(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'lib'
        (self.root / 'Notes').mkdir(parents=True)
        (self.root / 'Sources').mkdir()
        (self.base / 'recovery').mkdir()
        (self.root / 'Sources/e.md').write_text('# Evidence\n')
        self.settings = {'version': 1, 'library_root': 'lib', 'authorized_paths': ['Notes', 'Sources'],
                         'layers': {'sources': ['Sources']}, 'write_policy': 'plain_files',
                         'recovery_directory': 'recovery',
                         'living_synthesis': {'scopes': ['Notes'], 'history_complete': True}}
        self.config = self.base / 'config.json'
        self.packet = self.base / 'packet.json'
        self.configure()
        for n in (1, 2):
            (self.root / f'Notes/m{n}.md').write_text(
                f'---\nid: map-{n}\nrole: map\nmap_kind: thematic\naddress: "{n:03}"\nformer_addresses: []\n---\n# Map\n')

    def configure(self):
        self.config.write_text(json.dumps(self.settings))

    def cli(self, script, *args, draft=None):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), '--config', str(self.config), *args],
                              input=draft, text=True, capture_output=True, timeout=5,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def propose(self, name, draft, create=True):
        args = ['proposal', '--target', f'Notes/{name}.md', '--evidence', 'Sources/e.md']
        if create:
            args.append('--create')
        result = self.cli('library.py', *args, draft=draft)
        if result.returncode == 0:
            self.packet.write_text(result.stdout)
        return result

    def save(self, action='save'):
        return self.cli('note_write.py', action, '--packet', str(self.packet))

    def note(self, identity, moc=1):
        return f'---\nid: {identity}\nrole: note\nmaturity: developing\nprimary_moc: Notes/m{moc}.md\n---\n# Argument\n'

    def meta(self, draft):
        return yaml.safe_load(draft.split('---', 2)[1])

    def test_successive_save_and_maturity(self):
        for name, moc, address in [('a', 1, '001-01'), ('b', 1, '001-02'), ('c', 2, '002-01')]:
            result = self.propose(name, self.note(name, moc))
            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(self.meta(packet['draft'])['address'], address)
            self.assertEqual(self.save('check').returncode, 0)
            self.assertEqual(self.save().returncode, 0)
        old = (self.root / 'Notes/a.md').read_text()
        result = self.propose('a', old.replace('developing', 'evergreen') + '[[Notes/m2]]\n', False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.meta(json.loads(result.stdout)['draft'])['address'], '001-01')
        self.assertEqual(self.save().returncode, 0)
        self.assertEqual(self.meta((self.root / 'Notes/a.md').read_text())['id'], 'a')

    def test_seeds_catalog_and_stale_scope(self):
        for name, metadata in [('seed', 'role: note\nmaturity: seed'), ('catalog', 'role: map\nmap_kind: catalog'),
                               ('map', 'role: map')]:
            result = self.propose(name, f'---\nid: {name}\n{metadata}\n---\n# X\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('address', self.meta(json.loads(result.stdout)['draft']))
            self.assertEqual(self.save().returncode, 0)
        rejected = self.propose('wrong', self.note('wrong').replace('Notes/m1.md', 'Notes/catalog.md'))
        self.assertEqual(rejected.returncode, 2)
        result = self.propose('next', self.note('next'))
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.root / 'Notes/other.md').write_text('---\nid: other\nrole: note\nmaturity: developing\nprimary_moc: Notes/m1.md\naddress: "001-01"\nformer_addresses: []\n---\n# X\n')
        before = {p.name: p.read_bytes() for p in (self.root / 'Notes').iterdir()}
        recovery = set((self.base / 'recovery').iterdir())
        for action in ('check', 'save'):
            self.assertEqual(self.save(action).returncode, 2)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / 'Notes').iterdir()})
        self.assertEqual(recovery, set((self.base / 'recovery').iterdir()))
        result = self.propose('next', self.note('next').replace('id: next', 'id: other'))
        self.assertEqual(result.returncode, 2)

    def test_refusals_and_restore(self):
        result = self.propose('a', self.note('a'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.save().returncode, 0)
        path = self.root / 'Notes/a.md'
        old = path.read_text()
        recovery = set((self.base / 'recovery').iterdir())
        for draft in (old.replace('id: a', 'id: changed'),
                      old.replace('Notes/m1.md', 'Notes/m2.md'),
                      old.replace('former_addresses: []\n', '')):
            rejected = self.propose('a', draft, False)
            self.assertEqual(rejected.returncode, 2, rejected.stdout)
        self.assertEqual(path.read_text(), old)
        self.assertEqual(set((self.base / 'recovery').iterdir()), recovery)
        update = self.propose('a', old + 'More argument.\n', False)
        self.assertEqual(update.returncode, 0, update.stderr)
        saved = self.save()
        self.assertEqual(saved.returncode, 0, saved.stderr)
        profile = self.settings.pop('living_synthesis')
        self.configure()
        refused = self.cli('note_write.py', 'restore', '--record', json.loads(saved.stdout)['record'])
        self.assertEqual(refused.returncode, 2)
        self.settings['living_synthesis'] = profile
        self.configure()
        restored = self.cli('note_write.py', 'restore', '--record', json.loads(saved.stdout)['record'])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(path.read_text(), old)
        (self.root / 'Notes/gap.md').write_text(old.replace('id: a', 'id: gap').replace('001-01', '001-03'))
        rejected = self.propose('new', self.note('new'))
        self.assertEqual(rejected.returncode, 2, rejected.stdout)
        (self.root / 'Notes/gap.md').write_text(old.replace('id: a', 'id: gap'))
        rejected = self.propose('new', self.note('new'))
        self.assertEqual(rejected.returncode, 2, rejected.stdout)

    def test_plain_packet_cannot_bypass_scope(self):
        result = self.propose('a', self.note('a'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.save().returncode, 0)
        path = self.root / 'Notes/a.md'
        old = path.read_bytes()
        recovery = set((self.base / 'recovery').iterdir())
        packet = subprocess.run([sys.executable, str(ROOT / 'scripts/knowledge.py'), '--root', str(self.root),
                                 '--proposal-target', 'Notes/a.md'], input='# Unnumbered\n', text=True,
                                capture_output=True, timeout=5,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(packet.returncode, 0, packet.stderr)
        self.packet.write_text(packet.stdout)
        self.assertEqual(self.save().returncode, 2)
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(set((self.base / 'recovery').iterdir()), recovery)

    def test_plain_compatibility(self):
        del self.settings['living_synthesis']
        self.configure()
        result = self.propose('plain', '# Plain\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.save().returncode, 0)


if __name__ == '__main__':
    unittest.main()
