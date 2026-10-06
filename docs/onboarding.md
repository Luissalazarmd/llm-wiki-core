# Onboarding checklist

This checklist collects decisions. It does not activate integrations.

1. **Purpose and boundaries:** what knowledge belongs in the instance, what must stay out, and whether personal memory is needed. Keep personal memory separate from bibliography.
2. **Single core folder:** use this repository as the private vault. Install the licensed engine into it from authorized local files. Do not migrate an old vault or history implicitly. Choose whether selected Raw/Review/Wiki content will later be versioned in this same private GitHub repository.
3. **Devices:** list operating systems and which device will be the canonical writer. Mobile devices may read and capture; they do not automatically become engine hosts.
4. **Synchronization:** select exactly one vault sync provider using [sync guidance](sync.md). Make backups before first sync or migration. Configure exclusions on each device and test an innocuous note round trip.
5. **Obsidian:** open this core folder as a vault. No community plugin is required. Review any optional plugin's permissions before installation.
6. **Task application:** select none, an existing task app, or an adapter to implement later. Decide read-only versus explicitly authorized write actions.
7. **Calendar application:** make a separate choice, including none. Choose a time zone and target calendar in ignored local configuration.
8. **Host and authority:** select an authenticated human-review channel, a single writer host, a protected audit store, and a recovery owner. Without these, keep all operations read-only/proposal-only.
9. **Engine:** run the [local installer](local-integration.md), then verify the read-only review CLI. Complete authenticated-host integration before enabling real-content apply; the synthetic test does not authenticate a user.
10. **Language:** internal instructions remain English; replies follow the user’s language. Optionally ask for a preferred Wiki language. Default to Spanish (`wiki_language: es`) if no preference is supplied; this question is not a blocker. Preserve original source titles, citations, and quotations, and label translations.
11. **Recovery rehearsal:** verify backup restore, stale approval rejection, conflict handling, and restart/replay behavior on synthetic fixtures.

Use [the example configuration](../config/example.json) as an inert record of choices. `null`, `unselected`, and `unconfigured` mean setup is incomplete; they are not permissive defaults. Put actual configuration in local ignored files in this same folder, and credentials in a secret store. Never paste credentials into review packets or commit them.
