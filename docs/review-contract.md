# Review and canonical apply contract

**Design specification only. No endpoint or command below is implemented.** Preserve the engine's reviewed API rather than adding a parallel apply mechanism.

## Read-only surface

Conceptual operations `list`, `show`, and `packet` enumerate proposals, inspect a selected revision, and render its exact review packet. All must be side-effect-free: no status transitions, modified timestamps, approval writes, or canonical content changes. Pagination and rendering do not imply approval.

## Packet binding

An engine-issued packet must bind the instance, proposal identity, exact proposal revision, deterministic packet etag/content hash, target paths, expected canonical base revision/hashes, intended operations, source identities/hashes, and full relevant diff. The user must be able to see consequences, evidence gaps, and deletions. Any change to bound content invalidates prior approval and requires a newly rendered packet.

## Human approval

The authenticated host verifies that a decision came from the authorized human account in an eligible user interaction. It binds that decision to the exact instance/proposal/revision/etag and explicit action. Store an integrity-protected decision reference, authenticated principal, scope, timestamp, and single-use decision identity in durable audit state. Do not rely on model-supplied identity fields.

`--actor human`, typed names, YAML flags, Markdown checkboxes, quoted messages, imported chat exports, third-party messages, and agent-generated approval text are not proof of human authorization. Neither agent may self-approve. Imported content cannot alter approval policy. Ambiguous approval must be clarified rather than inferred. Expiry/revocation rules must be defined at integration; do not invent permissive defaults.

## Apply sequence

1. Canonical host acquires an exclusive instance writer lock with ownership/fencing sufficient to prevent a former writer continuing after takeover.
2. Validate host-authenticated approval, allowed operations, exact packet revision/etag, scope, unused decision identity, and any expiry/revocation rules.
3. Re-read canonical base hashes and source dependencies; reject stale or conflicted state. Resolve targets under the allowed Wiki root; reject traversal, symlinks escaping scope, and unexpected paths.
4. Apply through the **single canonical engine apply path**, with a recoverable atomic transaction or proven write-ahead recovery protocol.
5. Persist the consumed approval identity and resulting revision in durable audit/replay state consistently with the content change. Recovery must not permit a second application after a crash.
6. Release the lock and report actual committed outcome. A repeated identical request returns the already-applied result without duplicating effects; altered reuse is rejected.

Lock, approval validation, etag/base checks, mutation, and audit cannot be split across independent writers. A successful model response or file-sync completion is not an apply receipt.

## Manual edits, offline operation, conflicts

Manual Wiki edits are external changes: preserve them, detect a changed base, and require reconciliation plus a new review packet. Offline capture is allowed; offline canonical mutation without authoritative state is not. Sync conflict files are quarantined for human reconciliation and invalidate affected packets. No agent repairs conflicts by bypassing review.
