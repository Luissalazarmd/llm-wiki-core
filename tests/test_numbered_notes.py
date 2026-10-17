"""Numbered naming uses existing identity and link behavior, not a new allocator."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/numbered-notes'
SPEC = importlib.util.spec_from_file_location('numbered_reader', ROOT / 'scripts/knowledge.py')
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


class NumberedNotesTests(unittest.TestCase):
    def test_existing_reader_preserves_addresses_and_meaning_without_inference(self):
        before = {p: p.read_bytes() for p in (EXAMPLE / 'Wiki').glob('*.md')}
        data = API.catalog(EXAMPLE, link_prefix='examples/numbered-notes')
        self.assertCountEqual([n['id'] for n in data['notes']], ['012', '012a', '012a1', '012b'])
        for note in data['notes']:
            self.assertTrue(Path(note['path']).name.startswith(note['id'] + ' - '))
            self.assertFalse(note['title'].startswith(note['id']))
            self.assertEqual(note['role'], 'note')
        self.assertCountEqual([e['kind'] for e in data['edges']], ['extends'] * 3)
        self.assertEqual(sum(n['maturity'] == 'unknown' for n in data['notes']), 3)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_title_and_filename_changes_preserve_id_but_links_need_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(EXAMPLE / 'Wiki', root / 'Wiki')
            original = root / 'Wiki/012a - Considerar el horario.md'
            renamed = root / 'Wiki/012a - Revisar el horario.md'
            original.rename(renamed)
            with self.assertRaisesRegex(ValueError, 'Unresolved native relation'):
                API.catalog(root, link_prefix='examples/numbered-notes')
            child = root / 'Wiki/012a1 - Separar explicaciones.md'
            child.write_text(child.read_text().replace(original.stem, renamed.stem))
            renamed.write_text(renamed.read_text().replace('El horario puede explicar una diferencia',
                                                          'El horario merece una comparación')
                               .replace('role: note', 'role: note\nmaturity: synthesis'))
            data = API.catalog(root, link_prefix='examples/numbered-notes')
            note = next(n for n in data['notes'] if n['id'] == '012a')
            self.assertEqual(note['title'], 'El horario merece una comparación')
            self.assertEqual(note['maturity'], 'synthesis')
            self.assertTrue(any(e['target'] == '012a' for e in data['edges']))
            (root / 'Wiki/duplicate.md').write_bytes(renamed.read_bytes())
            with self.assertRaisesRegex(ValueError, 'Duplicate identity'):
                API.catalog(root, link_prefix='examples/numbered-notes')

    def test_retirement_reserves_id_and_preserves_old_section_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(EXAMPLE / 'Wiki', root / 'Wiki')
            note = root / 'Wiki/012a - Considerar el horario.md'
            child = root / 'Wiki/012a1 - Separar explicaciones.md'
            before = note.read_text() + '\n## Detalle\nArgumento ficticio anterior.\n'
            child.write_text(child.read_text().replace('Considerar el horario]]',
                                                       'Considerar el horario#Detalle]]'))
            child_bytes = child.read_bytes()
            front, body = before.split('---\n', 2)[1:]
            front = front.replace('title: ', 'title: Retirada — ', 1)
            notice = ('Retirada: explicación integrada en '
                      '[[examples/numbered-notes/Wiki/012b - Expresar incertidumbre]].\n'
                      'El argumento anterior se conserva para interpretar referencias previas.\n\n')
            note.write_text('---\n' + front + '---\n' + notice + body)
            data = API.catalog(root, link_prefix='examples/numbered-notes')
            retired = next(n for n in data['notes'] if n['id'] == '012a')
            self.assertEqual(retired['path'], str(note.relative_to(root)))
            self.assertTrue(retired['title'].startswith('Retirada — '))
            self.assertEqual(retired['role'], 'note')
            self.assertEqual(retired['maturity'], 'unknown')
            self.assertTrue(any(e['source'] == '012a1' and e['target'] == '012a'
                                and e['target_locator'] == '#Detalle' for e in data['edges']))
            self.assertTrue(note.read_text().endswith(body))
            self.assertEqual(child.read_bytes(), child_bytes)
            (root / 'Wiki/012a - Otra idea.md').write_text('---\nid: "012a"\nrole: note\n---\nOtra idea.\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate identity'):
                API.catalog(root, link_prefix='examples/numbered-notes')


if __name__ == '__main__':
    unittest.main()
