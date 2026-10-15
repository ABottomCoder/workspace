---
name: feedback_evidence_required
description: Conclusions require verified evidence — never report from code/doc reading alone
metadata:
  type: feedback
---
Never present a conclusion based solely on reading code or docs. "I read the code and it does X" is a lead, not proof — run it, curl it, check the dashboard, query the data, and show the output. Have a concrete proof (command output, screenshot, log, repro) for every key finding. **Why:** the worst failure mode is a confidently-wrong assertion. **How to apply:** pre-assert self-check — "what did I EXECUTE or OBSERVE for this?"; if the answer is "I read it", tag `⚠️ unverified` or go verify. See [[feedback_verification_no_ask]].
