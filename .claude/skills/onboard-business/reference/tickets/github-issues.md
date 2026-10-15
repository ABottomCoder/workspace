# Adapter: GitHub Issues / Projects

**Detect:** the VCS is GitHub and repos have issues enabled (`hasIssuesEnabled`) with recent activity,
or the org uses GitHub Projects.

**Access:** same as `vcs/github.md` (`gh`).

**Read-only discovery:**
```bash
gh repo list <org> --limit 200 --json name,hasIssuesEnabled --jq '.[] | select(.hasIssuesEnabled) | .name'
gh issue list -R <org>/<repo> --state all --limit 50 --json number,title,state,assignees,labels,updatedAt
gh label list -R <org>/<repo>                       # labels often encode type/priority/area
gh project list --owner <org>                        # needs read:project
gh project item-list <n> --owner <org> --limit 50 --format json
```

**Infer:** ticket ID form (`#123` or `<repo>#123`; the ticket dir is `<repo>-123`), which labels
mean bug/feature, who triages.

**Token scopes if missing:** fine-grained: Issues (read), Metadata (read); Projects needs
classic `read:project`. Creating or commenting on issues is outward-facing: approver only.
