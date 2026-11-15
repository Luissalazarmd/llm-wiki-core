# Optional tools

Use existing permitted host tools or these helpers; no automatic installation.
[Private settings](../config/personal.example.json) restrict operations, never grant
permission. Declare actual library_root, authorized_paths and optional source/draft/
knowledge/proposal layers. Defaults are read-only; configuration stays private.

Python 3.10+ and PyYAML are needed only for these optional helpers (numbering uses
`zip(strict=True)`); the dependency is pinned in [requirements.txt](../requirements.txt).
No installation is automatic. The current suite was exercised on Linux with Python
3.14.8 and PyYAML 6.0.3; 3.10 is a code floor, not a tested minimum. Other
operating systems and filesystems require their own validation.

After the person agrees, set up an environment outside Core and the library:

```sh
python3 -m venv /path/outside/core-env
/path/outside/core-env/bin/python -m pip install -r requirements.txt
```

Keep the private JSON config outside the Core checkout too. Relative `../` example
paths resolve against the JSON's own directory, so put the JSON beside the library,
not in `config/`.
Without helper configuration or dependencies, use authorized host reading and
proposals. Omitted `write_policy` defaults to `read_only`.

Relative `library_root` and `recovery_directory` resolve against the JSON file's
directory, not the shell directory. Authorized paths and layer selections are
relative to that library root. A scope may be one exact selected file in a flat,
mixed library; no folder migration is needed.

Illustrative private settings for an **existing, explicitly editable** library:

```json
{
  "version": 1,
  "library_root": "../existing-library",
  "authorized_paths": ["Notes", "Sources"],
  "layers": {"sources": ["Sources"]},
  "write_policy": "plain_files",
  "recovery_directory": "../private-recovery"
}
```

Replace placeholders with authorized existing locations; this example creates no
directories and grants no consent, so `recovery_directory` must exist first. Use this
shape to write; [`config/personal.example.json`](../config/personal.example.json) is read-only. `layers.sources` protects originals from the
plain-note writer and is required with `plain_files` (`"sources": []` declares
none); `recovery_directory` must be outside both the library and the Core checkout.
In mixed folders, select exact source files for that layer.

```sh
python3 scripts/knowledge.py --root /library --mode existing --scope Reading
python3 scripts/library.py --config /private.json map --scope Reading
python3 scripts/library.py --config /private.json proposal --create --target Notes/new.md --evidence Sources/a.md < /draft.md
python3 scripts/library.py --config /private.json proposal --target Notes/existing.md --evidence Sources/a.md < /draft.md
python3 scripts/capture_check.py --config /private.json --target Sources/new.md < /capture.md
python3 scripts/capture_write.py --config /private.json prepare --target Sources/new.md --attach /downloads/paper.pdf Sources/new.pdf < /capture.md > /capture.json
python3 scripts/capture_write.py --config /private.json save --packet /capture.json
python3 scripts/template_write.py --config /private.json prepare --name Fuente-podcast.md < /template.md > /template.json
python3 scripts/template_write.py --config /private.json save --packet /template.json
python3 scripts/view_write.py --config /private.json prepare --target Mapa.canvas < /draft.canvas > /view.json
python3 scripts/view_write.py --config /private.json save --packet /view.json
python3 scripts/note_write.py --config /private.json check --packet /proposal.json
```

For the first save, prepare the packet and present exact content/diff plus the
readable result; obtain the actual person’s approval under the [review contract](review-contract.md).
Immediately recheck base/evidence, permission and conflicts; save with private
recovery, then read back exact bytes. CLI flags cannot authenticate approval.

A proposal that arrives while the person is away may be parked, never accepted,
when the library rules permit [custody](review-contract.md#proposal-custody) and
the settings declare `layers.proposals` beside `sources` and `knowledge`:

```sh
python3 scripts/library.py --config /private.json proposal --park --target Review/Inbox/new.md --origin "agent: reader" --proposed-target Wiki/Notes/new.md < /received.md > /parked.json
python3 scripts/note_write.py --config /private.json save --packet /parked.json
```

See [parked proposals](plain-saving.md#parked-proposals). Someone starting without a
library can copy the [starter library](starter-library.md).

An idea the owner states in conversation has no library evidence. Retain it as a
seed whose draft declares `role: note`, `maturity: seed` and `origin: owner`, through
the same review and save; `--owner-authored` replaces `--evidence` for that case only:

```sh
python3 scripts/library.py --config /private.json proposal --create --owner-authored --target Wiki/Notes/idea.md < /draft.md > /seed.json
python3 scripts/note_write.py --config /private.json save --packet /seed.json
```

See [owner-authored seeds](plain-saving.md#owner-authored-seeds); the flag is the
agent's assertion, never proof of authorship or approval.

Save uses save instead of check; recovery uses restore --record, which reports its own
[record](plain-saving.md) so the restore can be reversed the same way. A capture, with
optional PDF, image, EPUB or audio attachments, goes through `capture_write.py`
prepare → review → save, which rechecks, creates independent copies without overwrite
and verifies them; it is not an approval engine. `capture_write.py retire` is the
owner's explicit exception to create-only custody, never routine: it prints a plan,
then moves the capture to private recovery under `--expected-sha256`; `revise` is the narrower
exception that replaces only a wrapper's text and keeps its attachments. `template_write.py`
creates or changes a blank [source template](raw-admission.md#templates) the same way,
outside every layer. `view_write.py` does the same for [views](views.md): a `.canvas`, a `.base` or a
Markdown page declaring `role: view`, in the library root or a declared `layers.views`
folder, never in Raw, Review or Wiki. Obsidian syntax comes from the vendored
[Obsidian skills](../adapters/obsidian/README.md), which never replace these writers. Follow [review](review-contract.md),
[capture](raw-admission.md), [plain saving](plain-saving.md) and [projection](projection-reference.md).
Mapping bounds inventory to 500 entries and reads attachment metadata, never binary content.
Existing-library `map` and `knowledge.py --mode existing` deliberately report `role:
unknown` and path-based IDs: read the note for what it declares. `--focus` takes that
ID, as in `path:Notes/x.md`. `library_rules_path: null` means only that there is no root
`AGENTS.md`; the library's rules may have another name, so look for them.
Helpers follow wikilinks with library-relative paths; Markdown links such as
`[x](Other.md)` are not counted here, so report them instead of assuming a connection.

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
