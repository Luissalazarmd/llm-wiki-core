"""Citation formatting from fictional first pages. A citation comes only from fields printed in the places the docs name."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support  # noqa: F401  real temp dir for symlink-refusing helpers

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
import citation_format as c

ARTICLE = ('Revista Inventada. 2031;12(3):40–48. doi: 10.1234/prueba\n\n'
           'Mediciones de\nprueba\n'
           'Ana María Del Río1,*, Bo Li2 and Eva-Sol Paz1,†\n'
           '1 Instituto Ficticio. 2 Centro Inventado.\n\n'
           'Abstract\nUn resumen inventado.\n\n'
           'Introduction\nEl estudio previo Otro trabajo distinto (Rey, 2019) midió 7 casos en 3 días.\n\n'
           'Acknowledgements\nAgradecemos a Luz Mora.\n\n'
           'References\n1. Rey L. Otro trabajo distinto. Rev Falsa. 2019;7:1-3. doi: 10.9999/ajena\n')
AUTHORS = [dict(family='Del Río', given='Ana María'), dict(family='Li', given='Bo'), dict(family='Paz', given='Eva-Sol')]
FIELDS = dict(authors=AUTHORS, title='Mediciones de prueba', journal='Revista Inventada', year='2031', volume='12',
              issue='3', pages='40–48', doi='10.1234/prueba')
CITED = 'Del Río AM, Li B, Paz ES. Mediciones de prueba. Revista Inventada. 2031;12(3):40–48. doi: 10.1234/prueba'


def cite(fields=None, text=ARTICLE):
    return c.format_citation('vancouver', FIELDS if fields is None else fields, text)


class CitationFormatTests(unittest.TestCase):
    def test_article_with_three_authors_and_affiliation_marks(self):
        report = cite()
        self.assertEqual(report['citation'], CITED)
        self.assertEqual((report['dropped'], report['missing']), ([], []))
        self.assertEqual(report['found'], ['authors', 'doi', 'issue', 'journal', 'pages', 'title', 'volume', 'year'])

    def test_line_breaks_hyphenation_tabs_ligatures_and_decomposed_accents(self):
        text = (ARTICLE.replace('Mediciones de\nprueba', 'Medi-\nciones\tde\nprueba').replace('40–48', '40 -\n48')
                .replace('Del Río', 'Del Río'))
        self.assertEqual(cite(text=text)['citation'], CITED)
        ligature = ARTICLE.replace('Mediciones de\nprueba', 'Mediciones de prueba ﬁnal')
        self.assertTrue(cite(dict(FIELDS, title='Mediciones de prueba final'), ligature)['citation'])

    def test_six_authors_are_listed_and_a_seventh_becomes_et_al(self):
        families = ('Paz', 'Rey', 'León', 'Jun', 'Mora', 'Gil', 'Cruz')
        for count, expected in ((6, 'Paz S, Rey S, León S, Jun S, Mora S, Gil S. Un ensayo largo.'),
                                (7, 'Paz S, Rey S, León S, Jun S, Mora S, Gil S, et al. Un ensayo largo.')):
            with self.subTest(count=count):
                names = families[:count]
                text = ('arXiv:2411.01234v2 [cs.XX] 3 Mar 2031\nUn ensayo largo\n'
                        + ', '.join(f'Sol {f}{i}' for i, f in enumerate(names, 1)) + '\nAbstract\nTexto.\n')
                report = cite(dict(authors=[dict(family=f, given='Sol') for f in names], title='Un ensayo largo',
                                   arxiv='2411.01234', year='2031'), text)
                self.assertEqual(report['citation'], expected + ' arXiv:2411.01234 [Preprint]. 2031.')

    def test_a_preprint_server_and_a_journal_that_wins_over_arxiv(self):
        text = 'medRxiv preprint 2031\nUn ensayo largo\nSol Paz1\nAbstract\n'
        fields = dict(authors=[dict(family='Paz', given='Sol')], title='Un ensayo largo', server='medRxiv', year='2031')
        self.assertEqual(cite(fields, text)['citation'], 'Paz S. Un ensayo largo. medRxiv [Preprint]. 2031.')
        report = cite(dict(FIELDS, arxiv='2411.01234'), ARTICLE.replace('Abstract', 'arXiv:2411.01234\nAbstract'))
        self.assertEqual((report['citation'], report['unused']), (CITED, ['arxiv']))

    def test_continuous_signature_in_a_script_without_spaces(self):
        text = '某期刊. 2031;5:1-9.\n测试研究标题\n王小明1, 李华2\nAbstract\n'
        report = cite(dict(authors=[dict(family='王', given='小明'), dict(family='李', given='华')],
                           title='测试研究标题', journal='某期刊', year='2031'), text)
        self.assertTrue(report['citation'].startswith('王小明, 李华. 测试研究标题.'), report)

    def test_names_outside_the_byline_or_an_incomplete_list_give_no_citation(self):
        cases = {'acknowledgements only': [dict(family='Mora', given='Luz')],
                 'first author left out': AUTHORS[1:],
                 'middle author left out': [AUTHORS[0], AUTHORS[2]],
                 'last author left out': AUTHORS[:2],
                 'out of order': AUTHORS[::-1],
                 'shorter family name': [dict(family='Pa', given='Eva-Sol')],
                 'no given name': [dict(family='Li')]}
        for name, authors in cases.items():
            with self.subTest(name):
                report = cite(dict(FIELDS, authors=authors))
                self.assertIsNone(report['citation'])
                self.assertEqual(report['missing'][:1], ['authors'])

    def test_title_year_and_numbers_are_dropped_when_not_printed_in_place(self):
        report = cite(dict(FIELDS, title='Otro trabajo distinto'))
        self.assertEqual((report['citation'], report['missing']), (None, ['title']))
        self.assertIn('title', cite(dict(FIELDS, title='A'))['dropped'])
        report = cite(dict(FIELDS, year='2019'))
        self.assertEqual((report['citation'], report['missing']), (None, ['year']))
        report = cite(dict(FIELDS, volume='7'))  # a wrong volume breaks the whole locator
        self.assertEqual(report['dropped'], ['volume', 'issue', 'pages'])
        self.assertIn('Revista Inventada. 2031. doi:', report['citation'])

    def test_a_byline_must_not_continue_on_a_neighbouring_line(self):
        text = ('Revista Inventada. 2031;12(3):40–48.\nMediciones de prueba\n'
                'Ana Paz1, Luis Gil2,\nMaria Ruiz1, Pedro Sol3*\n1 Instituto Ficticio.\nAbstract\n')
        everyone = [dict(family='Paz', given='Ana'), dict(family='Gil', given='Luis'),
                    dict(family='Ruiz', given='Maria'), dict(family='Sol', given='Pedro')]
        base = dict(title='Mediciones de prueba', journal='Revista Inventada', year='2031')
        self.assertTrue(cite(dict(base, authors=everyone), text)['citation'].startswith('Paz A, Gil L, Ruiz M, Sol P.'))
        for part in (everyone[:2], everyone[2:]):
            with self.subTest(part=part):
                self.assertIsNone(cite(dict(base, authors=part), text)['citation'])
        one_per_line = text.replace('Ana Paz1, Luis Gil2,\nMaria Ruiz1, Pedro Sol3*', 'Ana Paz1\nLuis Gil2')
        self.assertIsNone(cite(dict(base, authors=[everyone[1]]), one_per_line)['citation'])
        degrees = text.replace('Ana Paz1, Luis Gil2,\nMaria Ruiz1, Pedro Sol3*', 'Ana Paz, MD, PhD; Luis Gil, MSc')
        self.assertTrue(cite(dict(base, authors=everyone[:2]), degrees)['citation'])

    def test_a_title_is_a_whole_block_of_lines(self):
        text = ARTICLE.replace('Mediciones de\nprueba', 'Melanoma')
        self.assertTrue(cite(dict(FIELDS, title='Melanoma'), text)['citation'].startswith('Del Río AM, Li B, Paz ES. Melanoma.'))
        self.assertEqual(cite(dict(FIELDS, title='de prueba'))['missing'], ['title'])
        noted = ARTICLE.replace('Mediciones de\nprueba', 'No effect of aspirin on mortality')
        self.assertEqual(cite(dict(FIELDS, title='effect of aspirin on mortality'), noted)['missing'], ['title'])

    def test_a_doi_split_across_lines_or_beside_another_work_is_dropped(self):
        split = ARTICLE.replace('10.1234/prueba', '10.1016/S0140-\n6736(20)30183-5')
        self.assertEqual(cite(dict(FIELDS, doi='10.1016/S0140-'), split)['dropped'], ['doi'])
        comment = ARTICLE.replace('Abstract', 'See Comment doi: 10.5555/comentario\n' + 'x ' * 200 + '\nAbstract')
        self.assertEqual(cite(dict(FIELDS, doi='10.5555/comentario'), comment)['dropped'], ['doi'])
        continued = ARTICLE.replace('References\n', 'REFERENCES (continued)\n')
        self.assertEqual(cite(dict(FIELDS, doi='10.9999/ajena'), continued)['dropped'], ['doi'])

    def test_a_doi_must_be_printed_whole_and_outside_the_references(self):
        printed = ARTICLE.replace('10.1234/prueba', '10.1016/S0140-6736(20)30183-5')
        self.assertTrue(cite(dict(FIELDS, doi='10.1016/s0140-6736(20)30183-5'), printed)['citation'].endswith(
            'doi: 10.1016/s0140-6736(20)30183-5'))
        for doi in ('10.1016/S0140-6736', '10.9999/ajena'):
            with self.subTest(doi=doi):
                report = cite(dict(FIELDS, doi=doi), printed)
                self.assertEqual(report['dropped'], ['doi'])
                self.assertNotIn('doi:', report['citation'])

    def test_whole_numbers_are_read_and_other_types_dropped(self):
        self.assertEqual(cite(dict(FIELDS, year=2031, volume=12, issue=3))['citation'], CITED)
        self.assertEqual(cite(dict(FIELDS, pages=['40']))['dropped'], ['pages'])
        self.assertEqual(cite(dict(FIELDS, title='x' * 513))['missing'], ['title'])

    def test_command_reads_regular_files_only_and_refuses_bad_input(self):
        with tempfile.TemporaryDirectory() as temp:
            fields, text = Path(temp) / 'fields.json', Path(temp) / 'first-pages.txt'
            fields.write_text(json.dumps(FIELDS))
            text.write_text(ARTICLE)

            def run(style='vancouver', source=text, given=fields):
                return subprocess.run([sys.executable, str(BASE / 'scripts/citation_format.py'), '--style', style,
                                       '--fields', str(given), '--text', str(source)],
                                      capture_output=True, text=True, timeout=20)

            done = run()
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)['citation'], CITED)
            self.assertEqual(run('apa').returncode, 2)
            big, bad, pipe, link = (Path(temp) / n for n in ('big.txt', 'bad.json', 'pipe', 'link.txt'))
            big.write_text('x' * (c.LIMIT + 1))
            bad.write_bytes(b'{\xff')
            os.mkfifo(pipe)
            link.symlink_to(text)
            linked_dir = Path(temp) / 'linked'
            linked_dir.symlink_to(temp)
            for source, given, message in ((big, fields, 'exceeds 1 MiB'), (text, bad, ''),
                                           (pipe, fields, 'not a regular file'), (link, fields, ''),
                                           (linked_dir / 'first-pages.txt', fields, 'through a link')):
                with self.subTest(source=source.name, given=given.name):
                    refused = run(source=source, given=given)
                    self.assertEqual(refused.returncode, 2)
                    self.assertIn(message, refused.stderr)


if __name__ == '__main__':
    unittest.main()
