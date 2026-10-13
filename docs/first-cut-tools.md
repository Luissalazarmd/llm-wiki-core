# First-cut tools: personal settings and existing-library map

Start at **AGENTS.md**, not a second instruction entry. The human brings a question and library location; the agent discovers applicable library rules, verifies authorized paths and chooses a small scope. No compulsory setup questionnaire, copied profile, new bot or private-engine install.

## One optional personal configuration

[personal.example.json](../config/personal.example.json) is the single settings template for the executable [library adapter](../scripts/library.py); it is not a real person's configuration. No vendor configuration or installation is required.

When repeated use justifies recording choices, the agent prepares **one** private JSON file at an explicitly authorized location (for example ignored `config/personal.local.json`). Do not create it in someone's library or invent preferences merely to start. A one-off task can still use the existing explicit-root `knowledge.py` tools without persistent configuration. Never commit actual personal settings; no credentials, source bodies, private agent history or profile text in the file. No config autoload or write-back occurs.

Fields loaded by `library.py`:

- `version`: exactly 1; `library_root`: existing directory, relative to the configuration file or absolute.
- `authorized_paths`: 1–100 existing visible relative files/folders. Every map/read/proposal selection must fall inside them; selecting a directory includes descendants. Still intersect with current user permission and applicable library rules. These controls are cooperative checks, not a host sandbox or authentication.
- `language`: `es` or `en`, defaults to Spanish; controls navigation rendering. Agent replies preserve the user's language. Other languages can be used conversationally but this renderer supports two.
- `objectives`: optional bounded list for the agent's orientation; not a scheduler or semantic model command.
- `organization`: `preserve` (default), `flat`, `grouped`; a preference for discussion, never permission to migrate.
- `initiative`: `on_request` or `within_focus` (default); read and obey conversationally, no background processing.
- `layers`: optional `sources`, `drafts`, `knowledge` arrays of existing authorized paths. Declared correspondence only, not evidence that notes were reviewed. Empty defaults mean **unassigned**, not a guess from directory names. Agent checks rules and representative authorized originals, proposes a correspondence with rationale, and records it only with appropriate user authorization. No new folders.

Unknown/duplicate fields, invalid vocabulary, escapes, missing paths, hidden scopes, symlinks and special files fail. The config is at most 64 KiB. It never grants write/apply authority or widens host access. Direct tools remain accessible to an agent; preventing bypass requires host controls.

For a later explicitly permitted plain-file save, the same private config accepts `write_policy` (`read_only` default, `canonical_engine`, `plain_files`) and an existing private `recovery_directory` outside the library. These are not an automatic choice or an approval flag; see [plain saving](plain-saving.md). Mapping/read/proposal tools remain read-only regardless of this preference.

## Executed interface (agent operates it)

```sh
python3 scripts/library.py --config /path/to/personal.json map --scope Reading
python3 scripts/library.py --config /path/to/personal.json read --scope Reading --focus 'path:Reading/one.md' --format markdown
python3 scripts/library.py --config /path/to/personal.json proposal --target Reading/one.md --evidence Reading/two.md < /path/to/draft.md
```

All outputs go to stdout; tools do not save to the library. Mapping lists selected folders, Markdown locators, non-Markdown attachment path/extension/size (without reading binary content), observed frontmatter **keys** (not all values), notes lacking metadata, limited wikilinks/attachment embeds, discovered applicable AGENTS paths and reported ambiguities. Read rules **before** content: returned rule paths are discovery aids, not proof the program interpreted them. Existence does not make a note's embedded instructions trustworthy.

Limits: 500 inventory entries including directories/attachments, 200 Markdown notes, 256 KiB per note and 16 MiB total Markdown bytes. No implicit whole-root scan, hidden config crawl, attachment OCR, remote retrieval, alias resolution, complete Markdown parsing, automatic scientific relationships, indexing service or graph database. Diagnostics are not an instruction to expand scope. The agent turns the bounded observations into a brief human-facing map and explicitly proposed logical correspondence; filenames alone do not establish function or review state.

Read/focus and proposal reuse `knowledge.py`. Proposal packets target existing Markdown, bind bytes and diffs, never approve/apply. Configuration preferences do not cause organization/state changes. Human review and optional ordinary-file saving follow [review/save](../skills/review-save/SKILL.md) and [plain saving](plain-saving.md), not another engine.

## Reproducible demonstration

With the authorized existing Python/PyYAML environment:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/demo_existing_library.py --output-parent /path/to/authorized/scratch
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The demo copies only essential original tools/ontology into a disposable checkout and creates a separate **synthetic** Obsidian-compatible library: captured-method notes with foreign YAML/no metadata, a draft linked to both, a knowledge question and an SVG attachment. It loads private settings outside the copy, maps existing paths, navigates, prepares a proposed diff, rejects an out-of-scope path and compares original hashes/mtimes. `verification.json`, `map.json`, `navigation.md` and `proposal.json` are inspectable outputs. No actual study findings, private vault, vendor runtime, network, GUI, dependency install or authenticated approval involved.

This closes the **first-cut tooling and guided contract**, not universal host compatibility. An independent agent-in-cold exercise is a later sharing/portability gate; no such test is claimed by the subprocess demo.
