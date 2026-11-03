# Plain-save mechanics

The [review contract](review-contract.md) owns consent. This helper does not
request/authenticate it. Explicit plain_files policy and existing private recovery
directory outside the library are required; read_only/canonical_engine refuse.
Managed markers, configured sources and known instruction filenames are protected;
actual rules must cover unknown markers/documents and unconfigured originals.
plain_files requires an explicit `layers.sources` list (`[]` declares none); the
source boundary is compared by filesystem identity, not spelling, and an existing
note whose frontmatter declares `role: source` is refused even outside that layer.
Created notes get the process default mode (umask), records stay 0600 UTF-8, and a
recovery directory inside the Core checkout is refused.

Packets bind base/absence, draft, recomputed exact diff and evidence. Recheck before
publication. Updates persist previous bytes in a private 0600 pre-write record,
then atomically replace one note. Creation stages/fsyncs complete bytes and uses
an atomic no-clobber hard link: competing entries block publication. Records can
remain after failure; readback establishes success.

Restore verifies prior bytes and refuses later edits. Creation has no prior bytes;
restore never deletes. No rename or source capture is supplied.

The [optional numbered profile](first-cut-tools.md#optional-living-synthesis-numbering)
adds complete scoped membership/configuration/reservation checks before saving.
A numbered batch validates every target and postimage before the first recovery
record/write, then rechecks the expected scope before each sequential save. Only
its own exact writes advance that expectation. It uses the same per-file recovery
records, not a transaction journal. I/O failures can leave earlier files saved:
exit 2 reports `plain_batch_partial`, completed targets and new recovery records.
Inspect and prepare a fresh reviewed candidate; do not blindly retry or auto-undo.
Restore permits same-address content updates but refuses to release or replace
identity, primary association or current/former reservations. Creation still has
no automatic deletion recovery. A primary recoding reversal is another reviewed
move, not restoration that recycles history.

One quiet cooperative writer; no atomic compare-and-swap, locks/fencing, signed
receipts, multi-file transaction or full crash journal. ACL/xattr/ownership beyond
mode is unverified. Keep recovery private with independent backup/retention.

Creation requires filesystem hard-link support; these mechanics do not establish
OS portability. In mixed folders, protect originals through exact per-file
`layers.sources` selections and local rules; no migration is required.
