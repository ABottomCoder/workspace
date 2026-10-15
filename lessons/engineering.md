# Engineering gotchas

Concrete technical traps in code, data, builds, deploys and infrastructure, with the checks that catch them.

### Know the parser before writing text it will parse
**Mistake:** Text embedded in code or config broke the parser that reads it: markdown backticks inside a JS template-literal prompt closed the string early (twice), a bare top-level `return;` in generated ES-module code was a SyntaxError, and a `;` inside a SQL comment broke a schema string the app splits on `;` at boot. Each one crash-looped a production service.
**Root cause:** Wrote input for a parser without reading how it parses, and the checks before deploy used a different parse goal, a filtered error list, or a test path that was skipped.
**Rule:**
- Never put a backtick or `${` in template-literal prompt text; use double quotes. In top-level module code, exit with if/else fall-through or `throw`.
- Read the parser before you edit a string it splits or evaluates at runtime.
- Validate generated code with the real parse goal: write a sample to `.mjs` and `node --check` it. `vm.Script` passes code that a module would reject.
- Before shipping, read every `error TS` line, not a grep-filtered subset, and `node --check` each changed emitted file. When the real path is skipped in tests (for example, no DB DSN), add a cheap structural test that runs everywhere and confirm it fails on the broken version.
- After every restart, confirm the service is "active" (not "activating") and the health check returns 200.
**Seen:** 4

### "It compiled" is not verification
**Mistake:** Changes built cleanly but did nothing or crashed at runtime: JSX placed in the wrong component of a huge file never rendered, `t()` was called in components that never called the i18n hook (white screen in production), and one MCP tool schema made the whole `tools/list` response fail, so no new tools registered.
**Root cause:** esbuild-based builds and loose typing accept undefined identifiers and out-of-scope names, and some SDK + zod 4 combinations fail to serialize mixed unions to JSON Schema without a build error.
**Rule:**
- Before inserting stateful JSX, grep for the nearest enclosing `function Component` above the insertion point. Sibling top-level components don't share closures, so call each hook at the top of every component that uses it.
- `vite build` is not a type-check: run `tsc --noEmit` with zero errors in touched files, then click the feature in the browser (in each locale for i18n) before committing.
- In MCP tool inputs, avoid mixed primitive/object unions and `z.record(z.any())`; accept a JSON-encoded string and parse it in the handler. After any schema change, pipe `initialize` + `tools/list` to the server over stdio and check that the tool count matches the number registered.
**Seen:** 4

### A pattern bug means fixing every sibling, consumer and mode
**Mistake:** A missing filter was fixed in one endpoint while an identical sibling endpoint kept it and corrupted data. One reader of a shared "pending" slot was guarded while a second reader fired into the wrong session. A feature wired for one component mode was missing in a mode added later.
**Root cause:** Fixed the traced path or the original mode instead of every place with the same shape.
**Rule:** When the root cause is a pattern (missing tenant filter, unsafe selection, missing auth check, unguarded shared state), grep every call site and reader of the same shape and fix them all in the same ship, or centralize the logic. Bind the target id to the shared value (or use a per-key map) so readers can't race on a parallel field. When a component gains a mode, audit every feature on it in that mode: visibility conditionals, ref binding, event handlers, sandbox and permissions.
**Seen:** 3

