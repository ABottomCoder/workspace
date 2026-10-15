# Session rollover — handoff rules

A session whose transcript passes **50 MB** (`CLAUDE_ROLLOVER_MB`) hands its work to a fresh
session and closes itself. The Stop hook `tools/rollover/check.sh` (in `.claude/settings.json`)
checks after every reply and fires once per session.

## When the hook fires (old session)

Do it right away, without asking the user:

1. **Update the durable records first**: the bound work item (`LOG.md` via `tools/work/log`, or the
   project `DEVDOC.md` change log), lessons, memory pointers. The handoff points at them instead of
   copying them.
2. **Write the handoff where the hook says** — into the bound work item:
   - ticket / `user/work/<slug>`: `tools/work/handoff` (archives the old one), then fill `HANDOFF.md`;
   - project: update `DEVDOC.md` (state, active work, TODO) and its `## Session handoff` section;
   - not attached: `user/sessions/.rollover/<session-id>.handoff.md`.

   Short, but enough for a session with no other context:
   - Role first, if the session has one (e.g. "You run app `slack_example`; take it over per `apps/RULES.md`").
   - What the work is, where it stands, the exact next step.
   - Open commitments: who is waiting for a reply, what was promised, running background jobs/listeners.
   - Key files, decisions and why, what is verified vs. not.
   - The user's in-flight instructions that are not written down anywhere else.
3. **Run** `bash tools/rollover/handoff.sh <session-id> <transcript_path> [name]` (the hook message
   has the exact command). Pass `name` only when the session is unnamed and not attached.
4. If it prints `FAIL`, tell the user why and keep this session as is.

## Naming the new session

Convention `<ShortDesc>_<app>_<n>`: ShortDesc = project or ticket (no underscores), app = app name
or `None`. `handoff.sh` sets the new name with `claude -n`:
- `<Desc>_<app>_<n>` → `<n+1>`, padding kept (`ABC-18_None_1` → `ABC-18_None_2`, `web_slack_example_09` → `_10`).
- Named without a trailing number (legacy) → append `_2`.
- Unnamed → the name passed as the 3rd argument, else `<bound item>_None_2`.

## When you are the new session

Your first prompt names the handoff file. The binding was copied before you started, so the
SessionStart hook has already restored the work item. Read the handoff, follow its role line (e.g.
take the app over per `apps/RULES.md`), confirm with `tools/work/show`, then carry on with the next
step. Tell the user in one line that you took over from the previous session.

## Mechanics

- The new session starts in the main dir with a pre-generated `--session-id`; the binding file is
  copied to that id first (with a `from=<old id>` line).
- New window: `launch.sh` picks `launch.<variant>.sh` by `$WORKSPACE_TERMINAL`, else by
  `$TERM_PROGRAM` (iTerm → `mac-iterm`, Terminal.app → `mac-terminal`), and fails clearly otherwise.
  Variants are listed in `docs/compatibility.md`.
- The old session is SIGTERMed 5 s after the new session's transcript appears; not before.
- Skipped: headless sessions (no tty). Opt out: `CLAUDE_ROLLOVER_DISABLE=1`.
- State and log: `user/sessions/.rollover/` (`rollover.log`). Test without exiting:
  `CLAUDE_ROLLOVER_DRYRUN=1`; skip the tty check: `CLAUDE_ROLLOVER_INTERACTIVE=1`.
- Claude Code specifics (transcript naming, custom-title record, CLI flags) live in
  `tools/lib/cc-internals.sh`; fix them there after an upgrade breaks them.
- bash 3.2's `printf %q` mangles UTF-8; the scripts single-quote instead.
