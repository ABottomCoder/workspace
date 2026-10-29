# tools/eval: prove a prompt change is better before it ships

The workspace is a local agent system: `CLAUDE.md`, `lessons/`, `docs/principles/`, skills and hooks are
its prompt. A change to them can make the agent better or worse, and the online stats
(`tools/sessions/intervention_stats.py`) cannot tell alone: task mix shifts, detection bias (a rule that
makes the agent admit more looks worse) and Goodhart. This kit replays real moments against two versions
of the framework and compares judged outcomes on the same case set.

| Piece | Does |
|---|---|
| `replay.py` | runs cases against one git rev: a worktree of that rev, `business/` and `user/` mirrored in as hardlinks, `claude -p` with read-only tools (Read, Grep, Glob, WebSearch, WebFetch), no MCP, no session persistence |
| `judge.py` | deterministic `auto` checks first, then an LLM judge (sonnet, rubric, may answer UNKNOWN); `--calibrate` grades each case's original answer |
| `report.py` | per-case pass rates, mean per-case rate per kind, B − A with a paired bootstrap over cases; `--split` for A/A |
| `scoreboard.py` | one entry per scored run set with its fingerprint; compares a new version with the recorded baseline |

Data lives outside the workspace and outside git: `<workspace>-eval/` next to it (`WS_EVAL_HOME`):
`worktrees/<sha8>` and `data/` (cases, runs, verdicts, reports). Cases hold conversation excerpts: they
never go into a repo.

## Golden mode (the default for prompt changes)

`replay.py --golden data/golden/<version>` replays a **frozen, offline** set, like test cases for an algorithm:
each case's input, conversation prefix, world and rubric are fixed; only the framework under test differs.

- `golden/<v>/world/`: one shared snapshot of `business/` and `user/` (redacted copies): every text file up to
  300 KB plus every file a case has ever read, minus sessions, backups, the journal, intervention records and
  the eval's own work items (they hold the answers). Copied into the worktree for each case, never linked.
- `golden/<v>/<case>/overlay/`: for a resumed case, the files it reads that live in a git repo, as of its cut
  (last commit before it); `overlay_deleted` lists files that did not exist yet. Without it a later fix in
  today's files hands the replay the answer (seen: T17's code carried the "verified" comment of the later fix).
- `golden/<v>/<case>/prefix.jsonl`: the conversation up to the cut, redacted, paths as `{{WT}}` placeholders.
- `golden/<v>/<case>/case.json`: prompt, rubric (offline variant where the live one needed the web), hashes.
- `manifest.json`: sha256 of every case and of the world. A frozen version is never edited: any change is a new
  version, and scores across versions are not comparable. `replay.py` checks every hash before a golden run and
  refuses on any difference; the data repo stores files byte-exact (`* -text`).
- Offline: tools are Read, Grep, Glob; the guard (`readonly_guard.py --confine`) blocks the web and any path
  outside the worktree (absolute, `/d/…`, drive-relative, `..`).
- Built by `data/build_golden.py <version>`, which asserts the fact cases' answers against the world.

**Tiers** (`golden/<v>/tiers.json`, outside the hashes, re-derived from each A/A): `core` = every case the A/A
shows as discriminating (pass rate 10-90 %) plus one or two cheap always-pass guards per class; `extended` = the
rest, mostly long resumed conversations that always pass. The gate is computed on core (`--tier core` for
replay and report); extended runs before big changes only.

## Scoreboard: score each version once

`data/scoreboard.jsonl` (+ rendered `scoreboard.md`) holds one entry per scored run set: date, rev (+ patch hash),
golden version and world hash, tier, k, model, `claude --version`, judge fingerprint (model, votes, hash of the
verdict code), per-group pass rate and score, every case's passes, cost, tag, report.

- A new version runs only itself: `scoreboard.py compare` pairs it with the latest **baseline** entry of the
  same fingerprint (bootstrap over cases on the stored per-case rates) and prints the gate verdict. Old versions
  are never re-run, nothing is back-filled when cases change (that is a new golden version).