### Irreversible actions: order steps so a crash fails safe
**Mistake:** A sentinel file that authorized a real send to a customer was never consumed, so every rerun sent again; the workaround (remembering the sentinel's mtime) fails open if that record is lost. Separately, a reader advanced its cursor before delivering, and a kill in between lost a message silently.
**Root cause:** Steps were ordered for convenience without asking which way a crash between them falls, and a one-time authorization was stored as persistent state with no one responsible for resetting it.
**Rule:**
- For "flag present = do an irreversible action once": consume the flag first, then act, and refuse if it can't be consumed.
- Prefer guards that block when something is absent (fail closed) over guards that block on a matching record (fail open); if you must use the latter, add a max-age cutoff.
- Put sentinels in a directory created by and owned by the executing identity, not a shared sticky dir like `/tmp`.
- When marking and delivery are separate steps, deliver first and mark after, so a crash causes a visible replay, not a silent loss. Test by killing the process between the two steps.
**Seen:** 3

### Make failure look different from success
**Mistake:** A UI computed a success count from results when the API's guaranteed `ok` field was missing, so an error showed as a normal number. A fix shipped with a green source-level test while every production write threw on a UNIQUE constraint into a bare `.catch(() => {})`.
**Root cause:** A missing field was treated as something to degrade gracefully, an error was silenced, and a test that only checks a line exists was taken as proof that it works.
**Rule:** Fall back only when absence has a meaning. If a field is guaranteed on the success path, its absence is a fault: show an error and no number, and check that the error CSS selectors match the failure DOM. Never swallow a write error; log it at least. Check column constraints before designing a write, and verify runtime effects through the product, not the repo.
**Seen:** 2

### Values the server decides must come from the API
**Mistake:** The API returned `truncated: true` while the page hard-coded "only the first 8000 chars kept". On a client dashboard, bare "not filled" placeholders were reported as bugs, though a one-time notification had explained them once.
**Root cause:** A hard-coded number keeps rendering when it no longer matches the server and silently lies, and a one-off notice is not a lasting record.
**Rule:** Anything the server decides and the page repeats, including numbers, comes from the API (return `limit`, not just a boolean). Test: if the backend changes the value and the page doesn't follow, does the page go blank or go wrong? If it goes wrong, the API must supply the value. A blank on a client-facing screen says why it is blank and who fills it, using wording from the API.
**Seen:** 2

### Print counts before and after every join and filter
**Mistake:** A total came from a query that inner-joined to a parent table and dropped every row with a null foreign key (about a third). A field with a similar name was used as a "step completed" flag; it was set on almost every row, so a work queue filtered from 34 items to 0, which looked like "nothing to do".
**Root cause:** An inner join used for enrichment also worked as a filter, and a field was used without checking what it means.
**Rule:** Count with no joins first, then join for detail and check that the numbers match; any gap is a finding. Use left joins for enrichment. Filter on status only with fields that have exactly that meaning; if none exists, say so and let the owner decide. A result of 0 or "all" after a filter is a red flag.
**Seen:** 2

### Before using an existing helper or pattern, read a real instance
**Mistake:** `toast.show(msg)` was called dozens of times when `toast` was a plain function, so every call threw silently. A new modal was built with a different UI library than every other modal in the project, which caused z-index conflicts over three rounds of patches.
**Root cause:** An assumed convention was used instead of the codebase's own. A noisy tsc baseline hid the errors, and "reference that commit" was applied to the logic only.
**Rule:** Grep an existing call site before you use an unfamiliar export, and an existing instance before you build a modal, drawer or form; match its library, imports and styling, not just its logic. When success depends on a feedback channel you can't see (toasts, logs), smoke-test that channel before you claim the change is verified.
**Seen:** 2

### Deploys must not delete what the incoming set omits
**Mistake:** A deploy ran `rm -rf` then `rsync --delete`, so a partial update wiped user-uploaded images and server code. In another case, users with cached HTML got a blank page: requests for deleted hashed bundles fell through to `index.html` and failed to parse as JS.
**Root cause:** The deploy treated the incoming file set as the full desired state, and a catch-all SPA fallback covered `/assets/*`.
**Rule:** Merge incoming files over the existing tree (files sent win, files not sent are kept) and keep version history so you can restore. For an SPA on nginx, use `location /assets/ { try_files $uri =404; }` with an immutable long cache, and `location / { SPA fallback }` with `Cache-Control: no-cache, must-revalidate`. Deploy without `--delete` and keep the previous bundle set for a grace period.
**Seen:** 2

### Scraper output: trim before the model, cap in the input body
**Mistake:** A tool returned full scraper objects (MBs each) to an agent, which used up the run's cost cap in one turn. A run-level item-cap query param became a charge cap below a per-page actor's minimum, so the run "succeeded" with 0 rows.
**Root cause:** There was no projection step before the model, and one cap mechanism was applied to actors with different pricing models.
**Rule:** Reduce each item to a short allowlist of fields with truncated text before it reaches an LLM, and give each new source its own field list or a strict generic trim. For pay-per-page or pay-per-event actors, set the cap in the input body, not the run-start query param. Treat "SUCCEEDED with 0 items" as suspicious and read the run log.
**Seen:** 2

### Diagnose at the data, not the symptom
**Mistake:** Broken images were blamed on a stale cache when a hand-written server was reading binaries as UTF-8 and serving them as text/plain. Internal IDs showing in place of case numbers were patched in the display layer, while an async fallback kept writing the wrong value to the DB for other modules to read.
**Root cause:** A plausible explanation of the visible symptom was accepted without checking the stored or served bytes.
**Rule:** Compare the served bytes with the file on disk, or trace how the value was stored, before you pick a cause or a layer to fix. If anything besides the display reads the value, fix it upstream, and say in the report which layer you fixed. Static servers read non-text files as Buffers, include image, font, video, audio and pdf MIME types, and default to `application/octet-stream` (or use `express.static`). When you exempt a loop from dedup, ask whether it can now write without limit.
**Seen:** 2

### CSS and layout: check the cascade and the worst case
**Mistake:** A property was edited again and again inside an `@media` block that never applied, because the base rule came later in the source. A list in a pinned area above a chat input pushed the input off-screen when there were many items in a small Firefox window.
**Root cause:** Reasoned about the value instead of whether the rule wins (media queries add no specificity), and flex children default to `min-height: auto`.
**Rule:** Read `getComputedStyle` (or the DevTools computed pane) first; if the override loses, fix the order or specificity, then verify at the real breakpoint. For pinned areas, test the maximum item count, the smallest realistic viewport and Firefox; cap content with `max-height` + `overflow-y: auto` + `min-height: 0`, or move variable-length content into the scroll region.
**Seen:** 2

### Browser automation: bulk-fill text, screenshot silent failures
**Mistake:** Typing a few hundred characters with one `locator.type(ch)` per character hit the script timeout. A 248-char connection note left a send button disabled, and the run failed.
**Root cause:** Each Playwright action costs about 200ms of actionability checks, and an outdated length limit was assumed (free accounts on that network allow 200 chars).
**Rule:** Use `locator.pressSequentially(text, {delay: 10-15})` or `.fill()` for bulk text, and keep per-character jitter only for short, detection-sensitive fields. Enforce platform input limits in code, schema and agent guidance. When a scripted submit fails silently and the dialog stays open, take a screenshot: usually a validation rule has disabled the button, and the selector is fine.
**Seen:** 2

### Swapping a dependency: stored copies keep the old call shape
**Mistake:** A vendor integration was swapped by updating the allowlist and the prompt template, but each agent's prompt had been copied into its DB row at creation, so existing agents kept the old field names. The new vendor's limit field also counted pages, not items (about 20x the cost).
**Root cause:** The template was treated as live config, though stored copies are not references, and fields with the same name were assumed to use the same units.
**Rule:** Before swapping a dependency, find every place where stored state contains the old call shape. Put a translation shim at the single choke point and test it with the old shape. Check the unit of every limit or cap field before you reuse cap logic.
**Seen:** 1

### Route on explicit state, not keyword heuristics
**Mistake:** A `created || looksLikeEdit(msg)` guard sent the first message down the "modify" path because an auto-generated prompt contained a trigger keyword.
**Root cause:** An OR with a keyword heuristic let text, including system-generated text, override real state.
**Rule:** Gate flow transitions only on explicit state flags. A keyword heuristic may refine a branch but must never bypass the state that decides which branch you're in.
**Seen:** 1

### Structured data goes through a parser, never model transcription
**Mistake:** An LLM agent read an uploaded CSV by eye or split it on commas, and silently dropped about 20% of the rows (quoted fields contained commas).
**Root cause:** The agent prompt had no guidance for data files.
**Rule:** Tell agents to parse data files with a real parser (Python `csv.DictReader` with `utf-8-sig`, papaparse, csv-parse), map columns by header name, and assert that rows in equals rows out. Verify both deterministically (the parser on the real file) and end to end (the agent with the new prompt on the real file).
**Seen:** 1

### BigInt columns break strict equality and JSON
**Mistake:** `projectId === 2` on a Prisma BigInt column was always false, so the feature silently did nothing; `JSON.stringify` on the same value throws.
**Root cause:** ORM BigInt columns map to JS `bigint`, which can't be compared with `===` to a `number` and can't be serialized to JSON.
**Rule:** Compare as `Number(x) === n` or `x === 2n`, and convert before any `JSON.stringify` (responses, queues, logs). Grep the diff for the field and check every site. Nearby `Number(...)` calls are a hint that the column is BigInt. Run an e2e test against real DB types.
**Seen:** 1

### Cross-page handoffs: use persistent storage only
**Mistake:** Both an in-memory store value and sessionStorage were set before a full-page navigation; the old page's effect fired synchronously, consumed and cleared the storage, and the new page got nothing.
**Root cause:** Store updates are synchronous, and subscribed effects run before the navigation completes.
**Rule:** For a handoff across a hard navigation, write only to session or local storage, and don't also change in-memory state on the source page.
**Seen:** 1

### A missing table after a merge: check migrations before permissions
**Mistake:** A merged PR added a model to the schema, the table never appeared, and a grants problem was suspected.
**Root cause:** `prisma migrate deploy` and similar tools apply only committed migration folders, and no image had been built after the merge.
**Rule:** Check that the migration file is committed and that the deployed image contains it before you touch permissions. For read-only roles, use `ALTER DEFAULT PRIVILEGES` so future tables are covered. Docker container IPs can change when a stack is recreated, so pin a stable host port for external consumers.
**Seen:** 1

### Security-group references match only private traffic
**Mistake:** Deploys timed out silently after the source host's public IP changed, even though an SG-to-SG rule existed.
**Root cause:** The traffic went to the target's public IP, so only the public CIDR allowlist applied.
**Rule:** Send host-to-host traffic over private VPC addresses so SG-reference rules apply; otherwise, update the CIDR allowlist on every public IP change. "Connection timed out" (rather than "refused") points to a firewall.
**Seen:** 1

### Keep a generator's inputs as separate persisted files
**Mistake:** An invoice render script held its data inline, so editing it for the next invoice destroyed the previous input, which later had to be rebuilt from the sent PDF.
**Root cause:** The script was both program and data, and programs get edited.
**Rule:** For scripts that run repeatedly and produce output that is sent out, store each input as its own file (for example, `invoices/<name>.json`) that the script reads. After you refactor a generator, re-render an already-shipped artifact and diff it against the original; a new output only proves the program runs.
**Seen:** 1

### An agent framework is not the model
**Mistake:** A request to adopt another agent CLI was described as "switching the LLM model".
**Root cause:** The runtime (tool loop, MCP, agent loop) was conflated with the model behind it, which distorts estimates and trade-offs.
**Rule:** A named CLI or tool means the framework; a named model or API means the model. If it's ambiguous, offer three options (swap the framework, swap the model, or both) and estimate each separately.
**Seen:** 1
