# <Project name>

<What it is in 2–4 sentences: who uses it, what it does, current phase.> **Start from `DEVDOC.md`**
(local, gitignored: current state, active work, TODO, change log, accounts). Design docs: `docs/`.

<History, only if it changes how you read the code: renamed from X, forked from Y, legacy repo Z.>

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

Append newly discovered gotchas immediately. Repo knowledge here; live state, people and accounts
in `DEVDOC.md`; durable design in `docs/`. Deviations from the business defaults (base branch,
host, conventions) go here and in the business `stack.md` repo table.
