# Starter library

[`examples/starter-library`](../examples/starter-library/Home.md) is a template for a
person who has no library yet. Its root is the library root: it contains no demo
notes, no `examples/` prefixes and no links into Core, so it is copied as it is.
An existing library is never replaced by it; follow
[progressive adoption](../skills/progressive-adoption/SKILL.md) there instead.

It holds `Home.md`, `Raw/Sources/`, `Review/Inbox/`, `Wiki/Notes/`, `Wiki/Maps/` with one
empty starting map, the library rules and an optional Obsidian `Biblioteca.base`
whose folders are relative to the copied root. Folders follow the three
[roles](ontology.md): sources, notes and maps. Wiki prose is Spanish by default.

## Rules file

The rules are the root `AGENTS.md`. That is the name `library.py map` and
`knowledge.py --mode existing` already report, and the one `note_write.py` refuses
to write. Hosts that protect `AGENTS.md` from their own writing tools add to this:
the file that permits [proposal custody](review-contract.md#proposal-custody) cannot be
rewritten by the agent it governs. The template is copied once with an ordinary
file copy, which those protections do not affect. The helpers therefore recognize
no second rules filename. Inside this checkout the file governs only the template.

The rules declare the library editable as plain files, the Raw/Review/Wiki
correspondence, the language, the review needed before any Wiki save, and that
literal proposals may be parked in `Review/Inbox` without the owner present.

## One authorization

Show the person the [rules](../examples/starter-library/AGENTS.md) and the
[private settings](../examples/starter-library.config.example.json), with the
location you propose, and obtain one decision covering both. That decision makes the
library editable and permits custody; it accepts no note. Afterwards parking a
proposal asks nothing of the owner, and every Wiki save still follows the
[review contract](review-contract.md).

With `CORE` set to this checkout and `PRIVATE` to a new private folder outside it:

```sh
set -eu
mkdir "$PRIVATE"
cp -R "$CORE/examples/starter-library" "$PRIVATE/library"
cp "$CORE/examples/starter-library.config.example.json" "$PRIVATE/library.json"
chmod -R u+w "$PRIVATE/library" "$PRIVATE/library.json"
mkdir -m 700 "$PRIVATE/recovery"
python3 "$CORE/scripts/library.py" --config "$PRIVATE/library.json" map --scope Raw --scope Review --scope Wiki
python3 "$CORE/scripts/knowledge.py" --root "$PRIVATE/library"
```

`mkdir` stops when the folder exists, so nothing is overlaid. `chmod` matters when
Core is a read-only checkout, whose file modes a copy inherits. The settings resolve
`library` and `recovery` against the JSON's own folder; the JSON and the recovery
records stay outside both the library and Core. The checks pass when `map` reports
`"rule_paths": ["AGENTS.md"]` with no issues and the strict reading lists the
starting map. The helpers need the Python environment in [tools](first-cut-tools.md).

The settings declare `Raw` as sources, `Review/Inbox` as proposals and `Wiki` as
knowledge. They restrict the helpers and grant nothing; the rules and the person's
decision do. [Plain saving](plain-saving.md#parked-proposals) describes parking.

## Limits

Copying creates no source, note or approval. Obsidian is optional: `Home.md` embeds
the Base views and reads as plain Markdown without them. Bases rendering of this
template has not been observed natively. Canvas, K-Plex settings and CSS from the
[Obsidian example](../examples/obsidian/README.md) are not included because they
depend on that example's paths. Empty folders carry a hidden `.gitkeep` file.
