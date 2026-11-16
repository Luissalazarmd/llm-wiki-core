# Capture identity and a lasting connection

Preserve title, Reference, known author/date and permitted original/excerpt/attachment.
Separate authored annotations from evidence. Optional verified Version identifies an
edition; unknown stays unknown, as an empty field rather than a sentence. The wrapper
is reading text: [write for the reader](knowledge-workflow.md#write-for-the-reader);
hashes, local paths, checks and capture history stay in the writer's private records.

Connect to an existing question/note with an explicit wikilink and explanation.
For chat-only questions, persist the question and contribution/limits under
`## Capture context` or `## Contexto de captura` in the wrapper; the section ends
at the next heading. This is reading context, not a typed K-Plex edge or placeholder note. MOC/tags are optional.
Draft this context from the person's stated purpose instead of questioning them;
one line such as "reference to consult later" is valid.

```markdown
---
id: fictional-report
role: source
Title: Fictional report
Reference: https://example.org/fictional-report
---
# Fictional report

## Capture context
Reference to consult later.
```

The read-only checker binds absent destination, draft, dependencies, scope and
source inventory. Exact Reference/Version duplicates or unknown-version ambiguity
require reuse/reconciliation; source IDs also remain unique within that scope.
No semantic/global uniqueness is claimed. Bounds: 50 links, 2,000 inventory entries,
256 KiB/file, 16 MiB source text; a malformed draft or dependency fails, while an
oversized, non-UTF-8 or unparsable existing source is listed as `not_checked` so the
agent reports a limited duplicate scope.

An existing source with an ambiguous Reference or Version stops the check until it
is reconciled.

`note_write.py` refuses sources by design. A capture is created by `capture_write.py`
or, where plain-file writing is not permitted, by the host's own create-only tool
[with the checker alone](#without-the-writer).

## Capture writer

`capture_write.py` creates one capture: the Markdown wrapper and up to 8 attachments
([several at once](#several-captures-one-decision) share one decision).
It needs `write_policy: plain_files`, a `recovery_directory` and `layers.sources`, and
mirrors proposal → save. Check each exit code directly:

```sh
# 1. Bind the exact wrapper, the absent targets and each original. Writes nothing.
capture_write.py --config /private.json prepare --target Sources/new.md --attach /downloads/paper.pdf Sources/new.pdf < /capture.md > /capture.json
# 2. Show the exact wrapper and each attachment name and size (the sha256 stays in the packet); obtain the decision for this packet.
# 3. Recheck every input, create, read back and verify.
capture_write.py --config /private.json save --packet /capture.json
```

Name each attachment with its wrapper's file stem (`Sources/new.md`, `Sources/new.pdf`),
not the download's name: they then sort, link and retire together.

`prepare` runs the checker on the wrapper and prints a packet with a fresh
`capture_id`. It refuses an existing target, an unfilled `{{title}}`, `{{date}}` or
`{{time}}` placeholder, and an attachment that is a symlink, lies inside the library,
changes extension, exceeds 128 MiB or is not an admitted type: `.pdf`, `.png`, `.jpg`,
`.jpeg`, `.gif`, `.webp`, `.epub`, `.mp3`, `.m4a`, `.ogg`, `.opus`, `.wav`, `.flac`,
each with its leading signature. That is a sanity bound, not content validation or a
malware scan. Video, SVG and larger files stay outside; reference them. Attachment
targets sit inside a source folder. The wrapper is the manifest: every attachment is
linked from it, and every link to an admitted type names a declared target, by library
path or relative to the wrapper. Bare names in another folder and absolute or `file:`
links are refused; external URLs are not attachment links.

`save` rederives the whole packet, so a changed wrapper, original, target, duplicate
scope or policy means review again (`check --packet` does the same without writing).
It writes the private record `capture-<capture_id>.json` first, stages verified copies
and publishes them no-clobber, attachments first and the wrapper last. Each file is an
independent copy: never a hard link to the person's original, which is neither moved
nor changed. It then reads back the wrapper bytes and attachment hashes and runs the
saved check. On any failure it removes only the entries it published and its record:
`capture_not_saved` with `library_unchanged: true`. If that removal fails, it reports
`capture_partial` with the `remaining` paths and leaves a `.partial.json` record
beside the first; stop and tell the owner.

### Several captures, one decision

Each packet binds the source inventory it was checked against, so saving one capture
invalidates every other packet prepared before it. Documents handed over together are
therefore prepared together:

```sh
# 1. Bind every wrapper and attachment at once. Writes nothing.
capture_write.py --config /private.json prepare-batch < /batch-manifest.json > /batch.json
# 2. Show every exact wrapper (a table when they hold only fields) and every attachment name and size, once; obtain one decision for this packet.
# 3. Recheck every input, create all of them, read back and verify.
capture_write.py --config /private.json save --packet /batch.json
```

The manifest is a JSON array of 1 to 20 captures, each
`{"target": "Sources/a.md", "draft_path": "/scratch/a.md", "attach": [["/downloads/a.pdf", "Sources/a.pdf"]]}`;
`"draft"` may hold the wrapper text instead of `"draft_path"`, a file outside the
library. Every capture is prepared exactly as a single one and stays a complete packet
inside `captures`. They are also compared with each other: two captures naming the same
target, the same explicit `id`, or the same Reference with an equal or unknown Version
are refused, as is the whole batch when any one capture fails.

`save` rederives every capture, writes `capture-batch-<batch_id>.json` and one
`capture-<capture_id>.json` per capture, stages all files, rechecks, publishes them
no-clobber and verifies each wrapper against the inventory it was reviewed with. It is
whole or nothing under the same rule as one capture: any failure removes every entry
this run published and its records (`capture_not_saved`, `library_unchanged: true`),
or reports `capture_partial` with the `remaining` paths. The batch and each of its
captures save once. One decision covers exactly the wrappers and attachments shown;
adding, dropping or changing a capture is a new packet and a new decision.

The writer authenticates no consent. The [review contract](review-contract.md) still
requires showing the exact wrapper, with the attachment names and hashes, and the
owner's decision for this capture. An approval of an earlier capture of the same
source, since retired or deleted, does not carry over: prepare again, show it again.
A packet saves once; reusing it after a retirement is refused. Never rewrite what was
recorded about a decision to fit a later action.

Limits: no locking; pause concurrent editing and sync. Publication needs hard links
inside the source folder's filesystem. A killed process cannot roll back: hidden
`.core-capture-*` temporaries or attachments without their wrapper may remain, and the
record names what was intended. Rights and consent are not certified.

## Templates

A template is a blank shape for a capture wrapper: shape, not approval, and never
sources. Creating one ("make a podcast template") or changing one ("add a DOI field to
the article one") is part of capture, and goes through `template_write.py` rather than
an improvised script. It needs the same settings as the capture writer.

```sh
# New template. 1. Bind the exact text; writes nothing.
template_write.py --config /private.json prepare --name Fuente-podcast.md < /template.md > /template.json
# 2. Show the exact template (`draft`); obtain the decision for this packet.
# 3. Recheck, create without overwrite, read back.
template_write.py --config /private.json save --packet /template.json

# Change. 1. Read the current file and its hash (`current_sha256`); writes nothing.
template_write.py --config /private.json check --name Fuente-articulo.md < /library/_templates/Fuente-articulo.md
# 2. Bind the complete new text to that current version.
template_write.py --config /private.json prepare --name Fuente-articulo.md --expected-sha256 <current_sha256> < /changed.md > /template.json
# 3. Show the `diff` and the complete resulting template; obtain the decision for this packet.
template_write.py --config /private.json save --packet /template.json
```

The owner asks, sees the exact template and approves once. `check --name` validates a
text on stdin without writing, and without write permission. A template declares
`role: source` with `Title` (empty or `{{title}}`) and an empty `Reference`, keeps
`Version` and `id` empty, has a `## Contexto de captura` or `## Capture context` section
and uses only the placeholders of Obsidian's core Templates plugin, written exactly:
`{{title}}`, `{{date}}`, `{{time}}`, `{{date:FORMAT}}` and `{{time:FORMAT}}`. A concrete
Reference or a link to an attachment or local file makes it a source in disguise:
capture that instead. The helper then fills the placeholders, a Reference and a context
line into a copy in memory and runs the capture checker on it, so every template still
fills into a valid wrapper; a `capture_policy` is checked per capture, not here.

The target is a plain `.md` filename directly inside the library's templates folder:
`folder` in `.obsidian/templates.json` when that file exists, else `_templates`. The
folder stays inside the library and outside `authorized_paths` and every layer (Raw,
Review, Wiki); symlinks and traversal are refused. Where the setting names a folder
that does not exist yet, the first approved save creates it. Core writes nothing else
under `.obsidian`: enabling the Templates core plugin (`core-plugins.json`) and pointing
it at a folder are the owner's manual steps in Obsidian.

`save` rederives the packet, writes the private record `template-<template_id>.json`
first and reads back the saved bytes. A new template is created no-clobber. A change
requires `--expected-sha256` of the current file: the previous version is first copied
to `template-<template_id>.previous.md` in the private recovery directory, then replaced
atomically. Without that hash an existing template is never overwritten, and there is
no delete command. A failure leaves the library as it was (`template_not_saved`), or
reports `template_partial` with the kept copy. A packet saves once, and one decision
covers one template write.

An existing library adopts templates through
[progressive adoption](../skills/progressive-adoption/SKILL.md): read what the owner
already uses, propose one template at a time and never replace the owner's existing
templates with Core's. Changing one of theirs is their request, shown as an exact diff.
The helper authenticates no consent and takes no lock; pause concurrent editing and sync.

## Retiring a capture: an owner exception

Custody of originals is create-only. Removing one is an exception only the library
owner can make, never routine and never the agent's suggestion to tidy up. Act only
when the owner asks in the current conversation; before acting, name the rule being
excepted and show the plan, including the notes that link to the source.

```sh
# 1. Plan: files, hashes, linking notes, the rule and the exception statement. Changes nothing.
capture_write.py --config /private.json retire --target Sources/new.md --reason "<owner's reason>"
# 2. Only after the owner confirms that plan:
capture_write.py --config /private.json retire --target Sources/new.md --reason "<owner's reason>" --expected-sha256 <plan_sha256>
```

The target is the wrapper; its attachments are the admitted files it links. The helper
copies them into `retired-<id>/` in the private recovery directory, verifies the
copies, writes `retired-<id>.json` (paths, hashes, UTC date, reason, the rule and the
statement that this is an owner exception), removes the library files and verifies
their absence and the copies again. A failed removal restores the files and deletes
the copies (`retirement_not_done`); if restoring fails it reports `retirement_partial`
with the copies kept.

It refuses a target outside the source locations, a note that is not a source, a
wrapper whose attachment link is dangling, an attachment another capture links, and a
changed plan. A captured file the wrapper does not link is listed in
`unlinked_siblings` and retired only when named with `--attachment`. Notes that link
to the source are reported in `linked_from` and never edited: tell the owner, whose
later corrections follow the ordinary review. The scan covers `authorized_paths`, at
most 2,000 entries, reads wikilinks, embeds and local Markdown links, and lists
unreadable notes in `link_scan.not_checked`; a bare-name match is a possibility, not a
resolved link.

The helper reads no rules file, so a library copied before its rules mentioned this
exception needs no migration: the owner's explicit request is the exception, and the
agent states the rule it found. The record is not proof of that request. There is no
restore command: capturing again uses the recovery copy as the original, as a new
capture with a new review.

## Revising a wrapper: an owner exception

Correcting only a wrapper's text (a lean context, a fixed author, a removed note) is
the same owner exception, narrower: the attached originals stay untouched, so there
is no retirement and no recapture. Act only when the owner asks in the current
conversation; name the rule being excepted and show the packet's `diff` with the
complete resulting text.

```sh
# 1. Bind the complete new text to the current wrapper; writes nothing.
capture_write.py --config /private.json revise --target Sources/new.md < /revised.md > /revision.json
# 2. Only after the owner's decision on that diff:
capture_write.py --config /private.json save --packet /revision.json
```

The revision keeps the source identity (`id`, Reference, Version) and exactly the same
attachment links; a different source is a new capture, and different attachments need
retirement and a new capture. `save` rechecks the current wrapper, keeps it as
`revision-<id>.previous.md` with a `revision-<id>.json` record in the private recovery
directory, replaces the text atomically and verifies it and the unchanged attachments.
An owner edit after `revise` is refused: revise again and show it again. A failure
before the replace leaves the library and recovery as they were
(`revision_not_saved`); one after it reports `revision_partial` with the previous copy.

## Without the writer

The checker prints `check_sha256`; `--expected-sha256` takes that value, never
`draft_sha256`. Each `capture_check.py` call reads the same draft on stdin. Run the
steps one at a time and check each exit code (a pipe can hide it). A failed recheck
means no save:

```sh
# 1. Before writing: recheck
capture_check.py --config /private.json --target Sources/new.md --expected-sha256 <check_sha256> < /capture.md
# 2. Only if step 1 passed: create with the host's own create-only tool
(set -o noclobber; cat /capture.md > /library/Sources/new.md)
# 3. After writing: verify the saved bytes
capture_check.py --config /private.json --target Sources/new.md --saved --expected-sha256 <check_sha256> < /capture.md
```

Create an independent file, not a hard link to the draft. The checker validates the
Markdown wrapper only, never attachment bytes. No overwrite, locking or rights/consent certification.

## Optional stronger policy

Existing capture_policy retains authorized roots/taxonomy and field mappings;
acyclic map chains reach a parentless root within 32 nodes. Library custody prevails.
