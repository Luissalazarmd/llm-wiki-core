"""Template writer on a copied starter library: blank source-wrapper shapes only; synthetic only."""
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
WRITER = BASE / 'scripts/template_write.py'
STARTER = BASE / 'examples/starter-library'
PODCAST = ('---\nrole: source\nTitle: "{{title}}"\nReference:\nVersion:\nauthors:\nshow:\nepisode:\n'
           'captured: "{{date}}T{{time}}"\n---\n# {{title}}\n\n## Contexto de captura\n\n'
           '## Marcas de tiempo\n\n## Original\n')
NAME = 'Fuente-podcast.md'


def sha(raw):
    return hashlib.sha256(raw if isinstance(raw, bytes) else raw.encode()).hexdigest()


class TemplateWriteCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='template-write-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'casa privada ñ'
        self.home.mkdir()
        self.root = self.home / 'library'
        shutil.copytree(STARTER, self.root)
        self.config = self.home / 'library.json'
        shutil.copyfile(BASE / 'examples/starter-library.config.example.json', self.config)
        self.recovery = self.home / 'recovery'
        self.recovery.mkdir()
        self.folder = self.root / '_templates'
        self.before = self.tree()

    def tree(self):
        return {p.relative_to(self.root).as_posix(): None if p.is_dir() else p.read_bytes()
                for p in sorted(self.root.rglob('*')) if not p.is_symlink()}

    def call(self, *args, stdin=None, script='template_write.py'):
        return subprocess.run([sys.executable, str(BASE / 'scripts' / script), '--config', str(self.config), *args],
                              input=stdin, text=True, capture_output=True, timeout=20,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def prepare(self, text=PODCAST, name=NAME, expected=None):
        return self.call('prepare', '--name', name, *(() if expected is None else ('--expected-sha256', expected)),
                         stdin=text)

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

    def unchanged(self):
        """No template written, replaced, staged or recorded."""
        self.assertEqual(self.tree(), self.before)
        self.assertEqual(list(self.recovery.iterdir()), [])

    def settings(self, **changes):
        data = json.loads(self.config.read_text())
        data.update(changes)
        self.config.write_text(json.dumps(data))

    def obsidian(self, folder):
        (self.root / '.obsidian/templates.json').write_text(json.dumps({'folder': folder}))
        self.before = self.tree()

    def module(self):
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('template_write', WRITER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, module.library.load_config(self.config)


class NewTemplateTests(TemplateWriteCase):
    def test_new_template_is_shown_exactly_then_created_once(self):
        checked = self.call('check', '--name', NAME, stdin=PODCAST)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout), {
            'status': 'template_structure_checked_not_saved', 'target': '_templates/' + NAME, 'exists': False,
            'current_sha256': None, 'draft_sha256': sha(PODCAST),
            'placeholders': ['{{date}}', '{{time}}', '{{title}}'], 'fills_into_capture_wrapper': True,
            'capture_policy_checked': False, 'semantic_validation': False, 'approval_available': False})
        packet = json.loads(self.packet().read_text())
        self.assertEqual((packet['status'], packet['operation'], packet['target'], packet['draft'],
                          packet['draft_sha256'], packet['base_sha256'], packet['approval_available']),
                         ('prepared_not_approved', 'create', '_templates/' + NAME, PODCAST, sha(PODCAST), None,
                          False))
        self.assertTrue(packet['diff'].startswith('--- /dev/null\n'))
        self.unchanged()  # check and prepare write nothing
        current = self.call('check', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(json.loads(current.stdout)['status'], 'template_inputs_current')
        saved = self.call('save', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual((result['status'], result['sha256'], result['previous_copy'], result['folder_created'],
                          result['human_authentication_verified']),
                         ('template_created', sha(PODCAST), None, False, False))
        self.assertEqual((self.folder / NAME).read_bytes(), PODCAST.encode())
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()),
                         sorted([NAME, *(p.name for p in (STARTER / '_templates').iterdir())]))
        record = json.loads(Path(result['record']).read_text())
        self.assertEqual((record['format'], record['packet'], record['previous_copy']),
                         ('template-recovery-v1', packet, None))
        self.assertEqual([p.name for p in self.recovery.iterdir()], [f"template-{packet['template_id']}.json"])
        self.assertEqual(stat.S_IMODE(Path(result['record']).stat().st_mode), 0o600)

    def test_saved_template_is_not_library_content_and_fills_into_a_capture(self):
        self.save()
        mapped = self.call('map', '--scope', 'Raw', '--scope', 'Review', '--scope', 'Wiki', script='library.py')
        self.assertNotIn('podcast', mapped.stdout)
        wrapper = ((self.folder / NAME).read_text().replace('{{title}}', 'Episodio inventado')
                   .replace('{{date}}', '2026-11-12').replace('{{time}}', '09:30')
                   .replace('Reference:\n', 'Reference: synthetic:episodio\n')
                   .replace('## Contexto de captura\n', '## Contexto de captura\nPara escuchar luego.\n'))
        captured = self.call('prepare', '--target', 'Raw/Sources/episodio.md', stdin=wrapper,
                             script='capture_write.py')
        self.assertEqual(captured.returncode, 0, captured.stderr)

    def test_all_shipped_starter_templates_pass_check(self):
        names = sorted(p.name for p in (STARTER / '_templates').iterdir())
        self.assertEqual(len(names), 5)
        for name in names:
            with self.subTest(template=name):
                text = (STARTER / '_templates' / name).read_text()
                checked = self.call('check', '--name', name, stdin=text)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                result = json.loads(checked.stdout)
                self.assertEqual((result['exists'], result['current_sha256'], result['placeholders']),
                                 (True, sha(text), ['{{date}}', '{{time}}', '{{title}}']))
        self.unchanged()

    def test_format_placeholders_and_english_heading_are_accepted(self):
        text = (PODCAST.replace('"{{date}}T{{time}}"', '"{{date:YYYY-MM-DD}} {{time:HH:mm}}"')
                .replace('Contexto de captura', 'Capture context').replace('Title: "{{title}}"', 'Title:'))
        checked = self.call('check', '--name', NAME, stdin=text)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)['placeholders'],
                         ['{{date:YYYY-MM-DD}}', '{{time:HH:mm}}', '{{title}}'])

    def test_check_reads_without_write_permission_but_prepare_needs_it(self):
        self.settings(write_policy='read_only')
        self.assertEqual(self.call('check', '--name', NAME, stdin=PODCAST).returncode, 0)
        self.refused(self.prepare(), 'Plain writing is disabled')
        self.settings(write_policy='plain_files')
        (self.root / '.wanderloots-llm-wiki').mkdir()
        self.refused(self.prepare(), 'Managed library')


