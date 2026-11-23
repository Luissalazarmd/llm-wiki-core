#!/usr/bin/env python3
"""Read-only citation, quotation and declared-validity report. It judges no claim and approves nothing."""
from __future__ import annotations

import argparse
from datetime import date
import errno
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import sys

sys.dont_write_bytecode = True
import connections
import knowledge

VERSION = 1
LIMIT = 4 * 1024 * 1024
TOTAL = 64 * 1024 * 1024
TEXTS = ('.md', '.markdown', '.txt', '.yaml', '.yml', '.json', '.csv', '.tsv')
DEST = r'<(?P<angle>[^<>\n]+)>|(?P<md>(?:[^\s()<>]|\([^\s()<>]*\))+)'
MD = (r'\[[^\[\]\n]{0,400}\]\([ \t]{0,20}(?:' + DEST
      + r')(?:[ \t]{1,20}(?:"[^"\n]{0,400}"|\'[^\'\n]{0,400}\'|\([^()\n]{0,400}\)))?[ \t]{0,20}\)')
WIKI = r'\[\[(?P<wiki>[^\[\]\n]+)\]\]'
LINK = re.compile(r'(?<!\\)(?P<embed>!?)(?:' + WIKI + '|' + MD + ')')
NUMBERS = r'\[(?P<call>[1-9][0-9]{0,2}(?:\s*[,;–-]\s*[1-9][0-9]{0,2}){0,20})\](?!\(|\[(?!\d))'
# A quotation belongs to the link or number that follows it at once.
OWNED = re.compile(r'[\s.,;:(]*!?(?:' + WIKI + '|' + MD + '|' + NUMBERS + ')')
CALL = re.compile(r'(?<![\[!\\])' + NUMBERS)
DEFINITION = re.compile(r'^\s{0,3}\[[^\]^][^\]]*\]:')
ENTRY = re.compile(r'^\s{0,3}(?:\[([1-9][0-9]{0,2})\]|([1-9][0-9]{0,2})[.)])\s+\S')
HEADING = re.compile(r'^(#{1,6})[ \t]+(\S.*)$')
REFERENCES = re.compile(r'(?:References|Referencias|Bibliography|Bibliografía)', re.I)
MATURE = ('synthesis', 'developing', 'evergreen')
CLOSING = {'«': '»', '“': '”'}


def heading(line):
    """Return (level, title) without optional closing marks."""
    match = HEADING.match(line)
    if not match:
        return None
    title = match[2].rstrip()
    bare = title.rstrip('#')
    return len(match[1]), (bare.rstrip() if bare != title and bare[-1:] in (' ', '\t') else title)


def closes_fence(line, fence):
    marker = re.fullmatch(r'\s{0,3}(`{3,}|~{3,})\s*', line)
    return marker is not None and marker[1].startswith(fence)


def prose(text):
    """Same lines and columns, with frontmatter, fenced code, comments and inline code blanked out.

    Fences are recognized before comments, so an example never hides the rest of a note. Indented
    lines stay: they are usually lists or footnotes, and a spurious finding is better than a silent one.
    """
    text = text.removeprefix('\ufeff').replace('\r\n', '\n')
    front = re.match(r'---\n.*?\n---(?:\n|\Z)', text, re.S)
    skipped, fence, comment, result = front[0].count('\n') if front else 0, None, None, []
    for number, line in enumerate(text.split('\n')):
        if number < skipped:
            result.append('')
            continue
        marker = None if comment else re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if fence:
            fence = None if closes_fence(line, fence) else fence
            result.append('')
            continue
        if marker:
            fence = marker[1]
            result.append('')
            continue
        out, at = [], 0
        while at < len(line):
            if comment:
                end = line.find(comment, at)
                stop = len(line) if end < 0 else end + len(comment)
                comment = comment if end < 0 else None
            elif line[at] == '`':
                ticks = re.match('`+', line[at:])[0]
                end = re.search(r'(?<!`)' + ticks + r'(?!`)', line[at + len(ticks):])
                stop = at + len(ticks) + (end.end() if end else 0)
            elif line.startswith(('<!--', '%%'), at):
                comment = '-->' if line[at] == '<' else '%%'
                stop = at + (4 if line[at] == '<' else 2)
            else:
                out.append(line[at])
                at += 1
                continue
            out.append('\x00' * (stop - at))
            at = stop
        result.append(''.join(out))
    return result


