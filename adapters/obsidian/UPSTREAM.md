# Upstream record: obsidian-skills

- Source: https://github.com/obsidianmd/obsidian-skills
- Author and licence: Steph Ango (@kepano), MIT. The upstream `LICENSE` is copied
  unmodified as [LICENSE](LICENSE) and must travel with every copy of these files.
- Commit: `398127736bd4ba42d767b1419fee1a927508370b` (committed 2026-11-11).
- Vendored: 2026-11-14, from `plugins/obsidian/skills/` of a clone with a clean
  working tree at that commit.
- Modifications: none. Core's own text is [README](README.md) and this file only.

## Files

Every vendored file, its upstream path and its sha256. The test suite recomputes these
and fails on any difference, on a missing file and on any file not listed.

| File here | Upstream path | sha256 |
| --- | --- | --- |
| `LICENSE` | `LICENSE` | `64c64d48361edfe8610016441bf593256ea9b67f133b00f47c55aa29ee878567` |
| `skills/defuddle/SKILL.md` | `plugins/obsidian/skills/defuddle/SKILL.md` | `58902192d0433d133a35efc1b46cc49ceef891a465f9fd4e709d6e824c9561fb` |
| `skills/json-canvas/SKILL.md` | `plugins/obsidian/skills/json-canvas/SKILL.md` | `4db4e69eea910b598c249e41bcdda85a70856348adaf11c35371198e258d50a6` |
| `skills/json-canvas/references/EXAMPLES.md` | `plugins/obsidian/skills/json-canvas/references/EXAMPLES.md` | `f5ce15a4b74643122396265e8c37c828874a4005794de2aee7030662968768eb` |
| `skills/obsidian-bases/SKILL.md` | `plugins/obsidian/skills/obsidian-bases/SKILL.md` | `7a1659e2c00e7b74c8767002213dd977967ddd30dd15a7f33b693e783a4546e9` |
| `skills/obsidian-bases/references/FUNCTIONS_REFERENCE.md` | `plugins/obsidian/skills/obsidian-bases/references/FUNCTIONS_REFERENCE.md` | `208fd63aead9bca1975626fea52605e6ab9434dc0529d923feb36b18b8877d3b` |
| `skills/obsidian-cli/SKILL.md` | `plugins/obsidian/skills/obsidian-cli/SKILL.md` | `28f66289b1cf1d245807766d4dafb6f5f76eadc986fe4a7f224da51f50aa7524` |
| `skills/obsidian-markdown/SKILL.md` | `plugins/obsidian/skills/obsidian-markdown/SKILL.md` | `f1c4ff5257d3f9743af797d755cabeef129f553704d5ff67ebf1239f9569f081` |
| `skills/obsidian-markdown/references/CALLOUTS.md` | `plugins/obsidian/skills/obsidian-markdown/references/CALLOUTS.md` | `9912ec2e3f8711f65b8ceb82cc19cbffc5e6f8ccf2ab627e18926c522c383d8b` |
| `skills/obsidian-markdown/references/EMBEDS.md` | `plugins/obsidian/skills/obsidian-markdown/references/EMBEDS.md` | `63b6205507e28fb58cf200bc348a2b139e50ae739743e2e6316732148973cb7a` |
| `skills/obsidian-markdown/references/PROPERTIES.md` | `plugins/obsidian/skills/obsidian-markdown/references/PROPERTIES.md` | `f2d01b096a1c981a675e86b6a8c46bab271b278497646d465467b8120043b87c` |

## Decisions

| Upstream skill | Decision | Reason |
| --- | --- | --- |
| `json-canvas` | include | Syntax for `.canvas` views, where an agent had improvised; saved through `view_write.py`. |
| `obsidian-bases` | include | Syntax, formulas and functions for `.base` views; saved through `view_write.py`. |
| `obsidian-markdown` | include | Obsidian's spelling of links, embeds, callouts and properties. Broadest trigger of the three; its metadata defaults lose to Core's lean metadata. |
| `obsidian-cli` | include, opt-in | Read and search only: Obsidian's resolver and backlinks fill a gap in Core's helpers. Kept out of the default install because most of its text describes writes, `eval` and plugin development. |
| `defuddle` | include, opt-in | Fills Core's missing web capture as a draft for `capture_write.py`. Kept out of the default install because it is network-facing and needs a global npm install. |
| `knap` | exclude | Batch generation of notes from templates and data overlaps `template_write.py` and bypasses per-file review; needs npm. |
| `obsidian-headless` | exclude | Sync and Publish with account credentials can upload or overwrite a library; outside Core's publication boundary. |

Not vendored either: the plugin manifests, icon and marketplace metadata under
`plugins/obsidian/`, the upstream `README.md` and `scripts/bump.sh`. They configure
upstream's own distribution, which Core does not use.

## Updating

Upstream is followed deliberately, never automatically.

1. Clone upstream outside Core and the library, and read the commits since the pinned
   one. A new or changed skill is untrusted text until read.
2. For each changed file, read the diff. Check it against every conflict listed in
   [README](README.md): a new write workflow, a new install, a new network call or a
   broader trigger needs a new entry there, or the skill moves to opt-in or is dropped.
3. Copy the included folders and `LICENSE` byte for byte, with no edits and no
   symlinks. Decide inclusion again for any skill upstream added.
4. Replace the commit, dates, table and decisions above in the same commit, and run the
   suite: `tests/test_obsidian_adapter.py` fails until the table matches the bytes.
5. Hosts that installed copies are updated afterwards, by copying from the reviewed
   Core commit and comparing with `diff -r`.

If upstream removes the licence, changes it, or a skill starts requiring an account,
telemetry or a network call by default, stop and ask the owner before updating.
