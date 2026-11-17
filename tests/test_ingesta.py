"""Ingesta items: the agent's unreviewed reading aid in the proposals layer; never knowledge, evidence or a decision."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

import support  # noqa: F401  real temp dir for symlink-refusing helpers
import yaml

BASE = Path(__file__).resolve().parents[1]
STARTER = BASE / 'examples/starter-library'
TARGET = 'Review/Inbox/ingesta-guia.md'
SOURCE = 'Raw/Sources/guia.md'
WRAPPER = ('---\nrole: source\nTitle: Guía inventada\nReference: synthetic:guia-inventada\n---\n'
           '# Guía inventada\n\n## Contexto de captura\nReferencia para consultar luego.\n\n## Resumen\n')
ANALYSIS = ('## Orientación\n\nGuía ficticia sobre sombra y temperatura; alcance: adultos.\n\n'
            '## Mapa de lectura\n\n- Cap. 1, pp. 1–12 · método · relevancia alta\n'
            '- Cap. 2, pp. 13–40 · recomendaciones · relevancia media\n\n'
            '## Contraste con la biblioteca\n\n- Nuevo: sin notas previas sobre el tema (pp. 13–15).\n\n'
            '## Cobertura\n\nLeídas pp. 1–15 de 40; el resto no se leyó.\n')
ITEM = ('---\ningest_status: pending\nsource: "Raw/Sources/guia.md"\norigin: "agente: lector"\n'
        'conversation: "hilo-ficticio-3"\ncreated: "2026-11-15"\n---\n# Ingesta: Guía inventada\n\n'
        'Fuente: [[Raw/Sources/guia]]\n\n'
        '> Análisis preparatorio del agente, sin revisar: orienta la lectura; no es conocimiento aceptado ni '
        'sustituye leer el original.\n\n' + ANALYSIS
        + '\n## Historial\n\n- 2026-11-15 · pendiente · preparada por agente: lector\n')
SEED = ('---\nrole: note\nmaturity: seed\norigin: owner\nconversation: "lectura 2026-11-17"\n---\n'
        '# La sombra no basta para comparar\n\nLa comparación ignora la hora del día.\n\n'
        'Al leer [[Raw/Sources/guia]], pp. 13–15.\n')


def sha(raw):
    return hashlib.sha256(raw if isinstance(raw, bytes) else raw.encode()).hexdigest()


class IngestaCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ingesta-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'casa privada ñ'
        self.home.mkdir()
        self.root = self.home / 'library'
        shutil.copytree(STARTER, self.root)
        self.config = self.home / 'library.json'
        shutil.copyfile(BASE / 'examples/starter-library.config.example.json', self.config)
        self.recovery = self.home / 'recovery'
        self.recovery.mkdir()
        (self.root / SOURCE).write_text(WRAPPER)
        (self.root / 'Wiki/Notes/sombra.md').write_text('---\nrole: note\nmaturity: seed\n---\n# Sombra\n\nNota ficticia.\n')
        self.item = self.root / TARGET

    def configure(self, **changes):
        settings = {**json.loads(self.config.read_text()), **changes}
        self.config.write_text(json.dumps({k: v for k, v in settings.items() if v is not None}))

    def call(self, script, *args, stdin=None):
        return subprocess.run([sys.executable, str(BASE / 'scripts' / script), '--config', str(self.config), *args],
                              input=stdin, text=True, capture_output=True, timeout=20,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def prepare(self, target=TARGET, body=ANALYSIS, source=SOURCE, origin='agente: lector'):
        return self.call('library.py', 'ingest', '--target', target, '--source', source, '--origin', origin,
                         '--conversation', 'hilo-ficticio-3', '--created', '2026-11-15', stdin=body)

    def packet(self, **options):
        prepared = self.prepare(**options)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        return json.loads(prepared.stdout)

    def write(self, packet, action='save'):
        path = self.home / 'packet.json'
        path.write_text(json.dumps(packet))
        return self.call('note_write.py', action, '--packet', str(path))

    def create(self):
        saved = self.write(self.packet())
        self.assertEqual(saved.returncode, 0, saved.stderr)
        return json.loads(saved.stdout)

    def status(self, *args, expected=None, target=TARGET):
        expected = expected or sha((self.root / target).read_bytes())
        return self.call('library.py', 'ingest-status', '--target', target, '--expected-sha256', expected, *args)

    def record(self, *args):
        prepared = self.status(*args)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        saved = self.write(json.loads(prepared.stdout))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        return json.loads(saved.stdout)

    def refused(self, result, message):
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(result.stdout, '')
        self.assertIn(message, json.loads(result.stderr)['error'])

    @staticmethod
    def rehash(packet):
        packet = {k: v for k, v in packet.items() if k != 'packet_sha256'}
        packet['packet_sha256'] = sha(json.dumps(packet, sort_keys=True, ensure_ascii=False, separators=(',', ':')))
        return packet

    def forged(self, packet, draft=None, previous='', **changes):
        """A packet edited by hand and rebound: only the writer's own checks can refuse it."""
        packet = json.loads(json.dumps(packet))
        target = packet['target']['path']
        if draft is not None:
            packet['draft'], packet['draft_sha256'] = draft, sha(draft)
            packet['diff'] = ''.join(difflib.unified_diff(
                previous.splitlines(keepends=True), draft.splitlines(keepends=True),
                fromfile=target if previous else '/dev/null', tofile=target + ' (proposed)'))
        packet.update(changes)
        return self.rehash(packet)

    def tree(self, *folders):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for folder in folders for p in sorted((self.root / folder).rglob('*')) if p.is_file()}


