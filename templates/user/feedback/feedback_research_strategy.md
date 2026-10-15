---
name: feedback_research_strategy
description: Check git history before reading full code, to save tokens
metadata:
  type: feedback
---
Check `git log --oneline --grep=<ticket>` and read commit messages to judge relevance before reading full code diffs. **Why:** avoids wasting context/tokens on irrelevant code. See [[feedback_subagent_economy]].
