#!/usr/bin/env python3
"""Format a citation from bibliographic fields found verbatim in a document's first pages. Writes nothing.

Finding a field printed there shows it is not invented, not that it belongs to this work: the owner confirms it."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata

sys.dont_write_bytecode = True

VERSION = 4
LIMIT = 1024 * 1024
CAPS = {'title': 512, 'journal': 256, 'server': 64, 'year': 4, 'volume': 32, 'issue': 32, 'pages': 32,
        'doi': 256, 'arxiv': 64, 'family': 128, 'given': 128}
MAX_AUTHORS = 100
MAX_SPANS = 200
FIELDS = ('title', 'journal', 'server', 'year', 'volume', 'issue', 'pages', 'doi', 'arxiv')
REQUIRED = ('authors', 'title', 'year')
NEAR = 120          # characters: year beside the journal or preprint id
LOCATOR = 300       # characters: a DOI beside the journal, preprint id or year
BYLINE = 200        # characters between consecutive authors
TITLE_BEFORE = 1500  # characters between the title and the first author
FRONT = 5000        # characters searched for title and authors when no abstract or introduction heading is found
DASHES = str.maketrans('‐‑‒–—−', '------')
LINE_BREAK_HYPHEN = re.compile(r'(?<=\w)-[^\S\n]*\n[^\S\n]*(?=\w)')
REFERENCES = re.compile(r'^[^\S\n]*(?:\d+[.)]?[^\S\n]+)?(?:references|bibliography|works cited|referencias'
                        r'|bibliograf[ií]a|literature cited)(?:[^\S\n]+and[^\S\n]+notes)?'
                        r'(?:[^\S\n]*\((?:continued|cont\.?|continuaci[oó]n)\))?[^\S\n]*:?[^\S\n]*$', re.I | re.M)
OPENING = re.compile(r'^[^\S\n]*(?:\d+[.)]?[^\S\n]+)?(?:abstract|summary|introduction|background|keywords'
                     r'|resumen|introducci[oó]n|antecedentes|palabras clave)\b', re.I | re.M)
DEGREES = ('MD', 'PhD', 'MSc', 'MS', 'MA', 'MPH', 'DrPH', 'DPhil', 'MBBS', 'MBChB', 'BSc', 'BS', 'BA', 'RN', 'PharmD',
           'DO', 'DDS', 'FRCP', 'FACC', 'FAHA', 'FESC', 'MRCP', 'Jr', 'Sr')
CONNECTOR = re.compile(r'(?:[\d*†‡§¶#⁎∗.]+|[a-z]|and|&|y|e|und|et|(?:' + '|'.join(DEGREES) + r')\.?)')
NAMEISH = re.compile(r'(?:[^\W\d_][^\W\d_.\'’-]*\.?|[^\W\d_]\.)')
IDENTIFIERS = {
    'doi': re.compile(r'10\.[0-9]{4,9}/\S+'),
    'arxiv': re.compile(r'(?:[0-9]{4}\.[0-9]{4,5}|[a-zA-Z][\w.-]*/[0-9]{7})(?:v[1-9][0-9]*)?'),
}


def one_line(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def normal(text: str, *, lines: bool = False) -> str:
    """NFKC, with control characters dropped and other whitespace as one space."""
    text = unicodedata.normalize('NFKC', text.replace('\r\n', '\n'))
    return ''.join(c if c == '\n' and lines else ' ' if c.isspace() else c
                   for c in text if c.isspace() or unicodedata.category(c)[0] != 'C')


def clean(value, field: str) -> str:
    if type(value) is int and field in ('year', 'volume', 'issue'):
        value = str(value)
    if not isinstance(value, str):
        return ''
    value = one_line(normal(value))  # kept as printed for the citation; dashes are matched loosely
    return value if len(value) <= CAPS[field] else ''


def literal(value: str) -> str:
    value = value.translate(DASHES)
    return r'\s*-\s*'.join(r'\s+'.join(map(re.escape, part.split())) for part in value.split('-'))


def readings(text: str) -> list[str]:
    """The front matter as printed, and with end-of-line hyphens joined; references are left out."""
    text = normal(text, lines=True).translate(DASHES)
    cut = REFERENCES.search(text)
    text = text[:cut.start()] if cut else text  # nothing after the reference list counts
    return [text, LINE_BREAK_HYPHEN.sub('', text)]


def spans(field: str, value: str, text: str) -> list[tuple[int, int]]:
    if field in IDENTIFIERS:
        compact = re.sub(r'\s+', '', value).translate(DASHES)
        if not IDENTIFIERS[field].fullmatch(compact):
            return []
        pattern = r'\s*'.join(map(re.escape, compact))
        if field == 'doi':
            # Whole: not followed by more DOI text on the same line, nor on the next line after a single break.
            end, flags = r'(?![^\s.,;)\]]|[.,;)\]]\S)(?![^\S\n]*\n[^\S\n]*[\w(./-])', re.I
        else:
            versioned = re.search(r'v[0-9]+$', compact)
            pattern, end, flags = pattern + ('' if versioned else r'(?:v[1-9][0-9]*)?'), r'(?![\w/-]|\.[\w/])', 0
    else:
        pattern, end, flags = literal(value), r'(?!\w)', 0
    found = []
    for match in re.finditer(rf'(?<!\w){pattern}{end}', text, flags):
        found.append(match.span())
        if len(found) == MAX_SPANS:
            break
    return found


def near(found: list[tuple[int, int]], anchors: list[tuple[int, int]], distance: int) -> list[tuple[int, int]]:
    return [s for s in found if any(abs(s[0] - a[0]) <= distance or abs(s[1] - a[1]) <= distance for a in anchors)]


def whole_block(found: list[tuple[int, int]], text: str) -> list[tuple[int, int]]:
    """Matches that fill their lines: nothing else on the first line before, nor on the last line after."""
    def line_start(i):
        return text.rfind('\n', 0, i) + 1

    def line_end(i):
        j = text.find('\n', i)
        return len(text) if j < 0 else j
    return [(a, b) for a, b in found if not text[line_start(a):a].strip() and not text[b:line_end(b)].strip()]


def unspaced(text: str) -> bool:
    """Written in a script without spaces between words (Chinese, Japanese)."""
    return any(unicodedata.name(ch, '').startswith(('CJK', 'HIRAGANA', 'KATAKANA')) for ch in text)


def gap_is_byline(gap: str) -> bool:
    """Between two authors only separators, affiliation marks, degrees and a connector: never another name."""
    return all(CONNECTOR.fullmatch(token) for token in re.split(r'[\s,;]+', gap) if token)


def looks_like_byline(line: str) -> bool:
    """A line of names, each followed by an affiliation digit or mark: more of the same byline."""
    line = line.strip()
    if not line or line.endswith((',', '&')) or re.search(r'(?:^|\s)and$', line):
        return bool(line)
    names = re.findall(r'((?:[^\W\d_][\w.\'’-]*\s+){0,3}[^\W\d_][\w\'’-]*)\s*[\d*†‡§¶#⁎∗]', line)
    return bool(names) and gap_is_byline(re.sub(r'(?:[^\W\d_][\w.\'’-]*\s+){0,3}[^\W\d_][\w\'’-]*(?=\s*[\d*†‡§¶#⁎∗])',
                                                '', line))


def neighbour(text: str, index: int, step: int) -> str:
    """The nearest non-empty line before (step -1) or after (step 1) the line holding index."""
    lines, here = text.split('\n'), text.count('\n', 0, index)
    i = here + step
    while 0 <= i < len(lines):
        if lines[i].strip():
            return lines[i]
        i += step
    return ''


def initials(given: str) -> str:
    return given if unspaced(given) else ''.join(p[0].upper() for p in re.findall(r'[^\W\d_]+', given))


def byline(authors, text: str) -> tuple[list[str], int, int] | None:
    """The complete author list, in order, as one byline: (names, start, end), or None."""
    if not isinstance(authors, list) or not 0 < len(authors) <= MAX_AUTHORS:
        return None
    people = []
    for author in authors:
        if not isinstance(author, dict):
            return None
        family, given = clean(author.get('family'), 'family'), clean(author.get('given'), 'given')
        if not family or not given:
            return None
        f, g = literal(family), literal(given)
        people.append((family, given, re.compile(rf'(?<!\w)(?:{g}\s+{f}|{f}(?:\s*,\s*|\s+){g}|{g}{f}|{f}{g})'
                                                 rf'(?![^\W\d_])')))
    for first in people[0][2].finditer(text):
        line_start = text.rfind('\n', 0, first.start()) + 1
        if re.search(r'[^\W\d_]', text[line_start:first.start()]):
            continue
        end, ok = first.end(), True
        for _, _, pattern in people[1:]:
            match = pattern.search(text, end, end + BYLINE + 200)
            if match is None or match.start() - end > BYLINE or not gap_is_byline(text[end:match.start()]):
                ok = False
                break
            end = match.end()
        line_end = text.find('\n', end)
        tail = text[end:line_end if line_end >= 0 else len(text)]
        before, after = neighbour(text, first.start(), -1), neighbour(text, end, 1)
        if (ok and gap_is_byline(tail) and not tail.rstrip().endswith((',', '&'))
                and not re.search(r'(?:^|\s)and\s*$', tail)
                and not looks_like_byline(after) and not re.search(r'(?:,|&|\sand)\s*$', before)
                and not looks_like_byline(before)):
            names = [f'{family} {initials(given)}'.rstrip() if not unspaced(family + given) else family + given
                     for family, given, _ in people]
            return names, first.start(), end
    return None


def locator(year: str, values: dict, text: str, anchors: list[tuple[int, int]]) -> dict:
    """Year, volume, issue and pages as one locator beside the journal or preprint id."""
    kept = {}
    years = near(spans('year', year, text), anchors, NEAR)
    if not years:
        return kept
    kept['year'] = year
    y = literal(year)
    v, i, p = (literal(values[f]) if values[f] else None for f in ('volume', 'issue', 'pages'))
    forms = []
    if v:
        forms.append((rf'(?<!\w){y}\s*[;,]\s*{v}' + (rf'(?:\s*\(\s*(?P<issue>{i})\s*\))?' if i else '')
                      + (rf'(?:\s*:\s*(?P<pages>{p}))?' if p else '') + r'(?![\w-])', 'volume'))
        forms.append((rf'(?<!\w)vol(?:ume)?\.?\s*{v}(?!\w)', 'volume'))
    if i:
        forms.append((rf'(?<!\w)(?:no|issue|n\.?º?)\.?\s*(?P<issue>{i})(?!\w)', None))
    if p:
        forms.append((rf'(?<!\w)(?:pp?|pages?)\.?\s*(?P<pages>{p})(?![\w-])', None))
    for pattern, field in forms:
        for match in re.finditer(pattern, text, re.I):
            if not near([match.span()], years, NEAR):
                continue
            if field:
                kept[field] = values[field]
            for group in ('issue', 'pages'):
                if group in match.re.groupindex and match.group(group):
                    kept[group] = values[group]
    if 'issue' in kept and 'volume' not in kept:
        del kept['issue']
    return kept


def vancouver(fields: dict) -> str:
    """ICMJE/Vancouver: up to six authors, otherwise the first six and et al."""
    authors = fields['authors']
    parts = [', '.join(authors if len(authors) <= 6 else authors[:6] + ['et al.']), fields['title']]
    if fields.get('journal'):
        volume = fields.get('volume', '')
        volume += f"({fields['issue']})" if volume and fields.get('issue') else ''
        date = fields['year'] + (f';{volume}' if volume else '') + (f":{fields['pages']}" if fields.get('pages') else '')
        parts += [fields['journal'], date]
    else:
        origin = f"arXiv:{fields['arxiv']}" if fields.get('arxiv') else fields.get('server')
        parts += [f'{origin} [Preprint]' if origin else None, fields['year']]
    citation = ' '.join(p if p.endswith(('.', '?', '!')) else p + '.' for p in parts if p)
    return citation + (f" doi: {fields['doi']}" if fields.get('doi') else '')


STYLES = {'vancouver': vancouver}


def verify(given: dict, text: str) -> tuple[dict, list[str]]:
    kept, dropped = {}, []
    opening = OPENING.search(text)
    front = text[:opening.start()] if opening and opening.start() > 0 else text[:FRONT]
    found = byline(given.get('authors'), front)
    if found:
        kept['authors'] = found[0]
    elif given.get('authors'):
        dropped.append('authors')
    values = {f: clean(given.get(f), f) for f in FIELDS}
    if values['title'] and found:
        titles = whole_block(spans('title', values['title'], front), front)
        if any(found[1] - TITLE_BEFORE <= e <= found[1] for _, e in titles):
            kept['title'] = values['title']
    places = {f: spans(f, values[f], text) for f in ('journal', 'server', 'arxiv') if values[f]}
    anchors = [s for f in ('journal', 'server', 'arxiv') for s in places.get(f, [])]
    for f in ('journal', 'server', 'arxiv'):
        if places.get(f):
            kept[f] = re.sub(r'\s+', '', values[f]) if f in IDENTIFIERS else values[f]
    year = values['year'] if re.fullmatch(r'[0-9]{4}', values['year']) else ''
    if year and anchors:
        kept.update(locator(year, values, text, anchors))
    elif year and found and spans('year', year, front):
        kept['year'] = year
    if values['doi']:
        doi_anchors = anchors + (near(spans('year', year, text), anchors, NEAR) if anchors else [])
        if doi_anchors and near(spans('doi', values['doi'], text), doi_anchors, LOCATOR):
            kept['doi'] = re.sub(r'\s+', '', values['doi'])
    dropped += [f for f in FIELDS if given.get(f) not in (None, '') and f not in kept]
    return kept, dropped


def format_citation(style: str, given: dict, first_pages: str) -> dict:
    if style not in STYLES:
        raise ValueError('Unknown citation style: ' + style)
    given = given if isinstance(given, dict) else {}
    results = [verify(given, text) for text in readings(first_pages)]
    kept, dropped = max(results, key=lambda r: (all(f in r[0] for f in REQUIRED), len(r[0])))
    missing = [field for field in REQUIRED if not kept.get(field)]
    unused = ['arxiv', 'server'] if kept.get('journal') else []
    return {'version': VERSION, 'style': style, 'citation': None if missing else STYLES[style](kept),
            'found': sorted(kept), 'dropped': dropped, 'missing': missing,
            'unused': [f for f in unused if f in kept]}


def read(path: Path) -> str:
    """A regular file only, reached without any link and opened without waiting on a pipe."""
    if os.path.realpath(path) != os.path.abspath(path):
        raise ValueError(f'{path.name} is reached through a link')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(f'{path.name} is not a regular file')
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError(f'{path.name} exceeds 1 MiB')
    return raw.decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--style', required=True, choices=sorted(STYLES))
    parser.add_argument('--fields', type=Path, required=True, help='JSON with the fields as the document prints them')
    parser.add_argument('--text', type=Path, required=True, help="the first pages' text, kept outside the library")
    args = parser.parse_args()
    try:
        report = format_citation(args.style, json.loads(read(args.fields)), read(args.text))
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    except (ValueError, OSError, UnicodeError, RecursionError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
