---
name: app
description: Run this session as a chat app (bot) by name — "use slack_helper to run this session", "start app helper", "stop the app". Takes over a configured app under business/*/apps/, keeps it listening, and follows the app conduct rules.
---

# Run an app

The procedure lives in `apps/README.md` → "Take over an app"; conduct in `apps/RULES.md`. Read both
now, then follow the steps. Non-negotiables while running:

1. Both ends are `run_in_background` Bash tasks of this session (`app run` unless the service is
   installed; `wait-event.sh <co>/<id>` always). Never a trailing `&`.
2. Every wake: re-arm `wait-event.sh` **first**, then `app inbox`, `app read`, reply in-thread.
   Exit code 3 = the app was deaf: re-read conversations and tell the owner.
3. Conduct is `apps/RULES.md` (ack = the reaction §4, owner-only instructions §2, own area §10);
   re-read it after a compaction rather than relying on a summary.
4. Log to the ticket (`app log`) as you go; handoff before stopping (`app handoff`, then `app down`).
