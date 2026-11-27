#!/usr/bin/env python3
"""Format a citation from bibliographic fields found verbatim in a document's first pages. Writes nothing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata

sys.dont_write_bytecode = True

VERSION = 1
LIMIT = 1024 * 1024
FIELDS = ('title', 'journal', 'server', 'year', 'volume', 'issue', 'pages', 'doi', 'arxiv')
REQUIRED = ('authors', 'title', 'year')
DASHES = str.maketrans('‐‑‒–—−', '------')
LINE_BREAK_HYPHEN = re.compile(r'(?<=\w)-[^\S\n]*\n[^\S\n]*(?=\w)')
IDENTIFIERS = {
    'doi': re.compile(r'10\.[0-9]{4,9}/\S+'),
    'arxiv': re.compile(r'(?:[0-9]{4}\.[0-9]{4,5}|[a-zA-Z][\w.-]*/[0-9]{7})(?:v[1-9][0-9]*)?'),
}


def one_line(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def clean(value) -> str:
    if not isinstance(value, str):
        return ''
    return one_line(''.join(' ' if unicodedata.category(c)[0] == 'C' else c for c in value))


def dashes(text: str) -> str:
    return re.sub(r' ?- ?', '-', one_line(text.translate(DASHES)))


def literal(value: str) -> str:
    return r'\s+'.join(map(re.escape, value.split()))


def readings(text: str) -> tuple[str, str]:
    """The text as printed, and with end-of-line hyphens joined: either may hold the field."""
    text = ''.join(c for c in text.replace('\r\n', '\n')
                   if c == '\n' or unicodedata.category(c)[0] != 'C').translate(DASHES)
    return dashes(text), dashes(LINE_BREAK_HYPHEN.sub('', text))


def found(field: str, value: str, texts: tuple[str, str]) -> bool:
    end = r'(?!\w)'
    if field in IDENTIFIERS:
        compact = re.sub(r'\s+', '', value)
        if not IDENTIFIERS[field].fullmatch(compact):
            return False
        pattern = r'\s*'.join(map(re.escape, compact.translate(DASHES)))
        end = r'(?![\w/-]|\.[\w/])'
    else:
        pattern = literal(dashes(value))
    return any(re.search(rf'(?<!\w){pattern}{end}', text) for text in texts)


def verified_authors(authors, text: str) -> list[str]:
    """Every author, in order, as printed; an affiliation mark may follow the family name (Lee1,2,*)."""
    if not isinstance(authors, list) or not authors:
        return []
    names, position = [], 0
    for author in authors:
        if not isinstance(author, dict):
            return []
        family, given = clean(author.get('family')), clean(author.get('given'))
        if not family:
            return []
        pattern = literal(dashes(family))
        if given:
            first = literal(dashes(given))
            pattern = rf'(?:{first}\s+{pattern}|{pattern}(?:\s*,\s*|\s+){first})'
        match = re.compile(rf'(?<!\w){pattern}(?![^\W\d_])').search(text, position)
        if match is None:
            return []
        position = match.end()
        initials = ''.join(part[0].upper() for part in re.findall(r'[^\W\d_]+', given))
        names.append(f'{family} {initials}'.rstrip())
    return names


def vancouver(fields: dict) -> str:
    """ICMJE/Vancouver: up to six authors, otherwise the first three and et al."""
    authors = fields['authors']
    parts = [', '.join(authors if len(authors) <= 6 else authors[:3] + ['et al.']), fields['title']]
    if fields.get('arxiv') or fields.get('server'):
        origin = f"arXiv:{fields['arxiv']}" if fields.get('arxiv') else fields['server']
        parts += [f'{origin} [Preprint]', fields['year']]
    else:
        volume = fields.get('volume', '')
        volume += f"({fields['issue']})" if volume and fields.get('issue') else ''  # no issue without its volume
        date = fields['year'] + (f';{volume}' if volume else '') + (f":{fields['pages']}" if fields.get('pages') else '')
        parts += [fields.get('journal'), date]
    citation = ' '.join(p if p.endswith(('.', '?', '!')) else p + '.' for p in parts if p)
    return citation + (f" doi: {fields['doi']}" if fields.get('doi') else '')


STYLES = {'vancouver': vancouver}


def format_citation(style: str, given: dict, first_pages: str) -> dict:
    if style not in STYLES:
        raise ValueError('Unknown citation style: ' + style)
    given = given if isinstance(given, dict) else {}
    texts = readings(first_pages)
    authors = verified_authors(given.get('authors'), texts[0]) or verified_authors(given.get('authors'), texts[1])
    kept, dropped = {'authors': authors}, ['authors'] if given.get('authors') and not authors else []
    for field in FIELDS:
        value = clean(given.get(field))
        if value and (field != 'year' or re.fullmatch(r'[0-9]{4}', value)) and found(field, value, texts):
            kept[field] = re.sub(r'\s+', '', value) if field in IDENTIFIERS else value
        elif given.get(field):
            dropped.append(field)
    missing = [field for field in REQUIRED if not kept.get(field)]
    return {'version': VERSION, 'style': style, 'citation': None if missing else STYLES[style](kept),
            'verified': sorted(k for k, v in kept.items() if v), 'dropped': dropped, 'missing': missing}


def read(path: Path) -> str:
    with path.open('rb') as stream:
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
