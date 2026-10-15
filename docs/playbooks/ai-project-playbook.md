# AI Project Playbook

Scope: building client software with AI agents. This playbook runs from the first requirements conversation until local acceptance passes (G3) and the code and documents are handed over. Deployment, staging, launch and post-launch operations are out of scope; humans arrange them separately.

Origin: distilled from real client builds (a two-sided marketplace with a derived sister product, and a small single-merchant MVP) and their retrospectives. Items marked "(Not yet proven in practice.)" are rules adopted from those retrospectives that no project has yet run end to end.

Readers: the project lead (does not need to write code) and any AI session that later acts as lead AI.

How to use: on a new project, follow section 0. Before each stage, read that stage's section; before moving on, run its checklist. Each rule lives in exactly one place; everywhere else only points to it. Templates are in the appendix.

Division of labour: this playbook covers process only (stages, gates, roles, review, acceptance, effort, records). The quality bar the system must meet lives only in `docs/playbooks/production-playbook.md` (below, "the production playbook"). This playbook cites its sections; section 2.8 says at which stage each is checked. Common AI-coding failure modes and countermeasures: `docs/playbooks/ai-coding-pitfalls.md`. A lighter summary of this playbook: `docs/playbooks/ai-project-playbook-lite.md`.

## 0. One-page overview

### 0.1 Stage flow

1. Requirements interview: using the client-signed proposal as baseline, turn every ambiguity into a decision or a question.
2. Requirements document: one document, independently reviewed once before freeze. After freeze the project lead says GO and confirms the track (G1, section 0.4). Work starts.
3. Kickoff pack (parallel): acceptance criteria, money model and kickoff plan are written at the same time; the client choice sheet and client answers run in parallel. Effort is estimated before the requirements freeze (section 5).
4. Foundation and API contract: skeleton, data model, complete API contract, third-party abstractions, money core. On day 1, verify third-party assumptions with our own test accounts.
5. Parallel development: several agents build in parallel along a module split.
6. Independent review: tiered by risk (section 2.2), once per finished block.
7. Black-box acceptance: a tester AI that sees only the requirements and acceptance criteria tests item by item, alternating full rounds and targeted retest rounds until passing (G3).

The final step is handover: after G3, hand over code and documents (section 1, "Handover"). The AI's work ends there.

### 0.2 Who does what

Principle: humans decide and accept; AI does everything else.

| Role | Who | Owns | Does not |
|---|---|---|---|
| Project lead | Technical lead on our side | Scope decisions; the gates (section 0.3); confirms the P0 / P1 split (after kickoff, does not block development); acceptance verdict; pricing multiplier (with the account manager) | Write or read code |
| Account manager | Our client-facing lead | All client communication and deliverables; price, schedule, contract; relays client answers and assets; opens the third-party test accounts the lead AI lists, target within 2 days of receiving the list | Change the technical design |
| Client | The customer | Answers client-must-answer questions; supplies assets and lawyer-written text | Read internal documents |
| Approver | The business owner | Is copied on anything involving money or client commitments (section 0.3) | Day-to-day decisions |
| Lead AI | One session dedicated to this project | Writes documents; makes technical calls; dispatches work; merges; records; reports (section 4); at the end of stage 1 lists the needed third-party test accounts (appendix A1 item 13) and gives the list to the account manager | Do heavy work itself; make scope decisions for humans; push, deploy, or touch servers or real third-party accounts (section 2.1 rule 14); contact the client directly |
| One-shot AI | Developer, fixer, reviewer, acceptance tester agents | Completes one block per its brief and reports | Change shared contracts; read material outside its remit |

### 0.3 Gates

Default behaviour: when something needs a human decision, the AI proceeds with the default, marks it "to confirm" in DECISIONS.md and in reports, and a human can overturn it at any time. The AI stops and waits only at the gates below, and for anything that changes scope.

| Gate | When | Who confirms | What |
|---|---|---|---|
| G1 Kickoff | Requirements frozen | Project lead | Says GO; confirms the track (section 0.4); answers once on non-functional preferences and test thresholds (stage 2 key point 3); budget cap (see below) |
| G2 Scope change | Any time during development and acceptance | Project lead (plus account manager if money is involved) | New features outside the requirements; changes to scope, cost or schedule; changes to business rules in the signed proposal |
| G3 Local acceptance passed | End of stage 7 | Project lead | Exit conditions met (section 2.3); production playbook local-testing criteria met (section 2.8, G3 row); whether failing P1 items may be released (Not yet proven in practice.) |

Budget cap: the account manager obtains it before G1. The main project starts after GO; if the cap is not yet known, mark it "to confirm" in DECISIONS.md; it does not block the main project. Derived projects and optional items start only once both the budget cap and the client choice sheet are back.

Copy the approver: anything involving money or client commitments, the lead AI copies the approver immediately.

AI operating boundary: commit to local git only; never push, deploy, or touch any server or real third-party account (section 2.1 rule 14). No gate lifts this.

### 0.4 Small-project track

At the end of the stage 1 interview the lead AI proposes a track; the project lead confirms it at G1. Until confirmed, write the requirements document in the full-track structure (appendix A1). Conditions: at most 3 user roles (including admin); at most 15 pages (counted by distinct route); online payment with a single merchant only, i.e. the platform collects and any payouts to others are handled manually. Automatic split payments or automatic payouts to multiple sellers (e.g. marketplace transfers to each seller) disqualify. All three met: small track. Otherwise: full track.

