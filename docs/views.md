# Views

A view is navigation, not knowledge: an Obsidian Canvas (`.canvas`), a Base (`.base`)
or a Markdown page such as `Home.md` or a dashboard that arranges and links what the
library already holds. Changing one still needs the owner's decision on its exact
content under the [review contract](review-contract.md), so views have their own
optional writer, `view_write.py`. It is not an approval engine, and it is the only Core
helper that writes these files; `note_write.py` takes Markdown notes only.

```sh
python3 scripts/view_write.py --config /private.json check --target Mapa.canvas < /draft.canvas
python3 scripts/view_write.py --config /private.json prepare --target Mapa.canvas < /draft.canvas > /view.json
python3 scripts/view_write.py --config /private.json save --packet /view.json
# changing an existing view: check prints current_sha256
python3 scripts/view_write.py --config /private.json check --target Mapa.canvas < /changed.canvas
python3 scripts/view_write.py --config /private.json prepare --target Mapa.canvas --expected-sha256 <current_sha256> < /changed.canvas > /view.json
python3 scripts/view_write.py --config /private.json save --packet /view.json
```

`check` validates and writes nothing; it works under `read_only`. `prepare` needs
`plain_files`, binds the exact text to the absent target or to the current version, and
prints a packet with that text (`draft`), a unified `diff` and what the checker found.
Show the owner the draft, or the diff with the readable result, then `save`. Creation
never overwrites. A change requires `--expected-sha256` of the current file, keeps the
previous version as a private copy in the recovery directory, replaces the file
atomically and reads the saved bytes back. A packet saves once: every later change is
prepared and shown again. No restore command is supplied; returning to the copy is
another reviewed change. Write a canvas with one attribute per line so its diff reads.

## Where a view may live

Directly in the library root, where `Home.md` and `Biblioteca.base` already are, or
inside a folder the owner declares in the private settings as `layers.views`, for
example `"layers": {"views": ["Vistas"]}`. A declared folder must exist and may not overlap `sources`, `proposals`,
`knowledge` or `drafts`; it need not be inside `authorized_paths`. An owner who wants
canvases beside the notes declares knowledge precisely (`Wiki/Notes`, `Wiki/Maps`) and
the views folder next to them (`Wiki/Vistas`).

The writer refuses everything else: any path inside a source, proposal, knowledge or
draft layer or a numbered scope; hidden paths, so never `.obsidian`, plugin settings or
workspace files; `AGENTS.md`, `SKILL.md`, `CLAUDE.md`, `GEMINI.md`, `SOUL.md` and
`copilot-instructions.md` whatever they declare; symlinks, traversal, a missing folder
and a name that differs from an existing file only by case. It creates no folders.

## What is checked

- **Canvas**: JSON Canvas 1.0. Node and edge ids are unique across both; every
  `fromNode` and `toNode` is a node; `x`, `y`, `width` and `height` are integers with
  positive sizes; types, sides, ends and colours are the specified values. A file card
  must point to an existing library file, and a `#Heading` or `#^block` on a Markdown
  card must exist in it. That file is read only when it is in the root, a views folder
  or `authorized_paths`; elsewhere, link it without a subpath. A link card takes an
  `http(s)` address only. The result lists the file cards, the link addresses Obsidian
  would load, the amount of card text, subpaths it could not verify (a PDF page) and
  attributes outside the specification, which are kept and reported, not refused.
- **Base**: YAML with unique keys and no aliases, and the top-level shape of
  `filters`, `formulas`, `properties`, `summaries` and `views`. Filters, formulas and
  view options are not interpreted; only Obsidian shows whether a Base renders.
- **Markdown**: the frontmatter declares `role: view`, a marker outside the
  [three roles](ontology.md), and none of `maturity`, `origin`, `proposal_status`,
  `primary_moc`, `address`, `former_addresses`, `map_kind` or `review`. An existing
  file is replaced only if it already declares `role: view`, or declares no role and
  none of those keys: that is how an unlabelled `Home.md` is adopted, with the added
  declaration visible in the diff.

## Not a back door

A view has no evidence binding, so it must never carry what a note carries. The
location rules keep the writer out of retained knowledge; a Markdown file at the root
that `authorized_paths` selects is content and goes through `library.py proposal` and
`note_write.py`; a file that declares another role, or the format of a parked proposal
or an owner seed, is never replaced here. The writer cannot judge prose. Keep card text
and dashboard prose to labels and orientation, and put any claim, summary or
interpretation in a note with its evidence, linked from the view. Views are library
text: [write for the reader](knowledge-workflow.md#write-for-the-reader), with no
procedure, hashes or status. A card that links a note or a Base that lists one says
nothing about its review. These mechanics authenticate no consent, read no library
rules and share the [plain-save limits](plain-saving.md): one quiet cooperative writer,
no locks, hard links required for creation.

Obsidian syntax for these files is in the vendored
[Obsidian skills](../adapters/obsidian/README.md); where they say to create or edit the
file directly, use this writer instead.
