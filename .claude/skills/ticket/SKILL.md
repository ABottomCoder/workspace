---
name: ticket
description: Create, log, hand off, close or index a ticket / work item dir (business/<co>/tickets/<ID>/ or user/work/<slug>/). Use when the user says "new ticket", "open a ticket for X", "log this", "close ticket <ID>", "list tickets", "ticket index", or starts finite work that should be tracked.
argument-hint: "new|log|handoff|close|index [<business>] [<ID>] [...]"
---

# ticket

One dir per ticket: the ticket-system ID as written (`ABC-18`), else a short kebab description.
Everything about it (reports, QA, evidence) lives in that dir. Nothing is ever deleted.
Format of `STATE.md` and the commands: `tools/work/README.md`.

| Action | Do |
|---|---|
| **new** | `bash tools/work/new-ticket <co> <ID> "title" [project]`, then fill `STATE.md` (links, acceptance criteria, who), then `bash tools/work/attach <co>/tickets/<ID>`, then `bash tools/work/index <co>`. Non-trivial work (3+ steps, prod or schema, destructive): copy `templates/ticket/spec.md` in and fill it before code. |
| **log** | `bash tools/work/log "<one line>"` (bound item) or `bash tools/work/log <co>/tickets/<ID> "..."`. Log changes, decisions + why, messages sent, failures, findings; not files read or raw output. |
| **status** | Edit `status:` in `STATE.md` front matter (`open → active → review → closed`, or `blocked`), log the change, re-run `index`. |
| **handoff** | Use the `handoff` skill. |
| **close** | Verify the acceptance criteria with evidence (`reports/`, `evidence/`). Log a closing line (what shipped, where), refresh your `handoff/<role>.md` to a final summary, then `bash tools/work/work close <co>/tickets/<ID>` (sets `status: closed` + `closed:`, moves the dir to `tickets/_archive/<ID>`, rebinds sessions; `reopen` moves it back), run `index`. Heavy-tier businesses: also the ticket-system comment and reports per `docs/process/heavy-track.md`. |
| **rename** | `bash tools/work/work rename <target> <new ID or target>` (e.g. an unrouted `user/work/s-<sid8>` once its subject is known): moves the dir and rebinds its sessions. |
| **index** | `bash tools/work/index <co>` regenerates `business/<co>/tickets/INDEX.md`. Never edit it by hand. |

Never answer "did I do X on this ticket?" from memory: check `LOG.md`, git, or the conversation.