- Fingerprint = golden version + world + tier and its case list + model + CLI version + judge. No match (the CLI auto-updates, e.g.
  2.1.220 → 2.1.312 during the build of this kit) → re-run the current baseline once under the new fingerprint
  and `add --baseline` it, then compare.
- A shipped change is added with `--baseline`; a rejected candidate is added without it, for the record.
- Drift: an anchor run of the baseline's own rev (core, small k) compared the same way; beyond the A/A floor →
  re-baseline.

## Cases

`{"id", "kind": "target"|"fact"|"control", "prompt", "pass", "fail", "session"?, "cut"?, "original"?,
"original_calls"?, "auto"?, "auto_only"?}`

- **target**: a confirmed past error (from the journal's `user/intervention/errors/`). With `session` and
  `cut` (UTC timestamp of the user message the wrong answer replied to) the transcript is resumed up to
  that message (`--resume --fork-session`); without them it is a fresh session. `original` is what the
  agent really answered: the judge must grade it FAIL.
- **fact**: a fresh question whose truth is in today's files (`auto` checks the value and that a reading
  tool was used). No leakage problem: the present is the answer key.
- **control**: answered correctly and simply at the time; guards against over-correction (stalling,
  needless tool calls). `original` must grade PASS.

### Validity rules (each one cost a wrong result once)

1. Cut at the user message the wrong answer replied to, never at the correction: replaying the correction
   tests the recovery, not the mistake.
2. Drop errors the agent fixed itself within the same turn: the turn's final answer was right.
3. Drop future leakage: if later work is now in the files (the fix, the decision), the replay reads it.
   Spot it in the first run: the answer cites work done after the cut.
4. Only what read-only tools can show: no images, browsers, live accounts, running processes, or state
   that has changed since.
5. Resume reloads `CLAUDE.md` from the worktree (probed with a marker); the stored copy is swapped anyway.
   Lesson or principle files read before the cut keep their old text: only what is read live is versioned.
6. Redact: prompts, originals and the replayed history go through `scan_sessions.redact`.
7. No family, health or finance content in cases.
8. Calibrate before trusting the judge: originals with their real tool calls, at least 90 % agreement.
   Facts the rubric states about the conversation are given to the judge as true.
9. The judge is noisy too (measured: one sonnet call repeated agreed 26/28). So: reason before verdict
   (a verdict that contradicted its own reason was seen), majority of 3 votes, and anything mechanical
   (language, a value, a tool used) as an `auto` check instead of a rubric line. With these: sonnet
   27-28/28 on repeats, opus 28/28, sonnet vs opus 27/28.
10. Drop a case whose label depends on context the judge cannot see (an answer citing files read earlier in
   the conversation): it flips between runs and inflates the noise floor.

## Procedure for a prompt change

1. **Baseline on the scoreboard:** the current version's entry for this fingerprint (`scoreboard.md`, ★). None →
   run the current version once (`--golden data/golden/v1 --tier core --k 10`), judge, `scoreboard.py add --baseline`.
2. **Pre-register the gate** in the change's spec before running B (default below).
3. Commit the change on a branch, or pass it as `--patch` (applied in the worktree only); run **only the
   candidate**: `replay.py --rev <rev> [--patch …] --golden data/golden/v1 --tier core --k 10 --tag B-…`, then
   `judge.py --cases data/golden/v1 --runs … --jobs 4`.
4. `scoreboard.py compare --cases data/golden/v1 --tier core --runs …` prints B against the baseline and the gate
   verdict. Ship only if the gate holds; `add` the candidate either way (`--baseline` only if it ships).
5. Before a big change, run `--tier extended` too. Every few weeks, or when results look odd, an anchor run of the
   baseline's own rev (core, k = 5): `compare` reports drift beyond ±10 points → re-baseline.