class IngestItemTests(IngestaCase):
    def test_item_is_created_in_the_proposals_layer_without_touching_raw_or_wiki(self):
        before = self.tree('Raw', 'Wiki')
        packet = self.packet()
        self.assertEqual(packet['draft'], ITEM)
        self.assertEqual(packet['target'], {'path': TARGET, 'operation': 'ingest', 'expected_absent': True,
                                            'base_sha256': None})
        self.assertEqual((packet['custody'], packet['status'], packet['approval_available']),
                         ('agent_analysis_not_reviewed', 'prepared_not_approved', False))
        self.assertEqual(packet['evidence'], [{'path': SOURCE, 'sha256': sha(WRAPPER)}])
        self.assertFalse(self.item.exists())
        self.assertEqual(list(self.recovery.iterdir()), [])
        self.assertEqual(self.write(packet, 'check').returncode, 0)
        saved = self.write(packet)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual({k: result[k] for k in ('status', 'custody_only', 'reviewed_by_owner',
                                                 'human_authentication_verified')},
                         {'status': 'ingest_item_created', 'custody_only': True, 'reviewed_by_owner': False,
                          'human_authentication_verified': False})
        self.assertEqual(self.item.read_text(), ITEM)
        self.assertEqual(self.tree('Raw', 'Wiki'), before)
        record = Path(result['record'])
        self.assertEqual((record.parent, stat.S_IMODE(record.stat().st_mode)), (self.recovery.resolve(), 0o600))
        self.assertEqual(json.loads(record.read_text())['proposal'], packet)
        metadata = yaml.safe_load(ITEM.split('---')[1])
        self.assertFalse({'role', 'maturity', 'review', 'proposal_status'} & set(metadata))
        # Creation never overwrites: the same packet, or another analysis of the same target, is refused.
        self.refused(self.write(packet), 'already exists')
        self.refused(self.prepare(), 'already exists')
        self.assertEqual(self.item.read_text(), ITEM)

    def test_one_open_item_per_document(self):
        second = self.packet(target='Review/Inbox/ingesta-guia-2.md')
        self.create()
        self.refused(self.prepare(target='Review/Inbox/ingesta-guia-2.md'), 'already waits in the reading queue at ' + TARGET)
        self.refused(self.write(second), 'already waits in the reading queue')
        self.record('--status', 'reading')
        self.refused(self.write(second), 'already waits in the reading queue')
        self.record('--status', 'withdrawn')
        # A closed item stays as history; the document may be queued again.
        self.assertEqual(self.write(second).returncode, 0)
        strict = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(strict.returncode, 0, strict.stderr)
        self.assertNotIn(TARGET, [note['path'] for note in json.loads(strict.stdout)['notes']])

    def test_english_library_gets_english_labels(self):
        self.configure(language='en')
        body = ('## Orientation\n\nFictional guide.\n\n## Reading map\n\n- Ch. 1, pp. 1-12\n\n'
                '## Contrast with the library\n\n- New.\n\n## Coverage\n\nRead pp. 1-15 of 40.\n')
        packet = self.packet(body=body)
        self.assertIn('# Ingest: Guía inventada\n\nSource: [[Raw/Sources/guia]]\n\n> Preparatory analysis by the agent, '
                      'not reviewed', packet['draft'])
        self.assertTrue(packet['draft'].endswith('## History\n\n- 2026-11-15 · pending · prepared by agente: lector\n'))
        self.assertEqual(self.write(packet).returncode, 0)
        self.refused(self.prepare(target='Review/Inbox/otra.md'), 'starts with "## Orientation"')

    def test_item_never_lands_outside_the_declared_proposals_layer(self):
        (self.root / 'Review/Otra').mkdir()
        before = self.tree('Raw', 'Wiki', 'Review')
        for target in ('Wiki/Notes/ingesta-guia.md', 'Raw/Sources/ingesta-guia.md', 'Review/Otra/ingesta-guia.md'):
            with self.subTest(target=target):
                self.refused(self.prepare(target=target), 'only inside the declared layers.proposals')
        self.refused(self.prepare(target='Review/Inbox/../../Wiki/Notes/x.md'), 'safe relative Markdown path')
        packet = self.packet()
        for target in ('Wiki/Notes/ingesta-guia.md', 'Review/Otra/ingesta-guia.md'):
            moved = json.loads(json.dumps(packet))
            moved['target']['path'] = target
            moved['diff'] = moved['diff'].replace(TARGET + ' (proposed)', target + ' (proposed)')
            self.refused(self.write(self.rehash(moved)), 'only inside the declared layers.proposals')
        raw = json.loads(json.dumps(packet))
        raw['target']['path'] = 'Raw/Sources/ingesta-guia.md'
        self.refused(self.write(self.rehash(raw)), 'Captured sources are immutable')
        self.assertEqual(self.tree('Raw', 'Wiki', 'Review'), before)
        self.assertFalse(self.item.exists())
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_ingest_custody_needs_its_own_permission_and_parking_does_not_grant_it(self):
        packet = self.packet()
        self.configure(ingest_custody=None)
        self.refused(self.prepare(), 'Ingest custody is not enabled')
        self.refused(self.write(packet), 'Ingest custody is not enabled')
        # A library that permitted only literal parking keeps exactly that.
        parked = self.call('library.py', 'proposal', '--park', '--target', 'Review/Inbox/aviso.md', '--origin',
                           'agente: lector', '--proposed-target', 'Wiki/Notes/aviso.md', stdin='Texto literal.\n')
        self.assertEqual(self.write(json.loads(parked.stdout)).returncode, 0, parked.stderr)
        self.configure(ingest_custody=False)
        self.refused(self.write(packet), 'Ingest custody is not enabled')
        self.assertFalse(self.item.exists())
        self.configure(ingest_custody='yes')
        self.refused(self.prepare(), 'ingest_custody is true or false')
        settings = json.loads(self.config.read_text())
        settings['ingest_custody'] = True
        del settings['layers']['proposals']
        self.config.write_text(json.dumps(settings))
        self.refused(self.prepare(), 'true requires layers.proposals')

    def test_status_records_need_the_same_permission(self):
        self.create()
        prepared = self.status('--status', 'reading')
        self.configure(ingest_custody=None)
        self.refused(self.status('--status', 'reading'), 'Ingest custody is not enabled')
        self.refused(self.write(json.loads(prepared.stdout)), 'Ingest custody is not enabled')
        self.assertEqual(self.item.read_text(), ITEM)

    def test_writers_refuse_without_plain_files_or_under_a_pin_this_install_does_not_match(self):
        packet = self.packet()
        self.configure(write_policy='read_only')
        self.refused(self.write(packet), 'Plain writing is disabled')
        self.configure(write_policy='plain_files')
        rules = self.root / 'AGENTS.md'
        rules.write_text(rules.read_text().replace('- Core commit: unpinned', '- Core commit: ' + 'd' * 40))
        self.refused(self.write(packet), 'pin Core commit')
        self.assertFalse(self.item.exists())
        rules.write_text(rules.read_text().replace('d' * 40, 'unpinned'))
        self.assertEqual(self.write(packet).returncode, 0)
        prepared = json.loads(self.status('--status', 'reading').stdout)
        rules.write_text(rules.read_text().replace('- Core commit: unpinned', '- Core commit: ' + 'd' * 40))
        self.refused(self.write(prepared), 'pin Core commit')
        self.assertEqual(self.item.read_text(), ITEM)
        self.assertEqual(len(list(self.recovery.iterdir())), 1)

    def test_item_points_to_one_captured_source_bound_by_its_bytes(self):
        self.refused(self.prepare(source='Wiki/Notes/sombra.md'), 'wrapper of a captured source inside layers.sources')
        self.refused(self.prepare(source='Raw/Sources/ausente.md'), 'does not exist')
        (self.root / 'Raw/Sources/nota.md').write_text('---\nrole: note\n---\n# Nota fuera de sitio\n')
        self.refused(self.prepare(source='Raw/Sources/nota.md'), 'captured source, not to a note')
        (self.root / 'Raw/Sources/guia.pdf').write_bytes(b'%PDF-1.7\n')
        self.refused(self.prepare(source='Raw/Sources/guia.pdf'), 'wrapper of a captured source')
        (self.root / 'Raw/Sources/enorme.md').write_text(WRAPPER.replace('guia-inventada', 'enorme') + 'x' * 270000)
        self.refused(self.prepare(source='Raw/Sources/enorme.md'), 'Source wrapper exceeds byte limit')
        (self.root / 'Raw/Sources/enorme.md').unlink()
        self.configure(living_synthesis={'scopes': ['Review/Inbox'], 'history_complete': True})
        self.refused(self.prepare(), 'unavailable inside a numbered scope')
        self.configure(living_synthesis=None)
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        import knowledge
        for evidence in ([], [SOURCE, 'Wiki/Notes/sombra.md']):
            with self.assertRaisesRegex(ValueError, 'binds exactly one captured source'):
                knowledge.prepare_proposal(self.root, TARGET, ITEM, evidence, ingest=True)
        packet = self.packet()
        other = self.forged(packet, evidence=[{'path': 'Wiki/Notes/sombra.md',
                                               'sha256': sha((self.root / 'Wiki/Notes/sombra.md').read_bytes())}])
        self.refused(self.write(other), 'binds exactly the captured source it names')
        self.refused(self.write(self.forged(packet, evidence=[])), 'binds exactly the captured source it names')
        (self.root / SOURCE).write_text(WRAPPER + '\nCambio posterior.\n')
        self.refused(self.write(packet), 'Stale evidence')
        self.assertFalse(self.item.exists())

    def test_analysis_must_have_the_four_sections_and_declare_its_coverage(self):
        for body, message in (
                (ANALYSIS.replace('## Cobertura\n\nLeídas pp. 1–15 de 40; el resto no se leyó.\n', ''),
                 'exactly these sections'),
                (ANALYSIS.replace('Leídas pp. 1–15 de 40; el resto no se leyó.\n', ''), '"Cobertura" is empty'),
                (ANALYSIS.replace('Guía ficticia sobre sombra y temperatura; alcance: adultos.\n', ''),
                 '"Orientación" is empty'),
                (ANALYSIS.replace('## Mapa de lectura', '## Mapa'), 'exactly these sections'),
                (ANALYSIS + '\n## Conclusiones\n\nUna síntesis del agente.\n', 'exactly these sections'),
                (ANALYSIS + '\n## Historial\n\n- 2026-11-01 · revisada\n', 'Ingesta item format'),
                ('Texto previo.\n\n' + ANALYSIS, 'starts with "## Orientación"'),
                (ANALYSIS.replace('Guía ficticia', '![figura](https://example.invalid/pixel.png) Guía ficticia'),
                 'links and never embeds'),
                (ANALYSIS.replace('Guía ficticia', '![[Raw/Sources/guia.pdf]] Guía ficticia'), 'links and never embeds'),
                (ANALYSIS.replace('Guía ficticia', '<IMG src="https://example.invalid/x"> Guía ficticia'),
                 'links and never embeds'),
                (ANALYSIS + 'x' * 33000, 'never copies the document')):
            with self.subTest(message=message):
                self.refused(self.prepare(body=body), message)
        self.refused(self.prepare(origin='owner'), "names that agent as its origin")
        self.refused(self.prepare(origin='agente\nlector'), 'origin must be one nonempty line')
        self.assertFalse(self.item.exists())

    def test_writer_itself_refuses_any_other_shape(self):
        packet = self.packet()
        for draft, message in (
                (ITEM.replace('ingest_status: pending', 'ingest_status: reviewed'), 'creates a pending item only'),
                (ITEM.replace('ingest_status: pending', 'ingest_status: pending\nrole: note\nmaturity: evergreen'),
                 'no role, maturity, review or proposal status'),
                (ITEM.replace('ingest_status: pending', 'ingest_status: pending\nprogress: "p. 40"'),
                 'declares only ingest_status'),
                (ITEM.replace('origin: "agente: lector"', 'origin: owner').replace('por agente: lector', 'por owner'),
                 'names that agent as its origin'),
                (ITEM.replace('created: "2026-11-15"', 'created: "ayer"'), 'Invalid isoformat'),
                (ITEM.replace('> Análisis preparatorio del agente, sin revisar', '> Revisado por el propietario'),
                 'the notice that it is not reviewed'),
                (ITEM.replace('Fuente: [[Raw/Sources/guia]]', 'Fuente: [[Raw/Sources/otra]]'),
                 'the link to its source'),
                (ITEM + '- 2026-11-16 · revisada\n', 'one history line'),
                (ITEM.replace('## Cobertura\n\nLeídas pp. 1–15 de 40; el resto no se leyó.\n', '## Cobertura\n'),
                 '"Cobertura" is empty'),
                ('# Nota libre\n\nSin formato.\n', 'Ingesta item format'),
                (ITEM.replace('Guía ficticia', '<iframe src="https://example.invalid"></iframe> Guía ficticia'),
                 'links and never embeds'),
                (ITEM + 'relleno ' * 5000, 'never copies the document')):
            with self.subTest(message=message):
                self.refused(self.write(self.forged(packet, draft)), message)
        # The custody label belongs to its operation: it cannot be moved onto another kind of write.
        self.refused(self.write(self.forged(packet, custody='literal_proposal_not_accepted')), 'Only a custody packet')
        self.refused(self.write(self.forged(packet, custody=None)), 'Only a custody packet')
        plain = json.loads(json.dumps(packet))
        plain['target']['operation'] = 'create'
        self.refused(self.write(self.rehash(plain)), 'Only a custody packet')
        self.assertFalse(self.item.exists())
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_an_item_is_never_evidence_for_a_note(self):
        self.create()
        note = '---\nrole: note\nmaturity: synthesis\n---\n# Síntesis\n\nAfirmación tomada del análisis.\n'
        prepared = self.call('library.py', 'proposal', '--create', '--target', 'Wiki/Notes/sintesis.md',
                             '--evidence', TARGET, stdin=note)
        self.refused(prepared, 'preparatory analysis is not evidence')
        honest = self.call('library.py', 'proposal', '--create', '--target', 'Wiki/Notes/sintesis.md',
                           '--evidence', SOURCE, stdin=note)
        self.assertEqual(honest.returncode, 0, honest.stderr)
        packet = json.loads(honest.stdout)
        laundered = self.forged(packet, evidence=[{'path': TARGET, 'sha256': sha(self.item.read_bytes())}])
        self.refused(self.write(laundered), 'preparatory analysis is not evidence')
        self.assertFalse((self.root / 'Wiki/Notes/sintesis.md').exists())
        self.assertEqual(self.write(packet).returncode, 0)


    def test_an_edited_item_is_still_never_evidence_by_either_entry_point(self):
        self.create()
        self.item.write_text(self.item.read_text().replace('## Historial', '## Bitácora'))
        note = '---\nrole: note\nmaturity: synthesis\n---\n# Síntesis\n\nAfirmación tomada del análisis.\n'
        self.refused(self.call('library.py', 'proposal', '--create', '--target', 'Wiki/Notes/sintesis.md',
                               '--evidence', TARGET, stdin=note), 'preparatory analysis is not evidence')
        direct = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root),
                                 '--proposal-target', 'Wiki/Notes/sintesis.md', '--create', '--evidence', TARGET],
                                input=note, text=True, capture_output=True, timeout=20,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.refused(direct, 'preparatory analysis is not evidence')
        original = self.item.read_text()
        for broken in (original.replace('created:', 'created: "x"\ncreated:'),
                       original.replace('origin: "agente: lector"', 'origin: *nope'),
                       original.replace('ingest_status:', 'Ingest_status:'),
                       original.replace('ingest_status: pending', '"ingest\\u005fstatus": pending'),
                       original.replace('---\ningest_status: pending\nsource: "Raw/Sources/guia.md"\norigin: "agente: lector"\n'
                                        'conversation: "hilo-ficticio-3"\ncreated: "2026-11-15"\n---',
                                        '---\n{ingest_status: pending}\n---')):
            self.item.write_text(broken)
            self.refused(self.call('library.py', 'proposal', '--create', '--target', 'Wiki/Notes/sintesis.md',
                                   '--evidence', TARGET, stdin=note), 'preparatory analysis is not evidence')

    def test_any_html_element_is_refused_in_an_item(self):
        for markup in ('<div style="background:url(https://example.invalid/x)">x</div>',
                       '<picture><source srcset="https://example.invalid/x"></picture>',
                       '<img/src="https://example.invalid/x">'):
            self.refused(self.prepare(body=ANALYSIS.replace('alcance: adultos.', markup)), 'no HTML element')
        self.assertEqual(self.prepare(body=ANALYSIS.replace('alcance: adultos.', 'p<0.05 y <https://example.invalid>')).returncode, 0)

