# Adapter: Bitbucket Cloud

**Detect:** `bitbucket.org` in remotes or `~/.ssh/config`; `ssh -T git@bitbucket.org` prints the account.

**Access:** REST `https://api.bitbucket.org/2.0` with an Atlassian API token (scoped) via basic auth
`<atlassian-email>:<token>`, or a workspace/repository access token as `Authorization: Bearer`.
(App passwords are being phased out; prefer API tokens.) Store as `.secrets/bitbucket-token`, read
it in the request without echoing it.

**Read-only discovery:**
```bash
B=https://api.bitbucket.org/2.0
curl -s -u "$EMAIL:$TOKEN" "$B/user" | jq -r .display_name
curl -s -u "$EMAIL:$TOKEN" "$B/workspaces?pagelen=100" | jq -r '.values[].slug'
curl -s -u "$EMAIL:$TOKEN" "$B/repositories/<ws>?pagelen=100&sort=-updated_on" \
  | jq -r '.values[] | [.slug,.mainbranch.name,.updated_on,.description] | @tsv'
curl -s -u "$EMAIL:$TOKEN" "$B/workspaces/<ws>/members?pagelen=100" | jq -r '.values[].user.display_name'
curl -s -u "$EMAIL:$TOKEN" "$B/repositories/<ws>/<repo>/branching-model"   # Git Flow prefixes, dev/prod branches
```
Follow `.next` for pagination. Load `$TOKEN` from the secrets file inside the same command.

**Note:** many Bitbucket teams use Git Flow with `develop` as the PR target; read the
branching model per repo and record it, never assume `main`.

**Clone:** `git clone git@bitbucket.org:<ws>/<repo>.git business/<co>/<repo>`.

**Token to ask for if missing:** API token with scopes `read:user:bitbucket`,
`read:workspace:bitbucket`, `read:repository:bitbucket`, `read:pullrequest:bitbucket`
(add `read:project:bitbucket` for projects).
