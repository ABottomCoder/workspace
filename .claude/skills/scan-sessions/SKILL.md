---
name: scan-sessions
description: Incrementally scan local Claude Code transcripts (user/sessions/) and update the agent's confirmed-error stats and tracking. Use when the user says "scan sessions", "tally session errors", "how often was I corrected", or runs /scan-sessions.
---

# scan-sessions

Lazy-mode intervention tracking (`docs/process/intervention-tracking.md`): no manual logging; judge
the errors the agent made from transcripts, with a high evidence bar.

1. **Extract (deterministic):** `python3 tools/sessions/scan_sessions.py` (`--list` to preview,
   `--all` to rescan). It reads `user/sessions/` (fallback: the main dir's `~/.claude/projects`
   dir), skips already-scanned lines (`user/intervention/.scan_state.json`) and writes one digest per
   new/changed session to `user/intervention/digests/<sessionId>.md`.
2. **Nothing new** → say so and stop.
3. **Judge the new digests.** More than ~3 → parallel subagents, ~10 digests each, all with this
   standard:
   - Count an error only with strong evidence: (a) a `// fix:[<category>]` marker, (b) the user
     explicitly says something was wrong ("that's wrong", "redo this"), or (c) the agent explicitly
     admits one ("I misread", "that was wrong").
   - Clarifying questions, mid-course refinements and preference tweaks are not errors. If unsure, it
     is not an error. Never speculate.
   - One category per error: `requirements`, `approach`, `implementation`, `testing`, `tooling`.
   - Return JSON: `{session, title, date, is_ticket_work, errors: [{category, signal, root_cause, corrected}]}`.
4. **Merge** (append/update, never rewrite history):
   - `user/intervention/stats.md`, created from `stats-template.md` next to this file if missing:
     recompute the three dashboards, update "Last scan" and the session count.
   - `user/intervention/tracking.md`: one short narrative line per confirmed error, newest first;
     list clean sessions.
5. **Report:** new sessions, new errors, the dominant category this round, and any repeated root
   cause worth a lesson (`lessons/`) or principle edit.

Digests contain conversation content and live only under `user/` (never committed).
