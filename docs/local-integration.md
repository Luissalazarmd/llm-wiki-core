# Local private-engine integration

## Implemented boundary

The baseline now contains original, read-only adapter code and a synthetic integration test. It still does **not** distribute or install the private Wanderloots engine. Install that dependency separately only from an authorized source, preserving its LICENSE and notices. Keep both dependency and instance outside this baseline.

The tested dependency is engine 2.0.5, pinned by a private `SOURCE_MANIFEST.json` containing the source commit, exact Git blob hashes, SHA-256 values and an explicit file allowlist. The local extraction contains Python runtime modules, four generic schema/policy files, templates and notices. It excludes the old vault's Raw, Review, Wiki, Agents, preferences, durable history, credentials and Git history. No dependency files were uploaded.

The canonical apply path invokes `wiki_tool.py`, which imports the wider CLI. Its import dependencies therefore include optional support packages even though this test does not activate updates, expansions, browser servers, memory providers or network access. This is not a complete upstream kit/bootstrap installation.

## Read-only review CLI

Set ENGINE_ROOT to the separately provisioned private engine directory and INSTANCE_ROOT to the separate private instance. After reviewing and authorizing the engine's execution:

```bash
python3 adapters/review_chat.py --engine-root "$ENGINE_ROOT" --instance-root "$INSTANCE_ROOT" list
python3 adapters/review_chat.py --engine-root "$ENGINE_ROOT" --instance-root "$INSTANCE_ROOT" show "$CASE_ID"
python3 adapters/review_chat.py --engine-root "$ENGINE_ROOT" --instance-root "$INSTANCE_ROOT" packet "$CASE_ID"
```

- `list` delegates to upstream `review.list_cases`.
- `show` delegates to upstream `rail.case_detail`, preserving evidence, proposed contents and full diffs.
- `packet` additionally returns the engine's persisted case and full proposal envelope, including base targets and source anchors when present.
- Packet hashing identifies the displayed payload. Display fields such as case age can change with time even when the proposal does not. It is not an approval token and does not strengthen the upstream case ETag.
- There is no approve, reject, apply or external communication endpoint in this adapter.
- The CLI disables Python bytecode writes and installs an audit guard against accidental writes, child processes and network use. The Python helper alone does not install that guard. Multiple engine roots in one Python process are unsupported because imports are cached. This is a cooperative safety check, not a hostile-code sandbox.
- Display reads are best-effort snapshots without a concurrent-writer lock. Do not use this packet as a production approval object. A future authenticated host must acquire a consistent engine snapshot and bind the actual user event to it.

Run the adapter in an OS-level restricted environment when stronger isolation is required. The synthetic test was run inside a fresh Linux user/network namespace.

## Reproducible synthetic test

This command requires Linux with permitted unprivileged user/network namespaces. OUTSIDE_BASELINE must be a dedicated location outside this repository. No packages need installing for the exercised code paths.

```bash
LIBRARIAN_HOST_NETNS="$(readlink /proc/self/ns/net)" \
  unshare --user --map-root-user --net -- \
  env PYTHONDONTWRITEBYTECODE=1 python3 tests/synthetic_engine_smoke.py \
    --engine-root "$ENGINE_ROOT" \
    --output-parent "$OUTSIDE_BASELINE" --synthetic-only
```

The harness creates fresh, visibly marked synthetic instances. It supplies invented Spanish source text and a typed draft, calls the upstream validator and receipt-backed hold path, exports read-only review packets, then **simulates** one reviewer decision against invented content. Only the existing upstream canonical apply path creates the resulting concept page. Held proposals can already update the engine's Wiki log; the proposed concept page remains absent until simulated approval.

The main instance disables Git and memory and forbids external model processing. No authenticated Git checkout, real vault startup, semantic model synthesis or real human approval is claimed. The source body is verified unchanged after apply. Recovery fixtures are invented files in the same disposable test area; a separate instance deliberately preserves an unresolved recovery conflict.

The harness retains JSON evidence outside the baseline: read-only outputs, held/apply receipts, the clearly simulated decision, recovery checkpoints and test-report.json. The test report records the exact source revision and distinct host/test network namespaces.

## Observed result

35 checks passed on the local pinned extraction:

- Source capture detection, receipt-backed scan and no-work rescan
- Valid review-first proposal held without creating its concept page
- Repeated list/show/packet responses identical, with instance file hashes and modification times unchanged
- Full persisted proposal, evidence and diff available for review; display hash recomputes correctly
- Malformed and missing case IDs fail without observed instance-file changes
- Stale revision/ETag rejected without writes
- Changed source and competing target block canonical apply and preserve content
- Simulated approval produces a Spanish concept, resolved case and canonical receipt
- Receipt hashes valid; no incomplete happy-path transactions
- Replay rejected without duplicate effects, including from a fresh Python process
- Recovery after prepared/files_applied/backup_recorded and safe repeated recovery
- Terminal-receipt recovery preserves committed state
- Concurrent recovery edit preserved and reported as a conflict

This is a bounded smoke test, not the complete [acceptance specification](acceptance.md). Production bootstrap/preflight, model-driven semantic submission, authenticated user-event binding, expiry/revocation, multi-writer fencing and device sync remain untested or unimplemented. The upstream actor field is a heuristic and its ETag argument is optional. Upstream replay currently raises a stale-decision error rather than returning the prior receipt. Do not label the authenticated review/apply milestone complete.

## Next useful step

Present an engine-issued pending packet in the chosen host, then implement the host's verified user-event binding before enabling any real-content approval or mutation. The read-only adapter can support that work now. Keep vendor code private and review original adapter changes separately before any optional upload.
