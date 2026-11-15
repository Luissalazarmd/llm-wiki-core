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
restore never deletes. No rename is supplied; sources are created only by the
[capture writer](raw-admission.md#capture-writer).

A restore is recorded too. Before replacing the note it writes a new private 0600
record of the same format holding the bytes it displaces, `operation: restore` and
the name and hash of the record it used (`restored_from`). It reports that record
as `record`, beside `sha256`, `previous_sha256` and `restored_from`; nothing is
written into the library. `restore --record` on the new record reverses the restore
under the same checks, so save → restore → restore returns to the saved bytes, and
each step leaves its own record. A record applies only while the note holds exactly
the version that record produced. Reversing re-applies bytes that were saved before;
it re-checks neither their evidence nor their review, and stays a decision for the person.

If that record cannot be written, nothing is replaced. If the replacement fails
afterwards, the note keeps its bytes and the unused record is removed. Both exit 2
with `restore_not_done`, `note_unchanged: true` and `record: null`; `unused_record`
names a record that could not be removed. A replaced note whose readback fails
reports `restore_unverified`, `note_unchanged: false` and the record holding the
displaced bytes: inspect before doing anything else.

The [optional numbered profile](first-cut-tools.md#optional-living-synthesis-numbering)
adds complete scoped membership/configuration/reservation checks before saving.
A numbered batch validates every target and postimage before the first recovery
record/write, then rechecks the expected scope before each sequential save. Only
its own exact writes advance that expectation. It uses the same per-file recovery
records, not a transaction journal. I/O failures can leave earlier files saved:
exit 2 reports `plain_batch_partial`, completed targets and new recovery records.
Inspect and prepare a fresh reviewed candidate; do not blindly retry or auto-undo.
Restore permits same-address content updates but refuses to release or replace
identity, primary association or current/former reservations, in either direction:
a restore record carries the numbered binding forward (`numbered`). Creation still has
no automatic deletion recovery. A primary recoding reversal is another reviewed
move, not restoration that recycles history.

## Parked proposals

[Custody](review-contract.md#proposal-custody) needs the library rules to permit it
and an explicit `layers.proposals` list of existing folders. That declaration also
requires explicit `layers.sources` and `layers.knowledge`, and refuses any overlap
with either by spelling or filesystem identity, so custody has no path into
originals or retained knowledge. `library.py proposal --park --target ... --origin
... --proposed-target ...` wraps literal stdin; `note_write.py save` publishes it with
the same no-clobber creation and private record, and reports `proposal_parked`,
`custody_only: true`, `accepted: false`.

```markdown
---
proposal_status: pending
origin: "agent: reader"
conversation: "thread 7"
received: "2026-11-11"
proposed_target: "Wiki/Notes/shade.md"
evidence:
  - path: "Raw/Sources/a.md"
    sha256: "..."
  - reference: "doi:10.0000/example v2"
    verified: "no"
text_sha256: "..."
---
# Propuesta en custodia

> Custodia, no aceptación: ...

## Historial

- 2026-11-11 · pendiente · recibida de agent: reader

## Texto propuesto

(the literal text, unchanged to the end of the file)
```

`conversation` and `evidence` are optional; `--evidence` binds library files by hash
and `--external-evidence` records the origin's own statement unverified. Labels
follow `language`. The writer parks only this shape with `pending`, the bound text
hash and no `role`, `maturity` or `review` of its own. Custody creates without
evidence only inside the proposals layer. Outside it, the single evidence-free
creation is a declared [owner-authored seed](#owner-authored-seeds); every other
creation, Wiki included, keeps every existing requirement.

Close with an ordinary `proposal` update after the decision exists: change
`proposal_status`, append a history line and, when accepted, name the saved note. The
writer refuses an update that alters the literal text, origin, reception or earlier
history lines, or drops the format. The file stays in place; no deletion or rename
is supplied, and restoring the update returns it to its previous status.

The helper wraps what it is given: it cannot prove that stdin equals the original
message or that the origin is who it claims, and it reads no library rules. Edits
made outside the helper remain possible, as for every plain file.

## Ingesta items

[Ingest custody](review-contract.md#ingest-custody) needs the library rules to permit
it, `"ingest_custody": true` in the private settings and the same explicit
`layers.proposals` that parking needs; without the setting every command below
refuses, whatever parking is allowed. `library.py ingest --target ... --source ...
--origin ...` wraps the analysis on stdin; `note_write.py save` publishes it with the
same no-clobber creation and private record, and reports `ingest_item_created`,
`custody_only: true`, `reviewed_by_owner: false`.

```markdown
---
ingest_status: pending
source: "Raw/Sources/guia.md"
origin: "agent: reader"
conversation: "thread 7"
created: "2026-11-15"
---
# Ingesta: (the title of the source)

Fuente: [[Raw/Sources/guia]]

> Análisis preparatorio del agente, sin revisar: ...

## Orientación
## Mapa de lectura
## Contraste con la biblioteca
## Cobertura

## Historial

- 2026-11-15 · pendiente · preparada por agent: reader
```

Stdin holds the four sections, in that order, starting at the first heading; the
helper adds the frontmatter, title, source link, notice and history. Labels follow
`language`. Preparation and the writer both refuse: a target outside `layers.proposals`
or inside a numbered scope; a source that is not the existing Markdown wrapper of a
capture inside `layers.sources`, or whose bytes changed since preparation; a second
open item for the same source; any status but `pending`; `role`, `maturity`, `review`,
`proposal_status` or any other key; `origin: owner`; a missing, extra or reordered
`##` section; an empty orientation or coverage; an `![embed]` or an HTML element such
as `<img>`, so that opening an unreviewed file loads nothing; and more than 32 KiB. `conversation`
is optional. The source is bound by hash in the packet and the private record, not in
the file.

```sh
python3 scripts/library.py --config /private.json ingest-queue
python3 scripts/library.py --config /private.json ingest-status --target Review/Inbox/ingesta-guia.md --status reading --progress "p. 45" --expected-sha256 <sha256> > /status.json
python3 scripts/note_write.py --config /private.json save --packet /status.json
```

`ingest-queue` is read-only and works under `read_only`: it lists the `pending` and
`reading` items (`--all` adds the closed ones) with their source, progress and the
`sha256` of the current file. `ingest-status` takes that hash, so a record is prepared
only on the version just read, and builds the same file with a new `ingest_status`,
an optional `progress`, and one more history line (`--note` adds one line to it, such
as the notes the owner kept). It moves `pending` or `reading` to `reading`, `reviewed`
or `withdrawn`. The writer recomputes that transition from the current bytes and
refuses any packet that differs from it by one byte, so a status record cannot carry
a change to the analysis, the source, the origin or earlier history; it reports
`ingest_status_recorded` and keeps the previous bytes in a private record like any
update. A frontmatter the helper cannot change line by line, a missing history and a
closed item are refused: those are reviewed updates.

An ordinary `proposal` update of an item, shown and decided like any other, may change
its analysis or status; the writer refuses one that drops the format, changes
`source`, `origin`, `conversation` or `created`, or removes or reorders history lines.
No deletion or rename is supplied. An Ingesta item is refused as `--evidence` for any
note, at preparation and at save: bind the captured source it points to.

The helper wraps what it is given. It cannot tell whether the analysis is accurate,
whether the coverage statement is true, which agent wrote it, or whether the owner
said what a status record states; it reads no library rules. Edits made outside the
helper remain possible, as for every plain file.

## Owner-authored seeds

An [owner-authored seed](review-contract.md#owner-authored-seeds) uses the ordinary
creation with one flag and no evidence:

```sh
python3 scripts/library.py --config /private.json proposal --create --owner-authored --target Wiki/Notes/idea.md < /draft.md > /seed.json
python3 scripts/note_write.py --config /private.json save --packet /seed.json
```

```markdown
---
role: note
maturity: seed
origin: owner
conversation: "session 2026-11-12"
---
# The idea, in the owner's words
```

The helper validates and adds nothing, so the bytes saved are the bytes the owner
reviewed: the draft must already declare `role: note`, `maturity: seed` and
`origin: owner`; `conversation` is optional, one line. The packet and the save
result carry `authorship: owner_declared_not_authenticated`; the operation stays
`create`, with the same absence binding, private record, no-clobber publication and
readback, and `plain_file_created`. It needs no rule or setting beyond `plain_files`.

Preparation and the writer both refuse: any other maturity or role, a draft in the
parked-proposal format, an existing target, a target inside `layers.sources` or
`layers.proposals` (compared by spelling and filesystem identity), a target outside
`layers.knowledge`/`layers.drafts` when either is declared, and any combination
with `--evidence`, `--park` or `--move-primary`. A note with evidence is an ordinary
creation; add `origin: owner` there only if it is true. Without the flag, creation
without evidence fails exactly as before. Afterwards an update that keeps the three
declarations needs no evidence; one that changes maturity or role, or drops
`origin: owner`, is refused unless it binds `--evidence`. That guard reads the note's
current frontmatter, so it also applies to an existing note that already declares
this exact shape, and it does not judge whether the bound evidence supports the text.

The flag and the frontmatter record an assertion. The helper cannot tell the
owner's idea from an agent's or a third party's text, cannot match the draft to
what was said, and reads no conversation. Edits outside the helper can add or
remove `origin: owner` like any other bytes.

A seed the owner states while reading a source says where it arose in its own text,
as a plain link with the pages (`Al leer [[Raw/Sources/guia]], pp. 13–15.`). That
locator is orientation for the reader, not an evidence binding: no field is added,
and promoting the seed later still binds the source as evidence.

One quiet cooperative writer; no atomic compare-and-swap, locks/fencing, signed
receipts, multi-file transaction or full crash journal. ACL/xattr/ownership beyond
mode is unverified. Keep recovery private with independent backup/retention.

Creation requires filesystem hard-link support; these mechanics do not establish
OS portability. In mixed folders, protect originals through exact per-file
`layers.sources` selections and local rules; no migration is required.
