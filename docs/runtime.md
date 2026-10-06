# Runtime and durable state

The original installer provisions pinned vendor engine files locally into the same core folder. Vendor files are not distributed by the tracked project; see [local integration](local-integration.md). This is a tested API installation, not the complete upstream bootstrap kit. Agent profiles remain instructions, not executables.

## Installation boundary

Provision the pinned authorized engine revision using the original local installer on the designated host. Verify dependencies, integrity, exact root layout, runtime skill paths, and canonical entry points. Do not assume vault synchronization installs executable code or hidden runtime files.

## One writer

The host is the sole canonical writer for each instance. Another host requires explicit controlled takeover, fencing, and durable-state reconciliation. A mobile reader or newly synced computer is not a writer merely because it has the vault files.

## State classification before implementation

- **Disposable local state:** caches and temporary rendering artifacts may be excluded and regenerated.
- **Private configuration/secrets:** kept in ignored local files in the same project; credentials in an appropriate secret store.
- **Durable engine state:** approval decisions, consumed identities, transactional journals, lineage, revision records, and audit history require explicit integrity, retention, access, backup, and recovery design.

The inspected upstream stores decisions, review cases, receipts, source/evidence indexes and revision lineage under `.wanderloots-llm-wiki/durable/`. Runs, checkpoints, locks, staging and pending backups are under `.wanderloots-llm-wiki/runtime/`; pending recovery data is not disposable merely because it is called runtime. Production Git, backup and restore policy remain to be selected; the synthetic instance explicitly disables Git. The installed operational root is excluded from Git publication by default, including durable state. This is a publication boundary, not permission to discard it: backup and restore must preserve canonical content and its corresponding audit/recovery state together. Selected note content may be versioned in this same private repository after explicit publication approval.

Sync is not a database replication protocol. Keep live engine databases and lock files out of general-purpose vault file synchronization. Use an engine-supported snapshot/backup protocol and test consistent restoration with canonical content. Runtime-owned hidden directories are not supplied by Obsidian Sync.

## Readiness gate

Until authenticated approvals, the canonical apply path, durable recovery, locking, and synthetic tests are implemented and verified, the system remains read-only/proposal-only. Report this state plainly to users.
