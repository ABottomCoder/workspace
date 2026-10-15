# Claude Code Setup Methodology

The *method* behind this framework, distilled from about six months of daily use in one workspace
(a 32 KB main prompt, ~80 KB of docs, ~140 lessons, 20 repo-level CLAUDE.md files, ~100 memory files)
and from a second, independently grown workflow engine. Every rule here was written after a failure.
Read it when setting up or auditing a Claude Code workspace, or porting this framework.

## 0. If you are an agent handed this file

Don't summarise it. Instead:
1. **Inventory your own setup:** the project `CLAUDE.md` (or its absence), `~/.claude/settings.json`,
   any lessons/memory mechanism, any `docs/` layering. One sentence on the current state.
2. **Compare section by section (§1–§7):** do I have this? If yes, where is mine weak (rule without a
   trigger, without a counter-example, without a self-check)? If no, is it worth adding, and why or why not?
3. **Produce a diff, not praise:** at most 5 concrete edits ("in CLAUDE.md section X, add/replace these
   sentences"), ranked by return on effort, favouring ones that change behaviour.
4. **Don't copy rule text wholesale.** Rules are bought with specific incidents; copy the *mechanisms*
   (the correction loop, the routing table), and let the rules grow from your own failures.
5. Ask the user which changes they actually want; don't edit their `CLAUDE.md` yourself.

## 1. Layered prompts, loaded on demand

Most setups have one `CLAUDE.md` that grows to 2,000 lines nobody (model included) really reads. Split
by when content is needed:

| Layer | Loaded | Here |
|---|---|---|
| 1. Always-on | every session | main `CLAUDE.md` (index + core rules + routing, < 200 lines); `MEMORY.md` index |
| 2. On demand | when the topic comes up | `docs/**` (principles, process, reference, playbooks); `business/<co>/CLAUDE.md`; project and repo `CLAUDE.md` |
| 3. State and history | when the agent goes looking | ticket dirs, project `DEVDOC.md`, `lessons/`, `user/logs/` |

Always-on context has a cost: every token competes with the task. The test:

> **Would an unrelated task waste context on this paragraph? Yes → it doesn't belong in layer 1.**

A pointer to layer 2 says **what is inside and when to read it**, in one line, so the model can decide
whether the read is worth it. Never restate the content next to the pointer.

## 2. Shape of an upper-level CLAUDE.md

Order matters: the earlier, the more likely it is actually read.
- **Ownership statement first:** "You own this document; it is a seed; discover what you can, ask only
  what you can't, enrich it with every task." This turns the file from a manual into an asset the model
  maintains, which is what makes self-evolution work.
- **Quickstart:** what is active right now, what to read in which order, with **dated pivots** ("since
  <date> X is paused; the earlier stance is void"). Without the pivot, a new session works in the
  direction of three months ago.
- **A written conflict rule:** "if this file and X disagree, X wins". Documents will drift; decide who wins.
- **Traceability on every auto-written entry:** `<!-- auto: discovered -->`, `<!-- auto: user -->`,
  `<!-- auto: <ticket-id> -->`, `<!-- auto: user-corrected <date> -->`.
- **Mark stale content instead of deleting it** ("⚠️ domain A is live, B is retired; some older docs
  still say B"), because the model will read those older docs too.
- Index rows stay short (≤ 2 lines: what it is + where the detail is).

## 3. The routing table

The routing table (main `CLAUDE.md`) is what keeps knowledge from silting up in the top file. Before
writing anything persistent, ask: **who needs to read this, in what situation?** Hard rules:
1. Auto-memory never holds business or project knowledge, not even a pointer line; the index row in the
   right `CLAUDE.md` is already the discovery hook.
2. Index tables: ≤ 2 lines per row; details move down a level.
3. **One fact, one home.** Other places hold pointers. Writing the same fact twice means the routing is wrong.
4. After writing, self-check: would a session on an unrelated business or project pay context for this?
   Yes → move it down.

The table itself was born from a correction: one session misfiled knowledge twice in one day (first into
memory, then into the top-level file).

## 4. Self-evolution

**Update rules.** After every ticket, and whenever an important conclusion about a codebase is reached,
record it in the right place immediately. The model may freely **add**; **changing an existing rule goes
through the human**, and a workflow step that doesn't match reality is **reported**, not silently
rewritten. That boundary keeps self-evolution from turning into self-drift. Never delete content unless
asked.

**The correction loop.** After any user correction, add or strengthen a lesson (Mistake / Root cause /
Rule / Source); scan the relevant lessons at session start; never duplicate, strengthen instead. Where
lessons live: `lessons/` (generic), `business/<co>/lessons.md`, `user/lessons.md` (taste).

**What six months taught about writing lessons:**
- **Replace the command, don't add a caveat.** "Remember the bundler doesn't type-check" failed twice in
  one day; "before pushing run the type-check command CI runs; never use the build as the gate" worked.
  If a lesson is about a misleading success signal, the fix must replace that command.
- **Merge recurrences instead of stacking them.** Of ~140 lessons about 60 were independent; the rest
  were second and third occurrences. Strengthen the original and count recurrences; the count is a signal.
- **Record the positive example next to the negative** ("this time the broken state was measured first,
  so the inference held; that time it wasn't, so three rounds of reasoning sat on an uncalibrated ruler").
- **Write down how the rule could be abused in reverse** ("ask a colleague before re-escalating" must not
  decay into "assume the colleague handled it").
- **Root cause names the cognitive failure, not the tool detail.** "Tool X behaves like Y" doesn't
  transfer; "I used a criterion that could not have detected the bug" does.

Three examples of the shape (generalised):
- *Truncated search proved a negative.* A `grep … | head` was labelled "(empty = never deleted)"; the
  real match was pushed past the cut-off. Rule: absence-proving searches are never truncated, and a check
  that can be empty for boring reasons is first run on a known positive.
- *Keyword scan certified a file as secret-free.* Searching for `PASSWORD|TOKEN` returned 0 on a file
  with a password inside a connection URL. Rule: read the whole file and look for secret *shapes*
  (`scheme://user:pass@`, `--password` args, high-entropy strings, key blocks); a file too long to read
  is too long to certify.
- *Reversible was taken as authorised.* An unrequested `git init` in the user's top-level directory.
  Rule: creating or removing infrastructure in someone's environment is the owner's call.

## 5. Memory conventions

One fact per file plus an always-loaded index (`MEMORY.md`); here it lives in `user/memory/` via
`autoMemoryDirectory`.
- Types: `user` (who the user is), `feedback` (how they want work done, with **Why** and **How to
  apply**), `project`, `reference`. In this framework `project`/`reference` facts about a business
  belong in `business/<co>/`, not memory.
- Frontmatter: `name` (kebab slug), `description` (one line used for recall), `type`; link related
  entries with `[[name]]`.
- ⚠️ **The index has a hard size limit (~25 KB / 200 lines); past it, the whole index silently stops
  loading.** Put the warning on the index's first line and `wc -c` after each addition. When tight,
  compress superseded rows first.
- An index row states the **current state**, not "what this file is about". Authority-type entries say
  which earlier entry they supersede; keep superseded ones in a lineage section (latest wins).
- Memory is true *when written*. Before recommending something a memory names (a file, flag, switch),
  verify it still exists. Update existing entries instead of adding duplicates; delete wrong ones.
- Don't store what the repo already records (code structure, past fixes, git history, CLAUDE.md content).

## 6. Settings, hooks, skills

- **"Every time X, do Y" is a hook, not a prompt rule.** `CLAUDE.md` and memory are advice the model can
  miss; hooks are executed by the harness. End hook commands with `; true` (or handle failures) so a
  broken hook never blocks the session. Use `$CLAUDE_PROJECT_DIR` for paths. `/update-config` writes them.
- Permission allowlists don't need hand-writing: `/fewer-permission-prompts` mines history for frequent
  read-only commands.
- **Skills trigger from their own `description`**; a vague description means the skill never fires.
  Every installed skill's description sits in context, so unused skills cost tokens; check before
  installing (`claude plugin details <plugin>`). Many "install a plugin" needs are built in (review,
  security review, simplify, loop, schedule, update-config, dataviz).
- Project skills (`.claude/skills/<name>/SKILL.md`) load with the workspace; prefer them over loose
  command files for workflows that must be found.
- Bind conventions to concrete triggers: "touched auth/billing/secrets → run a static security scan and
  triage before shipping", not "be careful with security".

## 7. The invisible skeleton (lives outside the workspace; a folder copy misses it)

1. **`~/.claude/settings.json`**: model routing and provider auth (`env` block: provider switch, model
  ids per tier, auth/profile/region), `cleanupPeriodDays` (keep local transcripts; this framework
  requires a very large value), permission defaults. Most likely piece to be lost on a new machine.
2. **Company MCP servers** registered at user scope (`~/.claude.json`) or by an external manager, not in
  the repo's `.mcp.json`. Re-create them per business and record them in `business/<co>/stack.md`.
3. **`.claude/settings.local.json`**: machine-specific permissions and absolute paths
  (`autoMemoryDirectory`); generated by the installer, never committed.
4. **Onboarding installers** (auth portals, VPN, cloud roles) are company-specific; keep their shape,
  rewrite their values in `business/<co>/`.

**Never carry between companies:** secrets or secret pointers; people data (rosters, contact ids,
conversation ids); infra data (hosts, accounts, internal API docs); accumulated ticket data (reports,
logs, intervention rows, digests); project memories. Rule of thumb: behavioural rules and workflow logic
carry; anything naming a real person, host, ticket, secret or accumulated number does not. This
framework enforces that split structurally (`user/` and `business/` are gitignored; the pre-commit
guard blocks denylisted names).

**Verify a port objectively:** grep the framework for the old company's names, ticket prefixes, tool
names and people (expect zero); run the session scanner and the harness on a throwaway repo.

## 8. Self-audit checklist

Ordered by how much each item changes behaviour.

**Structure:** quickstart first, with dated pivots? written conflict rule? big blocks pushed to layer 2
with what+when pointers? traceability markers?
**Rule quality:** criteria ("can I roll back in seconds?") instead of adjectives ("be careful")? an
explicit "when to skip the process"? a never-lazy list kept separate from "save where you can"? rules
that replace commands rather than add caveats?
**Loop:** a lessons mechanism that is *read* at session start? root causes as cognitive failures? a
"strengthen, don't duplicate" rule? a routing table? "model adds freely, humans approve rule changes"?
**Verification:** "done" defined as measured behaviour (not build/green/deployed)? baseline in the broken
state? negative claims need wider searches, and "didn't find" is worded differently from "doesn't exist"?
**Mechanism:** "every time X" implemented as hooks? installed plugins actually used? memory index under
its size limit (measured)?

Three most often ignored: context is a real budget (state in files, compact at checkpoints); self-evolution
needs a boundary (add freely, change only via the human); a rule is worth how much it changes a concrete
action, not how true it is.
