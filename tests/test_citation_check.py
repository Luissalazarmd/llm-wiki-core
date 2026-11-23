"""Citation report over fictional notes. Passing shows structure and words, never that a claim follows."""
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support  # noqa: F401  real temp dir for symlink-refusing helpers

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
import citation_check as c

TODAY = date(2031, 9, 1)


class CitationCheckTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.write('Raw/acta.md', '# Acta\n\n## Cierre\n\nEl envío se hizo el lunes y\nno se corrigió.\n\n'
                                  '## Doble\n\n## Doble\n\nÚltima línea. ^final\n')
        self.write('Raw/datos.yaml', 'estado: "enviado"\n')
        (self.root / 'Raw/foto.jpg').write_bytes(b'\xff\xd8\xff\x00')

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def note(self, body, meta='role: note\nmaturity: synthesis'):
        self.write('Wiki/n.md', f'---\n{meta}\n---\n{body}\n')

    def read(self, relative):
        root = c.open_root(self.root)
        try:
            return c.safe_read(root, relative)
        finally:
            c.os.close(root)

    def kinds(self, **options):
        data = c.check(self.root, ['Wiki'], ['Raw'], TODAY, **options)
        return [(f['kind'], f['detail']) for n in data['notes'] for f in n['findings']]

    def test_links_and_fragments(self):
        good = ('[[Raw/acta]] [[Raw/acta.md#Cierre|acta]] [a](../Raw/acta.md#Cierre) ![[Raw/acta#Cierre]] '
                '[[Raw/acta#^final]] [[Raw/datos.yaml]] ![[Raw/foto.jpg]] [web](https://example.org) [[#Aquí]]\n\n# Aquí\n')
        self.note(good)
        self.assertEqual(self.kinds(), [])
        for link, kind in (('[[Raw/acta#Nada]]', 'heading_missing'), ('[[Raw/acta#Doble]]', 'heading_ambiguous'),
                           ('[[Raw/acta#^otro]]', 'block_missing'), ('[[acta]]', 'explicit_path_required'),
                           ('[[Raw/falta]]', 'outside_selection_or_missing'), ('[[../fuera]]', 'outside_selection_or_missing'),
                           ('[x](/etc/passwd)', 'unsupported_target'), ('[[Raw/a%20b]]', 'unsupported_target'),
                           ('[[Raw/datos.yaml#x]]', 'fragment_not_checked'), ('[[#Nada]]', 'heading_missing')):
            with self.subTest(link=link):
                self.note(link)
                self.assertEqual([k for k, _ in self.kinds()], [kind])
        self.note('`[[Raw/falta]]` %%[[Raw/falta]]%%\n```\n[[Raw/falta]]\n```\n<!-- [[Raw/falta]] -->')
        self.assertEqual(self.kinds(), [])

    def test_quotes_match_words_and_detect_these_alterations(self):
        self.note('Dice «El envío se hizo el lunes y no se corrigió.» ([[Raw/acta#Cierre]]) y “estado: "enviado"” [[Raw/datos.yaml]].')
        data = c.check(self.root, ['Wiki'], ['Raw'], TODAY)
        self.assertEqual((data['notes'][0]['findings'], data['notes'][0]['checked']['quotes']), ([], 2))
        for altered, kind in (('El envío se hizo el martes', 'quote_not_found'), ('el envío se hizo', 'quote_not_found'),
                              ('no  se corrigio', 'quote_not_found'), ('corri', 'quote_not_checked'), ('nvío se hizo', 'quote_not_checked'),
                              ('El envío `no` se hizo', 'quote_not_found')):
            with self.subTest(altered=altered):
                self.note(f'Dice «{altered}» ([[Raw/acta#Cierre]]).')
                self.assertEqual([k for k, _ in self.kinds()], [kind])
        self.note('Una palabra «sin fuente» en el texto y [[Raw/acta]] después de otra frase.')
        self.assertEqual(c.check(self.root, ['Wiki'], ['Raw'], TODAY)['notes'][0]['checked']['quotes'], 0)
        self.note('Imagen «algo» ([[Raw/foto.jpg]]).')
        self.assertEqual([k for k, _ in self.kinds()], ['quote_not_checked'])

    def test_a_quantity_or_mark_is_never_accepted_by_resemblance(self):
        self.write('Raw/q.md', '---\nfase: cierre total\n---\nHay 120 cajas a -20 °C, 1.20 m y 20% de agua. La _luz_ es **azul**.\n'
                               'Dosis 20 mg/kg, 30 mg / kg, − 40 cajas; Dosis 1.5 mg. Total 2*0 y _nombre. caso-control. Sumó 60 mg.\n'
                               'A  B. Temperatura 90 °C. Hay 33. Luego, otro.\nFin (50 ml). [acta](../acta.md "antes: borrador interno") y 75 por ciento\n')
        (self.root / 'Raw/p.pdf').write_bytes(b'%PDF-1.4\n% frase oculta\n')
        for quote, ok in (('20 cajas', False), ('120 cajas', True), ('20 °C', False), ('20 m', False), ('20', False), ('La luz es azul', False),
                          ('La _luz_ es **azul**', True), ('Dosis 20 mg', False), ('30 mg', False), ('40 cajas', False), ('Dosis 1.', False),
                          ('nombre', False), ('Total 20', False), ('caso', False), ('Sumó 60 mg.', True), ('50 ml', True), ('Fin', True),
                          ('75', False), ('75 por ciento', True), ('A B', False), ('A  B', True), ('90', False), ('Hay 33', True)):
            with self.subTest(quote=quote):
                self.note(f'Dice «{quote}» [[Raw/q]].')
                kinds = [k for k, _ in self.kinds()]
                self.assertEqual(kinds == [], ok, kinds)
                self.assertTrue(set(kinds) <= {'quote_not_found', 'quote_not_checked'})
        self.note('Dice «frase oculta» [[Raw/p.pdf]].')
        self.assertEqual([k for k, _ in self.kinds()], ['quote_not_checked'])

    def test_distance_never_hides_a_unit_or_a_sign(self):
        self.write('Raw/d.md', 'Son 20' + ' ' * 40 + '°C y −' + ' ' * 40 + '30 °C.\n\n− \n\n40 casos\n\nFin 50\n\nkg aparte. Hay 60\u00a0°C o −\u00a070 °C, −\u00a0.5 mm\n')
        for quote, ok in (('Son 20', False), ('30 °C', False), ('40 casos', True), ('Fin 50', True),
                          ('Hay 60', False), ('70 °C', False), ('.5 mm', False)):
            with self.subTest(quote=quote):
                self.note(f'Dice «{quote}» [[Raw/d]].')
                self.assertEqual([k for k, _ in self.kinds()], [] if ok else ['quote_not_checked'])

    def test_nested_or_open_quotations_are_never_silent(self):
        for text in ('«Informe «inventado» confirmado» [[Raw/acta]]', '“a “b” c” [[Raw/acta]]', 'Abre «sin cerrar [[Raw/acta]]',
                     '«Un “no se corrigió” dentro» [[Raw/acta]]', '«' * 20000):
            with self.subTest(text=text[:40]):
                self.note(text)
                self.assertEqual([k for k, _ in self.kinds()], ['quote_not_checked'])
        for owner in ('     [[Raw/acta]]', ' ![[Raw/acta]]', ' ' * 41 + '[[Raw/acta]]', '\n[[Raw/acta]]', '.\n([[Raw/acta]])', '\u00a0\n[[Raw/acta]]'):
            self.note('«inventado»' + owner)
            self.assertEqual([k for k, _ in self.kinds()], ['quote_not_found'])

    def test_no_link_is_skipped_in_silence(self):
        for link, kind in (('[a](../Raw/no-existe(1).md)', 'outside_selection_or_missing'), ("[a](../Raw/acta.md (título))", None),
                           ('[a](../Raw/acta.md "sin cerrar)', 'link_not_checked'), ('[a [b]](../Raw/acta.md)', 'link_not_checked'),
                           ('[[Raw/acta', 'link_not_checked'), ('    [[Raw/falta]]', 'outside_selection_or_missing'),
                           ('```html\n<!--\n```\n[[Raw/falta]]', 'outside_selection_or_missing'), ('`<!--` [[Raw/falta]]', 'outside_selection_or_missing'),
                           ('`%%` [[Raw/falta]]', 'outside_selection_or_missing'),
                           ('~~~md\n~~~ejemplo\n~~~\n[[Raw/falta]]', 'outside_selection_or_missing')):
            with self.subTest(link=link):
                self.note(link)
                self.assertEqual([k for k, _ in self.kinds()], [kind] if kind else [])
        self.write('Wiki/n.md', '\ufeff---\nrole: note\nmaturity: synthesis\nstale_after: 2000-01-01\n---\n')
        self.assertEqual(self.kinds(), [('stale', '2000-01-01')])
        self.write('Wiki/n.md', '\ufeff```\nx\n```\n[[Raw/falta]]\n')
        self.assertEqual([k for k, _ in self.kinds()], ['outside_selection_or_missing'])

    def test_markdown_destinations_resolve_beside_the_note(self):
        self.write('Raw/con espacio.md', 'humo\n')
        self.write('Wiki/Raw/s.md', 'otra cosa\n')
        self.write('Raw/s.md', 'Humo\n')
        for link, kinds in (('[F](Raw/s.md)', ['quote_not_checked', 'target_ambiguous']), ('[F](../Raw/s.md)', []), ('[F](<../Raw/con espacio.md>)', ['quote_not_found']),
                            ('[F](../Raw/s.md "título")', []), ('[F](Raw/acta.md)', ['quote_not_checked', 'root_relative_markdown_link'])):
            with self.subTest(link=link):
                self.note(f'«Humo» {link}')
                self.assertEqual(sorted(k for k, _ in self.kinds()), kinds)

    def test_footnote_paragraphs_and_incomplete_selections(self):
        self.note('Nota.[^a]\n\n[^a]: Primero.\n\n    Segundo [9].\n\n## Referencias\n')
        self.assertEqual(self.kinds(), [('reference_missing', '9')])
        real = c.os.walk

        def denied(top, **options):
            options['onerror'](PermissionError(13, 'denied'))
            return real(top, **options)
        c.os.walk = denied
        self.addCleanup(setattr, c.os, 'walk', real)
        with self.assertRaises(PermissionError):
            self.kinds()
        c.os.walk = real
        check_note = c.check_note
        self.addCleanup(setattr, c, 'check_note', check_note)

        def adding(*arguments):
            self.write('Wiki/nueva.md', '[[Raw/falta]]')
            return check_note(*arguments)
        c.check_note = adding
        with self.assertRaisesRegex(ValueError, 'Input changed'):
            self.kinds()

    def test_hostile_frontmatter_and_descriptors(self):
        for meta, kind in (('role: note\nmaturity: synthesis\nstale_after: !!timestamp x', 'frontmatter_invalid'),
                           ('role: note\nmaturity: synthesis\nstale_after: 2031-W10-1', 'stale_after_invalid'),
                           ('role: note\nmaturity: synthesis\nsuperseded_by: "[[Raw/acta#Nada]]"', 'superseded_by_unresolved')):
            self.note('Texto.', meta)
            self.assertEqual([k for k, _ in self.kinds()], [kind])
        before = len(c.os.listdir('/proc/self/fd')) if c.os.path.isdir('/proc/self/fd') else None
        for _ in range(20):
            with self.assertRaises(ValueError):
                self.read('Raw')
        if before is not None:
            self.assertEqual(len(c.os.listdir('/proc/self/fd')), before)

    def test_heading_chains_and_repeated_blocks(self):
        self.write('Raw/h.md', '# Uno\n\n## Estado\n\na ^z\n\n# Dos\n\n## Estado\n\n### Fin\n\nb ^z\n\nc ^y\n')
        for fragment, kind in (('Uno#Estado', None), ('Dos#Estado', None), ('Dos#Fin', None), ('Estado', 'heading_ambiguous'),
                               ('Nada#Estado', 'heading_missing'), ('Uno#Fin', 'heading_missing'), ('Fin#Dos', 'heading_missing'),
                               ('^z', 'block_ambiguous'), ('^y', None)):
            with self.subTest(fragment=fragment):
                self.note(f'[[Raw/h#{fragment}]]')
                self.assertEqual([k for k, _ in self.kinds()], [kind] if kind else [])

    def test_references_never_borrow_a_source(self):
        self.note('«no se corrigió» [1]\n\n## Referencias\n\n1. Autor. [Original](../Raw/acta.md)')
        self.assertEqual(self.kinds(), [])
        self.note('«Verde» [1]\n\n## Referencias\n\n1. Autor. [Original](../Raw/acta.md)')
        self.assertEqual(self.kinds(), [('quote_not_found', 'Verde')])
        self.note('«no se corrigió» [1]\n\n## Referencias\n\n[1] Libro sin enlace\n\n### Lectura adicional\n\n[[Raw/acta]]')
        self.assertEqual(self.kinds(), [('quote_not_checked', 'no se corrigió')])
        self.note('Dato [9].\n\n## Referencias\n')
        self.assertEqual(self.kinds(), [('reference_missing', '9')])
        self.note('Dos [1,2], rango [3–5] y nota.[^a]\n\n[^a]: Véase [6]\n\n## Referencias\n\n'
                  + '\n'.join(f'[{n}] [[Raw/acta]]' for n in range(1, 7)))
        self.assertEqual(self.kinds(), [])
        self.note('| a |\n|---|\n| [[Raw/acta\\|Acta]] |')
        self.assertEqual(self.kinds(), [])

    def test_hostile_inputs_are_contained(self):
        (self.root / 'Wiki').mkdir(exist_ok=True)
        (self.root / 'Wiki/mala.MD').write_bytes(b'\xff\xfe')
        self.note('Texto.', 'role: [note]\nstale_after: 2031-01-01')
        self.assertEqual(sorted(k for k, _ in self.kinds()), ['note_unreadable', 'stale', 'validity_not_applicable'])
        (self.root / 'Wiki/mala.MD').unlink()
        self.note('Texto.', 'role: note\nmaturity: {a: b}\nsuperseded_by: [x]')
        self.assertEqual(sorted(k for k, _ in self.kinds()), ['superseded_by_unresolved', 'validity_not_applicable'])
        self.note('Texto.', 'role: map\nsuperseded_by: "[[Raw/foto.jpg]]"')
        self.assertEqual(self.kinds(), [('superseded_by_unresolved', 'target_is_not_a_note_or_map')])
        self.note('Texto.', 'role: project\nmaturity: evergreen\nstale_after: 2032-01-01')
        self.assertEqual(self.kinds(), [])
        (self.root / 'Raw/.oculta').mkdir()
        (self.root / 'Raw/.oculta/enlace.md').symlink_to('/etc/passwd')
        self.note('[[Raw/acta]]')
        self.assertEqual(self.kinds(), [])
        for relative in ('Raw/../../x', '.git/config', 'Raw/.oculta/enlace.md'):
            with self.assertRaises(ValueError):
                self.read(relative)
        outside = self.root / 'Otra'
        outside.mkdir()
        (outside / 'acta.md').write_text('# X\n')
        (self.root / 'Enlace').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.read('Enlace/acta.md')
        (self.root / 'Raw/grande.md').write_bytes(b'x' * (c.LIMIT + 1))
        self.note('[[Raw/grande]]')
        with self.assertRaisesRegex(ValueError, '4 MiB: Raw/grande.md'):
            self.kinds()

    def test_a_change_during_the_run_discards_the_result(self):
        self.note('[[Raw/acta]]')
        real = c.check_note

        def changing(*arguments):
            result = real(*arguments)
            self.write('Wiki/n.md', 'otro')
            return result
        c.check_note = changing
        self.addCleanup(setattr, c, 'check_note', real)
        with self.assertRaisesRegex(ValueError, 'Input changed'):
            self.kinds()

    def test_numbered_references(self):
        self.note('Se envió «no se corrigió» [1]. Otro [2]; véase [3](https://example.org) y lista[4].\n\n## Referencias\n\n'
                  '[1] [[Raw/acta#Cierre]]\n[3] [[Raw/datos.yaml]]\n\n## Después\n\nFinal [1].')
        self.assertEqual(sorted(self.kinds()), [('reference_missing', '2'), ('reference_missing', '4'), ('reference_unused', '3')])
        self.note('Par [1][2] y tres [3] [4]: ![5] \\[6] [[7]]\n[8]: x\n\n## Referencias\n\n[1] [[Raw/acta]]\n')
        self.assertEqual(sorted(d for k, d in self.kinds() if k == 'reference_missing'), ['2', '3', '4'])
        self.note('Uno «no se borró» [1].\n\n## References\n\n1. [[Raw/acta]]\n1. [[Raw/datos.yaml]]')
        self.assertEqual(sorted(k for k, _ in self.kinds()), ['quote_not_found', 'reference_repeated'])
        self.note('Sin sección de referencias [7].')
        self.assertEqual(self.kinds(), [])

    def test_declared_validity_is_reported_and_never_enforced(self):
        self.write('Wiki/nueva.md', '---\nrole: note\nmaturity: synthesis\n---\n')
        base = 'role: note\nmaturity: synthesis\n'
        for meta, expected in ((base + 'stale_after: 2031-09-01', []), (base + 'stale_after: 2031-08-31', [('stale', '2031-08-31')]),
                               (base + 'stale_after: pronto', [('stale_after_invalid', 'pronto')]),
                               (base + 'superseded_by: "[[Wiki/nueva]]"', [('superseded', 'Wiki/nueva.md')]),
                               (base + 'superseded_by: "[[Wiki/n]]"', [('superseded_by_unresolved', 'replaces_itself')]),
                               (base + 'superseded_by: "[[nueva]]"', [('superseded_by_unresolved', 'explicit_path_required')]),
                               (base + 'superseded_by: nueva', [('superseded_by_unresolved', 'explicit_wikilink_required')]),
                               ('role: map\nstale_after: 2032-01-01', [])):
            with self.subTest(meta=meta):
                self.note('Texto.', meta)
                self.assertEqual(self.kinds(), expected)
        for meta in ('role: note\nmaturity: seed\nstale_after: 2032-01-01', 'role: source\nsuperseded_by: "[[Wiki/nueva]]"'):
            self.note('Texto.', meta)
            self.assertIn('validity_not_applicable', [k for k, _ in self.kinds()])

    def test_changed_sources_since_an_earlier_report(self):
        self.note('[[Raw/acta]] [[Raw/datos.yaml]] ![[Raw/foto.jpg]]')
        first = json.loads(json.dumps(c.check(self.root, ['Wiki'], ['Raw'], TODAY)))
        self.assertEqual(sorted(first['sources']), ['Raw/acta.md', 'Raw/datos.yaml', 'Raw/foto.jpg'])
        self.assertEqual(c.check(self.root, ['Wiki'], ['Raw'], TODAY, first)['changed_since'], [])
        self.write('Raw/datos.yaml', 'estado: "otro"\n')
        self.note('[[Raw/datos.yaml]] ![[Raw/foto.jpg]]')
        self.assertEqual([(x['kind'], x['path']) for x in c.check(self.root, ['Wiki'], ['Raw'], TODAY, first)['changed_since']],
                         [('source_no_longer_cited', 'Raw/acta.md'), ('source_changed', 'Raw/datos.yaml')])
        for bad in ({}, [], first | {'version': 2}, first | {'algorithm': 'otro'}, first | {'sources': []},
                    first | {'sources': {'a': 'corto'}}):
            with self.assertRaisesRegex(ValueError, 'version 1'):
                c.check(self.root, ['Wiki'], ['Raw'], TODAY, bad)
        with self.assertRaisesRegex(ValueError, 'version 1'):
            c.check(self.root, ['Wiki'], ['Raw'], TODAY, None)
        self.root.rename(self.root.parent / (self.root.name + '-antes'))
        self.addCleanup(__import__('shutil').rmtree, self.root.parent / (self.root.name + '-antes'))
        self.write('Raw/acta.md', '# X\n')
        self.note('[[Raw/acta]]')
        with self.assertRaisesRegex(ValueError, 'different library'):
            c.check(self.root, ['Wiki'], ['Raw'], TODAY, first)
        now = c.check(self.root, ['Wiki'], ['Raw'], TODAY)
        identity = c.folder_identity
        self.addCleanup(setattr, c, 'folder_identity', identity)
        c.folder_identity = lambda opened: b'other-volume-' + identity(opened).split(b'-')[-1]
        with self.assertRaisesRegex(ValueError, 'different library'):
            c.check(self.root, ['Wiki'], ['Raw'], TODAY, now)
        c.folder_identity = identity
        for other in ((['Wiki'], [], first), (['Wiki'], ['Raw'], first | {'library': 'x'})):
            with self.assertRaisesRegex(ValueError, 'different library or selection'):
                c.check(self.root, *other[:2], TODAY, other[2])

    def test_selection_is_explicit_read_only_and_refuses_links(self):
        self.note('[[Raw/acta]]')
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual([k for n in c.check(self.root, ['Wiki'], [], TODAY)['notes'] for k in [f['kind'] for f in n['findings']]],
                         ['outside_selection_or_missing'])
        self.kinds()
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()})
        for scope in ('.', '..', '../x', '/tmp', '.hidden', 'Nada'):
            for arguments in ((['Wiki'], [scope]), ([scope], [])):
                with self.subTest(scope=scope), self.assertRaises(ValueError):
                    c.check(self.root, *arguments, TODAY)
        with self.assertRaises(ValueError):
            c.check(self.root, [], ['Raw'], TODAY)
        self.write('Raw/.oculto/secreto.md', '# S\n')
        self.note('[[Raw/.oculto/secreto]]')
        self.assertEqual([k for k, _ in self.kinds()], ['outside_selection_or_missing'])
        (self.root / 'Raw/enlace.md').symlink_to(self.root / 'Raw/acta.md')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.kinds()

    def test_command_line(self):
        self.note('[[Raw/falta]]')
        run = lambda *extra: subprocess.run([sys.executable, '-B', str(BASE / 'scripts/citation_check.py'), '--root',
                                             str(self.root), '--scope', 'Wiki', '--sources', 'Raw', *extra],
                                            capture_output=True, text=True)
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['notes'][0]['findings'][0]['line'], 5)
        self.assertIn('no claim', data['limits'])
        self.assertEqual(run('--since', str(self.root / 'nada.json')).returncode, 2)


if __name__ == '__main__':
    unittest.main()
