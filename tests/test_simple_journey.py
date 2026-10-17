"""Synthetic capture -> navigation -> one evolving idea, not human approval."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SimpleJourneyTests(unittest.TestCase):
    def test_capture_and_evolution_reuse_one_idea_and_leave_originals_unchanged(self):
        with tempfile.TemporaryDirectory(prefix='core-simple-journey-') as directory:
            work = Path(directory)
            vault = work / 'library'
            for folder in ('Raw/Sources', 'Wiki/Maps', 'Wiki/Concepts'):
                (vault / folder).mkdir(parents=True, exist_ok=True)
            (work / 'recovery').mkdir()
            (vault / 'Wiki/Maps/Tema.md').write_text('---\nid: topic\nrole: map\n---\n# Recorrido ficticio\n')
            settings = work / 'personal.json'
            settings.write_text(json.dumps({
                'version': 1, 'library_root': str(vault),
                'authorized_paths': ['Raw/Sources', 'Wiki'],
                'layers': {'sources': ['Raw/Sources'], 'knowledge': ['Wiki']},
                'write_policy': 'plain_files', 'recovery_directory': str(work / 'recovery')}))

            def cli(script, *args, draft=None):
                result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                                        input=draft, text=True, capture_output=True, timeout=10,
                                        env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            capture = ('---\nid: source1\nrole: source\nTitle: Informe ficticio\n'
                       'Reference: https://example.org/fictional-method\n---\n# Informe ficticio\n'
                       'Related:: [[Wiki/Maps/Tema]]\n'
                       '## Método\nEste ejemplo describe un método, no mide efectos.\n')
            target = vault / 'Raw/Sources/Informe.md'
            before = {p: p.read_bytes() for p in vault.rglob('*.md')}
            receipt = json.loads(cli('capture_check.py', '--config', str(settings),
                                    '--target', 'Raw/Sources/Informe.md', draft=capture))
            self.assertFalse(target.exists())
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            # Host publication is represented by a test-only create operation, not an approval event.
            with target.open('xb') as stream:
                stream.write(capture.encode())
            saved_capture = json.loads(cli('capture_check.py', '--config', str(settings),
                                           '--target', 'Raw/Sources/Informe.md', '--saved',
                                           '--expected-sha256', receipt['check_sha256'], draft=capture))
            self.assertFalse(saved_capture['approval_available'])
            original = target.read_bytes()
            catalog = json.loads(cli('knowledge.py', '--root', str(vault)))
            self.assertEqual({(e['source'], e['target']) for e in catalog['edges']},
                             {('source1', 'topic')})
            self.assertNotIn('maturity', capture)
            self.assertNotIn('relations', capture)

            packet_path = work / 'proposal.json'
            import yaml
            metadata = {'id': 'idea1', 'title': 'Métodos no equivalen a efectos', 'role': 'note'}
            phases = [('seed', 'Pregunta: ¿describir un método permite concluir su efecto?'),
                      ('synthesis', 'Argumento: una descripción metodológica no determina un efecto; falta medirlo.'),
                      ('evergreen', 'Alcance acotado: distinguir descripción y medición; no se afirma un efecto real.')]
            for index, (maturity, explanation) in enumerate(phases):
                draft = ('---\n' + yaml.safe_dump({**metadata, 'maturity': maturity}, allow_unicode=True)
                         + '---\n# Idea ficticia\nEvidence:: [[Raw/Sources/Informe#Método]]\n\n' + explanation + '\n')
                arguments = ['--root', str(vault), '--proposal-target', 'Wiki/Concepts/Idea.md',
                             '--evidence', 'Raw/Sources/Informe.md']
                if index == 0:
                    arguments.append('--create')
                previous = (vault / 'Wiki/Concepts/Idea.md').read_bytes() if index else None
                packet = cli('knowledge.py', *arguments, draft=draft)
                packet_path.write_text(packet)
                cli('note_write.py', '--config', str(settings), 'check', '--packet', str(packet_path))
                if index:
                    self.assertEqual((vault / 'Wiki/Concepts/Idea.md').read_bytes(), previous)
                else:
                    self.assertFalse((vault / 'Wiki/Concepts/Idea.md').exists())
                result = json.loads(cli('note_write.py', '--config', str(settings), 'save',
                                       '--packet', str(packet_path)))
                self.assertFalse(result['human_authentication_verified'])
                self.assertEqual((vault / 'Wiki/Concepts/Idea.md').read_bytes(), draft.encode())
                self.assertEqual(target.read_bytes(), original)
                data = json.loads(cli('knowledge.py', '--root', str(vault)))
                self.assertEqual(len([n for n in data['notes'] if n['role'] == 'note']), 1)
                idea = next(n for n in data['notes'] if n['id'] == 'idea1')
                self.assertEqual(idea['maturity'], maturity)
                self.assertIsNone(idea['declared_review'])
                self.assertFalse(idea['approval_available'])
                navigation = cli('knowledge.py', '--root', str(vault), '--focus', 'idea1',
                                 '--format', 'markdown', '--typed-navigation')
                self.assertIn('Evidence:', navigation)
                self.assertIn('supported_by', navigation)
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            self.assertEqual(len(list((vault / 'Wiki/Concepts').glob('*.md'))), 1)
            # Maturity labels are supplied fixtures, never inferred/authenticated by a helper.


if __name__ == '__main__':
    unittest.main()
