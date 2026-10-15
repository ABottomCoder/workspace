# Secrets and Credentials

How secrets are stored, shared and rotated. Read whenever a task obtains, shares, stores or rotates a
credential. The company's approved tools (password manager, runtime secret store, large-file transfer)
are named in `business/<co>/stack.md`.

## Where secrets live in this framework

- **`business/<co>/.secrets/`**: directory mode 700, files mode 600, gitignored. One file per secret or
  per app (`.secrets/apps/<channel>_<name>.env`). Created by onboarding when a token is first provided.
- Docs, memory, logs and tickets reference secrets **by name and location only**
  (`.secrets/<file>`, `<secret-manager> item X`, `<runtime store> path Y`), never by value.
- Personal (non-business) credentials: the OS keychain or `user/.secrets/` with the same modes.
- The framework repo's pre-commit guard (`tools/guard/`) blocks token patterns (`xox*`, `ghp_`, `AKIA…`,
  private-key blocks), any path under `user/` or `business/`, and the denylist kept in `user/`.
- A keychain-backed store may be added later as a parallel variant.

```
mkdir -p business/<co>/.secrets && chmod 700 business/<co>/.secrets
umask 077; printf '%s' "$TOKEN" > business/<co>/.secrets/<name>   # value never echoed to the transcript
```

## Which tool for what

| Need | Use |
|---|---|
| Share a password, API key, private key or `.env` with a teammate | the company's **password manager** (item share link or team collection) |
| Transfer a large file | the approved large-file transfer service, never for credentials |
| Secrets consumed by an app at runtime | the **runtime secret store**; never hardcoded, never committed |
| Paste a credential into chat, a ticket, a doc or a commit | ❌ never, not even in a DM, not even partially redacted |

Record where the policy came from (who announced it, when). Superseded habits stay visible in old chat;
don't cite pre-policy behaviour as precedent.

## Behaviour rules

- Need a secret from a teammate → ask them to share it **via the password manager**, naming the channel.
- **Never type the user's credentials yourself**, including into an automated browser; hand the login to
  the human, resume once authenticated.
- **Assume local transcripts are permanent** (this framework keeps them forever in `user/sessions/`).
  Never `cat`/`grep`/`cut` a credentials file: parse it in a script and print only derived facts (key
  present, length, account, a hash).
- Never certify a file as secret-free by keyword search. Read the whole file for secret *shapes*:
  `scheme://user:pass@host`, `--password`/`--requirepass` args, `Authorization:` values, long
  high-entropy strings, `BEGIN … KEY` blocks. A file too long to read is too long to certify.
- Short-lived tokens (daily session tokens) may be cached in `.secrets/` with their expiry noted; on a
  401/403, ask the approver for a fresh one.
- **Suspected exposure** (pasted in chat, committed, echoed into a transcript, readable by the wrong
  people): say so immediately and arrange rotation; a quiet exposure is worse than an awkward one.
  Encryption keys that protect stored data are **decrypt-then-re-encrypt**, never simply replaced
  (replacing destroys everything encrypted with the old key).

## Account setup (capture per company in the business stack file)

1. How to request an account (company email, official use).
2. Install order (some managers want the browser extension before first login).
3. **Which identity provider authenticates it**, and which one does *not*; multiple SSO/MFA systems are
   the usual cause of failed logins.
4. On-network vs off-network behaviour.
5. Team collections: you only see the ones you were added to; only their managers can share them (a
   short chat request naming the collection is usually faster than a support ticket). Record item
   *names*, never values.
6. Not-a-member vs lost-access: a first sign-in asking for a recovery secret you never had means you're
   not in the tenant yet; the fix is the account request, not recovery.
7. Shared-account tools whose access-request system grants nothing: the credential is in the team collection.

## Rotating a runtime secret

**Before:** know who receives the new value (an owner distribution list you may not be on); expect the old
value to die immediately; enumerate every consumer from the catalog *and* the code and diff them (every
environment, compute platforms with their own secret scopes, scheduled jobs, per-consumer variable names).

**Stale copies hide:** an uncatalogued orphan with plausible names; a different secret under a generic name
in the same entry (confirm which account a key belongs to by its full identifier); consumers that disagree
(the disagreement shows which copy is stale).

**Doing it:** validate the new value (format, then one cheap identity call) before propagating; write every
store entry first, then restart; restart only what reads secrets at startup and only what you updated, one
at a time, validating between; scheduled jobs re-read on the next run, so verify that run; enumerate
regions/accounts rather than assuming one; read the API response, not the UI toast.

**Verify in layers:** the credential works (identity call + one read proving permissions) → workloads
actually rolled → no auth errors in consumer logs since the rotation, paired with a positive control on the
same query → the next scheduled run succeeds → audit views lag, so no change there isn't failure.

**Close out:** update last-rotated dates; announce completion to consumers' owners; delete temporary keys
and decrypted plaintext once dependents validate; never broadcast the new value; write down the process
gaps you hit. Rotation is an irreversible-risk change: follow the
[high-risk protocol](../principles/backups-and-risk.md#high-risk-protocol-for-the-left-column).