def quotations(line):
    """Scan once. Yield (start, end), or (start, None) when nesting or a missing mark makes it ambiguous."""
    stack = []
    for position, char in enumerate(line):
        if char in CLOSING:
            if stack:
                stack[0][2] = True
            stack.append([position, char, False])
        elif stack and char == CLOSING[stack[-1][1]]:
            start, _, nested = stack.pop()
            if not stack:
                yield start, None if nested else position
    if stack:
        yield stack[0][0], None


def flat(text):
    """Join wrapped lines; keep paragraph breaks and every space inside a line."""
    paragraphs, current = [], []
    for line in text.replace('\r\n', '\n').split('\n'):
        line = line.strip(' \t')
        if line:
            current.append(line)
        elif current:
            paragraphs.append(' '.join(current))
            current = []
    return '\n'.join([*paragraphs, *([' '.join(current)] if current else [])])


def contains(source, quoted):
    """Literal presence between word boundaries; a sign, decimal, unit or joined word is another quantity."""
    at = source.find(quoted)
    while at >= 0:
        # Look past any spaces on either side, never past the paragraph.
        end = last = at + len(quoted)
        first = at
        while first > 0 and source[first - 1].isspace() and source[first - 1] != '\n':
            first -= 1
        head, before = source[at - 1:at], source[first - 1:first]
        while last < len(source) and source[last] in '.,;:!?…)]»”"\'':
            last += 1
        ended, tail = last > end, source[last:last + 1]
        while last < len(source) and source[last].isspace() and source[last] != '\n':
            last += 1
        following = source[last:last + 1].strip()
        opens = not head or head.isspace() or head in '([«“"\'¿¡—'
        signed = bool(re.match(r'[.,]?\d', quoted)) and before in tuple('-−–+±<>≤≥~≈')
        closes = not tail or tail.isspace() or tail == '—'
        joined = following in tuple('%‰/·×^°') or quoted[-1].isdigit() and not ended and following not in ('', *'([«“—')
        if opens and closes and not signed and not joined:
            return True
        at = source.find(quoted, at + 1)
    return False


def numbers(call):
    """Expand a Vancouver list or range; an implausible range is returned as written."""
    found = []
    for part in re.split(r'\s*[,;]\s*', call):
        ends = [int(x) for x in re.split(r'\s*[–-]\s*', part)]
        if len(ends) == 2 and ends[0] < ends[1] <= ends[0] + 100:
            found += range(ends[0], ends[1] + 1)
        else:
            found += ends
    return [str(n) for n in found]


def open_root(root):
    return os.open(root, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY)


def folder_identity(opened):
    """File system and folder; stable across restarts, different for another volume at the same path."""
    return f'{os.fstatvfs(opened).f_fsid}-{os.fstat(opened).st_ino}'.encode()


def safe_read(root, relative, limit=LIMIT):
    """Open under an already opened root, no link in any component, regular files only, bounded."""
    parts = relative.split('/')
    if any(part in ('', '.', '..') or part.startswith('.') for part in parts):
        raise ValueError('Select explicit library-relative files or folders')
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    current = os.dup(root)
    try:
        for part in parts[:-1]:
            following = os.open(part, flags | os.O_DIRECTORY, dir_fd=current)
            os.close(current)
            current = following
        following = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=current)
        os.close(current)
        current = following
        if not stat.S_ISREG(os.fstat(current).st_mode):
            raise ValueError('Regular files required: ' + relative)
        chunks, size = [], 0
        while size <= limit and (chunk := os.read(current, min(1 << 20, limit + 1 - size))):
            chunks.append(chunk)
            size += len(chunk)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValueError('Symlink in selection rejected: ' + relative) from None
        raise
    finally:
        os.close(current)
    if size > limit:
        raise ValueError('File exceeds 4 MiB: ' + relative)
    return b''.join(chunks)