How the small track differs:
1. Only one spec document stating what is and is not built, including feature items and effort (section 5); independently reviewed once before freeze (stage 2 key point 2). The spec must contain a P0 acceptance checklist (item format as appendix A4). With any online payment, or any offline/manual collection or payout, it must also contain a money outcome matrix (stage 3 item 2.2) and money invariants (stage 3 item 2.3). Skip stage 3; no separate acceptance criteria file, money model file or kickoff plan.
2. One developer agent, no parallel module split; review still per section 2.2. (Not yet proven in practice: the reference small project only had its spec independently reviewed, not its code.)
3. Day 1: verify third-party assumptions with our own test accounts (stage 4).
4. One interaction check (appendix A10 item 5) plus one black-box acceptance round; only the spec's P0 checklist must fully pass. If any P0 fails, fix per section 2.3 items 4 and 5: one long-lived fixer agent, review per section 2.2, then a targeted retest; repeat until all P0 pass. (Not yet proven in practice.)
5. Gates are only G1 and G3, plus G2 on scope change. G3 confirms all spec P0 items pass and the local test layers pass (section 2.8, G3 row).
6. Which production-playbook items are mandatory and which may be reduced: section 2.8.

Example shape: a small MVP with single-merchant online payment, built in about three calendar days, documented with little more than one spec file and one status file.

## 1. Stages

Each section gives: purpose, outputs, key points, checklist, common pitfalls. `<project>/` is the project root.

### Stage 1 Requirements interview

**Purpose**: make the business explicit; every ambiguity becomes "decided" or "to ask".

**Inputs**: the client-signed proposal, the client prototype, meeting notes, background from the account manager.

**Whom to ask**: the project lead and the account manager. Client-must-answer questions go to the client only via the account manager.

**Outputs**: a first draft of the requirements document (structure in appendix A1), with Q&A conclusions and open questions written straight into it; create `DEVDOC.md` (section 3, template `templates/project/DEVDOC.md`); at the end, propose a track (section 0.4). No separate interview notes or question sheets.

**Key points**:
1. The baseline is the client-signed proposal. The draft has a separate "Differences from the signed proposal" list; the project lead explicitly confirms each item. Skipping this comparison is how a core business rule (e.g. commission direction) gets silently flipped mid-project.
2. Walk the must-ask list item by item, asking both "how does it normally go" and "what happens when it goes wrong":
   1. Roles and accounts: sign-up, login, verification; how many accounts per organisation.
   2. Each role's main flows.
   3. Money flow: who pays whom, when, commission, who bears fees, when funds go to sellers, refunds, partial refunds, deposit and balance, how one order is split across several sellers.
   4. Failure handling: cancellation by each party at each stage, rejection, timeout, duplicate payment, payment succeeded but the success page never returned, refund failure, transfer failure, revoking a claim or approval, holds, concurrent operations on the same object, account deletion, import errors.
   5. Content and notifications: what data is imported, what unclaimed records show, who can edit; which events email whom.
   6. Admin, legal and privacy: what admins see, change and handle manually; who supplies terms, how deletion requests are handled, which claims must not be made.
   7. Third parties and external dependencies: payments, maps, email, storage, captcha, whose account each needs and how long it takes; domain, servers, recurring costs (record only; goes into the deploy-notes draft at handover); what phase 1 does not do.
3. One line per open question: stable ID (section 2.5); question; our default; impact of not choosing the default; category. Three categories: client must answer (only the client can decide, and the answer changes development); default (inform the client); needs a lawyer or third party.

**Checklist**:
1. All 7 must-ask items have conclusions or are listed as open questions; every "what happens when it goes wrong" sub-item has a conclusion.
2. No more than 5 client-must-answer questions; all others have defaults.
3. Every difference from the signed proposal is listed.

**Common pitfalls**:
1. Edge flows under-thought. Revoking a claim, holding a shipment, orders left stranded after a cancellation, concurrent duplicate payments, refund failures all tend to surface only in development and testing. Go through item 4 deliberately.
2. Dumping dozens of questions on the client. Give defaults first; dozens of questions typically collapse to about 5.

### Stage 2 Requirements document and kickoff

**Purpose**: one agreed statement of "what we build", frozen before work starts.

**Outputs**:
1. Requirements document: one shared online document (e.g. a Google Doc), in the team's working language. Internal content is marked with paragraphs prefixed "[INTERNAL]". The feature list is one section; effort is a column in it (section 5).
2. Client version: at freeze, the AI strips the [INTERNAL] paragraphs from the same document and translates it into the client's language if different. Also a single document updated in place, sent to the client via the account manager.

**Key points**:
1. Write per section 2.5 (stable IDs, edit in place, batch decisions).
2. Before freeze, dispatch a fresh AI to independently review the requirements document and effort once, using brief A15. Fix every MUST before freezing. Such reviews routinely find a dozen-plus MUSTs in requirements and several in effort, and catch things like "webhook dedupe and fulfilment must be in the same transaction".
3. At G1, ask the project lead once for non-functional preferences and record them in DEVDOC and in the shared rules. Typical examples: keep the prototype's look; simplest effective solution; independent review of key changes; logging at key points; paginated lists; strong focus on user experience; code stays local, never pushed. At the same time ask whether to build the monitoring in production playbook §3.2 (optional per client need) and set the test thresholds (section 2.8).

**Checklist**: every section maps to the must-ask list, no empty sections; the independent review has no open MUST; the client version contains no internal content; the project lead says GO and confirms the track (G1).

### Stage 3 Kickoff pack (parallel)

**Purpose**: after GO, produce in parallel everything development and testing need. Four pieces go to different agents (brief A15); the lead AI merges. The small track skips this stage (section 0.4). (Most of this stage is not yet proven in practice.)

