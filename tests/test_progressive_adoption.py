"""Foreign-library adoption slices; fixture judgments are not human approval."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


class ProgressiveAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='adoption-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'library'
        for name in ('Caja', 'Cuaderno', 'Textos'):
            (self.root / name).mkdir(parents=True)
        (self.base / 'recovery').mkdir()
        (self.root / 'AGENTS.md').write_text('Synthetic rules: preserve originals and author prose; review updates.\n')
        self.source = 'Caja/registro.md'
        self.personal = 'Caja/idea-propia.md'
        self.target = 'Cuaderno/explicacion.md'
        (self.root / self.source).write_bytes(b'---\r\nReference: fixture:retrieval-a\r\n---\r\n# Invented record\r\nThree planted cards were found; other finds were not measured.\r\n')
        (self.root / self.personal).write_text('---\nauthor: Fictional owner\nkind: personal hypothesis\n---\n# My idea\nPerhaps labels affect retrieval. This is not evidence.\n')
        self.original = ('---\nauthor: Fictional owner\nstatus: growing\n---\n# Existing explanation\n'
                         'I want to distinguish counted cards from overall usefulness.\n[[Caja/registro]]\n')
        (self.root / self.target).write_text(self.original)
        (self.root / 'Textos/borrador.md').write_text('# Private authoring fixture\nAn unfinished essay, not reviewed knowledge.\n')
        (self.root / 'unselected.md').write_text('Unselected fixture')
        self.settings = {'version': 1, 'library_root': 'library',
                         'authorized_paths': [self.source, self.personal, 'Cuaderno', 'Textos'],
                         'layers': {'sources': [self.source], 'knowledge': [self.target], 'drafts': ['Textos']}}
        self.config = self.base / 'personal.json'
        self.config.write_text(json.dumps(self.settings))
        sys.path.insert(0, str(BASE / 'scripts'))
        self.addCleanup(lambda: sys.path.remove(str(BASE / 'scripts')))
        spec = importlib.util.spec_from_file_location('adoption_writer', BASE / 'scripts/note_write.py')
        assert spec and spec.loader
        self.writer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.writer)
        self.library = self.writer.library
        self.knowledge = self.library.knowledge
        self.draft = self.original + ('\n## Reviewed fixture clarification\n'
            'The source counts planted cards only, not overall usefulness. '
            'Locator: Caja/registro.md, body paragraph 1. '
            'My hypothesis remains untested; [[Caja/idea-propia]] is author context, not independent evidence.\n')

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.root.rglob('*') if p.is_file()}

    def packet(self):
        return self.knowledge.prepare_proposal(self.root, self.target, self.draft,
                                              [self.source, self.personal])

    def test_small_sample_mapping_preserves_mixed_folder_authorship_and_unknown_states(self):
        before = self.snapshot()
        loaded = self.library.load_config(self.config)
        self.assertEqual(loaded.get('write_policy', 'read_only'), 'read_only')
        scopes = [self.source, self.personal, self.target, 'Textos/borrador.md']
        mapped = self.library.map_library(self.root, scopes, loaded['layers'])
        self.assertEqual(len(mapped['notes']), 4)
        self.assertTrue(all(n['maturity'] == 'unknown' and n['review'] == 'unverified' for n in mapped['notes']))
        source_mapping = next(item for item in mapped['layer_proposal'] if item['layer'] == 'sources')
        self.assertEqual(source_mapping['paths'], [self.source])
        self.assertEqual(source_mapping['status'], 'declared_not_verified')
        self.assertFalse(mapped['conventions']['classification_inferred'])
        self.assertFalse(mapped['migration_performed'])
        with self.assertRaisesRegex(ValueError, 'outside authorized_paths'):
            self.library.authorize(self.root, loaded['authorized_paths'], 'unselected.md')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(any((self.root / name).exists() for name in ('Raw', 'Review', 'Wiki')))

    def test_first_case_reuses_explanation_with_no_write_during_proposal_and_check(self):
        before = self.snapshot()
        packet = self.packet()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(packet['approval_available'])
        self.settings.update(write_policy='plain_files', recovery_directory='recovery')
        self.config.write_text(json.dumps(self.settings))
        loaded = self.library.load_config(self.config)
        self.writer.check_packet(loaded, packet)
        self.assertEqual(self.snapshot(), before)
        saved = self.writer.save(loaded, packet)  # Fixture execution, not a simulated user event.
        self.assertFalse(saved['human_authentication_verified'])
        self.assertEqual((self.root / self.target).read_bytes(), self.draft.encode())
        after = self.snapshot()
        self.assertEqual(set(before), set(after))
        for relative in before:
            if relative != self.target:
                self.assertEqual(before[relative], after[relative], relative)
        self.assertTrue((self.root / self.target).read_text().startswith(self.original))
        view = self.knowledge.focus(self.knowledge.discover(self.root,
            [self.source, self.personal, self.target]), 'path:' + self.target)
        self.assertEqual(len(view['notes']), 3)
        self.assertEqual(len(view['edges']), 2)
        record = self.writer.read_json(Path(saved['record']))
        self.assertEqual(record['before_sha256'], packet['target']['base_sha256'])
        self.assertFalse(any((self.root / name).exists() for name in ('Raw', 'Review', 'Wiki')))

    def test_mapping_never_grants_writing_and_source_or_stale_base_is_refused(self):
        before = self.snapshot()
        packet = self.packet()
        loaded = self.library.load_config(self.config)
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.writer.save(loaded, packet)
        self.assertEqual(self.snapshot(), before)
        self.settings.update(write_policy='plain_files', recovery_directory='recovery')
        self.config.write_text(json.dumps(self.settings))
        loaded = self.library.load_config(self.config)
        source_packet = self.knowledge.prepare_proposal(self.root, self.source, 'Changed source', [])
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.writer.save(loaded, source_packet)
        (self.root / self.target).write_text(self.original + 'Later owner work\n')
        with self.assertRaisesRegex(ValueError, 'Stale proposal base'):
            self.writer.save(loaded, packet)
        self.assertEqual((self.root / self.target).read_text(), self.original + 'Later owner work\n')
        self.assertEqual(list((self.base / 'recovery').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
