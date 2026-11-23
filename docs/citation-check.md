# Citation check

`scripts/citation_check.py` reads explicitly selected notes and prints a JSON report.
It writes nothing, judges no claim and approves nothing: a citation can be exact and
the conclusion wrong. Read the library rules first; the selection is the authorization.

```sh
python3 -B scripts/citation_check.py --root /path/to/library --scope Wiki --sources Raw > /private/report.json
python3 -B scripts/citation_check.py --root /path/to/library --scope Wiki --sources Raw --since /private/report.json
```

`--scope` selects the notes to check and `--sources` the further files they may cite.
Nothing else is opened, so a target outside both is reported as outside the selection or
missing, never as globally absent. Keep reports outside the library.

## What it reports

- **Links**: explicit wikilinks, embeds and inline Markdown links whose file, heading or
  block does not resolve to exactly one place. Wikilinks resolve from the library root and
  Markdown destinations beside the note; a destination that exists only from the root, or
  in both places, is reported. `#Parent#Child` follows heading levels. Bare names are not
  guessed, external addresses are not opened, and the start of a link that could not be
  read is reported as not checked.
- **Quotations**: text between «» or “” immediately followed by a link, or by a number
  listed under References. The exact characters, apart from line wrapping and final
  punctuation, must be present anywhere in the cited text file between word boundaries;
  a neighboring sign, decimal, unit or word joined to a number is not accepted. Presence
  is not support: the words may stand in another section, in code or beside a denial.
  Anything else is reported as not found, or as not checked when only marks differ, when
  marks are nested or unclosed, or when the source is not a text format. A quotation
  with no citation at once after it is not examined.
- **Numbered references**: in a note with a References section, numbers without an
  entry, entries never called and repeated entries. Lists and ranges such as `[1,3]` and
  `[2–4]` are expanded. If the endpoints differ by more than 100, only the endpoints are
  checked. An entry ends at the next entry or heading, so a later link is never lent to
  it.
- **Declared validity**: `stale_after` dates already past and `superseded_by` targets,
  described in [declared validity](knowledge-workflow.md#declared-validity).
- **Changed sources**: with `--since`, cited files whose bytes differ from an earlier
  report over the same library folder and selection; a moved or replaced library is
  refused. A changed file is a reason to read it again, not a finding against the note.
  The earlier report is trusted as the owner kept it.

In the checked note, frontmatter, fenced code, inline code and comments are skipped;
indented lines are read. Markdown reference-style links and HTML links are not read.
Limits: 2,000 notes, 5,000 selected files, 4 MiB per file and 64 MiB in total. Hidden
folders are never entered, symbolic links are refused and an unreadable folder stops the
run. A change in the list of selected files, or in the bytes of a note or cited file,
seen before the report is printed discards it. This is a cooperative check, not a lock.

Use findings while preparing a review: correct the note through
[review and save](review-contract.md), never by rewriting the original.