class ValidationTests(TemplateWriteCase):
    def test_each_invalid_template_is_refused_and_nothing_is_written(self):
        cases = {
            'empty': ('\n', 'nonempty'),
            'oversized': (PODCAST + 'x' * 262144, 'at most 262144 bytes'),
            'no frontmatter': (PODCAST.split('---\n', 2)[2], 'role: source'),
            'unclosed frontmatter': (PODCAST.replace('\n---\n# ', '\n# '), 'Unclosed frontmatter'),
            'derived role': (PODCAST.replace('role: source', 'role: note'), 'role: source'),
            'no role': (PODCAST.replace('role: source\n', ''), 'role: source'),
            'no Title': (PODCAST.replace('Title: "{{title}}"\n', ''), 'keys Title and Reference'),
            'lowercase title': (PODCAST.replace('Title:', 'title:'), 'keys Title and Reference'),
            'no Reference': (PODCAST.replace('Reference:\n', ''), 'keys Title and Reference'),
            'concrete Title': (PODCAST.replace('"{{title}}"', 'Episodio 12'), 'Title must be empty or {{title}}'),
            'concrete Reference': (PODCAST.replace('Reference:', 'Reference: https://example.org/e12'),
                                   'Reference must be empty'),
            'concrete Version': (PODCAST.replace('Version:', 'Version: v2'), 'Version must be empty'),
            'concrete id': (PODCAST.replace('authors:', 'id: episodio-12'), 'id must be empty'),
            'no context section': (PODCAST.replace('## Contexto de captura\n', ''), 'Contexto de captura'),
            'context only in code': (PODCAST.replace('## Contexto de captura\n', '```\n## Contexto de captura\n```\n'),
                                     'Contexto de captura'),
            'foreign placeholder': (PODCAST.replace('authors:', 'authors: "{{author}}"'), 'only the Obsidian core'),
            'spaced placeholder': (PODCAST.replace('# {{title}}', '# {{ title }}'), 'only the Obsidian core'),
            'empty format': (PODCAST.replace('{{date}}', '{{date:}}'), 'only the Obsidian core'),
            'plugin syntax': (PODCAST + '<% tp.file.cursor() %>\n', 'only the Obsidian core'),
            'attachment embed': (PODCAST + '![[Raw/Sources/episodio.mp3]]\n', 'links an attachment'),
            'attachment link': (PODCAST + '[audio](Raw/Sources/episodio.mp3)\n', 'links an attachment'),
            'local file link': (PODCAST + '[nota](file:///home/x/nota.txt)\n', 'links an attachment'),
            'second reference': (PODCAST + 'Reference:: https://example.org/e12\n',
                                 'does not fill into a valid capture wrapper'),
            'quoted key': (PODCAST.replace('Reference:', '"Reference":'), 'Write Reference as its own plain'),
            'filled is too large': (PODCAST.replace('authors:', 'authors: "' + 'x' * (262130 - len(PODCAST)) + '"'),
                                    'does not fill into a valid capture wrapper'),
        }
        for label, (text, message) in cases.items():
            for action in ('check', 'prepare'):
                with self.subTest(case=label, action=action):
                    self.refused(self.call(action, '--name', NAME, stdin=text), message)
        self.unchanged()

    def test_non_utf8_template_is_refused(self):
        result = subprocess.run([sys.executable, str(WRITER), '--config', str(self.config), 'check', '--name', NAME],
                                input=PODCAST.encode() + b'\xff', capture_output=True, timeout=20)
        self.assertEqual((result.returncode, result.stdout), (2, b''))
        self.unchanged()

    def test_name_must_be_a_plain_markdown_filename_in_the_templates_folder(self):
        for name in ('../Fuente.md', 'sub/Fuente.md', '/tmp/Fuente.md', '..md', '.oculta.md', 'Fuente.txt', 'Fuente',
                     'Fuente.MD', '.md', 'a[b].md', 'a|b.md', 'a#b.md', 'a\\b.md', ' Fuente.md', 'AGENTS.md',
                     'Skill.md', '../Raw/Sources/Fuente.md', 'x' * 121 + '.md'):
            for action in ('check', 'prepare'):
                with self.subTest(name=name, action=action):
                    self.refused(self.call(action, '--name', name, stdin=PODCAST), 'plain .md filename')
        self.refused(self.prepare(name='fuente.md'), 'differing only by case')
        self.unchanged()

    def test_template_needs_a_source_folder_to_prove_the_filled_wrapper(self):
        self.settings(layers={'sources': [], 'knowledge': ['Wiki']}, ingest_custody=False)
        self.refused(self.call('check', '--name', NAME, stdin=PODCAST), 'needs a declared source folder')

    def test_a_stronger_capture_policy_does_not_block_a_template(self):
        (self.root / 'Wiki/Maps/Taxonomia.md').write_text('---\nrole: map\ntags: [medicina]\n---\n# Taxonomía\n')
        self.settings(capture_policy={'roots': ['Wiki/Maps/Indice.md'], 'taxonomy_path': 'Wiki/Maps/Taxonomia.md'})
        checked = self.call('check', '--name', NAME, stdin=PODCAST)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertFalse(json.loads(checked.stdout)['capture_policy_checked'])


