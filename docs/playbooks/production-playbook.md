# Production Playbook: Design, Build, Test

> **This is the top-level guide for building any new production-grade project with Claude Code.**
> Followed in full, the resulting system should be excellent on four axes: **secure, stable, reliable, scalable**.
>
> **Scope:** greenfield production projects, promoting a POC/demo into a production system, and production-grade refactors of existing systems.
> One-off scripts, purely internal tools and explicitly throwaway prototypes do **not** need the full process, but the design and security red lines still apply.
>
> **How to use it:** read it once before starting. Use §1 as the design checklist, follow §2 while coding, build logging and monitoring per §3, test layer by layer per §4 (including verifying that the observability from §3 actually works), launch per §5, and self-check against the Definition of Done in §6 before delivery. **Every layer needs an objective oracle: an SLO, an invariant, a consistency model, an ASVS item. "Looks fine" is not a pass condition.**

---

## 0. Three meta-principles (apply throughout)

1. **Design for failure, not for success.** Most production incidents happen on untested **error paths**: timeouts, network loss, partitions, races, bad input. The happy path is only the starting point.
2. **Determinism is the meta-goal.** You can only fix what you can reproduce. Control the clock (inject time, never `sleep`), isolate state, stub the network, seed randomness. A flaky test is no test: first it gets ignored, then disabled.
3. **Buy confidence where it is cheapest.** Unit, contract and property tests are cheap; let them carry most of the coverage. E2E, Jepsen, fuzzing and pen-testing are expensive; reserve them for the highest-risk surfaces. Allocate test effort with cost in mind.

---

## 1. Design rules: stable, reliable, scalable

> The goal of design is to turn adjectives like "highly available, fast, reliable, scalable" into **concrete architecture decisions and verifiable metrics**. For non-trivial projects, write a spec and plan first (template: `templates/ticket/spec.md`), then touch code.

### 1.1 Define quality attributes and metrics first (no metrics, no "reliable")

Before building any production system, write these numbers down. They are the oracle for every later test.

- **SLI / SLO / SLA**
  - **SLI** (service level indicator): a quantified measure of service quality, ideally expressed as the ratio `good events / valid events`. Classic SLIs: availability, latency, error rate, throughput, data freshness, correctness.
  - **SLO** (service level objective): the target value for an SLI over **a time window**. Example: 99.9% of requests succeed over a rolling 28 days; p95 latency < 300 ms. The SLO must be **stricter** than the SLA so internal alerts fire before you breach a customer contract.
  - **SLA** (service level agreement): the commercial contract with the customer, including breach consequences. Not every service has an SLA, but **every service has an SLO**.
  - **Error budget = 1 - SLO.** 99.9% availability means roughly 43 minutes of allowed downtime per 30 days. The budget is the shared currency between reliability and iteration speed: budget left, ship features freely; budget gone, freeze risky releases and work on reliability. Alert on **multi-window, multi-burn-rate** (fast burn 14.4x over 1h pages; slow burn 1x over 6h opens a ticket), not on raw thresholds.
- **The four golden signals** (observable by default): **Latency (success and failure latency measured separately), Traffic, Errors, Saturation.** Use **RED** (Rate/Errors/Duration) at the service layer and **USE** (Utilization/Saturation/Errors) at the infrastructure layer. Latency usually degrades well before saturation hits 100%, so set a **utilization ceiling** (e.g. 60-70%).
- **Always percentiles, never averages.** p95 / p99 / p999. Averages hide the tail.

### 1.2 Architecture principles (the foundation of scalability and availability)

