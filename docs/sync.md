# Optional vault synchronization

Preserve the library's existing sync setup. Only if setup/change is requested, choose one provider and test it per device before importing real data; take independent backups. Core requires no sync provider or runtime bootstrap. Agent tools and any managed writer come from the actual authorized host/library, independently of note synchronization. Keep private recovery/state backup explicit.

## Obsidian Sync

Obsidian documents support across Windows, macOS, Linux, iOS, and Android. Sync transports notes, not the approval authority. [Official overview](https://obsidian.md/help/sync-notes).

Hidden paths such as `.agents/`, `.git/`, and `.durable/` are excluded; the vault configuration folder has special handling. Sync preferences and conflict behavior must be checked on each device. Sync does not provision agent tools, authenticate decisions or supply a managed writer. If the library requires a writer, verify its own documented tools; missing availability means proposal-only, not installing a Core engine. Plan private recovery/state backup separately. [Selective syncing](https://obsidian.md/help/sync/settings).

## Other providers

- **Google Drive:** desktop options exist for Windows/macOS; an Android vault generally needs a third-party folder-sync route, not merely the Drive app. Linux has no official Drive desktop client. Drive-based Obsidian vault sync on iOS is not officially supported. Validate the exact workflow before adopting it. [Obsidian guidance](https://obsidian.md/help/sync-notes), [Google desktop requirements](https://support.google.com/drive/answer/2375082).
- **iCloud:** an Apple-focused option. Obsidian warns that Windows use may cause duplication or corruption. [Obsidian guidance](https://obsidian.md/help/sync-notes).

## Operational rules

Keep vault files available offline. Do not layer providers over the same vault, or file-sync `.git` internals or live engine databases. Git can distribute reviewed code without being a second automatic note-sync service. During provider migration, back up, stop the previous provider, relocate/configure as needed, then verify the new provider before resuming writes. [Migration guidance](https://obsidian.md/help/sync/switch).

Headless Sync is an **optional open-beta** route requiring Obsidian Sync; it is not a baseline dependency. Do not run desktop Sync and Headless Sync for the same vault on one device. Review current requirements before installing. [Headless documentation](https://obsidian.md/help/sync/headless).

An offline capture may later sync into Raw. A conflict or unsynchronized canonical base blocks apply until reconciled; sync completion alone never authorizes a proposal.

Documentation checked 2026-10-06. Recheck vendor documentation during actual setup.
