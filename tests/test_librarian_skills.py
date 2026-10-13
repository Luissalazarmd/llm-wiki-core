"""Portable procedure contracts; syntax tests are not host-behavior certification."""
from pathlib import Path
import re
import unittest
import yaml

BASE = Path(__file__).resolve().parents[1]


class LibrarianSkillTests(unittest.TestCase):
    def test_three_skills_are_discoverable_and_portable(self):
        for name in ('read-connect', 'capture-source', 'review-save'):
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
        self.assertIn('current and proposed maturity', review)
        self.assertIn('new evidence undermines', review)

    def test_entry_point_discovers_each_skill(self):
        for name in ('read-connect', 'capture-source', 'review-save'):
            self.assertIn(f'skills/{name}/SKILL.md', (BASE / 'AGENTS.md').read_text())


if __name__ == '__main__':
    unittest.main()
