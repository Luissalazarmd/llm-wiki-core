# Upstream and license integration boundary

Target dependency: the private Wanderloots 2.0.5 engine, still **unbundled in this scaffold**. A separately pinned local extraction has passed the bounded [synthetic integration](local-integration.md); it is not a complete bootstrap installation.

This baseline uses original documentation and placeholders. It does not copy upstream code, license text, runtime instructions, personal vault data, source history, identities, or secrets. No open-source license is granted or implied by this repository.

Before an authorized integration:

1. Read the exact upstream LICENSE and applicable notices; confirm private-use and derivative/distribution scope. Preserve them unchanged for every copied component. If scope is uncertain, stop and ask the rights holder.
2. Pin and record a reviewed source revision in private integration records; do not transplant Git history or personal content.
3. Preserve the known root layout: `Raw/`, `Review/`, `Wiki/`, `Schema/`, `scripts/`, `rail/`, `automation/`, `docs/`, `_templates/`, `.agents/`, and `.wanderloots-llm-wiki/` with its bootstrap and durable internals. Preserve the canonical root `Librarian Profile.md`; `Agents/bibliotecario.md` points to it rather than duplicating it. Inspect exact trusted entry points, approval model, durable-state requirements, and dependencies before installing anything.
4. Extract only licensed, necessary engine components into a clean branch. Audit tracked and generated files for personal data and secrets.
5. Reconcile this design contract with actual APIs. Do not implement a competing approval/apply path to make an example appear functional.
6. Verify synthetic acceptance and recovery before labeling the private instance operational.

A separate local extraction preserves the license and notices and supports the tested read-only adapter and synthetic canonical flow. No vendor files are copied into this baseline. Migration of an existing vault and production activation remain deferred. A repository scaffold commit does not satisfy those milestones.
