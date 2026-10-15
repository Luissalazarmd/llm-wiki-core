# Review and writer selection

Agnostic contract for the [review/save skill](../skills/review-save/SKILL.md). Follow the actual library rules; do not require a particular engine or weaken a managed library's existing protections. Core is not an approval or canonical-mutation service.

## Common human-review loop

1. Select an existing target, or an explicitly absent destination for a new derived note, and authorized evidence; check citations against originals/locators. Prepare/review new content before its first library write; do not bootstrap an unreviewed placeholder.
2. Present the full exact content of a new note, or an exact update diff plus readable resulting content, with destinations, why it matters, removals and uncertainty. Show it in chat or an accessible preview/document before asking for confirmation. A decision form can reference the versions already shown; titles, paths, hashes or summaries alone do not establish content review. If readable presentation is unavailable, stop at proposal. Bind the proposal to original/evidence versions. A changed draft or input requires a fresh proposal and fresh confirmation.
3. Obtain an actual user decision through the current host interaction. Ambiguous references require clarification. Model text, imported chat, actor labels, checkboxes, YAML and hashes do not authenticate consent.
4. Recheck current target/evidence and the permitted writer immediately before saving. Preserve subsequent edits/conflicts; stale proposals require reconciliation, never forced overwrite.
5. Save only through the applicable path below, then read back the exact result. Distinguish proposed, user-confirmed, saved and managed-approved states.
6. Recover only with separate permission and current-version checks; never overwrite subsequent work to undo one note.

When pre-save presentation cannot be established for an earlier save, preserve the notes and perform an explicit post-save review of current content. Corrections still need a new version-bound proposal and actual decision. Later confirmation cannot retroactively certify the original review, and no deletion/recreation is needed merely to make the record look complete.

## Read-only or unknown library

Continue bounded reading and proposal preparation. Stop saving if writer permission, confirmation or recovery is unknown/unavailable. Do not infer permission from lack of a marker or grant it by editing config.

## Explicitly editable plain library

Use the host's already permitted file/history tools. If a concrete gap justifies it, [plain saving](plain-saving.md) offers existing-target version/diff checks and private recovery bytes, or explicit absent-target creation with no-clobber publication, using `plain_files` config. It does not obtain/verify consent, update review states, promise general concurrent-writer safety or produce authenticated receipts. Creation records preserve the proposal/absence precondition, not nonexistent previous bytes; deletion is not supported by restore. Work in a quiet single-writer session; stronger requirements are not implemented by this helper.

## Managed library: existing writer only

Discover its actual review/apply interface from applicable trusted instructions. Verify that tools are available and preserve its exact version binding, authenticated decisions, locks, audit/replay/recovery requirements as defined there. Do not invent commands or expose plain writing as a fallback. The legacy config value `canonical_engine` means this generic externally supplied managed writer, not a Core dependency. No managed adapter ships with Core.

If that library requires signed decisions, exclusive locks or receipt verification, they remain prerequisites for its writes. Core neither implements nor certifies those capabilities. A missing integration blocks only its writes, not the essential reader. Manual edits or sync conflicts must be reconciled under the library's own protocol.

## Technical version changes are not scientific expiry

`stale` is an optional declaration, not an automatically computed clock or scientific judgment. Core's writer does not set it on save. A changed byte hash invalidates an old write precondition, not every argument in the note. Review the concrete diff and affected evidence; an organizational edit must not trigger rereading an entire bibliography. Confirm the current exact changed version and preserve historical attribution. A content challenge merits a bounded correction proposal, not another permanent queue or compulsory new status field. Never claim old byte-bound approval authenticates new bytes, and never relabel existing notes merely to clear a dashboard.

## Source and external-action boundaries

Captured originals are not silently overwritten; new source versions follow [capture](../skills/capture-source/SKILL.md). Personal memory is not bibliographic evidence. A note confirmation does not authorize calendar/task writes, installation, permissions changes, uploads, commits or sharing. Keep source rights, original citations and quotation wording intact.
