# AI Project Playbook (Lite)

Scope: building client software with AI agents, from the first requirements conversation until local acceptance passes and code and documents are handed over. Deployment, launch and operations are out of scope; humans arrange them separately.

Relationship to the full playbook: this is the condensed version of `docs/playbooks/ai-project-playbook.md`, which remains the reference for detail and templates. Once the project lead confirms, a project may run on this version alone.

Quality bar: the system's quality requirements live in `docs/playbooks/production-playbook.md` (below, "the production playbook"); this playbook covers process only.

## 1. Flow

1. Requirements interview: using the client-signed proposal as baseline, turn every ambiguity into a decision or a question.
2. Requirements document: write one, review it independently once; after freeze the project lead says GO (G1).
3. Kickoff prep: acceptance criteria, money rules (if payments), work split.
4. Foundation: skeleton, data model, API contract, third-party abstractions, money core; parallel work starts only after the foundation review passes.
5. Parallel development: several agents build by module; each block is reviewed and merged when done.
6. Black-box acceptance: a tester agent that sees only the requirements tests item by item; fix and retest until passing (G3).
7. Handover: deliver code, documents and a deploy-notes draft.

## 2. Roles

| Role | Who | Owns |
|---|---|---|
| Project lead | Technical lead on our side | Scope decisions, G1 / G3, acceptance verdict; neither writes nor reads code |
| Account manager | Our client-facing lead | All client communication, price, schedule; opens third-party test accounts |
| Client | The customer | Answers must-answer questions; supplies assets and legal text |
| Lead AI | One session dedicated to this project | Writes documents, makes technical calls, dispatches, merges, records, reports; does no heavy work itself; never contacts the client directly |
| One-shot AI | Developer, fixer, reviewer, tester agents | Completes one block per its brief and reports |

## 3. Gates

| Gate | When | What is confirmed |
|---|---|---|
| G1 Kickoff | Requirements frozen | GO; track (section 4); non-functional preferences |
| G2 Scope change | Any time | New features outside the requirements, or changes to scope, cost or schedule |
| G3 Local acceptance passed | End of acceptance | No blockers or criticals; all P0 acceptance items pass; local tests pass |

Everything else needing a human: the AI proceeds with the default, marks it "to confirm" in DECISIONS.md and in reports, and a human can overturn it at any time. Copy the approver (the business owner) on anything involving money or client commitments.

## 4. Small-project track

Take the small track only if all three hold: at most 3 user roles; at most 15 pages; a single merchant collects payment (no automatic split payouts to multiple sellers).

Differences: one spec document only (feature items, effort, P0 acceptance checklist, plus money rules if payments); one developer agent; only G1 and G3; production-playbook tests may be reduced in scale, with the reduced scope written into DECISIONS.md beforehand.

## 5. Stage key points

**Requirements interview**
1. List every difference from the signed proposal; the project lead confirms each.
2. For every topic ask both "how does it normally go" and "what happens when it goes wrong": roles and accounts, main flows, money flow (commission, fees, refunds, deposits, multiple sellers), failures (cancellation, timeout, duplicate payment, refund failure, concurrency), notifications, admin, third-party dependencies.
3. Give a default for every open question; send only questions only the client can decide (at most 5) to the client via the account manager.

**Requirements document**
1. One shared online document, edited in place, never saved as new versions; questions and features use stable IDs (e.g. `F-ORDER-CANCEL`).
2. The feature list has effort columns (section 9).
3. Before freeze, a fresh agent reviews it independently once; fix every MUST before freezing.
4. The AI produces the client version by stripping internal content (and translating if needed); the account manager sends it.

**Kickoff prep**
1. Acceptance criteria: at least one per requirement, marked P0 / P1; the project lead confirms the split.
2. Money rules (if payments): how money moves in each case; how to handle third-party uncertainty (success / failure / timeout) crossed with local write failure; invariants that always hold (e.g. "refunded + transferred <= collected"), written as property-based tests.
3. Work split: agents by module, each with its own worktree, database and port.

**Foundation**
1. A foundation agent builds the complete data model, API contract, third-party abstractions (stub and real), money core, logging (with `trace_id`), security baseline and demo-data script.
2. Day 1: verify key third-party assumptions with our own test accounts; record results in DECISIONS.md.
3. Never skip the foundation review.

**Parallel development**
1. Only the lead AI may change the API contract and data model; a developer agent that needs a change writes NEEDS.md and the lead AI handles it immediately.
2. Port the frontend 1:1 from the prototype; switch to real endpoints as soon as they exist.
3. Review and merge each block when done; do not wait for everything.

