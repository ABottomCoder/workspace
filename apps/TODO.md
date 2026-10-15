# TODO

## Claim registry — only free apps can be taken (decided 2026-10-02, not built)

Problem: two machines running the same app split its messages at random, and nothing stops it
today (`botdock up` only catches a second listener on the same machine).

Agreed design:
- A Slack channel `#botdock` holding a **Slack canvas** with one row per app:
  name · status (idle / in-use) · holder · what it's being used for · since.
  A canvas, not a message: a message can only be edited by its author, a canvas by every member.
- No bots in the channel. People edit it with their own accounts; the bot tokens are not used.
- Start: the session's Claude reads the canvas through the user's own Slack connection. Not idle →
  refuse and say who holds it, for what, since when. Idle → mark the row in-use (user, purpose,
  time) as the user, read it back to confirm, then start.
- Stop: `botdock down`, then mark the row idle.
- A session that died without releasing stays "in-use" with its start time; a person resets it by
  hand. Taking over a held app needs the user's explicit confirmation, never silent.
- No Slack connection in the session → Claude asks the user to edit the canvas by hand.
- RULES.md needs a narrow exception: posting through a human's Slack connection is forbidden for
  bots, except editing this registry, which is the user's own action.
- Accepted risk: two claims in the same second can both succeed; the read-back after writing
  catches most of it. Atomic alternative (DynamoDB conditional write) rejected: every colleague
  would need AWS credentials.

Open: confirm the channel name, then create channel + canvas and seed the six current apps.
The canvas is the only list of apps — the repo holds no per-app files (decided 2026-10-02).

## Remotes (pending names from Hong)
Company remote (Bitbucket `example`?) as `origin`, plus a private personal GitHub mirror pushed in
the same `git push` via an extra push URL. The mirror stays invisible to colleagues: remotes live
only in local `.git/config`. Commit author must be the company identity, never a personal email.

## Live trial
Needs a free Slack app — every registered app is in use. Create a test app from
`templates/manifest.yaml`, then run the full start → DM → reply → stop cycle.
