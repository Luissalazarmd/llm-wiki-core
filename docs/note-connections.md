# Deterministic activity and connections

Use `scripts/connections.py` for an explicitly selected Wiki scope. It emits JSON
or Spanish Markdown to stdout; it never saves notes, starts histories or approves
content. Existing custody and nested rules must be read before running it.

```sh
python3 -B scripts/connections.py --root /path/to/library --scope Wiki --format json
python3 -B scripts/connections.py --root /path/to/library --scope Wiki/Ideas --format markdown --sort connections
```

Version 1 includes only explicit `role: note` and legacy `role: concept` files.
No inferred roles or migration. Iterations read the optional existing v1
`iteration_tracking` history: unknown and invalid are not zero. Content drift is
shown separately. No wall-clock window participates in this deterministic result.
Core's reader does not create or extend histories; the library's permitted editing
workflow remains responsible for recording completed rounds.

## Counting contract

Incoming and outgoing counts use distinct neighboring notes. Unique connections
are their set union, so reciprocal links count once. Repeated links, aliases in
link display text, and different section fragments do not multiply neighbors.
This counts explicit connections, not semantic importance, quality or maturity.

Supported syntax is `[[Wiki/Ideas/target|display]]` and inline Markdown links such
as `[display](./target.md#section)`. Wikilinks may omit `.md`. Explicit root-relative
paths and `./` or `../` paths resolved from the source are supported. Resolution is
case-sensitive. Fragments identify the containing note; heading existence is not
validated. Bare names and metadata aliases are not guessed, even when only one
candidate is visible. Percent-encoded paths are reported as unsupported.

Frontmatter, HTML and Obsidian comments, fenced/indented code, inline code,
embeds/images, escaped link openings, same-note links and external URLs do not
count. Sources, maps and other roles are excluded. Targets outside the selected
set are reported as outside-selection-or-unresolved, never claimed globally
missing. Markdown reference-style links, HTML links and complex Markdown link
syntax are outside this v1 grammar and are not measured. Use explicit wikilinks
for the portable counting contract; no automatic rewriting is permitted.

## Reproducibility and coverage

The same bytes, scope and algorithm version produce the same sorted JSON.
Results include input SHA-256 hashes, selected paths, all neighbors and located
exclusions. Scope is always labeled `within_selection`; a partial selection cannot
claim whole-library totals. Unknown/invalid histories remain visible.

Reads are bounded to 2,000 Markdown files, 256 KiB per file and 16 MiB total.
Hidden scopes and symlinks are rejected. Malformed metadata fails the calculation
rather than silently changing membership. A second membership/hash pass rejects
observed drift. This is cooperative detection, not an atomic snapshot, locking,
or protection from a change occurring after the final check.

## Display and refresh

Markdown offers `--sort connections` or `--sort iterations`, with path tie-breaks,
neighbor lists and exclusions. A saved report is a disposable snapshot with an
input fingerprint, not a second knowledge registry. Refresh only on explicit
request, after checking the current inputs, output version and library writer
rules. Do not feed the report back as source evidence. No background task runs.

Native Bases backlink formulas are not certified equivalent to this grammar.
Use the reference output until parity is demonstrated in the actual host. A
report can be embedded in Home outside canonical Raw/Review/Wiki after permitted
review/save. Notes, metadata, existing iteration events and maturity stay intact.

## Verification

`python3 -B -m unittest discover -s tests -p test_connections.py -v` checks the
agreed graph, duplicates/reciprocity, exclusion rules, scope, input drift, bounded
reads, unknown/zero/invalid histories and read-only CLI output. Native rendering
requires a separate observed check. No plugin or provider installation is needed.
