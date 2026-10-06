# Onboarding checklist

This checklist collects decisions. It does not activate integrations.

1. **Purpose and boundaries:** what knowledge belongs in the instance, what must stay out, and whether personal memory is needed. Keep personal memory separate from bibliography.
2. **Private instance:** choose a new private vault location outside this reusable template's tracked content. Do not copy an old vault, source dump, account history, or runtime state into the baseline.
3. **Devices:** list operating systems and which device will be the canonical writer. Mobile devices may read and capture; they do not automatically become engine hosts.
4. **Synchronization:** select exactly one vault sync provider using [sync guidance](sync.md). Make backups before first sync or migration. Configure exclusions on each device and test an innocuous note round trip.
5. **Obsidian:** open the instance folder as a vault. No community plugin is required by this scaffold. Review any optional plugin's permissions before installation.
6. **Task application:** select none, an existing task app, or an adapter to implement later. Decide read-only versus explicitly authorized write actions.
7. **Calendar application:** make a separate choice, including none. Choose a time zone and target calendar in private configuration, never in the template.
8. **Host and authority:** select an authenticated human-review channel, a single writer host, a protected audit store, and a recovery owner. Without these, keep all operations read-only/proposal-only.
9. **Engine:** complete authorized licensed integration and acceptance tests before enabling apply. There is no installer in this baseline.
10. **Language:** internal instructions remain English; replies follow the user’s language. Optionally ask for a preferred Wiki language. Default to Spanish (`wiki_language: es`) if no preference is supplied; this question is not a blocker. Preserve original source titles, citations, and quotations, and label translations.
11. **Recovery rehearsal:** verify backup restore, stale approval rejection, conflict handling, and restart/replay behavior on synthetic fixtures.

Use [the example configuration](../config/example.json) as an inert record of choices. `null`, `unselected`, and `unconfigured` mean setup is incomplete; they are not permissive defaults. Put actual configuration and credentials in a private instance/secret store, not this repository. Never paste credentials into review packets or commit them.
