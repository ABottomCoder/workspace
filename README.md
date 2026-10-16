# Workspace

A company-agnostic framework for working with [Claude Code](https://claude.com/claude-code) across many
companies and projects. It gives every session the same rules, the same places to put knowledge, and a way to
resume work after compaction, a restart or a hand-off, without ever committing personal or company data.

Start Claude Code in this directory; `CLAUDE.md` is the entry point the agent reads first.

## What it gives you

- **Rules and lessons.** Always-on core rules in `CLAUDE.md`; about 200 generic lessons learned from real
  corrections in `lessons/`; principles, processes and playbooks in `docs/`.
- **Three tiers, one home per fact.** Framework (this repo, English, business-free) · `user/` (the person:
  profile, memory, transcripts, logs) · `business/<co>/` (people, stack, lessons, tickets, repos). `user/` and
  `business/` are gitignored. Routing table: `docs/reference/knowledge-routing.md`.
- **Work items that survive compaction.** `tools/work` binds a session to a project or ticket; a SessionStart
  hook re-injects its state on resume/compact. Project live state follows a per-company policy (committed
  `docs/HANDOFF.md`, an orphan branch, or local `DEVDOC.md`).
- **Hand-off.** The `handoff` and `resume` skills save and restore a session's working context; rollover can
  open a new session automatically when a transcript gets large (macOS terminals).
- **Leak guard.** A pre-commit hook blocks business/person names (from `user/denylist.txt`), home paths and
  secret-like tokens from entering the framework.
- **Tests.** `bash tests/run.sh`: plain-bash tests for the tools, same files on macOS and Windows; the pre-commit
  hook runs them whenever `tools/` or `tests/` change.
- **Skills.** `onboard-business`, `attach`, `ticket`, `handoff`, `resume`, `qa`, `scan-sessions`, `app`.
- **Apps and kits.** `apps/`: chat bots any session can take over by name (Slack adapter). `kits/`: standalone
  tools (page chat, meeting proxy, MCP scaffold, deck tools, contrast check, Slack app provisioning).

## Setup on a new device

```bash
git clone git@github.com:<owner>/workspace.git && cd workspace
bash install.sh
```

`install.sh` is idempotent. It creates `user/` from `templates/user/`, points Claude Code's memory at
`user/memory`, links the transcript directory to `user/sessions`, and installs the leak guard. Also set
`"cleanupPeriodDays": 36500` in `~/.claude/settings.json` so transcripts are never deleted.

Supported: macOS and Windows (Git Bash). Small OS differences branch inline (e.g. `tools/lib/link.sh`), large
ones are variant files; status per feature in `docs/compatibility.md`.

## Daily use

- New company or project collection: ask Claude to onboard it (`onboard-business` creates `business/<co>/`).
- Real work: Claude routes the request and runs `tools/work/work attach <co>/<project>` (or a ticket).
- Before stopping or at milestones: say "handoff"; later, "resume <target>".
- After any correction, a lesson goes to the right tier; generic ones are promoted into `lessons/`.

## Several devices

Only the framework syncs through git. `user/` and `business/` stay on each machine; sync or back them up
separately. Commit framework changes on any device and pull on the others; line endings and script modes
are pinned by `.gitattributes` (new scripts committed from Windows need `git update-index --chmod=+x`).

## Layout

| Path | What |
|---|---|
| `CLAUDE.md` | entry point: core rules, session start, index |
| `lessons/` | generic lessons by category (`lessons/index.md`) |
| `docs/` | principles, process, playbooks, reference, compatibility |
| `tools/` | `work` (work items), `guard` (leak guard), `rollover`, `sessions`, shared `lib` |
| `tests/` | tool tests (`bash tests/run.sh`) |
| `.claude/` | hooks (`settings.json`), skills, agents |
| `templates/` | business, project, ticket and user templates |
| `apps/`, `kits/` | chat apps; standalone tools |
| `install.sh` | one-time setup per device |
