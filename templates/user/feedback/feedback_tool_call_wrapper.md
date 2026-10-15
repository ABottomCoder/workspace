---
name: feedback_tool_call_wrapper
description: Malformed tool calls come from a wrong opening wrapper token, not from payload size
metadata:
  type: feedback
---

Repeated malformed tool calls were caused by emitting a bare word in place of the correct opening wrapper tag before the invoke element. The call then renders as literal text in the transcript, nothing executes, and the user has to notice and report it.

**Why the obvious diagnosis is wrong:** the first theory blamed long shell heredocs. It was incomplete. The same failure occurred on a no-argument tool call, on a script-evaluation call, and on a one-line navigation call. Payload size and tool type are not the trigger.

**How to apply:** before every tool call, emit the correct opening wrapper tag first, then the invoke block. Never begin a tool-call block with a bare identifier. When the user reports a malformed call, just re-issue it correctly — one sentence at most, no post-mortem; the fix is the retry.

Writing long multi-line text to a file and referencing it from a short command (`git commit -F /tmp/msg.txt`) is still good practice for readability, but it is not the fix for this bug.
