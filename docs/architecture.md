# Architecture boundary

## Three content stages

- **Raw:** captured source material plus provenance. Preserve the input/version used for a claim. New versions do not silently replace evidence underlying an approved note.
- **Review:** proposed Wiki changes, source references, base revision, and review packet. A proposal is not canonical knowledge and a synced edit is not approval.
- **Wiki:** approved derived Markdown. Only the canonical apply engine changes its machine-managed content after validating authenticated approval.

The root layout remains stable and human-readable. A fresh clone has empty placeholders; the same folder becomes the private Wiki after local engine installation and authorized capture. The tested API boundary is documented in local integration.

## Control plane

Authenticated user → host-generated approval bound to a packet → canonical apply validation → transactional update and durable audit.

Bibliotecario produces evidence and proposals. Orquestador routes work and presents review. Neither can create its own human authority. Obsidian and sync transport files; neither substitutes for the host's authorization or concurrency controls.

## Data classes

Bibliography contains source identity and evidence. Personal memory contains private context, preferences, and commitments in a separately configured store outside the bibliography. A link between classes must be intentional and authorized. Credentials belong in a secret store, never either class.

## Failure posture

Offline readers can read and capture Raw drafts. Missing authoritative state, conflicts, stale proposals, ambiguous approval, or unavailable writer locks block apply. Do not resolve these conditions using last-write-wins. Canonical files, approval records, and replay/audit state must recover consistently.

## One project, deliberate publication

Keep the engine, agents and private Wiki in the same core folder. Original code and selected authorized knowledge may use the same private Git repository. Licensed engine files, local configuration and operational state remain excluded by default. A private repository is not permission to disclose personal data or redistribute upstream source. Keep explicit retention, backup and sync rules; exclusion from Git does not make durable state disposable.
