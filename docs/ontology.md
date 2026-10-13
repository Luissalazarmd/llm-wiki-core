# Original ontology and read-only projection

[config/ontology.json](../config/ontology.json) is loaded and enforced by [scripts/knowledge.py](../scripts/knowledge.py). This is an original projection contract, not an approval service or a mandatory schema for every library. Do not inject fields into managed notes or alter their schema without the library's permitted review/write process. Foreign notes can fail strict mode; use scoped existing mode, not a migration to make the validator pass.

## Start with an existing library

For a first bounded map including attachment inventory, observed conventions and optional declared layer correspondence, use [first-cut tools](first-cut-tools.md). The adapter loads a single personal settings file for authorized paths/language and calls this module for read/focus/proposal. One-off explicit-root commands below remain available without persistent configuration. Neither interface is a host sandbox.

Default `--mode strict` enforces the ontology below on Raw/Wiki. For an unadapted library use `--mode existing` with explicit relative file/folder `--scope` selections. No required IDs, stages, role, maturity or review metadata; unknowns stay unknown. Paths become temporary `path:relative/file.md` locators, not new persistent identities. Existing or malformed frontmatter is not rewritten; parsing/ambiguous-link issues are returned separately. `rule_paths` lists existing regular non-symlink AGENTS.md files along the selected scope/note ancestor chains up to the library root, without reading their contents or scanning unrelated branches. `library_rules_path` is retained as the root-only compatibility field; `null` does not mean no nested rules. The tool does not execute these rules: the agent must discover/read applicable instructions before content, not use post-read indexing as a permission preflight.

```sh
python3 scripts/knowledge.py --root /path/to/library --mode existing --scope Reading
python3 scripts/knowledge.py --root /path/to/library --mode existing --scope Reading --focus 'path:Reading/one.md' --format markdown
python3 scripts/knowledge.py --root /path/to/library --proposal-target Reading/one.md --evidence Reading/two.md < /path/to/draft.md
```

Discovery limits: 200 selected Markdown notes, 256 KiB each, 16 MiB total. Hidden scopes, whole-root `.` selections, symlinks, unsafe link paths and parent escapes are rejected. Overlapping scopes deduplicate paths. A scope is a deliberate reading selection, not automatic permission to inspect everything inside it. No PDF, binary, external-link retrieval, alias resolution, semantic inference or automatic graph completion is implemented. Only explicit-path wikilinks resolving among selected notes become unverified navigation edges, for example `[[Reading/method]]` or `[[./method]]`. Basename-only links such as `[[method]]` produce `basename_link_requires_explicit_path`, even with one scoped match: an out-of-scope homonym may exist. They never become neighbors and do not trigger a broader scan. Unresolved explicit paths are reported, not fetched. Common inline/fenced code examples are excluded, not a complete Markdown parser. The existing mode does not translate custom fields into Core ontology.

Proposal preparation accepts an **existing Markdown target** and a UTF-8 draft from stdin, plus explicit existing evidence files. It returns original-byte base hash, draft, proposed diff, evidence hashes and a deterministic packet content hash to stdout. Changed bases during preparation fail; byte binding preserves CRLF. No directories/files are created. No source locators, claim checking, approval, signing, durable queue, locking, replay protection or atomic evidence snapshot is provided. A changed input produces a different packet; a hash is not a human decision. The host must verify evidence and concurrency again before any future apply. New-note proposals may be expressed by the agent but are not supported by this CLI packet helper.

## Independent dimensions

- **Role:** source, concept, entity, map (MOC), project, diagram. Sources belong to Raw; other roles belong to the Wiki stage in a future canonical application. Test fixtures use invented Wiki files, not approved real knowledge.
- **Maturity:** seed (semilla), developing (en desarrollo), evergreen (maintained reusable explanation). Increasing maturity does not approve a note or guarantee truth.
- **Declared review:** unreviewed, pending, changes_requested, accepted, stale. These labels are permitted declarations only. The projector reports effective review `unverified` for any non-unreviewed declaration. Verified host decisions, hashes and receipts must determine actual review authority; this projector never does.
- Physical stage and grouping folder are separate from all three. A seed can legitimately be accepted in a verified future flow; a developed note may still need changes. The projection does not advance stages or states.

Property names are English and case-sensitive. For metadata compatibility source captures also support `Title` and `Reference`; new notes can use `title`. These are data fields, not an engine dependency. Conflicting case variants fail instead of guessing. Unused properties do not confer authority.

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

The CLI writes stdout/stderr only: JSON catalog, bounded selection or optional Markdown view. In strict mode Raw and Wiki are scanned recursively; absence of both fails with guidance to use scoped `--mode existing`. An existing empty stage directory can legitimately yield an empty catalog. Review is NOT parsed as ordinary knowledge: pending proposals follow the library's existing review procedure. Root directories are not added or moved.

Catalog limits: 2,000 Markdown notes, 256 KiB per note, 16 MiB total note bytes. Focus: one hop, default eight neighbors, at most 50, 16 KiB serialized context. Exceeding limits blocks; it does not silently truncate evidence. This implementation reads bounded files to compute hashes/metadata; “thin” means returned context excludes source bodies, not that indexing performs zero body I/O. Rebuilding per invocation is appropriate only for this bounded increment; large-library incremental indexing is not implemented.

Malformed/non-mapping/duplicate/aliased YAML, symlinks, unsafe wikilink paths, duplicate IDs, invalid state vocabulary, unresolved targets and stale evidence fail closed. The tool is cooperative read-only code, not a sandbox or a concurrency/approval snapshot. Do not run it on an actively edited/synced collection for authorization decisions. It has no server, credentials, model call, database or network operation.

Markdown views use existing wikilinks plus `Children` to group selected neighbors for K-Plex; typed edge meaning remains in the text, not equivalent to K-Plex's parent/child ontology. A view is disposable and carries no approval. Host rendering is not verified by syntax tests. Plain Markdown fallback works without a plugin; graphical host, voice and canonical accepted-state transport remain separate integration gates.
