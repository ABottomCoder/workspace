---
name: feedback_no_ui_bypass_pr
description: Never let a UI's auto-sync bypass PR review; config-as-code via PR
metadata:
  type: feedback
---
Never make changes through an ops UI whose auto-sync would bypass PR review. Make config-as-code changes on a feature branch via PR; use operational UIs read-only. **Why:** bypassing review removes the safety net. (Generalized from a pipeline-UI-auto-syncs-to-main incident.)
