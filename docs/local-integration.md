# Local private-engine integration

## One project, local licensed dependency

The original installer provisions the reviewed engine into the same core folder as the agents, Raw, Review and Wiki. There is no second user-managed repository. The authorized source folder is an installation input only; the installed runtime does not depend on it.

```bash
python3 scripts/install_private_engine.py --source /path/to/authorized-engine --root . --check
python3 scripts/install_private_engine.py --source /path/to/authorized-engine --root .
```

The pinned manifest in `config/private-engine-files.json` verifies 90 source files by SHA-256 and exact Git blob hashes. The installer copies only those files plus local provenance metadata, preserving LICENSE and notices. Existing differing files block installation before writes; matching repeated installation leaves files unchanged. Existing local settings are preserved. No old Raw/Review/Wiki, identity, history or preference files are copied.

The engine lives at its canonical `scripts/`, `Schema/` and `_templates/` paths. The tracked original installer remains `scripts/install_private_engine.py`. Licensed files, generated local settings and `.wanderloots-llm-wiki/` operational state are excluded from Git publication. Raw/Review/Wiki are deliberately not blanket-ignored: the owner can select knowledge for this same private GitHub repository after reviewing publication scope. No remote writes or vendor uploads are performed by installation or these tests. Back up operational state explicitly; ignored does not mean disposable.

The tested engine is 2.0.5. Canonical apply calls `wiki_tool.py`, whose broad imports require support modules even though this test never activates updates, expansions, servers or network services. This is an API installation, not the complete upstream graphical/bootstrap kit.

## Read-only review CLI

After installation and authorized runtime execution, use this same project root:

```bash
python3 adapters/review_chat.py --root . list
python3 adapters/review_chat.py --root . show "$CASE_ID"
python3 adapters/review_chat.py --root . packet "$CASE_ID"
```

The earlier `--engine-root` / `--instance-root` pair remains supported for compatibility; it is not the recommended user layout.

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
    --output-parent "$OUTSIDE_BASELINE" --synthetic-only --unified
```

ENGINE_ROOT supplies the authorized installation files. The harness creates a fresh, visibly marked synthetic copy of the core layout, installs its engine into that same folder and uses its copied adapter with `--root`. These disposable test fixtures are not extra repositories for normal use. It supplies invented Spanish source text and a typed draft, calls the upstream validator and receipt-backed hold path, exports read-only review packets, then **simulates** one reviewer decision against invented content. Only the existing upstream canonical apply path creates the resulting concept page. Held proposals can already update the engine's Wiki log; the proposed concept page remains absent until simulated approval.

The main instance disables Git and memory and forbids external model processing. No authenticated Git checkout, real vault startup, semantic model synthesis or real human approval is claimed. The source body is verified unchanged after apply. Recovery fixtures are invented files in the same disposable test area; a separate instance deliberately preserves an unresolved recovery conflict.

The harness retains JSON evidence outside the baseline: read-only outputs, held/apply receipts, the clearly simulated decision, recovery checkpoints and test-report.json. The test report records the exact source revision and distinct host/test network namespaces.

## Observed result

35 integration checks passed in the unified single-folder fixture:

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

Nine additional installer tests passed: read-only preview, idempotent reinstall, collision preservation, corrupted-source rejection, symlink rejection, required-folder and parent-path conflict rejection, existing-setting preservation, and Git exclusion checks showing vendor files excluded while original code and Raw/Review/Wiki remain trackable. Run them with:

```bash
unshare --user --map-root-user --net -- env PYTHONDONTWRITEBYTECODE=1 \
  LIBRARIAN_ENGINE_SOURCE="$ENGINE_ROOT" \
  python3 -m unittest discover -s tests -p test_private_engine_install.py -v
```

This is a bounded smoke test, not the complete [acceptance specification](acceptance.md). Production bootstrap/preflight, model-driven semantic submission, authenticated user-event binding, expiry/revocation, multi-writer fencing and device sync remain untested or unimplemented. The upstream actor field is a heuristic and its ETag argument is optional. Upstream replay currently raises a stale-decision error rather than returning the prior receipt. Do not label the authenticated review/apply milestone complete.

## Next useful step

Present an engine-issued pending packet in the chosen host, then implement the host's verified user-event binding before enabling any real-content approval or mutation. The read-only adapter can support that work now. Keep vendor code private and review original adapter changes separately before any optional upload.
