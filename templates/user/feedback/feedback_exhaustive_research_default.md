---
name: feedback_exhaustive_research_default
description: Default to exhaustive research; never ask "research more or proceed?"
metadata:
  type: feedback
---
When a decision would benefit from more investigation, do the exhaustive research by default — do NOT ask the user "should I research first, or proceed?". Fan out parallel subagents per source, then surface only genuine judgment calls. **Why:** the answer to that question is always "research thoroughly first". See [[feedback_research_before_asking]], [[feedback_evidence_required]], [[feedback_subagent_economy]].
