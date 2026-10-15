# Adapter: GitLab (gitlab.com or self-managed)

**Detect:** `gitlab.com` / self-managed host in remotes or `~/.ssh/config`; `glab` installed; `ssh -T git@<host>` greets an account.

**Access:** `glab` CLI (`glab auth status`), else REST `https://<host>/api/v4` with header
`PRIVATE-TOKEN: <token>` from `.secrets/gitlab-token`.

**Read-only discovery:**
```bash
glab api user | jq -r .username
glab api 'groups?min_access_level=10&per_page=100' | jq -r '.[].full_path'
glab api 'groups/<group>/projects?include_subgroups=true&per_page=100&order_by=last_activity_at' \
  | jq -r '.[] | [.path_with_namespace,.default_branch,.last_activity_at,.ssh_url_to_repo] | @tsv'
glab api 'groups/<group>/members/all?per_page=100' | jq -r '.[] | [.username,.access_level] | @tsv'
glab api 'projects/<id>/repository/files/CODEOWNERS?ref=<branch>'   # also .gitlab/CODEOWNERS
```

**Note:** GitLab uses *merge requests*, often different branch conventions; record per-repo
deviations in `stack.md`. Subgroups map to deep paths; record local dir vs remote path when they differ.

**Clone:** `git clone <ssh_url_to_repo> business/<co>/<project>`.

**Token to ask for if missing:** personal or group access token with `read_api` + `read_repository`
(add `read_user` for the profile). Store as `.secrets/gitlab-token`.