class Reader:
    """Read explicitly selected files once; keep hashes and one normalized copy per source."""

    def __init__(self, root, selected):
        self.root, self.selected = root, selected
        self.hashes, self.texts, self.plain, self.sections, self.total = {}, {}, {}, {}, 0

    def text(self, relative):
        """Return the text, or None for a file that is not UTF-8."""
        if relative not in self.hashes:
            raw = safe_read(self.root, relative)
            self.total += len(raw)
            if self.total > TOTAL:
                raise ValueError('Selection exceeds 64 MiB of cited files at ' + relative)
            self.hashes[relative] = connections.digest(raw)
            try:
                self.texts[relative] = raw.decode('utf-8')
            except UnicodeDecodeError:
                self.texts[relative] = None
        return self.texts[relative]

    def quoted(self, relative, wanted):
        """True when the exact words are present, False when they are not, None when it cannot be decided."""
        if not relative.lower().endswith(TEXTS) or self.text(relative) is None or not wanted:
            return None
        if relative not in self.plain:
            text = self.text(relative)
            self.plain[relative] = flat(text), flat(re.sub(r'[*_`\\]', '', text))
        exact, loose = self.plain[relative]
        if contains(exact, wanted):
            return True
        # Words present with other marks or as part of a longer run are left to the reader.
        return None if re.sub(r'[*_`\\]', '', wanted) in loose else False

    def outline(self, relative):
        """Every heading with its ancestors, and every block identifier."""
        if relative not in self.sections:
            chains, stack, blocks = [], [], []
            for line in prose(self.text(relative)):
                if found := heading(line):
                    stack = [(level, name) for level, name in stack if level < found[0]] + [found]
                    chains.append([name for _, name in stack])
                if m := re.search(r'(?:^|\s)\^([A-Za-z0-9-]+)$', line.rstrip()):
                    blocks.append(m[1])
            self.sections[relative] = chains, blocks
        return self.sections[relative]

    def unchanged(self):
        return all(connections.digest(safe_read(self.root, r)) == value for r, value in self.hashes.items())


def locate(reader, note, target, markdown=False):
    """Return (relative path or None, fragment, problem). Never guesses a name or widens the selection."""
    if not markdown:
        target = re.split(r'\\?\|', target, maxsplit=1)[0]
    name, _, fragment = target.partition('#')
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', name):
        return None, '', 'external'
    if not name:
        return note, fragment, None
    if '%' in name or '\\' in name or name.startswith('/'):
        return None, fragment, 'unsupported_target'
    if '/' not in name and not markdown:
        return None, fragment, 'explicit_path_required'
    beside = posixpath.normpath(posixpath.join(posixpath.dirname(note), name))
    names = [beside] if name.startswith(('./', '../')) or '/' not in name else [beside, name] if markdown else [name]
    found = set()
    for option in names:
        if not any(part in ('', '.', '..') for part in option.split('/')):
            found |= {c for c in (option, option + '.md') if c in reader.selected}
    if markdown and beside not in found and beside + '.md' not in found and found:
        return None, fragment, 'root_relative_markdown_link'  # Obsidian may open it; plain Markdown would not.
    if len(found) > 1:
        return None, fragment, 'target_ambiguous'
    if not found and any(part in ('', '.', '..') for part in names[-1].split('/')):
        return None, fragment, 'unsupported_target'
    return (found.pop(), fragment, None) if found else (None, fragment, 'outside_selection_or_missing')


