# Any agent, any host

A library that follows Core says so in its own rules, so every agent that opens it
(Hermes, Claude Code, Codex, Cursor, Copilot, Gemini CLI or a cloud agent that sees only
a Git clone) reaches the same method and the same writers. Nothing here is specific to
one host, and nothing private is written into the library.

## The declaration

The library's root `AGENTS.md` carries a `## LLM Wiki Core` section, as the
[starter rules](../examples/starter-library/AGENTS.md) do. Three lines are read by
`doctor.py`; the rest is prose for the agent:

```markdown
- Core: https://github.com/Luissalazarmd/llm-wiki-core
- Core commit: unpinned
- Library id: biblioteca
```

- `Core` is the public address of the method and tools.
- `Core commit` is a full 40-character commit, or `unpinned`. Pin it before the library
  is shared or kept in Git: `git -C "$CORE" rev-parse HEAD` gives the value. A ZIP
  download cannot be checked against a commit, so it works only while `unpinned`.
- `Library id` is a short name the owner chooses (lowercase letters, digits, hyphens),
  unique among that person's libraries. It names the private file below and reveals
  nothing else.

The section is rules text: the owner writes it, and an agent never edits it. The
writers read no rules; only `doctor.py` reads this section.

## Where Core and the settings are found

Private paths stay on each machine. Each value is looked up on its own, first match wins:

1. `doctor.py --config /path/settings.json` (settings only), for a host that already holds the path;
2. the environment variables `LLM_WIKI_CORE` and `LLM_WIKI_SETTINGS`;
3. the owner's file `${XDG_CONFIG_HOME:-~/.config}/llm-wiki-core/<Library id>.json`:

```json
{"version": 1, "core": "/absolute/path/to/core", "settings": "/absolute/path/to/library.json"}
```

