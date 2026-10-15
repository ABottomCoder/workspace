# Answering With Real Data

> Read this **before** concluding that a question needs production access, and before answering any question about what the data actually contains: rates, incidence, "does this column exist / is it populated", "how often does X happen in production".
>
> The single rule: **if a question is about what the data contains, measure it. Do not reason about it from the SQL, the schema, or the code that writes it.**
>
> SQL is ANSI where possible. Dialect-specific lines are labelled (`-- [postgres]`, `-- [snowflake]`, `-- [mysql]`); translate to your engine, the method is what carries. Per-business facts (what you can read, compute, table sizes, recipes, measured values) go in `business/<co>/docs/data-access.md`, never here.

## Why this exists

A team can spend weeks reasoning about production behaviour from the code that produces it, while the answer is one bounded query away. The recurring shape of the mistake is:

1. A question arises about incidence, coverage, or shape ("how often is this field empty?").
2. Someone answers it by reading the query or the writer code.
3. The answer is confidently wrong, because code says what it *attempts*, never what the data *is*.

The corollary failure is procedural: treating "I'd need access" as a conclusion rather than a step. Check whether you already have access before assuming you don't — access is often present through an indirect path (a share, an inbound grant, an existing console login, a read replica) and invisible to the obvious check. In one epic, four questions had been recorded as "unanswerable without production access"; all four turned out to be two queries in a browser, from an account the engineer already had.

## Access — establish it once, then write it down

Do this once per company and record the result in `business/<co>/docs/data-access.md`, so no future session re-derives it:

- **What can I already read, from the account I already have?** Enumerate it explicitly. Indirect grants (data shares, inbound cross-account access, catalog mounts) frequently don't show up in the listing you'd naturally run — a filter that looks right can hide the very objects you're looking for. Query the metadata catalog broadly before concluding something isn't there.
- **Running the tool is not the same as reading the data.** A tool's config often points at a dedicated production account with its own credentials, which is why everyone assumes production access is required. That account is required to run *the tool*. It is frequently not required to query *the data* the tool reads. Record the mapping from the tool's object names to the names you can actually read (often only the database/catalog prefix changes; the schema and table names stay the same).
- **What identity does each console use?** Record which SSO/MFA path each data tool uses. Multiple identity providers in one company is normal and is the usual cause of "I have no access".
- **Which compute do I run on, and what does it cost?** Record the available warehouses/clusters, their sizes, and which one is the designated ad-hoc target for your role.
- **How big are the tables I'll touch?** Record row counts for the big ones. A `GROUP BY` over a multi-billion-row table is not a casual query, and knowing that before writing it is the difference between a 10-second answer and a stalled session.

### The name-filter trap

The single most common way to "prove" you have no access when you do: a prefix filter on the listing. Shared or mounted databases are usually renamed on the consumer side with a prefix or suffix (`<SHARE_PREFIX>_<ORIGINAL>`), so a listing such as `SHOW DATABASES LIKE 'ORIGINAL%'` (`-- [snowflake]`/`[mysql]`; `information_schema` elsewhere) returns **zero rows** while `LIKE '%ORIGINAL%'` returns everything. A zero-row metadata listing is evidence about your filter, not about your access. Always run the unanchored pattern before concluding something is absent, and record the real names in the business data-access file.

## Standing authorization and its limit

Agree this with the user once, then hold to it. The default worth proposing:

**Read-only queries that cannot affect production and would produce information we need — just run them. Do not ask.** Ask only when a query would consume substantial compute or run a long time.

So: **size it, guard it, run it, report it.** Do not open a turn with "shall I query this?" — that is exactly the friction the authorization exists to remove. Two specific corollaries, both learned by getting them wrong repeatedly:

- **Never surface a query as a suggestion.** If you have designed it well enough to describe, you have designed it well enough to run. Describing a measurement you could have taken, in the same turn you could have taken it, is the failure. Run it, then report the number.
- **A dead session is not a blocker, it is a step.** Try the console first. If a human login really is required, ask for it in one line *while already doing everything that doesn't depend on it* — never as a reason to stop and wait, and never as a closing note on an answer.

Anything that **writes**, deletes, alters an object, or is outward-facing is unchanged: it still stops with the user.

## Before you run anything

