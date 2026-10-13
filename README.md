# llm-wiki-core

An agent-guided, Markdown-first knowledge workflow. Bring a capable agent and a new or existing library: read, connect, navigate and prepare proposals without a private engine or metadata migration. Core supplies contracts and optional tools, not an autonomous bot, model or file-access permission.

**Essential status:** guided role contract, scoped library mapper (notes, attachments and conventions), executable personal settings, strict optional ontology, bounded navigation and content-bound proposal preparation work without the private engine. They are read-only; authenticated approval and canonical application remain unconnected.

The [guided contract](docs/knowledge-workflow.md) makes the Bibliotecario the human-facing guide. The library can remain outside this checkout; its existing rules and organization are preserved. No new vault, mandatory thematic folders or duplicated knowledge. The Core repository is public; personal libraries remain separate and private. Public visibility is not a redistribution license, and technical independence of essential tools does not settle redistribution rights.

## Start with your agent

Tell your capable agent: **“Read Core's AGENTS.md. My library is at [path]; follow its existing rules. Help me understand [source/question], selecting only relevant notes. Do not move or modify my library yet.”** If the path cannot be retrieved, ask for it; never assume the checkout is the user's vault. Commands are for the agent, not the human. Interoperability with every host is not certified by this prompt.

For original-code validation without vendor installation (Python plus pinned PyYAML in requirements.txt):

```sh
python3 scripts/knowledge.py --root /path/to/library --mode existing --scope Reading
python3 scripts/knowledge.py --root /path/to/library --mode existing --scope Reading --focus 'path:Reading/one.md' --format markdown
python3 scripts/knowledge.py --root /path/to/library --proposal-target Reading/one.md --evidence Reading/two.md < /path/to/draft.md
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 tests/demo_existing_library.py --output-parent /path/to/authorized/scratch
# Only for the intentionally empty Core Raw/Wiki placeholders, not a library census:
python3 scripts/knowledge.py --root . --mode strict --allow-empty-strict
```

Start an existing library with the scoped existing-mode command above. Strict mode projects only a known Raw/Wiki layout, not the whole library; it never scans unrelated folders to check for hidden knowledge. Missing stages or zero stage notes fail with guidance to scoped `--mode existing`. Only an intentionally empty stage projection may use explicit `--allow-empty-strict`; that result says nothing about other folders. Existing mode requires explicit scopes and reads Markdown without mandatory metadata. CRLF frontmatter is parsed while original bytes/hashes are preserved. Missing maturity remains unknown in either mode; no seed label is fabricated. Basename-only wikilinks are reported as unresolved candidates, never automatic neighbors; explicit paths resolve only among selected notes. No wider scan is performed to find homonyms. Path locators are temporary, not persistent IDs. Proposal drafts come from stdin; JSON/diffs go to stdout, never apply. See [ontology](docs/ontology.md) and [current evidence](docs/self-contained-increment.md).

For repeated use, [first-cut tools](docs/first-cut-tools.md) load **one private personal config** (library root, authorized paths, objectives, language, organization, initiative and optional declared layer correspondence), separate from the shared profile. Mapping observes selected folders/notes/attachments without decoding attachments or inferring review states; missing layer correspondence remains unassigned. No auto-created settings, migration or mandatory persistent configuration for one-off reading.

## Existing library or new instance

Keep an existing library at its current location. Do not copy content into Core or overwrite its rules. Raw → Review → Wiki describes source inputs, reviewable elaboration and retained knowledge, not mandatory directory names. The stage placeholders are an optional starting layout for a new library; existing libraries retain their own paths. Core ships no vendor installer, source manifest or vendor adapter.

- `Raw/`: your captured sources and their provenance
- `Review/`: proposals and readable review material
- `Wiki/`: approved canonical Markdown
- `Agents/` and `Librarian Profile.md`: the two role contracts and canonical librarian profile
- `skills/`: three portable action procedures, not additional bots
- `scripts/`, `tests/`, `config/`, `docs/`: original tools, tests and contracts

