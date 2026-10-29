---
name: scan-sessions
description: Catch up the daily journal and the agent's confirmed-error stats from local Claude Code transcripts (user/sessions/), then report the two-week trend. Use when the user says "scan sessions", "tally session errors", "how often was I corrected", "catch up the journal", "补日志", or runs /scan-sessions.
---

# scan-sessions

Lazy-mode intervention tracking (`docs/process/intervention-tracking.md`) plus the daily journal, in
one pass per finished day. It normally runs by itself: the SessionStart hook
`tools/sessions/journal-hook.sh` starts the catch-up in the background at most once a day. This skill
is the manual run and the read-out.

1. **Catch up:** `python3 tools/sessions/journal_catchup.py` (run_in_background for more than a few
   days; `--dry-run` lists the pending days, `--max N` limits the run, `--day YYYY-MM-DD` re-judges a
   day). It rebuilds the per-day extracts (`scan_sessions.py` → `user/intervention/days/`), runs the
   worker (`journal-day.md`, `claude -p`, no tools) on each pending day, writes the journal entry into
   `user/logs/journal/YYYY-MM.md` and the errors into `user/intervention/errors/<day>.json`, and
   rebuilds `stats.md` and `tracking.md` (`intervention_stats.py`). Cost per day:
   `user/intervention/.worker_runs.jsonl`.
2. **A failure** stops after 3 in a row: check `claude -p` works in a terminal (an expired login is the
   usual cause), then rerun.
3. **Report from `user/intervention/stats.md`:** the latest full two-week period against the ones
   before it (errors per 100 user messages, top category), lessons with errors after they were added
   (they are not working), and the category with most errors no lesson covers. Propose one concrete
   lesson or principle change for the worst of these; changing rules goes through the user.

Error standard (kept in `tools/sessions/journal-day.md`): a `// fix:` marker, an explicit user
correction, or an explicit agent admission; if unsure, not an error. Extracts, journal and errors hold
conversation content and live only under `user/` (never committed).
