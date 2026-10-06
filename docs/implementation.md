# Implementation milestones

## M0: private baseline (this delivery)

Original documentation, two role profiles, inert config example, fixed stage-directory placeholders, and acceptance requirements. Validate syntax, internal links, privacy, and clear non-runnable status. This is not engine acceptance.

## M1: licensed engine mapping

Inspect authorized upstream source and license. Pin revision; document root layout and existing APIs; identify minimal clean reusable components. Resolve durable-state location and recovery policy. Gate: rights and compatibility reviewed, no personal data copied.

## M2: isolated synthetic instance

Install the reviewed runtime on one canonical host using a verified procedure. Provision an empty private instance outside the template, with synthetic input only. Gate: read-only list/show/packet demonstrably leave state unchanged.

## M3: authenticated review and canonical apply

Integrate the trusted human-chat host, packet binding, single writer, canonical apply, durable audit, and replay-safe recovery. Gate: all [acceptance cases](acceptance.md) pass, including crash recovery and adversarial content.

## M4: device and sync validation

Choose one provider; verify note round trips, offline capture, stale-base blocking, conflict handling, code installation, and backup restoration. Headless is optional. Gate: no hidden assumption that Sync replicates runtime or durable state.

## M5: optional task/calendar adapters

Choose providers during onboarding. Start read-only; test permissions and explicit write authorization on synthetic or safe test targets. Gate: approved Wiki changes cannot accidentally create external communications, tasks, or events.

## M6: controlled private use

Only after the prior gates, admit authorized real sources under retention/privacy rules. Observe audit and recovery behavior. Additional specialist roles and broad automation are out of v0.1 scope.

No milestone after M0 is claimed complete by this repository.
