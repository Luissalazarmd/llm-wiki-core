"""Capture writer and owner-exception retirement on a copied starter library; synthetic only."""
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
PDF = b'%PDF-1.7\nbytes inventados, no un documento real\n'
WRAPPER = ('---\nrole: source\nTitle: Informe inventado\nReference: synthetic:informe-inventado\n---\n'
           '# Informe inventado\n\n## Contexto de captura\nReferencia para consultar luego.\n\n'
           '## Original\n![[Raw/Sources/informe.pdf]]\n')
REASON = 'El propietario pidió retirarla'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class CaptureWriteCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='capture-write-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'casa privada ñ'
        self.home.mkdir()
        self.root = self.home / 'library'
        shutil.copytree(BASE / 'examples/starter-library', self.root)
        self.config = self.home / 'library.json'
        shutil.copyfile(BASE / 'examples/starter-library.config.example.json', self.config)
        self.recovery = self.home / 'recovery'
        self.recovery.mkdir()
        self.original = self.home / 'descargas/informe.pdf'
        self.original.parent.mkdir()
        self.original.write_bytes(PDF)
        self.sources = self.root / 'Raw/Sources'

    def call(self, *args, stdin=None, script='capture_write.py'):
        return subprocess.run([sys.executable, str(BASE / 'scripts' / script), '--config', str(self.config), *args],
                              input=stdin, text=True, capture_output=True, timeout=20,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def prepare(self, wrapper=WRAPPER, target='Raw/Sources/informe.md', attach=None):
        pairs = [(str(self.original), 'Raw/Sources/informe.pdf')] if attach is None else attach
        return self.call('prepare', '--target', target, *[arg for pair in pairs for arg in ('--attach', *pair)],
                         stdin=wrapper)

    def packet(self, **options):
        prepared = self.prepare(**options)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        path = self.home / 'packet.json'
        path.write_text(prepared.stdout)
        return path

    def save(self, **options):
        saved = self.call('save', '--packet', str(self.packet(**options)))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        return json.loads(saved.stdout)

    def refused(self, result, message):
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(result.stdout, '')
        self.assertIn(message, json.loads(result.stderr)['error'])

    def module(self):
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('capture_write', WRITER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, module.library.load_config(self.config)

    def captured(self):
        return sorted(p.name for p in self.sources.iterdir())

    def unchanged(self):
        """Nothing captured, staged or recorded."""
        self.assertEqual(self.captured(), ['.gitkeep'])
        self.assertEqual(list(self.recovery.iterdir()), [])
        self.assertEqual(self.original.read_bytes(), PDF)


class CaptureWriteTests(CaptureWriteCase):
    def test_wrapper_and_pdf_are_saved_as_verified_independent_copies(self):
        packet = json.loads(self.packet().read_text())
        self.assertEqual((packet['status'], packet['approval_available']), ('prepared_not_approved', False))
        self.assertEqual(packet['draft'], WRAPPER)
        self.assertEqual(packet['attachments'], [{
            'source': str(self.original.resolve()), 'target': 'Raw/Sources/informe.pdf', 'sha256': sha(PDF),
            'bytes': len(PDF), 'type': '.pdf'}])
        self.unchanged()
        checked = self.call('check', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.unchanged()
        saved = self.call('save', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual((result['status'], result['human_authentication_verified']), ('capture_saved', False))
        self.assertEqual(result['attachments'], [{'target': 'Raw/Sources/informe.pdf', 'sha256': sha(PDF),
                                                  'bytes': len(PDF)}])
        self.assertEqual(self.captured(), ['.gitkeep', 'informe.md', 'informe.pdf'])
        self.assertEqual((self.sources / 'informe.md').read_text(), WRAPPER)
        copy = self.sources / 'informe.pdf'
        self.assertEqual(copy.read_bytes(), PDF)
        self.assertEqual(copy.stat().st_nlink, 1)
        self.assertFalse(os.path.samefile(copy, self.original))
        self.assertEqual(self.original.read_bytes(), PDF)
        record = Path(result['record'])
        self.assertEqual(record, self.recovery.resolve() / f"capture-{packet['capture_id']}.json")
        self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
        self.assertEqual(json.loads(record.read_text())['packet'], packet)
        verified = self.call('--target', 'Raw/Sources/informe.md', '--saved', '--expected-sha256',
                             result['check_sha256'], stdin=WRAPPER, script='capture_check.py')
        self.assertEqual(verified.returncode, 0, verified.stderr)
        strict = subprocess.run([sys.executable, str(BASE / 'scripts/knowledge.py'), '--root', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(strict.returncode, 0, strict.stderr)
        self.assertIn('Raw/Sources/informe.md', strict.stdout)

    def test_wrapper_alone_and_relative_markdown_link_are_accepted(self):
        alone = WRAPPER.replace('![[Raw/Sources/informe.pdf]]\n', 'Extracto inventado. [Editorial](https://example.org/a.pdf)\n')
        self.assertEqual(self.save(wrapper=alone, attach=[])['attachments'], [])
        other = (WRAPPER.replace('synthetic:informe-inventado', 'synthetic:otro')
                 .replace('![[Raw/Sources/informe.pdf]]', '[PDF](<otro informe.pdf>) y ![[otro informe.pdf#page=2]]'))
        result = self.save(wrapper=other, target='Raw/Sources/otro.md',
                           attach=[(str(self.original), 'Raw/Sources/otro informe.pdf')])
        self.assertEqual((self.sources / result['attachments'][0]['target'].split('/')[-1]).read_bytes(), PDF)

    def test_existing_targets_are_never_overwritten(self):
        (self.sources / 'informe.pdf').write_bytes(b'previo')
        self.refused(self.prepare(), 'Attachment target already exists')
        (self.sources / 'informe.pdf').unlink()
        (self.sources / 'informe.md').write_text('previo')
        self.refused(self.prepare(), 'already exists')
        (self.sources / 'informe.md').unlink()
        packet = self.packet()
        for name in ('informe.pdf', 'informe.md'):
            (self.sources / name).write_bytes(b'competidor')
            self.refused(self.call('save', '--packet', str(packet)), 'already exists')
            self.assertEqual((self.sources / name).read_bytes(), b'competidor')
            (self.sources / name).unlink()
            self.unchanged()

    def test_original_changed_between_prepare_and_save_is_refused(self):
        packet = self.packet()
        self.original.write_bytes(PDF + b'otra edicion')
        for action in ('check', 'save'):
            self.refused(self.call(action, '--packet', str(packet)), 'Attachment original changed since prepare')
        self.assertEqual(self.captured(), ['.gitkeep'])
        self.assertEqual(list(self.recovery.iterdir()), [])
        self.original.unlink()
        self.refused(self.call('save', '--packet', str(packet)), 'regular non-symlink file')

    def test_original_changed_while_copying_publishes_nothing(self):
        module, settings = self.module()
        packet = json.loads(self.packet().read_text())
        real = module.check_packet

        def check_then_change(*args):
            result = real(*args)
            self.original.write_bytes(PDF.replace(b'inventados', b'alterados!'))
            return result
        with patch.object(module, 'check_packet', side_effect=check_then_change):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        self.assertIn('Bytes changed while copying', caught.exception.result['error'])
        self.assertTrue(caught.exception.result['library_unchanged'])
        self.assertEqual(self.captured(), ['.gitkeep'])
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_hard_link_to_the_original_is_refused_and_rolled_back(self):
        module, settings = self.module()
        packet = json.loads(self.packet().read_text())
        real = module.stage

        def linking_stage(source, directory, sha256, mode=None):
            if isinstance(source, bytes):
                return real(source, directory, sha256, mode)
            temporary = Path(directory) / '.core-capture-linked'
            os.link(source, temporary)
            return temporary
        with patch.object(module, 'stage', side_effect=linking_stage):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        self.assertIn('hard link to the original', caught.exception.result['error'])
        self.assertEqual(caught.exception.result['status'], 'capture_not_saved')
        self.unchanged()
        self.assertEqual(self.original.stat().st_nlink, 1)

    def test_attachment_links_must_be_relative_and_match_declared_targets(self):
        for link, message in (
                ('![[Raw/Sources/otro.pdf]]', 'does not point to a declared attachment target'),
                ('![[informe.pdf]] y ![[figura.png]]', 'does not point to a declared attachment target'),
                ('[PDF](../../../descargas/informe.pdf)', 'must be relative'),
                ('![[../informe.pdf]]', 'does not point to a declared attachment target'),
                ('![[/Raw/Sources/informe.pdf]]', 'must be relative'),
                (f'[PDF](<file://{self.original}>)', 'must be relative'),
                (f'[PDF](<{self.original}>)', 'must be relative'),
                ('[PDF](file:///tmp/informe.pdf)', 'must be relative'),
                ('Sin enlace al adjunto.', 'Every attachment must be linked from the wrapper')):
            with self.subTest(link=link):
                self.refused(self.prepare(wrapper=WRAPPER.replace('![[Raw/Sources/informe.pdf]]', link)), message)
        self.refused(self.prepare(attach=[]), 'does not point to a declared attachment target')
        upward = WRAPPER.replace('![[Raw/Sources/informe.pdf]]', '[PDF](../Sources/informe.pdf)')
        self.assertEqual(self.prepare(wrapper=upward).returncode, 0)
        self.unchanged()

    def test_attachment_type_size_origin_and_target_bounds(self):
        outside = self.original.parent

        def other(name, raw=PDF):
            (outside / name).write_bytes(raw)
            return str(outside / name)
        link = '![[Raw/Sources/informe.pdf]]'
        (self.root / 'Wiki/Notes/dentro.pdf').write_bytes(PDF)
        os.symlink(self.original, outside / 'enlace.pdf')
        for pair, wrapper, message in (
                ((other('a.exe'), 'Raw/Sources/a.exe'), WRAPPER, 'not admitted'),
                ((other('a.svg'), 'Raw/Sources/a.svg'), WRAPPER, 'not admitted'),
                ((other('a.md', b'# nota'), 'Raw/Sources/b.md'), WRAPPER, 'not admitted'),
                ((other('texto.pdf', b'no es un pdf'), 'Raw/Sources/informe.pdf'), WRAPPER, 'do not start like .pdf'),
                ((other('vacio.pdf', b''), 'Raw/Sources/informe.pdf'), WRAPPER, 'do not start like .pdf'),
                ((str(self.original), 'Raw/Sources/informe.png'), WRAPPER.replace('.pdf]]', '.png]]'),
                 'keep the extension'),
                ((str(outside / 'enlace.pdf'), 'Raw/Sources/informe.pdf'), WRAPPER, 'regular non-symlink'),
                ((str(outside / 'ausente.pdf'), 'Raw/Sources/informe.pdf'), WRAPPER, 'regular non-symlink'),
                ((str(self.root / 'Wiki/Notes/dentro.pdf'), 'Raw/Sources/informe.pdf'), WRAPPER,
                 'outside the library'),
                ((str(self.original), 'Wiki/Notes/informe.pdf'), WRAPPER.replace(link, '![[Wiki/Notes/informe.pdf]]'),
                 'inside a declared source folder'),
                ((str(self.original), 'Review/Inbox/informe.pdf'), WRAPPER, 'inside a declared source folder'),
                ((str(self.original), '_templates/informe.pdf'), WRAPPER, 'outside authorized_paths'),
                ((str(self.original), 'informe.pdf'), WRAPPER, 'safe relative path'),
                ((str(self.original), 'Raw/Sources/../Sources/informe.pdf'), WRAPPER, 'safe relative path'),
                ((str(self.original), 'Raw/Sources/.informe.pdf'), WRAPPER, 'safe relative path'),
                ((str(self.original), 'Raw//Sources/informe.pdf'), WRAPPER, 'safe relative path'),
                ((str(self.original), 'Raw/Sources/informe.pdf/'), WRAPPER, 'safe relative path'),
                ((str(self.original), str(self.sources / 'informe.pdf')), WRAPPER, 'safe relative path'),
                ((str(self.original), 'Raw/Sources/nueva/informe.pdf'), WRAPPER, 'does not exist')):
            with self.subTest(pair=pair):
                self.refused(self.prepare(wrapper=wrapper, attach=[pair]), message)
        twice = [(str(self.original), 'Raw/Sources/informe.pdf'), (str(self.original), 'Raw/Sources/Informe.PDF')]
        self.refused(self.prepare(attach=twice), 'Duplicate attachment target')
        many = [(str(self.original), f'Raw/Sources/n{i}.pdf') for i in range(9)]
        self.refused(self.prepare(attach=many), 'at most 8 attachments')
        module, settings = self.module()
        self.assertEqual(module.MAX_ATTACHMENT_BYTES, 512 * 1024 * 1024)
        with patch.object(module, 'MAX_ATTACHMENT_BYTES', len(PDF) - 1):
            with self.assertRaisesRegex(ValueError, 'exceeds byte limit'):
                module.prepare(settings, 'Raw/Sources/informe.md', WRAPPER.encode(),
                               [(str(self.original), 'Raw/Sources/informe.pdf')])
        with patch.object(module, 'MAX_ATTACHMENT_BYTES', len(PDF)):
            module.prepare(settings, 'Raw/Sources/informe.md', WRAPPER.encode(),
                           [(str(self.original), 'Raw/Sources/informe.pdf')])
        self.assertEqual(self.captured(), ['.gitkeep'])

    def test_admitted_signatures_cover_documents_images_and_audio(self):
        module, _ = self.module()
        samples = {'.pdf': b'%PDF-1.4', '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff\xe0', '.jpeg': b'\xff\xd8\xff',
                   '.gif': b'GIF89a', '.webp': b'RIFF0000WEBP', '.epub': b'PK\x03\x04', '.mp3': b'ID3\x04',
                   '.m4a': b'\x00\x00\x00\x20ftypM4A ', '.ogg': b'OggS', '.opus': b'OggS', '.wav': b'RIFF0000WAVE',
                   '.flac': b'fLaC'}
        self.assertEqual(set(samples), set(module.TYPES))
        for extension, head in samples.items():
            self.assertTrue(module.TYPES[extension](head), extension)
            self.assertFalse(module.TYPES[extension](b'MZ\x90\x00 no es ' + extension.encode()), extension)
        self.assertTrue(module.TYPES['.mp3'](b'\xff\xfb\x90'))

    def test_wrapper_must_pass_the_capture_check_and_be_filled(self):
        self.refused(self.prepare(wrapper=WRAPPER.replace('Reference: synthetic:informe-inventado\n', '')),
                     'requires a title and Reference')
        self.refused(self.prepare(wrapper=WRAPPER.replace('role: source', 'role: note')), 'not a derived note')
        self.refused(self.prepare(wrapper=WRAPPER.replace('Referencia para consultar luego.\n', '')),
                     'Capture requires an existing note link')
        self.refused(self.prepare(target='Wiki/Notes/informe.md'), 'within a declared source location')
        for unfilled in (WRAPPER.replace('Title: Informe inventado', 'Title: "{{title}}"'),
                         WRAPPER.replace('# Informe inventado', '# {{title}}'),
                         WRAPPER.replace('luego.', 'luego, {{date:YYYY}} {{ time }}.')):
            self.refused(self.prepare(wrapper=unfilled), 'Template placeholder left unfilled')
        literal = WRAPPER + '\n```\nEl original cita {{date}} como ejemplo.\n```\n'
        self.assertEqual(self.prepare(wrapper=literal).returncode, 0)
        self.unchanged()

    def test_edited_packets_are_refused(self):
        path = self.packet()
        packet = json.loads(path.read_text())

        def rebound(**changes):
            data = {**{k: v for k, v in packet.items() if k != 'packet_sha256'}, **changes}
            data['packet_sha256'] = sha(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                                   separators=(',', ':')).encode())
            return data
        attachment = packet['attachments'][0]
        for edited, message in (
                ({**packet, 'draft': packet['draft'] + 'añadido\n'}, 'Packet content changed'),
                (rebound(draft=packet['draft'] + 'añadido\n'), 'not its check_sha256'),
                (rebound(attachments=[{**attachment, 'sha256': sha(b'otro')}]), 'changed since prepare'),
                (rebound(attachments=[]), 'does not point to a declared attachment target'),
                (rebound(identity={**packet['identity'], 'title': 'Otro'}), 'Capture inputs changed since prepare'),
                (rebound(capture_id='../fuera'), 'Invalid capture_id'),
                (rebound(status='approved'), 'Expected an unapplied capture packet'),
                (rebound(format=None), 'Expected an unapplied capture packet')):
            path.write_text(json.dumps(edited))
            self.refused(self.call('save', '--packet', str(path)), message)
        self.unchanged()

    def test_failed_publication_leaves_no_half_capture(self):
        module, settings = self.module()
        packet = json.loads(self.packet().read_text())
        real, calls = os.link, []

        def second_link_fails(source, target):
            calls.append(target)
            if len(calls) == 2:
                raise OSError('Injected link failure')
            return real(source, target)
        with patch.object(module.os, 'link', side_effect=second_link_fails):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        self.assertEqual(len(calls), 2)
        result = caught.exception.result
        self.assertEqual((result['status'], result['library_unchanged'], result['remaining']),
                         ('capture_not_saved', True, []))
        self.unchanged()
        # Nothing was saved or recorded, so the same reviewed packet is still usable.
        self.assertEqual(module.save(settings, packet)['status'], 'capture_saved')

    def test_failed_final_verification_removes_both_published_files(self):
        module, settings = self.module()
        packet = json.loads(self.packet().read_text())
        real = module.capture_check.check

        def saved_check_fails(*args, **options):
            if options.get('saved'):
                self.assertEqual(len(self.captured()), 5)  # Both published, their temporaries still held.
                raise ValueError('Injected readback failure')
            return real(*args, **options)
        with patch.object(module.capture_check, 'check', side_effect=saved_check_fails):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        self.assertIn('Injected readback failure', caught.exception.result['error'])
        self.unchanged()

    def test_scope_changed_after_the_first_check_stops_before_publication(self):
        module, settings = self.module()
        packet = json.loads(self.packet().read_text())
        real = module.write_record

        def record_then_duplicate(path, record):
            real(path, record)
            (self.sources / 'gemela.md').write_text(WRAPPER.replace('![[Raw/Sources/informe.pdf]]', ''))
        with patch.object(module, 'write_record', side_effect=record_then_duplicate), \
                patch.object(module.os, 'link', side_effect=AssertionError('published before the recheck')):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        self.assertIn('Duplicate reference', caught.exception.result['error'])
        self.assertEqual(self.captured(), ['.gitkeep', 'gemela.md'])
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_unverified_readback_removes_the_capture(self):
        module, settings = self.module()
        packet = json.loads(self.packet().read_text())
        with patch.object(module.note_write, 'read_bytes', return_value=b'otros bytes'):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        self.assertIn('Saved wrapper bytes do not match', caught.exception.result['error'])
        self.unchanged()
        real = module.measure

        def wrong_inside(path, limit=None):
            sha256, size, head, identity = real(path, limit)
            return ('0' * 64 if path.is_relative_to(self.sources.resolve()) else sha256), size, head, identity
        with patch.object(module, 'measure', side_effect=wrong_inside):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        self.assertIn('Saved attachment does not match its bound hash', caught.exception.result['error'])
        self.unchanged()

    def test_unrecoverable_partial_capture_is_reported_and_recorded(self):
        module, settings = self.module()
        packet = json.loads(self.packet().read_text())
        real, calls = os.link, []

        def second_link_fails(source, target):
            calls.append(target)
            if len(calls) == 2:
                raise OSError('Injected link failure')
            return real(source, target)
        with patch.object(module.os, 'link', side_effect=second_link_fails), \
                patch.object(module.os.path, 'samefile', side_effect=OSError('Injected identity failure')):
            with self.assertRaises(module.CaptureError) as caught:
                module.save(settings, packet)
        result = caught.exception.result
        self.assertEqual((result['status'], result['library_unchanged']), ('capture_partial', False))
        self.assertEqual(result['remaining'], ['Raw/Sources/informe.pdf'])
        self.assertEqual(self.captured(), ['.gitkeep', 'informe.pdf'])
        self.assertEqual(json.loads(Path(result['partial_record']).read_text())['remaining'], result['remaining'])
        self.assertEqual(sorted(p.name for p in self.recovery.iterdir()),
                         sorted([Path(result['record']).name, Path(result['partial_record']).name]))

    def test_used_packet_is_not_reusable_after_retirement(self):
        packet = self.packet()
        first = json.loads(packet.read_text())
        self.assertEqual(self.call('save', '--packet', str(packet)).returncode, 0)
        plan = json.loads(self.call('retire', '--target', 'Raw/Sources/informe.md', '--reason', REASON).stdout)
        retired = self.call('retire', '--target', 'Raw/Sources/informe.md', '--reason', REASON,
                            '--expected-sha256', plan['plan_sha256'])
        self.assertEqual(retired.returncode, 0, retired.stderr)
        self.assertEqual(self.captured(), ['.gitkeep'])
        records = sorted(self.recovery.iterdir())
        # The earlier decision covered the earlier capture; the same inputs do not revive it.
        self.assertEqual(self.call('check', '--packet', str(packet)).returncode, 0)
        self.refused(self.call('save', '--packet', str(packet)), 'already used for a save')
        self.assertEqual(self.captured(), ['.gitkeep'])
        self.assertEqual(sorted(self.recovery.iterdir()), records)
        copy = Path(json.loads(retired.stdout)['recovery_copies']) / 'Raw/Sources/informe.pdf'
        again = self.save(attach=[(str(copy), 'Raw/Sources/informe.pdf')])
        self.assertNotEqual(again['capture_id'], first['capture_id'])
        self.assertEqual((self.sources / 'informe.pdf').read_bytes(), PDF)

    def test_writer_needs_plain_files_permission_and_an_unmanaged_library(self):
        (self.root / '.private-engine-install.json').write_text('{}')
        self.refused(self.prepare(), 'Managed library')
        self.refused(self.call('retire', '--target', 'Raw/Sources/informe.md', '--reason', REASON), 'Managed library')
        (self.root / '.private-engine-install.json').unlink()
        packet = self.packet()
        settings = json.loads(self.config.read_text())
        del settings['write_policy'], settings['recovery_directory']
        self.config.write_text(json.dumps(settings))
        self.refused(self.prepare(), 'Plain writing is disabled')
        self.refused(self.call('save', '--packet', str(packet)), 'Plain writing is disabled')
        self.refused(self.call('retire', '--target', 'Raw/Sources/informe.md', '--reason', REASON),
                     'Plain writing is disabled')
        self.unchanged()


class RetireCaptureTests(CaptureWriteCase):
    def setUp(self):
        super().setUp()
        self.save()
        self.wiki = self.root / 'Wiki/Notes/sombra.md'
        self.wiki.write_text('---\nrole: note\nmaturity: seed\n---\n# Sombra\n\nEvidence:: [[Raw/Sources/informe]]\n')
        self.parked = self.root / 'Review/Inbox/aviso.md'
        self.parked.write_text('# Aviso\n\nVer [el PDF](../../Raw/Sources/informe.pdf) y ![[informe.pdf]].\n')

    def retire(self, *args, target='Raw/Sources/informe.md', reason=REASON):
        return self.call('retire', '--target', target, '--reason', reason, *args)

    def plan(self, *args, **options):
        planned = self.retire(*args, **options)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        return json.loads(planned.stdout)

    def tree(self):
        return {p.relative_to(self.home).as_posix(): p.read_bytes()
                for p in sorted(self.home.rglob('*')) if p.is_file()}

    def test_plan_changes_nothing_and_reports_linking_notes(self):
        before = self.tree()
        plan = self.plan()
        self.assertEqual(self.tree(), before)
        self.assertEqual(plan['status'], 'retirement_planned_nothing_changed')
        self.assertEqual(plan['files'], [
            {'path': 'Raw/Sources/informe.md', 'sha256': sha(WRAPPER.encode()), 'bytes': len(WRAPPER.encode())},
            {'path': 'Raw/Sources/informe.pdf', 'sha256': sha(PDF), 'bytes': len(PDF)}])
        self.assertEqual(plan['linked_from'], [
            {'path': 'Review/Inbox/aviso.md', 'links': ['![[informe.pdf]]', '[el PDF](../../Raw/Sources/informe.pdf)'],
             'targets': ['Raw/Sources/informe.pdf'], 'in_sources': False},
            {'path': 'Wiki/Notes/sombra.md', 'links': ['[[Raw/Sources/informe]]'],
             'targets': ['Raw/Sources/informe.md'], 'in_sources': False}])
        self.assertEqual(plan['link_scan'], {'scope': ['Raw', 'Review', 'Wiki'], 'not_checked': []})
        self.assertIn('create-only', plan['rule_excepted'])
        self.assertIn('Owner exception to create-only custody', plan['exception'])

    def test_retirement_moves_the_capture_to_recovery_with_a_verified_record(self):
        notes = (self.wiki.read_bytes(), self.parked.read_bytes())
        plan = self.plan()
        done = self.retire('--expected-sha256', plan['plan_sha256'])
        self.assertEqual(done.returncode, 0, done.stderr)
        result = json.loads(done.stdout)
        self.assertEqual((result['status'], result['human_authentication_verified']), ('capture_retired', False))
        self.assertEqual(result['linked_from'], plan['linked_from'])
        self.assertEqual(self.captured(), ['.gitkeep'])
        self.assertEqual((self.wiki.read_bytes(), self.parked.read_bytes()), notes)
        record_path = Path(result['record'])
        holding = Path(result['recovery_copies'])
        self.assertEqual((record_path.parent, holding.parent), (self.recovery.resolve(),) * 2)
        self.assertEqual(stat.S_IMODE(record_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(holding.stat().st_mode), 0o700)
        record = json.loads(record_path.read_text())
        self.assertEqual(record['format'], 'capture-retirement-v1')
        self.assertEqual((record['reason'], record['target']), (REASON, 'Raw/Sources/informe.md'))
        self.assertEqual(record['files'], plan['files'])
        self.assertEqual((record['exception'], record['rule_excepted']), (plan['exception'], plan['rule_excepted']))
        self.assertEqual(record['linked_from'], plan['linked_from'])
        self.assertRegex(record['date'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$')
        self.assertFalse(record['human_authentication_verified'])
        for item, raw in zip(record['files'], (WRAPPER.encode(), PDF)):
            copy = Path(record['recovery_copies'][item['path']])
            self.assertEqual(copy, holding / item['path'])
            self.assertEqual((copy.read_bytes(), sha(copy.read_bytes())), (raw, item['sha256']))
            self.assertEqual(stat.S_IMODE(copy.stat().st_mode), 0o600)
        self.refused(self.retire('--expected-sha256', plan['plan_sha256']), 'does not exist')

    def test_only_a_capture_wrapper_inside_sources_is_retired(self):
        (self.sources / 'derivada.md').write_text('---\nrole: note\n---\n# Derivada\n')
        before = self.tree()
        for target, message in (
                ('Wiki/Notes/sombra.md', 'inside a declared source location'),
                ('Wiki/Maps/Indice.md', 'inside a declared source location'),
                ('Review/Inbox/aviso.md', 'inside a declared source location'),
                ('Raw/Sources/informe.pdf', 'exact Markdown wrapper'),
                ('Raw/Sources', 'exact Markdown wrapper'),
                ('Raw/Sources/../Sources/informe.md', 'remain inside the library'),
                ('Raw/Sources/ausente.md', 'does not exist'),
                ('AGENTS.md', 'outside authorized_paths'),
                ('_templates/Fuente.md', 'outside authorized_paths'),
                ('Raw/Sources/derivada.md', 'does not declare a captured source')):
            with self.subTest(target=target):
                self.refused(self.retire(target=target), message)
                self.refused(self.retire('--expected-sha256', '0' * 64, target=target), message)
        for reason in ('', '  ', 'dos\nlíneas', 'x' * 513):
            self.refused(self.retire(reason=reason), 'one nonempty line')
        self.assertEqual(self.tree(), before)

    def test_stale_or_missing_plan_hash_retires_nothing(self):
        plan = self.plan()
        before = self.tree()
        self.refused(self.retire('--expected-sha256', sha(WRAPPER.encode())), 'not its plan_sha256')
        self.refused(self.retire('--expected-sha256', plan['plan_sha256'], reason='Otro motivo'), 'show the plan again')
        self.assertEqual(self.tree(), before)
        (self.root / 'Wiki/Notes/nueva.md').write_text('# Nueva\n\n[[Raw/Sources/informe]]\n')
        before = self.tree()
        self.refused(self.retire('--expected-sha256', plan['plan_sha256']), 'show the plan again')
        self.assertEqual(self.tree(), before)

    def test_dangling_or_shared_attachments_are_refused(self):
        shared = self.sources / 'otra.md'
        shared.write_text(WRAPPER.replace('synthetic:informe-inventado', 'synthetic:otra'))
        before = self.tree()
        self.refused(self.retire(), 'Another capture links to an attachment being retired: Raw/Sources/otra.md')
        self.assertEqual(self.tree(), before)
        shared.write_text(WRAPPER.replace('synthetic:informe-inventado', 'synthetic:otra')
                          .replace('informe.pdf', 'perdido.pdf'))
        before = self.tree()
        self.refused(self.retire(target='Raw/Sources/otra.md'), 'Dangling attachment link ![[Raw/Sources/perdido.pdf]]')
        self.assertEqual(self.tree(), before)

    def test_unlinked_files_are_reported_and_retired_only_when_named(self):
        (self.sources / 'informe.epub').write_bytes(b'PK\x03\x04 inventado')
        (self.sources / 'otra.md').write_text(WRAPPER.replace('synthetic:informe-inventado', 'synthetic:otra')
                                              .replace('![[Raw/Sources/informe.pdf]]', 'Sin adjunto.'))
        self.assertEqual(self.plan()['unlinked_siblings'], ['Raw/Sources/informe.epub'])
        self.refused(self.retire('--attachment', 'Raw/Sources/otra.md'), 'another wrapper is retired on its own')
        self.refused(self.retire('--attachment', 'Wiki/Notes/sombra.md'), 'inside a source location')
        self.refused(self.retire('--attachment', 'Raw/Sources/ausente.epub'), 'inside a source location')
        plan = self.plan('--attachment', 'Raw/Sources/informe.epub')
        self.assertEqual([item['path'] for item in plan['files']],
                         ['Raw/Sources/informe.md', 'Raw/Sources/informe.pdf', 'Raw/Sources/informe.epub'])
        self.assertEqual(plan['unlinked_siblings'], [])
        done = self.retire('--attachment', 'Raw/Sources/informe.epub', '--expected-sha256', plan['plan_sha256'])
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.captured(), ['.gitkeep', 'otra.md'])

    def test_unreadable_linking_notes_are_listed_as_not_checked(self):
        (self.root / 'Wiki/Notes/binaria.md').write_bytes(b'\xff\xfe no es utf-8')
        plan = self.plan()
        self.assertEqual([item['path'] for item in plan['link_scan']['not_checked']], ['Wiki/Notes/binaria.md'])

    def test_failed_removal_restores_the_capture_and_leaves_no_recovery_copies(self):
        module, settings = self.module()
        plan = module.retire_plan(settings, 'Raw/Sources/informe.md', REASON, [])
        before, real = self.tree(), os.path.lexists
        still_there = lambda path: str(path).endswith('informe.pdf') or real(path)
        with patch.object(module.os.path, 'lexists', side_effect=still_there):
            with self.assertRaises(module.CaptureError) as caught:
                module.retire(settings, 'Raw/Sources/informe.md', REASON, [], plan['plan_sha256'])
        result = caught.exception.result
        self.assertEqual((result['status'], result['library_unchanged']), ('retirement_not_done', True))
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.captured(), ['.gitkeep', 'informe.md', 'informe.pdf'])

    def test_unverified_recovery_copy_stops_the_retirement(self):
        module, settings = self.module()
        plan = module.retire_plan(settings, 'Raw/Sources/informe.md', REASON, [])
        before, real = self.tree(), os.replace

        def replace_then_corrupt(source, target):
            real(source, target)
            Path(target).write_bytes(b'copia corrupta')
        with patch.object(module.os, 'replace', side_effect=replace_then_corrupt):
            with self.assertRaises(module.CaptureError) as caught:
                module.retire(settings, 'Raw/Sources/informe.md', REASON, [], plan['plan_sha256'])
        self.assertIn('Recovery copy does not match the planned bytes', caught.exception.result['error'])
        self.assertEqual(self.tree(), before)
        real_measure, seen = module.measure, []

        def second_look_differs(path, limit=None):
            result = real_measure(path, limit)
            if path.is_relative_to(self.recovery.resolve()) and path.suffix == '.pdf':
                seen.append(path)
                if len(seen) == 2:
                    return ('0' * 64, *result[1:])
            return result
        with patch.object(module, 'measure', side_effect=second_look_differs):
            with self.assertRaises(module.CaptureError) as caught:
                module.retire(settings, 'Raw/Sources/informe.md', REASON, [], plan['plan_sha256'])
        self.assertIn('Recovery copy does not match the retired bytes', caught.exception.result['error'])
        self.assertTrue(caught.exception.result['library_unchanged'])
        self.assertEqual(self.tree(), before)

    def test_library_rules_copied_before_the_exception_sentence_need_no_migration(self):
        (self.root / 'AGENTS.md').write_text('# Reglas anteriores\n\nCapture is create-only.\n')
        plan = self.plan()
        self.assertEqual(self.retire('--expected-sha256', plan['plan_sha256']).returncode, 0)
        self.assertEqual(self.captured(), ['.gitkeep'])

    def test_capture_changed_during_retirement_is_not_removed(self):
        module, settings = self.module()
        plan = module.retire_plan(settings, 'Raw/Sources/informe.md', REASON, [])
        records, real = sorted(self.recovery.iterdir()), module.write_record

        def record_then_edit(path, record):
            real(path, record)
            (self.sources / 'informe.pdf').write_bytes(PDF + b'editado')
        with patch.object(module, 'write_record', side_effect=record_then_edit):
            with self.assertRaises(module.CaptureError) as caught:
                module.retire(settings, 'Raw/Sources/informe.md', REASON, [], plan['plan_sha256'])
        self.assertIn('changed during retirement', caught.exception.result['error'])
        self.assertTrue(caught.exception.result['library_unchanged'])
        self.assertEqual((self.sources / 'informe.md').read_text(), WRAPPER)
        self.assertEqual((self.sources / 'informe.pdf').read_bytes(), PDF + b'editado')
        self.assertEqual(sorted(self.recovery.iterdir()), records)

    def test_unrestorable_partial_retirement_is_reported_with_its_recovery_copies(self):
        module, settings = self.module()
        plan = module.retire_plan(settings, 'Raw/Sources/informe.md', REASON, [])
        real = os.path.lexists
        still_there = lambda path: str(path).endswith('informe.pdf') or real(path)
        with patch.object(module.os.path, 'lexists', side_effect=still_there), \
                patch.object(module.os, 'link', side_effect=OSError('Injected link failure')):
            with self.assertRaises(module.CaptureError) as caught:
                module.retire(settings, 'Raw/Sources/informe.md', REASON, [], plan['plan_sha256'])
        result = caught.exception.result
        self.assertEqual((result['status'], result['library_unchanged']), ('retirement_partial', False))
        self.assertEqual(result['removed_and_not_restored'], ['Raw/Sources/informe.md', 'Raw/Sources/informe.pdf'])
        self.assertEqual(self.captured(), ['.gitkeep'])
        holding = Path(result['recovery_copies'])
        self.assertEqual((holding / 'Raw/Sources/informe.md').read_text(), WRAPPER)
        self.assertEqual((holding / 'Raw/Sources/informe.pdf').read_bytes(), PDF)
        self.assertTrue(Path(result['record']).is_file())
        self.assertEqual(json.loads(Path(result['partial_record']).read_text())['status'], 'retirement_partial')


if __name__ == '__main__':
    unittest.main()


class CaptureRevisionTest(CaptureWriteCase):
    LEAN = WRAPPER.replace('Referencia para consultar luego.', 'Para consulta.')

    def setUp(self):
        super().setUp()
        self.save()
        self.wrapper = self.sources / 'informe.md'
        self.pdf_sha = sha((self.sources / 'informe.pdf').read_bytes())

    def revise(self, text=None, *extra):
        return self.call('revise', '--target', 'Raw/Sources/informe.md', *extra, stdin=self.LEAN if text is None else text)

    def revision(self, text=None):
        prepared = self.revise(text)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        path = self.home / 'revision.json'
        path.write_text(prepared.stdout)
        return path, json.loads(prepared.stdout)

    def test_revision_replaces_only_the_wrapper_and_keeps_the_previous_text(self):
        path, packet = self.revision()
        self.assertEqual(self.wrapper.read_text(), WRAPPER)  # prepare writes nothing
        self.assertIn('-Referencia para consultar luego.', packet['diff'])
        self.assertEqual(packet['rule_excepted'], 'Capture is create-only: never edit, move, rename or delete a captured original')
        self.assertEqual(self.call('check', '--packet', str(path)).returncode, 0)
        saved = self.call('save', '--packet', str(path))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual(result['status'], 'capture_revised')
        self.assertEqual(self.wrapper.read_text(), self.LEAN)
        self.assertEqual(Path(result['previous_copy']).read_text(), WRAPPER)
        self.assertEqual(stat.S_IMODE(Path(result['previous_copy']).stat().st_mode), 0o600)
        self.assertEqual(sha((self.sources / 'informe.pdf').read_bytes()), self.pdf_sha)
        self.assertEqual(result['attachments_unchanged'], ['Raw/Sources/informe.pdf'])
        self.refused(self.call('save', '--packet', str(path)), 'Wrapper changed')

    def test_owner_edit_after_revise_or_stale_hash_is_refused(self):
        path, _ = self.revision()
        self.wrapper.write_text(WRAPPER + '\nNota del dueño.\n')
        self.refused(self.call('save', '--packet', str(path)), 'Wrapper changed')
        self.refused(self.revise(None, '--expected-sha256', sha(WRAPPER.encode())), 'not the sha256 of the current file')
        self.assertIn('Nota del dueño.', self.wrapper.read_text())

    def test_a_revision_may_add_a_citation_and_keeps_the_identity(self):
        cited = self.LEAN.replace('Reference: synthetic:informe-inventado\n',
                                  'Reference: synthetic:informe-inventado\nCitation: "Paz A. Informe inventado. 2031. doi: 10.1234/prueba"\n')
        path, packet = self.revision(cited)
        self.assertEqual(packet['identity']['reference'], 'synthetic:informe-inventado')
        saved = self.call('save', '--packet', str(path))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertIn('Citation: "Paz A. Informe inventado. 2031. doi: 10.1234/prueba"', self.wrapper.read_text())

    def test_identity_and_attachments_cannot_change_in_a_revision(self):
        self.refused(self.revise(self.LEAN.replace('synthetic:informe-inventado', 'synthetic:otro')),
                     'keeps the source identity')
        self.refused(self.revise(self.LEAN.replace('![[Raw/Sources/informe.pdf]]', 'Sin enlace.')),
                     'keeps its attachment links')
        self.refused(self.revise(self.LEAN.replace('informe.pdf', 'otro.pdf')), 'does not name a captured file')
        self.refused(self.revise(WRAPPER), 'identical to the current wrapper')
        self.refused(self.revise(self.LEAN.replace('Para consulta.', '{{title}}')), 'placeholder')

    def test_only_a_capture_wrapper_in_sources_is_revised(self):
        refused = self.call('revise', '--target', 'Wiki/Maps/Indice.md', stdin=self.LEAN)
        self.assertEqual(refused.returncode, 2)
        refused = self.call('revise', '--target', 'Raw/Sources/ausente.md', stdin=self.LEAN)
        self.assertEqual(refused.returncode, 2)

    def test_edited_revision_packet_is_refused(self):
        path, packet = self.revision()
        packet['draft'] = packet['draft'] + 'extra\n'
        path.write_text(json.dumps(packet))
        self.refused(self.call('save', '--packet', str(path)), 'Packet content changed')
        self.assertEqual(self.wrapper.read_text(), WRAPPER)

    def test_failed_replace_leaves_the_wrapper_and_no_previous_copy(self):
        path, packet = self.revision()
        module, settings = self.module()
        with patch.object(module.os, 'replace', side_effect=OSError('simulated')):
            with self.assertRaises(module.CaptureError) as caught:
                module.save_revision(settings, packet)
        self.assertEqual(caught.exception.result['status'], 'revision_not_saved')
        self.assertEqual(self.wrapper.read_text(), WRAPPER)
        self.assertFalse(any(p.name.startswith('revision-') for p in self.recovery.iterdir()))
