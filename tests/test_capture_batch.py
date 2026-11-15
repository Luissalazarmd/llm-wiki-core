"""Several captures under one decision: one packet, created whole or not at all; synthetic only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import support  # noqa: F401  real temp dir for symlink-refusing helpers

BASE = Path(__file__).resolve().parents[1]
WRITER = BASE / 'scripts/capture_write.py'
NAMES = ('guia', 'libro')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pdf(name):
    return f'%PDF-1.7\nbytes inventados de {name}\n'.encode()


def wrapper(name, reference=None, extra=''):
    return (f'---\nrole: source\nTitle: Documento inventado {name}\nReference: {reference or "synthetic:" + name}\n'
            f'{extra}---\n# Documento inventado {name}\n\n## Contexto de captura\nReferencia para consultar luego.\n\n'
            f'## Resumen\n\n## Original\n[PDF original]({name}.pdf)\n')


class CaptureBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='capture-batch-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'casa privada ñ'
        self.home.mkdir()
        self.root = self.home / 'library'
        shutil.copytree(BASE / 'examples/starter-library', self.root)
        self.config = self.home / 'library.json'
        shutil.copyfile(BASE / 'examples/starter-library.config.example.json', self.config)
        self.recovery = self.home / 'recovery'
        self.recovery.mkdir()
        self.downloads = self.home / 'descargas'
        self.downloads.mkdir()
        for name in NAMES:
            (self.downloads / f'{name}.pdf').write_bytes(pdf(name))
        self.sources = self.root / 'Raw/Sources'

    def call(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(WRITER), '--config', str(self.config), *args],
                              input=stdin, text=True, capture_output=True, timeout=20,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def entry(self, name, **changes):
        return {'target': f'Raw/Sources/{name}.md', 'draft': wrapper(name),
                'attach': [[str(self.downloads / f'{name}.pdf'), f'Raw/Sources/{name}.pdf']], **changes}

    def prepare(self, entries=None):
        return self.call('prepare-batch', stdin=json.dumps([self.entry(n) for n in NAMES] if entries is None else entries))

    def packet(self, entries=None):
        prepared = self.prepare(entries)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        path = self.home / 'batch.json'
        path.write_text(prepared.stdout)
        return path

    def refused(self, result, message):
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(result.stdout, '')
        self.assertIn(message, json.loads(result.stderr)['error'])

    def captured(self):
        return sorted(p.name for p in self.sources.iterdir())

    def unchanged(self):
        self.assertEqual(self.captured(), ['.gitkeep'])
        self.assertEqual(list(self.recovery.iterdir()), [])

    def module(self):
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('capture_write', WRITER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, module.library.load_config(self.config)

    def test_two_single_packets_cannot_share_one_review_but_one_batch_can(self):
        singles = []
        for name in NAMES:
            prepared = self.call('prepare', '--target', f'Raw/Sources/{name}.md', '--attach',
                                 str(self.downloads / f'{name}.pdf'), f'Raw/Sources/{name}.pdf', stdin=wrapper(name))
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            path = self.home / f'{name}.json'
            path.write_text(prepared.stdout)
            singles.append(path)
        batch = self.packet()
        self.unchanged()
        self.assertEqual(self.call('save', '--packet', str(singles[0])).returncode, 0)
        # The first save changed the inventory the second packet was reviewed against.
        self.refused(self.call('save', '--packet', str(singles[1])), 'changed')
        self.refused(self.call('save', '--packet', str(batch)), 'Raw/Sources/guia.md')
        self.assertEqual(self.captured(), ['.gitkeep', 'guia.md', 'guia.pdf'])

    def test_batch_is_one_packet_saved_whole_as_verified_independent_copies(self):
        path = self.packet()
        batch = json.loads(path.read_text())
        self.assertEqual((batch['format'], batch['status'], batch['approval_available'], len(batch['captures'])),
                         ('capture-batch-v1', 'prepared_not_approved', False, 2))
        for name, child in zip(NAMES, batch['captures']):
            # Everything the owner must see once: the exact wrapper and each attachment name, size and sha256.
            self.assertEqual(child['draft'], wrapper(name))
            self.assertEqual(child['attachments'], [{
                'source': str((self.downloads / f'{name}.pdf').resolve()), 'target': f'Raw/Sources/{name}.pdf',
                'sha256': sha(pdf(name)), 'bytes': len(pdf(name)), 'type': '.pdf'}])
        self.unchanged()
        self.assertEqual(self.call('check', '--packet', str(path)).returncode, 0)
        self.unchanged()
        saved = self.call('save', '--packet', str(path))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual((result['status'], result['human_authentication_verified'], result['batch_id']),
                         ('capture_batch_saved', False, batch['batch_id']))
        self.assertEqual([c['target'] for c in result['captures']], [f'Raw/Sources/{n}.md' for n in NAMES])
        self.assertEqual(self.captured(), ['.gitkeep', 'guia.md', 'guia.pdf', 'libro.md', 'libro.pdf'])
        for name in NAMES:
            self.assertEqual((self.sources / f'{name}.md').read_text(), wrapper(name))
            copy = self.sources / f'{name}.pdf'
            self.assertEqual((copy.read_bytes(), copy.stat().st_nlink), (pdf(name), 1))
            self.assertEqual((self.downloads / f'{name}.pdf').read_bytes(), pdf(name))
        records = {p.name: p for p in self.recovery.iterdir()}
        self.assertEqual(sorted(records), sorted([f"capture-batch-{batch['batch_id']}.json",
                                                  *(f"capture-{c['capture_id']}.json" for c in batch['captures'])]))
        self.assertEqual(Path(result['record']).name, f"capture-batch-{batch['batch_id']}.json")
        self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in records.values()))
        self.assertEqual(json.loads(Path(result['record']).read_text())['packet'], batch)
        strict = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(strict.returncode, 0, strict.stderr)

    def test_a_decision_covers_the_batch_once(self):
        path = self.packet()
        batch = json.loads(path.read_text())
        self.assertEqual(self.call('save', '--packet', str(path)).returncode, 0)
        self.refused(self.call('save', '--packet', str(path)), 'already exists')
        for name in NAMES:
            retire = ('retire', '--target', f'Raw/Sources/{name}.md', '--reason', 'El propietario lo pidió')
            plan = json.loads(self.call(*retire).stdout)
            retired = self.call(*retire, '--expected-sha256', plan['plan_sha256'])
            self.assertEqual(retired.returncode, 0, retired.stderr)
        # The library is as it was at prepare, yet neither the batch nor a member packet revives a retired capture.
        self.assertEqual(self.call('check', '--packet', str(path)).returncode, 0)
        self.refused(self.call('save', '--packet', str(path)), 'already used for a save')
        for child in batch['captures']:
            member = self.home / 'member.json'
            member.write_text(json.dumps(child))
            self.refused(self.call('save', '--packet', str(member)), 'already used for a save')
        self.assertEqual(self.captured(), ['.gitkeep'])

    def test_captures_of_one_batch_are_compared_with_each_other(self):
        same = self.entry('libro', draft=wrapper('libro', reference='synthetic:guia'))
        self.refused(self.prepare([self.entry('guia'), same]), 'Duplicate reference/version or unknown version inside the batch')
        tagged = [self.entry(n, draft=wrapper(n, extra='id: fuente-repetida\n')) for n in NAMES]
        self.refused(self.prepare(tagged), 'Duplicate source id inside the batch')
        self.refused(self.prepare([self.entry('guia'), self.entry('guia')]), 'name the same target')
        shared = self.entry('libro', draft=wrapper('libro').replace('(libro.pdf)', '(guia.pdf)'),
                            attach=[[str(self.downloads / 'guia.pdf'), 'Raw/Sources/guia.pdf']])
        self.refused(self.prepare([self.entry('guia'), shared]), 'name the same target')
        # A hand-joined batch of two valid packets for the same document is refused by the writer too.
        module, settings = self.module()
        children = [module.prepare(settings, e['target'], e['draft'].encode(), [tuple(p) for p in e['attach']])
                    for e in (self.entry('guia'), same)]
        joined = {'format': module.BATCH, 'status': 'prepared_not_approved', 'batch_id': 'a' * 32,
                  'captures': children, 'approval_available': False}
        joined['packet_sha256'] = module.canonical(joined)
        with self.assertRaisesRegex(ValueError, 'inside the batch'):
            module.save_batch(settings, joined)
        self.unchanged()

    def test_existing_source_or_bad_entry_stops_the_whole_batch(self):
        (self.sources / 'previa.md').write_text(wrapper('libro').replace('[PDF original](libro.pdf)', ''))
        self.refused(self.prepare(), 'Raw/Sources/libro.md: Duplicate reference')
        (self.sources / 'previa.md').unlink()
        for entries, message in (
                ([], 'JSON array of 1 to 20 captures'),
                ([self.entry('guia')] * 21, 'JSON array of 1 to 20 captures'),
                ({'target': 'x'}, 'JSON array of 1 to 20 captures'),
                ([{**self.entry('guia'), 'draft_path': str(self.home / 'guia.md')}], 'Each capture is'),
                ([{'target': 'Raw/Sources/guia.md'}], 'Each capture is'),
                ([{**self.entry('guia'), 'decision': 'approved'}], 'Each capture is'),
                ([self.entry('guia', attach=[['solo-uno']])], '"attach" is a list of [original, target] pairs'),
                ([self.entry('guia'), self.entry('libro', draft='sin metadatos')], 'Raw/Sources/libro.md: Capture identity'),
                ([self.entry('guia', target='Wiki/Notes/guia.md')], 'Wiki/Notes/guia.md: ')):
            with self.subTest(message=message):
                self.refused(self.prepare(entries), message)
        self.unchanged()

    def test_wrapper_drafts_may_be_named_by_path_outside_the_library(self):
        entries = []
        for name in NAMES:
            draft = self.home / f'{name}.md'
            draft.write_text(wrapper(name))
            entry = self.entry(name, draft_path=str(draft))
            del entry['draft']
            entries.append(entry)
        batch = json.loads(self.packet(entries).read_text())
        self.assertEqual([c['draft'] for c in batch['captures']], [wrapper(n) for n in NAMES])
        inside = self.root / 'Wiki/Notes/borrador.md'
        inside.write_text(wrapper('guia'))
        entries[0]['draft_path'] = str(inside)
        self.refused(self.prepare(entries), 'written outside the library')

    def test_changed_input_or_edited_packet_means_review_again(self):
        path = self.packet()
        batch = json.loads(path.read_text())
        (self.downloads / 'libro.pdf').write_bytes(pdf('libro') + b'cambio')
        self.refused(self.call('save', '--packet', str(path)), 'Raw/Sources/libro.md: Attachment original changed')
        (self.downloads / 'libro.pdf').write_bytes(pdf('libro'))
        (self.sources / 'gemela.md').write_text(wrapper('guia').replace('[PDF original](guia.pdf)', ''))
        self.refused(self.call('save', '--packet', str(path)), 'Raw/Sources/guia.md: Duplicate reference')
        (self.sources / 'gemela.md').unlink()

        def rebound(**changes):
            data = {**{k: v for k, v in batch.items() if k != 'packet_sha256'}, **changes}
            data['packet_sha256'] = sha(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                                   separators=(',', ':')).encode())
            return data
        child = batch['captures'][1]
        for edited, message in (
                ({**batch, 'captures': batch['captures'][:1]}, 'Packet content changed'),
                (rebound(captures=[batch['captures'][0], {**child, 'draft': child['draft'] + 'añadido\n'}]),
                 'Raw/Sources/libro.md: Packet content changed'),
                (rebound(captures=[]), 'holds 1 to 20 captures'),
                (rebound(batch_id='../fuera'), 'Invalid batch_id'),
                (rebound(status='approved'), 'Expected an unapplied capture batch'),
                (rebound(decision='approved'), 'and nothing else')):
            with self.subTest(message=message):
                path.write_text(json.dumps(edited))
                self.refused(self.call('save', '--packet', str(path)), message)
        self.unchanged()

    def test_failed_publication_leaves_no_capture_of_the_batch(self):
        module, settings = self.module()
        batch = json.loads(self.packet().read_text())
        real, calls = os.link, []

        def fourth_link_fails(source, target):
            calls.append(target)
            if len(calls) == 4:
                raise OSError('Injected link failure')
            return real(source, target)
        with patch.object(module.os, 'link', side_effect=fourth_link_fails):
            with self.assertRaises(module.CaptureError) as caught:
                module.save_batch(settings, batch)
        self.assertEqual(len(calls), 4)
        result = caught.exception.result
        self.assertEqual((result['status'], result['library_unchanged'], result['remaining']),
                         ('capture_not_saved', True, []))
        self.unchanged()
        # Nothing was saved or recorded, so the same reviewed batch is still usable.
        self.assertEqual(module.save_batch(settings, batch)['status'], 'capture_batch_saved')

    def test_failed_verification_of_the_last_capture_removes_every_published_file(self):
        module, settings = self.module()
        batch = json.loads(self.packet().read_text())
        real, seen = module.capture_check.check, []

        def second_saved_check_fails(*args, **options):
            if options.get('saved'):
                seen.append((args[1], options.get('ignore')))
                if len(seen) == 2:
                    self.assertEqual(len(self.captured()), 9)  # Four published, their temporaries still held.
                    raise ValueError('Injected readback failure')
            return real(*args, **options)
        with patch.object(module.capture_check, 'check', side_effect=second_saved_check_fails):
            with self.assertRaises(module.CaptureError) as caught:
                module.save_batch(settings, batch)
        self.assertIn('Injected readback failure', caught.exception.result['error'])
        # Each wrapper is verified against the inventory it was reviewed with: its batch siblings left out.
        self.assertEqual(seen, [('Raw/Sources/guia.md', {'Raw/Sources/libro.md'}),
                                ('Raw/Sources/libro.md', {'Raw/Sources/guia.md'})])
        self.unchanged()

    def test_scope_changed_after_the_first_check_stops_before_publication(self):
        module, settings = self.module()
        batch = json.loads(self.packet().read_text())
        real, written = module.write_record, []

        def record_then_duplicate(path, record):
            real(path, record)
            written.append(path)
            if len(written) == 3:
                (self.sources / 'gemela.md').write_text(wrapper('guia').replace('[PDF original](guia.pdf)', ''))
        with patch.object(module, 'write_record', side_effect=record_then_duplicate), \
                patch.object(module.os, 'link', side_effect=AssertionError('published before the recheck')):
            with self.assertRaises(module.CaptureError) as caught:
                module.save_batch(settings, batch)
        self.assertIn('Duplicate reference', caught.exception.result['error'])
        self.assertEqual(self.captured(), ['.gitkeep', 'gemela.md'])
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_unrecoverable_partial_batch_is_reported_and_recorded(self):
        module, settings = self.module()
        batch = json.loads(self.packet().read_text())
        real, calls = os.link, []

        def third_link_fails(source, target):
            calls.append(target)
            if len(calls) == 3:
                raise OSError('Injected link failure')
            return real(source, target)
        with patch.object(module.os, 'link', side_effect=third_link_fails), \
                patch.object(module.os.path, 'samefile', side_effect=OSError('Injected identity failure')):
            with self.assertRaises(module.CaptureError) as caught:
                module.save_batch(settings, batch)
        result = caught.exception.result
        self.assertEqual((result['status'], result['library_unchanged']), ('capture_partial', False))
        self.assertEqual(result['remaining'], ['Raw/Sources/guia.md', 'Raw/Sources/guia.pdf'])
        self.assertEqual(json.loads(Path(result['partial_record']).read_text())['remaining'], result['remaining'])
        # The records stay: they name what was intended, and the batch cannot be saved again blindly.
        self.assertEqual(len(list(self.recovery.iterdir())), 4)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            module.save_batch(settings, batch)

    def test_batch_needs_plain_files_permission_and_the_pinned_install(self):
        path = self.packet()
        settings = json.loads(self.config.read_text())
        self.config.write_text(json.dumps({k: v for k, v in settings.items()
                                           if k not in ('write_policy', 'recovery_directory')}))
        self.refused(self.prepare(), 'Plain writing is disabled')
        self.refused(self.call('save', '--packet', str(path)), 'Plain writing is disabled')
        self.config.write_text(json.dumps(settings))
        rules = self.root / 'AGENTS.md'
        rules.write_text(rules.read_text().replace('- Core commit: unpinned', '- Core commit: ' + 'd' * 40))
        self.refused(self.call('save', '--packet', str(path)), 'pin Core commit')
        self.unchanged()


if __name__ == '__main__':
    unittest.main()