- **Stateless services (12-Factor #6).** Hold **no** client session state in process. Each request carries what it needs or fetches it from a shared backend (Redis / DB / the JWT itself). Payoff: any instance can serve any request, giving horizontal scaling, rolling deploys, instant failover, and disposability. **Push all durable state to dedicated stores; treat compute as cattle, not pets.**
- **Prefer scaling out over scaling up.** Vertical scaling is simple but has a single point of failure, a ceiling, and needs downtime. Horizontal scaling is nearly unbounded and adds availability through redundancy. It requires statelessness plus load balancing.
- **Fault isolation / limit blast radius.** Use several small resources instead of one big one so a single failure has bounded impact. Make it redundant across AZs/regions; N+1/N+2 so losing one instance or AZ is still survivable.
- **Idempotency is the foundation of distributed systems.** Every cross-boundary **mutating** operation (especially money, inventory, order creation) must accept an **idempotency key**, so retry-with-backoff is safe.
- **Loose coupling and async.** Decouple producers and consumers with queues/events. Make long tasks async with a status endpoint; never park a request thread waiting.
- **Follow the 12-Factor App in full:** one codebase, many deploys; explicitly declared dependencies; config in environment variables; backing services as swappable attached resources; strict build/release/run separation with immutable releases; stateless processes; port binding; concurrency via the process model; fast startup and graceful shutdown (handle SIGTERM); dev/prod parity; logs as event streams to stdout; admin tasks as one-off processes.

### 1.3 Data layer: consistency is a deliberate choice

- **CAP / PACELC, practically:** network partitions are unavoidable, so the real choice is **CP vs AP during a partition**. `PACELC` adds that **even without a partition you trade latency (L) against consistency (C)**. Traditional RDBMS = PC/EC; DynamoDB = PA/EL.
- **Default strategy:** stateless services, data layer defaulting to **AP / eventual consistency plus session guarantees** (read-your-writes, monotonic reads, via sticky routing or version tokens). Use **strong consistency only for the small set of invariants that must never break** (payments, inventory decrement, uniqueness).
- **Consistency models, strong to weak:** linearizable (money / inventory / locks) -> causal -> session guarantees -> eventual (feeds / caches / analytics).
- **Concurrency control:** read-heavy, few conflicts -> optimistic locking (version column, `WHERE version=n`). Frequent write conflicts -> pessimistic locking (`SELECT ... FOR UPDATE`; acquire locks in a fixed order to avoid deadlock).
- **Pick isolation levels from business invariants, and know each engine's traps.** Postgres "Repeatable Read" is actually Snapshot Isolation: it **blocks phantoms but allows write skew**. Only true `SERIALIZABLE` (Postgres SSI) blocks write skew. The wrong level means data corruption; you must prove in §4 Layer 2, with two-connection tests, that the chosen level is safe for your invariants.

### 1.4 Resilience patterns (make "recovers from failure on its own" a mechanism)

A robust cross-boundary remote call is: **timeout -> bounded retry (exponential backoff + jitter + idempotency protection) -> circuit breaker -> bulkhead-isolated connection pool -> fallback on failure**. The server side also runs **rate limiting + load shedding**; streaming pipelines are governed by **backpressure**.

| Pattern | In one line | When to use |
|---------|-------------|-------------|
| **Timeout** | Cap every remote call / resource wait; never wait forever | **At every process/network boundary.** Unbounded waits are the top way one slow dependency drains every thread pool |
| **Retry + exponential backoff + jitter** | Retry transient failures at `base*2^n` plus random jitter | Idempotent, transient failures (rate limits, network blips). **Jitter is mandatory**, otherwise synchronized retries cause thundering herds / retry storms. Needs a retry budget and a total-time cap |
| **Circuit breaker** | Trip to fail-fast past a failure threshold; probe half-open after cooldown | When a dependency is down/degraded: stop hammering the patient. States: Closed -> Open -> Half-Open. Libraries: resilience4j / Polly / opossum (Node) |
| **Bulkhead** | Isolate thread/connection pools per dependency/tenant | Multiple dependencies or tenants sharing a process: one saturated pool must not sink the ship |
| **Rate limiting** | Token bucket / leaky bucket / sliding window | Overload protection and fair tenant quotas. Distinguish client self-limiting from server rejection (429 + `Retry-After`) |
| **Load shedding** | Under overload, reject fast (503) to protect accepted work | Near saturation. Serving 80% well beats total collapse. Shed by cost/priority: cheap, low-priority first |
| **Backpressure** | Signal upstream to slow down when downstream can't keep up | Streams / queues / producer-consumer. Use bounded queues, never unbounded buffers. Backpressure **slows**; shedding **drops** |
| **Idempotency key** | Request carries a unique key; server dedupes for exactly-once | Any non-idempotent operation that may be retried (payments, orders). Store the key transactionally with the side effect |
| **Graceful degradation** | When a dependency fails, return a degraded but usable response (cache/default) | Non-critical paths. E.g. recommendations down: product page still renders, just without personalization |

**Implementation rules (hard constraints and defaults for each pattern; these go into code, not onto a poster):**

- **Timeouts:** every remote call / DB query / lock wait **must set an explicit timeout**. Default to 2-3x that dependency's p99 with a hard cap; **never use a framework's "infinite / very large" default**. Mind the **cascading timeout budget**: the upstream total should be >= the sum of downstream timeouts, and a downstream timeout must never exceed its upstream's (otherwise upstream gives up while downstream keeps waiting).
- **Retries:** retry only **idempotent operations + transient/retryable errors** (timeouts, 429, 5xx, connection reset). **Never retry 4xx business errors.** Defaults: exponential backoff (base 100 ms, cap 2 s) + **mandatory jitter** + at most 3 attempts + a total-time cap. Add a **retry budget** (e.g. stop retrying when the overall failure rate exceeds 10%, so you don't finish off a degraded dependency).
- **Circuit breakers:** wrap every external dependency. Rule: failure rate over the threshold in a sliding window (default 50%, minimum sample e.g. 20 requests) -> **Open**. While Open, **go straight to fallback with no real call**; cooldown defaults to 30 s. **Half-Open** lets one or a few probes through: success closes, failure reopens. Breaker state **must be exposed as a metric + alert** (see §3.2), otherwise you don't know you are degraded.
- **Bulkheads:** each downstream dependency / tenant gets **its own connection pool and its own concurrency limit**; one saturated dependency cannot drag down the others. Separate pools for critical and non-critical paths.
- **Degradation plans (defined at design time, not improvised in production).** This is the most often missed and the most important:
  - **Classify features:** mark each feature **critical / non-critical**. **A non-critical dependency failure must never take down a critical path**: wrap it in try/catch + fallback and return a degraded but usable result (cache / default / empty state with a notice) instead of failing the whole request with a 500.
  - **Write the degradation ladder:** for each critical path, **state in advance what is returned when dependency X fails** (stale cache -> default value -> read-only mode -> friendly error page). Decide at design time and confirm in review, not after the incident.
  - **Kill switch / feature flag:** put heavy, expensive or fragile features behind a switch so you can **degrade or disable them in one step without a release** (e.g. LLM workload overloaded -> switch to a smaller model or queue it; a third-party API down -> turn off the features that depend on it).
  - **Degradation must be observable:** entering a degraded state emits a **WARN log + metric + (when needed) an alert**. **Never degrade silently** until users complain. Record recovery too.
- **Rate limiting + load shedding:** enforce rate limits server-side (token bucket, per user/IP/key) and reject with **429 + `Retry-After`**. Near saturation, **shed by priority** (fast 503 for low-priority requests) to protect latency for high-priority ones.
- **Think through the default failure mode (fail-open vs fail-closed):** security-related (authz / payments / quotas) **defaults to fail-closed**: on error, deny; never "allow on error". Experience-related (recommendations / decorative content / personalization) **defaults to fail-open**: on error, degrade and let the main flow continue. Every fallback must state which category it is in.

### 1.5 Capacity planning and autoscaling

- Compare a **demand forecast** (organic growth + launch spikes + seasonality) against **measured unit capacity** (the req/s a single instance sustains before breaking the latency SLO, found by load testing: the **saturation knee**, usually well below 100% utilization).
- Reserve headroom with a **utilization target** (60-70%) for failover, spikes and redundancy.
- **Autoscale** on **leading signals** (queue depth, RPS, p95 latency), not CPU alone. Account for **warm-up / boot latency**; pre-scale for predictable spikes. Validate the scaling policy with load tests.

### 1.6 Security by design (shift left into design = OWASP A04 Insecure Design)

- **Threat modeling with STRIDE:** draw the data-flow diagram -> mark trust boundaries -> apply STRIDE to each element (Spoofing -> authentication / Tampering -> integrity / Repudiation -> audit logs / Information disclosure -> encryption + least privilege / Denial of service -> rate limits and quotas / Elevation of privilege -> RBAC, deny by default) -> rank with CVSS -> record mitigations. Tools: Threat Dragon / pytm.
- **Strong identity foundation:** least privilege, separation of duties, centralized identity, **eliminate long-lived static credentials**.
- **Defense in depth:** controls at every layer (edge / network / load balancer / instance / OS / application / code).
- **Data protection:** encrypt in transit and at rest; keys live in a key manager, never in code or the repo.
- **Input validation at trust boundaries is the task itself, not "extra code".** Never drop it to shorten a diff.
- **Auditability:** real-time monitoring, alerting and audit of security events (maps to A09 logging and monitoring).

### 1.7 Observability by design (built in from day one, not bolted on)

Observability is a design constraint, not a pre-launch add-on: structured logs with `trace_id` throughout, the four golden signals, distributed tracing, and liveness/readiness health checks all need a reserved place in the architecture. **The full rules are in §3, the authoritative home for logging and monitoring.**

---

## 2. Development rules

> Working principles come from the Decision Ladder (`docs/principles/decision-ladder.md`): the least code that fully solves the problem; reuse before writing new; fix root causes, not symptoms. This section adds the hard requirements for production code.

- **Every cross-boundary call has a timeout.** No exceptions. Calls without timeouts are the top source of cascading failure.
- **Error handling prevents data loss:** either succeed completely or roll back cleanly; never half-commit. Distinguish retryable from non-retryable errors.
- **Idempotency and retries come as a pair:** idempotency keys plus optimistic/pessimistic locking make retries safe.
- **Circuit breakers, degradation and bulkheads are coding requirements, not "later":** wrap each external dependency with a **circuit breaker** (trip past threshold + fallback) and a **dedicated connection pool** (bulkhead) per the §1.4 rules. Each critical path handles dependency failure per its **predefined degradation ladder**; **a non-critical failure never takes down a critical path**. Security fallbacks default fail-closed, experience fallbacks fail-open. Degraded states emit WARN + metrics, never silent.
- **Graceful shutdown:** catch SIGTERM -> stop accepting new work -> drain in-flight requests within a deadline -> close connection pools -> deregister from the LB / service discovery -> exit (before the orchestrator's SIGKILL).
- **Config in environment variables; secrets in a secrets manager**, never hard-coded, never in the repo. Add `gitleaks`/`trufflehog` pre-commit hooks that scan full history.
- **Pin dependencies explicitly** (lockfile) and scan for CVEs regularly (Trivy / Dependabot / `npm audit`).
- **API contract first:** define a schema (OpenAPI / JSON Schema / Protobuf) and validate inputs and outputs.
- **All resources are bounded:** connection pools, queues, caches and concurrency all have limits, to prevent unbounded growth and OOM.
- **Parameterized queries** (ORMs such as Prisma parameterize by default, but any raw SQL such as `$queryRaw` / `$executeRaw` needs dedicated review).
- **Logging instrumentation is part of development, not optional:** per §3, the shared logging library attaches `trace_id` to every log line automatically; critical paths and every error branch leave traceable structured logs.
- Before shipping security-sensitive changes (auth, billing, secrets), run a high-confidence SAST scan (e.g. Semgrep "important only") and triage the findings.

---

## 3. Logging and monitoring rules: complete traceability, full coverage, fast response

> Two hard targets: **(a) complete log traceability**: any anomaly or error can be reproduced accurately end to end; **(b) monitoring** (optional depending on the client's needs, but once in scope): **full coverage and fast response, without alert fatigue.**
> This chapter comes before testing (§4) because logs and monitoring are **things under test**. Build them first so §4 has something to verify.
>
> **The traceability spine:** `trace_id` runs through everything, propagated on the wire with W3C Trace Context and carried manually across async/queue boundaries. Given any error log line, its `trace_id` retrieves every log line for that one request across all services and all async hops (plus the distributed-trace waterfall). This spine must be enforced in a **shared logging/instrumentation library**, not reimplemented per service.

### 3.1 Logging rules (complete traceability is mandatory, regardless of client requirements)

**Structured first: emit only machine-parseable JSON events, never free prose.** Plain text has to be parsed at ingest with fragile regex/grok that breaks when a sentence changes, and cannot be filtered or aggregated by field. With structured logs the backend indexes fields directly and you query `level:ERROR AND service:payments AND user_id:42` instead of substring matching.

- **Uniform field schema** (aligned with OpenTelemetry semantic conventions / Elastic Common Schema, enforced in the shared library rather than named ad hoc per service):

  | Field | Notes |
  |-------|-------|
  | `timestamp` | RFC 3339 / ISO 8601, **UTC**, millisecond or nanosecond precision. Never local time. |
  | `level` | TRACE/DEBUG/INFO/WARN/ERROR/FATAL (see below) |
  | `service` / `service.version` / `deployment.environment` | Service name + version + environment |
  | `trace_id` (128-bit) / `span_id` (64-bit) | W3C Trace Context, linking logs to distributed traces |
  | `request_id` / `correlation_id` | Per-request / per-business-transaction id, present even without a tracer |
  | `user_id` / `tenant_id` | **Pseudonymous ids, not emails / PII** |
  | `message` | Human-readable, low cardinality, stable wording |
  | `error.type` / `error.code` / `error.message` / `error.stack_trace` | Error classification + full stack (required on ERROR/FATAL) |
  | `duration_ms` / `http.status_code` / `http.method` / `http.route` / `host` / `version` | Context dimensions |

- **End-to-end `trace_id` propagation (the backbone of traceability):**
  - **Generate at the edge:** the first entry point (gateway / LB / first service) checks for an inbound correlation id and generates one if absent (UUIDv4 / 128-bit trace id). **Never trust "nothing": ensure an id exists before the request enters the system.**
  - **On the wire, use W3C Trace Context:** the `traceparent` header (`version-trace_id-parent_id-flags`), understood by OTel, Datadog, Jaeger, Zipkin and cloud providers. A human-friendly `X-Request-ID` can coexist.
  - **In process:** store it in an **execution-bound context object**: Go `context.Context`, Node **`AsyncLocalStorage`**, Python `contextvars`, Java OTel Context + thread-local. The logging library injects `trace_id` / `span_id` / `correlation_id` from the current context into every line automatically; no manual threading.
  - **Outbound:** inject these headers into **every downstream HTTP/gRPC/DB call** (OTel auto-instrumentation does this for you).
  - **Async / queue / event boundaries (where traceability gaps most often appear):** context does **not** cross thread pools, message queues or callbacks automatically. You must **serialize the trace context into the message envelope** (Kafka / RabbitMQ / SQS message headers) and the consumer must **extract it and restore it into context** before processing. Wrap thread pools / `CompletableFuture` with context-propagating executors. Scheduled jobs / cron **start a new root trace on each run** and tag it with a `job_id`.
- **Log level semantics** (configurable and switchable at runtime without restart; production defaults to INFO/WARN, temporarily DEBUG while troubleshooting):
  - TRACE: finest grain (inside loops, function entry/exit). **Never left on in production** (volume explosion + PII leakage).
  - DEBUG: development diagnostics. INFO: normal events worth recording (start/stop, request completed, order placed).
  - WARN: unexpected but handled (retry succeeded, fallback used, quota at 80%).
  - ERROR: **your own** failure: a request/job could not complete, a dependency exhausted retries, an uncaught exception.
  - FATAL: the process cannot continue and is about to exit.
  - **Two disciplines:** (1) **Log-and-throw is an anti-pattern.** Log an exception **once**, at the boundary where it is handled / turned into a response, not in every catch (otherwise one failure produces five ERROR lines and pollutes the error-rate SLI). (2) **4xx client errors are not ERROR** (a user sending a bad request is INFO/WARN). Reserve ERROR for your own failures so the error rate is a meaningful signal.
- **Never log (hard ban):** passwords / password hashes, API keys, tokens (access / refresh / JWT bodies), plaintext session ids, private keys, connection strings with credentials, **full card numbers / CVV** (prohibited by PCI-DSS; keep only first 6 / last 4), PII beyond what is necessary, full bodies of auth / payment / PII endpoints.
  - **Two layers of redaction:** (1) **At the source:** the logging library masks by key name (`password` / `authorization` / `token` / `ssn` / `card`) and by value pattern (card / SSN / email regex); for high-risk objects use an **allowlist of loggable fields** rather than a denylist. (2) **In the pipeline** (defense in depth): Fluent Bit / Vector filters or Datadog Sensitive Data Scanner as a second net. **Mask, don't drop** (`card=****1234`).
  - **Compliance:** logs containing personal data fall under GDPR (minimization, retention limits, right to be forgotten), so ideally PII never enters logs. If it must, isolate it, encrypt at rest, restrict access, auto-delete on a schedule (30-90 days), and authenticate + audit access to the logs themselves.
- **Error logs must enable reproduction:** ERROR/FATAL carry the **full stack** (in its own field, not stuffed into `message`) + the **cause chain** (Java `caused by:` / Python `raise from` / JS `Error.cause`; the root cause is often innermost) + a **stable error code** (`error.code=E_PAY_402`, machine-groupable for alerts) + **context metadata** (`trace_id` / `user_id` / endpoint / downstream involved / version). An exception without context is nearly useless; context turns "NullPointerException" into "checkout failed for tenant X on v1.4.2 while calling the tax service".
  - **Exception tracking tools** (fingerprinting, grouping, dedup and alerting on top of raw logs): Sentry / Rollbar / Bugsnag / Datadog Error Tracking. They give fingerprint grouping (thousands of events -> one issue + trend), first/last seen, affected users, regression detection, release attribution and breadcrumbs. For frontend / minified code, **upload source maps** (in CI, per release version; **never ship source maps in the public bundle**) so `a.b.c:1:2345` maps back to real file and line. Tag every event with `release` / `environment`.
- **Log pipeline (12-Factor #11):** the app writes **unbuffered to stdout/stderr** and does not handle routing, files or storage. The execution environment (journald / Docker / K8s) captures it and a collector ships it.
  - **Collectors:** Fluent Bit (lightweight, first choice as a K8s DaemonSet) / Vector (Rust, high throughput, strong transforms) / Fluentd / OTel Collector (unifies all three pillars).
  - **Storage and query:** ELK / Elastic (strong full-text search, but indexing every field is expensive) / **Grafana Loki** ("Prometheus for logs": indexes only labels and stores compressed bodies, cheap at scale; watch label cardinality) / Datadog / Splunk / CloudWatch.
  - **Retention and cost:** tiered retention (hot index 7-30 days -> warm -> cold archive S3/Glacier -> delete). **Sample** high-volume INFO/DEBUG (tail sampling: **always keep errors and slow requests**, sample only boring successes). Drop known noise in the collector. Log volume is one of the top three observability costs: budget it explicitly and monitor bytes per service per day.
- **Audit logging is a separate subsystem, not a log level.** Record who (the authenticated principal, not just an IP) / what (action + object) / when (trusted server time) / where (IP / session / request id) / outcome / before-after. Its requirements differ from application logs: **tamper evidence** (append-only, WORM, hash chain: each entry hashes the previous one, so any edit or deletion breaks the chain and integrity is provable), **access control on the audit log itself** (admins who can act must not be able to quietly edit the trail), **longer compliance retention** (SOX / HIPAA / PCI / SOC 2 often 1-7 years). Record all authn/authz events, sensitive data access, admin/config changes and data exports.

### 3.2 Monitoring rules (optional per client needs; once in scope = full coverage + fast response)

**The three pillars and how they work together:** **metrics** tell you "something is wrong" (cheap, good for dashboards and alerts) -> **traces** tell you "where" (which service / span) -> **logs** tell you "why" (exact error + stack + context). The operational loop: **metric alert** (SLO burn) -> open the **trace** of a bad request -> jump from the span to the **logs** via `trace_id` -> root cause. Prometheus/OTel **exemplars** embed `trace_id` in metric samples for one-click metric-to-trace.

- **Instrument once with OpenTelemetry:** one SDK emits traces + metrics + logs with unified semantic conventions (`service.name` / `http.*` / `error.*`) so they correlate automatically. The OTel Collector (receive -> process -> export) decouples app from backend: switch backends without code changes, no vendor lock-in. W3C Trace Context is its default propagator, which is why all three pillars share `trace_id`.
- **Use the right metric type:** Counter (monotonic; query `rate()`, not the raw total) / Gauge (snapshot that goes up and down: memory, queue depth, in-flight requests) / **Histogram** (buckets; **computes p50/p95/p99 server-side across instances**; use it for latency/size distributions, with buckets aligned to SLO thresholds) / Summary (client-side precomputed quantiles, **cannot be aggregated across instances**; prefer Histogram whenever possible).
- **Cardinality is the number-one metrics trap:** every combination of label values is its own time series. **Never put high-cardinality values (`user_id` / `request_id` / `email` / full URLs with ids / `trace_id`) in labels**; they blow up the TSDB. Labels hold only **bounded, low-cardinality dimensions** (route template `/users/{id}`, not `/users/42`; status code; region; method). High-cardinality identifiers go in logs/traces.
- **Full coverage = no blind spots at any layer:**
  - **Infrastructure / host** (USE: Utilization / Saturation / Errors): CPU, memory, disk I/O and space, network, file descriptors, run queue. `node_exporter` / `cAdvisor`.
  - **Application / service** (RED: Rate / Errors / Duration): request rate, error rate and latency distribution p50/p95/p99 per service / endpoint.
  - **Business KPIs:** signups per minute, orders, checkout success rate, revenue per minute, active users. Infrastructure can look fine while a broken button loses orders; business KPIs are often **the most sensitive early warning**.
  - **Dependencies / external:** for each downstream (DB / cache / third-party API / payments): call rate, error rate, latency, timeout / retry / breaker state, pool saturation. Instrument on the **client side**.
  - **Synthetic monitoring (blackbox):** scripted real user journeys run on a schedule from outside ("does login work right now?"), catching problems before real users and covering low-traffic paths. Blackbox Exporter / Checkly / Pingdom.
  - **Real user monitoring (RUM):** instrument real clients: real latency, Core Web Vitals (LCP / INP / CLS), JS errors, geography and devices. Sentry / Grafana Faro / Datadog RUM.
  - **Distributed tracing:** attribute latency to specific spans/dependencies. Jaeger / Grafana Tempo / Zipkin, fed by OTel.
  - **Four golden signals** (the minimum required set, a superset of RED/USE): Latency (**success and failure separately**), Traffic, Errors, Saturation (the resource closest to its limit, the leading indicator of degradation).
- **Responsive but quiet: alerting philosophy.**
  - **Alert on symptoms, not causes:** alert on **user-visible symptoms** (checkout error rate > X, p99 > SLO, orders per minute dropping sharply), **not on every internal cause** (CPU 90%, a pod restarting; causes often self-heal and are pure noise). **Page only when a human must act now**; everything else goes to a dashboard or a ticket. Saturation is the accepted **predictive** exception (page ahead of symptoms when the trend is clear).
  - **SLO error-budget burn-rate alerts (current best practice):** alert on **how fast the budget is burning**, not on instantaneous error rate. **Multi-window, multi-burn-rate** (SRE Workbook): fast burn (e.g. 14.4x over 1h, which exhausts a 30-day budget in about 2 days -> **page**) + slow burn (e.g. 3x over 6h -> **ticket**). **Pair long and short windows** (both 1h and 5m exceeded) for fast detection, fast reset, and no false positives from transient blips. This is the mechanism for "sensitive and quiet".
  - **Noise reduction:** every alert must be **actionable** (nothing to do means it should not page; delete or downgrade alerts that are routinely ignored). **Tier** them (page P1 / ticket P2-3 / info dashboard-only) and route by channel. **Dedupe, group, inhibit** (Alertmanager merges related alerts, an upstream failure inhibits 50 downstream dependency alerts, silence during maintenance). **Attach a runbook link to every alert** (meaning / diagnosis / fix / escalation) so a 3 a.m. page is a checklist, not a research project. Add a `for:` duration to avoid flapping.
- **Incident response tooling:** on-call and escalation (PagerDuty / Opsgenie / Grafana OnCall: rotations + escalation policies + multi-channel notification); dashboards (Grafana; few and high-signal: RED / USE / SLO burn-down / business KPIs / dependency health); health checks (separate liveness and readiness, shallow `/healthz` vs deep `/readyz`; **don't cascade deep checks**: a dependency outage should not get you killed and mask the real cause).
  - **Dead man's switch (alert on the absence of a signal): critical and most often missed.** Healthy pipelines emit a heartbeat; **alert when the heartbeat stops**. This catches "the monitoring itself is dead" (scraper down, cron didn't run, a whole datacenter dark -> no metrics -> no alerts -> silent failure). Use Prometheus `Watchdog` / Dead Man's Snitch / Healthchecks.io / Cronitor. **Every critical scheduled job, and the alerting pipeline itself, needs a dead man's switch**; otherwise "no alerts" and "all is well" are indistinguishable.
- **Thresholds and anomaly detection (pragmatic order):** start with **static thresholds on symptoms/SLOs** (explainable, covers 80%); then add **rate-of-change alerts** on leading signals (`deriv()` / `rate()`: "at this slope the disk fills in 4h", KPI cliffs); use **dynamic / ML anomaly detection** only for strongly seasonal metrics or those with no natural upper bound (traffic, business KPIs), seasonality-aware (Holt-Winters / STL) so the normal Sunday dip doesn't page. Anomaly detection **supplements**, never replaces, SLO symptom alerts.

---

## 4. Testing rules: progressive layers, every layer must pass

> The test pyramid: many fast **unit** tests at the bottom, **integration/contract** in the middle, a few **E2E** at the top. Cost and duration grow upward. The four layers are **progressive**: if a layer fails, do not move to the next. Every layer has an objective oracle. In addition there is a cross-cutting **observability verification** (Layer 5, §4.5) that proves the logging and monitoring built in §3 actually work.

### Layer 1: Business correctness

**Goal: features work as specified.**

- **Unit tests:** test single functions/classes in isolation. Prefer fakes for collaborators over mocking everything (over-mocking couples tests to implementation and produces brittle "mockery"). Tools: Jest / Vitest (JS/TS), pytest, JUnit 5, Go `testing`.
- **Integration tests** (the biggest lever for backend quality): exercise multiple real components together, especially across I/O boundaries. Use **Testcontainers** for real Postgres / Redis / Kafka (eliminating "passes on SQLite, fails on Postgres" bugs); stub outbound calls with **WireMock / MSW / nock**; test Express routes with **supertest**.
- **Contract tests** (key to keeping microservices independently deployable): **Pact** (consumer-driven, Pact Broker + `can-i-deploy` gate) or schema-level (OpenAPI validation, Buf for Protobuf backward-compatibility linting).
- **E2E:** only for critical revenue / auth journeys (e.g. sign up -> core action -> checkout). Use **Playwright** (auto-waiting, trace viewer). Anti-flake: auto-wait instead of fixed sleeps, stub third parties, isolated test data per run, quarantine failures instead of blind retries.
- **Property-based testing (PBT):** assert properties that hold for **all** inputs; the framework generates hundreds of random cases and **shrinks** to a minimal counterexample. Tools: fast-check (JS/TS), Hypothesis (Python, including stateful), jqwik (Java). Killer patterns: round-trip (`decode(encode(x))==x`), invariants, oracle (compare against a naive implementation), state-machine model tests.
- **Coverage philosophy:** coverage is **a floor, not a target**. Use a ratchet (never decrease) rather than a vanity number; ~70-85% branch coverage on business logic **with meaningful assertions** is the healthy zone. **Goodhart's law:** once coverage becomes the target it stops measuring quality. Run **mutation testing** on critical modules (Stryker / PIT / mutmut) to measure suite quality directly: surviving mutants are behavior left untested even at 100% line coverage.

**Pass criteria:** all acceptance criteria green; mutation testing on critical modules shows no large number of surviving mutants.

### Layer 2: Concurrency and races

**Goal: SLOs hold under high load, and concurrency causes no data corruption. Race bugs are non-deterministic; "run it and see" is not a test.**

- **Load testing** (define SLOs first, so there is a pass/fail): pick tools by protocol and authoring style: **k6** (JS scripts, first choice for CI), Gatling, Locust, JMeter. Watch for **coordinated omission**; prefer **constant arrival rate** (open model: k6 `constant-arrival-rate`) over a fixed-VU closed model.
- **Four load profiles:**
  - **Load:** expected peak; verify SLOs (p95/p99, throughput, error rate) hold.
  - **Stress:** push past capacity to find the breaking point and observe **how it breaks** (graceful degradation vs cascading collapse).
  - **Spike:** sudden surge and drop; test autoscaling response, pool exhaustion, cold starts.
  - **Soak / endurance:** moderate load for hours/days to catch **memory leaks, fd/connection leaks, unbounded cache growth**: the slow killers short tests never see.
- **Actually detect races** (not by luck):
  - **Dynamic race detectors:** Go `go test -race`, ThreadSanitizer for C/C++/Rust, Java `jcstress`. **Run the whole CI suite under `-race`.**
  - **Deterministic simulation testing (DST):** run on a controlled scheduler + clock + network so any interleaving reproduces from a seed (the FoundationDB / TigerBeetle approach; in Rust: madsim / Shuttle / tokio's model checker).
  - **Distributed correctness, Jepsen:** inject partitions / clock skew / process kills into databases and queues, verify linearizability and detect isolation anomalies with the Elle / Knossos checkers. TLA+ can model the design first.
- **Idempotency and concurrency-control tests:**
  - **Idempotency:** send N concurrent duplicate requests with the same key; assert the side effect happens **exactly once** (one charge, one row).
  - **Optimistic locking:** test the conflict path: two transactions both read v1 and both write; one must fail with a stale version and retry; assert no lost update.
  - **Pessimistic locking:** test deadlock (fixed lock ordering), lock-wait timeouts, and throughput collapse under contention.
  - Force real interleavings with **barriers/latches** (block all threads, then release together), **not sleeps**.
- **Database isolation anomaly matrix** (encode each as a test with two interleaved transactions):

  | Anomaly | Symptom | Prevented by |
  |---------|---------|--------------|
  | Dirty read | T2 reads T1's uncommitted write | Read Committed+ |
  | Non-repeatable read | T1 re-reads a row and sees T2's committed update | Repeatable Read+ |
  | Phantom | T1 re-runs a range query and sees T2's committed insert | Serializable (PG RR and MySQL InnoDB RR also block it via MVCC / gap locks) |
  | Lost update | Two read-modify-write cycles overwrite each other | RR + locks / optimistic versioning / `SELECT FOR UPDATE` |
  | Write skew | Two transactions read overlapping sets and write disjoint ones, breaking a joint invariant | **Only true Serializable**; Snapshot Isolation does not prevent it; needs PG SSI |
  | Read skew | Reads see an inconsistent snapshot across concurrent commits | Snapshot Isolation / RR |

**Pass criteria:** p99 and error rate meet SLOs at target load; no races under `-race`/DST; idempotency and lock conflict paths behave correctly; the chosen isolation level is proven safe for business invariants; soak shows no leaks.

### Layer 3: Faults and chaos

**Goal: under network loss, bad input, process crashes and dependency failures, the system handles things gracefully instead of crashing or corrupting data.**

- **Chaos engineering principles:** (1) define steady-state metrics -> (2) hypothesize they hold under failure -> (3) inject real faults -> (4) **minimize blast radius** -> (5) run in production (or production-like) with abort conditions. Chaos is **a hypothesis-driven experiment**, not random destruction. Tools: Chaos Monkey, Gremlin, LitmusChaos / Chaos Mesh (K8s), AWS FIS.
- **Network fault injection:** **toxiproxy** (a proxy in front of a dependency injecting latency / down / bandwidth / timeout / slicer; ideal for integration suites, proving your timeout / retry / breaker code actually works); **`tc netem`** (kernel-level delay / loss / reordering / corruption); iptables for hard partitions.
- **Test resilience patterns for behavior, not existence:**
  - **Timeouts:** assert every outbound call has a timeout and fails fast on it (verify with toxiproxy latency).
  - **Retries:** assert exponential backoff + jitter + retry budget, retrying only idempotent / retryable errors; test the retry-storm anti-pattern.
  - **Circuit breakers:** drive the full state machine closed -> open -> half-open -> closed.
  - **Degradation / fallback:** assert a degraded but usable response instead of an error.
- **Lifecycle and protocol faults:**
  - **Client disconnects mid-request:** abort the connection mid-flight; assert the server cancels work, releases DB locks/connections, leaks nothing and does not half-commit (tests context propagation / cancellation).
  - **Graceful shutdown:** send SIGTERM; assert stop accepting -> drain within deadline -> close pools -> deregister from LB -> exit (before SIGKILL). On K8s test `preStop` + `terminationGracePeriodSeconds` + readiness flip to verify zero-downtime deploys.
  - **Backpressure / queue overflow:** assert bounded queues shed load instead of OOM.
- **Bad input and fuzzing:**
  - **Malformed input:** oversized payloads, wrong content-type, truncated bodies, invalid UTF-8, deeply nested JSON (billion laughs / decompression bombs), unexpected nulls, Unicode edge cases. Assert **clean rejection, never a crash or hang**.
  - **Fuzzing:** Go `go test -fuzz`, libFuzzer + sanitizers, AFL++, Atheris (Python), cargo-fuzz (Rust); at the API layer **Schemathesis** (OpenAPI-driven) / RESTler (stateful REST).
  - **Boundaries and edges:** off-by-one (min-1 / min / min+1 / max+-1), empty / null, NaN / +-Inf, integer overflow, time zones / DST / leap years / Y2038, emoji / combining characters. Use equivalence partitioning + boundary value analysis, and let PBT automate the search.

**Pass criteria:** steady-state metrics recover under every injected fault class; all resilience patterns verified by behavior; client disconnects leave no leaks and no half-commits; graceful shutdown drops zero requests; all malformed input rejected cleanly; fuzzing finds no crashes or hangs.

### Layer 4: Security

**Goal: resist OWASP Top 10 class attacks and reach the target ASVS level.**

- **Target verification level:** most apps handling sensitive data default to **ASVS L2** (recommended default); L1 is the floor for any app; critical systems (high-value finance / healthcare / critical infrastructure) go to L3. Verify item by item across the 14 ASVS chapters (architecture / authentication / session / access control / input validation / cryptography / logging / data protection / communications / malicious code / business logic / files and resources / API / configuration), using the OWASP WSTG as the how-to.
- **OWASP Top 10 (2021), item by item:** A01 Broken Access Control (#1) / A02 Cryptographic Failures / A03 Injection (incl. XSS) / A04 Insecure Design / A05 Security Misconfiguration / A06 Vulnerable and Outdated Components / A07 Identification and Authentication Failures / A08 Software and Data Integrity Failures (incl. deserialization + supply chain) / A09 Security Logging and Monitoring Failures / A10 SSRF.
  - **For LLM products, also cover the OWASP LLM Top 10:** LLM01 prompt injection, LLM02 sensitive information disclosure, LLM06 excessive agency. Directly relevant to agent-driven products.
- **Highest-yield targets: access control (A01) + authentication (A07):**
  - **IDOR/BOLA:** as user A, request user B's object id; assert 403/404, not the object. Test vertical escalation (a member calling owner-only write routes) and horizontal escalation (reading a peer's data). **The viewer's role must be derived server-side, never trusted from the client**; every write route enforces ownership.
  - **Mass assignment:** the client stuffs `role: admin` into the body; assert it is ignored.
  - **Authentication:** brute-force lockout, JWT handling (`alg=none` attacks, weak signing keys, missing expiry, tokens in URLs, no rotation on privilege change), refresh-token rotation and revocation, account enumeration (differential responses / timing), cookie flags (HttpOnly / Secure / SameSite).
- **Injection (A03) + SSRF (A10):**
  - **SQLi:** parameterized queries are the cure (review raw ORM queries such as Prisma `$queryRaw` specifically); detect with sqlmap / Semgrep taint rules.
  - **XSS:** output encoding + a strong CSP. React escapes by default, but test `dangerouslySetInnerHTML` and URL/href sinks; sanitize unavoidable HTML with DOMPurify.
  - **SSRF:** feed internal / metadata URLs (`http://0.0.0.0/`, localhost, private ranges) to every server-side fetch; assert an allowlist + blocking of link-local / metadata + DNS-rebinding protection. **Highly relevant to products with outbound fetch tools.**
  - **Command injection / path traversal:** no shell interpolation; use argument arrays. Feed `../` to file APIs.
- **Abuse, rate limiting and transport:**
  - **Rate limiting / anti-automation:** verify per-user / per-IP / per-key limits. Expensive endpoints (LLM calls, image generation, signup, password change, OTP) must be throttled and quota-limited. Test burst vs sustained, distributed-key bypass, and that **limits are enforced server-side** (not just in the UI). **Especially critical for LLM products:** one abusive account can burn real model spend; test the cost/quota guards.
  - **TLS:** enforce TLS 1.2+ (prefer 1.3), disable weak ciphers, HSTS, valid chain; scan with testssl.sh / SSL Labs; verify certificate auto-renewal (e.g. certbot) keeps working.
  - **Security headers:** CSP, HSTS, `X-Content-Type-Options: nosniff`, `frame-ancestors`, `Referrer-Policy`; scan with ZAP baseline / Observatory.
- **Four quadrants of scanning tools:**
  - **SAST** (static): Semgrep ("important only" for high confidence), CodeQL (heavy interprocedural taint), gosec / Bandit / Brakeman.
  - **DAST** (dynamic, black box): OWASP ZAP (baseline + active scan), Burp Suite, Nuclei.
  - **SCA** (dependency CVEs, maps to A06): Trivy, Grype, Dependabot / Renovate, `npm audit` / `pip-audit` / `govulncheck`; produce an SBOM (CycloneDX / SPDX via Syft) and sign with Sigstore / cosign (maps to A08).
  - **Secret scanning:** gitleaks, trufflehog (scan **full git history**, not just HEAD), with both pre-commit and CI gates.
- **Shift-left CI/CD gate order:** pre-commit (gitleaks / format) -> PR (Semgrep SAST + Trivy SCA + secret scan) -> build (SBOM + signing) -> staging (ZAP / Nuclei DAST) -> periodic (deep CodeQL + pen test + fuzzing). Normalize output to **SARIF** for aggregation and dedup; gate on **severity + confidence** (high-confidence high-severity blocks, the rest become tickets) to avoid alert fatigue that gets scanners disabled.

**Pass criteria:** all items at the target ASVS level pass; no unfixed high-confidence high-severity issues in any Top 10 category; all access-control escalation tests are denied; zero leaked secrets; no unfixed high-severity dependency CVEs; expensive endpoints have quota guards.

### Layer 5 (cross-cutting): Observability verification (logs can track, monitoring reflects state in real time)

**Goal: prove that the logging and monitoring built in §3 actually work. "We deployed a logger and a dashboard" does not count. The bar is: every situation is recorded faithfully, key metrics change with the real state in real time, and alerts fire and clear.** Best practice is to **weave this layer into the first four**: as you run each scenario, also assert that it left the right trace in logs, metrics and alerts. You can also run a dedicated "observability game day".

- **Verify logs can track every situation** (for each event class produced by Layers 1-4: normal business, concurrency conflicts, injected faults, rejected attacks, go back and check the logs):
  - **It was recorded:** the event produced structured logs at the expected level with the expected fields (structured output can be asserted directly in tests: capture stdout and assert JSON fields).
  - **It can be stitched end to end:** logs carry a complete `trace_id` that retrieves every log line for the request, **including async/queue hops** (test one cross-queue request specifically and confirm the consumer's `trace_id` matches the producer's).
  - **Errors are reproducible:** error-branch logs carry full stack + cause chain + stable error code + context.
  - **Redaction actually works (test it actively):** deliberately push a fake password / fake card number / token through the flow, then grep the log store and **assert zero plaintext persisted**. This is the item most likely to blow up in production and must be verified actively.
- **Verify monitoring tracks key metrics and reflects system state in real time:**
  - **Metrics move with the real state:** when you generate the corresponding load or fault, the metrics backend shows the expected change: inject 500s -> error rate rises; inject latency -> p99 rises; stop a business action -> the corresponding KPI drops; saturate a resource -> saturation rises. Check every key metric (four golden signals + key KPIs) one by one; don't assume it is wired correctly.
  - **Alerts fire and clear:** when a threshold / burn rate is crossed, the alert **actually fires**, and after recovery it **actually resolves**. **Test alert rules like code**: for Prometheus, unit-test rules with `promtool test rules`, rather than discovering in production that a rule is wrong and never fires.
  - **The dead man's switch works:** deliberately stop the heartbeat / scraper and assert the "signal missing" alert fires, proving "the monitoring itself died" is detectable (otherwise silent failures go unnoticed).
  - **Rehearse the root-cause path once:** starting from an alert, follow exemplar / `trace_id` to the trace, then to the logs; walk the metric -> trace -> log pivot end to end, so the main troubleshooting path is known to work before a real incident.

**Pass criteria:** every event class from Layers 1-4 can be fully reproduced from logs via `trace_id` (including async hops); active redaction tests confirm zero plaintext; every key metric changes faithfully with real load/faults; alert rules are verified (via `promtool test rules` or equivalent) to fire and to resolve; the dead man's switch is verified; the alert-to-root-cause pivot has been rehearsed at least once.

---

## 5. Launch and operations rules

- **Releases:** small, frequent, reversible. Use immutable releases (build + config, unique ID); blue-green / canary / rolling, with rollback in seconds.
- **Back up before high-risk operations** (see `docs/principles/backups-and-risk.md`: **back up only for irreversible risk**: production deploys, DB schema migrations, destructive operations, auth/deploy-path changes. Reversible changes under git need no backup). Write the backup and the recovery path **before executing**.
- **DB migrations:** **additive** changes only + test locally first + back up first; avoid destructive migrations. Deploy code compatible with both old and new schema first, then migrate data, then remove old columns (expand-contract).
- **Observability ready at launch:** four-golden-signal dashboards + burn-rate alerts + aggregated structured logs + distributed tracing.
- **Blameless postmortems:** assume everyone acted in good faith with the information they had; focus on **systemic root causes**; produce systemic action items with owners (not "be more careful next time").
- **Game days:** regularly rehearse fault injection and recovery procedures to prove that "recovers from failure on its own" is real.
- **Control toil:** automate work that is manual, repetitive, automatable and grows linearly with scale, so operational burden does not grow linearly with users.

---

## 6. Definition of Done: pre-delivery self-check

For a production-grade delivery, every item below must be answerable with "yes":

**Design**
- [ ] SLIs/SLOs (with error budget) written down, and pass/fail defined from them?
- [ ] Services stateless and horizontally scalable? State pushed to shared backends?
- [ ] Consistency model chosen deliberately? Strong consistency only for invariants that require it?
- [ ] Every cross-boundary call has a timeout + bounded retry (backoff + jitter) + circuit breaker + dedicated connection pool (bulkhead)?
- [ ] A **predefined degradation ladder** for each critical path? Features classified critical / non-critical, with non-critical failures unable to take down critical paths? Each fallback explicitly fail-open or fail-closed? Degraded states observable (WARN + metric)? Kill switches on expensive features?
- [ ] Idempotency keys on mutating operations? Isolation level proven safe for business invariants?
- [ ] STRIDE threat model done? Least privilege, no static credentials, defense in depth?
- [ ] Four golden signals + structured logs + tracing built in from day one?

**Logging and monitoring**
- [ ] **Log traceability (mandatory):** structured JSON + uniform field schema? `trace_id` generated at the edge, propagated via W3C Trace Context, **carried across async/queue boundaries**? Given one error log line, can `trace_id` retrieve every log and the trace for the whole request?
- [ ] ERROR carries full stack + cause chain + stable error code + context? Logged once at the handling boundary (no log-and-throw)? 4xx not logged as ERROR?
- [ ] Zero leakage of secrets / tokens / PII / full card numbers and CVV (source + pipeline redaction)? Log retention capped? Audit log separate, tamper-evident, long retention?
- [ ] **Monitoring (if the client needs it):** instrumented once with OTel; covers host (USE) / service (RED) / business KPIs / dependencies / synthetic / RUM / tracing, aligned with the four golden signals? No high-cardinality label explosion?
- [ ] Alerts symptom-based + SLO multi-window multi-burn-rate? Tiered + deduped + runbook attached? **Dead man's switch** on critical jobs and on the alerting pipeline?

**Testing (all four layers pass + observability verification)**
- [ ] **L1 Business:** acceptance criteria all green; mutation testing healthy on critical modules?
- [ ] **L2 Concurrency:** p99 / error rate meet SLOs at target load; no races under `-race`; idempotency / lock conflict paths correct; isolation level proven safe; soak shows no leaks?
- [ ] **L3 Chaos:** steady state recovers after injected faults; client disconnects leave no leaks or half-commits; graceful shutdown drops zero requests; malformed input rejected cleanly; fuzzing finds no crashes?
- [ ] **L4 Security:** target ASVS level reached; no high-confidence high-severity Top 10 issues; escalation tests all denied; zero leaked secrets; no high-severity dependency CVEs; quotas on expensive endpoints?
- [ ] **L5 Observability verification:** every event class fully reproducible from logs via `trace_id` (including async); active redaction tests show zero plaintext; key metrics change faithfully with real state; alert rules verified to fire and resolve; dead man's switch verified; alert-to-root-cause pivot rehearsed?

**Operations**
- [ ] Releases reversible, with rollback in seconds? High-risk operations backed up with a written recovery path?
- [ ] Dashboards + burn-rate alerts live?
- [ ] Graceful shutdown + health checks (separate liveness/readiness) in place?

> **Self-check questions:** Would this pass code review by the tech lead? Under network loss, concurrency, bad input and attack, will it avoid crashing, losing data and leaking secrets? When anything goes wrong, can I locate the root cause from logs and monitoring within minutes? Every "yes" needs evidence (test output, scan reports, load-test curves, log/alert screenshots), not "it should be fine".

---

## Appendix: the whole thing in one paragraph

> **Stability** comes from designing for failure (timeouts / circuit breakers / degradation / backpressure). **Reliability** comes from measurability (SLOs / error budgets / four golden signals) + idempotency + the right consistency choices. **Scalability** comes from statelessness + horizontal scaling + capacity planning. **Security** comes from modeling at design time (STRIDE) + defense in depth + shift-left scanning across four quadrants. **Operability** comes from fully traceable logs threaded by `trace_id` + monitoring with full coverage and fast response, so any incident can be followed from alert to root cause in one path. None of these are pre-release checklist items; they are constraints present from the first line of design.

See also: `docs/playbooks/ai-project-playbook.md` (process for agent-run client builds), `docs/playbooks/ai-coding-pitfalls.md` (failure modes of AI-written code), `docs/playbooks/client-handover.md`.
