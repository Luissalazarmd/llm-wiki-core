"""View writer on a copied starter library: .canvas, .base and Markdown views, never knowledge; synthetic only."""
import copy
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
WRITER = BASE / 'scripts/view_write.py'
STARTER = BASE / 'examples/starter-library'
NAME = 'Mapa.canvas'
CANVAS = {
    'nodes': [
        {'id': 'grupo', 'type': 'group', 'x': -20, 'y': -20, 'width': 900, 'height': 400, 'label': 'Lectura'},
        {'id': 'indice', 'type': 'file', 'x': 0, 'y': 0, 'width': 400, 'height': 300,
         'file': 'Wiki/Maps/Indice.md'},
        {'id': 'nota', 'type': 'text', 'x': 460, 'y': 0, 'width': 380, 'height': 120, 'text': 'Empieza aquí.',
         'color': '4'},
    ],
    'edges': [{'id': 'lee', 'fromNode': 'nota', 'fromSide': 'left', 'toNode': 'indice', 'toSide': 'right',
               'toEnd': 'arrow', 'label': 'abre', 'color': '#00AA00'}],
}
DASHBOARD = '---\nrole: view\n---\n# Tablero\n\n![[Biblioteca.base#Panorama]]\n'


def sha(raw):
    return hashlib.sha256(raw if isinstance(raw, bytes) else raw.encode()).hexdigest()


def canvas(change=None):
    data = copy.deepcopy(CANVAS)
    if change:
        change(data)
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


class ViewWriteCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='view-write-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'casa privada ñ'
        self.home.mkdir()
        self.root = self.home / 'library'
        shutil.copytree(STARTER, self.root)
        self.config = self.home / 'library.json'
        shutil.copyfile(BASE / 'examples/starter-library.config.example.json', self.config)
        self.recovery = self.home / 'recovery'
        self.recovery.mkdir()
        self.before = self.tree()

    def tree(self):
        return {p.relative_to(self.root).as_posix(): None if p.is_dir() else p.read_bytes()
                for p in sorted(self.root.rglob('*')) if not p.is_symlink()}

    def call(self, *args, stdin=None, script='view_write.py'):
        return subprocess.run([sys.executable, str(BASE / 'scripts' / script), '--config', str(self.config), *args],
                              input=stdin, text=True, capture_output=True, timeout=20,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def prepare(self, text=None, target=NAME, expected=None):
        return self.call('prepare', '--target', target,
                         *(() if expected is None else ('--expected-sha256', expected)),
                         stdin=canvas() if text is None else text)

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
        """No view written, replaced, staged or recorded."""
        self.assertEqual(self.tree(), self.before)
        self.assertEqual(list(self.recovery.iterdir()), [])

    def settings(self, **changes):
        data = json.loads(self.config.read_text())
        data.update(changes)
        self.config.write_text(json.dumps(data))

    def views_folder(self, folder='Vistas'):
        (self.root / folder).mkdir(parents=True)
        layers = json.loads(self.config.read_text())['layers']
        self.settings(layers={**layers, 'views': [folder]})
        self.before = self.tree()

    def module(self):
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('view_write', WRITER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, module.library.load_config(self.config)


class NewViewTests(ViewWriteCase):
    def test_new_canvas_is_shown_exactly_then_created_once(self):
        text = canvas()
        checked = self.call('check', '--target', NAME, stdin=text)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        facts = {'kind': 'canvas', 'lines': len(text.splitlines()), 'nodes': 3, 'edges': 1,
                 'file_cards': ['Wiki/Maps/Indice.md'], 'unverified_subpaths': [], 'link_urls': [],
                 'text_cards': 1, 'text_characters': len('Empieza aquí.'), 'unknown_keys': []}
        self.assertEqual(json.loads(checked.stdout), {
            'status': 'view_structure_checked_not_saved', 'target': NAME, 'exists': False, 'current_sha256': None,
            'draft_sha256': sha(text), **facts, 'semantic_validation': False, 'approval_available': False})
        packet = json.loads(self.packet().read_text())
        self.assertEqual((packet['status'], packet['operation'], packet['target'], packet['draft'],
                          packet['draft_sha256'], packet['base_sha256'], packet['facts'],
                          packet['approval_available']),
                         ('prepared_not_approved', 'create', NAME, text, sha(text), None, facts, False))
        self.assertTrue(packet['diff'].startswith('--- /dev/null\n'))
        self.assertIn('+      "file": "Wiki/Maps/Indice.md"\n', packet['diff'])
        self.unchanged()  # check and prepare write nothing
        current = self.call('check', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(json.loads(current.stdout)['status'], 'view_inputs_current')
        saved = self.call('save', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual((result['status'], result['kind'], result['sha256'], result['previous_copy'],
                          result['human_authentication_verified']),
                         ('view_created', 'canvas', sha(text), None, False))
        self.assertEqual((self.root / NAME).read_bytes(), text.encode())
        self.assertEqual(self.tree(), dict(self.before, **{NAME: text.encode()}))  # no temporaries, nothing else
        record = json.loads(Path(result['record']).read_text())
        self.assertEqual((record['format'], record['packet'], record['previous_copy']),
                         ('view-recovery-v1', packet, None))
        self.assertEqual([p.name for p in self.recovery.iterdir()], [f"view-{packet['view_id']}.json"])
        self.assertEqual(stat.S_IMODE(Path(result['record']).stat().st_mode), 0o600)

    def test_saved_view_is_not_library_content(self):
        self.save()
        self.save(text=DASHBOARD, target='Tablero.md')
        mapped = self.call('map', '--scope', 'Raw', '--scope', 'Review', '--scope', 'Wiki', script='library.py')
        self.assertEqual(mapped.returncode, 0, mapped.stderr)
        self.assertNotIn(NAME, mapped.stdout)
        self.assertNotIn('Tablero', mapped.stdout)

    def test_base_and_markdown_views_are_created_in_the_root_and_in_a_declared_folder(self):
        self.views_folder()
        base = (STARTER / 'Biblioteca.base').read_text()
        for target, text, kind in (('Lecturas.base', base, 'base'), ('Vistas/Lecturas.base', base, 'base'),
                                   ('Tablero.md', DASHBOARD, 'markdown'), ('Vistas/Tablero.md', DASHBOARD, 'markdown'),
                                   ('Vistas/' + NAME, canvas(), 'canvas')):
            with self.subTest(target=target):
                result = self.save(text=text, target=target)
                self.assertEqual((result['status'], result['kind'], result['target']), ('view_created', kind, target))
                self.assertEqual((self.root / target).read_text(), text)

    def test_check_reads_without_write_permission_but_prepare_needs_it(self):
        self.settings(write_policy='read_only')
        self.assertEqual(self.call('check', '--target', NAME, stdin=canvas()).returncode, 0)
        self.refused(self.prepare(), 'Plain writing is disabled')
        self.settings(write_policy='plain_files')
        (self.root / '.wanderloots-llm-wiki').mkdir()
        self.refused(self.prepare(), 'Managed library')

    def test_shipped_starter_base_passes_check_and_home_is_adopted_by_declaring_itself(self):
        base = (STARTER / 'Biblioteca.base').read_text()
        checked = self.call('check', '--target', 'Biblioteca.base', stdin=base)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        result = json.loads(checked.stdout)
        self.assertEqual((result['exists'], result['current_sha256'], result['unknown_keys']), (True, sha(base), []))
        self.assertIn('Panorama', result['views'])
        home = (STARTER / 'Home.md').read_text()
        self.refused(self.call('check', '--target', 'Home.md', stdin=home), 'declares role: view')
        declared = '---\nrole: view\n---\n' + home
        saved = self.save(text=declared, target='Home.md', expected=sha(home))
        self.assertEqual(saved['status'], 'view_replaced')
        self.assertEqual(Path(saved['previous_copy']).read_text(), home)
        self.assertEqual((self.root / 'Home.md').read_text(), declared)


class ScopeTests(ViewWriteCase):
    def test_target_must_be_a_view_in_the_root_or_a_declared_folder(self):
        (self.root / 'Wiki/Notes/nota.md').write_text('---\nrole: note\n---\n# Nota\n')
        self.views_folder()
        (self.root / 'Vistas/home.md').write_text(DASHBOARD)
        self.before = self.tree()
        cases = {
            '../fuera.canvas': 'inside the library', '/tmp/fuera.canvas': 'inside the library',
            'Vistas/../Wiki/Notes/x.canvas': 'inside the library', 'a\\b.canvas': 'inside the library',
            '.obsidian/workspace.canvas': 'inside the library', 'Vistas/.oculta.canvas': 'inside the library',
            ' Mapa.canvas': 'inside the library', 'a[b].canvas': 'inside the library',
            'a#b.canvas': 'inside the library', 'x' * 121 + '.canvas': 'inside the library',
            './Mapa.canvas': 'inside the library', '': 'inside the library',
            'Mapa.txt': '.canvas, .base or .md', 'Mapa': '.canvas, .base or .md', 'Mapa.CANVAS': '.canvas, .base or .md',
            'Mapa.json': '.canvas, .base or .md', '.obsidian/app.json': 'inside the library',
            'Wiki/Mapa.canvas': 'layers.views', 'Wiki/Notes/Mapa.canvas': 'layers.views',
            'Wiki/Notes/nota.md': 'layers.views', 'Raw/Sources/Mapa.canvas': 'layers.views',
            'Review/Inbox/Mapa.canvas': 'layers.views', '_templates/Mapa.canvas': 'layers.views',
            '_templates/Fuente.md': 'layers.views', 'Ausente/Mapa.canvas': 'existing real directory',
            'Home.md/Mapa.canvas': 'existing real directory',
            'AGENTS.md': 'instruction or rules files', 'Vistas/agents.md': 'instruction or rules files',
            'CLAUDE.md': 'instruction or rules files', 'Vistas/SKILL.md': 'instruction or rules files',
            'SOUL.md': 'instruction or rules files', 'Gemini.md': 'instruction or rules files',
            'Vistas/Home.md': 'differing only by case', 'home.canvas': None,
        }
        for target, message in cases.items():
            for action in ('check', 'prepare'):
                with self.subTest(target=target, action=action):
                    result = self.call(action, '--target', target, stdin=DASHBOARD if target.endswith('.md')
                                       else canvas())
                    if message is None:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.refused(result, message)
        self.save()
        self.refused(self.prepare(target='mapa.canvas'), 'differing only by case')

    def test_views_never_land_in_originals_proposals_or_retained_knowledge(self):
        # A root file the settings select as a source, a proposal or knowledge is still theirs.
        for layer, name in (('sources', 'Fuente.md'), ('knowledge', 'Idea.md'), ('drafts', 'Borrador.md')):
            with self.subTest(layer=layer):
                (self.root / name).write_text('# Texto\n')
                self.settings(authorized_paths=['Raw', 'Review', 'Wiki', name], ingest_custody=False,
                              layers={'sources': ['Raw'], 'knowledge': ['Wiki'], layer:
                                      [*{'sources': ['Raw'], 'knowledge': ['Wiki']}.get(layer, []), name]})
                self.refused(self.call('check', '--target', name, stdin=DASHBOARD), f'inside layers.{layer}')
                self.refused(self.call('prepare', '--target', name, stdin=DASHBOARD), f'inside layers.{layer}')
                (self.root / name).unlink()

    def test_root_markdown_selected_as_content_goes_through_the_note_writer(self):
        (self.root / 'Idea.md').write_text('# Una idea sin metadatos\n')
        self.settings(authorized_paths=['Raw', 'Review', 'Wiki', 'Idea.md'])
        self.refused(self.prepare(DASHBOARD, 'Idea.md', sha('# Una idea sin metadatos\n')), 'selected as library content')
        self.assertEqual(self.call('check', '--target', 'Idea.canvas', stdin=canvas()).returncode, 0)

    def test_declared_views_folders_are_exact_existing_directories_outside_every_other_layer(self):
        layers = json.loads(self.config.read_text())['layers']
        (self.root / 'Vistas').mkdir()
        (self.root / 'Wiki/Vistas').mkdir()
        for folder, message in (('Ausente', 'does not exist'), ('Home.md', 'exact existing directories'),
                                ('Vistas/', 'exact existing directories'), ('../fuera', 'inside the library'),
                                ('.obsidian', 'Hidden'), ('Wiki', 'must not overlap layers.knowledge'),
                                ('Wiki/Vistas', 'must not overlap layers.knowledge'),
                                ('Raw', 'must not overlap layers.sources'),
                                ('Raw/Sources', 'must not overlap layers.sources'),
                                ('Review', 'must not overlap layers.proposals'),
                                ('Review/Inbox', 'must not overlap layers.proposals')):
            with self.subTest(folder=folder):
                self.settings(layers={**layers, 'views': [folder]})
                self.refused(self.call('check', '--target', NAME, stdin=canvas()), message)
        self.settings(layers={**layers, 'views': 'Vistas'})
        self.refused(self.call('check', '--target', NAME, stdin=canvas()), 'path lists')
        # The owner may carve a views folder out of an authorized location by declaring knowledge precisely.
        self.settings(layers={**layers, 'knowledge': ['Wiki/Notes', 'Wiki/Maps'], 'views': ['Wiki/Vistas']})
        self.assertEqual(self.call('check', '--target', 'Wiki/Vistas/' + NAME, stdin=canvas()).returncode, 0)
        self.refused(self.call('check', '--target', 'Wiki/Maps/' + NAME, stdin=canvas()), 'layers.views')
        self.settings(layers={**layers, 'knowledge': ['Wiki/Notes', 'Wiki/Maps'], 'views': ['Wiki/Vistas']},
                      living_synthesis={'scopes': ['Wiki'], 'history_complete': True})
        self.refused(self.call('check', '--target', 'Wiki/Vistas/' + NAME, stdin=canvas()), 'numbered')

    def test_templates_folder_cannot_be_declared_as_views(self):
        layers = json.loads(self.config.read_text())['layers']
        self.settings(layers={**layers, 'views': ['_templates']})
        text = (STARTER / '_templates/Fuente.md').read_text()
        self.refused(self.call('check', '--name', 'Fuente.md', stdin=text, script='template_write.py'), 'overlaps')

    def test_symlinks_are_refused(self):
        outside = self.home / 'fuera'
        outside.mkdir()
        (outside / 'Mapa.canvas').write_text(canvas())
        (outside / 'Indice.md').write_text('# Fuera\n')
        cases = {
            'view': (NAME, lambda: (self.root / NAME).symlink_to(outside / 'Mapa.canvas')),
            'dangling view': (NAME, lambda: (self.root / NAME).symlink_to(outside / 'ausente.canvas')),
            'views folder': ('Vistas/' + NAME, lambda: ((self.root / 'Vistas').rmdir(),
                                                       (self.root / 'Vistas').symlink_to(outside, True))),
            'views folder into sources': ('Vistas/' + NAME, lambda: (
                (self.root / 'Vistas').rmdir(), (self.root / 'Vistas').symlink_to(self.root / 'Raw/Sources', True))),
            'subfolder': ('Vistas/Sub/' + NAME, lambda: (self.root / 'Vistas/Sub').symlink_to(outside, True)),
            'file card': (NAME, lambda: ((self.root / 'Wiki/Maps/Indice.md').unlink(),
                                         (self.root / 'Wiki/Maps/Indice.md').symlink_to(outside / 'Indice.md'))),
            'file card folder': (NAME, lambda: (shutil.rmtree(self.root / 'Wiki/Maps'),
                                                (self.root / 'Wiki/Maps').symlink_to(outside, True))),
        }
        layers = json.loads(self.config.read_text())['layers']
        self.settings(layers={**layers, 'views': ['Vistas']})
        for label, (target, link) in cases.items():
            with self.subTest(symlink=label):
                shutil.rmtree(self.root)
                shutil.copytree(STARTER, self.root)
                (self.root / 'Vistas').mkdir()
                link()
                for action, extra in (('check', ()), ('prepare', ()),
                                      ('prepare', ('--expected-sha256', sha(canvas())))):
                    result = self.call(action, '--target', target, *extra, stdin=canvas())
                    self.assertEqual((result.returncode, result.stdout), (2, ''), label)
                    self.assertIn('View is not a regular non-symlink file' if 'view' in label.split()[-1:]
                                  else 'ymlink', json.loads(result.stderr)['error'])
                self.assertEqual(sorted(p.name for p in outside.iterdir()), ['Indice.md', 'Mapa.canvas'])
                self.assertEqual((outside / 'Mapa.canvas').read_text(), canvas())
                self.assertEqual(sorted(p.name for p in (self.root / 'Raw/Sources').iterdir()), ['.gitkeep'])
                self.assertEqual(list(self.recovery.iterdir()), [])

    def test_a_folder_named_like_a_view_is_not_replaced(self):
        (self.root / NAME).mkdir()
        self.refused(self.call('check', '--target', NAME, stdin=canvas()), 'View is not a regular non-symlink file')

    def test_folder_swapped_for_a_symlink_after_prepare_is_refused(self):
        self.views_folder()
        packet = self.packet(target='Vistas/' + NAME)
        outside = self.home / 'fuera'
        (self.root / 'Vistas').rename(outside)
        (self.root / 'Vistas').symlink_to(outside, True)
        self.refused(self.call('save', '--packet', str(packet)), 'ymlink')
        self.assertFalse((outside / NAME).exists())
        self.assertEqual(list(self.recovery.iterdir()), [])


class CanvasValidationTests(ViewWriteCase):
    def test_each_invalid_canvas_is_refused_and_nothing_is_written(self):
        node = lambda data, i=1: data['nodes'][i]
        edge = lambda data: data['edges'][0]
        cases = {
            'duplicate node id': (lambda d: node(d, 2).update(id='indice'), 'Duplicate canvas id'),
            'edge id reuses a node id': (lambda d: edge(d).update(id='nota'), 'Duplicate canvas id'),
            'duplicate edge id': (lambda d: d['edges'].append(dict(edge(d))), 'Duplicate canvas id'),
            'missing id': (lambda d: node(d).pop('id'), 'nonempty string "id"'),
            'empty id': (lambda d: node(d).update(id=''), 'nonempty string "id"'),
            'numeric id': (lambda d: node(d).update(id=7), 'nonempty string "id"'),
            'node is not an object': (lambda d: d['nodes'].append('nota'), 'nonempty string "id"'),
            'unknown type': (lambda d: node(d).update(type='card'), 'type must be text, file, link or group'),
            'missing type': (lambda d: node(d).pop('type'), 'type must be text, file, link or group'),
            'float x': (lambda d: node(d).update(x=1.5), '"x" must be an integer'),
            'string y': (lambda d: node(d).update(y='0'), '"y" must be an integer'),
            'boolean width': (lambda d: node(d).update(width=True), '"width" must be an integer'),
            'missing height': (lambda d: node(d).pop('height'), '"height" must be an integer'),
            'zero width': (lambda d: node(d).update(width=0), 'width and height must be positive'),
            'negative height': (lambda d: node(d).update(height=-10), 'width and height must be positive'),
            'bad preset color': (lambda d: node(d).update(color='7'), 'color is a preset'),
            'bad hex color': (lambda d: edge(d).update(color='#00AA0'), 'color is a preset'),
            'numeric color': (lambda d: node(d).update(color=4), 'color is a preset'),
            'text card without text': (lambda d: node(d, 2).pop('text'), '"text" must be a string'),
            'file card without file': (lambda d: node(d).pop('file'), '"file" must be a string'),
            'link card without url': (lambda d: node(d, 2).update(type='link'), '"url" must be a string'),
            'local url': (lambda d: node(d, 2).update(type='link', url='file:///etc/passwd'), 'http or https'),
            'script url': (lambda d: node(d, 2).update(type='link', url='javascript:alert(1)'), 'http or https'),
            'app url': (lambda d: node(d, 2).update(type='link', url='obsidian://open?vault=x'), 'http or https'),
            'group label': (lambda d: node(d, 0).update(label=3), '"label" must be a string'),
            'group background style': (lambda d: node(d, 0).update(backgroundStyle='tile'), 'backgroundStyle'),
            'group background missing': (lambda d: node(d, 0).update(background='Raw/fondo.png'),
                                         'points to a missing library file'),
            'dangling fromNode': (lambda d: edge(d).update(fromNode='ausente'), '"fromNode" must be the id of a node'),
            'dangling toNode': (lambda d: edge(d).update(toNode='lee'), '"toNode" must be the id of a node'),
            'missing toNode': (lambda d: edge(d).pop('toNode'), '"toNode" must be the id of a node'),
            'unhashable fromNode': (lambda d: edge(d).update(fromNode=['nota']), '"fromNode" must be the id'),
            'bad side': (lambda d: edge(d).update(fromSide='center'), '"fromSide" must be one of'),
            'bad end': (lambda d: edge(d).update(toEnd='circle'), '"toEnd" must be one of'),
            'edge label': (lambda d: edge(d).update(label=['abre']), '"label" must be a string'),
            'nodes is not an array': (lambda d: d.update(nodes={}), '"nodes" and "edges" are arrays'),
            'edges is not an array': (lambda d: d.update(edges='lee'), '"nodes" and "edges" are arrays'),
        }
        raw = {
            'empty': ('\n', 'nonempty'),
            'oversized': (canvas(lambda d: d['nodes'][2].update(text='x' * 262144)), 'at most 262144 bytes'),
            'not json': ('{"nodes": [', 'not valid JSON'),
            'array': ('[]\n', 'JSON object'),
            'duplicate key': ('{"nodes": [], "nodes": []}', 'Duplicate JSON key'),
            'non-finite': ('{"nodes": [{"id": "a", "type": "text", "text": "", "x": NaN, "y": 0, "width": 1, '
                           '"height": 1}]}', 'Non-finite'),
            'yaml instead': ((STARTER / 'Biblioteca.base').read_text(), 'not valid JSON'),
        }
        raw.update({label: (canvas(change), message) for label, (change, message) in cases.items()})
        for label, (text, message) in raw.items():
            for action in ('check', 'prepare'):
                with self.subTest(case=label, action=action):
                    self.refused(self.call(action, '--target', NAME, stdin=text), message)
        self.unchanged()

    def test_non_utf8_view_is_refused(self):
        result = subprocess.run([sys.executable, str(WRITER), '--config', str(self.config), 'check', '--target', NAME],
                                input=canvas().encode() + b'\xff', capture_output=True, timeout=20)
        self.assertEqual((result.returncode, result.stdout), (2, b''))
        self.unchanged()

    def test_file_cards_must_point_to_existing_library_files(self):
        card = lambda d: d['nodes'][1]
        for file, message in (('Wiki/Maps/Ausente.md', 'points to a missing library file'),
                              ('Wiki/Maps', 'points to a missing library file'),
                              ('Indice', 'points to a missing library file'),
                              ('../fuera.md', 'visible library-relative path'),
                              ('/etc/passwd', 'visible library-relative path'),
                              ('Wiki\\Maps\\Indice.md', 'visible library-relative path'),
                              ('.obsidian/templates.json', 'visible library-relative path'),
                              ('Wiki/Maps/../Maps/Indice.md', 'visible library-relative path'),
                              (7, 'must be a string')):
            with self.subTest(file=file):
                self.refused(self.call('check', '--target', NAME, stdin=canvas(lambda d: card(d).update(file=file))),
                             message)
        packet = self.packet()
        (self.root / 'Wiki/Maps/Indice.md').rename(self.root / 'Wiki/Maps/Inicio.md')
        for action in ('check', 'save'):  # a card that stopped resolving after review is not saved
            self.refused(self.call(action, '--packet', str(packet)), 'points to a missing library file')
        self.assertFalse((self.root / NAME).exists())
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_heading_and_block_subpaths_must_exist(self):
        (self.root / 'Wiki/Notes/nota.md').write_text(
            '---\nrole: note\n---\n# Nota\n\n## Sombra  y luz ##\n\nUn párrafo citado. ^cita\n\n'
            '```\n## Solo en código\n```\n### Límites\n')
        (self.root / 'Raw/Sources/informe.pdf').write_bytes(b'%PDF-1.4 sintetico')
        card = lambda d: d['nodes'][1]
        check = lambda **fields: self.call('check', '--target', NAME,
                                           stdin=canvas(lambda d: card(d).update(**fields)))
        for subpath in ('#Nota', '#sombra y LUZ', '#Nota#Límites', '#^cita'):
            with self.subTest(subpath=subpath):
                result = check(file='Wiki/Notes/nota.md', subpath=subpath)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['file_cards'], ['Wiki/Notes/nota.md' + subpath])
        for subpath, message in (('#Ausente', 'subpath does not exist'), ('#Solo en código', 'subpath does not exist'),
                                 ('#Nota#Ausente', 'subpath does not exist'), ('#^otra', 'subpath does not exist'),
                                 ('#Nota#', 'subpath does not exist'), ('Nota', 'starting with #'),
                                 ('#', 'starting with #'), (3, 'starting with #')):
            with self.subTest(subpath=subpath):
                self.refused(check(file='Wiki/Notes/nota.md', subpath=subpath), message)
        self.refused(check(file='_templates/Fuente.md', subpath='#Original'), 'cannot be verified')
        self.assertEqual(check(file='_templates/Fuente.md').returncode, 0)  # existence only, content unread
        self.assertEqual(check(file='Home.md', subpath='#De un vistazo').returncode, 0)
        unverified = json.loads(check(file='Raw/Sources/informe.pdf', subpath='#page=3').stdout)
        self.assertEqual(unverified['unverified_subpaths'], ['Raw/Sources/informe.pdf#page=3'])

    def test_links_text_and_unknown_attributes_are_reported_for_review(self):
        def change(data):
            data['nodes'].append({'id': 'web', 'type': 'link', 'x': 0, 'y': 400, 'width': 300, 'height': 100,
                                  'url': 'https://example.org/a?b=1', 'styleAttributes': {}})
            data['metadata'] = {'version': '1.0-1.0'}
            data['edges'][0]['styleAttributes'] = {}
        result = json.loads(self.call('check', '--target', NAME, stdin=canvas(change)).stdout)
        self.assertEqual((result['link_urls'], result['unknown_keys'], result['text_cards']),
                         (['https://example.org/a?b=1'], ['metadata', 'styleAttributes'], 1))
        self.assertEqual(json.loads(self.call('check', '--target', NAME, stdin='{}').stdout)['nodes'], 0)


class BaseAndMarkdownValidationTests(ViewWriteCase):
    def test_each_invalid_base_is_refused(self):
        cases = {
            'invalid yaml': ('views:\n  - type: table\n name: x\n', 'not valid YAML'),
            'tab indentation': ('views:\n\t- type: table\n', 'not valid YAML'),
            'list': ('- type: table\n', 'must be a YAML mapping'),
            'scalar': ('table\n', 'must be a YAML mapping'),
            'only a comment': ('# vacío\n', 'must be a YAML mapping'),
            'json canvas': ('[1, 2]\n', 'must be a YAML mapping'),
            'duplicate key': ('views: []\nviews: []\n', 'plain and unique'),
            'nested duplicate key': ('formulas:\n  a: "1"\n  a: "2"\n', 'plain and unique'),
            'alias': ('formulas: &f\n  a: "1"\nsummaries: *f\n', 'aliases'),
            'views mapping': ('views:\n  type: table\n', '"views" has the wrong shape'),
            'view without type': ('views:\n  - name: Panorama\n', 'string "type"'),
            'view scalar': ('views:\n  - table\n', 'string "type"'),
            'view name': ('views:\n  - type: table\n    name: [a]\n', 'string "type"'),
            'filters list': ('filters:\n  - a\n', '"filters" has the wrong shape'),
            'formulas list': ('formulas:\n  - a\n', '"formulas" has the wrong shape'),
            'formula number': ('formulas:\n  unidad: 1\n', 'expression strings'),
            'summary mapping': ('summaries:\n  media:\n    a: b\n', 'expression strings'),
            'properties string': ('properties: nota\n', '"properties" has the wrong shape'),
            'property setting': ('properties:\n  note.autor: Autor\n', 'maps each property'),
        }
        for label, (text, message) in cases.items():
            for action in ('check', 'prepare'):
                with self.subTest(case=label, action=action):
                    self.refused(self.call(action, '--target', 'Lecturas.base', stdin=text), message)
        self.unchanged()
        minimal = json.loads(self.call('check', '--target', 'Lecturas.base',
                                       stdin='filters: \'file.ext == "md"\'\nnuevo: 1\nviews:\n  - type: table\n').stdout)
        self.assertEqual((minimal['views'], minimal['unknown_keys']), ([None], ['nuevo']))

    def test_markdown_view_declares_itself_and_nothing_that_belongs_to_knowledge(self):
        cases = {
            'no frontmatter': ('# Tablero\n', 'declares role: view'),
            'note': (DASHBOARD.replace('role: view', 'role: note'), 'declares role: view'),
            'map': (DASHBOARD.replace('role: view', 'role: map'), 'declares role: view'),
            'source': (DASHBOARD.replace('role: view', 'role: source'), 'declares role: view'),
            'unclosed': ('---\nrole: view\n# Tablero\n', 'Unclosed frontmatter'),
            'maturity': (DASHBOARD.replace('role: view', 'role: view\nmaturity: seed'), 'declares no maturity'),
            'owner origin': (DASHBOARD.replace('role: view', 'role: view\norigin: owner'), 'declares no origin'),
            'parked proposal': (DASHBOARD.replace('role: view', 'role: view\nproposal_status: pending'),
                                'declares no proposal_status'),
            'numbered': (DASHBOARD.replace('role: view', 'role: view\nprimary_moc: Wiki/Maps/Indice.md\naddress: "001-01"'),
                         'declares no address, primary_moc'),
        }
        for label, (text, message) in cases.items():
            for action in ('check', 'prepare'):
                with self.subTest(case=label, action=action):
                    self.refused(self.call(action, '--target', 'Tablero.md', stdin=text), message)
        self.unchanged()

    def test_existing_markdown_that_is_not_a_view_is_never_replaced(self):
        self.views_folder()
        for label, current in (('note', '---\nrole: note\nmaturity: seed\n---\n# Idea\n'),
                               ('map', '---\nrole: map\n---\n# Mapa\n'),
                               ('source', '---\nrole: source\nTitle: x\nReference: y\n---\n# Fuente\n'),
                               ('parked', '---\nproposal_status: pending\n---\n# Propuesta\n'),
                               ('seed without role', '---\norigin: owner\n---\n# Idea\n'),
                               ('unreadable', '---\nrole: [view\n---\n# Roto\n')):
            with self.subTest(current=label):
                path = self.root / 'Vistas/Tablero.md'
                path.write_text(current)
                for action, extra in (('check', ()), ('prepare', ('--expected-sha256', sha(current)))):
                    self.refused(self.call(action, '--target', 'Vistas/Tablero.md', *extra, stdin=DASHBOARD),
                                 'is not a view')
                self.assertEqual(path.read_text(), current)
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_note_and_capture_writers_do_not_take_a_view_and_this_one_takes_no_note(self):
        note = '---\nrole: note\nmaturity: seed\norigin: owner\n---\n# Una idea\n'
        for target in ('Idea.md', 'Wiki/Notes/Idea.md'):
            self.refused(self.call('prepare', '--target', target, stdin=note), 'role: view' if target == 'Idea.md'
                         else 'layers.views')
        self.unchanged()


class ChangeTests(ViewWriteCase):
    def setUp(self):
        super().setUp()
        self.current = canvas()
        (self.root / NAME).write_text(self.current)
        self.before = self.tree()
        self.changed = canvas(lambda d: d['nodes'][2].update(text='Empieza por el mapa.'))

    def test_existing_view_is_never_overwritten_without_its_current_hash(self):
        self.refused(self.prepare(self.changed), 'requires --expected-sha256')
        self.refused(self.prepare(self.changed, expected=sha('otra versión')), 'not the sha256 of the current file')
        self.refused(self.prepare(self.changed, expected=sha(self.changed)), 'not the sha256 of the current file')
        self.refused(self.prepare(self.current, expected=sha(self.current)), 'nothing to change')
        self.refused(self.prepare(target='Otro.canvas', expected=sha(self.current)), 'takes no --expected-sha256')
        self.unchanged()

    def test_change_keeps_the_previous_version_in_private_recovery_then_replaces(self):
        path = self.root / NAME
        path.chmod(0o640)
        packet = json.loads(self.packet(text=self.changed, expected=sha(self.current)).read_text())
        self.assertEqual((packet['operation'], packet['base_sha256'], packet['draft']),
                         ('replace', sha(self.current), self.changed))
        self.assertIn('-      "text": "Empieza aquí.",\n+      "text": "Empieza por el mapa.",\n', packet['diff'])
        self.assertEqual(path.read_text(), self.current)
        saved = self.call('save', '--packet', str(self.home / 'packet.json'))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual((result['status'], result['sha256'], result['previous_sha256']),
                         ('view_replaced', sha(self.changed), sha(self.current)))
        self.assertEqual(path.read_text(), self.changed)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        kept = Path(result['previous_copy'])
        self.assertEqual((kept.parent, kept.suffix), (self.recovery, '.canvas'))
        self.assertEqual(kept.read_text(), self.current)
        self.assertEqual(stat.S_IMODE(kept.stat().st_mode), 0o600)
        self.assertEqual(json.loads(Path(result['record']).read_text())['previous_copy'], str(kept))
        self.assertEqual(self.tree(), dict(self.before, **{NAME: self.changed.encode()}))  # no temporaries

    def test_owner_edit_after_prepare_is_preserved(self):
        packet = self.packet(text=self.changed, expected=sha(self.current))
        owner = canvas(lambda d: d['nodes'][0].update(label='Mi lectura'))
        (self.root / NAME).write_text(owner)
        for action in ('check', 'save'):
            self.refused(self.call(action, '--packet', str(packet)), 'not the sha256 of the current file')
        self.assertEqual((self.root / NAME).read_text(), owner)
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_packet_saves_once(self):
        packet = self.packet(target='Otro.canvas')
        self.assertEqual(self.call('save', '--packet', str(packet)).returncode, 0)
        self.refused(self.call('save', '--packet', str(packet)), 'already exists')
        (self.root / 'Otro.canvas').unlink()  # even with the target absent again, the decision was used
        self.refused(self.call('save', '--packet', str(packet)), 'already used for a save')
        self.assertFalse((self.root / 'Otro.canvas').exists())
        self.assertEqual(len(list(self.recovery.iterdir())), 1)

    def test_change_packet_saves_once_even_if_the_old_version_returns(self):
        path = self.root / NAME
        packet = self.packet(text=self.changed, expected=sha(self.current))
        self.assertEqual(self.call('save', '--packet', str(packet)).returncode, 0)
        self.refused(self.call('save', '--packet', str(packet)), 'not the sha256 of the current file')
        path.write_text(self.current)
        records = sorted(p.name for p in self.recovery.iterdir())
        self.refused(self.call('save', '--packet', str(packet)), 'already used for a save')
        self.assertEqual(path.read_text(), self.current)
        self.assertEqual(sorted(p.name for p in self.recovery.iterdir()), records)

    def test_altered_or_foreign_packet_is_refused(self):
        path = self.packet(target='Otro.canvas')
        packet = json.loads(path.read_text())
        path.write_text(json.dumps(dict(packet, draft=packet['draft'] + ' ')))
        self.refused(self.call('save', '--packet', str(path)), 'Packet content changed')
        path.write_text(json.dumps(dict(packet, status='approved')))
        self.refused(self.call('save', '--packet', str(path)), 'unapplied view packet')

        def forged(**changes):
            data = {k: v for k, v in dict(packet, **changes).items() if k != 'packet_sha256'}
            data['packet_sha256'] = sha(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')))
            path.write_text(json.dumps(data))
            return self.call('save', '--packet', str(path))
        self.refused(forged(view_id='../../fuera'), 'Invalid view_id')  # the id names the private record
        self.refused(forged(target='Wiki/Notes/Otro.canvas'), 'layers.views')
        self.refused(forged(target='../Otro.canvas'), 'inside the library')
        self.refused(forged(operation='replace'), 'inputs changed since prepare')
        self.refused(forged(facts=dict(packet['facts'], file_cards=[])), 'inputs changed since prepare')
        path.write_text(json.dumps(packet))
        self.refused(self.call('save', '--packet', str(path), script='capture_write.py'), 'unapplied capture packet')
        self.refused(self.call('save', '--packet', str(path), script='template_write.py'), 'unapplied template packet')
        self.refused(self.call('save', '--packet', str(path), script='note_write.py'), 'Unsupported proposal format')
        self.unchanged()

    def test_failed_publication_leaves_library_and_recovery_as_they_were(self):
        module, settings = self.module()
        for label, target, text, expected, call in (('create', 'Otro.canvas', self.current, None, 'link'),
                                                    ('replace', NAME, self.changed, sha(self.current), 'replace')):
            with self.subTest(operation=label):
                packet = module.prepare(settings, target, text.encode(), expected)
                real = getattr(os, call)

                def failing(source, destination, real=real):
                    if Path(destination).parent == self.root:
                        raise OSError('fallo inyectado')
                    return real(source, destination)

                with patch.object(module.os, call, failing), \
                        self.assertRaises(module.capture_write.CaptureError) as caught:
                    module.save(settings, packet)
                self.assertEqual((caught.exception.result['status'], caught.exception.result['library_unchanged']),
                                 ('view_not_saved', True))
                self.unchanged()

    def test_unverified_replacement_is_reported_as_partial_with_the_previous_copy(self):
        module, settings = self.module()
        packet = module.prepare(settings, NAME, self.changed.encode(), sha(self.current))
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
                         ('view_partial', False, [NAME]))
        self.assertEqual(Path(result['previous_copy']).read_text(), self.current)
        self.assertTrue(Path(result['record']).is_file())
        self.assertTrue(Path(result['partial_record']).is_file())


class ShippedExampleTests(unittest.TestCase):
    """The Obsidian workbench opens the Core checkout as its vault, so that is the library root here."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='view-example-')
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / 'core.json'
        self.config.write_text(json.dumps({
            'version': 1, 'library_root': str(BASE), 'authorized_paths': ['Agents', 'docs'],
            'layers': {'views': ['examples/obsidian']}}))

    def check(self, name):
        text = (BASE / 'examples/obsidian' / name).read_text()
        result = subprocess.run([sys.executable, str(WRITER), '--config', str(self.config), 'check', '--target',
                                 'examples/obsidian/' + name], input=text, text=True, capture_output=True,
                                timeout=20, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual((data['exists'], data['current_sha256'], data['unknown_keys']), (True, sha(text), []))
        return data

    def test_shipped_canvas_passes_check_with_every_card_and_heading_resolved(self):
        data = self.check('Arquitectura.canvas')
        self.assertEqual((data['kind'], data['nodes'], data['edges'], data['unverified_subpaths'], data['link_urls']),
                         ('canvas', 24, 12, [], []))
        self.assertEqual(len(data['file_cards']), 6)
        self.assertIn('docs/review-contract.md#Common human-review loop', data['file_cards'])

    def test_shipped_base_passes_check(self):
        data = self.check('Biblioteca.base')
        self.assertEqual(data['kind'], 'base')
        self.assertTrue({'Panorama', 'Atencion', 'Recientes'} <= set(data['views']))


class DocumentationTests(unittest.TestCase):
    def test_views_are_documented_and_reached_from_the_entry_points(self):
        views = ' '.join((BASE / 'docs/views.md').read_text().split())
        for statement in ('navigation, not knowledge', 'view_write.py', '--expected-sha256', 'layers.views',
                          'role: view', 'JSON Canvas 1.0', 'Not a back door', 'never `.obsidian`',
                          'write for the reader'):
            self.assertIn(statement, views)
        self.assertIn('(views.md)', (BASE / 'docs/first-cut-tools.md').read_text())
        self.assertIn('view_write.py', (BASE / 'docs/first-cut-tools.md').read_text())
        self.assertIn('docs/views.md', (BASE / 'skills/review-save/SKILL.md').read_text().replace('../../', ''))
        self.assertIn('views.md', (BASE / 'docs/review-contract.md').read_text())
        rules = ' '.join((STARTER / 'AGENTS.md').read_text().split())
        self.assertIn('A view is created or changed only', rules)
        self.assertEqual(sorted(p.name for p in (BASE / 'skills').iterdir()),
                         ['capture-source', 'ingesta', 'progressive-adoption', 'read-connect', 'review-save'])


if __name__ == '__main__':
    unittest.main()
