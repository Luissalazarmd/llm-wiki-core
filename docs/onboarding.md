# Start with something you want to understand

Choose a starting point: tell your existing agent a question, share a source,
or select a few notes.
Ask: “Start read-only. Help me understand this and show me what is worth keeping.”
Use [AGENTS](../AGENTS.md), its preflight and one of the four action skills.
Markdown and authorized host tools suffice; Obsidian and K-Plex are optional.

In plain terms: your agent reads what you point it to, explains it and suggests what
to keep. It changes a file only after you see the exact text and agree, and it keeps
the previous version so that the change can be undone.

Core is the tools checkout. Your actual library is independently located and may
already exist elsewhere. The host must actually access both locations and read
that library’s rules before its content. Access is not consent to write or share;
never copy Core over existing rules, move notes or reorganize the library.

For mixed or flat notes, select specific files or a small folder. No metadata
completion or root-wide scan is needed. This optional read-only command accepts
a selected Markdown file relative to the actual library root:

```sh
python3 scripts/knowledge.py --root /path/to/library --mode existing --scope Notes/selected.md
```

Run it from the Core checkout, only for an authorized selection that exists.
See [progressive adoption](../skills/progressive-adoption/SKILL.md) for existing libraries.

If you have no library, start with your question or source in chat. Only when you
ask to retain something should the host propose a minimal private destination.
It may prepare an explicitly authorized location; no automatic folders,
placeholder notes or required Raw/Review/Wiki folder names follow.

For a first capture, preserve the source and explain why it helps your question.
MOC and tags are optional. A chat question can persist as `Capture context` in
the source wrapper without creating a placeholder note. The existing host must
supply authorized retrieval and a permitted create-only writer; Core promises
no built-in downloader. Follow [source admission](raw-admission.md).

For a first note, the host shows the complete readable proposal or exact diff
with its readable result, then obtains your actual confirmation of that version.
A permitted writer must check the exact base and evidence immediately before
saving, preserve private recovery and read back the saved bytes. Missing write
permission blocks saving, not discussion or proposal preparation.
See the [review contract](review-contract.md) and [plain saving](plain-saving.md).

[Helpers](first-cut-tools.md) are optional. Their default is `read_only`;
`plain_files` configuration restricts operations and never supplies consent.
Wiki prose defaults to Spanish; source titles and original quotations retain
their language. The four skills and [ontology 2.0](ontology.md) remain the model.

## Get and update Core

Download a ZIP or ask your agent to clone the [public repository](https://github.com/Luissalazarmd/llm-wiki-core)
into a separate tools directory. A ZIP needs no Git installation; a clone supports
reviewing upstream changes. Give the agent the local Core `AGENTS.md` path, your
actual library location and one current question; it must verify access and rules.
GitHub is a distribution option, not a required account or a place to upload notes.

Updates are deliberate: inspect local changes, review the incoming diff and retain
a recovery route before updating. Never overwrite local adaptations or copy new
Core rules over a library's own instructions. For ZIP downloads, compare a fresh
copy before replacing the previous tools. Do not update in the middle of a reviewed
save: changed contracts or helpers require rechecking the operation.
Choose library storage separately under [storage, sync and backups](sync.md).
