# Acceptance

## Template writer — 2026-11-12

This update passed 332 synthetic tests on Linux with Python 3.14.8 and PyYAML 6.0.3,
run from a clean clone of the branch. Disabling each of the 26 refusal conditions in
`template_write.py` one at a time made the new tests fail. The earlier guard runs and
path variants were not repeated.

Not run for this update: an actual host creating or changing a template with its owner
reviewing the exact text; Obsidian inserting a template written this way, or reading a
custom `templates.json` folder; a filesystem without hard links; a process killed
mid-save; macOS; Python 3.10–3.13. Tests show that a template is a blank source wrapper
that still passes the capture checker once filled, that an existing template is replaced
only under the hash of its current version and after a verified private copy, and that a
packet saves once; they cannot show that the owner saw the template or asked for it.

## Capture writer, retirement and source templates — 2026-11-12

This update passed 306 synthetic tests on Linux with Python 3.14.8 and PyYAML 6.0.3,
run from the working checkout. Disabling each of 54 new capture-writer and retirement
guards one at a time made the new tests fail; two further guards were removed as
redundant with checks they repeated. One capture with a PDF, its retirement and the
refused reuse of its packet were also run by hand in a disposable copy of the starter
library. The earlier guard runs and path variants were not repeated.

Not run for this update: an actual host capturing or retiring with its owner
reviewing the exact wrapper; Obsidian inserting the source templates or reading the
copied `templates.json`; a filesystem without hard links; a process killed mid-save;
macOS; Python 3.10–3.13. Tests show that a capture is created whole or not at all
under injected failures, that attachments are independent verified copies, and that
retirement leaves verified recovery copies and edits no linking note; they cannot
show that the owner saw the wrapper, asked for a retirement or was told which rule it
excepts, nor that an attachment is what its name and first bytes suggest.

## Owner-authored seeds — 2026-11-12

This update passed 274 synthetic tests on Linux with Python 3.14.8 and PyYAML 6.0.3,
run from the working checkout. Disabling each of the 22 new owner-seed guards one at
a time made the new tests fail. One owner seed inside a numbered scope was prepared
and saved by hand in a disposable library; the suite does not cover that
combination. The earlier guard runs and path variants were not repeated.

Not run for this update: an actual host retaining an idea its owner stated, with
the owner reviewing the exact text; macOS; Python 3.10–3.13. Tests show that the
evidence-free creation stays a declared seed outside originals and the proposals
layer, and that leaving that state needs bound evidence; they cannot show that an
idea labelled `origin: owner` was the owner's, or that later evidence supports it.

## Starter library and proposal custody — 2026-11-11

This update passed 261 synthetic tests on Linux with Python 3.14.8 and PyYAML 6.0.3,
run from the working checkout. Disabling each of the 15 new proposal-custody and
layer guards one at a time made the new tests fail. The earlier 30-guard run and the
runs from paths with spaces, accents and a symlinked temp directory were not repeated.

Not run for this update: an actual host parking a specialist's proposal, a
human-reviewed acceptance of a parked proposal, native Obsidian rendering of the
starter `Biblioteca.base`, macOS, or Python 3.10–3.13. Tests show that custody stays
inside the declared proposals layer; they cannot show that parked text is literal
to the original message or that a later Wiki save was really reviewed.

## Adoption readiness checkpoint — 2026-11-03

This update passed 240 synthetic tests on Linux with Python 3.14.8 and PyYAML
6.0.3, from a copy in a path with spaces and accents, with the temp directory itself in
such a path, and with it under a symlink (a simulation of macOS `/tmp` and `/var`, not
a macOS run). Disabling 30 safety guards one at a time made the suite fail 29 times;
the lexical source boundary alone is backed by the identity check, and disabling both
fails. Local documentation
targets and whitespace were checked. These results support a bounded pilot, not
universal deployment or semantic approval.

Not run for this update: clean-machine installation, macOS execution, a new
human-reviewed end-to-end session, current native Obsidian/K-Plex interaction,
cross-host compatibility or cloud-sync acceptance. Earlier native observations
remain historical. No platform CI matrix is provided by this update.

Before claiming a supported Linux/macOS configuration, record the exact revision,
OS/architecture, filesystem and dependency versions; run the suite and disposable
export from a clean setup. Check spaces/Unicode/case-sensitive path behavior,
source preservation, stale-input refusal, no-clobber creation and recovery on
that filesystem. Observe one actual agent-guided correction with exact human
review. Validate optional graphical and sync integrations separately; retain the
single cooperative writer limitation. Add repeatable CI when those environments
are available, without treating it as a substitute for human acceptance.

## Next step: observe adaptive initiative

The [guided loop](knowledge-workflow.md#guided-loop) states the intended behavior; it
has not been observed across hosts. Assess it with a few authorized real tasks: a
simple reference, a purposeful reading and a correction. Look for useful initiative,
adaptation to the request, only consequential questions and exact review before
saving. Record only generalizable findings, keeping library sources and project
context private.

## Reproduce the checks

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`.
Synthetic cases cover bounded read-only discovery, native/legacy projection,
identity/version/locator checks, capture duplicates/connections, proposal binding,
stale/diff refusal, managed/source/instruction protection, no-clobber creation,
proposal custody confined to its declared layer, owner-authored seeds, the copied
starter library and its source templates, whole-or-nothing capture with attachments,
owner-exception retirement and wrapper-only revision, template creation and hash-bound change,
injected failures and recovery preserving later edits. Fixtures preserve originals.

`python3 tests/demo_existing_library.py --output-parent /tmp` independently
maps/reads/proposes without applying. Check JSON/Canvas, local links/headings,
whitespace and every publication candidate, including untracked files.

Separate actual human [review](review-contract.md), source rights/entailment and
useful synthesis from structural tests. Native acceptance observes settled
K-Plex roles and counts, not delays. Use approved disposable launches under host
rules. [Native results](../examples/obsidian/VALIDATION.md) record failures/limits;
mobile, concurrency, managed approval and automatic focal-node delivery remain distinct.

See [deterministic activity and connections](note-connections.md) for the optional,
read-only v1 counter, explicit scope, exclusions and synthetic checks. Counts do
not establish importance, maturity or acceptance.
