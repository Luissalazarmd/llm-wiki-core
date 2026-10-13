# Optional plain-note saving

The Bibliotecario [review/save skill](../skills/review-save/SKILL.md) uses host tools and actual user confirmation. **`scripts/note_write.py` does not request, authenticate or verify consent.** It must only be called after the host's real review/permission step. An agent with unrestricted shell/filesystem access can bypass this helper; it is not a sandbox. Do not grant it broad unattended access on the strength of these checks.

## Two library paths

- Managed libraries keep their canonical capture/review/apply path and authenticated-host requirements. Read [review contract](review-contract.md) only for those operations. This helper refuses any entry with a known local managed-marker name, including dangling symlinks, but cannot identify every vendor: the agent/host must inspect rules before choosing a path. Absence of markers is not writing permission.
- For a library that explicitly permits ordinary Markdown edits, reuse its save/history tools. If missing version/recovery checks justify a helper, select `write_policy: plain_files` in the single private personal config, plus an existing authorized `recovery_directory` **outside** the library. Both are choices requiring permission, not autoconfiguration. Default is `read_only`; `canonical_engine` also blocks this helper. Existing source paths declared in `layers.sources` and AGENTS files are not editable.

## Minimal executable helper

```sh
python3 scripts/note_write.py --config /path/to/personal.json check --packet /path/to/proposal.json
# Only after the actual person confirmed this exact diff and host permits the operation:
python3 scripts/note_write.py --config /path/to/personal.json save --packet /path/to/proposal.json
# Only after separate restore review and permission:
python3 scripts/note_write.py --config /path/to/personal.json restore --record /path/to/recovery-record.json
```

The packet comes from existing `knowledge.py`/`library.py proposal`: unchanged target/evidence byte hashes, exact draft/diff and packet content hash. The helper validates those bindings and authorized paths and **recomputes the exact diff from current original bytes and the draft**; a mismatched diff is rejected even if the packet hashes were recomputed. It stores previous bytes and proposed content/evidence in a private `0600` recovery record before replacing the one note, then re-reads saved content. The record is **not an authenticated approval receipt** and is written before save; its existence alone cannot prove success. No audit database or lifecycle service.

Restore compares current bytes to the saved-result hash, validates previous bytes and refuses to overwrite later work. Inspect records locally; they contain private originals and proposals and must not be committed/uploaded. Same-machine copies are not external backups. Existing directory permissions and retention are the owner's responsibility.

## Limits

Existing Markdown targets only, at most 256 KiB each; new captures/notes use the host's verified create-only or canonical tools. No deletion, renaming, instruction edits or state-label transitions. A source that is not configured as a source can only be protected by actual library rules/host restrictions; settings alone do not infer custody.

One local cooperative writer, no active sync/editor writes during operation. Checks immediately precede replacement but do not provide atomic compare-and-swap against another process: no lock, fencing, adversarial-race protection, signed records or multi-file transaction. Atomic single-file replacement and fsynced recovery bytes reduce ordinary failure risk; no full crash-durable directory journal is claimed. A failed save may leave a recovery record while the original remains unchanged. Do not report completion without actual target readback. ACL/xattr/ownership preservation beyond file mode is not certified; use the library's existing writer where those are material.

## Verification

Synthetic tests exercise save/readback, stale base/evidence refusal, changed packet refusal, managed/default blocking, immutable configured sources, restore refusal after later edits and injected replacement failure preserving original/recovery bytes. These prove helper behavior, not human authentication or semantic entailment. Host confirmation and permitted canonical integration remain distinct acceptance gates.
