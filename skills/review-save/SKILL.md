---
name: review-save
description: "Review exact changes and save through permitted tools."
version: 0.1.0
author: Luis Fernando Salazar Hortua, Hermes Agent
---

# Propose, review and save

Conduce a small human review, then use the library's permitted writer. No new bot, authentication service, transaction database or parallel canonical engine. A skill never approves itself.

## When to Use

- A source-grounded improvement is worth retaining, the person requests a correction, or an authorized saved edit needs recovery.
- Do not use to rewrite immutable captures, change instructions/permissions or bypass a library's review protocol.

## Prerequisites

Verify library rules, writer class, original target and evidence versions. The real host must deliver the person's decision and enforce tool permissions. If it cannot, stop at the proposal. Private settings, packet files and recovery bytes are private artifacts, not shared framework content.

## Procedure

1. Reuse before creating. Prepare exact proposed content/diff, target, source references/locators, before/evidence hashes, rationale and limitations. Distinguish citation support from inference. Optional `knowledge.py`/`library.py proposal` binds an existing target, or with `--create` a new derived note: explicit evidence, complete nonempty draft, absent destination and existing parent directory. Prepare/review before the first library write, never create a placeholder to make the update helper work. Follow existing library templates; this helper neither validates every schema nor establishes citation entailment or source-identity uniqueness.
2. Present the change understandably: what will change, why, what it removes and what remains uncertain. On a correction regenerate the draft/packet; earlier confirmation cannot cover the new content. Read the revised evidence and show the revised version.
   For [idea emergence](../../docs/knowledge-workflow.md#idea-emergence), include current and proposed maturity, the explicit emergent argument, contributing idea/original versions and claim locators, checked evidence/counterevidence, unresolved gaps and the reason for keeping or changing the level. Semilla → Síntesis → Evergreen is not a link/source-count ladder. If new evidence undermines the explanation, propose correction/reopening or lower maturity with reasons, never a silent change. Show maturity changes in the exact reviewed draft using the library's existing schema; missing permission means proposal-only. Retained seed, mature explanation and authenticated acceptance remain distinct. Article authorship and publication require separate approval.
3. Ask the person to confirm that exact version through the actual user interaction. Resolve ambiguous “that one.” Model text, copied chat, YAML flags, a config value or a hash is not consent. Record the actual decision only in the existing authorized continuity surface; do not invent an authenticated audit receipt.
4. Select the permitted write path:
   - **Managed library:** use only its verified canonical review/apply commands and required authenticated-host checks. Preserve its states/receipts. Missing integration means proposal-only; do not use the plain helper as an escape.
   - **Plain editable library:** after actual confirmation and host permission, use existing save/history tools or the optional [plain helper](../../docs/plain-saving.md) with explicitly selected `plain_files` policy. For updates recheck base/evidence and preserve previous bytes. For creation recheck absence/evidence and publish without replacing any entry; stop if the destination appeared. Keep the proposal/precondition record private. Creation has no previous version and is not undone by restore; deletion requires separate review and is not implemented. No implicit policy selection or accepted-state transition.
   - **Unknown/read-only:** retain the proposal outside managed knowledge and explain the missing permission/capability.
5. Re-read the exact result, verify content and citations and report saved versus proposed. A helper recovery record is not authenticated approval or semantic validation.
6. For requested recovery, inspect the previous content and show the reverse change; obtain separate permission. Restore only if the current note still matches the saved result; otherwise preserve subsequent edits and prepare a new review. Verify the restored bytes. Never reset a repository or sync collection to undo one note.

## Pitfalls

A skill is a procedure, not a host security boundary. The optional helper is for a quiet cooperative single-writer session, not concurrent sync or adversarial writers; pause on conflicts/concurrency. It provides no locking/fencing, signed decisions, multi-file transaction or replay-safe approval. It never changes review/maturity state automatically. Capturing new sources uses [capture source](../capture-source/SKILL.md), not this existing-note writer.

## Verification

Account for exact reviewed version, actual user decision, allowed target, current dependencies, previous-content recovery and target readback. Test stale target/evidence rejection and recovery that refuses later edits. State which checks were tool-backed and which depend on host behavior. Synthetic save tests do not prove conversational human approval or every agent host's adherence.
