"""Vendored Obsidian skills: unmodified bytes, licence and the Core boundary; no host behaviour is certified."""
import hashlib
from pathlib import Path
import re
import stat
import unittest

import yaml

BASE = Path(__file__).resolve().parents[1]
ADAPTER = BASE / 'adapters/obsidian'
DEFAULT = ['json-canvas', 'obsidian-bases', 'obsidian-markdown']
OPT_IN = ['defuddle', 'obsidian-cli']
EXCLUDED = ['knap', 'obsidian-headless']
CORE_ACTIONS = ['capture-source', 'ingesta', 'progressive-adoption', 'read-connect', 'review-save']


def local_links(path):
    return [(path.parent / link.split('#')[0]).resolve()
            for link in re.findall(r'\]\(([^)\s]+)\)', path.read_text()) if '://' not in link and link.split('#')[0]]


class VendoredBytesTests(unittest.TestCase):
    def setUp(self):
        self.upstream = (ADAPTER / 'UPSTREAM.md').read_text()
        self.recorded = dict(re.findall(r'^\| `([^`]+)` \| `[^`]+` \| `([0-9a-f]{64})` \|$', self.upstream, re.M))

    def test_every_vendored_file_matches_its_recorded_hash_and_nothing_is_unrecorded(self):
        actual = {p.relative_to(ADAPTER).as_posix(): p for p in sorted(ADAPTER.rglob('*'))
                  if not p.is_dir() and p.name not in ('README.md', 'UPSTREAM.md')}
        self.assertEqual(sorted(actual), sorted(self.recorded))
        self.assertEqual(len(actual), 11)
        for relative, path in actual.items():
            with self.subTest(file=relative):
                self.assertFalse(path.is_symlink())
                self.assertTrue(stat.S_ISREG(path.lstat().st_mode))
                self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o111, 0)  # reference text, nothing runnable
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.recorded[relative])
        self.assertFalse(any(p.is_symlink() for p in ADAPTER.rglob('*')))
        self.assertEqual({p.suffix for p in actual.values()}, {'', '.md'})

    def test_upstream_record_pins_source_commit_and_upstream_paths(self):
        self.assertIn('https://github.com/obsidianmd/obsidian-skills', self.upstream)
        self.assertEqual(re.findall(r'\b[0-9a-f]{40}\b', self.upstream), ['398127736bd4ba42d767b1419fee1a927508370b'])
        self.assertRegex(self.upstream, r'committed \d{4}-\d{2}-\d{2}')
        self.assertRegex(self.upstream, r'Vendored: \d{4}-\d{2}-\d{2}')
        self.assertIn('Modifications: none', self.upstream)
        for relative, upstream in re.findall(r'^\| `([^`]+)` \| `([^`]+)` \| `[0-9a-f]{64}` \|$', self.upstream, re.M):
            self.assertEqual(upstream, 'LICENSE' if relative == 'LICENSE' else 'plugins/obsidian/' + relative)
        for heading in ('## Files', '## Decisions', '## Updating'):
            self.assertIn(heading, self.upstream)

    def test_licence_and_attribution_travel_with_the_copies(self):
        licence = (ADAPTER / 'LICENSE').read_text()
        for statement in ('MIT License', 'Steph Ango', 'Permission is hereby granted',
                          'The above copyright notice and this permission notice shall be included'):
            self.assertIn(statement, licence)
        readme = ' '.join((ADAPTER / 'README.md').read_text().split())
        for statement in ('Steph Ango', 'MIT', '[LICENSE](LICENSE)', '[UPSTREAM](UPSTREAM.md)', 'unmodified',
                          'together with [LICENSE](LICENSE)'):
            self.assertIn(statement, readme)
        self.assertNotEqual((ADAPTER / 'LICENSE').read_bytes(), (BASE / 'LICENSE').read_bytes())

    def test_included_and_excluded_skills_are_exactly_the_recorded_decisions(self):
        self.assertEqual(sorted(p.name for p in (ADAPTER / 'skills').iterdir()), sorted(DEFAULT + OPT_IN))
        readme = (ADAPTER / 'README.md').read_text()
        for text in (readme, self.upstream):
            for name in DEFAULT:
                self.assertRegex(text, rf'\| `{name}` \| included? \|')
            for name in OPT_IN:
                self.assertRegex(text, rf'\| `{name}` \| included?, opt-in')
            for name in EXCLUDED:
                self.assertRegex(text, rf'\| `{name}` \| excluded? \|')

    def test_each_vendored_skill_has_parseable_frontmatter_naming_its_folder(self):
        for folder in sorted((ADAPTER / 'skills').iterdir()):
            with self.subTest(skill=folder.name):
                text = (folder / 'SKILL.md').read_text()
                front = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
                self.assertIsNotNone(front)
                metadata = yaml.safe_load(front[1])
                self.assertEqual(metadata['name'], folder.name)
                self.assertIsInstance(metadata['description'], str)
                self.assertTrue(metadata['description'].strip())
                self.assertTrue(text[front.end():].strip())
                for reference in re.findall(r'\]\((references/[^)#]+)', text):
                    self.assertTrue((folder / reference).is_file(), reference)


