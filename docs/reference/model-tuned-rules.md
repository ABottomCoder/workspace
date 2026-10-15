# Model-Tuned Rules

Rules that encode a model's weakness or strength at a point in time, not a timeless truth. Re-derive
them when the model changes instead of inheriting them; keep the **measurement habit** that produced them.

## Tombstone convention

When a model-tuned rule is reversed, don't delete it. Strike it through where it lived, add one line on
why it was right then and why it inverted, and link the replacement. A memory file that only documents a
reversed rule is named `…-SUPERSEDED` and is never seeded into a new instance. The reversal itself is the
useful knowledge.

## Current model-tuned rules

| Rule | Lives in | Tuned for | History |
|---|---|---|---|
| Subagents for wide reads, parallel work and context protection only | [subagents-and-context.md](../principles/subagents-and-context.md) | long-context models | was "delegate aggressively"; inverted when reflexive delegation cost more than it saved and delegated verification returned second-hand claims |
| Verify once, for real; no redundant self-check passes | [verification-before-done.md](../principles/verification-before-done.md) | models that self-verify unprompted | was "always double-check"; extra scaffolding caused over-verification with no accuracy gain |
| Output discipline (concise, in scope, no over-narrated corrections) | [communication.md](../principles/communication.md#output-discipline-talking-to-the-user) | models that over-narrate and drift in scope | added, not present originally |
| Context budget and compaction timing | below | a given context size and compaction behaviour | the "< 60%, compact before ~83%" figures came from one model's lossy auto-compaction |
| Tool-call hygiene | below | a specific recurring emission bug | |

## Context budget (thresholds are model-specific)

With the model where this was measured, auto-compaction fired near ~83% of the window and kept only a
fraction of detail, so the working rule was: keep the working context under ~60% and `/compact` at a
natural checkpoint. On a model with a different window or compaction behaviour, re-measure. The durable
part is model-independent: state in files, compaction at checkpoints, never relying on the transcript to
remember decisions.

## Tool-call hygiene (hard rule while the bug exists)

**Every tool call begins with the correct opening wrapper tag, immediately followed by the invoke
element. Never begin a tool-call block with a bare word.**

The failure is real and recurring: a bare identifier is emitted where the wrapper tag belongs, the call
renders as plain text, **nothing executes**, and the user has to notice. It happened on long heredocs,
no-argument calls and one-line calls alike, so payload size and tool type are not the cause, and "avoid
heredocs" is not the fix.

- Pre-emit check on every call: the block's first characters are the opening wrapper tag.
- When the user reports a malformed call: re-issue it correctly, at most one short sentence, no post-mortem.
- After sending a message through a tool, verify it landed; a malformed call silently sends nothing.
- Separate readability practice (not the fix): put long multi-line text in a file and reference it from a
  short command (`git commit -F <file>`).