class ChangeTests(TemplateWriteCase):
    def setUp(self):
        super().setUp()
        self.current = (self.folder / 'Fuente-articulo.md').read_text()
        self.changed = self.current.replace('journal:\n', 'journal:\ndoi:\n')
        self.assertNotEqual(self.current, self.changed)

    def test_existing_template_is_never_overwritten_without_its_current_hash(self):
        self.refused(self.prepare(self.changed, 'Fuente-articulo.md'), 'requires --expected-sha256')
        self.refused(self.prepare(self.changed, 'Fuente-articulo.md', sha('otra versión')),
                     'not the sha256 of the current file')
        self.refused(self.prepare(self.changed, 'Fuente-articulo.md', sha(self.changed)),
                     'not the sha256 of the current file')
        self.refused(self.prepare(self.current, 'Fuente-articulo.md', sha(self.current)), 'nothing to change')
        self.refused(self.prepare(expected=sha(PODCAST)), 'takes no --expected-sha256')
        self.unchanged()

    def test_change_keeps_the_previous_version_in_private_recovery_then_replaces(self):
        path = self.folder / 'Fuente-articulo.md'
        path.chmod(0o640)
        packet = json.loads(self.packet(text=self.changed, name='Fuente-articulo.md',
                                        expected=sha(self.current)).read_text())
        self.assertEqual((packet['operation'], packet['base_sha256'], packet['draft']),
                         ('replace', sha(self.current), self.changed))
        self.assertIn('+doi:\n', packet['diff'])
        self.assertEqual(path.read_text(), self.current)
        saved = self.call('save', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual((result['status'], result['sha256'], result['previous_sha256']),
                         ('template_replaced', sha(self.changed), sha(self.current)))
        self.assertEqual(path.read_text(), self.changed)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        copy = Path(result['previous_copy'])
        self.assertEqual(copy.parent, self.recovery)
        self.assertEqual(copy.read_text(), self.current)
        self.assertEqual(stat.S_IMODE(copy.stat().st_mode), 0o600)
        self.assertEqual(json.loads(Path(result['record']).read_text())['previous_copy'], str(copy))
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()),
                         sorted(p.name for p in (STARTER / '_templates').iterdir()))  # no temporaries
        after = dict(self.before, **{'_templates/Fuente-articulo.md': self.changed.encode()})
        self.assertEqual(self.tree(), after)

    def test_owner_edit_after_prepare_is_preserved(self):
        packet = self.packet(text=self.changed, name='Fuente-articulo.md', expected=sha(self.current))
        owner = self.current + '\n## Notas del propietario\n'
        (self.folder / 'Fuente-articulo.md').write_text(owner)
        for action in ('check', 'save'):
            self.refused(self.call(action, '--packet', str(packet)), 'not the sha256 of the current file')
        self.assertEqual((self.folder / 'Fuente-articulo.md').read_text(), owner)
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_packet_saves_once(self):
        packet = self.packet()
        self.assertEqual(self.call('save', '--packet', str(packet)).returncode, 0)
        self.refused(self.call('save', '--packet', str(packet)), 'already exists')
        (self.folder / NAME).unlink()  # even with the target absent again, the decision was used
        self.refused(self.call('save', '--packet', str(packet)), 'already used for a save')
        self.assertFalse((self.folder / NAME).exists())
        self.assertEqual(len(list(self.recovery.iterdir())), 1)

    def test_change_packet_saves_once_even_if_the_old_version_returns(self):
        path = self.folder / 'Fuente-articulo.md'
        packet = self.packet(text=self.changed, name='Fuente-articulo.md', expected=sha(self.current))
        self.assertEqual(self.call('save', '--packet', str(packet)).returncode, 0)
        self.refused(self.call('save', '--packet', str(packet)), 'not the sha256 of the current file')
        path.write_text(self.current)
        records = sorted(p.name for p in self.recovery.iterdir())
        self.refused(self.call('save', '--packet', str(packet)), 'already used for a save')
        self.assertEqual(path.read_text(), self.current)
        self.assertEqual(sorted(p.name for p in self.recovery.iterdir()), records)

    def test_altered_or_foreign_packet_is_refused(self):
        path = self.packet()
        packet = json.loads(path.read_text())
        path.write_text(json.dumps(dict(packet, draft=packet['draft'] + 'más\n')))
        self.refused(self.call('save', '--packet', str(path)), 'Packet content changed')
        path.write_text(json.dumps(dict(packet, status='approved')))
        self.refused(self.call('save', '--packet', str(path)), 'unapplied template packet')
        forged = dict(packet, template_id='../../fuera')  # the id names the private record
        del forged['packet_sha256']
        forged['packet_sha256'] = sha(json.dumps(forged, sort_keys=True, ensure_ascii=False, separators=(',', ':')))
        path.write_text(json.dumps(forged))
        self.refused(self.call('save', '--packet', str(path)), 'Invalid template_id')
        path.write_text(json.dumps(packet))
        self.refused(self.call('save', '--packet', str(path), script='capture_write.py'), 'unapplied capture packet')
        self.refused(self.call('save', '--packet', str(path), script='note_write.py'), 'Unsupported proposal format')
        self.unchanged()

    def test_failed_publication_leaves_library_and_recovery_as_they_were(self):
        module, settings = self.module()
        for label, name, text, expected, call in (
                ('create', NAME, PODCAST, None, 'link'),
                ('replace', 'Fuente-articulo.md', self.changed, sha(self.current), 'replace')):
            with self.subTest(operation=label):
                packet = module.prepare(settings, name, text.encode(), expected)
                real = getattr(os, call)

                def failing(source, destination, real=real):
                    if Path(destination).parent == self.folder:
                        raise OSError('fallo inyectado')
                    return real(source, destination)

                with patch.object(module.os, call, failing), self.assertRaises(module.capture_write.CaptureError) as caught:
                    module.save(settings, packet)
                self.assertEqual((caught.exception.result['status'], caught.exception.result['library_unchanged']),
                                 ('template_not_saved', True))
                self.unchanged()

    def test_unverified_replacement_is_reported_as_partial_with_the_previous_copy(self):
        module, settings = self.module()
        packet = module.prepare(settings, 'Fuente-articulo.md', self.changed.encode(), sha(self.current))
        real_replace, real_read, state = os.replace, module.note_write.read_bytes, {}

        def replace(source, destination):
            real_replace(source, destination)
            state['replaced'] = True

        def read(path, *args):
            return b'otra cosa' if state.get('replaced') else real_read(path, *args)

        with patch.object(module.os, 'replace', replace), patch.object(module.note_write, 'read_bytes', read), \
                self.assertRaises(module.capture_write.CaptureError) as caught:
            module.save(settings, packet)
        result = caught.exception.result
        self.assertEqual((result['status'], result['library_unchanged'], result['remaining']),
                         ('template_partial', False, ['_templates/Fuente-articulo.md']))
        self.assertEqual(Path(result['previous_copy']).read_text(), self.current)
        self.assertTrue(Path(result['record']).is_file())
        self.assertTrue(Path(result['partial_record']).is_file())


