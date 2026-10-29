# Short addresses, readable titles

An opt-in fixed-ID naming example using existing Core/K-Plex capabilities. This
example requires no allocator or registry; the separate optional MOC-scoped helper
below does not change these fixtures. Existing libraries keep
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

## MOC-scoped synthesis addresses (optional)

For the [living-synthesis profile](../../docs/knowledge-workflow.md#optional-living-synthesis-profile),
a library may agree a sequential human address within each thematic primary MOC.
Illustratively, MOC `001` has syntheses `001-01` and `001-02`; MOC `002` has its own
sequence. Seeds remain unnumbered. The [optional shared helper](../../docs/first-cut-tools.md#optional-living-synthesis-numbering)
implements this convention for an explicitly opted-in bounded collection, without
a separate number registry. Its field representation does not change the fictional
`012a` fixtures above or prescribe their migration.

Keep the technical identity stable and distinguish it from this organizational
address. The earlier example deliberately uses one fixed ID/prefix; a library
where these are inseparable must resolve that constraint before adopting mutable
MOC-scoped addresses. Do not rewrite an existing ID to make the convention fit.
Agree the address's permitted representation under local rules, without imposing
a field, folder layout or host. Mere title, maturity or secondary-map changes
never recode a synthesis. Secondary references link to the same note.

### Deliberate primary-MOC move

A true change of primary theme is an explicit reviewed organizational change,
not maturity progression or routine renumbering. Before review, prepare the new
primary association and next unused destination address, preserving technical
identity. Show the exact affected content, old/new references and history treatment
as one candidate. Keep the previous address reserved and interpretable under the
library's existing history/reference mechanisms; do not recycle it or break old
links. Reconcile source/destination maps and incoming section references through
the permitted writer/rename path. If that cannot preserve identity and references,
stop the move and remain proposal-only.

This differs from replacement or retirement: a move keeps the same explanation
and identity; a successor is a different note and follows
[retirement in place](#retire-in-place-do-not-recycle-addresses). Do not retire or
copy a live note merely to recode it. Continue the next unused sequence rather
than filling gaps, including addresses held by retired notes or previous moves;
incomplete custody/history means availability is unverified, not free.

The shared mechanism prepares allocation before exact human review and rechecks
scope, configuration, identity, bases, evidence and reservations before save.
A collision or changed base invalidates the candidate; it never silently chooses
a different reviewed address. Stable-path moves reserve former addresses on the
same file and include any destination-map companion edit in the reviewed batch.
Unsupported identity/rename/reference conventions remain proposal-only.
The [adoption plan](../../docs/implementation.md#prospective-living-synthesis-adoption)
still requires a separately authorized useful pilot. No concurrent allocation,
atomic multi-file save, native rendering or automatic host rename is certified.

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
