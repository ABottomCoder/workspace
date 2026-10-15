---
name: feedback_verification_no_ask
description: Do verification work to the max, proactively; don't ask per step
metadata:
  type: feedback
---
When work involves verifying correctness/accuracy, do ALL verification that can be done — don't stop to ask "want me to verify X too?". Prefer differential verification (two independent methods diffed) + real-source cross-checks. **Why:** the worst failure mode is a confidently-wrong answer. Only pause for irreversible/outward-facing actions. See [[feedback_evidence_required]].
