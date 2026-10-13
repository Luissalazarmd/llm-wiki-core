# Synthetic acceptance specification

**Acceptance specification, not a claim of a full executed suite.** Bounded earlier engine results are recorded in [local integration](local-integration.md); the original ontology/catalog tests are separately runnable under [ontology](ontology.md). All examples use synthetic fixtures and a test host. No real accounts, sources, personal data, or production vaults are needed. Implementation must produce machine-checkable results and retain evidence of each run.

## Fixture

Use a temporary instance containing a synthetic source, one canonical note, and one proposed change. Capture canonical file hashes and all durable-state hashes before each test. The trusted test host supplies authenticated human events; model output cannot impersonate that host. Use separate synthetic principals for proposer and reviewer.

## Required cases

1. **Read-only list/show/packet:** repeated listing, revision inspection, and packet rendering return consistent data and do not change canonical or durable state, statuses, or timestamps. Rendering must not mark reviewed or approved.
2. **Exact binding:** approve revision R and etag E from the authenticated host; change either field or any bound payload; apply rejects it without mutation. Editing the diff creates a new revision and requires new approval.
3. **Human authenticity:** model-supplied actor flags, typed names, Markdown checkboxes, quoted approvals, and imported chat text cannot authorize apply. A verified user event approves only its explicit packet and action.
4. **No self-approval:** both roles are denied approval authority, even when they generated a convincing approval message or possess proposal-write access.
5. **Stale base/source:** modify the canonical base or relevant source version after packet generation; reject apply and require reconciliation and a fresh packet.
6. **Replay:** applying a valid decision once succeeds; identical retry returns the same outcome with no duplicate effects; altered reuse is rejected. Verify after host restart.
7. **Single writer:** concurrent apply attempts cannot interleave. After takeover, a previous writer is fenced out. Lost locks block mutation rather than fall back to best effort.
8. **Canonical path only:** direct agent Wiki writes and alternate mutation entry points are denied. Traversal and symlink escape attempts cannot reach files outside the allowed targets.
9. **Prompt injection:** source text asking to approve, change policy, reveal secrets, run tools, or overwrite files remains quoted data. It cannot modify authorization or trigger external actions.
10. **Offline:** disconnected clients may read and capture drafts; apply without authoritative approval/state/lock fails closed. Reconnection does not auto-approve or replay queued mutations.
11. **Conflicts:** concurrent manual note edits and sync conflict files are preserved for reconciliation, invalidate affected packets, and never use silent last-write-wins canonical apply.
12. **Crash consistency:** inject failure before content write, during transaction, after content commit, and before response. Recovery yields a coherent before-or-after state and a durable consumed-decision record; retries never duplicate a committed action.
13. **Revocation/expiry:** under the chosen host policy, revoked or expired approvals are rejected; an unavailable policy service does not bypass checks.
14. **Separation:** personal-memory inputs cannot silently enter bibliographic evidence; a DOI does not make a synthetic low-quality source trustworthy.
15. **Adapter boundary:** Wiki approval does not permit task/calendar writes, messages, or third-party uploads. Unconfigured adapters fail closed.
16. **Publication boundary:** the original-code delivery contains generic code and synthetic fixtures only. Licensed engine files, credentials, local settings and operational state are excluded from publication. Selected real Raw/Review/Wiki content may be versioned in this same private repository only within approved scope; local presence is not upload approval.
17. **Recovery and bootstrap:** a fresh host installs the pinned licensed runtime separately from note sync, then restores canonical content and required durable state consistently. Missing replay state blocks apply.

18. **Language policy:** internal instructions remain English; replies follow the user’s language; new Wiki notes default to Spanish when no preference is supplied and use an explicitly configured alternative when present. Source titles, citations, identifiers, and original quotations remain exact; translations are labeled and never misrepresented as original text. An unanswered optional language question does not block work.

Passing document syntax/link checks is not a substitute for these engine tests. Report each case as passed, failed, blocked, or not run against an exact engine revision.

## Guided knowledge and navigation cases

- Flat/grouped capture identity and byte preservation; duplicate identities, symlinks and invalid paths rejected.
- Role/maturity/review independent; declared accepted metadata cannot authorize apply. Current projector reports it unverified.
- Connections include reasons; factual connections require exact source hashes and locators. Changed evidence blocks projection; locator meaning still needs source review.
- Focus excludes source bodies and unrelated neighbors, with explicit count/byte limits.
- Plain Markdown links and optional K-Plex view grouping retain original files. Real host rendering must be separately tested.
- No per-article thematic folder, duplicate bibliography or mandatory note creation. Existing knowledge is reused.
- Conversational explain/alternative/change/accept/ambiguous/stale requests follow exact object/version gates. An unconnected host stops at proposal, never fabricated approval.