**Outputs and key points**:
1. Acceptance criteria `<project>/qa/acceptance-criteria.md`: generated from the frozen requirements, format in appendix A4. The project lead only confirms the P0 / P1 split. (Not yet proven in practice: write them before acceptance, not after several rounds.)
2. Money model `<project>/docs/money-model.md` (mandatory for any project with payments):
   1. For each case, where money goes, when, how much: normal payment, cancellation by each party, timeout, partial refund, refund failure, transfer failure, chargeback.
   2. Outcome matrix: third-party result (success / failure / unknown or timeout) x local write (success / failure) x follow-up event (late webhook, duplicate, user retry, cancellation). Each cell says how the system handles it. Repeated money review rounds usually trace back not to a missing model but to never crossing third-party uncertainty with local write failure.
   3. Invariants that always hold, e.g. "paid = sum of seller shares + platform commission + fees", "refunded + transferred <= collected", "at most one transfer per order". Write them directly as property-based tests.
   4. All balances and transferable amounts are recomputed from the ledger, never adjusted incrementally.
3. Effort was estimated before freeze per section 5 as a column of the feature list (reviewed with the requirements). The account manager sends the client choice sheet (appendix A3); the main project proceeds, derived projects and optional items wait for the sheet (section 0.3).
4. Kickoff plan `<project>/app/docs/TASKS.md`:
   1. Split agents by module (e.g. backend core: auth, partners, listings, claims; money and admin: checkout, orders, payouts; frontend; derived project), not a coarse frontend/backend split.
   2. One section per agent: feature items, dependencies, deliverables, done criteria.
   3. Environment allocation table: each agent's git worktree, database name and port, no overlaps.
   4. Merge order for shared modules; at which step each stub is replaced by the real implementation.
   5. Fork point and sync method for derived projects (section 2.6).

**Checklist**: every feature item is assigned to an agent; every requirement has at least one acceptance criterion; the money matrix has no empty cells.

### Stage 4 Foundation and API contract

**Purpose**: build the base shared by all parallel development, so later agents only fill in features without changing structure. The lead AI dispatches one foundation agent; parallel work starts only after the foundation review passes.