class FolderTests(TemplateWriteCase):
    def test_custom_folder_comes_from_the_obsidian_setting(self):
        (self.root / 'Plantillas').mkdir()
        for folder in ('Plantillas', 'Plantillas/'):
            with self.subTest(folder=folder):
                self.obsidian(folder)
                checked = self.call('check', '--name', NAME, stdin=PODCAST)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertEqual(json.loads(checked.stdout)['target'], 'Plantillas/' + NAME)
        self.assertEqual(self.save()['target'], 'Plantillas/' + NAME)
        self.assertEqual((self.root / 'Plantillas' / NAME).read_text(), PODCAST)
        self.assertFalse((self.folder / NAME).exists())

    def test_default_folder_applies_without_a_setting_or_a_folder_key(self):
        (self.root / '.obsidian/templates.json').write_text('{"dateFormat": "YYYY-MM-DD"}')
        self.assertEqual(json.loads(self.call('check', '--name', NAME, stdin=PODCAST).stdout)['target'],
                         '_templates/' + NAME)
        shutil.rmtree(self.root / '.obsidian')
        self.assertEqual(self.save()['target'], '_templates/' + NAME)

    def test_first_approved_save_creates_a_missing_templates_folder(self):
        self.obsidian('Meta/Plantillas')
        checked = self.call('check', '--name', NAME, stdin=PODCAST)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        packet = self.packet()
        self.unchanged()  # neither check nor prepare creates the folder
        saved = self.call('save', '--packet', str(packet))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertTrue(json.loads(saved.stdout)['folder_created'])
        self.assertEqual([p.name for p in (self.root / 'Meta/Plantillas').iterdir()], [NAME])
        self.assertEqual((self.root / 'Meta/Plantillas' / NAME).read_text(), PODCAST)
        self.assertEqual(self.save(name='Otra.md')['folder_created'], False)

    def test_failed_first_save_removes_the_folder_it_created(self):
        self.obsidian('Meta/Plantillas')
        module, settings = self.module()
        packet = module.prepare(settings, NAME, PODCAST.encode())
        with patch.object(module.os, 'link', side_effect=OSError('fallo inyectado')), \
                self.assertRaises(module.capture_write.CaptureError) as caught:
            module.save(settings, packet)
        self.assertEqual(caught.exception.result['status'], 'template_not_saved')
        self.assertFalse((self.root / 'Meta').exists())
        self.unchanged()

    def test_templates_folder_must_stay_inside_the_library_and_outside_its_layers(self):
        (self.root / 'Raw/Plantillas').mkdir()
        for folder, message in (('../fuera', 'inside the library'), ('/', 'inside the library'),
                                ('', 'inside the library'), ('a/../b', 'inside the library'),
                                ('.obsidian/plantillas', 'inside the library'), ('a\\b', 'inside the library'),
                                (str(self.home / 'fuera'), 'inside the library'),
                                ('Raw', 'overlaps'), ('Raw/Plantillas', 'overlaps'), ('Raw/Sources', 'overlaps'),
                                ('Review', 'overlaps'), ('Review/Inbox', 'overlaps'), ('Wiki/Plantillas', 'overlaps'),
                                ('Home.md', 'real directory'), (7, '"folder" is a string')):
            with self.subTest(folder=folder):
                self.obsidian(folder)
                for action in ('check', 'prepare'):
                    self.refused(self.call(action, '--name', NAME, stdin=PODCAST), message)
                self.unchanged()
        (self.root / '.obsidian/templates.json').write_text('{"folder": ')
        self.assertEqual(self.call('check', '--name', NAME, stdin=PODCAST).returncode, 2)
        (self.root / '.obsidian/templates.json').write_text('["_templates"]')
        self.refused(self.call('check', '--name', NAME, stdin=PODCAST), '"folder" is a string')

    def test_symlinks_are_refused(self):
        outside = self.home / 'fuera'
        outside.mkdir()
        (outside / 'Fuente.md').write_text(PODCAST)
        refusal = {'template': 'Template is not a regular non-symlink file',
                   'dangling template': 'Template is not a regular non-symlink file'}
        cases = {
            'template': lambda: (self.folder / NAME).symlink_to(outside / 'Fuente.md'),
            'dangling template': lambda: (self.folder / NAME).symlink_to(outside / 'ausente.md'),
            'folder': lambda: (shutil.rmtree(self.folder), self.folder.symlink_to(outside, True)),
            'folder into sources': lambda: (shutil.rmtree(self.folder),
                                            self.folder.symlink_to(self.root / 'Raw/Sources', True)),
            'setting': lambda: ((self.root / '.obsidian/templates.json').unlink(),
                                (self.root / '.obsidian/templates.json').symlink_to(outside / 'templates.json')),
            'setting folder': lambda: (shutil.rmtree(self.root / '.obsidian'),
                                       (self.root / '.obsidian').symlink_to(outside, True)),
        }
        (outside / 'templates.json').write_text('{"folder": "_templates"}')
        for label, link in cases.items():
            with self.subTest(symlink=label):
                shutil.rmtree(self.root)
                shutil.copytree(STARTER, self.root)
                link()
                for action, extra in (('check', ()), ('prepare', ()), ('prepare', ('--expected-sha256', sha(PODCAST)))):
                    result = self.call(action, '--name', NAME, *extra, stdin=PODCAST)
                    self.assertEqual((result.returncode, result.stdout), (2, ''), label)
                    self.assertIn(refusal.get(label, 'ymlink'), json.loads(result.stderr)['error'])
                self.assertEqual(sorted(p.name for p in outside.iterdir()), ['Fuente.md', 'templates.json'])
                self.assertEqual((outside / 'Fuente.md').read_text(), PODCAST)
                self.assertEqual(sorted(p.name for p in (self.root / 'Raw/Sources').iterdir()), ['.gitkeep'])
                self.assertEqual(list(self.recovery.iterdir()), [])

    def test_folder_swapped_for_a_symlink_after_prepare_is_refused(self):
        packet = self.packet()
        outside = self.home / 'fuera'
        self.folder.rename(outside)
        self.folder.symlink_to(outside, True)
        self.refused(self.call('save', '--packet', str(packet)), 'symlink')
        self.assertFalse((outside / NAME).exists())
        self.assertEqual(list(self.recovery.iterdir()), [])


class DocumentationTests(unittest.TestCase):
    def test_capture_documentation_carries_the_template_path(self):
        admission = ' '.join((BASE / 'docs/raw-admission.md').read_text().split())
        for statement in ('## Templates', 'template_write.py', 'shape, not approval', 'never sources',
                          'progressive adoption', "never replace the owner's existing templates",
                          'core-plugins.json', '--expected-sha256'):
            self.assertIn(statement, admission)
        skill = (BASE / 'skills/capture-source/SKILL.md').read_text()
        self.assertIn('template_write.py', skill)
        self.assertIn('raw-admission.md#templates', skill)
        self.assertEqual(sorted(p.name for p in (BASE / 'skills').iterdir()),
                         ['capture-source', 'ingesta', 'progressive-adoption', 'read-connect', 'review-save'])


if __name__ == '__main__':
    unittest.main()
