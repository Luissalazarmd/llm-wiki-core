"""Portable procedure contracts; syntax tests are not host-behavior certification."""
from pathlib import Path
import re
import unittest
import yaml

BASE = Path(__file__).resolve().parents[1]


class LibrarianSkillTests(unittest.TestCase):
    def test_optional_connections_are_discoverable_from_work_entries(self):
        reference = (BASE / 'docs/note-connections.md').resolve()
        self.assertTrue(reference.is_file())
        for relative in ('Librarian Profile.md', 'docs/knowledge-workflow.md',
                         'skills/read-connect/SKILL.md'):
            with self.subTest(entry=relative):
                path = BASE / relative
                targets = [path.parent / link.split('#')[0]
                           for link in re.findall(r'\]\(([^)]+)\)', path.read_text())
                           if '://' not in link]
                self.assertIn(reference, [target.resolve() for target in targets])

    def test_four_skills_are_discoverable_and_portable(self):
        for name in ('progressive-adoption', 'read-connect', 'capture-source', 'review-save'):
            path = BASE / 'skills' / name / 'SKILL.md'
            self.assertTrue(path.is_file(), f'Missing {name} skill')
            text = path.read_text()
            front = yaml.safe_load(text.split('---', 2)[1])
            self.assertEqual(front['name'], name)
            self.assertLessEqual(len(front['description']), 60)
            self.assertTrue(front['description'].endswith('.'))
            self.assertNotIn('/home/', text)
            for heading in ('## When to Use', '## Procedure', '## Pitfalls', '## Verification'):
                self.assertIn(heading, text)
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if '://' not in link:
                    self.assertTrue((path.parent / link.split('#')[0]).exists(), link)
    def test_emergence_is_discovered_from_profile_reading_and_review_skills(self):
        for relative in ('Librarian Profile.md', 'skills/read-connect/SKILL.md', 'skills/review-save/SKILL.md'):
            text = (BASE / relative).read_text()
            self.assertIn('knowledge-workflow.md#idea-emergence', text, relative)
        workflow = (BASE / 'docs/knowledge-workflow.md').read_text()
        self.assertIn('## Idea emergence', workflow)
        for concept in ('Semilla', 'Síntesis', 'Evergreen', 'not a source-count or link-count threshold',
                        'Raw originals remain unchanged', 'publication permission is separate'):
            self.assertIn(concept, workflow)
        review = (BASE / 'skills/review-save/SKILL.md').read_text()
        self.assertIn('current and proposed maturity', ' '.join(review.split()))
        self.assertIn('new evidence undermines', review)

    def test_review_requires_readable_exact_content_before_confirmation(self):
        contract = (BASE / 'docs/review-contract.md').read_text()
        for phrase in ('full exact content', 'titles, paths, hashes or summaries alone', 'post-save review'):
            self.assertIn(phrase, contract)
        self.assertIn('docs/review-contract.md', (BASE / 'skills/review-save/SKILL.md').read_text())

    def test_entry_point_discovers_each_skill(self):
        for name in ('progressive-adoption', 'read-connect', 'capture-source', 'review-save'):
            self.assertIn(f'skills/{name}/SKILL.md', (BASE / 'AGENTS.md').read_text())

    def test_adoption_identifies_starting_material_before_requesting_a_sample(self):
        text = (BASE / 'skills/progressive-adoption/SKILL.md').read_text()
        for rule in ('## Identify the starting point', 'existing wiki', 'collected articles',
                     'authored articles', 'starting from scratch', 'ask one short question',
                     'do not search the device', 'unknown is not absent',
                     'no automatic folder creation', 'where they are'):
            self.assertIn(rule, ' '.join(text.split()), rule)
        self.assertLess(text.index('## Identify the starting point'), text.index('1. **Observe a sample.**'))
        for relative in ('docs/onboarding.md', 'README.md'):
            self.assertIn('starting point', (BASE / relative).read_text(), relative)

    def test_adoption_is_a_bounded_action_not_a_migration_or_router(self):
        path = BASE / 'skills/progressive-adoption/SKILL.md'
        self.assertTrue(path.is_file(), 'Progressive adoption procedure is missing')
        text = path.read_text()
        for rule in ('small authorized sample', 'external sources', 'personal notes',
                     'existing syntheses', 'author drafts', 'mixed folders',
                     'first useful case', 'mapping is not acceptance', 'do not move',
                     'actual confirmation', 'proposal-only', 'bytes and paths',
                     'no migration runtime', 'no whole-library completion claim'):
            self.assertIn(rule, ' '.join(text.split()), rule)
        for relative in ('Librarian Profile.md', 'docs/onboarding.md', 'README.md'):
            self.assertIn('progressive-adoption/SKILL.md', (BASE / relative).read_text(), relative)


if __name__ == '__main__':
    unittest.main()
