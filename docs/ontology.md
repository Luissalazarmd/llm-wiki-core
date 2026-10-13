# Original ontology and read-only projection

[config/ontology.json](../config/ontology.json) is loaded and enforced by [scripts/knowledge.py](../scripts/knowledge.py). It is an original projection contract, NOT a replacement for the licensed engine's schema or an approval service. Do not inject these fields into managed upstream notes until canonical proposal/schema integration is separately implemented and tested. Existing upstream notes without stable IDs/with different schema can fail this projector; it is not a migration utility.

## Independent dimensions

- **Role:** source, concept, entity, map (MOC), project, diagram. Sources belong to Raw; other roles belong to the Wiki stage in a future canonical application. Test fixtures use invented Wiki files, not approved real knowledge.
- **Maturity:** seed (semilla), developing (en desarrollo), evergreen (maintained reusable explanation). Increasing maturity does not approve a note or guarantee truth.
- **Declared review:** unreviewed, pending, changes_requested, accepted, stale. These labels are permitted declarations only. The projector reports effective review `unverified` for any non-unreviewed declaration. Verified host decisions, hashes and receipts must determine actual review authority; this projector never does.
- Physical stage and grouping folder are separate from all three. A seed can legitimately be accepted in a verified future flow; a developed note may still need changes. The projection does not advance stages or states.

Property names are English and case-sensitive. Source captures also support upstream `Title` and `Reference`; new notes can use `title`. Conflicting case variants fail instead of guessing. Unused properties do not confer authority.

## Identity and versions

Use an opaque stable `id` for maintained notes and local captures. A public source with `Reference` can omit `id`: identity is `source:` followed by SHA-256 of the exact Reference UTF-8 string. No normalization/repair is performed. Explicit IDs are preserved exactly. Different versions of one source require distinct capture IDs and may share `Reference`; each file has its current full-byte `sha256`.

Repeated IDs fail. Moving a file preserves identity/hash but changes location. This does NOT fix older links, manifests, receipts or approvals; reconciling a live move is separately gated. Do not give indistinguishable copies different IDs to hide duplication.

## Minimal relationships

`relations` is a list of `{kind, target, reason, evidence?}`; target is a stable ID, not a path. Allowed kinds:

- `groups`: a reading/topic selection; not source agreement.
- `related`: a relevant connection, without factual support implied.
- `supported_by`: a factual claim tied to source evidence.
- `contradicts`: an explicitly described comparable disagreement.
- `extends`: a described development with source support.

Each has a nonempty reason and declaration path. The last three require at least one evidence anchor `{source, sha256, locator}` resolving to a captured source and exact hash. Locator truth/meaning must still be checked by the Bibliotecario: this validator only checks presence and version binding. All edges are displayed as unverified declarations. There is no independent edge database.

## Executed commands

Requires Python and PyYAML. Use an isolated environment or the authorized existing runtime; never install globally on a managed Python host. The original projection does not require the private engine. No dependency installation is automatic.

```sh
python3 scripts/knowledge.py --root /path/to/core
python3 scripts/knowledge.py --root /path/to/core --focus NOTE_ID --neighbors 8
python3 scripts/knowledge.py --root /path/to/core --focus NOTE_ID --format markdown
python3 scripts/knowledge.py --root /path/to/core --focus NOTE_ID --format markdown --language en
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_knowledge.py -v
```

The CLI writes stdout/stderr only: JSON catalog, bounded selection or optional Markdown view. Raw and Wiki are scanned recursively. Review is NOT parsed as ordinary knowledge: pending cases belong to the existing review adapter. Root directories are not added or moved.

Catalog limits: 2,000 Markdown notes, 256 KiB per note, 16 MiB total note bytes. Focus: one hop, default eight neighbors, at most 50, 16 KiB serialized context. Exceeding limits blocks; it does not silently truncate evidence. This implementation reads bounded files to compute hashes/metadata; “thin” means returned context excludes source bodies, not that indexing performs zero body I/O. Rebuilding per invocation is appropriate only for this bounded increment; large-library incremental indexing is not implemented.

Malformed/non-mapping/duplicate/aliased YAML, symlinks, unsafe wikilink paths, duplicate IDs, invalid state vocabulary, unresolved targets and stale evidence fail closed. The tool is cooperative read-only code, not a sandbox or a concurrency/approval snapshot. Do not run it on an actively edited/synced collection for authorization decisions. It has no server, credentials, model call, database or network operation.

Markdown views use existing wikilinks plus `Children` to group selected neighbors for K-Plex; typed edge meaning remains in the text, not equivalent to K-Plex's parent/child ontology. A view is disposable and carries no approval. Host rendering is not verified by syntax tests. Plain Markdown fallback works without a plugin; graphical host, voice and canonical accepted-state transport remain separate integration gates.
