# Evidence Before Conclusions, and the Ask-Gate

Two halves of one discipline: **research before you ask; evidence before you assert.** Read this before
stating a conclusion to anyone, and before any question leaves the session.

## 1. Evidence before conclusions

Before stating anything as fact (to the user, a teammate, a report) you need **strong evidence**.
Reading code or docs is a lead, not proof. Verify it: run it, curl it, check the dashboard, query the data.

**Calibrate the wording to the evidence:**

| Evidence | Wording |
|---|---|
| Verified (ran it, saw the output) | state it plainly, cite the proof |
| Strong but unverified (several consistent sources) | "likely, but unverified" |
| Weak, single-source, pure inference | `⚠️ GUESS: needs verification` + what would confirm it and how |

Never let a guess wear the costume of a fact.

**Pre-send self-check (the one that matters).** Right before asserting a conclusion ask: *what did I
actually execute or observe for this?* If the honest answer is "I read the code / a config / a doc", it
is not verified: run it now, or tag it `⚠️ unverified: based on code reading`. A code read tells you
what the code *says*, never the runtime behaviour. When a code owner pushes back twice, stop asserting
and go get an executed proof.

**Match the evidence type to the claim type.** Data claim → a query. Runtime claim → a run.
Organisational claim ("there's no ticket for this", "nobody owns that") → a ticket-system query and a
read of the ticket body, not a code read. Evidence strength earned in one domain never underwrites a
claim in another.

**A written record outranks chat.** A decision record, ticket comment or report is the state; chat is
a notification about it. Before asserting what someone decided, grep the record and quote the
sha/section you read.

**Corroboration needs a different method**, not a second run of the same one. Two sessions using one
tool is n=1.

**Negative claims need a wider search than positive ones.** A positive needs one hit; "there is no X"
needs every place X could live: the writer side (setters, constructors, callers), sibling modules,
legacy repos, the artifact itself.
- A search meant to prove absence is never truncated (`head`, `tail`, `-m`). Use `grep -c`, `grep -l`
  over the whole tree, or print every hit.
- Before trusting a check's silence, prove it can fire: run it once on a case you know should match.
  A check can return empty for boring reasons (truncation, wrong path, unexpanded glob).
- If the search was not exhaustive, say "I didn't find X in <where I looked>", never "X doesn't exist".
- **Never report a source as exhausted without naming the endpoint you queried.** "Checked the wiki,
  nothing there" is false if you hit one instance, one space, or a stale URL. Ask: does this source have
  a second instance, domain or namespace? Companies mid-migration run legacy and new instances side by
  side; a 401/404 on one endpoint says nothing about whether the document exists.

Before quoting any count or measured number, read [verification-antipatterns.md](verification-antipatterns.md).
Verify once, properly, not repeatedly: see [verification-before-done.md](verification-before-done.md).

## 2. The Ask-Gate

Applies to every question to anyone: the user, a teammate, any channel. "Just a quick question to the
user" is not exempt. Post this checklist inline, with concrete evidence per line, before asking.
No checklist, no question.

```
Ask-Gate
1. Code / config?                    → file:line checked, and what it said
2. Ticket / wiki / chat history?     → what I searched (instance/space + query), conclusion
3. git log / blame?                  → conclusion
4. Can I run/verify it myself?       → the command I ran + what I observed
→ Ask only if all four were checked and the answer is genuinely in none of them.
```

Anything answerable by a `grep`, a one-line query, opening a config or a curl is not a question; it is
a check you skipped. When unsure whether something is externally owned, assume it is self-serviceable
and prove otherwise via the gate.

**Sources to check by default:** code and config · the ticket (description, AC, comments, links) ·
wiki · chat history · git history · existing docs (`CLAUDE.md` files, `docs/`, the business and project
docs, ticket dirs, `lessons/`, `user/logs/`) · trying it yourself. For deployments, infra, secrets or
account state also: the deploy tool / cloud console, the secret store, the account admin tool.

**Legitimate questions** are true externals only: access you cannot grant yourself, product intent with
no precedent, sign-off and priority calls. How to phrase them: [communication.md](communication.md#how-to-ask).

## 3. "Gather context": the full sweep

When the user says "gather context" (or a ticket number arrives, see
[ticket-lifecycle.md](../process/ticket-lifecycle.md)), sweep **all** sources, not one or two:

1. Ticket system: the ticket(s), AC, all comments, links, subtasks, parent epic, surrounding tickets.
2. Code: relevant source, tests, repo `CLAUDE.md`/README, `git log --grep`, `git blame`.
3. Local docs, index-first: `business/<co>/tickets/INDEX.md`, the project `DEVDOC.md`, business and
   framework lessons, recent `user/logs/`.
4. Wiki: the team's own space first, then widen; name the instance and query.
5. Chat: the ticket key and its key nouns; decisions are often made in chat and never written back.
6. Live front-ends when relevant (deploy tool, secret store, dashboards).
7. The real data when the topic is what the data contains ([data-verification.md](../process/data-verification.md)).

Fan out one subagent per source in a single message; keep the synthesis in the main loop. Report per
source, flag conflicts between sources, mark anything unverified. Skipping a source is allowed only when
it is genuinely irrelevant, and you **say which and why**.
