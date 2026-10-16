---
name: onboard-business
description: Auto-discover a company or project collection and fill business/<co>/ (people, stack, repos, tier). Use when the user says "scan and fill business info for X", "onboard business X", "I joined company X", "set up company X", "refresh business X", or the equivalent in any language. Re-runnable: on an existing business it refreshes and fills gaps.
argument-hint: "<business name> [refresh]"
---

# onboard-business

Builds or refreshes `business/<co>/` by discovering everything reachable, asking the user **once**
for what discovery could not reveal, then cloning repos and writing the business files.

`<co>` = lowercase kebab of the business name (`acme`, `acme-labs`). Ask only if the name is ambiguous.

## Boundaries

- **Read-only is free:** local files, CLIs, MCP reads, API `GET`s. No confirmation needed.
- **Outward-facing writes need the approver** (sending messages, creating tickets/comments, pushing,
  creating tokens or apps on someone's behalf, joining channels). Onboarding itself does none of them.
- **Secrets:** never print a token or file content that may hold one. Store tokens the user gives you
  in `business/<co>/.secrets/<name>` (dir 700, file 600) and reference them by name only.
- **Nothing business-specific enters the framework.** Writes go only to `business/<co>/` and the one
  index line in the main `CLAUDE.md`. Finish with `git status` in the main dir: it must be clean apart
  from that line.

## Mode

- `business/<co>/` missing → **create**: copy `templates/business/` into it.
- Exists → **refresh**: read the current files first; keep everything verified, fill `[PENDING]`
  items, add new repos/members, mark vanished ones `(not found <date>)` instead of deleting. Never
  overwrite a value the user stated with a discovered guess; list conflicts in the report.

## Step 1 — Local discovery (no questions)

Run `reference/local.md`. It yields: git identities, SSH host aliases and which hosts have keys,
installed CLIs and their login state, configured MCP servers, relevant env var *names*, and existing
clones on disk with their remotes. Group the results by system (VCS host, ticket system, chat, wiki,
cloud) and pick the adapter for each from the table below.

## Step 2 — Remote discovery (read-only, with what is already authorised)

For each detected system, follow its adapter. Each adapter lists detection, access method, read-only
commands and the token scopes to ask for if access is missing.

| Kind | Adapters |
|---|---|
| VCS | `reference/vcs/github.md`, `reference/vcs/gitlab.md`, `reference/vcs/bitbucket.md` |
| Tickets | `reference/tickets/jira.md`, `reference/tickets/github-issues.md` |
| Chat | `reference/chat/slack.md`, `reference/chat/teams.md` |
| Wiki | `reference/wiki/confluence.md` |

A system with no adapter: discover what you can, record it in `stack.md`, and add a new adapter file
next to the others (same shape) so the next run has it.

Collect: orgs/workspaces, repos (name, default branch, last activity, description, language), members
and their handles, ticket projects and key prefixes, chat channels, wiki spaces. Cap listing calls
(first 100–200 per kind, most recently active first) and say so if you truncated.

## Step 3 — One grouped question round

Send the user a single message, grouped, each question labelled with what you already checked:

1. **Access missing** — per system: what it would unlock, exact token type and minimal read scopes
   (from the adapter), where it will be stored (`business/<co>/.secrets/<name>`). Offer "skip".
2. **Facts discovery cannot reveal** — which repos/projects are "ours", team boundaries, the
   **approver** and any scoped delegations, process tier (light default / heavy), working language,
   default base branch if repos disagree.
3. **Confirmations** — anything inferred with low confidence (e.g. "X looks like the tech lead").

Do not block on answers: continue with everything that does not depend on them. Unanswered items
become `[PENDING]` in the files. When the user pastes a token, write it straight to the secrets file
(`umask 077`; `chmod 600`), never echo it, then re-run the affected adapter.

## Step 4 — Clone and describe projects

For each repo confirmed (or clearly) the team's:

- Already cloned elsewhere on disk → tell the user and ask before moving it; never move silently.
- Otherwise clone into `business/<co>/<project>/` (SSH alias if one exists for that host).
- If `<project>/CLAUDE.md` is missing, generate it from `templates/project/CLAUDE.md`: purpose from
  README, quick-start commands from build files (`package.json`, `Makefile`, `pyproject.toml`,
  `pom.xml`, `docker-compose*`), base branch and recent activity from `git log`. Mark guesses
  `[UNVERIFIED]`. If the repo already has a `CLAUDE.md`, leave it alone.
- Create the project state file per the business state policy (Step 5 records it in `stack.md`;
  `tools/work/work attach <co>/<project>` does it): local → `DEVDOC.md` from `templates/project/DEVDOC.md`,
  ignored by that repo (prefer `.git/info/exclude`, which changes nothing the team sees); orphan branch →
  `.state/` worktree (`tools/work/README.md`); in-repo → `docs/HANDOFF.md`, committed.

## Step 5 — Fill the business files

- `people.md`: members (role, modules owned from CODEOWNERS / commit history, chat ID), channels,
  authority (approver + delegations exactly as the user stated them; never inferred).
- `stack.md`: every system found, with access method and secret *names*; the repo table; the project state
  policy (ask whether a personal orphan branch on the company remote is allowed; default local).
- `CLAUDE.md`: tier, working language, onboarded/refresh dates, project table, `[PENDING]` list.
- Leave `lessons.md`, `tickets/INDEX.md`, `docs/`, `apps/` as templates unless there is content.

## Step 6 — Register the business

Make sure `business/<co>/CLAUDE.md` opens with a one-line summary and `tier: <light|heavy>` — the
directory itself is the registration. Never edit the main `CLAUDE.md` or any other framework file:
it is committed and must stay business-free.

## Step 7 — Report

Short: what was found per system (counts, not dumps), repos cloned, files written, `[PENDING]`
items, and what needs the user (tokens, facts, approvals). Then remind the user that re-running
"refresh business <co>" fills the gaps once access arrives.
