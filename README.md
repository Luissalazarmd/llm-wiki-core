# llm-wiki-core

One private project for the Bibliotecario, Orquestador and your Markdown Wiki. Open this same core folder in Obsidian; you do not need a second template or instance repository.

**Current status:** a local licensed-engine installer, read-only review CLI and tested synthetic canonical flow are implemented. The private engine is installed into this folder from authorized local files; its code is not redistributed by this repository. Authenticated chat approval and autonomous semantic synthesis are not connected yet.

## Install into this same folder

From the cloned core project, with the authorized engine files already available locally:

```bash
python3 scripts/install_private_engine.py --source /path/to/authorized-engine --root .
python3 adapters/review_chat.py --root . list
python3 adapters/review_chat.py --root . show CASE_ID
python3 adapters/review_chat.py --root . packet CASE_ID
```

The installer verifies the pinned source hashes and preserves existing differing files instead of overwriting them. It never downloads, runs the source, migrates another vault, pushes or uploads anything. Use `--check` for a read-only preview. A source folder is a one-time installation input, not a second project you must maintain.

The generated local settings start review-first, with automatic Git checkpoints, memory providers and external model processing disabled. Existing local settings are preserved. This is an engine/API installation, not the complete upstream graphical/bootstrap kit.

## One folder, explicit Git policy

- `Raw/`: your captured sources and their provenance
- `Review/`: proposals and readable review material
- `Wiki/`: approved canonical Markdown
- `Agents/` and `Librarian Profile.md`: the two role contracts and canonical librarian profile
- `adapters/`, `scripts/install_private_engine.py`, `tests/`, `config/`, `docs/`: original project code and contracts
- `scripts/librarian/`, support packages, `_templates/`, selected `Schema/` files and `LICENSE`: licensed engine installed locally into this same core folder
- `.wanderloots-llm-wiki/`: private operational state, requiring deliberate backup

Original code is versionable in the core repository. Vendor files, local settings and operational state are excluded from publication by default. Raw/Review/Wiki are **not** blanket-ignored: selected knowledge can be versioned in this same private GitHub repository when you choose what to publish. A private repository does not remove source-license, personal-data or credential constraints. No upload is automatic; review staged files before every publication. Secrets always belong in a secret store.

## Workflow

Raw → Review → Wiki. Bibliotecario prepares source-grounded proposals; Orquestador presents them. An authenticated human decision is required before enabling real-content canonical apply. The read-only CLI provides list/show/packet now and never approves anything.

The isolated single-folder smoke test passes 35 checks, including canonical simulated apply, stale blocking, receipts, replay and recovery. Nine installer tests cover integrity, conflicts, repeat installation and Git exclusions. These are synthetic results, not a claim that the authenticated chat host is ready.

See [local integration](docs/local-integration.md) for commands and limits, [onboarding](docs/onboarding.md) for setup choices, [review contract](docs/review-contract.md) for authority, and [acceptance](docs/acceptance.md) for the broader unfinished gates. Agents start with [AGENTS.md](AGENTS.md).

## Language

Internal agent instructions are English. Replies follow the user's language. Wiki prose defaults to Spanish; original titles, citations and quotations retain their wording. Current upstream structural headings are preserved.
