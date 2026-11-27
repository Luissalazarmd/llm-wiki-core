"""Citation formatting from fictional first pages. A citation comes only from fields printed in the text."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support  # noqa: F401  real temp dir for symlink-refusing helpers

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
import citation_format as c

ARTICLE = ('Mediciones de\nprueba\nAna María Del Río1,*, Bo Li2, Eva-Sol Paz1,†\n'
           'Revista Inventada. 2031;12(3):40–48. doi: 10.1234/\nprueba\n')
FIELDS = dict(authors=[dict(family='Del Río', given='Ana María'), dict(family='Li', given='Bo'),
                       dict(family='Paz', given='Eva-Sol')],
              title='Mediciones de prueba', journal='Revista Inventada', year='2031', volume='12',
              issue='3', pages='40–48', doi='10.1234/prueba')


class CitationFormatTests(unittest.TestCase):
    def test_article_with_three_authors_and_affiliation_marks(self):
        report = c.format_citation('vancouver', FIELDS, ARTICLE)
        self.assertEqual(report['citation'], 'Del Río AM, Li B, Paz ES. Mediciones de prueba. Revista Inventada. '
                                             '2031;12(3):40–48. doi: 10.1234/prueba')
        self.assertEqual((report['dropped'], report['missing']), ([], []))

    def test_line_breaks_and_hyphens_are_tolerated(self):
        text = ARTICLE.replace('Mediciones de\nprueba', 'Medi-\nciones de\nprueba').replace('40–48', '40 -\n48')
        self.assertTrue(c.format_citation('vancouver', FIELDS, text)['citation'].startswith('Del Río AM'))

    def test_preprint_with_more_than_six_authors(self):
        families = ('Paz', 'Rey', 'León', 'Jun', 'Mora', 'Gil', 'Cruz')
        authors = [dict(family=f, given='Sol') for f in families]
        text = 'Un ensayo\n' + ', '.join(f'Sol {f}{i}' for i, f in enumerate(families, 1)) + '\narXiv:2411.01234v2 2031'
        report = c.format_citation('vancouver', dict(authors=authors, title='Un ensayo', arxiv='2411.01234v2',
                                                     year='2031'), text)
        self.assertEqual(report['citation'], 'Paz S, Rey S, León S, et al. Un ensayo. arXiv:2411.01234v2 [Preprint]. 2031.')

    def test_a_field_not_printed_is_dropped(self):
        report = c.format_citation('vancouver', dict(FIELDS, volume='13', doi='10.1234/prue'), ARTICLE)
        self.assertEqual(report['dropped'], ['volume', 'doi'])
        self.assertNotIn('doi:', report['citation'])
        self.assertIn('Revista Inventada. 2031:40–48.', report['citation'])

    def test_authors_out_of_order_or_a_shorter_family_name_give_no_citation(self):
        for authors in (FIELDS['authors'][::-1], [dict(family='Pa', given='Eva-Sol')]):
            with self.subTest(authors=authors):
                report = c.format_citation('vancouver', dict(FIELDS, authors=authors), ARTICLE)
                self.assertIsNone(report['citation'])
                self.assertEqual((report['dropped'], report['missing']), (['authors'], ['authors']))

    def test_a_missing_required_field_gives_no_citation(self):
        report = c.format_citation('vancouver', dict(FIELDS, year='2030'), ARTICLE)
        self.assertIsNone(report['citation'])
        self.assertEqual(report['missing'], ['year'])

    def test_command_reads_files_and_refuses_an_unknown_style(self):
        with tempfile.TemporaryDirectory() as temp:
            fields, text = Path(temp) / 'fields.json', Path(temp) / 'first-pages.txt'
            fields.write_text(json.dumps(FIELDS))
            text.write_text(ARTICLE)
            run = lambda style: subprocess.run([sys.executable, str(BASE / 'scripts/citation_format.py'), '--style',
                                                style, '--fields', str(fields), '--text', str(text)],
                                               capture_output=True, text=True, timeout=20)
            done = run('vancouver')
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue(json.loads(done.stdout)['citation'].endswith('doi: 10.1234/prueba'))
            self.assertEqual(run('apa').returncode, 2)


if __name__ == '__main__':
    unittest.main()