def fragment_problem(reader, relative, fragment):
    if not fragment:
        return None
    if not relative.lower().endswith('.md'):
        return 'fragment_not_checked'
    if reader.text(relative) is None:
        return 'source_unreadable'
    chains, blocks = reader.outline(relative)
    if fragment.startswith('^'):
        count, kind = blocks.count(fragment[1:]), 'block'
    else:
        wanted = [part.strip() for part in fragment.split('#')]

        def leads(chain):
            names = iter(chain)
            return chain[-1] == wanted[-1] and all(part in names for part in wanted)
        count, kind = sum(leads(chain) for chain in chains), 'heading'
    return None if count == 1 else kind + ('_missing' if count == 0 else '_ambiguous')


def scope_files(root, scope):
    """List regular files of one scope; hidden folders are never entered and links are refused."""
    relative = Path(scope)
    if (relative.is_absolute() or not relative.parts
            or any(p in ('.', '..') or p.startswith('.') for p in relative.parts)):
        raise ValueError('Select explicit library-relative files or folders')
    base = root / relative
    if knowledge.linked_ancestor(base) is not None:
        raise ValueError('Symlink scope rejected')
    if base.is_file():
        return [relative.as_posix()]
    if not base.is_dir():
        raise ValueError('Scope must exist')
    found = []
    def refuse(error):
        raise error
    for folder, directories, files in os.walk(base, followlinks=False, onerror=refuse):
        directories[:] = sorted(d for d in directories if not d.startswith('.'))
        for name in directories + files:
            if not name.startswith('.') and (Path(folder) / name).is_symlink():
                raise ValueError('Symlink in selection rejected')
        for name in sorted(files):
            path = Path(folder) / name
            if not name.startswith('.') and path.is_file():
                found.append(path.relative_to(root).as_posix())
                if len(found) > 5000:
                    raise ValueError('Selection exceeds 5000 files')
    return found


def selection(root, scopes, sources):
    notes = {f for scope in sorted(set(scopes)) for f in scope_files(root, scope) if f.lower().endswith('.md')}
    if not notes:
        raise ValueError('Scope must exist and select Markdown')
    if len(notes) > 2000:
        raise ValueError('Selection exceeds 2000 notes')
    chosen = notes | {f for scope in sorted(set([*scopes, *sources])) for f in scope_files(root, scope)}
    if len(chosen) > 5000:
        raise ValueError('Selection exceeds 5000 files')
    return sorted(notes), chosen


# PyYAML constructors may raise these for hostile tags.
YAML_ERRORS = (ValueError, TypeError, AttributeError, KeyError, RecursionError, knowledge.yaml.YAMLError)


def declared_role(properties):
    role = properties.get('role')
    return knowledge.LEGACY_ROLES.get(role, role) if isinstance(role, str) else None


def validity(reader, note, properties, today):
    """Report declared dates and replacements; nothing expires or is retired by itself."""
    found = []
    stale, replacement = properties.get('stale_after'), properties.get('superseded_by')
    if stale is None and replacement is None:
        return found
    role, maturity = declared_role(properties), properties.get('maturity')
    if role not in ('note', 'map') or role == 'note' and not (isinstance(maturity, str) and maturity in MATURE):
        found.append({'kind': 'validity_not_applicable', 'detail': 'only a synthesis, evergreen note or map declares it'})
    if stale is not None:
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(stale)):
                raise ValueError
            value = date.fromisoformat(str(stale))
        except ValueError:
            found.append({'kind': 'stale_after_invalid', 'detail': str(stale)[:80]})
        else:
            if value < today:
                found.append({'kind': 'stale', 'detail': value.isoformat()})
    if replacement is not None:
        match = re.fullmatch(r'\[\[([^\[\]\n]+)\]\]', replacement) if isinstance(replacement, str) else None
        path, fragment, problem = locate(reader, note, match[1]) if match else (None, '', 'explicit_wikilink_required')
        if problem is None and fragment:
            problem = 'explicit_note_required'
        if problem is None and path == note:
            problem = 'replaces_itself'
        if problem is None:
            text = reader.text(path) if path.lower().endswith('.md') else None
            try:
                role = declared_role(knowledge.metadata_from(text)) if text is not None else None
            except YAML_ERRORS:
                role = None
            problem = None if role in ('note', 'map') else 'target_is_not_a_note_or_map'
        found.append({'kind': 'superseded', 'detail': path} if problem is None
                     else {'kind': 'superseded_by_unresolved', 'detail': problem})
    return found


