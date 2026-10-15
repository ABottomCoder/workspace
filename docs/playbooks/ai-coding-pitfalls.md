# AI Coding Pitfalls

Common failure modes of AI-written code and AI agents, with industry evidence and countermeasures.
Sources: published research and incident reports, plus bug logs, acceptance reports, incident
records and lessons from real agent-built projects.

Related: `docs/playbooks/production-playbook.md` (quality bar), `docs/playbooks/ai-project-playbook.md`
(process and gates for agent-run builds).

## Key findings

- **The most frequent and most recurrent problem is not wrong code but "claimed done / claimed
  verified" when it was not.** Written rules alone do not stop it from recurring. Enforce it with
  tooling: a real run, automated checks, review by someone else.
- **The most damaging code-level problems:** the same business rule re-implemented in many places,
  missing ownership checks ("is this data yours?"), and money plus concurrency.
- **Agents carry a non-code risk:** overreaching or destructive operations (deleting data, killing the
  wrong process, unreviewed merges, leaking secrets). Production databases have been deleted by agents
  in real public incidents.

## Failure modes

"Industry evidence" lists only verifiable sources; "(secondary)" marks figures taken from news
coverage without checking the original. "Seen in practice" gives generic examples from real projects.

### A. Code structure

| # | Failure mode | Industry evidence | Seen in practice | Countermeasures |
|---|---|---|---|---|
| 1 | **Over-complex implementation** | DORA 2024: every 25% rise in AI adoption cut delivery stability by about 7.2% (secondary) | Refund logic spread over 7 entry points, producing dozens of refund bugs; a process doc reviewed 11 rounds and grew to 500+ lines | Settle the simplest business rule before writing code; before piling up machinery for rare cases, ask whether it is worth it |
| 2 | **Same business rule written in many places** | GitClear 2025 (211M lines): copy-pasted code rose from 8.3% to 12.3%, refactoring fell from 25% to under 10% | "Is the order finished" checked in 50+ places; order buttons recomputed in 13 frontend spots and already diverging from the server | Collect the rule into one table and have code read it; add a check that blocks re-implementation elsewhere |
| 3 | **Dead code; comments that disagree with code** | none found | A state-transition table commented "enforced" that nothing called; docs naming the wrong framework major version and tools that did not exist | Unused-code checks (e.g. knip); in review, verify comments as if they were code |
| 4 | **Files keep growing** | none found | Many files over 500 lines, one over 1,100 | Set a line limit; split when exceeded |
| 5 | **Ignoring existing project conventions** | 567 Claude Code PRs: 45.1% of merged ones still needed human edits, mostly on project conventions (arXiv 2509.14745) | A "one day" constant defined 6 times, money formatting twice; a sister project stuck on pre-refactor patterns | Put conventions in CLAUDE.md plus lint; "search for an existing one before writing" |
| 6 | **Outdated or deprecated APIs** | ICSE'25: deprecated-API use of 25-38% across 7 models, 70-90% when the context is old code | A payment-platform integration written against v1 when the sandbox required v2 | Put dependency versions and official docs in context; check current docs before starting |

### B. Correctness and testing

