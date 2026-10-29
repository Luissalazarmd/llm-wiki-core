# Optional living-synthesis implementation
Objective: implement the authorized continuation of [documentation adoption](living-synthesis-adoption.md), preserving that completed history.
Branch: feat/living-synthesis-numbering; delivery: reviewable commits and push only, no PR; runner: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`.

## Specs

- S1 — "Inspect Git status, diff, staged and untracked files before editing. Preserve existing work." "The previous tracker describes a COMPLETED DOCUMENTATION delivery, not an implemented allocator. Preserve its history. Create a separate implementation tracker or an explicitly linked continuation rather than silently rewriting its original scope."
- S2 — "Prefer living integrated syntheses: coherent explanations with headings, original citations, limitations, connections and open questions." "Seeds may remain fragments in conversation or drafts; do not require an atomic file for every thought." "Within this OPTIONAL profile, every retained synthesis has one thematic primary MOC." "Associate an existing MOC or propose the synthesis and its new MOC together." "Generated inventories of sources, notes or other types are catalogs." "Do not automatically number every object whose technical role is map."
- S3 — "MOC 001 has syntheses 001-01, 001-02, etc." "MOC 002 has its own sequence: 002-01, 002-02, etc." "Seeds receive no synthesis address." "Progression to Evergreen does not change the address." "Referencing a synthesis from another MOC does not duplicate or recode it." "A real primary-MOC move assigns the next available destination address, preserves the SAME technical identity and reconciles previous references." "Preserve former-address history/reservations under the agreed convention. Do not silently recycle gaps or assume incomplete history means availability."
- S4 — "Human addresses are not technical IDs." "Preserve existing IDs, authorship, original evidence, source versions and historical decisions." "Where an existing library cannot separate identity from its current address, do not rewrite its identity to make the new convention fit." "No separate traces registry, duplicate knowledge store or full-chat ingestion."
- S5 — "Preserve current Core v2 source/note/map vocabulary and note-only maturity." "Do not restore superseded roles, mandatory review metadata, compulsory folders or globally mandatory MOCs/tags." "Existing libraries may retain other conventions." "Obsidian, K-Plex and Dataview remain optional surfaces."
- S6 — "Reuse existing reader/proposal/check/save/recovery functions." "Extend the current review/save skill where necessary; do not add a fifth skill or another writer." "Implement one small deterministic numbering module, integrated with the actual preparation and validation paths:" "Reuse an existing address when appropriate." "Propose an available MOC or synthesis address." "Validate eligibility, primary association and collisions." "Support deliberate primary-MOC recoding with reference/history reconciliation." "Prepare the complete numbered candidate BEFORE exact human review." "Recheck scope, identity, base/evidence versions and address availability BEFORE permitted saving." "If anything changed, stop and prepare a new candidate; never silently renumber an already-reviewed draft."
- S7 — "Do not claim concurrency safety or multi-file atomicity beyond what is actually implemented and tested. Preserve stronger local managed-writer requirements. An unavailable writer blocks dependent writes, not reading or proposal preparation." "Choose the minimum compatible representation after inspecting current code. Avoid duplicate allocation logic in skills, commands, views or examples."
- S8 — "Use isolated synthetic fixtures, not a personal library." "Use test-first for the new deterministic behavior. Keep code, focused tests, help text and documentation together." "Rejected operations preserving stored content and relevant allocation state." "Existing unnumbered workflows and save/recovery behavior remaining compatible." "Validate affected links, JSON/Canvas and whitespace."
- S9 — "Work on a non-destructive feature branch, not directly on main." "Reuse and reconcile the existing documentation; do not write a parallel guide." "Update “future/not implemented” claims only for capabilities actually delivered." "Keep the adoption plan generalizable and distinguish implemented mechanics from a future owner-authorized library pilot." "Inspect every staged file for scope, secrets and private material." "Make coherent Conventional Commits with their tests and docs." "Verify the configured remote belongs to the intended Core repository." "Push the feature branch without force." "Do not merge, release or create a pull request without separate authorization."

## Tasks

- T1 | S1,S9 | inline | done | Recovered state, preserved documentation/history, verified remote and created feature branch. Historical delivery preserved byte-for-byte in 95a505a4405499ff19eb16667ddb9d03037bbd89.
- T2 | S2-S8 | delegated core + parent corrections | done | Shared numbering/preparation/check/save/recovery implemented; independent and native findings fixed with public regressions. Full final suite: 192 passed. Risk: item 2 (scope/writer guards), item 3 (shared proposal/writer compatibility). Commits: 494b381ffbcbb976e07021693146d0ba5d9f9c73, f2637fb82d6bee38b1675aab857e5d094f88ff4c.
- T3 | S1-S9 | inline + independent verify + native review | done | Functional/differential/structural/publication checks passed; native approved acknowledgement burned authority. Non-force source push and remote hash verified at f2637fb82d6bee38b1675aab857e5d094f88ff4c; final evidence-only closure follows without changing reviewed code. No PR/merge/release or personal-library operation.

## Log

- L1 — Original request (verbatim):

Implement the optional living-synthesis workflow and MOC-scoped numbering already
 documented in this repository. Finish the in-scope implementation, verification,
 documentation, commits and push.

   AUTHORIZATION
   This live user request authorizes implementation in llm-wiki-core, reviewable commits and
 pushing a feature branch to the verified repository remote.

   It does NOT authorize:
   - Reading or migrating personal libraries.
   - Importing personal notes, bibliography, settings or conversation archives.
   - Force-push, history rewriting, merging, releases or account changes.
   - Installing providers, plugins or a new approval engine.
   - Bypassing repository rules, host permissions or review consent.

   Use neutral synthetic examples only.

   1. RECOVER THE ACTUAL STATE

   Read:
   - AGENTS.md
   - docs/agent-preflight.md
   - docs/simplification-handoff.md
   - odd/tasks/living-synthesis-adoption.md
   - docs/knowledge-workflow.md
   - examples/numbered-notes/README.md
   - docs/implementation.md
   - docs/review-contract.md
   - The existing proposal, check, save and recovery implementation.

   Inspect Git status, diff, staged and untracked files before editing. Preserve existing
 work.

   Last observed baseline: main at f18c15a, with uncommitted documentation changes in:
   - docs/knowledge-workflow.md
   - examples/numbered-notes/README.md
   - docs/implementation.md
   - An untracked operational tracker: odd/tasks/living-synthesis-adoption.md

   Verify this fresh; do not assume it remains unchanged.

   The previous tracker describes a COMPLETED DOCUMENTATION delivery, not an implemented
 allocator. Preserve its history. Create a separate implementation tracker or an explicitly
 linked continuation rather than silently rewriting its original scope.

   Last observed verification:
   - 3 focused numbered-note tests passed.
   - Full existing suite: 165 tests passed.
   - 17 documentation links/fragments and 5 JSON/Canvas files validated.
   - No allocator or real-library migration was implemented.
   - Engram cross-project mirroring was unavailable; the local tracker preserved continuity.
   These are historical observations, not verification of your new changes.

   2. PRESERVE THESE AGREED PRODUCT RULES

   A. Reading unit
   Prefer living integrated syntheses: coherent explanations with headings, original
 citations, limitations, connections and open questions.
   Seeds may remain fragments in conversation or drafts; do not require an atomic file for
 every thought.

   B. Bottom-up thematic organization
   Within this OPTIONAL profile, every retained synthesis has one thematic primary MOC.
   Associate an existing MOC or propose the synthesis and its new MOC together.
   Do not prebuild empty taxonomies or create MOCs merely because a source was captured.

   C. Catalogs are not thematic MOCs
   Generated inventories of sources, notes or other types are catalogs.
   Reserve thematic MOCs for meaningful reading routes.
   Do not automatically number every object whose technical role is map.

   D. Numbering
   - MOC 001 has syntheses 001-01, 001-02, etc.
   - MOC 002 has its own sequence: 002-01, 002-02, etc.
   - Seeds receive no synthesis address.
   - Progression to Evergreen does not change the address.
   - Referencing a synthesis from another MOC does not duplicate or recode it.
   - A real primary-MOC move assigns the next available destination address, preserves the
 SAME technical identity and reconciles previous references.
   - Preserve former-address history/reservations under the agreed convention. Do not
 silently recycle gaps or assume incomplete history means availability.

   E. Identity and evidence
   Human addresses are not technical IDs.
   Preserve existing IDs, authorship, original evidence, source versions and historical
 decisions.
   Where an existing library cannot separate identity from its current address, do not
 rewrite its identity to make the new convention fit.

   F. Intellectual thread
   Keep reasoning and lineage inside the integrated argument and relevant links/section
 citations.
   No separate traces registry, duplicate knowledge store or full-chat ingestion.

   G. Compatibility
   Preserve current Core v2 source/note/map vocabulary and note-only maturity.
   Do not restore superseded roles, mandatory review metadata, compulsory folders or globally
 mandatory MOCs/tags.
   Existing libraries may retain other conventions.
   Obsidian, K-Plex and Dataview remain optional surfaces.

   3. IMPLEMENT ONE SHARED PATH

   Reuse existing reader/proposal/check/save/recovery functions.

   Extend the current review/save skill where necessary; do not add a fifth skill or another
 writer.

   Implement one small deterministic numbering module, integrated with the actual preparation
 and validation paths:
   - Reuse an existing address when appropriate.
   - Propose an available MOC or synthesis address.
   - Validate eligibility, primary association and collisions.
   - Support deliberate primary-MOC recoding with reference/history reconciliation.

   Prepare the complete numbered candidate BEFORE exact human review.
   Recheck scope, identity, base/evidence versions and address availability BEFORE permitted
 saving.
   If anything changed, stop and prepare a new candidate; never silently renumber an
 already-reviewed draft.

   Do not claim concurrency safety or multi-file atomicity beyond what is actually
 implemented and tested. Preserve stronger local managed-writer requirements. An unavailable
 writer blocks dependent writes, not reading or proposal preparation.

   Choose the minimum compatible representation after inspecting current code. Avoid
 duplicate allocation logic in skills, commands, views or examples.

   4. VERIFY THROUGH PUBLIC INTERFACES

   Use isolated synthetic fixtures, not a personal library.

   Cover at least:
   - Independent MOC sequences and successive synthesis addresses.
   - Seeds remaining unnumbered.
   - Stable identity/address during ordinary updates and maturity progression.
   - Secondary-MOC references without duplication or recoding.
   - Explicit primary-MOC moves and reconciliation of the previous address.
   - Collision, stale-version, invalid-scope and incomplete-history rejection.
   - Rejected operations preserving stored content and relevant allocation state.
   - Existing unnumbered workflows and save/recovery behavior remaining compatible.

   Use test-first for the new deterministic behavior. Keep code, focused tests, help text and
 documentation together.

   Verified full-suite entry point:
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests

   Do not append an extra positional dot.
   Follow the host’s timeout/background rules; do not automatically retry failed checks.

   Inspect every publication candidate, including untracked files. Validate affected links,
 JSON/Canvas and whitespace. Do not confuse synthetic tests with scientific validation,
 authenticated human acceptance, native graphical integration or a completed real-library
 pilot.

   5. FINISH THE DELIVERY

   - Work on a non-destructive feature branch, not directly on main.
   - Reuse and reconcile the existing documentation; do not write a parallel guide.
   - Update “future/not implemented” claims only for capabilities actually delivered.
   - Keep the adoption plan generalizable and distinguish implemented mechanics from a future
 owner-authorized library pilot.
   - Run applicable functional checks and the existing suite.
   - Follow the actual repository/host review policy. Commit/push authorization does not
 manufacture provider consent or review approval.
   - Inspect every staged file for scope, secrets and private material.
   - Make coherent Conventional Commits with their tests and docs.
   - Verify the configured remote belongs to the intended Core repository.
   - Push the feature branch without force.
   - Do not merge, release or create a pull request without separate authorization.

   Complete executable in-scope work rather than repeatedly asking whether to continue. Stop
   only for a real unresolved product decision, required permission, conflict or
   unavailable/failed proof, and report the precise blocker.

   FINAL REPORT

   Return:
   - What was implemented versus still unimplemented.
   - Changed components and compatibility boundaries.
   - Passed, failed and not-run checks.
   - Branch, commit hashes and push result.
   - Any limitations concerning native integration or real-library adoption.
   - The next concrete adoption step.

   Do not claim that a personal wiki was migrated or that knowledge was scientifically
 reviewed.

- L2 — Fresh baseline confirmed main@f18c15a, exactly three documentation modifications (+159 lines), no staged changes, and only the completed adoption tracker untracked. origin fetch/push is https://github.com/Luissalazarmd/llm-wiki-core.git; remote HEAD is main@f18c15a. Created non-destructive feature branch. Historical tracker remains byte-for-byte unchanged.
- L3 — Read-only map and implementation readback establish one-file proposal/save/recovery, explicit scoped configuration, and no current multi-file transaction or authenticated approval. Implementation is large because custody/reference/recovery constraints must survive interruption, not because of file count. Forecast approximately 900 authored lines plus preserved documentation/tracking. No PR is authorized or being planned; retain coherent work-unit commits rather than manufacturing a PR chain.
- L4 — Design: optional config selects bounded Markdown scopes and explicitly declares complete custody/history. A small numbering module uses quoted human addresses distinct from explicit stable IDs, primary links to stable file paths, and per-note former-address reservations. No independent counter/registry. Batch preparation may co-propose MOCs and syntheses; saves remain sequential, explicitly non-atomic with existing per-file recovery. Moves preserve paths/headings, reserving old addresses; unsafe recovery that would free reservations is refused. Semantic quality and actual human consent remain outside deterministic validation.
- L5 — Runtime context backstop fired after tracker creation. Original bounded writer task mvtrl1oi-2-ra57 returned partial with no files changed; it ran test discovery before creating tests (exit 5, zero tests), which is not RED evidence. Existing new-note tests: 9 passed; writer tests: 10 passed. One correction batch, mvtrmh4i-3-6xgw, then wrote tests/test_living_synthesis.py (235 lines) but again returned partial without implementing anything. Its focused discovery failed all 13 tests, mostly at unsupported living_synthesis config and absent CLI options. These are provisional contract tests, not independent rule-by-rule RED/GREEN proof. No GREEN, refactor, allocator or candidate validation was delivered.
- L6 — The parent read all 235 new test lines and fresh Git state. Existing docs remain exactly the original +159 lines; source/runtime/skill files are unchanged. The new test file and both trackers are untracked; nothing is staged. Parent git diff --check passed for tracked changes, not a claim of complete publication checking. Remote verification and branch creation passed; no commits or push occurred.
- L7 — Native ASSESS was unavailable for this candidate because untracked scope was undeclared; it admitted no classification/approval. Agent escalation named item 2 for intended writer/scope guards, but no guard implementation exists. No native review or consent was started. Independent verifier, full suite, differential comparison, links, JSON/Canvas and publication clearance are not run: the incomplete failing implementation is not ready for those checks. Do not retry checks or claim historical 165 tests verify this work.
- L8 — Full Engram mirror unavailable through worker role: it refused raw-instruction persistence and lacks observation readback. Parent saved a continuity summary under odd/living-synthesis-implementation/tasks; the full current local document remains authoritative and a full mirror is still pending. No cross-project registration or installation was attempted.
- L9 — Stopped under the host's exhausted-correction rule, not because the owner withdrew implementation/commit/push authorization. T1 is narrowed to verified recovery; RED belongs to incomplete T2. Needs owner decision: authorize a fresh bounded implementation attempt (with the provisional tests and this tracker), or retain this partial state for later. Until implementation and required proof exist, no commit/push or completion claim is appropriate.
- L10 — User requested read-only diagnosis: "Before requesting another implementation attempt, diagnose why the delegated writer and its correction returned partial." Actual results/status showed normal completion, not a reported timeout/provider/tool failure. Observable failure was premature finalization with unfinished implementation. First memory mismatch was explicitly waived in correction; second still did not implement. Thirteen tests are provisional entry-point RED, with missing move/secondary-reference/reservation/public-output assertions, not thirteen independent rule-level RED proofs. No files changed during diagnosis.
- L11 — User: "no entiendo bro que pasa? osea el harness no funciona? volvemos a empezar mejor?" Parent recommended preserving all work and resuming via one functioning end-to-end vertical slice. User authorized: "si". Reopened T2; original implementation/verification/commit/push scope remains, without destructive reset or renewed exploration. Smaller working slices replace the failed broad handoff; full remaining specs are not dropped. No claim of a technical harness crash is made.
- L12 — First working slice mvts5qbj-4-n461 delivered scripts/numbering.py, proposal/check/save/restore integration, five public-CLI tests and first-cut-tools documentation. RED: two tests failed at unsupported config; GREEN: five core tests passed, nine creation and ten writer/recovery tests passed. Parent read source/tests/diff and independently reran the five core tests: passed in 2.372 s. No original provisional tests were deleted or skipped; remaining co-proposal/move/reference behavior is still outstanding. ASSESS remains unassessable until intended untracked scope is declared; risk escalation item 2 retains independent verification before delivery. No native authority started. T2 stays in progress, not complete.
- L13 — Dependent writer mvtsdhc7-5-vkps again returned partial without an identified technical blocker: added maturity validation and strengthened state snapshots, but left three move/batch tests failing. Parent performed the permitted correction batch inline instead of another broad handoff: one shared postimage planner, batch co-proposal/check/save, stable-ID/path moves reserving old addresses, explicit reference-scope assertion, exact heading resolution and visible destination-map companion links. Sequential I/O failure reports completed paths and private records without automatic rollback; restore cannot release recoding reservations. Focused run after correction passed 19 synthesis tests, 5 core tests, 9 existing creation tests and 10 existing writer/recovery tests (43 total); no failed tests remain in those groups. Reconciled current docs/entry/skill claims while keeping original documentation tracker and dated native evidence unchanged. T2 complete subject to final T3 verification; native approval, migration and scientific validation are not claimed.
- L14 — Full suite launched exactly once for the first candidate via background runner job-1 with the authorized discovery command; result was 189 tests, one failure in the synthetic demo's copied runtime because numbering.py was missing. Independent verification mvtsu39z-6-fxgl found one blocking batch defect: child save skipped numbering recheck after recovery persistence and could publish a newly colliding address. Existing numbered single-file guard worked in that probe. No PR, merge, release, force-push or personal-library operation is planned.
- L15 — One bounded verifier correction batch: reproduced the batch publication defect RED through public CLI fault injection, then passed expected scope into child saving and rechecked after recovery persistence AND staged fsync immediately before publication/replacement. Added persistent regression at both boundaries, retaining competitor/current bytes and no target publication; recovery record is intentionally retained. Updated demo's copied runtime dependency. Targeted re-verification mvtt5fxw-7-t6su independently passed the original reproducer plus both boundary injections: exit 2, empty stdout, exact partial JSON error, completed=[], no published target or staging file, existing/competitor bytes preserved. Original verifier's other S# verdicts stand; no concurrency/atomicity claim.
- L16 — Corrected candidate verification: 57 focused tests passed (20 synthesis, 5 core, 9 creation, 10 recovery, 13 library/demo). Full suite job-2 passed all 190 tests in 24.723 s, exit 0. This was a new run after actual code fixes, not an unchanged retry; initial failure remains L14. Active LSP checked six changed Python files: all clean, no unavailable/unsupported coverage. One parent differential script against isolated f18c15a copy observed identical exit/stdout/stderr for map, read, proposal, check, save, restore, capture refusal and malformed configuration; UUID generation fixed equally in both runs for deterministic output. Parent checked 45 affected local links/fragments, five JSON/Canvas files, whitespace and all 15 tracked/untracked publication candidates; no personal paths or secret patterns found. These checks establish mechanics only, not scientific validity, authentic human acceptance, native integration or a real-library pilot.
- L17 — Work-unit boundaries: 95a505a preserves only the historical tracker; 494b381 includes the shared module and its coupled writer guards/tests/docs, 1,578 authored diff lines including this full operational record, exceeding the advisory 400-line review slice. No tests/docs were omitted or minified to fit. No PR was authorized; PR shape/slicing remains an owner's later decision. Native review targeted this committed unit against 95a505a, not an accumulated feature-branch review. After staging all intended files, ASSESS classified the candidate high; host consent created review-059d6c3efd4c8af5.
- L18 — Four native lenses and one refuter corroborated R3-block-history: valid block-style former_addresses followed by another metadata key lost its separating newline during a second primary move. Provider accepted an 80-diff-line correction plan (distinct from its 200 logical-correction budget). LF and CRLF public move tests both observed RED with Invalid frontmatter; one bounded fix preserved separator whitespace and all existing ID/author/custom metadata/body/history. Correction f2637fb changed only scripts/numbering.py and its regression tests: 39 additions plus one deletion, 40 diff lines. Focused 22 synthesis and five core tests passed; final full suite job-3 passed 192 tests in 23.123 s, exit 0. Active LSP on both corrected files passed.
- L19 — Native targeted validator approved the corrected candidate. Exact facade acknowledgement returned native-approved-acknowledgement-completed, authority burned, target sha256:ca166900b9be5c9d1caea28510e1db4a9e7c7a92f6040152c2d3a9a16405c94b. No STATUS was issued after the burn. One nonblocking informational advisory remains: R4-postimage-budget at scripts/note_write.py:161; provider explicitly offered no further correction/review for it. No native verdict was authored by Pi, no consent inferred from push authorization, and no maintenance/recovery operation was used.
- L20 — Source delivery job-4 pushed feat/living-synthesis-numbering without force to verified origin https://github.com/Luissalazarmd/llm-wiki-core.git; exit 0. git ls-remote matched local source HEAD f2637fb82d6bee38b1675aab857e5d094f88ff4c. No PR, merge, release, history rewrite, installation or personal-library access occurred. This final tracker-only closure changes no reviewed source/test bytes. Parent handles full-document memory reconciliation; the earlier worker-only limitation in L8 remains historical.
- L21 — Adoption next step: after separate owner authorization, establish one bounded local collection's rules/identity/reference correspondence and permitted writer, then prepare one useful integrated synthesis with an existing or co-proposed thematic MOC for exact human review. No migration, native graphical integration, authenticated library acceptance or scientific review is delivered. Unknown history/unsupported address-based identity or reference conventions stay proposal-only. Sequential plain-file saves are not a lock, multi-file transaction or automatic rollback engine.
