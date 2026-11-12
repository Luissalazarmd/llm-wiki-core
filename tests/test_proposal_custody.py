"""Parked proposals: custody in the declared proposals layer, never acceptance or a human decision."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support  # noqa: F401  real temp dir for symlink-refusing helpers

BASE = Path(__file__).resolve().parents[1]
TEXT = ('---\nrole: note\nmaturity: evergreen\n---\n# Sombra\n\n## Texto propuesto\n\n'
        'Texto ficticio del especialista, sin revisar.\nÚltima línea sin salto final')


class ProposalCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='proposal-custody-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'library'
        for folder in ('Raw/Sources', 'Review/Inbox', 'Review/Other', 'Wiki/Notes'):
            (self.root / folder).mkdir(parents=True)
        (self.base / 'recovery').mkdir()
        (self.root / 'Raw/Sources/a.md').write_text('# Fictional source\nSynthetic paragraph only.\n')
        (self.root / 'Wiki/Notes/one.md').write_text('# One\nFictional retained note.\n')
        self.settings = {'version': 1, 'library_root': 'library',
                         'authorized_paths': ['Raw', 'Review', 'Wiki'],
                         'layers': {'sources': ['Raw'], 'proposals': ['Review/Inbox'], 'knowledge': ['Wiki']},
                         'write_policy': 'plain_files', 'recovery_directory': 'recovery'}
        self.config = self.base / 'library.json'
        self.configure()

    def configure(self, **changes):
        self.config.write_text(json.dumps({**self.settings, **changes}))

    def run_script(self, script, *args, stdin=None):
        return subprocess.run([sys.executable, str(BASE / 'scripts' / script), '--config', str(self.config), *args],
                              input=stdin, text=True, capture_output=True, timeout=10,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def prepare(self, target='Review/Inbox/sombra.md', text=TEXT, *extra):
        return self.run_script('library.py', 'proposal', '--park', '--target', target,
                               '--origin', 'agente: lector', '--conversation', 'hilo-ficticio-7',
                               '--proposed-target', 'Wiki/Notes/sombra.md', '--received', '2026-11-11',
                               *extra, stdin=text)

    def packet_file(self, data, name='packet.json'):
        path = self.base / name
        path.write_text(data if isinstance(data, str) else json.dumps(data))
        return path

    def write(self, action, packet):
        return self.run_script('note_write.py', action, '--packet', str(self.packet_file(packet)))

    @staticmethod
    def rehash(packet):
        packet = {k: v for k, v in packet.items() if k != 'packet_sha256'}
        packet['packet_sha256'] = hashlib.sha256(json.dumps(
            packet, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        return packet

    def retarget(self, packet, target):
        packet = json.loads(json.dumps(packet))
        packet['target']['path'] = target
        packet['diff'] = packet['diff'].replace('Review/Inbox/sombra.md (proposed)', target + ' (proposed)')
        return self.rehash(packet)

    def with_draft(self, packet, draft):
        import difflib
        packet = json.loads(json.dumps(packet))
        packet['draft'] = draft
        packet['draft_sha256'] = hashlib.sha256(draft.encode()).hexdigest()
        packet['diff'] = ''.join(difflib.unified_diff([], draft.splitlines(keepends=True), fromfile='/dev/null',
                                                      tofile=packet['target']['path'] + ' (proposed)'))
        return self.rehash(packet)

    def snapshot(self, *folders):
        return {str(p): p.read_bytes() for folder in folders
                for p in sorted((self.root / folder).rglob('*')) if p.is_file()}

    def parked(self):
        prepared = self.prepare()
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        saved = self.write('save', prepared.stdout)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        return json.loads(prepared.stdout), json.loads(saved.stdout)

    def test_parking_keeps_literal_text_without_evidence_or_any_decision(self):
        kept = self.snapshot('Raw', 'Wiki')
        packet, result = self.parked()
        self.assertEqual(packet['status'], 'prepared_not_approved')
        self.assertEqual(packet['target']['operation'], 'park')
        self.assertEqual(packet['evidence'], [])
        self.assertEqual(result['status'], 'proposal_parked')
        self.assertIs(result['custody_only'], True)
        self.assertIs(result['accepted'], False)
        self.assertIs(result['human_authentication_verified'], False)
        saved = (self.root / 'Review/Inbox/sombra.md').read_text()
        self.assertTrue(saved.endswith('\n## Texto propuesto\n\n' + TEXT))
        import yaml
        front = yaml.safe_load(saved.split('---\n', 2)[1])
        self.assertEqual(front, {'proposal_status': 'pending', 'origin': 'agente: lector',
                                 'conversation': 'hilo-ficticio-7', 'received': '2026-11-11',
                                 'proposed_target': 'Wiki/Notes/sombra.md',
                                 'text_sha256': hashlib.sha256(TEXT.encode()).hexdigest()})
        self.assertIn('Custodia, no aceptación', saved)
        self.assertEqual(self.snapshot('Raw', 'Wiki'), kept)
        self.assertFalse((self.root / 'Wiki/Notes/sombra.md').exists())
        record = json.loads(Path(result['record']).read_text())
        self.assertEqual(record['proposal']['custody'], 'literal_proposal_not_accepted')
        self.assertIs(record['before_exists'], False)

    def test_english_library_uses_english_labels(self):
        self.configure(language='en')
        prepared = self.prepare()
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(self.write('save', prepared.stdout).returncode, 0)
        saved = (self.root / 'Review/Inbox/sombra.md').read_text()
        self.assertTrue(saved.endswith('\n## Proposed text\n\n' + TEXT))
        self.assertIn('Custody, not acceptance', saved)

    def test_library_evidence_is_bound_and_external_statements_stay_unverified(self):
        prepared = self.prepare('Review/Inbox/sombra.md', TEXT, '--evidence', 'Raw/Sources/a.md',
                                '--external-evidence', 'doi:10.0000/ficticio v2')
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        packet = json.loads(prepared.stdout)
        source = hashlib.sha256((self.root / 'Raw/Sources/a.md').read_bytes()).hexdigest()
        self.assertEqual(packet['evidence'], [{'path': 'Raw/Sources/a.md', 'sha256': source}])
        import yaml
        front = yaml.safe_load(packet['draft'].split('---\n', 2)[1])
        self.assertEqual(front['evidence'], [{'path': 'Raw/Sources/a.md', 'sha256': source},
                                             {'reference': 'doi:10.0000/ficticio v2', 'verified': 'no'}])
        (self.root / 'Raw/Sources/a.md').write_text('# Fictional source\nChanged afterwards.\n')
        refused = self.write('save', packet)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('Stale evidence', refused.stderr)
        self.assertEqual(list((self.root / 'Review/Inbox').iterdir()), [])

    def test_preparation_refuses_every_target_outside_the_proposals_layer(self):
        kept = self.snapshot('Raw', 'Review', 'Wiki')
        for target, reason in (('Wiki/Notes/sombra.md', 'layers.proposals'),
                               ('Wiki/Notes/one.md', 'already exists'),
                               ('Review/Other/sombra.md', 'layers.proposals'),
                               ('Review/sombra.md', 'layers.proposals'),
                               ('Raw/Sources/sombra.md', 'layers.proposals'),
                               ('Review/Inbox/../../Wiki/Notes/sombra.md', 'safe relative'),
                               ('Home.md', 'authorized_paths')):
            with self.subTest(target=target):
                refused = self.prepare(target)
                self.assertEqual(refused.returncode, 2, refused.stdout)
                self.assertEqual(refused.stdout, '')
                self.assertIn(reason, refused.stderr)
        self.assertEqual(self.snapshot('Raw', 'Review', 'Wiki'), kept)

    def test_writer_refuses_a_custody_packet_aimed_outside_the_proposals_layer(self):
        packet = json.loads(self.prepare().stdout)
        kept = self.snapshot('Raw', 'Review', 'Wiki')
        for target, reason in (('Wiki/Notes/sombra.md', 'layers.proposals'),
                               ('Review/Other/sombra.md', 'layers.proposals'),
                               ('Raw/Sources/sombra.md', 'immutable')):
            for action in ('check', 'save'):
                with self.subTest(target=target, action=action):
                    refused = self.write(action, self.retarget(packet, target))
                    self.assertEqual(refused.returncode, 2, refused.stdout)
                    self.assertIn(reason, refused.stderr)
        self.assertEqual(self.snapshot('Raw', 'Review', 'Wiki'), kept)
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_wiki_creation_without_evidence_gains_no_exception(self):
        packet = json.loads(self.prepare().stdout)
        for target in ('Wiki/Notes/sombra.md', 'Review/Inbox/sombra.md'):
            plain = self.retarget(packet, target)
            plain['target']['operation'] = 'create'
            for candidate in (self.rehash(plain),
                              self.rehash({k: v for k, v in plain.items() if k != 'custody'})):
                refused = self.write('save', candidate)
                self.assertEqual(refused.returncode, 2, refused.stdout)
        for marker in (None, 'accepted'):
            changed = {k: v for k, v in packet.items() if k != 'custody'}
            if marker:
                changed['custody'] = marker
            unmarked = self.write('save', self.rehash(changed))
            self.assertEqual(unmarked.returncode, 2)
            self.assertIn('custody packet', unmarked.stderr)
        reviewed = self.run_script('library.py', 'proposal', '--create', '--target', 'Wiki/Notes/sombra.md',
                                   '--evidence', 'Raw/Sources/a.md', stdin='# Sombra\n')
        mislabeled = json.loads(reviewed.stdout)
        mislabeled['custody'] = packet['custody']
        refused = self.write('save', self.rehash(mislabeled))
        self.assertEqual(refused.returncode, 2)
        self.assertIn('custody packet', refused.stderr)
        created = self.run_script('library.py', 'proposal', '--create', '--target', 'Wiki/Notes/sombra.md',
                                  stdin='# Sombra\n')
        self.assertEqual(created.returncode, 2)
        self.assertIn('explicit evidence', created.stderr)
        self.assertEqual(sorted(p.name for p in (self.root / 'Wiki/Notes').iterdir()), ['one.md'])
        self.assertEqual(list((self.root / 'Review/Inbox').iterdir()), [])

    def test_parking_never_overwrites(self):
        late = json.loads(self.prepare().stdout)
        self.parked()
        first = (self.root / 'Review/Inbox/sombra.md').read_bytes()
        again = self.prepare('Review/Inbox/sombra.md', 'Otro texto ficticio.\n')
        self.assertEqual(again.returncode, 2)
        self.assertIn('already exists', again.stderr)
        for candidate in (late, self.with_draft(late, late['draft'].replace('sin revisar', 'cambiado'))):
            refused = self.write('save', candidate)
            self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertEqual((self.root / 'Review/Inbox/sombra.md').read_bytes(), first)
        self.assertEqual(list((self.root / 'Review/Inbox').glob('.core-note-*')), [])

    def test_custody_accepts_only_the_pending_literal_format(self):
        packet = json.loads(self.prepare().stdout)
        draft = packet['draft']
        variants = {
            'status': draft.replace('proposal_status: pending', 'proposal_status: accepted'),
            'pending': draft.replace('proposal_status: pending', 'proposal_status: approved'),
            'role': draft.replace('proposal_status: pending', 'proposal_status: pending\nrole: note'),
            'review': draft.replace('proposal_status: pending', 'proposal_status: pending\nreview: human'),
            'bound text': draft.replace('sin revisar', 'ya revisado'),
            'origin': draft.replace('origin: "agente: lector"\n', ''),
            'format': TEXT,
            'source': draft.replace('proposal_status: pending', 'proposal_status: pending\nrole: source'),
        }
        for reason, changed in variants.items():
            with self.subTest(reason=reason):
                self.assertNotEqual(changed, draft)
                refused = self.write('save', self.with_draft(packet, changed))
                self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertEqual(list((self.root / 'Review/Inbox').iterdir()), [])
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_parking_fields_are_single_line_and_need_the_park_flag(self):
        for flag, value in (('--origin', 'agente\nrole: note'), ('--proposed-target', ' '),
                            ('--received', 'mañana')):
            refused = self.prepare('Review/Inbox/sombra.md', TEXT, flag, value)
            self.assertEqual(refused.returncode, 2, refused.stdout)
        empty = self.prepare('Review/Inbox/sombra.md', ' \n')
        self.assertEqual(empty.returncode, 2)
        loose = self.run_script('library.py', 'proposal', '--target', 'Wiki/Notes/one.md',
                                '--origin', 'agente: lector', stdin='# One\n')
        self.assertEqual(loose.returncode, 2)
        self.assertIn('--park', loose.stderr)
        mixed = self.prepare('Review/Inbox/sombra.md', TEXT, '--create')
        self.assertEqual(mixed.returncode, 2)

    def test_layer_declaration_must_be_unmistakable(self):
        (self.root / 'Review/Inbox/kept.md').write_text('# Kept\n')
        cases = {
            'explicit layers.sources and layers.knowledge': {'sources': ['Raw'], 'proposals': ['Review/Inbox']},
            'overlap layers.knowledge': {'sources': ['Raw'], 'knowledge': ['Wiki'], 'proposals': ['Wiki/Notes']},
            'must not overlap layers.knowledge': {'sources': ['Raw'], 'knowledge': ['Wiki/Notes'],
                                                  'proposals': ['Wiki']},
            'overlap layers.sources': {'sources': ['Raw'], 'knowledge': ['Wiki'], 'proposals': ['Raw/Sources']},
            'exact existing directories': {'sources': ['Raw'], 'knowledge': ['Wiki'],
                                           'proposals': ['Review/Inbox/kept.md']},
            'exact existing directories ': {'sources': ['Raw'], 'knowledge': ['Wiki'],
                                            'proposals': ['Review/Inbox/']},
        }
        for reason, layers in cases.items():
            with self.subTest(reason=reason):
                self.configure(layers=layers)
                refused = self.prepare()
                self.assertEqual(refused.returncode, 2, refused.stdout)
                self.assertIn(reason.strip(), refused.stderr)
        self.configure(layers={'sources': ['Raw'], 'knowledge': ['Wiki']})
        undeclared = self.prepare()
        self.assertEqual(undeclared.returncode, 2)
        self.assertIn('layers.proposals', undeclared.stderr)

    def test_symlinked_knowledge_folder_cannot_be_declared_as_proposals(self):
        alias = self.root / 'Review/Alias'
        try:
            os.symlink(self.root / 'Wiki/Notes', alias)
        except OSError:
            self.skipTest('symlinks unavailable')
        self.configure(layers={'sources': ['Raw'], 'knowledge': ['Wiki'], 'proposals': ['Review/Alias']})
        refused = self.prepare('Review/Alias/sombra.md')
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(sorted(p.name for p in (self.root / 'Wiki/Notes').iterdir()), ['one.md'])

    def test_read_only_policy_parks_nothing(self):
        packet = json.loads(self.prepare().stdout)
        self.configure(write_policy='read_only')
        refused = self.write('save', packet)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('proposal-only', refused.stderr)
        self.assertEqual(list((self.root / 'Review/Inbox').iterdir()), [])

    def close(self, draft):
        prepared = self.run_script('library.py', 'proposal', '--target', 'Review/Inbox/sombra.md', stdin=draft)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        return self.write('save', prepared.stdout)

    def test_closing_keeps_origin_text_and_history(self):
        self.parked()
        path = self.root / 'Review/Inbox/sombra.md'
        pending = path.read_text()
        history = '- 2026-11-11 · pendiente · recibida de agente: lector\n'
        self.assertIn(history, pending)
        closed = pending.replace('proposal_status: pending', 'proposal_status: rejected').replace(
            history, history + '- 2026-11-12 · rechazada · decisión ficticia de la fixture\n')
        refusals = {
            'exact proposed text': closed.replace('sin revisar', 'revisado'),
            'exact proposed text ': closed.replace('origin: "agente: lector"', 'origin: "persona"'),
            'history lines': closed.replace(history, ''),
            'stays a parked proposal': closed.replace('proposal_status: rejected', 'proposal_status: approved'),
            'stays a parked proposal ': '# Sombra\nNota ordinaria que borra la propuesta.\n',
        }
        for reason, draft in refusals.items():
            with self.subTest(reason=reason):
                refused = self.close(draft)
                self.assertEqual(refused.returncode, 2, refused.stdout)
                self.assertIn(reason.strip(), refused.stderr)
                self.assertEqual(path.read_text(), pending)
        saved = self.close(closed)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual(result['status'], 'plain_file_saved')
        self.assertTrue(path.read_text().endswith('\n## Texto propuesto\n\n' + TEXT))
        restored = self.run_script('note_write.py', 'restore', '--record', result['record'])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(path.read_text(), pending)

    def test_map_reports_the_declared_proposals_layer_only_when_declared(self):
        mapped = self.run_script('library.py', 'map', '--scope', 'Review')
        self.assertEqual(mapped.returncode, 0, mapped.stderr)
        layers = {item['layer']: item for item in json.loads(mapped.stdout)['layer_proposal']}
        self.assertEqual(layers['proposals']['paths'], ['Review/Inbox'])
        self.assertEqual(layers['proposals']['status'], 'declared_not_verified')
        self.configure(layers={'sources': ['Raw']})
        mapped = self.run_script('library.py', 'map', '--scope', 'Review')
        self.assertEqual([item['layer'] for item in json.loads(mapped.stdout)['layer_proposal']],
                         ['sources', 'drafts', 'knowledge'])


if __name__ == '__main__':
    unittest.main()
