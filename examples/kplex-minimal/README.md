# Navigate original notes with three roles

This synthetic example tests source, note and map directly in K-Plex.
The strict reader now accepts it with `--root examples/kplex-minimal --link-prefix examples/kplex-minimal`.
This implements the first schema/navigation slice for issues #1 and #4; the current [handoff](../../docs/simplification-handoff.md) records the subsequent
capture/review candidate. No personal migration is implied.

## Read the example

Start with [the explanation](Wiki/Explicacion.md), then read its
[source](Raw/Observaciones.md), [challenge](Wiki/Comparabilidad.md) and
[map](Wiki/Sombras.md). All observations are invented. No private material,
third-party code or plugin binaries are included.

| Responsibility | Representation in this example |
| --- | --- |
| Raw | One preserved original with identity, version and claim locators. |
| Review | This candidate and the exact repository diff; no claimed human acceptance. |
| Wiki | Two illustrative derived notes and one authored reading map. |
| Maturity | One synthesis; one unknown; no maturity on source or map. |

The Librarian maintains the declarations and their explanations as part of a
reviewed content change. The human reads, challenges, synthesizes and approves.
Follow the existing [review contract](../../docs/review-contract.md) for real
library writes. This fixture does not admit a real capture; actual retention follows
[current admission](../../docs/raw-admission.md) and the library's stronger rules.

## Navigation candidate

| Declaration, stored once | Intended K-Plex behavior |
| --- | --- |
| `up` on each note | Map above the note; inverse children when the map is central. |
| `Evidence::` next to an argument | Source in the friend region; return navigation from the source. |
| `Contrasts::` next to the tension | Challenge in the challenger region; return navigation from the challenge. |

Reasons remain in prose. A friend position alone does not certify scientific
support: inspect the relationship label and original section. The baseline avoids
giving the same pair several roles. Follow-up testing found that Related/Contrasts
conflicts retain both declarations but use the friend region; see validation.
No reciprocal declarations or generated focal views are required by this design.
Temporary follow-up cases also exercised related links and idea development.
The settings treat ordinary links as friends, reserving hierarchy for explicit
organization. Both generic links and Evidence may be lateral: inspect the field
and argument to distinguish useful reading from declared support.

The [settings fragment](kplex.example.json) uses configurable ontology fields.
It is not a complete settings file and must not replace a personal configuration.
For a disposable vault, copy only `Raw/` and `Wiki/`, preserving the
`examples/kplex-minimal/` prefix so every vault-relative wikilink retains its
target. Keep this README and validation documents outside that vault: their
ordinary links otherwise introduce inferred parents. Apply the settings fragment
only to the disposable plugin configuration, never over personal settings.

Upstream basis: K-Plex main commit
[`867ef55`](https://github.com/zsviczian/kplex/tree/867ef55a280c730a6b0374338433fea3ab06b9de)
(manifest 0.1.3, minimum Obsidian 1.13). Its
[parser](https://github.com/zsviczian/kplex/blob/867ef55a280c730a6b0374338433fea3ab06b9de/src/core/parser/metadata.ts)
recognizes line-style inline fields; its
[documentation](https://github.com/zsviczian/kplex/blob/867ef55a280c730a6b0374338433fea3ab06b9de/README.md)
describes configurable ontology and connection inspection. Reading upstream code
does not establish compatibility with an installed plugin version.

## Acceptance

Automated structural checks:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_kplex_minimal.py -v

These check fixture roles, links, section locators and declared relationship
coverage. They do not execute K-Plex or duplicate its parser/layout engine.

Observed on 2026-10-15: focused suite 3/3 passed; complete suite 141/141 passed
with no failures, errors or skips (`python3 -m unittest discover -s tests`).
Relative documentation links, JSON parsing and `git diff --check` passed.
Publication scope reviewed: original synthetic content and public upstream
references only; no personal library data or third-party implementation copied.

Native navigation was exercised with K-Plex 0.1.3 on 2026-10-15 (Bogota);
see [observed results and limits](VALIDATION.md). The acceptance route is:

1. Center the explanation: map above, evidence left, challenge right.
2. Follow the source: recover the explanation through its inverse connection.
3. Follow the challenge: recover the explanation and inspect the tension reason.
4. Center the map: both notes appear as children without a hand-maintained list.
5. Open the evidence at Results and Limitations; verify exact section navigation.
6. Inspect connection details: each relation originates in these original notes.

Connection-details inspection and Go to source passed in the follow-up native
session, separately from the earlier heading-link test. Automatic transfer of
the selected K-Plex node to the agent is outside this candidate.

Rollback boundary: remove this directory, its focused test and the discovery
link in the existing workbench README. The reader has separate v2 tests; removing this demonstration does not roll back
the v2 runtime. No personal library migration depends on this example. No existing source files or live plugin settings have changed.
