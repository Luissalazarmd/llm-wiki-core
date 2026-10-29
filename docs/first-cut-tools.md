# Optional tools

Use existing permitted host tools or these helpers; no automatic installation.
[Private settings](../config/personal.example.json) restrict operations, never grant
permission. Declare actual library_root, authorized_paths and optional source/draft/
knowledge layers. Defaults are read-only; configuration stays private.

```sh
python3 scripts/knowledge.py --root /library --mode existing --scope Reading
python3 scripts/library.py --config /private.json map --scope Reading
python3 scripts/library.py --config /private.json proposal --create --target Notes/new.md --evidence Sources/a.md < /draft.md
python3 scripts/capture_check.py --config /private.json --target Sources/new.md < /capture.md
python3 scripts/note_write.py --config /private.json check --packet /proposal.json
```

Save uses save instead of check; recovery uses restore --record. Capture recheck
uses --expected-sha256; readback adds --saved. Follow [review](review-contract.md),
[capture](raw-admission.md), [plain saving](plain-saving.md) and [projection](projection-reference.md).
Mapping bounds inventory to 500 entries and reads attachment metadata, never binary content.

## Optional living-synthesis numbering

An owner may add `"living_synthesis": {"scopes": ["Notes"], "history_complete": true}`
to the private JSON settings. The declaration is a
human custody assertion, not inferred evidence of complete history. Scopes must
already be authorized. Numbering inventories at most 500 entries and hashes every
file (up to 256 KiB each and 8 MiB total); narrow the scope if necessary.

Existing thematic maps use explicit stable `id`, `role: map`,
`map_kind: thematic`, a quoted three-digit `address`, and `former_addresses`.
A retained note uses `id`, `role: note`, `maturity`, and `primary_moc` as an
exact scoped Markdown path. Preparation adds its quoted MOC-scoped address and
empty history when needed. Seeds, catalogs and maps without thematic designation
are not allocated. Existing reservations must be complete and gap-free; IDs and
addresses must be unique. Ordinary updates keep identity, primary association,
address and history. The review packet binds the complete candidate, scope and
configuration; check/save refuse stale packets. Restore cannot release a
reservation. The plain-file writer's existing permission and recovery rules still
apply; proposal preparation does not grant approval or write permission.

### Prepare and review together

The same `proposal` command numbers a synthesis under an existing MOC. For a new
MOC, use `proposal-batch --evidence Sources/a.md` with a JSON array on stdin:

```json
[
  {"target":"Notes/shade.md","create":true,"draft":"---\nid: theme-shade\nrole: map\nmap_kind: thematic\n---\n# Shade comparisons\nRead the conditions before comparing observations.\n"},
  {"target":"Notes/comparison.md","create":true,"draft":"---\nid: argument-comparison\nrole: note\nmaturity: synthesis\nprimary_moc: Notes/shade.md\n---\n# Comparison conditions\nFictional explanation; evidence: [[Sources/a]].\n## Limits\nNo measured effect is established.\n"}
]
```

Preparation adds MOC `001`, synthesis `001-01`, empty `former_addresses`, and the
MOC's reading link. Further MOCs and their syntheses have independent sequences.
The batch contains full drafts, exact diffs and base/evidence hashes for **every**
change; show all of them before the actual person's decision. Empty thematic MOC
creation is refused. Neither numbering nor a `map_kind` label evaluates usefulness.
There is no additional classification requirement outside this optional scope.

### Deliberate primary-MOC move

Add `"references_complete": true` inside `living_synthesis` only after establishing
that the selected scope contains the relevant incoming references. This is another
owner assertion, not automatic whole-library discovery. Prepare the existing
synthesis with its new `primary_moc` using `proposal --target Notes/comparison.md
--move-primary --evidence Sources/a.md`. This returns a **batch** including any
proposed destination-map link. Batch entries may also use `"move_primary": true`.

Moves keep the same ID/path and reserve the old address in `former_addresses`;
the next destination address is frozen before review. Source-map links remain
valid secondary references. Incoming explicit vault-path wikilinks and their
exact headings must still resolve; former-address labels remain interpretable.
Address-based IDs/filenames, affected Markdown links and unsupported basename or
relative references require local reconciliation first, not a guessed rename.
No native link updater or general Markdown/host resolver is supplied.

Use the same `note_write.py check/save --packet` for either packet shape. A batch
is bounded to 20 changes including generated companions and a 2 MiB packet.
All targets/postimages are checked before writing. Saving remains sequential,
**not multi-file atomic**: a later I/O failure returns exit 2, empty stdout and
JSON stderr with `status: plain_batch_partial`, completed targets and recovery
records. Stop and inspect that state; never blindly replay the original batch.
Restore uses each existing per-file record and refuses recoding rollback that
would release reservations. See [plain-save limits](plain-saving.md).

Pause concurrent editing/sync. There is no locking or concurrency guarantee,
new approval engine, library migration, scientific validation or native rendering
certification. Managed libraries still require their existing permitted writer.
