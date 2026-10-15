# Adapter: GitHub (github.com or GitHub Enterprise)

**Detect:** `github.com` / GHE host in remotes or `~/.ssh/config`; `gh` installed; `ssh -T git@github.com` greets an account.

**Access:** `gh` CLI (preferred; `gh auth status`), else REST `https://api.github.com` with a token
from `.secrets/github-token` (`Authorization: Bearer`). GHE: `gh --hostname <host>` / `https://<host>/api/v3`.

**Read-only discovery:**
```bash
gh api user --jq .login
gh api user/orgs --jq '.[].login'
gh repo list <org> --limit 200 --json name,description,defaultBranchRef,pushedAt,isArchived,primaryLanguage,sshUrl
gh api orgs/<org>/members --paginate --jq '.[].login'          # needs read:org
gh api orgs/<org>/teams --jq '.[] | [.slug,.name] | @tsv'       # needs read:org
gh api repos/<org>/<repo>/contents/CODEOWNERS --jq .content     # base64; also .github/CODEOWNERS
gh api repos/<org>/<repo>/branches/<default>/protection          # may 404 without admin; skip
```

**Clone:** `git clone git@github.com:<org>/<repo>.git business/<co>/<repo>` (or the SSH alias).

**Token to ask for if missing:** fine-grained PAT scoped to the org, **read-only**: Contents,
Metadata, Pull requests, Issues (read); org permission Members (read). Classic PAT fallback:
`repo` (needed for private repos, note it is broader than read) + `read:org`.
Store as `.secrets/github-token`.