**Gate (default), from the A/A on golden v1** (`AA-v1`: rev 1582d80, 36 cases × 10 runs, odd vs even; report
`data/reports/AA-v1.md`). Core tier: holdout +3 % [−6 %, +11 %], guards +10 % [−7 %, +33 %] at 5 vs 5 runs; a
10-vs-10 comparison is about √2 tighter (holdout half-width ≈ 6 points). With k = 10 per arm, on core:

- **holdout**: B − A ≥ +12 points (twice that half-width) and the 95 % interval's lower bound > 0;
- **guards**: the interval's lower bound ≥ −10 points, and no guard case falls from ≥ 8/10 to ≤ 5/10;
- **process**: the mean score (0.4 process + 0.6 outcome) over dev + holdout cases, B − A, has a 95 % lower bound
  ≥ −0.05. Pass rates miss a change that keeps answers right but drops the checking behind them: the negative
  control (evidence rules removed) kept its pass rates and fell −0.10 [−0.19, −0.02] here; A/A +0.02 [−0.01, +0.06];
- any case that drops from always passing to failing is read by hand before shipping.

`scoreboard.py` holds these numbers (`GATE`, `FLOOR`). The positive control (`POS-v1`, k = 5) passed the holdout
line by far (+50 % [+20, +79]) and the process line (+0.36 [+0.15, +0.56]); its guard interval reached −12 with 5
guards at k = 5, so C07 and C12 joined the core guards (8 now; user decision 2026-10-29, the line itself
unchanged). Re-run on all 8 core guards at k = 10: guards +2 % [−11, +16], still 1 point under the line (C05 10→7,
C07 10→8; no guard case fell to ≤ 5/10). Read: an oracle stuffed into `CLAUDE.md` is not a side-effect-free
change, so a guard flag on it is plausible, not proof the line is too tight. The
fingerprint covers the tier's case list, so the core baseline was re-added from the same AA-v1 runs. Earlier gate
(live world, AA-1582d80): holdout ≥ +10, guards ≥ −12.

Re-run the A/A when the golden version, the model, the CLI or the judge changes: the floor belongs to that
combination (the scoreboard fingerprint).

## Held-out cases

Each case carries an error class (`cls`: unverified-claim, misread, absence-count, lookup, language) and a
stable split within it: `dev` or `holdout`; controls are `guard`. A rule change may be written from **dev**
cases only (their transcripts, originals, rubrics); it is judged on **holdout** cases and guards. A change
that flips its own example but not the held-out ones has memorised a case, not learned a class.

## Flywheel

Every confirmed error the journal records is a candidate case. Add it (`data/build_cases.py`) only after it
passes the validity rules and calibration, with a class; the build assigns its split. A lesson written after
a correction counts as proven only when the **holdout** cases of its class improve under the gate, not when
its own case flips.

## Who may change the eval

The judge rubric (`judge.py`), the gate and these rules sit in the framework that ordinary sessions edit, so
the loop being graded could otherwise loosen its grader. Changes to `tools/eval/`, the gate or a case's
rubric go in their own commit, separate from any prompt change, with the user's approval; a prompt-change
branch that touches them is not evaluated. The replay always runs the judge and report from the main
checkout, never from the worktree under test. The data dir is a local git repository: every case or rubric
edit is a commit there, so a quiet change to the test set shows up in its log.

## Coverage

Single-turn, read-only replays. Not measured: errors inside long multi-step tasks, in actions (commands,
sends, deploys), and judgments that depend on context the judge cannot see. Every report states this; a
pass is no evidence about those.

## Operations

- One replay per worktree at a time (lock `worktrees/<sha8>.lock`): each run rebuilds the mirror.
- Runs are resumable (existing result files are skipped) and case-major, so repeated runs of one case
  hit the prompt cache: k runs cost about 1.4 × the first, not k ×.
- Cost: a fresh case is cents; a resumed long conversation is 1 to 5 USD for its first run.
- `replay.py --cleanup` removes worktrees: the mirrors are hardlinks (originals untouched); read-only
  originals are never mirrored, and a read-only link is restored on removal. `tests/test_eval.sh` covers it.
