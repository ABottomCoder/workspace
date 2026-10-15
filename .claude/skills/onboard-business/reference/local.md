# Local discovery (read-only, no questions)

Print names, hosts and states only. Never print key material, token values or credential files.

| What | Command | Keep |
|---|---|---|
| Git identity | `git config --global --get-regexp '^(user|url|credential)\.'` | name, email, URL rewrites, credential helper name |
| Per-dir identities | `git config --global --get-regexp '^includeif'` | which dirs use which identity |
| SSH hosts | `grep -iE '^\s*(host|hostname|user|identityfile)\s' ~/.ssh/config` | alias → host → key *path* (not contents) |
| Keys present | `ls ~/.ssh/*.pub` | which hosts have a key |
| Key works? | `ssh -T git@<host>` (github/gitlab/bitbucket print the account and exit) | account name per host |
| CLIs | `command -v gh glab bb jira acli aws gcloud az kubectl terraform docker slack` | installed list |
| CLI login state | `gh auth status`, `glab auth status`, `aws sts get-caller-identity`, `gcloud auth list`, `az account show` | account / org names |
| MCP servers | `claude mcp list` (also `.mcp.json` in the main dir) | server names and transport, no env values |
| Env var names | `env | cut -d= -f1 | grep -iE 'token|key|jira|atlassian|slack|github|gitlab|bitbucket|aws|gcp|azure'` | names only |
| Existing clones | `find ~ -maxdepth 4 -name .git -type d -prune 2>/dev/null` then `git -C <dir> remote get-url origin` | dir → remote; match against the business's hosts/orgs |
| Existing business dir | `ls business/<co>/ 2>/dev/null` | create vs refresh mode |

Classify each finding by system (VCS host, ticket system, chat, wiki, cloud). A remote URL or SSH
alias naming the business is the strongest signal of which org belongs to it; confirm in Step 3
rather than assuming every org on a shared account belongs to this business.
