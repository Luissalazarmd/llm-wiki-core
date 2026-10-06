# Runtime and durable state

No runtime, engine scripts, dependency lockfile, or bootstrap installer is installed here. Agent profiles are instructions, not executables.

## Planned installation boundary

After license and compatibility review, provision a pinned authorized engine revision using Git or an explicit bootstrap procedure on the designated host. Verify dependencies, integrity, exact root layout, runtime skill paths, and canonical entry points. Do not assume vault synchronization installs executable code or hidden runtime files.

## One writer

The host is the sole canonical writer for each instance. Another host requires explicit controlled takeover, fencing, and durable-state reconciliation. A mobile reader or newly synced computer is not a writer merely because it has the vault files.

## State classification before implementation

- **Disposable local state:** caches and temporary rendering artifacts may be excluded and regenerated.
- **Private configuration/secrets:** kept outside the baseline; credentials in an appropriate secret store.
- **Durable engine state:** approval decisions, consumed identities, transactional journals, lineage, revision records, and audit history require explicit integrity, retention, access, backup, and recovery design.

The upstream canonical durable-state path and Git policy are **TBD pending inspection**. This scaffold intentionally does not blanket-ignore `.durable/`, generic databases, or all engine state. If durable state contains private data, isolate it in the private instance and design its backup; do not silently discard it or commit it to this generic template. Conversely, do not assume unignored means safe to commit.

Sync is not a database replication protocol. Keep live engine databases and lock files out of general-purpose vault file synchronization. Use an engine-supported snapshot/backup protocol and test consistent restoration with canonical content. Runtime-owned hidden directories are not supplied by Obsidian Sync.

## Readiness gate

Until authenticated approvals, the canonical apply path, durable recovery, locking, and synthetic tests are implemented and verified, the system remains read-only/proposal-only. Report this state plainly to users.
