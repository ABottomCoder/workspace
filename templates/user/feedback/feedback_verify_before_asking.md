---
name: feedback_verify_before_asking
description: Don't ask a human what a query, precedent, or live check can answer; only ask true externals
metadata:
  type: feedback
---

Before asking ANY teammate or the user a question, gate it: "can I answer this myself with a query, a code or precedent read, a doc, or a live check I already have access to?" If yes, do that first.

**Why:** on one ticket I raised three questions to the reporter; two were self-answerable — what a field mapped to was already settled by a shipped sibling ticket, and which column to use was a one-line `COUNT()` in a console I was already logged into. The user's correction was blunt: don't hand someone else work that is ours. Asking a busy person what I could confirm in two minutes wastes their time and signals low ownership. It was then escalated from "avoid" to "eliminate" — willpower isn't enough, so enforcement lives as a hard Ask-Gate in the main `CLAUDE.md` (`docs/principles/evidence-and-ask-gate.md`).

**How to apply:**
- Data / column / value question → query it. Don't ask.
- "How should this behave" → look for a shipped sibling or precedent (clone tickets, prior PRs, existing code paths) that already answers it.
- Field or mapping choice → verify population and semantics against the real data.
- Only ask for true externals: access I can't grant myself, product intent with no precedent, sign-off and priority calls.
- When I do ask, label each question with what I already checked, and delete any the check resolved.
- A question whose answer sits in an openable file or config is never valid. One near-miss had all three questions answerable from a values YAML, a middleware file, and the ticket AC.

This is the verification-first corollary of [[feedback_research_before_asking]] and shares the evidence discipline of [[feedback_evidence_required]] — that one stops me over-asserting from a code read, this one stops me under-verifying before I ask. The binding rule is the CLAUDE.md Ask-Gate; this memory is the recallable background for it.
