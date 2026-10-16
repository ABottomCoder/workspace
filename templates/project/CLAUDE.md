# <Project name>

<What it is in 2–4 sentences: who uses it, what it does, current phase.> **Start from the state file**
(`DEVDOC.md`, `.state/DEVDOC.md` or `docs/HANDOFF.md`, per the business state policy: current state,
active work, TODO, change log). Design docs: `docs/`.

<History, only if it changes how you read the code: renamed from X, forked from Y, legacy repo Z.>

## ▶ Run book (when the user says "start / stop <project>")

**Safety tier:** <demo | signal-only | live>   <!-- demo, signal-only: run directly; live (real money or real
side effects): list the commands and wait for the user's go-ahead -->

- **Start:** `<absolute interpreter path> <entry>`; foreground or background monitor; success signal: `<log line>`.
  Guard: list running tasks first; never start a second copy.
- **Stop:** `<stop command or task to stop>`.
- **Recover context:** `<command that prints recent history/state>` (optional).

Keep this block state-agnostic: how to start/stop, never whether it is running now (that is live state).

## Quick start

```bash
<install>          # runtime version required
<infra up>         # local DB / cache, ports
<migrate>
<run>              # ports
```

- Full gate: `<verify command>` (what it runs).
- Tests: `<test command>` (what it needs running). Typecheck/lint: `<command>`.
- Required env vars: see `.env.example`; never commit `.env`.

## Architecture

- Repo layout: `<dir>/` — responsibility, one line each.
- Key entry points at file granularity (the file to open first for each concern).
- External services this depends on and who owns them.
- Branch → environment mapping, if deploys are branch-driven.

## Invariants (do not break)

- <rule> — why it exists and what breaks if violated (tenant isolation, migration immutability,
  idempotency of irreversible calls, secrets handling, logging/trace IDs, UI copy location, …).

## Gotchas

- <non-obvious behaviour, workaround, known issue> (append only; never delete, mark obsolete instead)

## Common patterns

- Logging, error handling, DB access, naming conventions specific to this repo.

## Maintaining this file

Budget: about 200 lines / 8 KB. This file holds only routing (doc map + run book), invariants and
must-not-do warnings, and how to run; overflow moves to `docs/` (architecture, operations) with a
pointer left here, never deleted (zero-loss move, `.claude/skills/handoff/SKILL.md`).
Acceptance: a fresh session reading only this file and the state file can answer what the project is
(business purpose), what is running or in flight, how to run/test/debug it, its architecture, the
gotchas already paid for, and what must not be done.

Append newly discovered gotchas immediately. Repo knowledge here; live state, people and accounts
in the state file; durable design in `docs/`. Deviations from the business defaults (base branch,
host, conventions) go here and in the business `stack.md` repo table.