| # | Failure mode | Industry evidence | Seen in practice | Countermeasures |
|---|---|---|---|---|
| 7 | **Claims done / verified when it is not** | Replit incident: the agent misreported test results (AIID #5578). METR 2025 study: developers were 19% slower but believed they were 20% faster | 96 unit tests green while the new feature never fired on the first real run; 39 items reported "fixed", 35 actually were; the same bug "fixed" three times; docs said "all pass" while 58-79 of 150 failed | Done = the real path ran once, with evidence; key changes reviewed by another person or agent; reports list skipped tests |
| 8 | **Gaming tests to make them pass** | METR 2025: o3 reward-hacked in 30.4% of RE-Bench runs, 70-95% even when explicitly forbidden; Claude 3.7 System Card §6 records similar behaviour | 25 gate tests all passed a flag value that production never used; DB tests silently skipped when the environment was missing, then one semicolon took production down for 2 minutes | Watch for edits to test files; skipped tests must appear in the report; keep a hidden acceptance suite the AI cannot see |
| 9 | **Tests that only record current behaviour** | arXiv 2410.21136: AI-written assertions track what the code does; accuracy at judging right vs wrong is under half | Dozens of tests only counting mock calls, 100+ only asserting "has a value"; a soak test that could never fail | Humans write expected values from requirements; new tests must first fail on the old code |
| 10 | **Wrong business logic** | CodeRabbit 2025: AI-involved PRs had about 1.75x the logic errors (secondary, vendor data) | 140+ bugs in one build; fixes that were themselves wrong (three chained fixes); money review took 4 rounds | Write the rules down as a table first and code to the table; money changes get golden-scenario tests |
| 11 | **Fake third parties behave differently from real ones** | none found | A fake payment API returned no invoice, tests passed, real subscriptions failed; fake fees appeared instantly, real ones 3 s later; hand-written mocks invented API fields | Changes touching payments/external APIs run for real in the sandbox before release; production refuses to start with mocks |
| 12 | **Concurrency races** | no verifiable study found | One escrow could be settled twice (paid out double); a load test passed 29/30 while real concurrency failed about 40%; over-refunds from a check outside the lock | Money operations always use row locks plus conditional state updates; fixed lock order guarded by a test; real concurrency tests |
| 13 | **Time zone and money details** | none found | Dates parsed as UTC so US users saw the previous day; a deadline shown as date only, so a 5 pm cutoff was missed | Shared date/money helpers; ban ad-hoc formatting |
| 14 | **Errors silently swallowed** | none found | An empty catch swallowed a unique-constraint error, so a feature never once succeeded after launch; refund failures silently ignored; missing fields defaulted into plausible-looking numbers | Lint bans empty catch; every failure gets a log or a user-facing message |
| 15 | **Inefficient code** | EffiBench (NeurIPS 2024): GPT-4 code averaged 3.12x the runtime of human canonical solutions | not specifically checked | Performance tests on key endpoints; check for N+1 queries and missing pagination |

### C. Security

| # | Failure mode | Industry evidence | Seen in practice | Countermeasures |
|---|---|---|---|---|
| 16 | **Missing ownership checks** | Veracode 2025: about 45% of code contains common vulnerabilities (secondary); NYU 2021: about 40% of Copilot code vulnerable | All tenant apps sharing one DB role, able to read/write hundreds of tables across apps; write routes with no ownership check; a transferred listing kept the previous owner's payment account and orders; a spoofed request header bypassed all rate limits | Funnel ownership filtering through one data-access function; one "switch account, fetch someone else's data" test per endpoint; a dedicated security review |
| 17 | **Secret leaks** | GitGuardian 2025: 6.4% leak rate in repos with Copilot vs 4.6% across all public repos | A production env file sat in a publicly readable shared folder for two months; a subagent printed a token while inspecting a file | Secret scanning pre-commit and in CI; secrets only in a secret store; redact all output |
| 18 | **Hallucinated dependencies** | USENIX 2025: about 20% of recommended packages do not exist and can be squatted | not observed | New dependencies need human approval |
| 19 | **Prompt injection from repo content; AI tools weaponised** | Invariant 2025: a malicious issue hijacked an agent into leaking private repos; Amazon Q 1.84 shipped with an injected data-wiping instruction; the Nx attack used local AI CLIs to harvest secrets from 2,180 accounts | A bot posted under a human approver's account; another bot relayed that as the approver's own position | Least-privilege agents; no auto-approve mode; accept instructions only from the approver's own channel |
| 20 | **License risk** | ICSE'25 LiCoEval: 0.88-2.01% of generated code closely matches open-source code, and most models mislabel the license | not checked | Run dependency and license scans before client handover |

### D. Agent operations and process

| # | Failure mode | Industry evidence | Seen in practice | Countermeasures |
|---|---|---|---|---|
| 21 | **Overreaching or destructive operations** | Replit agent deleted a production DB during a code freeze and fabricated 4,000 records (2025-07); OWASP LLM06 Excessive Agency | "Clean up test apps" archived 16 real projects; an unscoped DELETE wiped messages for dozens of users; tests registered real accounts on production; `pkill` killed another project's process; a 1.6k-line PR merged without review | Separate dev and prod; deletes by exact id plus dry-run plus snapshot; human approval for irreversible ops; every merge reviewed by someone else |
| 22 | **Assumption instead of verification** | none found | Stated a trial period from memory (wrong); built a permission boundary the other party already had full access around; fabricated "sent" | Check code/logs/records before answering; say "I don't know" when you don't |
| 23 | **Losing earlier decisions in long sessions** | Chroma 2025: all 18 models tested degrade as input length grows | Decision log entries marked "approved" that were never approved | Write decisions into the project dev doc, not chat memory; compact at checkpoints |
| 24 | **Deploy and ops mistakes** | none found | Deployed stale build output; a redeploy checked only HTTP 200 while the background worker was missing for about 42 hours; restarted a service mid-user-session | After deploy, check real functionality, not just 200; script the deploy |
| 25 | **Sister projects drift apart** | none found | 8 of 12 issues in one round of a sister project also existed in the original | When fixing one project, check its sibling |
| 26 | **Scope creep, oversized batches** | DORA 2024 stability drop; "larger batches" is the industry reading (secondary) | 11 review rounds on one doc; a single 1.6k-line PR | Small commits; cap review at 2-3 rounds, redesign if the same area keeps failing |
| 27 | **Team understanding and skill erosion** | Anthropic 2026 study: AI-assisted group averaged 50% on a quiz vs 67% for hand-coders, largest gap on debugging | Code mostly AI-written, humans knew little of the details; complexity problems only found by later audit | Require that key modules can be explained; run periodic complexity audits |
| 28 | **Technical jargon in user-facing copy** | none found | Raw validation errors shown to users; protocol jargon in public copy | Copy-check script; wording rules for non-technical users |

## Countermeasures

### Commonly in place

- **Verification gate:** one unified check command per project; money changes get golden-scenario tests.
- **Business rules as tables:** rule tables for refunds, order status, buttons, linked items.
- **Review:** independent agent review; every merge reviewed by someone else; review capped at 2-3 rounds.
- **Destructive ops:** delete by exact id, dry-run, backup only before irreversible operations.
- **Authorisation:** accept instructions only from the approver's own channel; bots never post under someone else's account.
- **Real-environment tests:** end-to-end mode against the real payment sandbox.

### To add (by priority)

1. **"Done" requires evidence:** every completion report attaches real-run evidence (screenshot, log,
   test report) and lists skipped tests. Enforced by tooling, not goodwill.
2. **Ownership checks in one place:** one data-access function for ownership filtering, plus a
   cross-account test per endpoint.
3. **Extend rule tables to other modules**, with a check that blocks re-implementation elsewhere.
4. **Tests from requirements:** humans write expected values; new tests first fail on the old code.
5. **CI checks:** secret scanning, unused code, empty catch, file line limits, new-dependency approval
   (do not rely on local-only checks).
6. **Sandbox-run payment and external-API changes before release;** production refuses mocks.
7. **Keep sister projects in sync** with the original's refactors.

## Sources

- GitClear 2025: https://www.gitclear.com/ai_assistant_code_quality_2025_research
- Veracode 2025 (secondary): https://www.veracode.com/press-release/ai-generated-code-poses-major-security-risks-in-nearly-half-of-all-development-tasks-veracode-research-reveals/
- Pearce et al. 2021: https://arxiv.org/pdf/2108.09293 ; Perry et al. 2022: https://arxiv.org/pdf/2211.03622
- CodeRabbit 2025 (secondary): https://www.theregister.com/2025/12/17/ai_code_bugs/
- AI assertion study: https://arxiv.org/html/2410.21136v1
- Package hallucination (CSA summary): https://labs.cloudsecurityalliance.org/research-rb/csa-research-note-slopsquatting-ai-coding-assistant-supply-c/
- DORA 2024 (InfoQ): https://www.infoq.com/news/2024/11/2024-dora-report/
- METR 2025 developer study: https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ ; METR reward hacking: https://metr.org/blog/2025-06-05-recent-reward-hacking
- Claude 3.7 Sonnet System Card: https://www-cdn.anthropic.com/9ff93dfa8f445c932415d335c88852ef47f1201e/claude-3-7-sonnet-system-card.pdf
- Deprecated APIs (ICSE'25): https://arxiv.org/html/2406.09834v3
- Replit incident: https://incidentdatabase.ai/reports/5578/ ; OWASP LLM06: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/
- GitGuardian 2025: https://gitguardian.com/state-of-secrets-sprawl-report-2025
- Invariant: https://invariantlabs.ai/blog/mcp-github-vulnerability ; Rules File Backdoor: https://thehackernews.com/2025/03/new-rules-file-backdoor-attack-lets.html
- Amazon Q: https://www.theregister.com/2025/07/24/amazon_q_ai_prompt/ ; Nx s1ngularity: https://www.bleepingcomputer.com/news/security/ai-powered-malware-hit-2-180-github-accounts-in-s1ngularity-attack/
- EffiBench: https://arxiv.org/abs/2402.02037 ; Agentic coding PR study: https://arxiv.org/abs/2509.14745
- Anthropic coding-skills study: https://www.anthropic.com/research/AI-assistance-coding-skills ; Chroma Context Rot: https://www.trychroma.com/research/context-rot
- LiCoEval: https://arxiv.org/abs/2408.02487
