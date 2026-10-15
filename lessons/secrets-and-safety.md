# Secrets and safety

Handling credentials, keeping secrets out of transcripts and shared places, and checking that security controls actually constrain what they claim to.

### Never run a text tool on a credentials file; give sub-agents an exact safe usage
**Mistake:** `cut -d= -f1` on a credentials file to "list the key names" printed every line of a multi-line PEM private key (PEM body lines have no `=`); separately, a sub-agent told "never print the token" inspected the token file with awk and dumped it. Both secrets had to be rotated.
**Root cause:** Used content-printing tools on a file whose only purpose is holding secrets, and forbade printing without giving a safe way to use or check the file.
**Rule:** Never run `cat`/`cut`/`grep`/`head`/`awk`/`sed`/`wc -c` on a credentials file or echo variables holding a secret. Parse it in a script and print only derived facts: key names via `split('=', 1)` inside a `try`, counts, lengths, booleans; if a check needs the value, print the verdict, never the input. Use `test -s FILE` to check existence, and consume secrets inline (e.g. `-H "Authorization: Bearer $(cat FILE)"` inside the command, or an existing script). Give sub-agents exactly that usage in their brief. Side note: hand-rolled `k=v` loaders often crash on multi-line values, so folded single-line keys (literal `\n`) may be required.
**Seen:** 3

### A share, output or sync folder is a publication channel
**Mistake:** A full production env file (DB password, JWT secrets, encryption key, private keys, live payment key) sat for two months in a cloud-synced folder shared "anyone with the link", while the agent carefully redacted its own doc in the same folder without asking who the folder was shared with.
**Root cause:** Scoped the risk to "does my file contain secrets" and missed "what is the destination".
**Rule:** Before writing into any output/share/sync folder, check its sharing (drive permissions, repo `.gitignore`/remote). Secret files never go there, redacted or not; keep them in a local 700/600 dir or not at all. When taking over a "put things in a shared place" task, scan what is already there for key patterns (`sk_live_`, `PRIVATE KEY`, `AKIA`, connection strings with credentials). Rotating an encryption-at-rest key requires decrypt-then-re-encrypt, never plain replacement.
**Seen:** 1

### Do not certify a file secret-free with a keyword grep
**Mistake:** A compose file was declared safe to commit because a `PASSWORD|SECRET|KEY|TOKEN` grep returned nothing; it held a live cache password inside a connection URL, a command flag and a healthcheck.
**Root cause:** Searched for a secret's label instead of its shape, then reported a negative search as proof.
**Rule:** Read the whole file and look for shapes: `scheme://user:pass@host`, `--requirepass`/`--password` flags, `Authorization:` values, long high-entropy strings, `BEGIN` key blocks. A file too long to read is not certifiable. When the answer gates someone's irreversible action, say exactly what you checked.
**Seen:** 1

### Redact all common secret shapes when reading event streams
**Mistake:** A redaction filter for reading chat events missed a cloud API key, which printed into the transcript.
**Root cause:** The pattern only knew a few key formats.
**Rule:** When reading message events, redact at least `AQ\.[A-Za-z0-9._-]{20,}`, `AIza[0-9A-Za-z_-]{30,}`, `xox[abp]-`, `ghp_`, `AKIA`, `sk-`, JWT `eyJ`, and password fields. Prefer sed-redacting over `grep -v` so the rest of the message stays readable.
**Seen:** 1

### Enumerate existing effective privilege before building a restriction
**Mistake:** Built and thoroughly tested a scoped sudo helper, but the account already had `NOPASSWD:ALL` from a file a cloud agent writes by default, so `sudo su` bypassed it.
**Root cause:** Verified the new control, not the surface it was meant to constrain.
**Rule:** Acceptance is "what can this identity do now": check `sudo -l -U <user>`, groups, all of `/etc/sudoers.d/`, and any agent that manages accounts (SSM, cloud-init), before and after, and again across a service restart. Grep effective config with comments stripped.
**Seen:** 1

### Keep substitution placeholder tokens only on their assignment line
**Mistake:** A secret placeholder token was mentioned in an explanatory comment in an env file; the substitution tool replaced it there too, writing the plaintext secret into a harmless-looking comment.
**Root cause:** Treated a placeholder as inert documentation; a substituted token is live text wherever it appears.
**Rule:** Put placeholder tokens only on the line they are meant to fill. In comments and prose, refer to them descriptively, never by the literal token.
**Seen:** 1
