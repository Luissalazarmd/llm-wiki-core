# Daily Focus

An on-demand, read-only Orquestador workflow for requests such as “Daily Focus”, “¿En qué me enfoco hoy?” or “What deserves attention today?”. This is an instruction contract for a capable host, not a scheduler, activated agent, or new model dependency.

## Inputs and scope

1. Establish today's date and the user's verified time zone. If the zone is unknown, ask only when timing depends on it; otherwise state the assumed zone and avoid precise scheduling.
2. Read the short, user-confirmed Principles and current Priorities context. Stable decision criteria belong in Principles; dated, active priorities belong in Priorities. Treat unconfirmed, expired, completed, archived, or superseded entries as context to verify, not active commitments. Never populate these notes from inferred personal goals.
3. Read authorized task and calendar sources for a seven-local-calendar-day window: today through the end of the sixth following day, plus currently open overdue tasks. Narrow to confirmed active projects and commitments; check completion/cancellation and last update before recommending work. Follow pagination within that scope, or disclose incomplete coverage. Refresh decisive task status, deadlines, and calendar availability for this run when accessible. If only a dated snapshot is available, label recommendations as of that snapshot and do not assert current status or availability; an unknown observation time is a relevant evidence gap.
4. Open a linked conversation or project note only to resolve a specific candidate's status, deadline, dependency, or next action. No default sweep of journals, message history, or all projects. Raw references and pending Review proposals are not task commitments.

Use the provider/location mapping below. Verify access for this run; a documented connector is not evidence of a live connection. If a decisive source is missing, mark the result partial and name the unknown. Continue with supported actions or return none; do not fill three slots with guesses.

## Choose and answer

- Return zero to three concrete next actions. Rank by explicit current priorities and principles, verified deadlines/consequences, dependencies, and available time. Explain a real tradeoff briefly; do not equate message volume or busy projects with importance.
- Each action has a next step, why it matters now, and its task/event/context source with a verified link or exact available identifier. Separate source facts from your recommendation. Include a due date or usable time window when supported; do not invent duration, availability, or a deadline.
- Ask at most one decision question, only if a genuine conflict or missing choice changes the recommendation. No compulsory work/life conflict, reflection questions, overdue goal, or productivity reproach.
- Missing journal entries mean missing evidence. Late logging does not establish a wasted morning. Neither supports claims that a habit or commitment was missed.
- Finish with a short evidence footer: sources actually read, observation time, date/time zone, query window, context confirmation/update dates, and meaningful gaps or conflicts. Distinguish “no relevant items found” from “source unavailable”.

Suggested response shape (match the user's language):

> Focus for [date, time zone]
> 1. [Next action] — [reason now]. [Source; deadline/window if known]
> [Up to two more actions, only when supported]
> [One decision question, if necessary]
> Evidence: [read sources and observation time]; window [start–end]; context [confirmation dates]; gaps [if any].

## Writes and knowledge boundary

Daily Focus only reads and replies. It does not change task status, create events, message others, save a daily note, update Principles/Priorities, or run the librarian as a side effect. A separate explicit request follows the existing authority rules for that action. Storing context requires an approved destination and only user-confirmed content. Keep personal context outside Raw → Review → Wiki; sources, reviews, and canonical knowledge retain their existing workflow.

## Provenance

Original selective adaptation of James Bedford's [Today's Focus](https://gist.github.com/jameesy/e6a313adff55d57fd33226abc08e4c69/7ac5571568d0567baa580078b9a64ed5a021f8b5). The external prompt is a reference, not an authority. No verbatim skill, author-specific account data, or automatic execution is imported.

## Provider-neutral setup

Use only the task and calendar providers selected independently during [onboarding](../docs/onboarding.md), including none. Do not add a provider, account, permission, or model dependency for this workflow. Confirm timezone and read capability for the run. A user-supplied dated snapshot can be used with its limitations stated.

| Function | Selected source | Bounded read |
|---|---|---|
| Stable criteria | Authorized personal-memory Principles record | Confirmed active criteria and confirmation dates |
| Current priorities | Authorized personal-memory Priorities record | Current section and confirmation/review dates |
| Tasks | Selected task adapter, or explicit snapshot | Open tasks in the window and confirmed active projects |
| Calendar | Independently selected calendar adapter, or explicit snapshot | Events and availability in the window |
| Candidate context | Authorized linked project/conversation | Only the unresolved candidate |

Generic starter records are [Principles](templates/principles.md) and [Priorities](templates/priorities.md). They are examples, never live personal context. At the user's request, initialize them in the separately authorized personal-memory store, for example `private/orchestrator/` inside this same core folder (already ignored). Record the chosen location in local configuration; do not add an unimplemented runtime setting or assume automatic loading. Do not copy private records back into the reusable templates or the knowledge pipeline. Ignored context is not disposable: use the chosen private backup/sync policy. If the user already has equivalent records, reference those rather than create duplicates.
