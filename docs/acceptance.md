# Acceptance

## Citation check and declared validity — 2026-11-23

The read-only `citation_check.py` and the optional `stale_after` and `superseded_by`
fields have synthetic tests for links, headings, blocks, altered and intact quotations,
numbered references, declared validity, changed sources, refused selections and
unchanged inputs, run on Linux with Python 3 and PyYAML. Independent read-only audits
found false clean results and unbounded reads in earlier versions; most of their cases
are now tests. It also ran once, read-only, over one small private library of 15 notes;
it finished and its findings have not been reviewed.

Not run: large selections, macOS, Python 3.10–3.13, Obsidian, and any
observation of the two fields in use. They change no validation, writer or status. The
tool finds words and links, not whether a claim follows from its source.

## Current evidence and unchecked citations — 2026-11-23

This text-only update passed 468 synthetic tests on Linux with Python 3 and PyYAML, run
from the branch checkout. The two new tests check selected wording in the evidence and
citation rules, one occurrence of the current-evidence heading in the workflow document,
and links to that heading from the librarian profile, read-connect and review-save. They
do not detect copies of the rules elsewhere or test whether an agent follows them.

One fictional library was also read in three fresh sessions of one model with the same
question and an expected answer fixed beforehand. The decisive record lay outside the
supplied excerpt, the synthesis was outdated, two boards disagreed, a later summary
repeated the older one and a later minute only proposed a change. The three answers
recovered the record, kept the negation and the block in force, separated the proposal
and the repetition from a change, and cited the originals. The library was unchanged.

Not run: the same question without the new text; without a baseline run, the trial
cannot establish whether the new text improved the answers; other models, hosts or real libraries; saving a note with an
unchecked citation; Obsidian opening a citation link or a collapsed embed.

## Ingesta follow-up and public checkout — 2026-11-17

All 466 synthetic tests passed at `aeb907f` on Linux x86_64 with Python 3.14.8
and PyYAML 6.0.3. The November 15 checkpoint below records the initial delivery.
Subsequent fixes through `4565958` preserve owner edits when appending history,
escape `<` in progress and notes, recognize edited Ingesta items as ineligible
evidence and reject batch packets that exceed the reader's size limit. Capture
review shows each attachment's name and size. SHA-256 stays in the packet and
recovery record. The limit is 512 MiB per attachment.

The queue reports titles and sorts by creation date, then path. The starter Base
now uses the declared date for “Pendientes”. Regression tests cover the CLI order,
the Base sort settings, source presence within the declared capture layer, and a
reopen refused at save when another item for that source has since opened. The
attachment tests check the configured ceiling and exercise both sides of a small
test limit.

The [Ingesta skill](../skills/ingesta/SKILL.md) commands also ran in a disposable
starter library. A pending item was closed, found with `ingest-queue --all`, and
reopened in `reading` using its current hash. The existing-library demo passed with
its input library unchanged. Native Obsidian rendering, real owner sessions,
other platforms and full-size attachments remain unverified in this run.

## Ingesta: reading queue, ingest custody and batch capture — 2026-11-15

This update passed 458 synthetic tests on Linux with Python 3.14.8 and PyYAML 6.0.3,
run from the working checkout. Disabling each of the 60 refusal conditions in the new
ingest and batch-capture functions one at a time, each compound condition as a whole,
made the new tests fail; the shared publication path keeps its earlier guards and was
not run again that way. One batch of two
captures, an Ingesta item, its status records with an owner edit in between, an owner
seed and the closing were also run by hand in a disposable copy of the starter library.
The earlier guard runs and path variants were not repeated.

Not run for this update: an actual host running Ingesta with its owner, by default or
in the background; a first analysis of a real long document, or any check that a
coverage statement matches what was read; a reading session with the owner stating
notes; Obsidian rendering the "Pendientes" view or rewriting an item's properties; a
sub-agent returning an analysis; a filesystem without hard links; a process killed
mid-save; macOS; Python 3.10–3.13. Tests show that an item is created only in the
declared proposals layer, only with its own opt-in, only in its exact pending shape and
about one captured source; that a status record changes the status, the progress and
one history line and no other byte; that an item is refused as evidence; and that a
batch of captures is created whole or not at all under injected failures and saves
once. They cannot show that an analysis is accurate or honest about its coverage, that
the owner said what a status record states, that the owner read anything, or that a
note labelled `origin: owner` holds the owner's words.

## View writer and vendored Obsidian skills — 2026-11-14

This update passed 381 synthetic tests on Linux with Python 3.14.8 and PyYAML 6.0.3,
run from a clean clone of the branch. Disabling each of the 55 refusal conditions in
`view_write.py` and in the `layers.views` setting one at a time made the new tests fail.
The earlier guard runs were not repeated.

Not run for this update: an actual host preparing a canvas with its owner reviewing the
exact content; Obsidian opening a canvas, Base or `role: view` page written this way; a
host loading the vendored skills, their triggering beside Core's four actions, or the
Hermes steps in the [adapter](../adapters/obsidian/README.md); the `obsidian` CLI and
Defuddle; a filesystem without hard links; a process killed mid-save; macOS; Python
3.10–3.13. Tests show that a view lands only in the library root or a declared views
folder, that an existing view is replaced only under the hash of its current version and
after a verified private copy, that a packet saves once, and that the vendored bytes
match the recorded upstream hashes. They cannot show that the owner saw the view, that
card or dashboard prose holds no claim, that a Base renders, or how a host behaves.

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
starter library and its source templates, whole-or-nothing capture with attachments, alone or as one batch,
ingest custody confined to its layer, opt-in and shape, status records that change nothing else,
owner-exception retirement and wrapper-only revision, template creation and hash-bound change,
injected failures and recovery preserving later edits, and the [portable entry](hosts.md):
the Core declaration, the private lookup order, `write` against `proposal_only`, the host
bridges and a library in Git with two clones. Fixtures preserve originals. Whether a given
host loads the rules, a bridge or a skill is observed per host, not proven by these tests.

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
