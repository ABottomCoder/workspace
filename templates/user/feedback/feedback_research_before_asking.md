---
name: feedback_research_before_asking
description: Exhaust self-service before asking a human
metadata:
  type: feedback
---
Before asking a teammate or the user, exhaust self-service: read the code → the ticket + comments → wiki search → chat history → git history (`git log --grep`, `git blame`) → local docs → try it yourself (curl the endpoint). Check live systems when the question touches deploy/infra/secrets. **How to apply:** when you must ask, lead with what you found; never ask what's answerable in-repo; batch related questions. To teammates, ask only for actions needing their permissions/decisions, not for info you can retrieve.
