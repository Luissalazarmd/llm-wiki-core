#!/usr/bin/env python3
"""Format a citation from bibliographic fields found verbatim in a document's first pages. Writes nothing."""
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

VERSION = 2
LIMIT = 1024 * 1024
CAPS = {'title': 512, 'journal': 256, 'server': 64, 'year': 4, 'volume': 32, 'issue': 32, 'pages': 32,
        'doi': 256, 'arxiv': 64, 'family': 128, 'given': 128}
MAX_AUTHORS = 100
FIELDS = ('title', 'journal', 'server', 'year', 'volume', 'issue', 'pages', 'doi', 'arxiv')
REQUIRED = ('authors', 'title', 'year')
NEAR = 120          # characters: year beside journal or preprint id; volume, issue and pages beside year
BYLINE = 200        # characters between consecutive authors
TITLE_BEFORE = 1500  # characters between the title and the first author
FRONT = 5000        # characters searched for title and authors when no abstract or introduction heading is found
DASHES = str.maketrans('‐‑‒–—−', '------')
LINE_BREAK_HYPHEN = re.compile(r'(?<=\w)-[^\S\n]*\n[^\S\n]*(?=\w)')
REFERENCES = re.compile(r'^[^\S\n]*(?:\d+[.)]?[^\S\n]+)?(?:references|bibliography|works cited|referencias'
                        r'|bibliograf[ií]a|literature cited)[^\S\n]*:?[^\S\n]*$', re.I | re.M)
OPENING = re.compile(r'^[^\S\n]*(?:\d+[.)]?[^\S\n]+)?(?:abstract|summary|introduction|background|keywords'
                     r'|resumen|introducci[oó]n|antecedentes|palabras clave)\b', re.I | re.M)
CONNECTOR = re.compile(r'(?:[\d*†‡§¶#⁎∗.]+|[a-z]|and|&|y|e|und|et)')
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
    text = text[:cut.start()] if cut else text
    return [text, LINE_BREAK_HYPHEN.sub('', text)]


def spans(field: str, value: str, text: str) -> list[tuple[int, int]]:
    if field in IDENTIFIERS:
        compact = re.sub(r'\s+', '', value).translate(DASHES)
        if not IDENTIFIERS[field].fullmatch(compact):
            return []
        pattern = r'\s*'.join(map(re.escape, compact))
        if field == 'doi':
            pattern, end, flags = pattern, r'(?![^\s.,;)\]]|[.,;)\]]\S)', re.I
        else:
            versioned = re.search(r'v[0-9]+$', compact)
            pattern, end, flags = pattern + ('' if versioned else r'(?:v[1-9][0-9]*)?'), r'(?![\w/-]|\.[\w/])', 0
    else:
        pattern, end, flags = literal(value), r'(?!\w)', 0
    return [m.span() for m in re.finditer(rf'(?<!\w){pattern}{end}', text, flags)]


def near(found: list[tuple[int, int]], anchors: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [s for s in found if any(abs(s[0] - a[0]) <= NEAR or abs(s[1] - a[1]) <= NEAR for a in anchors)]


def unspaced(text: str) -> bool:
    """Written in a script without spaces between words (Chinese, Japanese)."""
    return any(unicodedata.name(ch, '').startswith(('CJK', 'HIRAGANA', 'KATAKANA')) for ch in text)


def gap_is_byline(gap: str) -> bool:
    """Between two authors only separators, affiliation marks and a connector: never another name."""
    return all(CONNECTOR.fullmatch(token) for token in re.split(r'[\s,;]+', gap) if token)


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
        if ok and gap_is_byline(text[end:line_end if line_end >= 0 else len(text)]):
            names = [f"{family} {''.join(p[0].upper() for p in re.findall(r'[^\W\d_]+', given))}".rstrip()
                     for family, given, _ in people]
            return names, first.start(), end
    return None


def vancouver(fields: dict) -> str:
    """ICMJE/Vancouver: up to six authors, otherwise the first six and et al."""
    authors = fields['authors']
    parts = [', '.join(authors if len(authors) <= 6 else authors[:6] + ['et al.']), fields['title']]
    if fields.get('journal'):
        volume = fields.get('volume', '')
        volume += f"({fields['issue']})" if volume and fields.get('issue') else ''  # no issue without its volume
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
        kept['authors'], start, _ = found
    elif given.get('authors'):
        dropped.append('authors')
    values = {f: clean(given.get(f), f) for f in FIELDS}
    title = values['title']
    if title and (len(title) >= 8 and ' ' in title or len(title) >= 4 and unspaced(title)) and found:
        if any(found[1] - TITLE_BEFORE <= e <= found[1] for _, e in spans('title', title, front)):
            kept['title'] = title
    places = {f: spans(f, values[f], text) for f in ('journal', 'server', 'arxiv', 'doi') if values[f]}
    anchors = [s for f in ('journal', 'server', 'arxiv') for s in places.get(f, [])]
    for f in ('journal', 'server', 'arxiv', 'doi'):
        if places.get(f):
            kept[f] = re.sub(r'\s+', '', values[f]) if f in IDENTIFIERS else values[f]
    year = values['year'] if re.fullmatch(r'[0-9]{4}', values['year']) else ''
    years = near(spans('year', year, text), anchors) if year and anchors else (
        spans('year', year, front) if year else [])
    if years:
        kept['year'] = year
        for f in ('volume', 'issue', 'pages'):
            if values[f] and near(spans(f, values[f], text), years):
                kept[f] = values[f]
    dropped += [f for f in FIELDS if given.get(f) not in (None, '') and f not in kept]
    return kept, dropped


def format_citation(style: str, given: dict, first_pages: str) -> dict:
    if style not in STYLES:
        raise ValueError('Unknown citation style: ' + style)
    given = given if isinstance(given, dict) else {}
    kept, dropped = max((verify(given, text) for text in readings(first_pages)), key=lambda r: len(r[0]))
    missing = [field for field in REQUIRED if not kept.get(field)]
    unused = ['arxiv', 'server'] if kept.get('journal') else []
    return {'version': VERSION, 'style': style, 'citation': None if missing else STYLES[style](kept),
            'verified': sorted(kept), 'dropped': dropped, 'missing': missing,
            'unused': [f for f in unused if f in kept]}


def read(path: Path) -> str:
    """A regular file only, opened without following a link or waiting on a pipe."""
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
