"""Owner-authored seeds: a declared authorship stands in for evidence, for a new seed only."""
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
SEED = ('---\nrole: note\nmaturity: seed\norigin: owner\nconversation: "sesión ficticia 1"\n---\n'
        '# Idea ficticia\n\nEl módulo ficticio A es el más importante del proyecto ficticio.\n'
        'Última línea sin salto final')


class OwnerSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='owner-seed-')
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

    def prepare(self, target='Wiki/Notes/idea.md', text=SEED, *extra, flags=('--create', '--owner-authored')):
        return self.run_script('library.py', 'proposal', *flags, '--target', target, *extra, stdin=text)

    def write(self, action, packet):
        path = self.base / 'packet.json'
        path.write_text(packet if isinstance(packet, str) else json.dumps(packet))
        return self.run_script('note_write.py', action, '--packet', str(path))

    @staticmethod
    def rehash(packet):
        packet = {k: v for k, v in packet.items() if k != 'packet_sha256'}
        packet['packet_sha256'] = hashlib.sha256(json.dumps(
            packet, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        return packet

    def with_draft(self, packet, draft, target=None):
        import difflib
        packet = json.loads(json.dumps(packet))
        packet['target']['path'] = target or packet['target']['path']
        packet['draft'] = draft
        packet['draft_sha256'] = hashlib.sha256(draft.encode()).hexdigest()
        packet['diff'] = ''.join(difflib.unified_diff([], draft.splitlines(keepends=True), fromfile='/dev/null',
                                                      tofile=packet['target']['path'] + ' (proposed)'))
        return self.rehash(packet)

    def snapshot(self):
        return {str(p): p.read_bytes() for p in sorted(self.root.rglob('*')) if p.is_file()}

    def saved_seed(self):
        prepared = self.prepare()
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        saved = self.write('save', prepared.stdout)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        return json.loads(prepared.stdout), json.loads(saved.stdout)

    def update(self, draft, *extra):
        prepared = self.run_script('library.py', 'proposal', '--target', 'Wiki/Notes/idea.md', *extra, stdin=draft)
        if prepared.returncode:
            return prepared
        return self.write('save', prepared.stdout)

    def test_owner_seed_is_created_exactly_with_provenance_and_recovery(self):
        kept = self.snapshot()
        packet, result = self.saved_seed()
        self.assertEqual(packet['status'], 'prepared_not_approved')
        self.assertIs(packet['approval_available'], False)
        self.assertEqual(packet['target'], {'path': 'Wiki/Notes/idea.md', 'operation': 'create',
                                            'expected_absent': True, 'base_sha256': None})
        self.assertEqual(packet['evidence'], [])
        self.assertEqual(packet['authorship'], 'owner_declared_not_authenticated')
        self.assertEqual(packet['draft'], SEED)  # The helper adds nothing to what the owner reviews.
        self.assertEqual(result['status'], 'plain_file_created')
        self.assertEqual(result['authorship'], 'owner_declared_not_authenticated')
        self.assertIs(result['human_authentication_verified'], False)
        path = self.root / 'Wiki/Notes/idea.md'
        self.assertEqual(path.read_bytes(), SEED.encode())
        self.assertEqual(result['sha256'], hashlib.sha256(SEED.encode()).hexdigest())
        import yaml
        self.assertEqual(yaml.safe_load(path.read_text().split('---\n', 2)[1]),
                         {'role': 'note', 'maturity': 'seed', 'origin': 'owner',
                          'conversation': 'sesión ficticia 1'})
        record = json.loads(Path(result['record']).read_text())
        self.assertEqual(record['format'], 'plain-note-recovery-v1')
        self.assertIs(record['before_exists'], False)
        self.assertEqual(record['after_sha256'], result['sha256'])
        self.assertEqual(record['proposal']['authorship'], 'owner_declared_not_authenticated')
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)
        self.assertEqual({k: v for k, v in self.snapshot().items() if k != str(path)}, kept)
        self.assertEqual(list((self.root / 'Wiki/Notes').glob('.core-note-*')), [])

    def test_conversation_is_optional_and_check_does_not_write(self):
        plain = SEED.replace('conversation: "sesión ficticia 1"\n', '')
        prepared = self.prepare('Wiki/Notes/idea.md', plain)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        checked = self.write('check', prepared.stdout)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertFalse((self.root / 'Wiki/Notes/idea.md').exists())
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_without_the_flag_creation_still_requires_evidence(self):
        refused = self.prepare(flags=('--create',))
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stderr), {'error': 'New derived notes require explicit evidence'})
        packet = json.loads(self.prepare().stdout)
        unmarked = self.rehash({k: v for k, v in packet.items() if k != 'authorship'})
        for candidate in (unmarked, self.rehash({**packet, 'authorship': 'owner'}),
                          self.rehash({**packet, 'authorship': True})):
            refused = self.write('save', candidate)
            self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertFalse((self.root / 'Wiki/Notes/idea.md').exists())
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_only_a_declared_owner_seed_qualifies(self):
        variants = {
            'synthesis and evergreen': SEED.replace('maturity: seed', 'maturity: synthesis'),
            'synthesis and evergreen ': SEED.replace('maturity: seed', 'maturity: evergreen'),
            'synthesis and evergreen  ': SEED.replace('maturity: seed', 'maturity: developing'),
            'origin: owner': SEED.replace('origin: owner\n', ''),
            'origin: owner ': SEED.replace('origin: owner', 'origin: "agente: lector"'),
            'origin: owner  ': SEED.replace('maturity: seed\n', ''),
            'origin: owner   ': SEED.replace('role: note', 'role: map'),
            'origin: owner    ': SEED.replace('conversation: "sesión ficticia 1"', 'conversation: [a, b]'),
            'origin: owner     ': '# Idea ficticia\nSin metadatos.\n',
            'parked proposal': SEED.replace('role: note', 'role: note\nproposal_status: accepted'),
            'readable frontmatter': '---\nrole: note\nrole: note\n---\n# Idea\n',
        }
        packet = json.loads(self.prepare().stdout)
        for reason, draft in variants.items():
            with self.subTest(reason=reason):
                refused = self.prepare('Wiki/Notes/idea.md', draft)
                self.assertEqual(refused.returncode, 2, refused.stdout)
                self.assertEqual(refused.stdout, '')
                self.assertIn(reason.strip(), refused.stderr)
                forged = self.write('save', self.with_draft(packet, draft))
                self.assertEqual(forged.returncode, 2, forged.stdout)
                self.assertIn(reason.strip(), forged.stderr)
        source = self.write('save', self.with_draft(packet, SEED.replace('role: note', 'role: source')))
        self.assertEqual(source.returncode, 2)
        self.assertEqual(sorted(p.name for p in (self.root / 'Wiki/Notes').iterdir()), ['one.md'])
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_an_existing_target_is_never_replaced(self):
        late = json.loads(self.prepare().stdout)
        existing = self.prepare('Wiki/Notes/one.md')
        self.assertEqual(existing.returncode, 2)
        self.assertIn('already exists', existing.stderr)
        self.saved_seed()
        first = (self.root / 'Wiki/Notes/idea.md').read_bytes()
        for candidate in (late, self.with_draft(late, SEED.replace('ficticio A', 'ficticio B'))):
            refused = self.write('save', candidate)
            self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertEqual((self.root / 'Wiki/Notes/idea.md').read_bytes(), first)
        self.assertEqual((self.root / 'Wiki/Notes/one.md').read_text(), '# One\nFictional retained note.\n')
        change = self.run_script('library.py', 'proposal', '--owner-authored', '--target', 'Wiki/Notes/one.md',
                                 stdin=SEED)
        self.assertEqual(change.returncode, 2)
        self.assertIn('--create only', change.stderr)

    def test_originals_and_proposal_locations_are_refused(self):
        packet = json.loads(self.prepare().stdout)
        kept = self.snapshot()
        for target, prepared_reason, writer_reason in (
                ('Raw/Sources/idea.md', 'layers.sources', 'immutable'),
                ('Review/Inbox/idea.md', 'layers.proposals', 'layers.proposals'),
                ('Review/Other/idea.md', 'layers.knowledge', 'layers.knowledge'),
                ('Home.md', 'authorized_paths', 'authorized_paths')):
            with self.subTest(target=target):
                refused = self.prepare(target)
                self.assertEqual(refused.returncode, 2, refused.stdout)
                self.assertEqual(refused.stdout, '')
                self.assertIn(prepared_reason, refused.stderr)
                for action in ('check', 'save'):
                    forged = self.write(action, self.with_draft(packet, SEED, target))
                    self.assertEqual(forged.returncode, 2, forged.stdout)
                    self.assertIn(writer_reason, forged.stderr)
        self.assertEqual(self.snapshot(), kept)
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])

    def test_it_combines_with_neither_custody_nor_evidence(self):
        for extra in (('--evidence', 'Raw/Sources/a.md'), ('--park', '--origin', 'owner', '--proposed-target',
                                                           'Wiki/Notes/idea.md'), ('--move-primary',)):
            with self.subTest(extra=extra):
                refused = self.prepare('Wiki/Notes/idea.md', SEED, *extra)
                self.assertEqual(refused.returncode, 2, refused.stdout)
                self.assertIn('--create only', refused.stderr)
        loose = self.prepare('Wiki/Notes/idea.md', SEED, '--conversation', 'hilo-ficticio-7')
        self.assertEqual(loose.returncode, 2)
        self.assertIn('--park', loose.stderr)
        packet = json.loads(self.prepare().stdout)
        source = hashlib.sha256((self.root / 'Raw/Sources/a.md').read_bytes()).hexdigest()
        with_evidence = self.rehash({**packet, 'evidence': [{'path': 'Raw/Sources/a.md', 'sha256': source}]})
        parked = json.loads(json.dumps(packet))
        parked['target']['operation'] = 'park'
        for candidate in (with_evidence, self.rehash(parked),
                          self.rehash({**packet, 'custody': 'literal_proposal_not_accepted'})):
            refused = self.write('save', candidate)
            self.assertEqual(refused.returncode, 2, refused.stdout)
        park = self.run_script('library.py', 'proposal', '--park', '--target', 'Review/Inbox/idea.md',
                               '--origin', 'agente: lector', '--proposed-target', 'Wiki/Notes/idea.md', stdin=SEED)
        self.assertEqual(park.returncode, 0, park.stderr)
        mislabeled = self.rehash({**json.loads(park.stdout), 'authorship': packet['authorship']})
        refused = self.write('save', mislabeled)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('owner-authorship', refused.stderr)
        self.assertFalse((self.root / 'Wiki/Notes/idea.md').exists())
        self.assertEqual(list((self.root / 'Review/Inbox').iterdir()), [])

    def test_a_parked_proposal_does_not_become_an_owner_seed(self):
        park = self.run_script('library.py', 'proposal', '--park', '--target', 'Review/Inbox/sombra.md',
                               '--origin', 'agente: lector', '--proposed-target', 'Wiki/Notes/idea.md', stdin=SEED)
        self.assertEqual(self.write('save', park.stdout).returncode, 0)
        parked = (self.root / 'Review/Inbox/sombra.md').read_text()
        refused = self.prepare('Wiki/Notes/idea.md', parked)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('parked proposal', refused.stderr)
        relabeled = self.run_script('library.py', 'proposal', '--target', 'Review/Inbox/sombra.md', stdin=SEED)
        self.assertEqual(relabeled.returncode, 0, relabeled.stderr)
        refused = self.write('save', relabeled.stdout)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('stays a parked proposal', refused.stderr)
        self.assertEqual((self.root / 'Review/Inbox/sombra.md').read_text(), parked)

    def test_promotion_or_losing_the_provenance_requires_evidence(self):
        self.saved_seed()
        path = self.root / 'Wiki/Notes/idea.md'
        for draft in (SEED.replace('maturity: seed', 'maturity: synthesis'),
                      SEED.replace('maturity: seed', 'maturity: evergreen'),
                      SEED.replace('origin: owner\n', ''),
                      '# Idea ficticia\nSin metadatos.\n'):
            with self.subTest(draft=draft):
                refused = self.update(draft)
                self.assertEqual(refused.returncode, 2, refused.stdout)
                self.assertIn('requires explicit evidence', refused.stderr)
                self.assertEqual(path.read_bytes(), SEED.encode())
        self.assertEqual(len(list((self.base / 'recovery').iterdir())), 1)
        edited = SEED + '\n\nMatiz ficticio añadido por la propietaria.\n'
        kept = self.update(edited)
        self.assertEqual(kept.returncode, 0, kept.stderr)
        self.assertEqual(path.read_text(), edited)
        promoted = self.update(edited.replace('maturity: seed', 'maturity: synthesis'),
                               '--evidence', 'Raw/Sources/a.md')
        self.assertEqual(promoted.returncode, 0, promoted.stderr)
        self.assertIn('maturity: synthesis', path.read_text())
        restored = self.run_script('note_write.py', 'restore', '--record', json.loads(promoted.stdout)['record'])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(path.read_text(), edited)

    def test_preparation_itself_holds_the_boundary_for_direct_callers(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('knowledge_owner_seed', BASE / 'scripts/knowledge.py')
        knowledge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(knowledge)
        target = 'Wiki/Notes/idea.md'
        packet = knowledge.prepare_proposal(self.root, target, SEED, [], create=True, owner_authored=True)
        self.assertEqual(packet['authorship'], knowledge.OWNER_AUTHORED)
        refusals = (
            dict(draft=SEED, evidence=['Raw/Sources/a.md'], create=True),
            dict(draft=SEED, evidence=[], create=False),
            dict(draft=SEED, evidence=[], custody=True),
            dict(draft=SEED.replace('maturity: seed', 'maturity: evergreen'), evidence=[], create=True),
            dict(draft=SEED.replace('origin: owner\n', ''), evidence=[], create=True),
        )
        for case in refusals:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    knowledge.prepare_proposal(self.root, target, case.pop('draft'), case.pop('evidence'),
                                               owner_authored=True, **case)
        (self.root / target).write_text(SEED)
        with self.assertRaisesRegex(ValueError, 'requires explicit evidence'):
            knowledge.prepare_proposal(self.root, target, SEED.replace('maturity: seed', 'maturity: synthesis'), [])
        kept = knowledge.prepare_proposal(self.root, target, SEED + '\nMatiz ficticio.\n', [])
        self.assertNotIn('authorship', kept)

    def test_writer_refuses_an_evidence_free_promotion_packet(self):
        self.saved_seed()
        plain = '# Idea ficticia\nSin metadatos.\n'
        (self.root / 'Wiki/Notes/idea.md').write_text(plain)
        prepared = self.run_script('library.py', 'proposal', '--target', 'Wiki/Notes/idea.md',
                                   stdin=SEED.replace('maturity: seed', 'maturity: evergreen'))
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        (self.root / 'Wiki/Notes/idea.md').write_text(SEED)
        packet = json.loads(prepared.stdout)
        import difflib
        packet['target']['base_sha256'] = hashlib.sha256(SEED.encode()).hexdigest()
        packet['diff'] = ''.join(difflib.unified_diff(SEED.splitlines(keepends=True),
                                                      packet['draft'].splitlines(keepends=True),
                                                      fromfile='Wiki/Notes/idea.md',
                                                      tofile='Wiki/Notes/idea.md (proposed)'))
        refused = self.write('save', self.rehash(packet))
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn('requires explicit evidence', refused.stderr)
        self.assertEqual((self.root / 'Wiki/Notes/idea.md').read_text(), SEED)

    def test_libraries_without_declared_knowledge_keep_sources_and_proposals_closed(self):
        self.configure(layers={'sources': ['Raw']})
        prepared = self.prepare('Review/Other/idea.md')
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(self.write('save', prepared.stdout).returncode, 0)
        self.assertEqual((self.root / 'Review/Other/idea.md').read_bytes(), SEED.encode())
        refused = self.prepare('Raw/Sources/idea.md')
        self.assertEqual(refused.returncode, 2)
        self.assertIn('layers.sources', refused.stderr)

    def test_read_only_policy_saves_nothing(self):
        packet = json.loads(self.prepare().stdout)
        self.configure(write_policy='read_only')
        refused = self.write('save', packet)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('proposal-only', refused.stderr)
        self.assertFalse((self.root / 'Wiki/Notes/idea.md').exists())


if __name__ == '__main__':
    unittest.main()