```sql
-- always: a runaway guard, in whatever form your engine offers
SET statement_timeout = '300s';                         -- [postgres]
ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 300;   -- [snowflake]
SET SESSION MAX_EXECUTION_TIME = 300000;                -- [mysql] (ms, SELECT only)
-- always: pick the ad-hoc compute for your role explicitly, don't inherit a default
USE WAREHOUSE <adhoc_warehouse>;                        -- [snowflake]; other engines: the designated replica / cluster
```

**Choosing compute.** Use the warehouse/cluster that is purpose-built for ad-hoc work by your role. Not the biggest one you can see (cost), not one named for another tool such as a catalog crawler (even if it is the cheapest — it is someone else's budget and queue), and not a `*_SERVICE` one (those back production jobs). Record the choice and the alternatives in the business data-access file.

Then size the query before writing the real one: a count, a metadata check, or a bounded probe, so you know whether you're in the "just run it" category or the "ask about cost" category.

- **Metadata commands are usually free.** Many engines answer `SHOW ...` / `INFORMATION_SCHEMA` lookups without starting compute, so schema exploration costs nothing. Use that before anything else.
- **Know your engine's sampling limits.** Row-count sampling is often capped (e.g. at a million rows), and asking for more silently returns the cap. Record the cap in the business data-access file.

## PII discipline — non-negotiable

- **Return counts, not values.** `COUNT(DISTINCT ...)`, `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`. A result set of names, emails or birthdates is itself a PII extract, and it lands in a transcript.
- **Assume local transcripts are permanent.** Anything echoed into a tool result is kept. Keep identifiers out of it — aggregate in the query, not afterwards. When identifiers must move between tools, move them in a way that never prints them (see the in-page and clipboard techniques below).
- **Store any downloaded PII in a locked scratch dir outside the workspace** (`chmod 700`, e.g. `~/tmp-<ticket>-pii/`), and delete it when done. Never inside the workspace: ticket dirs are kept forever and reports are forwarded.
- **Reference/lookup tables are not PII.** Read them freely; know which ones they are.
- **Don't persist real identifiers between sessions.** If a measurement needs real request/user IDs, re-extract them from the source of truth each time. Re-extraction is part of the job, not a blocker.

## Driving a web console from a browser-automation MCP

**Prefer a programmatic connector over the DOM.** Most warehouses ship a client library that can authenticate through the same browser SSO the console uses (an "external browser" authenticator), so you need no keypair, no credentials file, and usually no interaction if the SSO session is already live. Console UIs get redesigned without notice — in one case a new UI put an AI chat box behind the very selector the SQL editor used to own, so the automation typed queries into the chat prompt. A connector call does not break that way. Keep a small runner script in the ticket's `evidence/` and record the connection parameters (account, role, compute; never secrets) in the business data-access file.

When the console really is the only route, automate it:

- **The human logs in.** Never type credentials yourself.
- **Use the right entry URL.** A vendor's generic landing page often drops you on an "enter your account" form; the account-specific path is what triggers SSO. Record the one that works.
- Identify the editor component and whether it lives in an **iframe** — most cloud SQL editors do, and this is the usual reason a naive "type into the page" fails silently.
- Prefer setting the query text programmatically (e.g. `execCommand('insertText', ...)` into the focused editor) over synthetic keystrokes or setting `.value`; keystroke automation into a code editor mangles indentation and autocompletes brackets, and `.value` is ignored by most editor components.
- **Work in a new file/worksheet**, never whichever one is open — the user's own queries live there.
- **End the SQL with `;` and a newline.** If the text ends on a bare identifier, the autocomplete popup can open and swallow the "Run" click: the query silently never runs and the results pane keeps showing the *previous* result, complete with a fresh-looking timestamp. Send `Escape` before clicking Run, and **always confirm the returned column names match the query you just submitted** rather than trusting the grid.
- Editors inject hint text into their DOM (keyboard-shortcut tips and the like). It is not part of the query, but it breaks naive "does the text end with `;`" assertions.
- Read results out of the DOM (grid rows/cells by ARIA role) or via a copy-to-clipboard action rather than screenshotting numbers you'll then re-type. A number transcribed by eye is an untrusted number.
- **Long queries outlive the tool-call timeout.** The automation call may block past its limit and get backgrounded. Wait for completion or cancel explicitly; don't fire a second query on top.
- **If the browser MCP can't attach** because a browser is already running on its profile, talk to that browser's remote-debugging port directly. Gotcha: a reused evaluation context keeps top-level `const` bindings, so the second call throws "already declared" — wrap each snippet in an IIFE.
- Record the working selector recipe in the business data-access file the first time you get it working. It will change, but a stale recipe is still a faster start than nothing.

## Query gotchas that cost re-runs

These are engine-flavoured but the shape recurs everywhere. Record your engine's versions in the business data-access file.

- **A `WHERE` on a sampled table may be pushed into the sample.** `FROM t SAMPLE (N ROWS) WHERE k = 1` (`-- [snowflake]`; `TABLESAMPLE` elsewhere) can return N rows that *all* match, not N rows of which some match. To learn a share, sample unfiltered and compute it.
- **A conditional count is a count, not a rate.** `100.0 * SUM(CASE WHEN p THEN 1 ELSE 0 END)` (or `COUNT_IF(p)` `-- [snowflake]`, `COUNT(*) FILTER (WHERE p)` `-- [postgres]`) without `/ COUNT(*)` yields numbers in the millions. **A percentage above 100 is this bug**, not a surprising finding.
- **Reserved words as aliases** (`rows`, `count`, `date`, …) are compile errors in some engines. Pick unambiguous aliases.
- **Seeding from a bridge/cross-reference table biases the population.** A mapping table usually covers most but not all of the entity table, and the part it misses is not random (typically the newest records, not yet mapped). Seeding a "how many customers…" question from the bridge skewed one figure by several points across four earlier measurements. Seed from the table whose population the question is about.
- **Read the data dictionary before inferring from a column name.** Column comments in the metadata catalog often carry real descriptions. In one case they settled an argument outright: the timestamp a production filter relied on was documented as *ETL metadata — when the platform last wrote the row*, and a separate documented column held the source system's own update time. One metadata query, skipped for a whole session's worth of inference. The dictionary tells you what a column *claims* to be; you still measure what it *contains*.
- **Check a column's value distribution before using it in a comparison.** Fill rate is not usability. A birthdate column was mostly populated, which looked usable; the majority of the populated values were a single placeholder date. Before using a column in an equality or range test, run `GROUP BY col ORDER BY COUNT(*) DESC LIMIT 10`.
- **Look at what the source has that the consumer ignores.** The production query selects a few columns; the source table often has a flag, a type key or an effective-dating column that answers the question directly ("which email is the primary one?" became a data question once a type key decoded to `PRIMARY`). List the unused columns with their fill rate and value distribution before designing a fix — and report sparse ones as sparse, not as available.

## Use the population the question is about

**The intake is the population.** If the question is about requests (or filers, or orders, or incidents), the only correctly-populated source is the actual intake those requests arrive in — the files, queue or table the tool really consumes. Random records from the entity table are a different population, and on the variable being measured they can differ in the opposite direction from what you'd guess.

- **Beware the similar-looking table.** A large, queryable table with the right-sounding columns (`REQUEST_TYPE`, `ACCOUNT_ID`) may belong to a sibling pipeline serving a different population, or hold a different request type. Confirm which pipeline writes it before using it.
- **Batch sizes vary wildly.** Observed intake files ranged from one record to dozens. Never generalise from one file.
- **Validate an extraction by its match rate.** If you pull identifiers out of intake files by pattern and join them to a very large table, a high match rate *is* the proof the extraction caught real identifiers — junk essentially never matches a billion-row table. A low match rate means the extraction is wrong, not the data.

### Reading files in place without downloading them

Browser automation frequently cannot download files (bulk downloads suppressed, download endpoints aborted). Do not fight it. Do the work inside the page that already has the authenticated session, which also keeps identifiers out of the transcript:

1. **Enumerate** via the document store's REST API from the page (`fetch` with the session's cookies) — the listing returns filenames, not contents.
2. **Fetch the bytes** of each file into an `ArrayBuffer`.
3. **Decode in the page.** Many office formats are ZIP containers of XML; read the central directory and inflate the entry you need with `DecompressionStream('deflate-raw')`.
4. **Extract by shape.** If the identifier you need has a distinctive shape (e.g. GUID-shaped) and no other column shares it, a regex over the string table needs no column parsing at all.
5. **Build the query input in the page** and hand it to the console without printing it.

