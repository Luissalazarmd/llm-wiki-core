# Architecture boundary

## Three content stages

- **Raw:** captured source material plus provenance. Preserve the input/version used for a claim. New versions do not silently replace evidence underlying an approved note.
- **Review:** proposed Wiki changes, source references, base revision, and review packet. A proposal is not canonical knowledge and a synced edit is not approval.
- **Wiki:** approved derived Markdown. Only the canonical apply engine changes its machine-managed content after validating authenticated approval.

The root layout remains stable and human-readable. The template has empty placeholders; a private instance contains actual content. Engine-specific paths, exact APIs, and upstream compatibility are unverified until integration review.

## Control plane

Authenticated user → host-generated approval bound to a packet → canonical apply validation → transactional update and durable audit.

Bibliotecario produces evidence and proposals. Orquestador routes work and presents review. Neither can create its own human authority. Obsidian and sync transport files; neither substitutes for the host's authorization or concurrency controls.

## Data classes

Bibliography contains source identity and evidence. Personal memory contains private context, preferences, and commitments in a separately configured store outside the bibliography. A link between classes must be intentional and authorized. Credentials belong in a secret store, never either class.

## Failure posture

Offline readers can read and capture Raw drafts. Missing authoritative state, conflicts, stale proposals, ambiguous approval, or unavailable writer locks block apply. Do not resolve these conditions using last-write-wins. Canonical files, approval records, and replay/audit state must recover consistently.

## Template versus instance

Keep reusable contracts and sanitized configuration in Git. Operate real vault data in a distinct private instance with explicit retention, access, backup, and sync rules. A private Git repository is not permission to include personal data or redistribute upstream source.
