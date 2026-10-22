---
name: attach
description: Route a request to its business and work item and bind this session to it, so compaction, resume and rollover restore the right context. Use at the start of real work, or when the user says "attach to X", "work on <project>", "this is ticket <ID>", "switch to <ticket>", or the equivalent in any language.
argument-hint: "<business>/<project> | <business>/tickets/<ID> | user/work/<slug>"
---

# attach

1. **Route.** Identify the business and the project or ticket from the request (`business/*/CLAUDE.md`
   index lines, ticket IDs, repo names). Ask only if genuinely ambiguous.
2. **Read** `business/<co>/CLAUDE.md`, then the project `CLAUDE.md` + its state file, or the ticket
   `STATE.md` + your role's `handoff/<role>.md` (the `HANDOFF.md` index lists the roles) + tail of `LOG.md`.
3. **Bind:** `bash tools/work/attach <target>`
   - project: `<co>/<project>` (creates the state file per the business policy if none exists: `tools/work/README.md` → Project state policy)
   - ticket: `<co>/tickets/<ID>`; if it does not exist yet, use the `ticket` skill to create it first.
     A second line of work on the same ticket (QA beside the developer, an app) adds `--role <name>`
     (`dev`, `qa`, …; default `main`); each role owns `handoff/<role>.md` and edits only that file.
   - a series of sessions on one theme (e.g. "fix bugs in the web app as they come"): a ticket named after it (`<co>/tickets/web-fix`)
     whose handoff points at the tickets it touches; rollover passes it from session to session
   - cross-business: `user/work/<slug>` (create with `tools/work/new-ticket user <slug> "title"`)
4. **Name the session** `<ShortDesc>_<app>_<n>` (ShortDesc = project or ticket, no underscores;
   app = app name or `None`; n starts at 1). The script prints the suggestion; ask the user to run
   `/rename <name>` (rollover bumps `<n>` itself).
5. Confirm in one line: what is bound, and the next step from the work item.

Re-attach whenever the work moves to another item; one session is bound to one item at a time.
`bash tools/work/show` tells what this session is bound to. Formats: `tools/work/README.md`.