**Cross-origin handoff.** The document store and the data console are usually different origins, so no shared JS state or `localStorage`. Use the clipboard: write it in one tab, read it in the other, insert into the editor. Clipboard permission must be granted **once by the human** for each origin — without it the read hangs on an invisible prompt and `execCommand('paste')` returns `false`. Bring the tab to the front first; clipboard writes need focus.

## Measured reference values — do not re-derive these

Keep a table in `business/<co>/docs/data-access.md` of values you've measured, each with the date, the exact population, the confidence interval, and the query that produced it. It is the highest-value part of that file over time: it stops three sessions measuring the same rate three different ways and getting three different answers.

Shape of the table (lives in the business file):

| Value | Measured | 95% CI | Date | Population / caveat |
|-------|----------|--------|------|---------------------|
| | | | | |

Rules for the table:

- **A value without its population is not a value.** Write "27% of requests in the last 12 months, excluding X" — never "27%".
- **Give an interval for any rate from a sample** (a binomial score interval is the safe default for proportions; the naive normal interval misbehaves near 0% and 100%), and record how many independent runs agreed and by how much.
- **Two unrelated sampling frames agreeing is what makes a number quotable.** One frame repeated is still one frame.
- **State bounds as bounds.** If the proxy can over-count (a differing surname may be a married name, a differing birthdate a typo), the figure is an upper bound — say so in the row.
- **When a value is withdrawn, keep the row** and mark it withdrawn with the reason. A silently deleted number gets re-quoted from chat.

