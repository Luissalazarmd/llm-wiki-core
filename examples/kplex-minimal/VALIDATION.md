# Native navigation observation

Observed 2026-10-15 America/Bogota (2026-10-16 UTC), using the official K-Plex
0.1.3 release in an isolated Obsidian profile and synthetic vault under `/tmp`.
Obsidian ran from the installed app package; its exact app version was not
recorded. Plugin source inspected during design and released binary tested are
distinct evidence. No personal library or plugin settings were changed.

## Passed

- Explanation centered: map is `parent`, original source is `left`, challenge
  is `right` in K-Plex's rendered node elements.
- Click source, then explanation: inverse evidence navigation works.
- Click challenge, then explanation: inverse tension navigation works.
- Click map: both notes are children, derived from their single `up` fields.
  Clicking the explanation returns to its original neighborhood.
- Obsidian opens both source heading links at their exact headings: Resultados
  at zero-based line 9 and Limitaciones at line 14. This used Obsidian's link
  opening API, not K-Plex's connection-details interaction.
- All four Raw/Wiki files matched repository bytes after the journey.
- The disposable window was closed and the launch process exited with code 0.

The agent inspected native screenshots and rendered DOM roles. Navigation used
click events on the actual K-Plex nodes, not a replacement graph implementation.
The sandbox remained enabled; the explicitly approved native run occurred
outside the command sandbox with a bounded lifetime and local inspection port.

## Finding and correction

Copying the README into the vault made its ordinary documentation links appear
as additional inferred parent relationships. Removing only that disposable copy
left exactly the intended map/source/challenge neighborhood. Preparation guidance
now copies Raw/Wiki only. This does not disable all inferred relationships or
establish how documentation should be filtered in an existing personal vault.

## Follow-up native session

The profile was reopened in a separately authorized bounded session. Original
relations survived restart. An initial probe ran before workspace restoration
completed and failed; waiting resolved that probe error without an app restart.
A renderer `require('obsidian')` version query was unavailable. These probe errors
do not establish a plugin crash; the exact app version remains unrecorded.

| Check | Observed result |
| --- | --- |
| Connection details | Evidence appeared as a defined Friend relation with its exact inline declaration and Markdown location. |
| Go to source | Opened Explicacion at zero-based line 16: the relation declaration, not the cited source's Results heading. |
| Related | A temporary Contexto note appeared left and exposed a return connection to Explicacion. |
| BuildsOn / Previous | A temporary Semilla appeared left; from Semilla, Explicacion appeared right. Both directions worked. |
| Maturity lens | Matching synthesis changed the focal border from transparent/1px to orange/4px without changing note maturity. |
| Context handoff | Observaciones could be central while the active editor still pointed to Explicacion. The native sync-tab-from-plex command aligned the editor with Observaciones. |

### Multiple relations constrain the design

Adding Related to an existing Contrasts pair preserved both declarations in
Connection details, but placed the pair in the Friend region because defined
roles conflicted. The challenge moved from right to left. Position alone cannot
represent every semantic role. The next design should avoid redundant Related
declarations when a more specific relation suffices, preserve genuinely distinct
arguments, and make their full meanings available in details and prose.

After combined note/settings edits, a transient view showed body links as inferred
Children. An explicit index rebuild produced the defined relations checked above.
Automatic incremental convergence was not independently established. Future GUI
acceptance must check observed readiness and relation details, not fixed delays.

The local debugging read is not a shipped agent integration. Center, highlighted
selection and active editor must remain distinct. The test established a
center/editor mismatch and explicit synchronization, not automatic agent delivery.

All temporary mutations were limited to the disposable vault. Extra Semilla and
Contexto notes, relations and lens were removed; all four original notes were
restored byte-for-byte. The window closed and the process exited with code 0.

## Not run / remaining limits

- Automatic selected-node delivery and a distinct keyboard-highlighted selection.
- Incremental convergence after combined note/settings edits (see the narrower
  successful note-only update below).
