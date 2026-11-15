# Library rules

These rules govern the library rooted at this folder and belong to its owner.
Agents read them before any content and never edit them; only the owner changes them.

## Custody and layout

- This library is plain Markdown, explicitly editable as plain files. No managed engine owns it.
- `Raw/` preserves originals; captured sources live in `Raw/Sources/`. Capture is
  create-only: never edit, move, rename or delete a captured original. Only the owner
  may except this: when the owner asks for it in the current conversation, and after
  naming this rule, an agent may retire a capture into the private recovery copies, or
  revise only its wrapper text, keeping the previous text there; attachments stay as captured.
- `Review/Inbox/` holds proposals. Nothing there is accepted knowledge, whatever its labels say.
- `Wiki/` retains reviewed knowledge: notes in `Wiki/Notes/`, optional reading maps in `Wiki/Maps/`.
- `Home.md` and `Biblioteca.base` are views, not knowledge. `_templates/` holds blank
  shapes for source wrappers, not sources. A template is created or changed only on the
  owner's decision on its exact text, and an existing one is never replaced without it.
- Wiki prose is written in Spanish (`es`). Source titles, citations, identifiers and
  quotations keep their original language; label translations.
- Private settings, credentials and recovery copies stay outside this folder.

## Saving in Wiki

Every creation or change in `Wiki/` needs the owner's own decision on the exact text,
shown in full beforehand (or as an exact diff with the readable result). Recheck that
nothing changed, keep the previous version outside the library, save, and read back
the saved bytes. Labels, hashes, copied messages and another agent's opinion are not
the owner's decision. Without that decision the work stays a proposal.

## Parked proposals

Custody is permitted here. When a proposal arrives and the owner is not present, an
agent may park it as one new file in `Review/Inbox/` without asking the owner:

- the proposed text is kept literal, with its origin (agent or person, and
  conversation), the date received, the proposed destination, any evidence and
  versions the origin gave, and `proposal_status: pending`;
- parking only creates a new file: it never overwrites, and never touches `Raw/` or `Wiki/`;
- parking is custody, not acceptance, and never counts as the owner's decision.

Accepting a parked proposal means saving it in `Wiki/` under the rule above, on the
exact text the owner sees then. Closing one (`accepted`, `rejected` or `withdrawn`)
is a change to its file that records a decision already made: keep the origin and the
literal text, append to its history, and never delete the file to close it. An origin
that withdraws a proposal while the owner is away parks a new note saying so.