def references(lines):
    """Return (start or None, end, entries, repeated). An entry ends at the next entry or at any heading."""
    start = next((n for n, x in enumerate(lines) if (h := heading(x)) and REFERENCES.fullmatch(h[1])), None)
    if start is None:
        return None, len(lines), {}, []
    level = heading(lines[start])[0]
    stop = next((n for n in range(start + 1, len(lines)) if (h := heading(lines[n])) and h[0] <= level), len(lines))
    entries, repeated, current = {}, [], None
    for n in range(start + 1, stop):
        if heading(lines[n]):
            current = None
        elif m := ENTRY.match(lines[n]):
            current = m[1] or m[2]
            if current in entries:
                repeated.append((n + 1, current))
            entries.setdefault(current, [])
        if current:
            entries[current] += [target(x) for x in LINK.finditer(lines[n])]
    return start, stop, entries, repeated


def target(match):
    """Keep the link kind: Markdown destinations resolve beside the note, wikilinks from the root."""
    return (match['wiki'], False) if match['wiki'] else (match['angle'] or match['md'], True)


def check_note(reader, note, today, cited):
    empty = {'links': 0, 'quotes': 0}
    text = reader.text(note)
    if text is None:
        return {'path': note, 'findings': [{'line': 1, 'kind': 'note_unreadable', 'detail': 'not UTF-8'}], 'checked': empty}
    try:
        properties = knowledge.metadata_from(text.removeprefix('﻿'))
    except YAML_ERRORS as error:
        return {'path': note, 'findings': [{'line': 1, 'kind': 'frontmatter_invalid', 'detail': str(error)[:240]}],
                'checked': empty}
    lines, original = prose(text), text.removeprefix('\ufeff').replace('\r\n', '\n').split('\n')
    findings = [{'line': 1, **item} for item in validity(reader, note, properties, today)]
    start, stop, entries, repeated = references(lines)
    findings += [{'line': n, 'kind': 'reference_repeated', 'detail': c} for n, c in repeated]
    if start is not None:
        calls = {}
        for n, line in enumerate(lines, 1):
            if start < n - 1 < stop or DEFINITION.match(line):
                continue
            for m in CALL.finditer(line):
                for c in numbers(m['call']):
                    calls.setdefault(c, n)
        findings += [{'line': n, 'kind': 'reference_missing', 'detail': c} for c, n in calls.items() if c not in entries]
        findings += [{'line': start + 1, 'kind': 'reference_unused', 'detail': c} for c in entries if c not in calls]
    links = quotes = 0
    for n, line in enumerate(lines, 1):
        spans = []
        for m in LINK.finditer(line):
            spans.append(m.span())
            name, markdown = target(m)
            path, fragment, problem = locate(reader, note, name, markdown)
            if problem == 'external':
                continue
            links += 1
            if problem is None:
                if path != note:
                    cited.add(path)
                problem = fragment_problem(reader, path, fragment)
            if problem:
                findings.append({'line': n, 'kind': problem, 'detail': name[:240]})
        for m in re.finditer(r'\]\(|\[\[', line):
            if not any(a <= m.start() < b for a, b in spans) and line[m.start() - 1:m.start()] != '\\':
                findings.append({'line': n, 'kind': 'link_not_checked', 'detail': original[n - 1].strip()[:240]})
        for begin, end in quotations(line):
            if end is None:
                findings.append({'line': n, 'kind': 'quote_not_checked', 'detail': original[n - 1].strip()[:240]})
                continue
            rest = line[end + 1:]
            if re.fullmatch(r'[\s.,;:(]*', rest) and n < len(lines):
                rest += ' ' + lines[n]  # The citation may begin the next line of the same paragraph.
            owner = OWNED.match(rest)
            if owner is None:
                continue
            wanted = original[n - 1][begin + 1:end].strip().rstrip('.,;:…')
            if owner['call']:
                targets = [t for c in numbers(owner['call']) for t in entries.get(c, [])]
            else:
                targets = [target(owner)]
            places = {p[0] for p in (locate(reader, note, *t) for t in targets) if p[2] is None and p[0] != note}
            results = [reader.quoted(p, wanted) for p in sorted(places)]
            if True in results:
                quotes += 1
            else:
                kind = 'quote_not_checked' if not results or None in results else 'quote_not_found'
                quotes += kind == 'quote_not_found'
                findings.append({'line': n, 'kind': kind, 'detail': wanted[:240]})
    return {'path': note, 'findings': sorted(findings, key=lambda f: (f['line'], f['kind'], f['detail'])),
            'checked': {'links': links, 'quotes': quotes}}


