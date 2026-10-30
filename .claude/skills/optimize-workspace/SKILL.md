---
name: optimize-workspace
description: One improvement round of the workspace itself - learn from recent sessions and work, update the workspace, evaluate the change on the framework eval, compare its report with the previous one, and publish a GitHub release only if it helped. Use when the user says "开始优化workspace", "optimize the workspace", "run an improvement round", or the equivalent in any language.
---

# optimize-workspace

Two roles, kept apart. The **learner** (a subagent) reads recent sessions and work and changes the workspace; it
never sees the eval. The **evaluator** (this session) runs the eval and decides. A change judged by cases its
author has read is tuned to the test, not to the work.

## 0. Start

- `main` clean and current (`git status`, `git pull`); attach to the eval work item if there is one and log the
  round. Window: since the latest release tag (`git describe --tags --match 'v[0-9]*' --abbrev=0`, its date); none →
  the last 14 days.
- Baseline: the latest baseline entry in `tools/eval/history/scoreboard.jsonl` for `framework-v1`, tier `core`,
  with today's model, `claude --version` and judge. None (the CLI updated, say) → re-baseline the current `main`
  first (steps 2-3 on `main`, then `scoreboard.py add --baseline`).

## 1. Learn (subagent)

- Catch up the journal and error records first (skill `scan-sessions`, step 1).
- Brief a `general-purpose` subagent with the window and:
  - **reads:** `user/intervention/errors/`, `user/intervention/stats.md`, `user/logs/journal/`, the LOG and HANDOFF
    of work items active in the window, and a transcript under `user/sessions/` when an error needs its context;
  - **never reads** anything under `tools/eval/` or the eval work item (cases, rubrics, history, reports);
  - **writes** each lesson, rule, doc, skill or tool fix where `docs/reference/knowledge-routing.md` puts it, in
    the lessons format, by the Decision Ladder; framework files stay company-agnostic; a change to an existing core
    rule in `CLAUDE.md` is listed as a proposal for the user, not made;
  - **output:** commits on branch `opt/<YYYY-MM-DD>`, and a change list: what, where, the evidence (day, session),
    and the failure class it addresses.
- Check the branch: `git diff --stat main...opt/<date>` touches nothing under `tools/eval/`; the pre-commit guard
  and `bash tests/run.sh` pass. Nothing worth changing → stop and say so.

## 2. Pilot

Two core cases (one target, one guard) at `--k 1`, tag `PILOT-<date>`: replay, then judge. Check that each step
produced what it should (two run files, two verdicts with a score and a reason that fits the answer), that no
ALERT appears, and that the replay used the branch tip. Only then the full run. (`compare` and `add` need the whole
tier, so they are first exercised in step 3; nothing of the pilot goes on the scoreboard.)

## 3. Evaluate

`G=tools/eval/golden/framework-v1`, tag `OPT-<date>`, rev = the branch tip.

- Split the core ids (`$G/tiers.json`) into 3-5 groups and start one replay per group in the background:
  `python3 tools/eval/replay.py --rev <rev> --golden $G --only <ids> --k 10 --slot <n> --tag OPT-<date>`.
- Every core case has 10 runs → `python3 tools/eval/judge.py --cases $G --runs <run dir> --jobs 4` → every run has
  a verdict. A short count is a broken run: fix and rerun those cases, never judge around it.
- `python3 tools/eval/scoreboard.py add --cases $G --tier core --runs <run dir> --note "<one line>"`. This writes
  the candidate's **version report** into `tools/eval/history/` with its comparison against the baseline's report
  and the gate verdict. Send the report to the user (HTML).

## 4. Decide from the report

**Effective** (the comparison passes the gate, and every case flagged "read by hand" was read and is fine):
`scoreboard.py promote OPT-<date> --tier core`; merge `opt/<date>` into `main` (no fast-forward) with the history
files, `bash tests/run.sh`, push; tag `v<N+1>` on the evaluated rev, where `v<N>` is the latest release (`v0` = the
first baseline, 2026-10-30), push the tag; `gh release create v<N+1> --title "v<N+1> · <YYYY-MM-DD>" --notes-file <file>`: three to six English bullets on what changed and
why, the scores against the previous release, and the path of the version report. Tell the user in their
language what changed, in a few lines.

**Not effective:** do not merge. Find the cause in the report (per-case table, cases that fell) and the judge's
reasons (`<run dir>/*.verdict.json`), then act on it:

- the change made some behaviour worse → send the learner the behaviour to fix in general terms (never a case,
  a rubric or an expected answer), or drop that change; evaluate once more;
- nothing moved and the change addresses a class the eval does not cover → the eval cannot see it: tell the user
  and offer to keep it on its branch, merge it on their word, or add a case for that class in the next framework
  set version (`golden-src/<v+1>/`, rebuilt and re-baselined);
- the difference sits inside the A/A floor, the fingerprint drifted, or runs are missing → rerun, re-baseline or
  fix the run first.

Either way commit the candidate's version report and scoreboard line to `main` (rejected candidates stay on
record), log the round, and report: what was learned, the report, the decision, the next step.

Cost: the pilot takes minutes; the full core run about 26 minutes on 3 slots (`tools/eval/README.md`).
