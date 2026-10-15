---
name: feedback_no_secret_in_output
description: Never use shell text tools on a credentials file; parse in a script and print only derived facts
metadata:
  type: feedback
---

**Never run a command that can echo the contents of a credentials file.** Not `cut`, `grep`, `head`, `awk`, `sed` or `cat`, not even to "just list the key names".

**Why:** `cut -d= -f1 <creds>` was once used to list key names. The file held a multi-line PEM private key; PEM body lines contain no `=`, so `cut` printed each one verbatim, the live key landed in the (permanently retained) transcript, and it had to be rotated. `cut -d=` only does what you want on well-formed single-line `k=v` input, and a creds file is exactly where that assumption fails.

**How to apply:** parse the file in a script and print only derived facts: key names via an explicit `split('=', 1)` inside a `try`, counts, string lengths, booleans. When a check genuinely needs the value (does this key load? is it non-empty? does the app's own parser survive the file?), compute the verdict and print the verdict. Treat "list the keys in this file" as a task needing a parser, not a one-liner. See `docs/reference/secrets-and-credentials.md`.
