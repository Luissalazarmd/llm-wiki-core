# llm-wiki-core

Read with purpose. Connect ideas. Keep what matters.

Core gives your existing agent four reusable workflows: adopt selected material,
read and connect ideas, capture sources, and review/save useful knowledge.
It combines Markdown instructions, synthetic examples and optional Python helpers.
Bring an existing library, collected articles, your own drafts or a first question;
no dedicated agent service, migration or plugin is required.

People: start with [onboarding](docs/onboarding.md). Agents: read
[AGENTS.md](AGENTS.md) first. Supply one starting point:
your library, an article, an authored draft or a question. Keep material where it
is. The Bibliotecario handles permitted technical work; you think, correct and approve.

Ask: “Start read-only; help me understand this question. Reuse existing explanations.
Before saving, show the complete proposed content or exact diff and readable result.”

[Adopt](skills/progressive-adoption/SKILL.md) · [Workflow](docs/knowledge-workflow.md) · [Onboarding](docs/onboarding.md) ·
[Tools](docs/first-cut-tools.md) · [Starter library](docs/starter-library.md) · [Obsidian example](examples/obsidian/README.md)

Obsidian can provide the reading workspace: Bases shows inventories, Canvas shows
the architecture, and optional [K-Plex](https://github.com/zsviczian/kplex) provides contextual knowledge navigation.
The example includes settings references, not plugin installers. Ordinary Markdown
remains usable without those interfaces; graph connections do not validate claims.

Status: early pilot. Exercised on Linux; in other environments your agent checks the [requirements](docs/agent-preflight.md#requirements).

Obtain Core from [GitHub](https://github.com/Luissalazarmd/llm-wiki-core), keeping your
private library separate. See [getting and updating Core](docs/onboarding.md#get-and-update-core)
and [storage, sync and backups](docs/sync.md) before choosing online storage.

Current synthetic checks: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`;
see [acceptance and limits](docs/acceptance.md).

Passing checks and native observations are not proof of scientific validity, human
approval or universal compatibility; see [acceptance](docs/acceptance.md).

Core code, documentation and bundled synthetic examples are covered by the
[MIT License](LICENSE). Using Core does not license or publish private user
libraries, sources, credentials, settings or recovery records. Third-party
dependencies retain their own licenses.

The optional Python helper below needs its dependencies (see [tools](docs/first-cut-tools.md)),
but scoped reading through authorized host tools needs no configuration:

```sh
python3 scripts/knowledge.py --root /path/to/library --mode existing --scope Notes/selected.md
```
