# Short addresses, readable titles

An opt-in naming example using existing Core/K-Plex capabilities. No new runtime,
number allocator, metadata field or registry is required. Existing libraries keep
their names and IDs. These four notes are fictional, not scientific evidence.

| Surface | Value |
| --- | --- |
| File explorer | `012a - Considerar el horario.md` |
| Stable identity | Existing `id: "012a"` property, quoted to preserve digits. |
| K-Plex label | Existing `title: El horario puede explicar una diferencia`. |
| Body | The argument and a justified explicit connection. |

The filename repeats the same address for human orientation; it is not a second
identity. The quoted metadata ID is authoritative; the visible prefix matches it.
Its short description need not repeat the full title. The body does not
repeat the title as another heading. K-Plex's existing `nameFields` setting must
prefer `title`; configure BuildsOn as Previous, as in the
[existing settings reference](../obsidian/kplex.example.json). Copy only Wiki,
retaining the `examples/numbered-notes/` prefix, to a disposable test vault.

## Authoring rule

The Librarian proposes one unused address when a new note is worth retaining.
Keep it fixed when title, maturity or maps change. Reuse an existing note before
allocating another. Numbering is an entry route; explicit links explain relations.
Do not derive topic, maturity, agreement or K-Plex direction from an address.
The reader already rejects duplicate IDs in its bounded strict catalog; this is
not a concurrent allocation service or a whole-library uniqueness guarantee.

### Retire in place; do not recycle addresses

Within a verified address sequence, propose the next unused continuation after
the existing ones; do not fill gaps. Retired notes remain in their original files
with the same quoted ID. The file itself reserves the address: no separate
counter, retirement registry or routine Git-history scan is needed.

This convention applies to derived notes, never to rewriting source originals.
Retirement or consolidation is a reviewed content change through the existing
writer. Prefix the readable title with `Retirada —` and add a short reason at the
top. If another note takes over the explanation, add an ordinary explicit link
to it. Keep the old text and referenced headings below the notice so incoming
links still resolve and previous arguments remain inspectable. Without a
successor, state that the explanation was withdrawn; do not invent an empty
replacement. Do not change role, maturity or review labels merely to retire it.

For example: “Retirada: esta explicación se integró en [the existing successor].
El contenido anterior se conserva debajo para interpretar referencias previas.”
The actual successor must be a resolving wikilink, never a placeholder.

The Librarian checks the notice before reusing the old argument. Retired files
remain discoverable; this convention adds no automatic redirect, hidden state or
special graph node. The reader rejects a second file with the same ID, including
one held by a retired note. It cannot reconstruct reservations from files deleted
outside this convention. If prior deletion or incomplete custody is known,
reconcile with available authorized history before claiming an address is unused.

Use short continuations while useful. Maps and cross-links keep other reading
routes available as a thread grows. No mandatory depth, category tree, numeric
folder migration or automatic renumbering is introduced. Renaming a linked file
requires the library's permitted rename workflow and link verification, not a
plain filesystem move. Existing-mode discovery continues to use temporary path
locators; stable-ID projection requires the known strict schema.

Prefer changing `title` alone when the short filename description still fits.
If a filename rename is necessary, verify automatic link updates and full
vault-relative link formatting before using Obsidian's rename operation.
The tested native settings are `alwaysUpdateLinks: true` and
`newLinkFormat: absolute`. The default shortest-link setting can produce basename
links that Core deliberately refuses. Change settings only with the library's
permission; afterward recheck links and identity. Do not add a basename resolver
or scan beyond the authorized scope to compensate.

## Checks and rollback

Run `python3 -m unittest discover -s tests -p test_numbered_notes.py -v`.
Observed: three focused tests passed; the complete suite passed 153 tests with
zero failures, errors or skips. Relative documentation links and whitespace checks passed.
The fixture must retain quoted, unique IDs and resolve all links. Native checks
must separately verify explorer order, title display and link-preserving rename.
Removing this directory and its test removes the example without changing Core.
The retirement increment changes only this rule, its discovery link in the
Librarian profile and the focused test; it introduces no new runtime boundary.
Retirement was checked through the actual reader on synthetic files; no new
K-Plex behavior or automatic redirect is claimed.

## Observed native result

Tested on 2026-10-15 America/Bogota (2026-10-16 UTC), with official K-Plex 0.1.3
in the existing disposable Obsidian profile. No personal settings were changed.

- Alphabetical explorer order: 012, 012a, 012a1, 012b. Temporary 012a2 and 012a10
  also sorted in numeric order and were removed after the test.
- K-Plex used clean `title` labels. Existing wrap/label-width settings avoided
  truncated labels; no custom renderer or CSS was needed.
- A native filename/title change retained ID 012a and updated the incoming link
  and focal graph label. With shortest links, Obsidian shortened that reference;
  the absolute-path test retained the explicit path Core needs.
- The exact renamed file and updated incoming-link bytes from Obsidian were
  accepted by the strict reader: four IDs, three development edges.
- Original note bytes and both temporary rename preferences were restored.
  The window closed and its launch process exited with code 0.

The first navigation probe did not activate the restored K-Plex tab; explicitly
opening it and syncing from the note established the test context. Native
acceptance checked the actual center and settled development directions.
Private evidence: `/tmp/core-kplex-native-20261015/numbered-start.js.result.json`,
`numbered-check.js.result.json`, `numbered-absolute.js.result.json` and
`numbered-view.png`. These observations are not a portable GUI test suite.

Not tested: concurrent address allocation, other plugin versions, mobile or
automated delivery of selected-note context. None is added by this convention.
