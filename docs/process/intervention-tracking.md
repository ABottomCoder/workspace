# Intervention Tracking

Measure execution autonomy with data, not feeling. Heavy tier: one row at the end of **every** ticket,
including fully autonomous ones (they are the denominator). Light tier: optional.

Core design: turn a subjective signal into an objectively collectable one. The agent cannot reliably
judge "was I corrected?", so the user gives an unmistakable marker and the agent only pattern-matches it.

## The `// fix:[category]` marker (the user's only burden)

To correct the agent, the user prefixes the message with `// fix:[category]`, e.g.
`// fix:[approach] use the index, not a full scan`. Case-insensitive (`// fix:`, `// FIX:`). The agent
never decides whether a message was a correction; it only checks for the prefix. That one message both
corrects and records one data point.

`category` is exactly one key from the fixed taxonomy (free-form can't be aggregated). Keys are English
and stable; display labels may be localised in `user/profile.md`.

| Key | Meaning |
|---|---|
| `requirements` | misread the ticket / AC, missed an edge condition |
| `approach` | result right but the approach was sub-optimal |
| `implementation` | approach right, code wrong |
| `testing` | tests missed coverage or tested the wrong thing |
| `tooling` | wrong tool or wrong parameters |

The same keys are used by `tools/sessions/scan_sessions.py` and the `/scan-sessions` skill; change them
in all three places together.

## The log

`user/intervention/log.md` (personal, cross-business; ticket IDs are business data, so it never enters
the framework repo). One row per ticket:

| Business | Ticket | Date | Rounds | Tools (+counts) | Help requests | PR passed first time? | `// fix` markers (category × n) | Notes |
|---|---|---|---|---|---|---|---|---|

1. **Capture objective fields as you go** (rounds, tools and counts, help requests, PR result) in the
   ticket's `LOG.md`; don't reconstruct from memory at the end.
2. **Derive intervention fields only from received `// fix:` markers.** Never self-judge.
3. **Append the row at ticket close.**
4. **Periodic analysis** (on request, about every 1 to 2 weeks): group by category, report the
   distribution and the autonomy rate (tickets with zero markers / all tickets), and propose one targeted
   rule change (a lesson or a principle edit) for the dominant category.

## Scan-based mode (supersedes manual rows when active)

`/scan-sessions` runs `tools/sessions/scan_sessions.py` over `user/sessions/`, writes compact digests
(`user/intervention/digests/`, may contain conversation content: never committed), then judges them with
a high bar: an error counts only with a real `// fix:` marker, an explicit user correction ("that's
wrong", "redo this"), or an explicit admission by the agent. Clarifying questions and preference tweaks
are not errors. Results go to `user/intervention/stats.md` (autonomy, category distribution, dominant
pattern → action) and `tracking.md` (one narrative line per confirmed error).

## Optional hardening

If the user keeps forgetting the prefix, a `UserPromptSubmit` hook can regex
`^//\s*fix:\[(.+?)\]` (case-insensitive) and append the marker to the log automatically. Not built;
mention it as the upgrade path when the marker proves easy to forget.
