# Lessons index

Generic agent-behaviour lessons that hold at any company. Business-specific lessons live in
`business/<co>/lessons.md`; this user's taste-level corrections in `user/lessons.md`.

**At session start:** scan this index and the routed business's lessons; open a category file when the
work touches it. **After any correction:** add or strengthen an entry in the right category (never a
duplicate). **Promotion:** when a business lesson still holds with the business details removed, add the
generic form here and leave a pointer in the business file. **Into the core rules** (`CLAUDE.md`, loaded
every session) only a lesson that is a cross-domain behaviour reflex (evidence, verification, pushback,
checking state after a failure) and keeps recurring; propose it, the user approves. A high Seen count in one
domain (code, communication, operations) is not enough: it reflects how often that task is done, and loading
it everywhere wastes context on unrelated work. Domain lessons stay in their category file.

Entry format: `### <short title>` / **Mistake:** / **Root cause:** / **Rule:** / **Seen:** <times merged>.
Entries are ordered by Seen.

- [verification](verification.md) (41) — proving a change, fix or claim is true: checks that can fail, real entry points, reading evidence
- [evidence-and-asking](evidence-and-asking.md) (17) — self-service before asking, hypothesis vs observation, relayed claims, read-only probes
- [engineering](engineering.md) (25) — generic code and framework gotchas (frontend, backend, database, infra code)
- [tooling-and-environment](tooling-and-environment.md) (33) — shell, processes, schedulers, CLIs, browsers, platform quirks
- [data-and-production](data-and-production.md) (19) — restarts, migrations, destructive ops, backups, production data and environments
- [communication](communication.md) (16) — writing for the reader, threads, reports, client promises, user-facing copy
- [multi-session-and-bots](multi-session-and-bots.md) (12) — parallel sessions and chat bots: identities, listeners, shared files, message delivery
- [git-and-release](git-and-release.md) (14) — reviews, PRs, branches, destructive git, deploy and CI proof
- [planning-and-scope](planning-and-scope.md) (12) — estimates, scope discipline, plans as checkable claims, design trade-offs
- [authority-and-approval](authority-and-approval.md) (7) — who may authorise what, identity of approvers, delegation
- [context-and-memory](context-and-memory.md) (7) — subagents, knowledge routing, docs vs memory, self-review
- [secrets-and-safety](secrets-and-safety.md) (6) — credentials handling, publication channels, redaction, privilege

Total: 208 entries.
