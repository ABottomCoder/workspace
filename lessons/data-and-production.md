# Data and production

Lessons about touching live systems and real data: restarts, deploy verification, destructive operations, migrations, environment identity, and numbers derived from production data.

### Check live use before restarting, and warm the service up after
**Mistake:** Restarted customer-facing services (an API with an in-memory queue, a job worker, a client's live service) while real users were active; in-flight requests were lost silently, and a worker's cold window stalled every job for minutes for the user who had reported the bug.
**Root cause:** Estimated the impact ("a few seconds, reversible", "no workers running") instead of checking the fact (is anyone using it right now?); lucky near-misses give no signal, so the habit repeats.
**Rule:** Before any restart, check recent real activity (access logs, recent DB rows, a quiet-check script that refuses when busy) and wait for a lull or warn affected users; bypass only for a real outage and say so. After a restart, wait for registration, push one throwaway job to completion and watch heartbeat age before telling anyone to retry. Durable fixes: a persistent queue, graceful drain on SIGTERM, automatic warm-up on boot.
**Seen:** 4

### After a deploy, migration or cutover, prove real end-to-end behavior yourself
**Mistake:** A host migration restored the DB but left a named volume empty, so existing user pages 404'd; a redeploy left an environment with no worker for almost two days because only web URLs were checked; after a config-only cutover, the client's first test crashed on one malformed inbound item.
**Root cause:** "Login works / HTTP 200 / same code" was taken as "everything works"; checks did not cover every role, every data store or real external input.
**Rule:** Enumerate everything stateful (`docker inspect` mounts, compose `volumes:`), size it on the old host and confirm it on the new one. Restart scripts wait for old processes to exit before starting new ones. After any redeploy verify every role (API, worker heartbeat, tunnel), then push one fresh transaction through end to end, and open an existing user-facing artifact, before the customer touches it. Make per-item input handling fault-tolerant: skip, log, advance the cursor.
**Seen:** 3

### Destructive operations need an explicit, reviewed, scoped target list
**Mistake:** A heuristic "remove old/test apps" sweep archived real projects and deleted live apps the night before an event, with no record of what was removed; a test-cleanup `DELETE ... WHERE content LIKE '...'` removed matching standard messages for dozens of real users.
**Root cause:** Targets were selected by heuristic or text pattern, which also matches real users' data; no allowlist, dry run, snapshot or log.
**Rule:** Build an explicit ID allowlist of rows/objects you created, print it and have it reviewed. Run `SELECT count(*)` with the same `WHERE` first to confirm blast radius. Snapshot the target set, log every removal, keep a recent dump, and never sweep during a freeze or before an event. Restore through the product's own deploy path, not hand-rolled copies.
**Seen:** 2

### "Idle" is not "abandoned": don't stop real users' workloads to save cost
**Mistake:** Stopped or deleted dozens of hosted user apps with no traffic for 7+ days to fit a smaller instance; still-used low-frequency sites went down within minutes, and the real memory math showed everything fit anyway.
**Root cause:** A traffic heuristic was used as a proxy for abandonment, and the destructive lever was chosen before measuring actual need (PSS).
**Rule:** Measure real resource use before choosing a destructive lever; right-size or go up one tier instead of stopping user workloads, which is a last resort needing confirmation. If an app must be parked under pm2, know that stopped apps come back on `resurrect` and may be skipped by "unchanged" redeploy checks, while `delete` removes the registration. Keep a bulk-restore tool.
**Seen:** 2

### Never test against production with real users
**Mistake:** A concurrency stress check on production tripped the worker's failure self-shutdown and stopped real jobs; separately, bulk-running an unread test suite created real accounts and paid jobs on production because tests hard-coded the production URL.
**Root cause:** A shared production environment was treated as a test target, and running tests was treated as read-only although a test file is arbitrary code.
**Rule:** Load-test only in an isolated environment; if production must be touched, keep it tiny, watch health live, pause background probes and abort before protective thresholds. Grep unfamiliar tests for base URLs, DB URLs, signups and POSTs before running. Gate live E2E behind an explicit env flag, refuse production without a second flag, and make env-dependent tests skip with a reason (with a strict mode that fails on skips).
**Seen:** 2

### Resolve which system is production, and check freshness by the data itself
**Mistake:** A container with the right name on a reachable host was taken as the production database; it was a retired stack with weeks-old data. Separately, a table was trusted as current because its modification metadata was recent while a broken ingest committed empty writes.
**Root cause:** Identity and freshness were inferred from resemblance and metadata, plus a remembered address from a stale note; a wrong or stale database raises no error.
**Rule:** Resolve the name (DNS, load balancer, config) before acting; old stacks are usually left running. For any data wiring, make freshness an acceptance test: `max(<date_col>)` and row count on the resolved target, never table metadata. Add a staleness alarm where possible.
**Seen:** 2

### Before changing or writing to a shared object, check everything that depends on it
**Mistake:** Rewrote a web-server vhost as a redirect; as the only server block on 443 it was the implicit default for another hostname, causing a redirect loop and an outage. Separately, proposed recording revenue as a row in a credit ledger whose readers compute users' spendable balance.
**Root cause:** Reasoned from the object's name ("ledger", "this site's vhost") instead of its position and readers; a recorded fact ("only one vhost") was never used in inference.
**Rule:** Before a change, ask what depends on it implicitly (default server, global plugin, sole route, balance computation). "Only one X on Y" usually means a load-bearing fallback. Before writing, list every reader, especially anything gating spend or access; keep revenue out of the product DB (append-only finance record). Run "is everything else still true" checks before reload (e.g. `curl --resolve` with each Host), and take the backup even when the change looks trivially reversible.
**Seen:** 2

### Back up only when the risk is irreversible, and prepare recovery before acting
**Mistake:** Risk handling swung between reflexive backups on every change and working out rollback in the middle of an incident.
**Root cause:** No explicit test for which changes need ceremony.
**Rule:** For irreversible-risk changes (prod deploy, schema migration, destructive op, auth or deploy-path change, secret rotation): write the plan, commit in-flight work, snapshot, and record exact recovery commands before executing. For anything git or a config flip undoes in seconds, just do it. Unsure means back up.
**Seen:** 1

### Never mutate a client's database data to test; use mock records
**Mistake:** Testing risked editing real client records, even in a local copy of client data.
**Root cause:** Code is protected by version control; database rows are not.
**Rule:** Code and file changes are fine. Create clearly marked throwaway test records instead of editing client data, and never touch the client's live database. A required real data change becomes a reproducible script with a backup of affected rows, tested on mocks, applied only with approval.
**Seen:** 1

### Before proposing deletion, ask why it exists, not whether it's used
**Mistake:** Proposed cleaning up a stale duplicate project that the owner had deliberately kept as a snapshot, then nearly "synced" it to latest, which would have destroyed it.
**Root cause:** Stale and archived look identical in data; intent is not stored, and an account's name says what it was created for, not who uses it now.
**Rule:** Presume a copy frozen at a meaningful point is intentional and ask its creator; "not updated in a while" systematically selects archives. Phrase uncertain destructive steps as questions. "Update this copy" is destructive: clarify "see the latest" vs "make this copy the latest", and satisfy the first with a new copy.
**Seen:** 1

### Enumerate a population from the object you act on, not a proxy
**Mistake:** An orphaned-app inventory was built from "apps with database tables" (41) while the action was stopping processes; listing processes found 62, including stateless and renamed apps the filter missed.
**Root cause:** A correlated proxy silently excludes whatever lacks the correlation.
**Rule:** Stopping processes means list processes; dropping tables means list tables; revoking grants means list grants. If a proxy is unavoidable, state the excluded class out loud. For every inventory filter, ask what it excludes.
**Seen:** 1

### Health checks must prove work is actually delivered
**Mistake:** A total outage (the upstream LLM account ran out of credit) went unseen because `/health` and `/ready` kept returning 200.
**Root cause:** Probes checked only DB, cache and loop liveness, not whether real work completed.
**Rule:** Add a deep readiness signal such as "a unit of work was delivered in the last N minutes" and alert on it or self-heal. Also verify the credential type each runtime needs (a CLI subscription token may not work for server-side agent APIs). Alert rules are useless if the monitoring stack itself is not running.
**Seen:** 1

### A new column that gates UI ships with a backfill or a NULL fallback
**Mistake:** Added a column used by strict-match UI logic; every existing row was NULL, so existing items disappeared overnight, and the gap was only "documented" in a code comment.
**Root cause:** Treated a data-migration gap as a comment instead of an UPDATE.
**Rule:** When a new column drives UI state, the same ship either backfills it from existing data or treats NULL as the legacy behavior. After migrating, count NULLs on production and backfill in the same window if non-zero.
**Seen:** 1

### Audit the denominator of any number an automation tells customers
**Mistake:** An automated Q&A assistant told the client "3904 unassigned cases, assign owners first"; 3056 of them were closed.
**Root cause:** An internal stat whose ambiguity didn't matter became customer-facing advice; automated errors repeat indefinitely and gain credibility with repetition.
**Rule:** For any number spoken automatically to customers, check whether it includes excluded classes (closed, handled, N/A), whether it triggers an automatic recommendation, and who would notice if it's wrong. A true number can still be wrong to say, or wrong to say a certain way.
**Seen:** 1

### Ask the deployer before declaring an incident on a fresh deploy
**Mistake:** Saw widespread 404s minutes after a teammate's deploy, escalated widely and recommended rollback; it was a planned stage of their migration.
**Root cause:** The observation was right but the "why" was invented; not knowing why something changed is not evidence it changed by accident.
**Rule:** Before declaring an incident on a system someone just deployed, ask the deployer first. Escalate immediately only if waiting is itself dangerous (data loss, money moving, a breach). If you escalated wrongly, retract everywhere you raised it.
**Seen:** 1

### Pull remote data out and diff locally; don't push payloads into production
**Mistake:** A check query embedding a list of customer emails was passed through a cloud-drive preview into a production shell; copy-paste injected UI text and it failed.
**Root cause:** The design made the payload travel several hops into production although one list was already local.
**Rule:** When comparing local and remote datasets, run a trivial argument-free query remotely (e.g. `select lower(email) from users`) and diff locally. Give the person with production access the smallest, simplest step; whoever has context does the thinking.
**Seen:** 1

### A release-gate environment must behave like production
**Mistake:** Recommended putting a test-only behavior switch in staging because it was the easiest place to verify it.
**Root cause:** Optimized for convenience over what the environment is for; staging being production-backed is exactly why it must not diverge.
**Rule:** Learn the team's environment semantics before proposing where a switch goes. Gate test-only behavior on an explicit allowlist of environments, never `env != "prod"`. If verification is hard in the intended environment, report that as a finding; any exception is the leads' documented decision.
**Seen:** 1

### Before an irreversible action, re-read live state and in-flight operations
**Mistake:** A close order was sent for a position that had already been closed, and the duplicate opened an inverted position; the state it acted on was cached, and a working order on the same instrument was not checked.
**Root cause:** Acted on assumed or cached state; did not look for operations already in flight on the same target.
**Rule:** Before any order, payment, deletion or other real-world action (automated or manual): fetch the current state from the system of record, not a cache, and list pending or working operations on the same target. If either differs from what you assumed, stop and re-plan. Build the check into code paths that act, not only into habits.
**Seen:** 1
