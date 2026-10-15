# Backups and Risk

Take a backup **only when a change carries irreversible risk**: you'd be afraid to roll it back. Don't
back up as a reflex on every change.

**Litmus test:** *if this breaks, can I get back to the previous state in seconds with `git` or a config
flip?* Yes → no backup. No (data or infra is mutated irreversibly) → backup first.

| Backup required (before executing) | No backup needed |
|---|---|
| Production deploys | Local edits |
| Database schema migrations | Doc changes, ticket/work-dir notes |
| Destructive ops: drop/delete/`rm`, data rewrites | Reversible code changes already in git (git history *is* the backup) |
| Auth or deploy-path changes | Small features or UI polish you can `git revert` |
| Secret rotation | |
| Shared infra you can't cleanly revert | |

## High-risk protocol (for the left column)

Before executing, in this order:

1. **Write it down** in the work item (`spec.md` safety block, see `templates/ticket/spec.md`): what
   changes, blast radius, who authorised it.
2. **Snapshot** the affected state (DB dump, file tree, config) and record path + timestamp.
3. **Write the recovery path**: the exact commands to revert (git range, restore command, dropped
   column), tested where cheap.
4. **Confirm authorisation** from the person with authority for this action
   ([communication.md](communication.md#authority-and-approval)). Delegated drive is not permission.
5. Execute, verify in layers, log the result in the work item's `LOG.md`.

Once the change is confirmed good and the owner signs off, the one-time backup may be removed;
until then it stays.

## Data you don't own

- Code and file changes are fine when git can roll them back. **Client or production data is not**:
  mock it locally, test against the mock, and only run the real change after testing and with explicit
  confirmation from the authority.
- Before any repo work: `git status`. Uncommitted changes, unstaged files or stash entries → report and
  wait. Never discard or stash someone's work without explicit approval.

## Reversible is not authorised

Reversibility describes blast radius, not permission. **Creating or removing infrastructure in someone
else's environment** (a repo, a git remote, a daemon, a cron job, a new top-level directory, a hook) is
the owner's decision even when it's trivially undoable and genuinely fixes something. Name the gap,
propose the fix, then wait. "It's reversible" and "it's obviously better" are not answers to "did anyone
ask for this?"

## Shared, unversioned locations

In any shared directory not under version control, treat every write as possibly destroying someone
else's work: `ls` before choosing a name; read the write tool's own result ("updated" means a file was
already there: stop and look at what you replaced). Put the distinguishing information in the filename.
Once you've sent someone a path, don't delete it on rename; leave a pointer at the old name.
