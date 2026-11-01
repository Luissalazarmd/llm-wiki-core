import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import connections as c


class ConnectionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Wiki').mkdir()

    def note(self, name, body='', role='note'):
        path = self.root / 'Wiki' / (name + '.md')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\nrole: {role}\n---\n' + body)
        return path

    def measure(self):
        return c.measure(self.root, ['Wiki'])

    def test_agreed_graph_and_read_only(self):
        self.note('A', '[[Wiki/B]] [[Wiki/B|Alias]] [[Wiki/B#Section]] [[Wiki/C]]')
        self.note('B', '[[Wiki/A]]')
        self.note('C')
        self.note('D', '[[Wiki/A]]')
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*.md')}
        data = self.measure()
        a = data['notes'][0]
        self.assertEqual(a['counts'], {'incoming': 2, 'outgoing': 2, 'neighbors': 3})
        self.assertEqual(a['neighbors'], ['Wiki/B.md', 'Wiki/C.md', 'Wiki/D.md'])
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})
        self.assertEqual(data, self.measure())

    def test_exclusions(self):
        self.note('A', '''[[Wiki/A]] ![[Wiki/B]]
`[[Wiki/B]]`
```md
[[Wiki/B]]
```
<!-- [[Wiki/B]] -->
%% [[Wiki/B]] %%
    [[Wiki/B]]
\\[[Wiki/B]]
[[Wiki/Map]] [[Raw/Sources/S]] [[Wiki/Missing]] [[B]]
''')
        self.note('B')
        self.note('Map', role='map')
        data = self.measure()
        self.assertEqual(data['notes'][0]['counts']['neighbors'], 0)
        self.assertEqual(len(data['issues']), 4)
        self.assertEqual(len(data['notes']), 2)

    def test_frontmatter_and_unclosed_code(self):
        self.note('B')
        a = self.note('A')
        a.write_text('---\nrole: note\nrelated: "[[Wiki/B]]"\n---\n```\n[[Wiki/B]]')
        self.assertEqual(self.measure()['notes'][0]['counts']['outgoing'], 0)

    def test_relative_markdown_and_sections(self):
        self.note('A', '[b](./B.md#section) [[./B|Alias]] [[#Local]] [web](https://example.com)')
        self.note('B')
        self.assertEqual(self.measure()['notes'][0]['outgoing'], ['Wiki/B.md'])

    def test_scope_and_overlap(self):
        self.note('A', '[[Wiki/B]]')
        self.note('B')
        data = c.measure(self.root, ['Wiki/A.md'])
        self.assertEqual(data['notes'][0]['counts']['outgoing'], 0)
        self.assertEqual(data['coverage'], 'within_selection')
        self.assertEqual(c.measure(self.root, ['Wiki', 'Wiki/A.md'])['notes'], self.measure()['notes'])
        with self.assertRaises(ValueError):
            c.measure(self.root, ['Raw'])

    def test_drift_rejected(self):
        path = self.note('A')
        original = c.inventory
        calls = 0
        def changed(root, scopes):
            nonlocal calls
            calls += 1
            if calls == 2:
                path.write_text('---\nrole: note\n---\nchanged')
            return original(root, scopes)
        with patch.object(c, 'inventory', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.measure()

    def test_membership_drift_rejected(self):
        self.note('A')
        original = c.inventory
        calls = 0
        def changed(root, scopes):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.note('B')
            return original(root, scopes)
        with patch.object(c, 'inventory', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.measure()

    def test_symlink_and_size_rejected(self):
        self.note('A')
        (self.root / 'Wiki' / 'B.md').symlink_to(self.root / 'Wiki' / 'A.md')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.measure()
        (self.root / 'Wiki' / 'B.md').unlink()
        self.note('A', 'x' * 262144)
        with self.assertRaisesRegex(ValueError, 'byte'):
            self.measure()

    def test_unknown_zero_invalid_and_drift_activity(self):
        import yaml
        payload = '---\nrole: note\n---\nA\n'
        history = {'version': 1, 'started_at': '2026-10-30T00:00:00+00:00',
                   'baseline_sha256': c.digest(payload.encode()), 'events': []}
        text = payload.replace('---\nA', yaml.safe_dump({'iteration_tracking': history}, sort_keys=False) + '---\nA')
        self.assertEqual(c.activity(payload, {'role': 'note'})['status'], 'unknown')
        summary = c.activity(text, {'iteration_tracking': history})
        self.assertEqual(summary['count'], 0)
        self.assertFalse(summary['unrecorded_changes'])
        self.assertTrue(c.activity(text + 'changed', {'iteration_tracking': history})['unrecorded_changes'])
        history['events'] = [{}]
        self.assertEqual(c.activity(text, {'iteration_tracking': history})['status'], 'invalid')

    def test_recorded_event_count_and_crlf(self):
        import yaml
        payload = '---\r\nrole: note\r\n---\r\nA\r\n'
        history = {'version': 1, 'started_at': '2026-10-30T00:00:00+00:00',
                   'baseline_sha256': '0' * 64,
                   'events': [{'id': 'round_1', 'at': '2026-10-31T00:00:00+00:00',
                               'content_sha256': c.digest(payload.encode()),
                               'via': 'host', 'change': 'Revise explanation'}]}
        block = yaml.safe_dump({'iteration_tracking': history}, sort_keys=False).replace('\n', '\r\n')
        text = payload.replace('---\r\nA', block + '---\r\nA')
        self.assertEqual(c.activity(text, {'iteration_tracking': history}),
                         {'count': 1, 'status': 'recorded', 'unrecorded_changes': False})
        history['events'].append(dict(history['events'][0]))
        self.assertEqual(c.activity(text, {'iteration_tracking': history})['status'], 'invalid')

    def test_scope_order_and_sorts(self):
        self.note('A', '[[Wiki/B]]')
        self.note('B')
        self.assertEqual(c.measure(self.root, ['Wiki/A.md', 'Wiki/B.md']),
                         c.measure(self.root, ['Wiki/B.md', 'Wiki/A.md']))
        self.assertIn('## Resumen', c.markdown(self.measure(), 'iterations'))

    def test_invalid_metadata_fails_not_zero(self):
        self.note('A').write_text('---\nrole: note\nrole: concept\n---\n')
        with self.assertRaises(ValueError):
            self.measure()

    def test_cli_and_markdown(self):
        self.note('A', '[[Missing]]')
        result = subprocess.run([sys.executable, '-B', str(Path(c.__file__)), '--root', str(self.root), '--scope', 'Wiki'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        output = c.markdown(data)
        self.assertIn('Sin seguimiento', output)
        self.assertIn('1 enlaces excluidos', output)
        self.assertEqual(data['version'], 1)

    def test_no_implicit_roles(self):
        self.note('A', role='concept')
        self.note('B').write_text('# Foreign note\n[[Wiki/A]]')
        self.assertEqual(len(self.measure()['notes']), 1)


if __name__ == '__main__':
    unittest.main()