def earlier(since, library, scopes, sources):
    """Accept only a report of this tool over the same library and selection."""
    if (not isinstance(since, dict) or since.get('algorithm') != 'citation-check' or since.get('version') != VERSION
            or not isinstance(since.get('sources'), dict)
            or not all(isinstance(k, str) and isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v)
                       for k, v in since['sources'].items())):
        raise ValueError('The earlier report is not a version 1 citation report')
    if since.get('library') != library or since.get('scope') != scopes or since.get('sources_scope') != sources:
        raise ValueError('The earlier report covers a different library or selection')
    return since['sources']


NOTHING = object()


def check(root, scopes, sources=(), today=None, since=NOTHING):
    root = knowledge.library_root(Path(root))
    if not scopes:
        raise ValueError('Explicit scope required')
    scopes, sources = sorted(set(scopes)), sorted(set(sources))
    opened = open_root(root)
    try:
        # The path and the folder itself: another library placed at the same path is another library.
        library = connections.digest(os.fsencode(root) + b'\0' + folder_identity(opened))
        previous = None if since is NOTHING else earlier(since, library, scopes, sources)
        notes, chosen = selection(root, scopes, sources)
        reader, cited = Reader(opened, chosen), set()
        today = today or date.today()
        report = [check_note(reader, note, today, cited) for note in notes]
        for path in sorted(cited):
            reader.text(path)  # A binary source is hashed, never interpreted.
        versions = {path: reader.hashes[path] for path in sorted(cited)}
        same = os.path.samestat(os.fstat(opened), os.stat(root, follow_symlinks=False))
        if not same or selection(root, scopes, sources) != (notes, chosen) or not reader.unchanged():
            raise ValueError('Input changed during the check; discard result')
    finally:
        os.close(opened)
    changed = [] if previous is None else [
        {'path': p, 'kind': 'source_changed' if p in versions else 'source_no_longer_cited'}
        for p, value in sorted(previous.items()) if versions.get(p) != value]
    return {'algorithm': 'citation-check', 'version': VERSION, 'library': library, 'scope': scopes,
            'sources_scope': sources, 'today': today.isoformat(), 'notes': report, 'sources': versions,
            'changed_since': changed,
            'limits': 'Structure and exact words only: no claim, entailment, review or approval is judged.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--scope', action='append', required=True, help='notes to check')
    parser.add_argument('--sources', action='append', default=[], help='further files or folders the notes may cite')
    parser.add_argument('--since', type=Path, help='an earlier report of this tool, kept outside the library')
    args = parser.parse_args()
    try:
        since = NOTHING
        if args.since:
            with args.since.open('rb') as stream:
                raw = stream.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError('The earlier report exceeds 8 MiB')
            since = json.loads(raw.decode('utf-8'))
        print(json.dumps(check(args.root, args.scope, args.sources, since=since), ensure_ascii=False,
                         sort_keys=True, indent=2))
    except (ValueError, OSError, RecursionError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
