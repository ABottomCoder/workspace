# Multi-Agent Harness (author ↔ adversarial critics)

A reusable system for running one coding task through an **author** agent that implements it and **two
complementary adversarial critics** that verify it, iterating to a human sign-off or an escalation.
Read this to run, verify or extend the harness.

## Trigger: explicit only

"Do ticket X" runs the normal single-session flow ([ticket-lifecycle.md](ticket-lifecycle.md)). The harness
runs only when the user explicitly asks for it ("use the harness for X"). A multi-agent run can spawn
many agents and burn many tokens, so it is never inferred.

## Design

- **Author** implements in the target repo and must paste executed evidence.
- **Two critics in parallel:** the built-in **correctness-critic** writes and *runs* adversarial tests;
  an optional pluggable **static scanner** (bug/security/impact) reads the staged diff. Their
  critical/important findings merge into one blocking set.
- **Why two:** even when every role shares one model family you get failure-mode diversity: dynamic
  test execution versus static analysis catch different real bugs. If policy allows a cross-vendor model
  for critic #2, that is stronger still; if not, same family + an explicit adversarial stance + the
  evidence gate is the accepted mitigation (self-preference bias, arXiv 2410.21819; agent debate,
  arXiv 2511.07784).
- **The orchestrator is a deterministic workflow script, not an LLM.** Fixed control flow (parallel,
  loop, round cap); judgement lives inside each agent. Auditable, reproducible, and no free-chat collusion.

```
task ─▶ [Author] edits repo, pastes executed evidence
            │
            ▼  loop (cap on REWORKS; a review always follows the last rework)
      [Review] correctness-critic (runs tests)  ║  static scanner (JSON findings)
            │  merge → blocking = critical/important from either
            ▼
      blocking and reworks left? ── yes ─▶ [Rework] author fixes all, re-runs, evidences ─┐
            │ no blocking + critic "go"                                 (back to Review) ◀┘
            ▼
      SIGNOFF_READY_FOR_HUMAN ─▶ human reviews diff ─▶ main session commits/pushes (only irreversible step)
      reworks exhausted with blocking open ─▶ ESCALATED
```

## Key mechanisms

- **Evidence gate.** A defect is blocking only if the critic *reproduced* it (command + failing output).
  A concern from reading code is downgraded to a suggestion. The critic has Bash because its ground
  truth is running code.
- **Unparseable scanner output → `scanner_ok=false` → NOT verified**, never a silent pass. A tolerant
  parser handles ```json fences, leading log lines and nested braces.
- **Rework-capped, not review-capped** (reviews = reworks + 1), so a late finding still gets one fix and
  one re-confirm; plus a hard iteration backstop. Default 3 reworks.
- **The human is the only committer.** The run ends at `SIGNOFF_READY_FOR_HUMAN` or `ESCALATED`.
- **Sub-agents never talk to each other.** State passes author → orchestrator → critic.

## Files

| Path | Role |
|---|---|
| `.claude/agents/author.md` | author role (Claude Code subagent definition) |
| `.claude/agents/correctness-critic.md` | critic role: adversarial stance, anti-false-positive rules |
| `tools/harness/orchestrator.workflow.js` | the orchestrator (Workflow tool script) |
| `tools/harness/config.template.json` | run arguments: task, repo, test command, role→model, scanner |

Per-business values (the scanner command, approved models) go in a copy at `business/<co>/harness.json`.
**Role→model is changed only in that config.** Verify each model is served by your backend before
relying on it; a wrong model id fails at run time, not at config time.

## How to run

1. Model backend credentials active; the target repo is a **git repo** (the scanner diffs staged changes).
2. Fill the config: `task`, `repoDir` (absolute), `testCmd`, `models`, `scanner`, `maxReworks`.
3. Run `Workflow({scriptPath: "tools/harness/orchestrator.workflow.js", args: <config object>})`, only
   after the user opted into multi-agent orchestration.
4. **Verify before trusting the status** (next section), then act as the human gate: review the diff in
   the repo and, if good and authorised, commit/push from the main session. Log the run in the ticket's
   `LOG.md`.

## Verifying a run (never trust SIGNOFF blindly)

A run can report SIGNOFF while a critic silently no-op'd (scanner timed out, stderr misread).
1. Grep the workflow journal (`…/subagents/workflows/<runId>/journal.jsonl`): each agent got real input
   and returned real output.
2. Check `scanner.ok` in the result; `false` means the scanner did not verify.
3. Run the tests yourself and reproduce the ticket scenario before committing.

## Static-scanner interface

The orchestrator depends only on this contract, not on a tool:
- **Input:** the staged diff of the target repo (the runner does `git add -A` first).
- **Invocation:** one shell command run in the repo, e.g. `<scanner> review --staged --output json`;
  `{{REPO}}` in the command is replaced with the repo path. Authenticated however the company does it.
- **Output:** JSON on stdout with a `findings` array; each finding has at least `severity`
  (`critical | important | suggestion`), `title`, `file`, `description` (optional `line_start`,
  `confidence`, `source`), plus optional `metrics`.
- **Success:** stdout has the JSON and exit code is 0; stderr warnings are fine.
- **Timeout:** generous and explicit (≥ 420000 ms); multi-minute scanners are common.
- Some scanners need an `origin` remote even for a local diff; the runner can add a self-pointing one.
- No scanner available → `scanner.enabled: false`; the correctness-critic alone still works, single-lens.

## Gotchas (append-only)

- Workflow scripts have **no** Node `process`/`require`/fs and no `Date.now()`/`Math.random()`. Pass
  paths, timestamps and env values via `args`.
- Prove `args` injection on a trivial run before relying on it: one run silently fell back to all
  defaults and reported an empty SIGNOFF. Inlining values in a copy of the script is the fallback.
- A sub-agent running a slow external command needs an explicit long Bash timeout and must judge success
  by stdout + exit code, not empty stderr.
- Reproduce a failing command manually before diagnosing; an agent's error narration can be wrong.
- `isolation: 'worktree'` requires the workspace to be a git repo; when the target repo is separate, the
  author edits it directly. Fan-out authors need per-author worktrees inside the repo.

## Extending

- A `context-loader` phase (ticket fetch + repo map) before the author.
- More critics: a security critic, or a read-only plan critic before implementation.
- Scanner custom rules via its own config, without forking.
- When a reproduced defect clears, record it as a `// fix:[category]` data point
  ([intervention-tracking.md](intervention-tracking.md)) and, if generic, a lesson.
