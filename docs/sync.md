# Storage, optional sync and backups

Start locally and preserve a working setup. Choose online storage only when the
person needs remote history or another device; Core requires neither a cloud
account nor a public repository for the library.

- **Core checkout:** the public code/contracts/examples obtained from GitHub.
  Keep personal notes and credentials outside this distribution directory.
- **Private library:** the person's actual files. Optional Git history can use a
  separate private remote, after checking selected files, access and source rights.
  A private GitHub repository is still an upload to another service; history can
  retain earlier contents. Never push library data to the public Core remote.
- **Device sync:** an optional service keeps a local library available on multiple
  devices. An online-only folder is insufficient for these filesystem helpers;
  selected files must be available locally. Choose for the actual device mix.
- **Backup:** an independent recoverable copy, including private recovery records.
  Verify restoration; a synced deletion or conflict must not erase the only copy.

For Obsidian, consult its current [sync options](https://help.obsidian.md/sync-notes)
and [backup guidance](https://help.obsidian.md/backup). Obsidian Sync is its supported
cross-platform option; other cloud folders and Git have device-specific tradeoffs.
These are choices to evaluate, not bundled integrations or automatic setup.

Preserve the existing setup. For a requested change, verify current vendor
requirements, one provider per vault and each device on synthetic data first.
Keep independent backups. Sync conflict copies enter scope as ordinary `.md` files, and online-only placeholders must be local. In the specific synced folder, test no-clobber hard-link creation on synthetic data first. Pause writes on conflicts/concurrency. Sync transports
files, not consent, tools or managed-writer authority. Private recovery needs its
own backup; installation/provider changes require separate authorization.