class IngestStatusTests(IngestaCase):
    def setUp(self):
        super().setUp()
        self.create()

    def test_reading_progress_and_closing_change_only_status_progress_and_history(self):
        result = self.record('--status', 'reading', '--date', '2026-11-16')
        self.assertEqual((result['status'], result['custody_only'], result['reviewed_by_owner']),
                         ('ingest_status_recorded', True, False))
        first = ITEM.replace('ingest_status: pending', 'ingest_status: reading') + '- 2026-11-16 · en lectura\n'
        self.assertEqual(self.item.read_text(), first)
        # The owner ticks a chapter by hand; the next record keeps that edit byte for byte.
        edited = first.replace('- Cap. 1, pp. 1–12', '- [x] Cap. 1, pp. 1–12')
        self.item.write_text(edited)
        self.record('--status', 'reading', '--progress', 'p. 12, cap. 1', '--date', '2026-11-17')
        second = (edited.replace('ingest_status: reading\n', 'ingest_status: reading\nprogress: "p. 12, cap. 1"\n')
                  + '- 2026-11-17 · en lectura · hasta p. 12, cap. 1\n')
        self.assertEqual(self.item.read_text(), second)
        self.record('--status', 'reading', '--progress', 'p. 40', '--date', '2026-11-18')
        closed = self.record('--status', 'reviewed', '--note', 'notas: [[Wiki/Notes/sombra]]', '--date', '2026-11-19')
        third = (second.replace('progress: "p. 12, cap. 1"', 'progress: "p. 40"').replace(
            'ingest_status: reading', 'ingest_status: reviewed')
            + '- 2026-11-18 · en lectura · hasta p. 40\n- 2026-11-19 · revisada · notas: [[Wiki/Notes/sombra]]\n')
        self.assertEqual(self.item.read_text(), third)
        self.assertEqual(sha(third), closed['sha256'])
        self.assertEqual(len(list(self.recovery.iterdir())), 5)
        # Each record keeps the bytes it displaced: the close can be undone like any other save.
        restored = self.call('note_write.py', 'restore', '--record', closed['record'])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertIn('ingest_status: reading\nprogress: "p. 40"', self.item.read_text())

    def test_owner_text_on_a_status_line_or_under_a_history_entry_is_never_lost(self):
        commented = ITEM.replace('ingest_status: pending', 'ingest_status: pending # mía')
        self.item.write_text(commented)
        self.refused(self.status('--status', 'reading'), 'cannot be updated mechanically')
        self.assertEqual(self.item.read_text(), commented)
        continued = ITEM + '  comentario mío sobre la preparación\n\n  y un segundo párrafo mío\n'
        self.item.write_text(continued)
        self.record('--status', 'reading', '--date', '2026-11-16')
        self.assertTrue(self.item.read_text().endswith(
            '- 2026-11-15 · pendiente · preparada por agente: lector\n  comentario mío sobre la preparación\n'
            '\n  y un segundo párrafo mío\n- 2026-11-16 · en lectura\n'))

    def test_history_is_the_one_its_title_names(self):
        mixed = ITEM.replace('Nuevo: sin notas previas', 'Nuevo:\n\n## History\n\nsin notas previas')
        self.item.write_text(mixed)
        self.record('--status', 'reading', '--date', '2026-11-16')
        self.assertTrue(self.item.read_text().endswith('- 2026-11-16 · en lectura\n'))
        english = ITEM.replace('# Ingesta: ', '# Ingest: ')
        self.item.write_text(english)
        self.refused(self.status('--status', 'reading'), 'Not an Ingesta item')

    def test_an_item_can_be_withdrawn_and_reopened_in_reading_with_one_record(self):
        self.record('--status', 'withdrawn', '--note', 'el propietario la descartó', '--date', '2026-11-16')
        text = self.item.read_text()
        self.assertTrue(text.endswith('- 2026-11-16 · retirada · el propietario la descartó\n'))
        self.assertTrue(self.item.exists())
        for status in ('reviewed', 'withdrawn'):
            self.refused(self.status('--status', status), 'or reopens a closed item in reading')
        self.assertEqual(self.item.read_text(), text)
        self.record('--status', 'reading', '--progress', 'cap. 3', '--date', '2026-11-20')
        self.assertTrue(self.item.read_text().endswith('- 2026-11-20 · en lectura · hasta cap. 3\n'))
        self.assertIn('ingest_status: reading', self.item.read_text())
        self.record('--status', 'reviewed', '--date', '2026-11-21')
        # A closed item is not reopened while another one for the same document waits.
        saved = self.write(self.packet(target='Review/Inbox/ingesta-otra.md'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.refused(self.status('--status', 'reading'), 'one open Ingesta item per document')

    def test_save_rechecks_the_queue_before_reopening(self):
        self.record('--status', 'reviewed')
        reopen = self.status('--status', 'reading')
        self.assertEqual(reopen.returncode, 0, reopen.stderr)
        saved = self.write(self.packet(target='Review/Inbox/ingesta-otra.md'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        before = self.tree('Review')
        records = set(self.recovery.iterdir())
        self.refused(self.write(json.loads(reopen.stdout)), 'one open Ingesta item per document')
        self.assertEqual(self.tree('Review'), before)
        self.assertEqual(set(self.recovery.iterdir()), records)

    def test_record_is_bound_to_the_version_the_agent_read(self):
        self.refused(self.status('--status', 'reading', expected='0' * 64), 'read it again')
        prepared = json.loads(self.status('--status', 'reading').stdout)
        self.item.write_text(ITEM.replace('- Cap. 2', '- [x] Cap. 2'))
        self.refused(self.write(prepared), 'Stale proposal base')
        self.assertIn('- [x] Cap. 2', self.item.read_text())
        self.assertIn('ingest_status: pending', self.item.read_text())

    def test_record_carries_one_line_and_never_repeats_itself(self):
        self.refused(self.status('--status', 'reading', '--progress', 'p. 1\n- 2026-01-01 · revisada'),
                     'progress must be one nonempty line')
        self.refused(self.status('--status', 'reading', '--note', 'x' * 301), 'note must be one nonempty line')
        self.refused(self.status('--status', 'reading', '--date', 'mañana'), 'Invalid isoformat')
        self.refused(self.status('--status', 'reviewed', '--note', 'ver ![x](https://example.invalid/p.png)'),
                     'note links and never embeds')
        # A comparison sign in clinical prose is not an element.
        self.assertEqual(self.status('--status', 'reading', '--progress', 'p. 12, tabla con p < 0.05').returncode, 0)
        # Nor is the owner's "<P95": it is kept as said and written as inert text in the history.
        self.record('--status', 'reading', '--progress', 'p. 9, valores <P95 en niños', '--note', '<b de grado')
        text = self.item.read_text()
        self.assertIn('progress: "p. 9, valores <P95 en niños"', text)
        self.assertTrue(text.endswith('hasta p. 9, valores &lt;P95 en niños · &lt;b de grado\n'))
        self.record('--status', 'reading', '--progress', 'p. 12')
        self.refused(self.status('--status', 'reading', '--progress', 'p. 12'), 'Nothing to record')
        self.refused(self.status('--status', 'reading'), 'Nothing to record')

    def test_writer_refuses_a_status_packet_that_changes_anything_else(self):
        packet = json.loads(self.status('--status', 'reading', '--date', '2026-11-16').stdout)
        self.assertEqual(packet['ingest'], {'status': 'reading', 'date': '2026-11-16', 'progress': None, 'note': None})
        self.assertEqual((packet['custody'], packet['evidence']), ('ingest_status_record_not_reviewed', []))
        rewritten = packet['draft'].replace('relevancia media', 'relevancia alta')
        for edited, message in (
                (self.forged(packet, rewritten, ITEM), 'every other byte of the item stays as it is'),
                (self.forged(packet, packet['draft'].replace('- 2026-11-15 · pendiente · preparada por agente: lector\n', ''),
                             ITEM), 'every other byte'),
                (self.forged(packet, packet['draft'].replace('guia.md"', 'otra.md"'), ITEM), 'every other byte'),
                (self.forged(packet, ingest={**packet['ingest'], 'status': 'reviewed'}), 'every other byte'),
                (self.forged(packet, ingest={'status': 'reading'}), 'carries only its status, date, progress and note'),
                (self.forged(packet, ingest=None), 'carries only its status'),
                (self.forged(packet, evidence=[{'path': SOURCE, 'sha256': sha(WRAPPER)}]), 'carries only its status'),
                ({**packet, 'draft': rewritten}, 'Packet content changed')):
            with self.subTest(message=message):
                self.refused(self.write(edited), message)
        # Without the custody label the same bytes are an ordinary update and may not carry the record.
        plain = {k: v for k, v in packet.items() if k != 'custody'}
        self.refused(self.write(self.rehash(plain)), 'Only a custody packet')
        self.assertEqual(self.item.read_text(), ITEM)
        self.assertEqual(len(list(self.recovery.iterdir())), 1)

    def test_status_record_applies_to_ingesta_items_in_the_proposals_layer_only(self):
        parked = self.call('library.py', 'proposal', '--park', '--target', 'Review/Inbox/aviso.md', '--origin',
                           'agente: lector', '--proposed-target', 'Wiki/Notes/aviso.md', stdin='Texto literal.\n')
        self.assertEqual(self.write(json.loads(parked.stdout)).returncode, 0, parked.stderr)
        self.refused(self.status('--status', 'reviewed', target='Review/Inbox/aviso.md'), 'Not an Ingesta item')
        self.refused(self.status('--status', 'reviewed', target='Wiki/Notes/sombra.md'),
                     'inside the declared layers.proposals')
        self.refused(self.status('--status', 'reviewed', target=SOURCE), 'inside the declared layers.proposals')
        # An item-shaped note in Wiki is not reachable either, even with a hand-made packet.
        wiki = self.root / 'Wiki/Notes/falsa.md'
        wiki.write_text(ITEM)
        packet = json.loads(self.status('--status', 'reading', '--date', '2026-11-16').stdout)
        moved = json.loads(json.dumps(packet))
        moved['target']['path'] = 'Wiki/Notes/falsa.md'
        moved['diff'] = moved['diff'].replace(TARGET, 'Wiki/Notes/falsa.md')
        self.refused(self.write(self.rehash(moved)), 'inside the declared layers.proposals')
        self.assertEqual(wiki.read_text(), ITEM)

    def test_frontmatter_rewritten_by_an_editor_is_still_updated_or_refused_whole(self):
        # Obsidian rewrites properties: quotes dropped, keys reordered.
        loose = ITEM.replace('source: "Raw/Sources/guia.md"\norigin: "agente: lector"\n',
                             'origin: "agente: lector"\nsource: Raw/Sources/guia.md\n')
        self.item.write_text(loose)
        self.record('--status', 'reading', '--progress', 'cap. 2', '--date', '2026-11-16')
        metadata = yaml.safe_load(self.item.read_text().split('---')[1])
        self.assertEqual((metadata['ingest_status'], metadata['progress'], metadata['source']),
                         ('reading', 'cap. 2', 'Raw/Sources/guia.md'))
        folded = self.item.read_text().replace('progress: "cap. 2"\n', 'progress: >-\n  cap. 2\n  y medio\n')
        self.item.write_text(folded)
        self.refused(self.status('--status', 'reading', '--progress', 'cap. 3'), 'cannot be updated mechanically')
        self.item.write_text(folded.replace('## Historial', '## Bitácora'))
        self.refused(self.status('--status', 'reviewed'), 'Not an Ingesta item')
        self.assertIn('## Bitácora', self.item.read_text())
        for text, message in (
                (ITEM.replace('ingest_status: pending', 'ingest_status : pending'), 'cannot be updated mechanically'),
                # A YAML comment that spells the heading does not stand in for the history itself.
                (ITEM.replace('ingest_status: pending', 'ingest_status: pending\n## Historial').replace(
                    '\n## Historial\n\n- 2026', '\n## Bitácora\n\n- 2026'), 'history cannot be located'),
                (ITEM.replace('- 2026-11-15 · pendiente · preparada por agente: lector\n', ''),
                 'no entries to append to'),
                (ITEM.replace('Leídas pp. 1–15', 'x' * 270000 + ' Leídas pp. 1–15'), 'Item exceeds byte limit')):
            with self.subTest(message=message):
                self.item.write_text(text)
                self.refused(self.status('--status', 'reading'), message)
                self.assertEqual(self.item.read_text(), text)

    def test_reviewed_update_may_change_the_analysis_but_keeps_source_origin_and_history(self):
        self.record('--status', 'reading', '--date', '2026-11-16')
        current = self.item.read_text()

        def update(draft):
            return self.call('library.py', 'proposal', '--target', TARGET, stdin=draft)
        better = update(current.replace('relevancia media', 'relevancia alta'))
        self.assertEqual(better.returncode, 0, better.stderr)
        saved = self.write(json.loads(better.stdout))
        self.assertEqual(json.loads(saved.stdout)['status'], 'plain_file_saved', saved.stderr)
        current = self.item.read_text()
        for draft, message in (
                (current.replace('guia.md"', 'otra.md"'), 'keeps its source, origin and creation date'),
                (current.replace('origin: "agente: lector"', 'origin: owner'), 'keeps its source, origin'),
                (current.replace('- 2026-11-16 · en lectura\n', ''), 'keeps its history lines'),
                (current.replace('- 2026-11-15 · pendiente · preparada por agente: lector\n- 2026-11-16 · en lectura\n',
                                 '- 2026-11-16 · en lectura\n- 2026-11-15 · pendiente · preparada por agente: lector\n'),
                 'keeps its history lines'),
                (current.replace('ingest_status: reading', 'ingest_status: aprobada'), 'stays an Ingesta item'),
                ('---\nrole: note\nmaturity: evergreen\n---\n# Conocimiento\n\nTexto.\n', 'stays an Ingesta item')):
            with self.subTest(message=message):
                prepared = update(draft)
                self.assertEqual(prepared.returncode, 0, prepared.stderr)
                self.refused(self.write(json.loads(prepared.stdout)), message)
        self.assertEqual(self.item.read_text(), current)


class IngestQueueAndReadingTests(IngestaCase):
    def test_queue_lists_waiting_items_read_only_and_never_parked_proposals(self):
        self.create()
        (self.root / 'Raw/Sources/libro.md').write_text(WRAPPER.replace('Guía inventada', 'Libro inventado')
                                                         .replace('guia-inventada', 'libro-inventado'))
        saved = self.write(self.packet(target='Review/Inbox/ingesta-libro.md', source='Raw/Sources/libro.md'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        parked = self.call('library.py', 'proposal', '--park', '--target', 'Review/Inbox/aviso.md', '--origin',
                           'agente: lector', '--proposed-target', 'Wiki/Notes/aviso.md', stdin='Texto literal.\n')
        self.assertEqual(self.write(json.loads(parked.stdout)).returncode, 0, parked.stderr)
        (self.root / 'Review/Inbox/roto.md').write_bytes(b'\xff\xfe no es utf-8')
        (self.root / 'Review/Inbox/enorme.md').write_text(ITEM + 'x' * 270000)
        self.record('--status', 'reading', '--progress', 'p. 12')
        self.configure(write_policy='read_only', recovery_directory=None)
        before = self.tree('Raw', 'Review', 'Wiki')
        queue = json.loads(self.call('library.py', 'ingest-queue').stdout)
        self.assertEqual([(i['path'], i['ingest_status'], i['progress'], i['source'], i['source_present'])
                          for i in queue['items']],
                         [(TARGET, 'reading', 'p. 12', SOURCE, True),
                          ('Review/Inbox/ingesta-libro.md', 'pending', None, 'Raw/Sources/libro.md', True)])
        self.assertEqual(queue['items'][0]['sha256'], sha(self.item.read_bytes()))
        self.assertEqual([i['title'] for i in queue['items']], ['Guía inventada', 'Libro inventado'])
        self.assertEqual([(entry['path'], entry['reason'][:7]) for entry in queue['not_checked']],
                         [('Review/Inbox/enorme.md', 'exceeds'), ('Review/Inbox/roto.md', "'utf-8'")])
        self.assertEqual((queue['mode'], queue['library_changed']), ('ingest_queue_read_only', False))
        self.assertIn('never evidence', queue['trust'])
        self.configure(write_policy='plain_files', recovery_directory='recovery')
        self.record('--status', 'reviewed')
        self.assertEqual([i['path'] for i in json.loads(self.call('library.py', 'ingest-queue').stdout)['items']],
                         ['Review/Inbox/ingesta-libro.md'])
        everything = json.loads(self.call('library.py', 'ingest-queue', '--all').stdout)['items']
        self.assertEqual([(i['path'], i['ingest_status']) for i in everything],
                         [(TARGET, 'reviewed'), ('Review/Inbox/ingesta-libro.md', 'pending')])
        del before[TARGET]
        after = self.tree('Raw', 'Review', 'Wiki')
        del after[TARGET]
        self.assertEqual(after, before)
        settings = json.loads(self.config.read_text())
        del settings['layers']['proposals'], settings['ingest_custody']
        self.config.write_text(json.dumps(settings))
        self.refused(self.call('library.py', 'ingest-queue'), 'none is declared')

    def test_queue_orders_by_calendar_date_then_path_without_rewriting_created(self):
        # Dates oppose filename order. Basic ISO dates are accepted by Python 3.11 and later.
        early = '20261114' if sys.version_info >= (3, 11) else '2026-11-14'
        dates = {'a': '0000-invalid', 'b': '2026-11-16', 'c': '2026-11-14', 'd': early}
        for name, date in dates.items():
            (self.item.parent / f'{name}.md').write_text(ITEM.replace('2026-11-15', date))
        self.configure(ingest_custody=None, write_policy='read_only', recovery_directory=None)
        result = self.call('library.py', 'ingest-queue')
        self.assertEqual(result.returncode, 0, result.stderr)
        items = json.loads(result.stdout)['items']
        self.assertEqual([(Path(item['path']).stem, item['created']) for item in items],
                         [(name, dates[name]) for name in ('c', 'd', 'b', 'a')])

    def test_queue_checks_presence_only_for_declared_source_files(self):
        (self.root / 'Raw/Sources/alias.md').symlink_to(self.root / SOURCE)
        for source in (SOURCE, 'Wiki/Notes/sombra.md', 'Raw/Sources/alias.md',
                       'Raw/Sources/absent.md', str(self.root / SOURCE)):
            with self.subTest(source=source):
                self.item.write_text(ITEM.replace(SOURCE, source))
                result = self.call('library.py', 'ingest-queue')
                self.assertEqual(result.returncode, 0, result.stderr)
                item, = json.loads(result.stdout)['items']
                self.assertEqual(item['source_present'], source == SOURCE)

    def test_what_the_owner_keeps_is_an_owner_seed_with_its_pages_in_wiki_only(self):
        self.create()
        seed = self.call('library.py', 'proposal', '--create', '--owner-authored', '--target',
                         'Wiki/Notes/sombra-no-basta.md', stdin=SEED)
        self.assertEqual(seed.returncode, 0, seed.stderr)
        packet = json.loads(seed.stdout)
        self.assertEqual((packet['authorship'], packet['evidence']), ('owner_declared_not_authenticated', []))
        saved = json.loads(self.write(packet).stdout)
        self.assertEqual(saved['status'], 'plain_file_created')
        self.assertEqual((self.root / 'Wiki/Notes/sombra-no-basta.md').read_text(), SEED)
        # The agent's item is never relabelled as the owner's, and the owner's note never waits in the queue.
        self.refused(self.call('library.py', 'proposal', '--create', '--owner-authored', '--target',
                               'Wiki/Notes/analisis.md', stdin=ITEM), 'An owner-authored seed declares')
        self.refused(self.call('library.py', 'proposal', '--create', '--owner-authored', '--target',
                               'Review/Inbox/sombra-no-basta.md', stdin=SEED), 'never lands in layers.sources or layers.proposals')
        self.record('--status', 'reviewed', '--note', 'notas: [[Wiki/Notes/sombra-no-basta]]')
        self.assertIn('revisada · notas: [[Wiki/Notes/sombra-no-basta]]', self.item.read_text())

    def test_retiring_the_source_reports_the_item_that_points_to_it(self):
        self.create()
        plan = json.loads(self.call('capture_write.py', 'retire', '--target', SOURCE, '--reason',
                                    'El propietario pidió retirarla').stdout)
        self.assertEqual([note['path'] for note in plan['linked_from']], [TARGET])
        self.assertEqual(self.item.read_text(), ITEM)


class IngestaContractTests(unittest.TestCase):
    def test_starter_rules_settings_and_views_carry_the_example(self):
        rules = ' '.join((STARTER / 'AGENTS.md').read_text().split())
        for sentence in ('Ingesta is permitted here', 'unless the owner says otherwise in that conversation',
                         'the owner decides once on the whole batch', 'without a further decision, create one new file',
                         'exactly what was and was not read', 'never knowledge, never evidence and never the owner\'s decision',
                         'never overwrites and never touches `Raw/` or `Wiki/`',
                         'only to record what the owner said in the current conversation',
                         'closed in place and never deleted',
                         'enters `Wiki/` as the owner\'s own notes'):
            self.assertIn(sentence, rules)
        self.assertIs(json.loads((BASE / 'examples/starter-library.config.example.json').read_text())['ingest_custody'], True)
        base = yaml.safe_load((STARTER / 'Biblioteca.base').read_text())
        pending = next(view for view in base['views'] if view['name'] == 'Pendientes')
        self.assertEqual(pending['sort'], [{'property': 'formula.fecha', 'direction': 'ASC'},
                                           {'property': 'file.path', 'direction': 'ASC'}])
        self.assertEqual(pending['filters'], {'and': ['formula.categoria == "Ingesta"',
                                                      {'or': ['ingest_status == "pending"', 'ingest_status == "reading"']}]})
        self.assertIn('if(ingest_status, "Ingesta", "Propuestas")', base['formulas']['categoria'])
        home = (STARTER / 'Home.md').read_text()
        self.assertIn('![[Biblioteca.base#Pendientes]]', home)
        self.assertIn('sin revisar', home)

    def test_contract_names_the_permission_and_its_limits_once(self):
        contract = ' '.join((BASE / 'docs/review-contract.md').read_text().split())
        self.assertEqual(contract.count('## Ingest custody'), 1)
        for phrase in ('the agent\'s own preparatory analysis', 'Only when the library\'s own rules permit it',
                       'never evidence', 'what was and was not read', 'only records what the owner said',
                       'not the owner\'s review of the document certified', 'Permission to park does not include it',
                       'never advances or closes an item on its own', 'never deleted, moved or copied into Wiki'):
            self.assertIn(phrase, contract)
        for relative in ('AGENTS.md', 'docs/plain-saving.md', 'docs/ingesta.md', 'skills/ingesta/SKILL.md'):
            self.assertIn('review-contract.md#ingest-custody', (BASE / relative).read_text(), relative)
        skill = (BASE / 'skills/ingesta/SKILL.md').read_text()
        for phrase in ('one document at a time', 'prepare-batch', 'ingest-status', '--owner-authored',
                       'never claims a complete reading', 'Permission to park proposals is not permission for this'):
            self.assertIn(phrase, ' '.join(skill.split()))


if __name__ == '__main__':
    unittest.main()