## Ways to get a wrong answer, all of which happened

1. **Stopping at "the column exists."** A field existed and was reported as available; it was populated on 7% of rows. Reporting existence without coverage sends a product owner down a wrong path. **Always check fill rate and value distribution, not just the schema.**
2. **Running a number once.** An average returned 66.7, 11.4 and 9.9 across three identical runs — heavy-tailed, and the sampling method couldn't estimate it at all. It was one keystroke from being published as a fact. **Re-run anything you intend to state**; if the sample re-randomizes, repetition is free evidence.
3. **Sampling the convenient population.** A rate measured over "random records" was quoted as an answer about *requests*, and produced a directional claim the real request population **inverted** — because the two populations differ on exactly the variable being measured. **Name your population before you quote a rate.**
4. **`LIMIT` inside `SAMPLE` is not a random sub-sample.** It takes whichever rows arrive first, which correlates with physical storage layout. Fine for "give me some seeds", wrong for any distribution statistic.
5. **A sentinel value read as data.** A headline figure about how often linked records belong to a provably different person was built on birthdate differences — and most birthdates were a placeholder date, so the "difference" was placeholder vs real. **The tell was a bimodal result:** the ≥20-year and ≥40-year thresholds gave nearly identical shares. Organic distributions don't do that. **If two nested thresholds give the same answer, suspect a sentinel.** The figure was withdrawn and re-measured.
6. **Comparing one value to one value on a multi-valued relationship.** "Do linked records share an address?" was first measured by taking *one* arbitrary partner and *one* most-recent address each, and came out about half the true rate; the resulting claim ("the linkage is not address-based") was wrong. Re-measured as "any address of A matches any address of B, across up to N partners", it roughly doubled. **Never compare one-to-one when both sides are multi-valued**, and distrust any single-partner comparison on a fan-out relationship.
7. **Reading a row-write timestamp as activity.** A recency filter on "last updated" looked like a retention policy. Over half the rows shared one month — a bulk load — and nothing predated it, so the filter selected "rows the platform happened to rewrite recently". Two consequences worth reusing: a "100% at five years" figure really meant "100% at the column's entire history", which was much shorter than five years, and **a recency filter suits events, not identity attributes** — a birthdate was not "collected last year". Check the timestamp's histogram before interpreting any filter on it.

See [verification-antipatterns.md](../principles/verification-antipatterns.md) for the full set — these are the data-specific subset of a larger pattern.

## Validate your test fixtures against production

Once the data is queryable, this becomes cheap and should be routine: **do the fixtures encode shapes production actually produces?**

A synthetic fixture that encodes a row shape the real pipeline cannot emit will make a broken code path look correct through a hundred passing tests. One such fixture (it populated every field, so a sparse-data defect was invisible) cost an entire epic a re-verification round. Checking it against production confirmed five of the code's claims and turned up two things the docs had wrong.

## Reproducible scripts

Keep measurement SQL in `tickets/<ID>/evidence/<what>.sql`, with each part's results and caveats inline as comments, and **deliberately without any identifier lists**. A script that reproduces the number is worth more than the number.
