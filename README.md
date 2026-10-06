# llm-wiki-core

Private, agent-first baseline for an Obsidian-readable Markdown knowledge system.

For humans: this repository defines the contracts and setup decisions for two agents. It does not yet automate your vault. For agents: start with [AGENTS.md](AGENTS.md), then run the [operational preflight](docs/agent-preflight.md) before proposing work.

**Status: v0.1 documentation scaffold. This is not a runnable engine.** No ingestion, review CLI, approval service, connectors, synchronization service, or canonical apply implementation is bundled. The empty content directories contain only Git placeholders, not compiled notes. No personal vault, source collection, identities, chat history, or credentials are included.

## v0.1 scope

- **Bibliotecario**: evidence intake, provenance, synthesis proposals, and maintenance proposals.
- **Orquestador**: explicit user intent, planning, routing, review presentation, and authorized coordination.
- Pipeline: **Raw → Review → Wiki**. Agents propose; an authenticated human approves an exact proposal revision; a single canonical writer applies it.
- Obsidian is the reading/editing interface, not the authority that authenticates approvals or runs the engine.
- Personal memory and bibliography remain separate information classes.

No additional specialist roles are included in v0.1. Task and calendar applications are onboarding choices, not required dependencies.

## Start here

1. Read [onboarding](docs/onboarding.md) and select an isolated private instance and one sync method.
2. Review the [architecture](docs/architecture.md), [agent contracts](Agents/README.md), and [review contract](docs/review-contract.md).
3. Use [config/example.json](config/example.json) as an inert questionnaire. There is currently no config loader.
4. Follow the [implementation milestones](docs/implementation.md) before expecting executable behavior.

The current repository may be opened as an Obsidian vault to read these documents. Do not import personal information into the template repository. Provision a distinct private instance before actual use.

## Layout

- `Raw/`: immutable or versioned intake in a future private instance.
- `Review/`: proposed changes and human-readable review packets in that instance.
- `Wiki/`: approved canonical Markdown in that instance.
- `Librarian Profile.md`: the single canonical Bibliotecario profile.
- `Agents/`: role contracts, Orquestador profile, and Bibliotecario profile pointer; not an executable runtime.
- `config/`: sanitized configuration example.
- `docs/`: onboarding, architecture, review, sync, runtime, and acceptance design.
- `AGENTS.md`: contributor and automation boundaries.

Retain these root names and casing. The upstream root layout also reserves `Schema/`, `scripts/`, `rail/`, `automation/`, `_templates/`, `.agents/`, and `.wanderloots-llm-wiki/` (including bootstrap and durable internals). These engine-owned paths are documented, not populated with fake runtime files. Their exact contents and compatibility still require licensed integration review.

## Engine and rights boundary

The intended upstream is the private Wanderloots 2.0.5 engine. It is **not bundled**. No upstream source, scripts, vault content, or LICENSE text has been copied. Integration requires an authorized source review, an exact revision, compatibility verification, and preservation of the upstream private-use license and notices. See [upstream boundary](docs/upstream.md). Do not publish this baseline or imported dependencies as open source without a separate rights review.

See [acceptance specification](docs/acceptance.md) for required synthetic tests. Those are requirements, **not passing test results**.

## Language defaults

Agent instructions are in English. User-facing replies follow the user’s language. Generated Wiki notes default to Spanish (`wiki_language: es`) unless the user selects another language. Source titles, citations, and original quotations retain their original wording; translations are labeled.
