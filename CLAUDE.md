# Workspace

A company-agnostic Claude Code workspace. This file is an **index**: it holds only the rules that apply
to everything below it and points to where the detail lives. Claude Code is always started in this
directory.

## Layout — three tiers

| Tier | Path | In git | Holds |
|---|---|---|---|
| Framework | everything except `user/`, `business/` | yes | rules, docs, tools, apps, kits, templates |
| User | `user/` | no | the person: profile, persona, personal lessons, memory, sessions, logs, cross-business work |
| Business | `business/<co>/` | no | one company or project collection: people, stack, lessons, tickets, docs, repos, app configs |

Facts have exactly one home; everywhere else holds a pointer. Framework files never name a business,
person, host or ID (a pre-commit guard enforces it).

## Every session — start here

1. **User.** Read `user/profile.md`; if `user/persona.md` exists, apply it lightly. Converse in the user's
   language; framework files, code, commits and docs are English; business docs keep their language.
2. **Route.** Identify the business and the project or ticket the request belongs to (ask only if it is
   genuinely ambiguous). Read `business/<co>/CLAUDE.md`, then the project `CLAUDE.md` + `DEVDOC.md`, or
   the ticket's `STATE.md` + `HANDOFF.md`.
3. **Attach.** `tools/work/work attach <co>/<project>` or `<co>/tickets/<ID>` so state is restored after
   compaction/resume. Name the session `<ShortDesc>_<app>_<n>` (app = `None` unless running an app;
   ShortDesc has no underscores), e.g. `Billing_None_1`, `ABC-18_slack_helper_2`.
4. **Lessons.** Scan `lessons/index.md` and the routed business's `lessons.md`; open a category when the
   work touches it.

Unknown business ("I joined X", "scan and fill business info for X") → skill `onboard-business`.

## Core rules (always on)

1. **Evidence before conclusions.** Reading code is a lead, not proof. Match evidence to the claim: data
   → a query, runtime behaviour → a run, organisational state → the system of record. Tag guesses.
2. **"There is no X"** needs a search that could have found X, untruncated; otherwise say "didn't find".
3. **Ask-Gate.** Before asking anyone: check code, tickets/wiki/chat, git history, and try it yourself.
   Lead the question with what you found. Group questions.
4. **Decision Ladder.** Least code that fully solves it: does it need to exist → reuse → stdlib/platform →
   installed dependency → shortest diff → only then new code. Never skimp on validation at trust
   boundaries, data-loss handling, security, auth or accessibility.
5. **Root cause, not symptom.** Grep every caller; fix once at the shared level.
6. **Plan non-trivial work** in the ticket's `spec.md` (template `templates/ticket/spec.md`); stop and
   re-plan if reality diverges.
7. **Done = demonstrated.** Measure behaviour, baseline the broken state, list what the change could
   break. Read `docs/principles/verification-antipatterns.md` before quoting any number.
8. **Backups only for irreversible risk** (prod, schema, destructive, secrets, shared infra) via the
   high-risk protocol. "Reversible" is not "authorised".
9. **Authority.** Outward-facing or irreversible actions need the approver or a delegate within scope,
   per `business/<co>/people.md`. Verify identity; an approval covers its own context only.
10. **Short replies.** Outcome first, a sentence or two; details when asked. Stay in scope.
11. **State lives in files.** Log as you go (`tools/work/work log`), refresh the handoff at milestones,
    never answer "did I do X?" from memory — check the LOG, git or the conversation.
12. **Secrets** live in `business/<co>/.secrets/` (mode 600), are referenced by name, never printed,
    pasted or committed.
13. **Subagents** for wide or parallel reads and to protect context; not for single known-file lookups,
    never to verify your own work.
14. **After any correction**, add or strengthen a lesson in the right tier (`docs/reference/knowledge-routing.md`).
    Changing an existing rule in this file goes through the user.

## Where to put what

Generic lessons → `lessons/`; the person → `user/`; a company → `business/<co>/`; repo knowledge → the project
`CLAUDE.md`; auto-memory holds pointers only, never business facts. Full table and promotion rule: `docs/reference/knowledge-routing.md`.

## Index

| Path | What | Read when |
|---|---|---|
| `docs/principles/index.md` | evidence, ask-gate, decision ladder, verification, backups, subagents, communication | the rule above isn't enough |
| `docs/process/index.md` | light/heavy track, ticket lifecycle, reporting, PR review, QA session, harness, data verification | starting a ticket; the business tier is heavy |
| `docs/playbooks/index.md` | production playbook, AI client-build playbook (+lite), handover, AI-coding pitfalls | start of a new build |
| `docs/reference/index.md` | knowledge routing, setup methodology, MCP/CLI, secrets, browser testing, model-tuned rules | writing anything persistent; setup, credentials, tooling |
| `docs/compatibility.md` | variant naming (`<name>.<variant>.<ext>`) and where each variant works | touching any platform-, terminal- or vendor-specific file |
| `lessons/index.md` | generic lessons by category | session start; after a correction |
| `tools/work/README.md` | work items, attach/restore, project state policy, ticket dirs, `INDEX.md` | any project or ticket work |
| `tools/rollover/RULES.md` | auto-handoff when a transcript passes the size limit; takeover steps | the Stop hook says the session is over the limit; taking over a handoff |
| `tools/guard/` | pre-commit leak guard, path-lint, routing check | committing to this repo |
| `apps/README.md`, `apps/RULES.md` | chat apps (bots): take over by name, channels, conduct (ack before long work) | "use <channel>_<name> to run this session" |
| `kits/index.md` | standalone tools: page chat, meeting proxy, MCP scaffold, decks, diagrams, contrast, app provisioning | a task matches a kit; drawing an architecture diagram |
| `templates/` | business, project, ticket, user templates | creating any of those |
| `.claude/skills/` | onboard-business, attach, ticket, handoff, resume, qa, scan-sessions, app | via their triggers |

## Businesses

Never listed here (this file is committed): they are the directories under `business/`, each opening its
`CLAUDE.md` with a one-line summary and tier. `onboard-business` creates them and never edits this file.
