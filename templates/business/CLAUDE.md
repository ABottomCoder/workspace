# <Business name>

> Business index. Loaded after the routing step picks this business. Keep it short: rules that
> apply to everything in this business, plus one line per child. Facts live in the child files.

- **Tier:** light            <!-- light (default) | heavy — see docs/process/light-track.md, heavy-track.md -->
- **Working language (product output):** English
- **Onboarded:** <YYYY-MM-DD> · **Last refresh:** <YYYY-MM-DD> (re-run `onboard-business` to refresh)

## Key rules (only what applies to all work here)

- Approver and delegations: `people.md` → Authority. Only they authorise outward-facing or irreversible actions.
- Default base branch and PR convention: `stack.md` → VCS.
- <add a rule only if it holds for every project in this business>

## Index

| What | Where |
|---|---|
| People, roles, authority, chat IDs | `people.md` |
| Ticket system, VCS, chat, CI/CD, environments, MCPs, secret names | `stack.md` |
| Business-specific lessons | `lessons.md` |
| Tickets (generated index) | `tickets/INDEX.md` |
| Non-ticket deliverables, research, recaps | `docs/` |
| Apps (bots) configured for this business | `apps/` |
| Secrets (mode 600, never printed) | `.secrets/` |

## Projects

| Project | What it is | Base branch | Details |
|---|---|---|---|
| <project> | <one line> | <main> | `<project>/CLAUDE.md`, live state `<project>/DEVDOC.md` |

## Pending

- [PENDING] <facts onboarding could not discover; resolve and delete the line>
