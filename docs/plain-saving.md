# Optional plain-note saving

The Bibliotecario [review/save skill](../skills/review-save/SKILL.md) uses host tools and actual user confirmation. **`scripts/note_write.py` does not request, authenticate or verify consent.** It must only be called after the host's real review/permission step. An agent with unrestricted shell/filesystem access can bypass this helper; it is not a sandbox. Do not grant it broad unattended access on the strength of these checks.

## Two library paths

- Managed libraries keep their canonical capture/review/apply path and authenticated-host requirements. Read [review contract](review-contract.md) only for those operations. This helper refuses any entry with a known local managed-marker name, including dangling symlinks, but cannot identify every vendor: the agent/host must inspect rules before choosing a path. Absence of markers is not writing permission.
- For a library that explicitly permits ordinary Markdown edits, reuse its save/history tools. If missing version/recovery checks justify a helper, select `write_policy: plain_files` in the single private personal config, plus an existing authorized `recovery_directory` **outside** the library. Both are choices requiring permission, not autoconfiguration. Default is `read_only`; `canonical_engine` also blocks this helper. Existing source paths declared in `layers.sources` are immutable. Known instruction filenames `AGENTS.md`, `SKILL.md`, `CLAUDE.md` are refused case-insensitively for check/save/create/restore. This is a filename guard, not detection of every possible instruction document; other policy files must be excluded by actual rules/host permissions.

## Minimal executable helper

For a new **derived** note, prepare the full proposal before writing anything to the library:

```sh
python3 scripts/library.py --config /path/to/personal.json proposal --create --target Notes/new.md --evidence Sources/a.md < /path/to/draft.md
# Save this stdout packet privately using authorized host tools; present it for actual review.
```

Without `--create`, proposals continue to require an existing target. With it, the packet binds `operation: create`, `expected_absent: true`, `base_sha256: null`, exact draft/diff from `/dev/null` and explicit evidence hashes. Parent directories must already exist within authorized paths; no folder creation or placeholder note. Nonempty drafts and at least one explicit existing Markdown evidence file are required. The same check/save commands below handle either operation. Human review, library templates and claim/locator verification remain mandatory host/agent steps, not hash properties.

```sh
python3 scripts/note_write.py --config /path/to/personal.json check --packet /path/to/proposal.json
# Only after the actual person confirmed this exact diff and host permits the operation:
python3 scripts/note_write.py --config /path/to/personal.json save --packet /path/to/proposal.json
# Only after separate restore review and permission:
python3 scripts/note_write.py --config /path/to/personal.json restore --record /path/to/recovery-record.json
```

The packet comes from existing `knowledge.py`/`library.py proposal`: unchanged target/evidence byte hashes, exact draft/diff and packet content hash. The helper validates those bindings and authorized paths and **recomputes the exact diff from current original bytes and the draft**; a mismatched diff is rejected even if the packet hashes were recomputed. It stores previous bytes and proposed content/evidence in a private `0600` recovery record before replacing the one note, then re-reads saved content. The record is **not an authenticated approval receipt** and is written before save; its existence alone cannot prove success. No audit database or lifecycle service.

For creation, check/save revalidate the absent destination and exact evidence/diff. Save stages complete bytes in a private temporary file in the existing destination directory, fsyncs it, then uses an atomic no-clobber hard link to publish: an existing file, directory or dangling symlink blocks publication, including one appearing after the check. Unsupported hard links fail closed; no overwrite fallback. The private record stores the proposal and `before_exists: false`, with null previous bytes/hash. It is still a pre-write record, not proof of success. Temporary files are cleaned on ordinary handled failures; no crash-cleanup journal is claimed.

Restore compares current bytes to the saved-result hash, validates previous bytes and refuses to overwrite later work. Creation records are rejected by restore: there were no previous bytes, and creating an empty file would not restore absence. Deleting a new note is a separately reviewed operation, not implemented here. Inspect records locally; they contain private originals and proposals and must not be committed/uploaded. Same-machine copies are not external backups. Existing directory permissions and retention are the owner's responsibility.

## Limits

Existing Markdown updates or absent derived-note creation, at most 256 KiB each; new source captures still use the host's verified capture tools. No deletion, renaming, editing of the known instruction filenames above or automatic state-label transitions. The helper does not classify arbitrary prose as instructions; the host must prevent any other prohibited target. No source-capture runtime, automatic template validation, Reference uniqueness or semantic duplicate detection. Reuse/identity checks apply within the authorized scope; do not claim library-wide uniqueness without evidence. A source that is not configured as a source can only be protected by actual library rules/host restrictions; settings alone do not infer custody.

One local cooperative writer, no active sync/editor writes during operation. Checks immediately precede replacement but do not provide atomic compare-and-swap against another process: no lock, fencing, adversarial-race protection, signed records or multi-file transaction. Atomic single-file replacement and fsynced recovery bytes reduce ordinary failure risk; no full crash-durable directory journal is claimed. A failed save may leave a recovery record while the original remains unchanged. Do not report completion without actual target readback. ACL/xattr/ownership preservation beyond file mode is not certified; use the library's existing writer where those are material.

## Verification

Synthetic tests exercise save/readback, stale base/evidence refusal, changed packet refusal, managed/default blocking, immutable configured sources, restore refusal after later edits and injected replacement failure preserving original/recovery bytes. These prove helper behavior, not human authentication or semantic entailment. Host confirmation and permitted canonical integration remain distinct acceptance gates.
