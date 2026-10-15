# Memory index

> **SIZE GUARD: hard limit 25 KB / 200 lines.** Past it the index silently stops loading (no error,
> just no memory). Check `wc -c -l MEMORY.md` after adding a line; when tight, compress superseded
> rows first and keep live entries.
>
> One line per memory: `[title](file.md) — one-line hook`. Never put memory content here.
> Memory holds only what fits nowhere else: preferences and feedback about how to work, and
> pointers. Business facts → `business/<co>/`; project state → the project `DEVDOC.md`;
> generic lessons → `lessons/`.
>
> Seeding (install script or by hand): copy this file and `templates/user/feedback/*.md` flat into `user/memory/`,
> except the tombstone `feedback_use_subagents.md` (kept in templates only, to record why that rule reversed).

## User
- [profile](../profile.md) — identity, languages, communication preferences

## Feedback (how to work)

*Evidence and verification*
- [Conclusions require verified evidence](feedback_evidence_required.md) — run or observe it; a code read is a lead, not proof
- [Verification to the max, don't ask](feedback_verification_no_ask.md) — do all verification proactively
- [Run read-only queries directly](feedback_run_readonly_queries_directly.md) — measure instead of infer; only cost needs approval
- [Run read-only tests without asking](feedback_run_readonly_tests_without_asking.md) — non-impacting probes that inform a decision: run, report

*Research and asking*
- [Research before asking](feedback_research_before_asking.md) — exhaust code, docs, history, self-test first
- [Verify before asking](feedback_verify_before_asking.md) — only ask true externals
- [Exhaustive research is the default](feedback_exhaustive_research_default.md) — never ask "research more or proceed?"
- [Commit history first](feedback_research_strategy.md) — git log before full diffs

*Communication*
- [Short messages to people](feedback_short_messages.md) — one purpose, no inline evidence, ≤120 words for findings
- [No dashes / no AI tells](feedback_no_em_dashes.md) — outbound messages read as typed by a person
- [Check before sending](feedback_check_before_sending.md) — read the latest messages first
- [Explicit permission before sending](feedback_explicit_permission_before_sending.md) — only "send it" for this draft unlocks a post
- [Product output in the working language](feedback_product_english_only.md) — chat language is a convenience

*Execution*
- [Subagent economy](feedback_subagent_economy.md) — delegate only when payoff exceeds overhead; never self-verification
- [Tool-call wrapper hygiene](feedback_tool_call_wrapper.md) — malformed calls come from a bad opening token
- [No secrets through shell text tools](feedback_no_secret_in_output.md) — parse in a script, print derived facts
- [No UI edits that bypass PR review](feedback_no_ui_bypass_pr.md) — config as code via PR
- [Self-review past sessions](feedback_self_review_sessions.md) — detached reviewer, high evidence bar

## Pointers
- <one line per pointer to a business/project file that a cross-business session must find>
