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
                    self.assertTrue((path.parent / link).exists(), link)
    def test_entry_point_discovers_each_skill(self):
        for name in ('read-connect', 'capture-source', 'review-save'):
            self.assertIn(f'skills/{name}/SKILL.md', (BASE / 'AGENTS.md').read_text())


if __name__ == '__main__':
    unittest.main()