The [private settings](first-cut-tools.md) and the recovery directory are unchanged:
they live outside the library, outside its Git repository and outside Core. On another
machine the owner clones the library, gets Core at the pinned commit and writes these
two private files again; nothing is copied from the repository. With `CORE`, `PRIVATE`
and `ID` set as in the [starter setup](starter-library.md#one-authorization):

```sh
dir="${XDG_CONFIG_HOME:-$HOME/.config}/llm-wiki-core"
mkdir -p "$dir" && chmod 700 "$dir"
python3 -c 'import json, sys; print(json.dumps({"version": 1, "core": sys.argv[1], "settings": sys.argv[2]}))' "$CORE" "$PRIVATE/library.json" > "$dir/$ID.json"
python3 "$CORE/scripts/doctor.py" --library "$PRIVATE/library"
```

## The doctor

`python3 scripts/doctor.py --library /path/to/library` changes nothing. It reports the
declaration, the commit and cleanliness of the install it runs from, how Core and the
settings were located, the write policy, the host bridges and one of two modes:

- `write`: the rules declare Core, this install is the located one and (when pinned) is
  exactly that commit with no local change, and valid `plain_files` settings for this
  very library were found with recovery outside the library and its repository. The
  writers may run. Every write still needs the decision the library rules require.
- `proposal_only`: anything else. `blocked_by` names each reason. The agent changes
  nothing in the library, gives proposals in the conversation and says what is missing.

Without a pin, `core_commit_not_pinned` is a warning and any Core version passes. The
report names private paths: keep it out of the library, commits and shared messages.
The doctor runs from the install it inspects, so a host that must not trust that
install checks it independently first (`git -C "$CORE" rev-parse HEAD`,
`git -C "$CORE" status --porcelain --ignored`).

## An agent that sees only the repository

A cloud agent or a fresh clone has the rules but no settings, no recovery and perhaps
no Core. It is in `proposal_only` mode by definition:

- It reads the library with its own tools, within the scope the person selects.
- If its environment allows network access, it may fetch Core from the declared address
  at the declared commit, outside the library, to read the method and run the read-only
  helpers (`knowledge.py --mode existing`, `doctor.py`). Fetching is not installing for
  the owner and never makes it a writer.
- It never edits, creates, moves or deletes anything under Raw, Review, Wiki, templates
  or views, and commits nothing. Proposals stay in the conversation with their exact text.

It does not write settings for itself: settings and recovery are the owner's, per
machine. A save from such an agent would leave its recovery copy in a place that
disappears with the session, and its only record of the owner's decision would be a
commit, which [authenticates no consent](review-contract.md).

## Host bridges

The rules are `AGENTS.md`. A host that reads another file gets a one-line bridge that
imports it; a bridge with any other text is a second rules file, and `doctor.py` reports
it. Bridges are instruction files: the owner owns them and the writers refuse to write them.

| Host | Reads | Bridge in the starter |
| --- | --- | --- |
| Codex | `AGENTS.md` from the project root down to the working directory, 32 KiB combined by default ([docs](https://developers.openai.com/codex/guides/agents-md)) | none needed |
| Cursor | `AGENTS.md` in the project root and subdirectories ([docs](https://cursor.com/docs/context/rules)) | none needed |
| GitHub Copilot | `AGENTS.md` anywhere in the repository; alternatively one root `CLAUDE.md` or `GEMINI.md` ([docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)) | none needed |
| Claude Code | `CLAUDE.md`; since v2.1.277 `AGENTS.md` when no `CLAUDE.md` exists; `@path` imports ([docs](https://code.claude.com/docs/en/memory#agents-md)) | `CLAUDE.md` containing `@AGENTS.md`, for older versions and sessions that cannot read `AGENTS.md` |
| Gemini CLI | `GEMINI.md` unless `context.fileName` is changed; `@./file.md` imports ([docs](https://geminicli.com/docs/cli/gemini-md/)) | `GEMINI.md` containing `@./AGENTS.md` |
| Hermes | not verified here; the profile's own librarian skill points to the library | none |

Read on 2026-11-15; hosts change, so check the linked page when one misbehaves. The
bridges themselves were not exercised in Gemini CLI, Cursor or Copilot.

## Core's four actions as host skills

[`skills/`](../skills) holds four `SKILL.md` folders with `name` and `description`
frontmatter, which Claude Code, Codex and Hermes all accept. With the owner's
authorization for that host:

1. Copy the four folders as regular files from the pinned Core commit into the host's
   user-level skills directory: `~/.claude/skills/` (Claude Code), `~/.agents/skills/`
   (Codex), or the profile's skills directory (Hermes). Never symlink them, and never
   point a host's external skills directory at the Core checkout: a host must not load
   whatever lands there on update, and some hosts patch external skills in place.
2. Do not copy them into the library. They are Core's text, not the owner's knowledge.
3. A copied skill keeps its relative links. They resolve from `skills/<name>/` inside
   the Core install; each skill says so in its first line.
4. After every Core update compare the copies (`diff -r "$CORE/skills" <host skills>`)
   and replace them only from the reviewed commit.

The frontmatter also carries `version` and `author`. Claude Code ignores keys it does
not know; Codex documents only that `name` and `description` are required; an upload to
claude.ai or the Skills API rejects unknown keys, so those copies are for local hosts.
Skill triggering has not been exercised in any host. The
[Obsidian skills](../adapters/obsidian/README.md#installing-in-a-host) install the same way.

## A library kept in Git

- The repository root is the library root. Settings, recovery, the user configuration
  file and Core stay outside it; the starter `.gitignore` only stops a misplaced copy
  from being staged and is no privacy boundary. `doctor.py` blocks writing when the
  settings or recovery are inside the repository.
- Git history keeps everything ever committed, a private remote is still an upload to
  another service, and committing or pushing is the owner's decision, never part of a save.
- Recovery records are per machine. A record applies only while the note holds exactly
  the version it produced, so it cannot undo a change made in another clone.

Two clones can work at once. Within one clone the writers refuse a stale write: a
packet prepared before a pull that changed the note, or its evidence, fails at save,
and creation never overwrites a file that arrived meanwhile. Between clones nothing is
locked. Both can save different versions of one note, park a proposal under the same
name or allocate the same [number](first-cut-tools.md#optional-living-synthesis-numbering);
the divergence appears as a Git conflict or, for numbering, as a refused scope after the
merge. Pull before working, let one agent write at a time, and treat a conflict as the
owner's decision: its resolution is a new reviewed save, never an automatic merge.

## Limits

The declaration and the doctor inform an agent; they do not stop one that ignores its
rules, and no host enforces them. The doctor authenticates neither the owner nor a
decision. Environment variables and the user configuration folder are trusted as the
person's own. Windows paths are unverified.
