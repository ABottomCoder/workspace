# Heavy Track (opt-in per business)

Enabled by `tier: heavy` in `business/<co>/CLAUDE.md`, typically for teams with formal ticket systems,
reviewers and stakeholders who read reports. Everything in [light-track.md](light-track.md) still applies;
these are added.

| Added step | When | Detail |
|---|---|---|
| Full context sweep on ticket intake, unprompted | Phase 1 | [ticket-lifecycle.md](ticket-lifecycle.md#phase-1-intake) |
| Ticket comments: Plan Rationale + Execution Plan | end of Phase 1 | same |
| Approver confirms the plan before code | end of Phase 1 | [communication.md](../principles/communication.md#authority-and-approval) |
| Versioned HTML test report | Phase 2 | [reporting.md](reporting.md) |
| Independent QA session, joint sign-off | after self-test, before reporting | [qa-session.md](qa-session.md), skill `/qa` |
| HTML ticket report with embedded evidence | Phase 3 | [reporting.md](reporting.md) |
| Push + PR per convention, completion notice to approver | Phase 3 | [ticket-lifecycle.md](ticket-lifecycle.md#phase-3-reporting-and-knowledge-capture) |
| Intervention-log row per ticket | ticket close | [intervention-tracking.md](intervention-tracking.md) |
| PR-review protocol (six lenses, evidence gate) | when asked to review someone else's PR | [pr-review.md](pr-review.md) |
| Multi-agent harness | only on explicit request | [multi-agent-harness.md](multi-agent-harness.md) |

Ticket-system specifics (fetching, field mapping, posting comments) come from the adapter named in
`business/<co>/stack.md`: [ticket-system adapters](index.md#ticket-system-adapters).

A light-tier business can still use any single heavy step when the user asks for it (a QA session, a
formal report); the tier only sets the default.