Original code and synthetic fixtures are versionable in this public Core repository. Vendor files, local settings and operational state are excluded from publication by default. Raw/Review/Wiki are **not** blanket-ignored, so never place private knowledge in this checkout by assuming Git will exclude it. Keep personal libraries elsewhere; any selected knowledge publication requires separate explicit approval and source-rights/privacy review. No upload is automatic; review staged files before every publication. Secrets always belong in a secret store.

## Workflow

### Librarian skills — local v0.1

Portable procedures now exist for [read/connect](skills/read-connect/SKILL.md), [capture](skills/capture-source/SKILL.md) and [review/save](skills/review-save/SKILL.md). They use the person's existing agent and tools, not separate bots. An optional [plain-note helper](docs/plain-saving.md) checks exact proposals and evidence, updates one derived note with recoverable previous bytes or creates a new derived note without overwriting an existing destination. New-note proposals use `--create` before any library write; actual confirmation is still required. Restore protects later edits and does not delete created notes. Managed libraries still require their canonical writer; default is read-only. No authenticated-host implementation is claimed.

AGENTS links all three skills progressively. They are portable files read by the agent, not automatically installed host plugins. Actual source capture uses existing permitted host tools; no capture runtime is bundled. This is a pilot checkpoint, not a tagged GitHub release; independent-agent portability, graphical rendering and managed authenticated-host integration remain separate gates. See [verification and limits](docs/self-contained-increment.md).

New Raw captures must be connected at admission: **existing MOC → valid acyclic hierarchy → declared root index**, plus nonempty tags from the library's declared taxonomy. [Raw admission](docs/raw-admission.md) provides a small read-only preflight/recheck/saved-byte checker. Missing classification stops at the draft; no automatic map creation, tag invention, source rewriting or vault migration. The checker is not a capture writer, authentication service or semantic quality score.

Bibliotecario guides capture, selected reading, connections and human review. Core's tools are small helpers beneath that experience. Saving follows actual library rules and host permissions; missing capabilities stop dependent writes, not reading. No engine migration, new authentication service or promise of canonical apply is implied.

Knowledge develops as **Semilla → Síntesis → Evergreen** (`seed`, `developing`, `evergreen`). The profile and read/connect/review skills follow [idea emergence](docs/knowledge-workflow.md#idea-emergence): explain the new argument, trace it to selected ideas and original evidence, examine tensions and justify any maturity change for actual review. MOC membership and link counts do not promote ideas. Raw stays original; articles are a separate author-led use, not a maturity level or implicit publication permission. Spanish views display the agreed labels; unknown foreign maturity stays unknown. This is an agent procedure, not an automatic semantic engine.

All product tests run on synthetic files without a specific library engine, private source files or skipped vendor suite. [Writer selection](docs/review-contract.md) respects the existing library's permitted tools: explicitly editable plain files or an independently supplied managed writer. Core does not implement that writer's authentication or concurrency guarantees. Absence of a managed marker is not permission. See [runtime](docs/runtime.md), [onboarding](docs/onboarding.md), [acceptance](docs/acceptance.md) and [current evidence](docs/self-contained-increment.md). Agents start with [AGENTS.md](AGENTS.md).

## Daily Focus

Ask the Orquestador “¿En qué me enfoco hoy?” for up to three sourced next actions. The [Daily Focus contract](Agents/daily-focus.md) uses confirmed principles, dated current priorities, and whichever task/calendar sources you choose. It runs only on request through a capable host; no background agent, connector, scheduler or new model is installed by these files. Personal context stays separate from bibliography.

## Language

Internal agent instructions are English. Replies follow the user's language. Wiki prose defaults to Spanish; original titles, citations and quotations retain their wording. Preserve the existing library's conventions rather than imposing a vendor layout.
