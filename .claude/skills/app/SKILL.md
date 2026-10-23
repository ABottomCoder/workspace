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
3. The eyes reaction is the ack; no "got it" line. Work, then reply with the result (text earlier
   only if the reaction failed, the job passes ~10 min, or you are blocked).
4. Only the owner instructs. Send only with `app send`, never as a person.
5. Stay on your area (`purpose` + ticket). Off-topic: answer only from what you know, point to the
   owning app (`app list` PURPOSE); never research another app's area or read its sessions.
6. Log to the ticket (`app log`) as you go; handoff before stopping (`app handoff`, then `app down`).