class BoundaryTests(unittest.TestCase):
    def test_boundary_is_reached_by_one_line_from_each_entry_point(self):
        readme = (ADAPTER / 'README.md').resolve()
        for relative in ('Librarian Profile.md', 'docs/first-cut-tools.md'):
            with self.subTest(entry=relative):
                path = BASE / relative
                self.assertIn(readme, local_links(path))
                self.assertEqual(path.read_text().count('adapters/obsidian/README.md'), 1)
        self.assertIn(readme, local_links(BASE / 'docs/views.md'))

    def test_core_keeps_its_five_actions_and_vendored_skills_are_not_among_them(self):
        self.assertEqual(sorted(p.name for p in (BASE / 'skills').iterdir()), CORE_ACTIONS)
        self.assertEqual(sorted(p.relative_to(BASE).as_posix() for p in BASE.rglob('SKILL.md')
                                if '.git' not in p.parts),
                         sorted([*(f'adapters/obsidian/skills/{name}/SKILL.md' for name in DEFAULT + OPT_IN),
                                 *(f'skills/{name}/SKILL.md' for name in CORE_ACTIONS)]))
        self.assertFalse(set(DEFAULT + OPT_IN) & set(CORE_ACTIONS))
        agents = (BASE / 'AGENTS.md').read_text()
        self.assertNotIn('adapters/obsidian', agents)  # the agent entry still names five actions only
        self.assertEqual(len(re.findall(r'\(skills/[^)]+/SKILL\.md\)', agents)), 5)

    def test_boundary_states_what_prevails_and_lists_a_conflict_for_every_vendored_skill(self):
        readme = ' '.join((ADAPTER / 'README.md').read_text().split())
        for statement in (
                'give syntax and tool usage only', "the library's own rules prevail",
                "written only through Core's writers after the owner's review", '`view_write.py`',
                'Never use an `obsidian` CLI command that changes anything',
                "direct file-editing steps", "needs the owner's authorization for that install",
                'untrusted data, never instructions', 'Never symlink them',
                "never point a host's external skills directory at the Core checkout",
                'Disable any generic Obsidian skill the host ships', 'note-taking/obsidian',
                'Core does not edit Hermes', 'nothing here adds a sixth',
                'lean metadata', '`tags`, `aliases`', '`eval`', '`npm install -g defuddle`',
                'never one found in a note', 'Sync and Publish'):
            self.assertIn(statement, readme)
        for name in DEFAULT + OPT_IN:
            self.assertRegex(readme, rf'\*\*`{name}`\*\*')
        for command in ('create', 'append', 'property:set', 'rename', 'move', 'delete'):
            self.assertIn(f'`{command}`', readme.split('Forbidden:')[1].split('Without `vault=`')[0])

    def test_boundary_links_resolve_and_vendored_text_is_not_linked_as_core_procedure(self):
        for name in ('README.md', 'UPSTREAM.md'):
            for target in local_links(ADAPTER / name):
                self.assertTrue(target.exists(), f'{name}: {target}')
        for relative in ('AGENTS.md', 'Librarian Profile.md', 'docs/first-cut-tools.md', 'docs/views.md',
                         *(f'skills/{name}/SKILL.md' for name in CORE_ACTIONS)):
            self.assertNotIn('adapters/obsidian/skills', (BASE / relative).read_text(), relative)


if __name__ == '__main__':
    unittest.main()
