# Runtime: existing agent, small tools

Core runs through the person's existing agent host. The Bibliotecario is a role with three progressively loaded skills, not an executable bot. Core supplies no model provider, vendor engine, installer, approval server or database. Python and pinned PyYAML are needed only for the supplied helpers; use an authorized environment, never install dependencies automatically.

## Available surfaces

- `knowledge.py`: strict optional ontology or scoped existing-library discovery, bounded navigation, existing-target proposal packets. Read-only.
- `library.py`: private personal-config validation, scoped folder/note/attachment mapping, read/navigation and proposal preparation. Read-only.
- `note_write.py`: optional save/conditional recovery of one existing derived Markdown note in an explicitly editable library. Actual host confirmation is required by the skill, not authenticated by this script. See [plain saving](plain-saving.md).
- [Action skills](../AGENTS.md): capture uses permitted host/library retrieval and create-only tools; reading uses relevant originals; review/save uses actual user interaction and the allowed writer.

## Library custody and writer selection

The library stays at its existing root, separate from the product if desired. Default policy is read-only. Inspect applicable rules first, then intersect current user permission, configured paths and real host capabilities. A managed library retains its own writer/approval/recovery requirements; Core installs no adapter and makes no claim that an arbitrary managed writer works. Choose its actual commands only after verification. Unknown/unavailable writer means proposal-only, not conversion to plain editing.

`canonical_engine` is a compatibility name for the generic managed-writer policy in personal settings; it refers to no bundled engine. Known historical marker names remain only as fail-closed safety signals in the plain helper. Removing a dependency must not make an existing governed library writable by accident.

## State and recovery

Markdown originals are the source/content authority. Proposals and thin maps are not accepted knowledge. Private personal config remains separate from shared profiles; credentials belong in the host's secret store. Continuity reuses the existing authorized project note/memory, not a mirrored library or queue.

Ordinary-save recovery records contain previous bytes and proposed content/source hashes. Keep them private, outside the library and out of Git publication, with agreed retention and backup. Their presence alone does not prove a successful write. Same-machine recovery is not an external backup.

The helper assumes a quiet cooperative single writer. It provides no atomic compare-and-swap, writer fencing, signed consent or multi-file crash journal. Pause on active concurrent editing/sync. For stronger requirements use the library's established writer, not a new Core engine. Sync transports notes; it grants no permission and does not install runtime/tools.

## Verification boundary

All shipped test cases use invented files and need no private engine input. [Acceptance](acceptance.md) separates deterministic helper tests from actual host interaction, semantic claim checks and graphical rendering. Universal host compatibility and authenticated managed apply are not claimed. No script or skill may invent user consent from a flag, quoted conversation or content hash.
