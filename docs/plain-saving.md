# Plain-save mechanics

The [review contract](review-contract.md) owns consent. This helper does not
request/authenticate it. Explicit plain_files policy and existing private recovery
directory outside the library are required; read_only/canonical_engine refuse.
Managed markers, configured sources and known instruction filenames are protected;
actual rules must cover unknown markers/documents and unconfigured originals.

Packets bind base/absence, draft, recomputed exact diff and evidence. Recheck before
publication. Updates persist previous bytes in a private 0600 pre-write record,
then atomically replace one note. Creation stages/fsyncs complete bytes and uses
an atomic no-clobber hard link: competing entries block publication. Records can
remain after failure; readback establishes success.

Restore verifies prior bytes and refuses later edits. Creation has no prior bytes;
restore never deletes. No rename, source capture or automatic state changes.

One quiet cooperative writer; no atomic compare-and-swap, locks/fencing, signed
receipts, multi-file transaction or full crash journal. ACL/xattr/ownership beyond
mode is unverified. Keep recovery private with independent backup/retention.
