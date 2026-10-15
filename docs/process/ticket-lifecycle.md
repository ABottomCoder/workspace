# Ticket Lifecycle

From a ticket number (or a request that deserves one) to closed. Steps marked **[heavy]** apply only in
heavy-tier businesses ([heavy-track.md](heavy-track.md)); everything else applies to both tiers.
Company values (ticket system, chat tool, git host, base branch, branch/PR conventions) come from
`business/<co>/stack.md`; the ticket-system mechanics from its adapter in [tickets/](index.md#ticket-system-adapters).

## The ticket directory

One directory per ticket: `business/<co>/tickets/<ID>/`. `<ID>` is the ticket ID exactly as the
ticket system writes it; without one, a short kebab description (`invite-flow`). Dates live in `STATE.md`,
not the directory name. Templates: `templates/ticket/`.

```
tickets/<ID>/
├── STATE.md     status (open/active/review/closed), title, project, AC, branch, PR, dates, links
├── LOG.md       append-only: changes, decisions + why, messages sent, failures
├── HANDOFF.md   current resume point (refreshed at milestones; old ones → history/)
├── spec.md      non-trivial work only: spec → plan → tasks, AC, safety block
├── reports/     test-report-v<n>.html, ticket-report.html, qa.md, qa-report.html, review-r<n>.md
├── evidence/    screenshots, logs, query files, one-off scripts
└── history/
```

- `tickets/INDEX.md` is **generated** (`tools/work/index`); never hand-edit it. Read it first during
  intake instead of listing directories; open only the tickets whose rows matter.
- Nothing is deleted. Closed tickets stay in place.
- Cross-business work uses the same shape under `user/work/<slug>/`.
- Never store ticket progress in auto-memory; it belongs in the ticket directory.

## Phase 1: Intake

1. **Fetch the ticket** via the adapter: summary, description, AC, **all comments**, attachments,
   links, subtasks, parent epic, assignee. If auth fails, ask the approver for credentials (store them in
   `business/<co>/.secrets/`, never in docs).
2. **Create or open the ticket dir**; fill `STATE.md`; attach the session (`tools/work/attach`).
3. **Assignee check:** if it isn't assigned to the user, warn and wait for explicit confirmation.
4. **Context sweep.** Light: what the ticket needs. **[heavy]** the full sweep, unprompted
   ([evidence-and-ask-gate.md](../principles/evidence-and-ask-gate.md#3-gather-context-the-full-sweep)):
   surrounding tickets (epic siblings, a search on the ticket's key nouns; prior tickets on the same
   file are the richest source), code + `git log --grep`/`blame`, `tickets/INDEX.md`, lessons, wiki
   (team space first, by page title when a legacy link is pasted), chat.
5. **Route to repos** via the business repo table; read each repo's `CLAUDE.md` first.
6. **Base branch:** default from `stack.md` or the repo row; state it, ask only on override. First time
   for a business: ask and record it.
7. **Working tree state:** `git status` in each repo. Uncommitted changes, unstaged files or stashes →
   report and wait. Never discard or stash without approval.
8. **Update the base branch** (pull) before reading code; prefer `git worktree add` to switching the
   user's branch.
9. **Identify dependents:** what upstream/downstream behaviour the change reaches; it sets the test scope.
10. **Clarify** what is genuinely ambiguous after the Ask-Gate, batched, to the right person.
11. **Present your understanding:**
    ```
    ## Ticket: <ID>
    Summary:     one line
    Base branch: …            Repo(s): …
    Scope:       files/modules likely affected
    Approach:    proposed implementation
    Questions:   anything still unclear
    Risks:       side effects to watch
    References:  related past tickets consulted
    ```
12. Non-trivial: write `spec.md` ([light-track.md](light-track.md#plan-before-build-non-trivial-work)).
13. **[heavy]** Post two ticket comments: **Plan Rationale** (questions raised, options, decisions and
    why) and **Execution Plan** (phases, files, scope). Then **wait for the approver's confirmation**
    before code.

## Phase 2: Development and validation

1. Create the feature branch from the up-to-date base, per the branch convention.
2. Implement; match the repo's style, naming and patterns; walk the
   [Decision Ladder](../principles/decision-ladder.md).
3. Write/update tests. For every new assertion, produce the input that makes it fail.
4. Run the suite until green; check skips as loudly as failures.
5. **Self-review before committing:** dead code, debug prints, commented-out blocks, unused imports;
   duplication; simpler idiom; naming; error handling (not excessive, not missing); performance (N+1,
   redundant calls, missing indexes); security (no hardcoded secrets, no injection, input validation at
   boundaries). Re-run tests if anything changed.
6. Commit with messages referencing the ticket ID. Log the commit in `LOG.md`.
7. Revert every temporary local-testing change (CORS hacks, pointed-at-localhost URLs, shortened
   intervals) before committing.
8. **[heavy]** Test report → `reports/test-report-v1.html` ([reporting.md](reporting.md)). New
   versions only for re-testing after review.
9. **[heavy]** Independent QA: start a fresh session with `/qa <ID>`; this session stays the developer,
   freezes at a named commit and hands over branch + worktree + plan. Report only after the joint
   sign-off ([qa-session.md](qa-session.md)).

## Phase 3: Reporting and knowledge capture

- **Ticket report** (light: when useful; **[heavy]** always) → `reports/ticket-report.html`:
  what was asked → what we did and why (files modified) → problems and resolutions → how it was tested →
  evidence it's done → learnings. Rules: [reporting.md](reporting.md).
- **Push and PR** per the PR convention (CLI when available, else copy-paste-ready content); assign
  reviewers. Pushing and opening PRs are outward actions: they need authorisation.
- **[heavy]** Notify the approver: done, branch, PR, report location.
- **[heavy]** Intervention-log row ([intervention-tracking.md](intervention-tracking.md)).
- Update `STATE.md` (status, PR, dates), regenerate the index, append lessons and repo `CLAUDE.md` notes.

### Daily log

After each completed task (commit, test pass, PR, decision), append to `user/logs/YYYYMMDD.log`:

```
[HH:mm] [<co>] [<ID>] | status: completed / in-progress / blocked
  done: brief summary
  blockers: if any
  next: if not completed
```

On session start, check today's and yesterday's log for `in-progress` entries and mention unfinished work.

## Code review rework (your own PR)

On reviewer feedback: stay on the existing feature branch, pull, fix, re-test, commit as a review fix
(`<ID> address review feedback: …`), new test report version, append a "Review Rework" section to the
ticket report (don't rewrite it), push, tell the user the PR is updated.

## Handoff and resume

- **Save:** verify ground truth (`git status`/`git log` per repo), then refresh `HANDOFF.md`:
  ⭐ resume-here line with the literal next action · verified facts · current state (committed / local
  only / not changed, per repo and branch) · ordered next steps · decisions and why · gotchas · config,
  env vars and secrets needed (by name) · how to test locally, including temporary changes and how to
  revert them · references. Old handoff → `history/`.
- **Quality bar:** a fresh session reading only `STATE.md` + `HANDOFF.md` + `LOG.md` tail continues
  seamlessly: concrete `file:line`, real commands, real branch and commit. Mark anything unproven
  UNVERIFIED. Anything you spent time debugging (wrong field name, startup order, config) must be written
  down so no one debugs it again.
- **Resume:** read the handoff fully, re-establish ground truth (the repo may have moved), play back
  where things stand and the next action, continue.

## Multi-session coordination

When several sessions work one ticket (developer + QA, or a commander over several tickets):
- **Each session gets its own `git worktree`.** Sessions sharing a clone silently revert each other.
- **The written record outranks the channel.** Decisions live in the ticket's `LOG.md`; messages only
  announce them.
- Messages are written, role- and ticket-tagged, and commit-anchored. Transport is pluggable (message
  bus, an append-only `tickets/<ID>/bus.md`, or the human relaying). Protocol: [qa-session.md](qa-session.md).
- Treat any file another session writes as append-only unless coordinated; no blind bulk edits.