**Outputs**:
1. Project skeleton, README, `app/docs/FOUNDATION.md` (in the project lead's language, so they understand the structure; records SLO, consistency choice, degradation ladder and threat-model highlights per production playbook §1, see section 2.8).
2. Complete data model and first migration.
3. Complete API contract (e.g. a single shared endpoints file, often 100+ endpoints): path, role, input/output validation; unimplemented endpoints return 501. Every operation in the acceptance criteria has an endpoint.
4. Third-party abstractions: one interface per third party, with a stub and a real implementation written to the provider's current official guidance.
5. Money core and property-based tests for the invariants.
6. Shared basics: ownership checks, logging library (production playbook §3.1, `trace_id` injected automatically), email outbox, audit log, security baseline (section 2.1 rule 10), dev-only routes (view verification codes, shift the clock, run jobs manually; mounted only in development).
7. Demo-data script (`--reset` rebuilds; local database only) and environment rebuild script.

**Day 1 mandatory** (for services whose accounts are not ready yet, on the day they arrive): using our own third-party test accounts (opened by the account manager, section 0.2), verify key assumptions in test mode and record results in DECISIONS.md. This is local verification, not deployment. Typical assumptions: payout delays and how they interact with transfers tied to a source charge; email sandbox limits; map API quotas and attribution requirements. A payment-provider assumption left unverified to the end of a project is exactly why this rule exists.

**Checklist**: type check, tests and build pass; money property tests pass; for each third-party service in appendix A1 item 13, assumptions are listed and verification evidence is in DECISIONS.md (services whose test accounts have not arrived are recorded as risks in DEVDOC and do not block stage 5; any still unverified at G3 go into the deploy-notes draft as known risks); the foundation review against production playbook §1 and §3.1 has no MUST.

**Common pitfalls**: foundation reviews regularly find several MUSTs (cross-site request protection, partner registration and claim paths, upload parsing, transferable-amount calculation). Never skip the foundation review.

### Stage 5 Parallel development

**Purpose**: several agents fill features into the foundation at once.

**Key points**:
1. Every agent's brief uses appendix A8; rules from section 2.1 and production playbook §2.
2. Change requests to the API contract and data model (NEEDS) are handled immediately per section 2.4.
3. The frontend switches to real endpoints as soon as they exist; page structure is ported 1:1 from the prototype, only wiring data and state.
4. Review (section 2.2) and merge each block as soon as it is done; do not wait for everything.

**Checklist** (before each block merges): type check, tests and build pass; related acceptance criteria self-tested; new decisions in DECISIONS.md; review passed.

**Common pitfalls**: a frontend that lives on mock data for a long time; mock data drifts from the real API and hides real bugs.

### Stage 6 Independent review

Rules in section 2.2, brief in appendix A9. Outputs: review reports; BUGS.md entries. Common pitfall: with all tests green, independent review still finds duplicate payouts, lost refunds, a revoked claim immediately re-claimable by the same person, and concurrent double charges.

### Stage 7 Black-box acceptance

**Purpose**: judge right and wrong against the requirements, catching "well-written code that does not meet the requirement".

Rules in section 2.3, brief in appendix A10, small track in section 0.4. Outputs: one `<project>/qa/acceptance-roundN.md` per round (appendix A5), screenshots in `qa/screens/`; for the final round, an item-by-item tick-off against the acceptance criteria in `qa/checklist-pass-N.md` (Not yet proven in practice.). Common pitfall: issues such as "a supplier cannot see the delivery address" or "the admin has no inbox, so refund requests are invisible" are invisible to code review and only show up when someone clicks through the requirements.

### Handover

**Purpose**: after G3, hand code and documents to humans. G3 plus handover completes the AI's work under this playbook.

**Outputs**:
1. Code: local repository path and the commit released at G3 (for derived projects, each repo and commit), handed to the project lead. Pushing and hosting are done by humans.
2. Documents: under `app/docs/`: FOUNDATION.md, DECISIONS.md, BUGS.md, TASKS.md; acceptance criteria; all acceptance reports and tick-off records; `qa/local-layers-N.md`; money model (if payments); link to the requirements document. The small track has no TASKS.md, acceptance criteria file or money model file; the spec replaces them (section 0.4), so hand over the spec.
3. Deploy-notes draft `<project>/docs/deploy-notes-draft.md`, listing what deployment needs: environment variables (names and purpose, never values); third-party accounts and configuration; database migrations and their order; placeholder content to replace (legal text, assets); production playbook items deferred to deployment (section 2.8); known risks (unverified third-party assumptions, released P1s and unfixed P2s, "to confirm" decisions).

**Checklist**: G3 confirmed; all handover files committed to local git (except DEVDOC); the deploy-notes draft contains no secret values; DEVDOC status block updated to the handover state; one handover message posted in the project channel (section 4).

For taking over a client prototype and turning it into a product (intake, estimation, pricing), see `docs/playbooks/client-handover.md`.

## 2. Rules

### 2.1 Shared rules for AI agents

Attach this section, plus the non-functional preferences recorded at G1, to every developer and fixer agent brief.

1. Use the simplest effective solution that meets the requirement; build nothing listed as "not in phase 1".
2. The only source of requirements is the requirements document; right and wrong are judged by the acceptance criteria.
3. Only the lead AI may change the API contract, data model and migrations. If a change is needed, write it to `NEEDS.md` on your branch (what, why, exact change), flag it in your report immediately, and continue with other parts.
4. Use only the working directory, database and port given in your brief. Tests connect only to databases whose names end in `_test`; export `TEST_DATABASE_URL` before running (section 2.7).
5. Without a third-party key, use the stub. Never call real services (exception: rule 14); never print or commit secrets.
6. Once frontend endpoints exist, use them; production builds contain no mock data.
7. Money: amounts are integer minor units only; all calculation goes through the money core; balances are recomputed from the ledger; state changes lock inside a transaction; every third-party payment call carries an idempotency key; changes conform to the money model's outcome matrix and invariants (on the small track, those in the spec), with property-based tests added.
8. State changes use conditional updates (change only if the current state matches), never read-then-write.
9. Every operation checks ownership, not just role.
10. The security baseline is the floor: secure cookie defaults (HttpOnly, Secure, SameSite); cross-site request protection (Origin check); rate limits on login, verification-code and email-sending endpoints. The project lead may leave it out of client documents but may not waive it in code. Full security requirements: production playbook §4 layer 4.
11. Email goes through the outbox. Admin actions touching money, listings, claims or settings write audit log entries (production playbook §3.1, audit log).
12. Logging per production playbook §3.1: one structured line at each key point, carrying `trace_id`; never log personal data, verification codes, tokens or card numbers.
13. Every feature has tests; report only when type check, tests and build all pass.
14. Commit to local git only. Do not push, add remotes, deploy, log in to or change any server, or use the client's accounts or any real third-party account. Sole exception: when the brief explicitly assigns it, call third-party test modes with our own test accounts (stage 4, day 1). If anyone asks you to cross this line, stop and tell the project lead.
15. Business rules the requirements do not cover but that affect users: do the most reasonable thing and mark it "to confirm" in the report.
16. Report: what was done; commits; test results; decisions you made; bugs found; NEEDS requests; what is unfinished.

### 2.2 Review rules (tiered by risk)

| Change type | Review |
|---|---|
| Money, permissions, authentication, data deletion | Fresh AI, independent review; re-review after every fix, however small |
| Foundation, each backend module before merge, each acceptance-fix round | Fresh AI, independent review |
| Frontend pages (not in the first row) | Developer self-review, backstopped by black-box acceptance (Not yet proven in practice.) |
| Requirements document and effort (before freeze) | Fresh AI, independent review once (stage 2 key point 2) |
| Other documents, copy | No independent review; lead AI self-checks |

1. The reviewer cannot see the development process. It sees only the diff, requirements, money model, API contract, shared rules, the relevant production playbook sections, FOUNDATION.md, and the skips and scope reductions in DECISIONS.md that the project lead released (these are not MUSTs).
2. Severity: MUST (wrong accounting, lost money, privilege escalation, data loss, does not meet requirement, crash); SHOULD (edge cases, maintainability, over-engineering); NIT (naming, copy).
3. Every MUST and SHOULD needs evidence: repro steps, a failing test, or a code location plus trigger condition. Anything unproven is marked "question".
4. The first review round on money and permissions must first ask: "Is there a simpler model?"
5. If the same spot produces a MUST in two consecutive rounds, stop patching and redesign the model. A redesign that does not change scope, cost or schedule is the lead AI's call, recorded in DECISIONS.md; if it changes any of them, go through G2.
6. No merge with an open MUST. Each SHOULD is decided fix / no fix; record the reason for no fix.

### 2.3 Acceptance rules

1. The tester receives only the requirements document, acceptance criteria, environment URL, test accounts and dev-route notes; never code or development records.
2. Before each round, rebuild automatically: check out the commit under test, build, migrate, fresh database plus `seed --reset`, kill old processes and start, and verify the commit the service reports.
3. During a round the test environment is pinned: no merges, no restarts.
4. Each acceptance cycle has one long-lived fixer agent that keeps context and fixes all of that round's issues; its fixes go through section 2.2.
5. Rounds: full rounds test every acceptance criterion; between full rounds run targeted retest rounds covering only last round's failures and items affected by fixes. (Not yet proven in practice: projects so far ran one full round then only retests.)
6. Real browser at desktop 1280 and mobile 390 widths; additionally call the API directly to test privilege escalation and duplicate submission; run the interaction checklist (appendix A10 item 5) every round.
7. Each issue quotes the requirement text and gives repro steps, expected, actual, screenshot. Any change the tester makes to the environment (clock shift, settings) goes in the report.
8. Severity: blocker (main flow cannot complete); critical (money, permission or data wrong, or core feature missing); major (workaround exists); minor (copy, style).
9. Items "not a bug per the requirements" are marked "to confirm" by the lead AI and decided by the project lead.
10. Exit conditions: no blockers or criticals; all P0 pass; failing P1s released by the project lead (G3); one complete item-by-item tick-off on the commit to be released at G3, with the commit recorded in `qa/checklist-pass-N.md`. (The last three are not yet proven in practice; the small track checks P0 only.)
11. Main and derived projects are accepted separately.
12. If the client cuts the test budget, every cut item must be released by the project lead in DECISIONS.md per section 2.8; marking it "to confirm" is not enough. Running the money flows once against real third-party test modes is done by humans at deployment, recorded in the deploy-notes draft at handover, and cannot be cut.

### 2.4 How the lead AI works

1. No heavy work itself: development, fixing, review, local testing and acceptance all go to one-shot agents. The lead AI owns and merges documents; long documents may be drafted by an agent. It only dispatches, merges, records and reports.
2. One session dedicated to this project; do not handle other projects at the same time.
3. Handle NEEDS requests immediately: land on trunk, notify every affected branch at once, merge into trunk first and then into the branches that depend on it. Do not batch.
4. Log every dispatched task in the task log (appendix A12).
5. Before borrowing another bot or peer session, get consent from whoever set that bot's scope.
6. On pause (including the project lead saying "pause"): record open issues without fixing them, update the DEVDOC status block, send the status block to the project lead, and wait for an explicit resume.

### 2.5 Reducing document rework

Sequential numbering, saving a copy per version, change logs inside documents, and decisions asked piecemeal drive requirements and estimates to twenty-plus versions. The practices below are not yet proven in practice as a whole:
1. Questions and feature items use stable topic-named IDs, e.g. `Q-PAY-DEPOSIT`, `F-ORDER-CANCEL`, not sequence numbers. Inserts and deletes do not break references.
2. Cross-document references cite IDs and section names, not version numbers.
3. No change log inside documents; changes go in DEVDOC.
4. Effort is a column of the requirements feature list; no separate effort document.
5. Batch the project lead's decisions into one ask.
6. Edit shared documents in place; never save as vN.

### 2.6 Derived projects (forks of the main project)

1. After forking, sync the main project's acceptance fixes promptly, or fork only after the main project passes acceptance. Forking while the main project is still being fixed means most of the derived project's first-round acceptance issues are main-project fixes not yet synced.
2. Every merge to the main project's trunk is synced to the derived project.
3. Keep a mapping table: each derived-project page and the main-project page it corresponds to, with differences noted.
4. After forking, check environment parity: dev routes, demo data and stubs all have matching versions.
5. Generic fixes made in the derived project are back-ported to the main project (e.g. shared validation, display rules).
6. Watch for migration timestamp collisions between the two (both sides may generate the same timestamp).

### 2.7 Environment traps

1. `pkill -f` matches by command line and misses processes started with relative paths (e.g. `node dist/index.js`). Use `lsof -i :<port>` to find the PID, kill it, then verify the commit.
2. If `TEST_DATABASE_URL` is not set, vitest falls back to the default test database and agents overwrite each other. Every agent always exports it.
3. Fresh database for every acceptance round.
4. Clock-shifting tests use their own database, not shared with other tests.
5. The demo-data script must check the environment after loading configuration, and allow only a local database. Checking before config load once made it possible to wipe production.

### 2.8 When each production-playbook section is checked

This playbook does not repeat the production playbook's content; it only sets when each part is checked.

| When | Production playbook section | How |
|---|---|---|
| Stage 4 foundation | §1 design; §3.1 logging | Conclusions written to FOUNDATION.md; the foundation review checks against them |
| Stages 5 and 6 | §2 development; local parts of §4 layers 1 to 4 (see G3 row); §4 layer 1 mutation testing of critical modules | Done with each block's tests and review; critical modules are money, permissions, state machines; black-box acceptance (section 2.3) is the requirements part of layer 1 |
| Before G3 | The locally runnable parts of §4 layers 1 to 4: layer 1 business (acceptance criteria meet the section 2.3 item 10 exit conditions; mutation testing); layer 2 concurrency and race tests; layer 3 local fault injection (timeouts, malformed input, etc.); layer 4 SAST, dependency scan, secret scan (gitleaks or trufflehog over full git history), privilege-escalation tests, checked against the ASVS level set at G1; the logging part of layer 5: trace one critical business flow end to end by `trace_id` (with online payment, from order to settlement; with split payments, through to transfer); deliberately feed fake passwords, card numbers and tokens through a flow, then search the logs to confirm no plaintext (production playbook §4 layer 5 redaction test) | A local test agent (appendix A14) runs these on the commit to be released at G3 (a derived project runs its own `local-layers-N.md` on its own commit, gets its own appendix A9 item 7 check, and passes G3 separately). Results go in `qa/local-layers-N.md`; before G3 an independent review per section 2.2 (appendix A9 item 7) checks the file against the raw output; once the pass criteria are met, confirm together with the section 2.3 exit conditions |

Production playbook parts that require staging or production (load and soak, DAST, ASVS items depending on a real domain and TLS such as communications, HSTS, certificates and renewal, layer 5 alerting, §5 release, §6 Definition of Done) are out of scope; list them as to-dos in the deploy-notes draft at handover.

Test thresholds: confirmed by the project lead at G1, written into FOUNDATION.md in stage 4. Used locally: the production playbook §4 layer 4 level, default ASVS L2; mutation score for critical modules (money, permissions, state machines), default at least 60%. SLOs, load-test target load and soak duration are not tested locally; the lead AI writes recommended values into FOUNDATION.md in stage 4 and lists them in the deploy-notes draft.

Node and TypeScript have no equivalent of `-race` or deterministic simulation testing. Tests that use a barrier so concurrent requests arrive simultaneously, covering every operation that touches money or changes state, satisfy that layer-2 criterion with no separate release needed.

Skipping any production playbook item, on any track, requires the project lead's release in DECISIONS.md with a reason.

Full track: all locally runnable parts of the production playbook apply.

Small track: all four local test layers still run, possibly at reduced scale, e.g. layer 3 tests only timeouts, retries and malformed input; SLO and threat model a few lines each. The reduced scope (which endpoints, which fault cases) is written into DECISIONS.md before running and confirmed by the project lead. A reduction done this way does not count as a skip.

Monitoring: at G1 the project lead decides whether to build production playbook §3.2 monitoring (stage 2 key point 3). If yes, locally only wire up the metrics; alert and dashboard verification is left to deployment and noted in the deploy-notes draft. If no, the deploy-notes draft states "no monitoring, per G1 decision"; this is not a skip. Logging per §3.1 is always done.

Where this playbook and the production playbook disagree on process, this playbook wins. For example, if the production playbook expects a separate spec file (`templates/ticket/spec.md`), here the spec is the requirements document plus stage 4's `<project>/app/docs/FOUNDATION.md`. The production playbook itself is not changed.

Red lines no track can waive: the security baseline (section 2.1 rule 10) and privilege-escalation tests; secrets never in code, logs or documents; no sensitive data in logs; money idempotency and no data loss; no push, deploy, servers or real accounts (section 2.1 rule 14). The production playbook's exemption for throwaway prototypes and purely internal tools does not waive these red lines either.

## 3. Record system

Principle: context lives in files, not memory. A freshly started AI can read these files and carry on.

| File | Location | Written by | Content | Updated |
|---|---|---|---|---|
| Requirements document | Shared online document (link in DEVDOC) | Lead AI | Appendix A1; includes open questions, feature items and effort | In place |
| DEVDOC.md | `<project>/DEVDOC.md` (local, not in git; template `templates/project/DEVDOC.md`) | Lead AI | Status block (appendix A11); people and roles; non-functional preferences; external dependency status; task log (appendix A12); newest-first change log | After every merge, decision, outward message, failure, new to-do |
| DECISIONS.md | `<project>/app/docs/` | Lead AI | Appendix A6 | Each decision, at once |
| BUGS.md | `<project>/app/docs/` | Lead AI | Appendix A7; review findings, acceptance issues and client feedback all go here | Created on discovery; status updated after fix and retest |
| Acceptance criteria | `<project>/qa/acceptance-criteria.md` | Lead AI; project lead confirms P0 / P1 | Appendix A4 | When requirements change |
| Acceptance reports | `<project>/qa/acceptance-roundN.md` | Acceptance tester | Appendix A5 | One per round; never edit old ones |
| Money model | `<project>/docs/money-model.md` | Lead AI | Stage 3 item 2 | When money rules change |
| Tick-off record | `<project>/qa/checklist-pass-N.md` | Acceptance tester | Item-by-item tick-off against acceptance criteria (stage 7) | One per complete tick-off |
| Local test layer results | `<project>/qa/local-layers-N.md` | Local test agent | Appendix A14; production playbook §4 local layer results, commit, raw tool output (section 2.8, G3 row) | One before each G3 request |
| Deploy-notes draft | `<project>/docs/deploy-notes-draft.md` | Lead AI | Deploy notes at handover (section 1, "Handover") | Written at handover; extended whenever a deployment need is discovered |
| TASKS.md | `<project>/app/docs/` | Lead AI | Stage 3 item 4 | On dispatch and completion |
| NEEDS.md | Root of each agent branch | Developer agent | What, why, exact change | When needed; cleared once handled |

The project's `CLAUDE.md` (template `templates/project/CLAUDE.md`) holds durable project knowledge; DEVDOC holds live state.

### 3.1 Recovering after an interruption

1. Read the DEVDOC status block: each branch's latest commit, test count, environment and rebuild command, who we are waiting on, the first next step.
2. Read BUGS.md "open" entries, the latest acceptance report, and recent DECISIONS.md entries.
3. Check every branch with `git log` and `git status`; where it disagrees with DEVDOC, git wins and DEVDOC is corrected.
4. Check for leftover agents or stale processes (section 2.7 item 1).
5. To answer "did we do X?", check DEVDOC and git first, never memory.
6. After recovering, post one message in the project channel saying where work resumed.

## 4. Reporting and communication

1. Each project session has its own chat channel or thread; project messages go only there.
2. The status block is always readable: the DEVDOC status block (appendix A11) is always current so the project lead can look at any time.
3. Event pushes: post one message immediately on trunk merge, end of an acceptance round, G3 passed, handover, anything needing a human decision, and external dependencies arriving or stuck.
4. Send a daily report every morning.
5. On pause, send the status block (section 2.4 item 6).
6. All client deliverables go through the account manager; the AI never contacts the client directly. Follow the account manager's formatting preferences for client documents (e.g. avoid dashes and divider lines, which read as AI-written).

Push and daily-report template (short, changes only):
1. Current stage; what remains before the next gate.
2. One line per block: module, status (in development / in review / merged / in acceptance), latest commit, test count.
3. Done: at most 5 items.
4. New issues: counts by severity, one sentence on the important ones.
5. Decisions to confirm: question; default; impact of not choosing it. If none, write "none".
6. Waiting on: external dependencies and how long.
7. Next.

## 5. Effort estimation and calibration

**Effort table**: the requirements feature list (appendix A2) has two time columns. "AI effort (hours, calibrated to actuals)" is the working time of the lead AI plus all sub-agents, including review and fixes. "External dependencies and calendar time" is calendar days spent waiting for accounts, keys, client answers and lawyer text. Human reference hours are no longer listed. Client price = AI effort x pricing multiplier, set by the project lead and the account manager.

**Method**:
1. Give each feature item a type: plain CRUD page, auth and permissions, money/payments, third-party integration, admin, scheduled jobs, etc. Effort = that type's unit time (appendix A13). Where A13 has no value yet, estimate by analogy with a completed reference project and mark "to calibrate".
2. Add fixed parts: foundation; merge coordination; per-round acceptance time x expected rounds. Where A13 has no value, likewise estimate by analogy and mark "to calibrate".
3. Add a risk reserve to the total (rule of thumb): start at 15% of all effort; adjust once there are samples.

**Measurement and calibration**:
1. Log one row per dispatched agent task in the DEVDOC task log (appendix A12), cross-checked against the git branch timeline. Do not record tokens or model cost for now.
2. Only projects that pass G3 and are handed over are used for formal calibration: compare estimate vs actual by type and update appendix A13. Records that cannot be split by type serve only as reference samples.
3. Do not compare an estimate directly with an observed duration that covers only part of the work. Observed elapsed time for local development and local acceptance (with agents in parallel) excludes third-party integration, deployment, derived-project acceptance and client feedback.

**Model cost**:
1. Whether the project's agent work uses a dedicated API key is decided by the approver or account manager before G1; absent a decision, use the subscription quota.
2. On subscription quota, many parallel sessions can exhaust it mid-run and stop all agents at once; flag in reports when the quota is half used.

## 6. Appendix: templates

### A1 Requirements document structure

1. About this document: date, readers, related documents (no version numbers).
2. Project overview: what it is, who it is for, phase 1 goals.
3. Differences from the signed proposal (each to be confirmed by the project lead).
4. Roles and accounts.
5. Requirements per role: main flows and the rules at each step.
6. Payment flows: plain-language version of the money model, including failure cases.
7. Business rules: ordering, state transitions, timeout days, limits, copy rules.
8. Feature list (appendix A2, with effort columns).
9. Not in phase 1: for each, why and when it would be needed.
10. Client-must-answer questions (stable ID; question; default; impact of not choosing it).
11. Defaults (inform the client), grouped by topic.
12. Items the client must supply or confirm separately: lawyer text, assets, accounts.
13. Third-party services and external dependencies: service, purpose, who prepares it, what is needed (application and arrival status tracked in DEVDOC).
14. Recurring costs (servers, third parties).

### A2 Feature list columns

ID (stable, e.g. `F-ORDER-CANCEL`); project (main or derived); feature (one sentence); content (what the user sees); source (requirements section); type (section 5); AI effort (hours, calibrated to actuals); external dependencies and calendar time. After the table: total (including fixed parts and risk reserve), calendar time, assumptions.

### A3 Client choice sheet (in the client's language, sent via the account manager)

Columns: ID (same as feature ID); Feature; What you get (one sentence); Hours (AI effort x pricing multiplier, set by the project lead and account manager, section 5); Can you build it yourself with your no-code tool? (Yes / Partly / No); Your choice (Us / Myself / Skip). Before the table, "How to use this"; after it, Totals and Dependencies (choosing A requires B).

### A4 Acceptance criteria entries

Header: source, exclusions, ID scheme, priority definitions (P0 must pass before G3; P1 should pass, failures need the project lead's release; P2 may wait until after handover and is listed as a known issue at handover), summary table.

| ID | Requirement source | Acceptance check (Given / When / Then) | Expected result | Priority |
|---|---|---|---|---|
| AC-SHARED-003 | Section 1: "Sign-up and login with email verification code" | Given a new email; When registering; Then a verification email arrives, and entering the correct code marks the account verified | Wrong code is rejected with a message; checkout and claiming are blocked until verified | P0 |

AC-<project>-NNN applies to one site only; AC-SHARED-NNN is tested once on each site. Every entry must be judgeable by someone who never reads code.

### A5 Acceptance report

Header: date, round type (full / targeted retest), commit, environment URL, method, self-created data, environment changes, issue counts.

Each issue: title (ID plus one sentence, e.g. "QA-001 Supplier cannot see the delivery address"); severity; requirement text; acceptance criterion ID; repro steps (including accounts and data); expected; actual; screenshot path. For each issue from the previous round: fixed / partly fixed / cannot reproduce.

### A6 Decision entries

| Date | Question | Chosen option | Reason / decided by |
|---|---|---|---|
| 2026-01-15 | An abandoned checkout page gets paid later | Expire the old session before creating a new checkout; if a voided order still receives payment, auto-refund in full and alert the admin | Prevent double charging (QA-003) (lead AI) |

Decisions by a human carry their role or name; decisions by the AI say "lead AI", plus "to confirm" if human confirmation is needed. Newest on top.

### A7 BUGS.md entries

| ID | Date | Source | Problem | Fix | Commit | Status |
|---|---|---|---|---|---|---|
| B034 | 2026-01-15 | review | Demo-data script checks the environment before loading config; run on a production host it would wipe the production database | Check after loading config; allow only a local database | abc1234 | fixed |

Source: review / acceptance / development / client. Status: open / fixed / retested; money and permission items add "re-reviewed".

### A8 Developer agent brief

1. Who you are: project name, the module you own (TASKS.md section; on the small track there is no TASKS.md, so cite the spec section).
2. Must read: shared rules (section 2.1) and non-functional preferences, relevant requirements sections, money model (if relevant), API contract, FOUNDATION.md, related acceptance criterion IDs.
3. Environment: working directory, branch, database name, `TEST_DATABASE_URL`, port.
4. To do: feature items and each one's done criteria.
5. Not to do: other modules; the API contract and data model (write NEEDS.md; exception for the foundation agent: when assigned by the lead AI it may draft the API contract, data model and first migration, which the lead AI reviews and merges); anything not in phase 1; real third-party calls (exception: section 2.1 rule 14); push; deploy; log in to any server.
6. Report: per section 2.1 rule 16.

A fixer agent uses the same template with item 4 replaced by this round's issue list.

### A9 Review brief (differences from A8)

1. Role: independent reviewer; did not take part in development, does not see development records, does not change code, only reports.
2. Scope: branch and commit range; materials as A8 item 2, plus the relevant production playbook sections, FOUNDATION.md, and the skips and scope reductions in DECISIONS.md released by the project lead (not MUSTs). The reviewer does not get the developer's brief.
3. Focus: money outcome matrix and invariants, concurrency and duplicate submission, idempotency, ownership checks, illegal state transitions, external call failures, failure flows in the requirements, over-engineering. For money and permissions, first answer "is there a simpler model?".
4. Severity and evidence per section 2.2.
5. Report: verdict (mergeable / not mergeable); MUST; SHOULD; NIT; code that can be deleted.
6. Re-review gets only the fix diff and the previous report.
7. Before G3, dispatch one more: check `qa/local-layers-N.md` against the raw tool output and commit, verdict in the report. Materials for this one: that file, the raw output, the commit to be released at G3 (the reviewer re-runs key commands on it and compares with the raw output), section 2.8 G3 row, the test thresholds in FOUNDATION.md, and the skips and scope reductions in DECISIONS.md released by the project lead (any track).

### A10 Acceptance tester brief (differences from A8)

1. Role: black-box tester; judges only against the requirements; does not read code or development documents, does not fix anything, does not guess at code causes.
2. Materials: per section 2.3 item 1; the commit the environment was rebuilt to, checked against the health endpoint before starting.
3. Round type (full / targeted retest) and scope.
4. Method and report per section 2.3 and appendix A5, written to `qa/acceptance-roundN.md`.
5. Interaction checklist, every round:
   1. After logging out or logging in as another account, is any of the previous user's data still on the page?
   2. After refresh and browser back, are you still on the site, at the same place?
   3. Does double-clicking or resubmitting create duplicate records?
   4. After closing and reopening, or in a new session, is a draft reused or is a new one created?

   Rationale: interaction checks have found the next user seeing the previous user's conversations and drafts after logout, close-and-reopen checkout creating duplicate pending orders, and the back button leaving the site entirely.

### A11 DEVDOC status block

1. Updated at (UTC).
2. Per repository or branch: latest commit, status, test count.
3. Acceptance: round number, open issue IDs.
4. Environment: URL, port, database, rebuild command.
5. Waiting on: whom, for what, since when.
6. Latest instructions from humans (verbatim or accurate paraphrase, dated).
7. Next: the first thing after resuming, then the order.

### A12 Task log (in DEVDOC)

Stage: development / local acceptance / third-party assumption verification / handover.

| Feature | Type | Stage | Start | End | Review rounds | Rework count | Branch |
|---|---|---|---|---|---|---|---|

### A13 Unit time table

Calibrate once for each project that passes G3 and is handed over (section 5). Where a reference project's records cannot be split by type, fill only the project total and leave the types pending.

| Type | Unit time (hours) | Sample projects | Last calibrated |
|---|---|---|---|
| Project total: reference project | to fill | 0 | |
| Plain CRUD page | to fill | 0 | |
| Auth and permissions | to fill | 0 | |
| Money / payments | to fill | 0 | |
| Third-party integration | to fill | 0 | |
| Admin | to fill | 0 | |
| Scheduled jobs | to fill | 0 | |
| Fixed: foundation | to fill | 0 | |
| Fixed: merge coordination | to fill | 0 | |
| Fixed: per acceptance round | to fill | 0 | |

### A14 Local test agent brief (differences from A8)

1. Role: one-shot local tester; only runs tests and records results; changes no code, fixes nothing.
2. Commit: the one to be released at G3; verify the commit before starting.
3. What to run: the local layers in section 2.8 G3 row, thresholds per FOUNDATION.md; skips released by the project lead in DECISIONS.md are not run, and scope reductions run at the released scope (any track).
4. Output `qa/local-layers-N.md`: commit and date at the top; for each layer the tool and command, pass or fail, and the threshold compared against; attach raw tool output (under `qa/local-layers-N/`, with paths in the file), not just a summary.
5. Failures go in the report; the lead AI records them in BUGS.md and dispatches fixes. After fixes, re-run on the new commit and write a new file.

### A15 Document drafting and document review brief (differences from A8 and A9)

1. Input: the frozen requirements document (for review, the requirements or spec document awaiting freeze); the client-signed proposal as baseline. No code needed.
2. Drafting: write one file, location and format per the section 3 record table and the matching appendix (acceptance criteria A4, money model stage 3 item 2, kickoff plan stage 3 item 4, requirements document A1 and A2). Where the requirements are silent, mark "to confirm"; never invent rules.
3. Review: severity and evidence per section 2.2 (MUST / SHOULD / NIT; unproven items marked "question"). Focus on money, failure flows (stage 1 must-ask item 4), effort arithmetic (line-by-line sums, fixed parts, risk reserve), and differences from the signed proposal. Do not edit the document; only report.
4. Report: verdict (can freeze / cannot freeze); MUST; SHOULD; NIT.
