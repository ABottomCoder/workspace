# TODO

## Claim registry — only free apps can be taken (designed, not built)

Problem: two machines running the same app split its messages at random; `app up` only catches a
second listener on the same machine.

Design: a chat channel holding a shared document (a Slack canvas: editable by every member, unlike
a message) with one row per app: name · status (idle / in-use) · holder · purpose · since. People
edit it with their own accounts; app credentials are not used.
- Start: the session reads the registry through the user's own chat connection. Not idle → refuse
  and say who holds it, for what, since when. Idle → mark it in-use as the user, read it back, start.
- Stop: `app down`, then mark the row idle. A dead session's row stays in-use until a person resets
  it; taking over a held app needs the user's explicit confirmation.
- No chat connection in the session → ask the user to edit the registry by hand.
- RULES.md needs a narrow exception: editing this registry through the user's connection is the
  user's own action.
- Accepted risk: two claims in the same second can both succeed; the read-back catches most.

## Channels
- Second adapter (e.g. feishu, teams) against `channels/README.md`.
- `service.linux-systemd.sh` implementation.

## Live trial
Create a test app from `channels/slack/manifest.yaml` in a test workspace and run the full
up → DM → ack → reply → handoff → down cycle on `apps/`.
