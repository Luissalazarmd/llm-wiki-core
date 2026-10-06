# Upstream and license integration boundary

Target dependency: the private Wanderloots 2.0.5 engine, **not redistributed by the tracked core project**, but installed locally into the same core folder. A separately pinned local extraction has passed the bounded [synthetic integration](local-integration.md); it is not a complete bootstrap installation.

The tracked delivery uses original code, documentation, hashes and placeholders. It does not redistribute upstream code or license text, personal vault data, source history, identities or secrets. Local installation preserves the upstream license beside its files. No open-source license is granted or implied by this repository.

Before an authorized integration:

1. Read the exact upstream LICENSE and applicable notices; confirm private-use and derivative/distribution scope. Preserve them unchanged for every copied component. If scope is uncertain, stop and ask the rights holder.
2. Pin and record a reviewed source revision in private integration records; do not transplant Git history or personal content.
3. Preserve the known root layout: `Raw/`, `Review/`, `Wiki/`, `Schema/`, `scripts/`, `rail/`, `automation/`, `docs/`, `_templates/`, `.agents/`, and `.wanderloots-llm-wiki/` with its bootstrap and durable internals. Preserve the canonical root `Librarian Profile.md`; `Agents/bibliotecario.md` points to it rather than duplicating it. Inspect exact trusted entry points, approval model, durable-state requirements, and dependencies before installing anything.
4. Install only licensed, necessary engine components locally into the core folder, outside the tracked publication set. Audit tracked and generated files for personal data and secrets.
5. Reconcile this design contract with actual APIs. Do not implement a competing approval/apply path to make an example appear functional.
6. Verify synthetic acceptance and recovery before labeling the private instance operational.

The installer copies only the pinned authorized engine allowlist into the core folder and preserves LICENSE/notices. The tested synthetic layout has engine and Wiki in that same folder. Vendor files are ignored by Git; original installer and adapter code remain trackable. Migration of an existing vault and production activation remain deferred. A repository scaffold commit does not satisfy those milestones.