**Black-box acceptance**
1. The tester agent gets only the requirements, acceptance criteria, environment URL and test accounts; never code.
2. Before each round, rebuild the environment to the commit under test with a fresh database.
3. Real browser at desktop and mobile widths, plus direct API calls for privilege escalation and duplicate submission. Every round run the interaction check: previous user's data after switching accounts, refresh and back, double-click resubmission, duplicate orders after close-and-reopen.
4. One fixer agent fixes all of a round's issues, then a targeted retest, until G3 is met.
5. Main and derived projects are accepted separately.

**Handover**
1. Local repository path and the commit that passed G3, to the project lead; pushing and hosting are done by humans.
2. Documents: FOUNDATION.md, DECISIONS.md, BUGS.md, acceptance criteria and reports.
3. Deploy-notes draft: environment variables (names only), third-party accounts, migration order, placeholder content to replace, known risks and unverified third-party assumptions.

## 6. Rules

**Shared rules for developer agents** (attach to every developer and fixer brief)
1. Simplest solution that meets the requirement; build nothing that is out of phase 1.
2. Use only the assigned directory, database and port; tests connect only to databases ending in `_test`.
3. Without a key, use the stub; never print or commit secrets.
4. Money in integer minor units only, only through the money core, balances recomputed from the ledger, state changes via conditional update or lock, every third-party payment call carries an idempotency key.
5. Every operation checks ownership, not just role.
6. Structured logs at key points with `trace_id`; never log personal data, verification codes, tokens or card numbers.
7. Every feature has tests; report only when type check, tests and build pass.
8. Rules the requirements do not cover: do the most reasonable thing and mark "to confirm" in the report.

**Review**
1. Money, permissions, authentication, data deletion, plus the foundation and every backend module: fresh agent, independent review, re-review after fixes. Frontend pages: developer self-review, backstopped by black-box acceptance.
2. Severity: MUST (wrong accounting, lost money, privilege escalation, data loss, does not meet requirement, crash) blocks merge; each SHOULD decided fix / no fix; NIT optional.
3. Same spot produces a MUST in two consecutive rounds: stop patching and redesign.

**Local tests before G3** (an independent test agent runs them on the commit to be released, keeping raw output)

Business tests and money property tests; concurrency tests (operations touching money or state); timeouts and malformed input; security scans (code, dependencies, secrets across full git history) and privilege-escalation tests; log checks (one complete business flow traceable by `trace_id`; no plaintext passwords, card numbers or tokens in logs).

Tests needing a real domain, staging or production are not run locally; list them in the deploy-notes draft. Skipping any production-playbook item requires the project lead's release in DECISIONS.md.

## 7. Red lines (no track waives these)

1. Security baseline: secure cookie defaults, cross-site request protection, rate limits on login and email endpoints; privilege-escalation tests.
2. Secrets never in code, logs or documents.
3. No sensitive data in logs.
4. Money idempotent; no data loss.
5. AI commits to local git only: no push, no deploy, no servers, no client or real third-party accounts (sole exception: our own test accounts against third-party test modes).

## 8. Records and reporting

| File | Content |
|---|---|
| `DEVDOC.md` (local, not in git; template `templates/project/DEVDOC.md`) | Status block (latest commit per branch, environment, waiting on whom, next step); task log; change log |
| `app/docs/DECISIONS.md` | Each decision: date, question, choice, who decided |
| `app/docs/BUGS.md` | Issues from review, acceptance and client feedback, with fix status |
| `qa/acceptance-criteria.md`, `qa/acceptance-roundN.md` | Acceptance criteria and each round's report |

1. After an interruption, read the DEVDOC status block first, then verify with git; answer "did we do X?" from records, never memory.
2. On trunk merge, end of an acceptance round, G3, handover, or anything needing a human decision, post a short message in the project channel. On pause, send the status block and wait for an explicit resume.
3. Everything for the client goes through the account manager; follow their formatting preferences (e.g. no dashes or divider lines).

## 9. Effort

1. The feature list's effort column is AI effort (lead AI plus all sub-agents, including review and fixes), estimated by feature type, plus a 15% risk reserve. Price = AI effort x pricing multiplier (set by the project lead and account manager).
2. Log one row per dispatched task in DEVDOC (feature, type, stage, start, end, review rounds, rework count); no token tracking for now.
3. Only projects that pass G3 and are handed over calibrate unit times; until there are samples, estimate by analogy with a completed reference project.

## 10. Derived projects (forks of the main project)

1. Preferably fork after the main project passes acceptance; otherwise sync every main-project merge across.
2. Generic fixes made in the derived project are back-ported to the main project.
3. Watch for migration timestamp collisions between the two.
