"""Starter library template: copyable as a root, editable, with proposals custody; synthetic only."""
import hashlib
import json
import os
from pathlib import Path
import re
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
CONFIG = BASE / 'examples/starter-library.config.example.json'
GUIDE = BASE / 'docs/starter-library.md'
SCOPES = ('--scope', 'Raw', '--scope', 'Review', '--scope', 'Wiki')


class StarterLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='starter-library-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'casa privada ñ'
        self.home.mkdir()
        self.root = self.home / 'library'
        shutil.copytree(STARTER, self.root)
        self.config = self.home / 'library.json'
        shutil.copyfile(CONFIG, self.config)
        (self.home / 'recovery').mkdir()

    def run_script(self, script, *args, stdin=None, core=BASE):
        return subprocess.run([sys.executable, str(core / 'scripts' / script), *args],
                              input=stdin, text=True, capture_output=True, timeout=20,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def configured(self, script, *args, stdin=None, core=BASE):
        return self.run_script(script, '--config', str(self.config), *args, stdin=stdin, core=core)

    def save(self, prepared, core=BASE):
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        packet = self.home / 'packet.json'
        packet.write_text(prepared.stdout)
        return self.configured('note_write.py', 'save', '--packet', str(packet), core=core)

    def capture(self):
        # Stands in for the host's create-only capture; Core ships no source writer.
        source = self.root / 'Raw/Sources/informe.md'
        with source.open('x') as stream:
            stream.write('---\nrole: source\nTitle: Informe ficticio\n'
                         'Reference: https://example.org/informe-ficticio\n---\n# Informe ficticio\n\n'
                         'Datos imaginarios, sin mediciones reales.\n')
        return source

    def tree(self, *folders):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for folder in folders
                for p in sorted((self.root / folder).rglob('*')) if p.is_file()}

    def test_template_root_is_self_contained_without_demo_notes(self):
        for required in ('Home.md', 'AGENTS.md', 'Raw/Sources', 'Review/Inbox', 'Wiki'):
            self.assertTrue((STARTER / required).exists(), required)
        files = [p for p in STARTER.rglob('*') if p.is_file()]
        self.assertEqual(sorted(p.relative_to(STARTER).as_posix() for p in files if p.suffix == '.md'),
                         ['AGENTS.md', 'Home.md', 'Wiki/Maps/Indice.md'])
        self.assertFalse(any(p.is_symlink() for p in STARTER.rglob('*')))
        for path in [*files, CONFIG]:
            text = path.read_text()
            for forbidden in ('/home/', '/Users/', 'examples/', 'docs/', 'scripts/', '../', '://', 'demo',
                              'ficticio', 'llm-wiki-core'):
                self.assertNotIn(forbidden, text, f'{path}: {forbidden}')
            self.assertEqual(re.findall(r'\]\((?!#)[^)]*\)', text), [], path)
            if path.suffix == '.md':
                for target in re.findall(r'\[\[([^\]|#\n]+)', text):
                    candidate = STARTER / target
                    self.assertTrue((candidate if candidate.suffix else candidate.with_suffix('.md')).is_file(),
                                    f'{path}: {target}')
        base = yaml.safe_load((STARTER / 'Biblioteca.base').read_text())
        views = {view['name'] for view in base['views']}
        for name in re.findall(r'Biblioteca\.base#([^\]|]+)', (STARTER / 'Home.md').read_text()):
            self.assertIn(name, views)
        for folder in re.findall(r'file\.inFolder\("([^"]+)"\)', (STARTER / 'Biblioteca.base').read_text()):
            self.assertTrue((STARTER / folder).is_dir(), folder)
        self.assertIn('formula.estado == "Pendiente"',
                      str(next(v for v in base['views'] if v['name'] == 'Atencion')['filters']))

    def test_rules_and_private_settings_declare_the_same_library(self):
        rules = ' '.join((STARTER / 'AGENTS.md').read_text().split())
        for declaration in ('explicitly editable as plain files', '`Raw/` preserves originals',
                            '`Review/Inbox/` holds proposals', '`Wiki/` retains reviewed knowledge',
                            'Spanish (`es`)', 'Custody is permitted here',
                            'custody, not acceptance, and never counts as the owner\'s decision',
                            'never touches `Raw/` or `Wiki/`', 'never delete the file to close it',
                            "needs the owner's own decision on the exact text"):
            self.assertIn(declaration, rules)
        settings = json.loads(CONFIG.read_text())
        self.assertEqual(settings, {
            'version': 1, 'library_root': 'library', 'authorized_paths': ['Raw', 'Review', 'Wiki'],
            'language': 'es',
            'layers': {'sources': ['Raw'], 'proposals': ['Review/Inbox'], 'knowledge': ['Wiki']},
            'write_policy': 'plain_files', 'recovery_directory': 'recovery'})

    def test_copied_root_reads_cleanly_and_its_rules_are_detected(self):
        strict = self.run_script('knowledge.py', '--root', str(self.root))
        self.assertEqual(strict.returncode, 0, strict.stderr)
        catalog = json.loads(strict.stdout)
        self.assertEqual([(n['path'], n['role']) for n in catalog['notes']], [('Wiki/Maps/Indice.md', 'map')])
        self.assertNotIn('unresolved', strict.stdout)
        existing = self.run_script('knowledge.py', '--root', str(self.root), '--mode', 'existing', *SCOPES)
        self.assertEqual(existing.returncode, 0, existing.stderr)
        data = json.loads(existing.stdout)
        self.assertEqual(data['issues'], [])
        self.assertEqual(data['library_rules_path'], 'AGENTS.md')
        mapped = self.configured('library.py', 'map', *SCOPES)
        self.assertEqual(mapped.returncode, 0, mapped.stderr)
        data = json.loads(mapped.stdout)
        self.assertEqual(data['rule_paths'], ['AGENTS.md'])
        self.assertEqual(data['issues'], [])
        self.assertEqual({item['layer']: item['paths'] for item in data['layer_proposal']},
                         {'sources': ['Raw'], 'drafts': [], 'knowledge': ['Wiki'], 'proposals': ['Review/Inbox']})
        for folder in ('Raw/Sources', 'Review/Inbox', 'Wiki/Notes', 'Wiki/Maps'):
            self.assertIn(folder, data['folders'])

    def test_reviewed_wiki_note_saves_with_recovery_and_raw_stays_immutable(self):
        source = self.capture()
        original = source.read_bytes()
        draft = ('---\nrole: note\nmaturity: seed\n---\n# Sombra\n\nIdea de prueba.\n\n'
                 'Evidence:: [[Raw/Sources/informe]]\n')
        created = self.save(self.configured('library.py', 'proposal', '--create', '--target',
                                            'Wiki/Notes/sombra.md', '--evidence', 'Raw/Sources/informe.md',
                                            stdin=draft))
        self.assertEqual(created.returncode, 0, created.stderr)
        result = json.loads(created.stdout)
        self.assertEqual(result['status'], 'plain_file_created')
        self.assertEqual((self.root / 'Wiki/Notes/sombra.md').read_text(), draft)
        record = Path(result['record'])
        self.assertEqual(record.parent, (self.home / 'recovery').resolve())
        self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
        updated = self.save(self.configured('library.py', 'proposal', '--target', 'Wiki/Notes/sombra.md',
                                            '--evidence', 'Raw/Sources/informe.md',
                                            stdin=draft + '\nSegunda idea de prueba.\n'))
        self.assertEqual(updated.returncode, 0, updated.stderr)
        restored = self.configured('note_write.py', 'restore', '--record', json.loads(updated.stdout)['record'])
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual((self.root / 'Wiki/Notes/sombra.md').read_text(), draft)
        strict = self.run_script('knowledge.py', '--root', str(self.root))
        self.assertEqual(strict.returncode, 0, strict.stderr)
        self.assertEqual(len(json.loads(strict.stdout)['notes']), 3)

        records = sorted((self.home / 'recovery').iterdir())
        for prepared in (
                self.configured('library.py', 'proposal', '--target', 'Raw/Sources/informe.md',
                                '--evidence', 'Wiki/Notes/sombra.md', stdin='# Informe alterado\n'),
                self.configured('library.py', 'proposal', '--create', '--target', 'Raw/Sources/otro.md',
                                '--evidence', 'Raw/Sources/informe.md', stdin='# Otro\n'),
                self.configured('library.py', 'proposal', '--create', '--target', 'Raw/otro.md',
                                '--evidence', 'Raw/Sources/informe.md', stdin='# Otro\n')):
            refused = self.save(prepared)
            self.assertEqual(refused.returncode, 2, refused.stdout)
            self.assertIn('immutable', refused.stderr)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in (self.root / 'Raw/Sources').iterdir()), ['.gitkeep', 'informe.md'])
        self.assertEqual(sorted((self.home / 'recovery').iterdir()), records)

    def test_proposal_is_parked_without_evidence_and_wiki_keeps_the_full_loop(self):
        kept = self.tree('Raw', 'Wiki')
        text = 'Propuesta de prueba enviada por un especialista.\n'
        park = ('proposal', '--park', '--origin', 'agente: especialista', '--conversation', 'hilo de prueba',
                '--proposed-target', 'Wiki/Notes/sombra.md', '--received', '2026-11-11')
        parked = self.save(self.configured('library.py', *park, '--target', 'Review/Inbox/sombra.md', stdin=text))
        self.assertEqual(parked.returncode, 0, parked.stderr)
        result = json.loads(parked.stdout)
        self.assertEqual((result['status'], result['accepted'], result['human_authentication_verified']),
                         ('proposal_parked', False, False))
        saved = (self.root / 'Review/Inbox/sombra.md').read_text()
        self.assertTrue(saved.endswith('\n## Texto propuesto\n\n' + text))
        self.assertIn('proposal_status: pending', saved)
        self.assertEqual(self.tree('Raw', 'Wiki'), kept)
        for target in ('Wiki/Notes/sombra.md', 'Raw/Sources/sombra.md', 'Review/sombra.md'):
            refused = self.configured('library.py', *park, '--target', target, stdin=text)
            self.assertEqual(refused.returncode, 2, refused.stdout)
        unreviewed = self.configured('library.py', 'proposal', '--create', '--target', 'Wiki/Notes/sombra.md',
                                     stdin=text)
        self.assertEqual(unreviewed.returncode, 2)
        self.assertIn('explicit evidence', unreviewed.stderr)
        self.assertEqual(self.tree('Raw', 'Wiki'), kept)
        existing = self.run_script('knowledge.py', '--root', str(self.root), '--mode', 'existing', *SCOPES)
        self.assertEqual(json.loads(existing.stdout)['issues'], [])

    def test_documented_setup_runs_from_a_read_only_checkout(self):
        block = re.search(r'```sh\n(set -eu\n.*?)```', GUIDE.read_text(), re.S)
        self.assertIsNotNone(block, 'Setup commands are missing from the guide')
        commands = block[1]
        self.assertEqual(len(commands.strip().splitlines()), 8)
        core = Path(self.temp.name) / 'core'
        for relative in ('scripts', 'config', 'examples/starter-library'):
            shutil.copytree(BASE / relative, core / relative, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(CONFIG, core / 'examples' / CONFIG.name)
        locked = [core, *core.rglob('*')]
        for path in locked:
            os.chmod(path, 0o555 if path.is_dir() else 0o444)
        try:
            private = Path(self.temp.name) / 'alta nueva'
            script = commands.replace('python3 ', f'"{sys.executable}" ')
            env = dict(os.environ, CORE=str(core), PRIVATE=str(private), PYTHONDONTWRITEBYTECODE='1')
            done = subprocess.run(['sh', '-c', script], text=True, capture_output=True, timeout=60, env=env)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn('"rule_paths": [\n    "AGENTS.md"\n  ]', done.stdout)
            self.assertEqual(stat.S_IMODE((private / 'recovery').stat().st_mode), 0o700)
            self.config, self.root, self.home = private / 'library.json', private / 'library', private
            parked = self.save(self.configured(
                'library.py', 'proposal', '--park', '--origin', 'agente: especialista', '--proposed-target',
                'Wiki/Notes/sombra.md', '--target', 'Review/Inbox/sombra.md', stdin='Texto de prueba.\n',
                core=core), core=core)
            self.assertEqual(parked.returncode, 0, parked.stderr)
            self.assertEqual(json.loads(parked.stdout)['status'], 'proposal_parked')
            again = subprocess.run(['sh', '-c', script], text=True, capture_output=True, timeout=60, env=env)
            self.assertNotEqual(again.returncode, 0, 'Setup must refuse an existing private home')
            self.assertFalse((private / 'library/starter-library').exists())
            self.assertEqual(hashlib.sha256((private / 'library/AGENTS.md').read_bytes()).hexdigest(),
                             hashlib.sha256((STARTER / 'AGENTS.md').read_bytes()).hexdigest())
        finally:
            for path in locked:
                os.chmod(path, 0o755 if path.is_dir() else 0o644)


if __name__ == '__main__':
    unittest.main()
