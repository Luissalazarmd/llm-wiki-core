"""The product must be reproducible without a particular library engine."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EngineIndependenceTests(unittest.TestCase):
    def test_vendor_installer_adapters_and_skipped_vendor_suite_are_not_product(self):
        for path in ('scripts/install_private_engine.py', 'adapters/review_chat.py',
                     'config/private-engine-files.json', 'config/example.json',
                     'tests/test_private_engine_install.py', 'tests/synthetic_engine_smoke.py',
                     'docs/upstream.md', 'docs/local-integration.md', 'docs/guided-increment.md'):
            self.assertFalse((ROOT / path).exists(), path)

    def test_active_startup_does_not_request_specific_engine_installation(self):
        for path in ('AGENTS.md', 'README.md', 'docs/onboarding.md', 'docs/runtime.md',
                     'docs/implementation.md', 'docs/acceptance.md', 'docs/review-contract.md', 'docs/sync.md'):
            text = (ROOT / path).read_text()
            for token in ('LIBRARIAN_ENGINE_SOURCE', 'install_private_engine.py',
                          'private-engine-files.json', 'local-integration.md', 'upstream.md', 'Git/bootstrap flow'):
                self.assertNotIn(token, text, path)

    def test_guided_entry_does_not_require_retired_or_future_writer(self):
        for path in ('AGENTS.md', 'Librarian Profile.md', 'docs/knowledge-workflow.md'):
            text = (ROOT / path).read_text()
            for token in ('existing verified engine', 'canonical host/engine', 'future host'):
                self.assertNotIn(token, text, path)

    def test_readme_starts_with_scoped_existing_library_command(self):
        commands = [line for line in (ROOT / 'README.md').read_text().splitlines()
                    if line.startswith('python3 scripts/knowledge.py ')]
        self.assertIn('--mode existing --scope', commands[0])

    def test_ontology_contains_only_role_and_maturity_vocabulary(self):
        ontology = json.loads((ROOT / 'config/ontology.json').read_text())
        self.assertEqual(ontology, {'version': '2.0', 'roles': ['source', 'note', 'map'],
                                    'maturity': ['seed', 'synthesis', 'evergreen']})


if __name__ == '__main__':
    unittest.main()
