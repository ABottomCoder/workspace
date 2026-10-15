---
name: feedback_run_readonly_tests_without_asking
description: Standing authorization to run read-only / non-production-impacting measurements that inform a decision, without asking first
metadata:
  type: feedback
---

Standing rule worth establishing with the user: **run any test or measurement that does not affect the live environment and yields incremental information for a decision. Don't ask permission each time.** The principle: don't guess, let the facts speak.

**Why:** asking costs a round trip and delays the decision, while the measurement itself is free and reversible. The failure being guarded against is the opposite one, asserting a conclusion from reasoning instead of measuring it. This extends [[feedback_run_readonly_queries_directly]] and [[feedback_verification_no_ask]] from "verify your own claims" to "go get the number that decides the question".

**How to apply:** if a decision hinges on an unknown and a read-only query, API `GET`, probe, or artifact diff would settle it, run it and report the number. Session-scoped temp tables in a dev scratch schema count as non-impacting.

**Still ask before:** anything that writes to production, sends a message to a person, changes a ticket's state in a way others act on, or costs real money at scale (a full scan of a huge table). Mention the cost if it was non-trivial.
