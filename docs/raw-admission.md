# Raw admission: connected at first capture

Every **new** Raw capture guided by Core must carry an explicit link to an existing MOC, a valid ancestor chain to a declared root index, and at least one tag from the library's declared taxonomy. This is organization, not scientific support or accepted review state. Reuse existing maps; no automatic new MOC, hierarchy, folder or tag just to pass a check. If classification is uncertain, explain it and retain a draft outside admitted Raw until resolved.

This rule applies to new capture, not read-only discovery of existing libraries. Do not retrofit or rewrite old sources, migrate a vault or replace a managed writer. The actual library's instructions still govern; incompatible or missing capability blocks this capture, not independent reading. The host operates the checks, not the person.

## One private policy, existing notes

Add `capture_policy` to the existing optional personal config only with permission. Also declare the authorized source location in `layers.sources`; every referenced map/root/taxonomy must be within `authorized_paths`.

Example policy fragment (fictional paths, not a complete config):

```json
{
  "capture_policy": {
    "roots": ["Maps/home.md"],
    "taxonomy_path": "Rules/taxonomy.md"
  }
}
```

Default declaration fields:

- Raw draft: `moc: Maps/topic.md`, `tags: [methods]` alongside the library's actual source identity/provenance fields.
- Topic MOC: `role: map`, `parent: Maps/home.md`.
- Root index: `role: map`, no `parent`, with its exact path explicitly listed in policy `roots`.
- Taxonomy note: `tags: [methods, another-existing-tag]` listing the allowed vocabulary.

These are declarations in existing authorized Markdown, not a separate registry. All paths are exact library-relative paths ending in `.md`, not basename-only links or inferred folders. A root may itself be the direct MOC. Nonroot maps have a single organizational parent; cycles, missing parents and chains longer than 32 nodes are rejected. This hierarchy does not prohibit additional topical links, multiple reading routes or shared source use across projects.

For an existing compatible schema, optional `fields` maps `moc`, `parent`, `role`, `tags`, `taxonomy_tags` to its existing property names (for example `MOC`, `Parent`, `type`, `labels`, `allowed`). The map role value remains exactly `map`; links are exact paths, not automatically decoded plugin syntax. Do not rewrite foreign notes to satisfy these defaults. Unsupported schema requires an explicitly reviewed adaptation or the library's verified equivalent validator; no speculative conversion.

## Check before, recheck, capture, read back

[The small read-only checker](../scripts/capture_check.py) reads the supplied Raw draft from stdin and only its explicit MOC ancestor chain and taxonomy. It never captures, creates, modifies a map, authenticates consent or executes instructions found in notes.

```sh
python3 scripts/capture_check.py --config /path/to/personal.json --target Inputs/new-source.md < /path/to/capture-draft.md
# Preserve the returned check_sha256 privately; show the actual draft/classification for review.
python3 scripts/capture_check.py --config /path/to/personal.json --target Inputs/new-source.md --expected-sha256 CHECK_HASH < /path/to/capture-draft.md
# Only then use the actual permitted capture writer, preserving the same draft bytes and refusing overwrite.
python3 scripts/capture_check.py --config /path/to/personal.json --target Inputs/new-source.md --saved --expected-sha256 CHECK_HASH < /path/to/capture-draft.md
```

Check verifies absence of the destination, authorized existing source parent, actual MOC/map roles, acyclic chain to a configured parentless root, and distinct nonempty tags contained in the declared vocabulary. It binds draft, target, hierarchy/taxonomy file hashes and policy in a reproducible content hash. Recheck rejects changed inputs. Saved verification additionally requires exact target bytes; neither status says scientifically accepted or authenticated. If the permitted writer changes capture bytes or dependencies, obtain a newly reviewed check rather than passing an old receipt as valid.

The capture skill must keep the same verified metadata with the Raw capture; a sidecar alone does not meet this contract. Source identity, Reference/version duplicate checks, rights, provenance, quote fidelity, semantic tag relevance and applicable templates remain required separate checks. This checker does not claim global Reference uniqueness or validate source content.

## Navigation and limits

The required connection is **Raw → MOC → ancestors → root**. A forward root-to-Raw listing is a distinct surface: use the library's existing backlinks/query navigation or propose the corresponding MOC source link through its permitted review writer. Do not mutate Raw later just to maintain inverse links. This checker proves the outgoing organizational route, not universal plugin rendering or bidirectional index completeness.

Up to 32 map nodes, 256 KiB each, plus one 256 KiB taxonomy; Raw draft at most 256 KiB, 1–50 distinct tags, taxonomy at most 1,000 distinct labels. No whole-vault scan. Source and map paths are scoped, regular and non-symlink. CRLF is normalized only for parsing; all version and saved-byte binding uses original bytes.

A skill/checker is not a filesystem access barrier. An unrestricted host can bypass it; no source-capture runtime, multi-file transaction, authenticated review, snapshot/locking guarantee or adversarial concurrency protection is added. Pause concurrent editing/sync. A successful preflight is not proof a source was captured: actual writer result and exact readback are mandatory. Missing policy/root/taxonomy/MOC/tag means draft/proposal only; never report an unlinked capture as complete.