- Other plugin versions, mobile, theme variations and accessibility interaction.
- Human review/save workflow or real source capture; this is synthetic navigation.

Evidence captured privately at `/tmp/core-kplex-native-20261015/`: `final.png`,
`journey.png`, `finish.js.result.json` and the bounded probe scripts. These are
local observations, not a portable automated GUI suite. Follow-up records include
`remaining-start.js.result.json`, `modal.js.result.json`, `goto.js.result.json`,
`multicheck.js.result.json`, `development.js.result.json`, `lens.js.result.json`,
`context.js.result.json` and corresponding screenshots. The complete Python
suite previously passed 141 tests; it does not certify this native behavior.

Decision supported: proceed with the three-role and body-field design for this
bounded case. Do not claim that all six implementation issues are resolved.

## Implemented v2 reader and full note example

The repository reader now accepts the three roles and native fields. Legacy
roles/maturity normalize only in output; legacy hash-bound relations retain their
validation. This is a local implementation, not a migration or an issue-closing
receipt. Source identity in this minimal fixture is now an explicit Reference
body field; the earlier native heading line numbers describe the earlier cut.

The updated full example's Raw/Wiki notes were copied to the disposable vault.
With K-Plex 0.1.3, the real Sintesis note showed Sombras above, Informe-A left,
Pregunta left and Explicacion right. Ordinary links initially produced unwanted
inferred parents. Setting `inferAllLinksAsFriends` to true kept general reading
links lateral while preserving explicit up/Evidence/Contrasts/BuildsOn roles.
Both supplied settings fragments now select that behavior. The `sources` field
is also mapped to the friend region; it has structural reader coverage, but its
dedicated native field was not separately exercised in this session.

For incremental acceptance, ordinary links to reports A/B were temporarily
removed from the disposable note so they could not mask the Evidence change.
The test required the correct focal note, the new source on the left, absence
of the former source, and the defined tension back on the right. It passed on
baseline, A-to-B change and B-to-A restoration in approximately 453/467/462 ms
of polling respectively, without rebuilding the index. These are observations
on this small fixture, not latency guarantees. Full original bytes were restored.

An earlier attempt had the wrong focal note and is excluded from acceptance;
the native sync-plex-from-tab command established the correct context. A looser
predicate saw links before their semantic roles had settled and was replaced
by the stricter predicate above. This distinction must remain in future checks.

Evidence: `v2-baseline.js.result.json`, `v2-incremental.js.result.json`,
`v2-precondition-failure.json` and their screenshots under the private test path.
All full-example Raw/Wiki bytes matched afterward; the window closed and exited
with code 0. No personal library was read or modified.

Verification: complete synthetic suite 150/150 passed; the focused native-reader
suite 8/8 passed after the final anchor/frontmatter-locator checks. JSON parsing,
relative documentation links and whitespace validation passed. Initial old-schema
expectation failures and a moved Canvas anchor were corrected; they are not
outstanding failures. Updated Home/Base/Canvas rendering, real capture/review and
automatic selected-node delivery remain outside the observed native result.

## Local review boundaries

This accumulated local work is larger than one review slice. No commit, PR or
publication is implied. Before publication, separate these work units with their
tests and relevant documentation, using hunks where they share the reader:

1. Three-role vocabulary, legacy normalization and maturity semantics.
2. Native relation parsing, scoped resolution, provenance and diagnostic tests.
3. The minimal synthetic fixture and its runtime/structural tests.
4. Full Obsidian fixtures, Base/settings, generated view and example tests.
5. Dated native observations and the remaining integration boundaries.

Rollback of runtime behavior requires reverting the ontology/reader changes with
their associated tests and contract updates, then the adapted example/view unit.
The minimal fixture alone remains removable independently. These are repository
changes only; no personal-library rollback or managed apply receipt is involved.
