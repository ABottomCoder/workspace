# <Ticket / feature name>

> Spec-driven template for **non-trivial** work (3+ steps, schema or prod changes, anything you
> want a checkpoint on). Skip it for obvious one-line fixes. Fill it in BEFORE touching code.
> Keep it tight: a thinking tool, not paperwork. If implementation diverges from the plan, stop,
> re-plan, and update this file.

## 1. Spec — what and why (stable intent)

- **Problem / user story:** who hits this, what they want, why now.
- **In scope:** the specific behaviour being built.
- **Out of scope:** what we are explicitly NOT doing.
- **Acceptance criteria** — every one testable (a command, a request, an observable UI state):
  - [ ] …
  - [ ] …

## 2. Plan — how (flexible implementation)

- **Approach:** the chosen design in 2–4 sentences; name the runner-up and why it lost.
- **Touched files / modules:** repo + path per change.
- **Decision Ladder check** (`docs/principles/decision-ladder.md`): does it need to exist, does it
  already exist, can it be reused, is this the shortest working diff?
- **Risk and blast radius:** prod? schema migration? destructive? new secret? If yes, fill §4.

## 3. Tasks — small, independently testable

- [ ] Task — *verify by:* <test / request / UI check>
- [ ] Task — *verify by:* …

## 4. Safety — only for irreversible-risk changes

Skip for reversible work (git-tracked code, docs, small features you can `git revert`). Fill in
**before executing** when the change carries irreversible risk: prod deploy, schema migration,
destructive op, secret, shared-infra change you cannot cleanly roll back
(`docs/principles/backups-and-risk.md`).

- **Backup taken:** path + timestamp, verified (file count / checksum / restore test).
- **Recovery path:** exact steps to revert (git range, restore command, down-migration).
- **Authorisation:** who approved it, with source (`people.md` → Authority).

## 5. What actually shipped (fill in after; becomes the audit trail)

- Commits / PRs, deploy steps run, verification evidence, deferred follow-ups.
- Mirror one line into `LOG.md` and the project `DEVDOC.md` change log.
