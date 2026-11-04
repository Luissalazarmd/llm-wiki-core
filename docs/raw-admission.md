# Capture identity and a lasting connection

Preserve title, Reference, known author/date, retrieval/extraction context and
permitted original/excerpt/attachment. Separate authored annotations from evidence.
Optional verified Version identifies an edition; unknown stays unknown.

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

Core has no source writer, and `note_write.py` refuses sources by design. After the
check, the host creates the file with its own permitted create-only tool, then
verifies exact saved bytes with the pre-write hash (`capture_check.py --saved
--expected-sha256`). No overwrite, locking or rights/consent certification.

## Optional stronger policy

Existing capture_policy retains authorized roots/taxonomy and field mappings;
acyclic map chains reach a parentless root within 32 nodes. Library custody prevails.
