# Ticket-system adapter: GitHub Issues

Instance values (host, org, repos, project boards, label scheme) live in `business/<co>/stack.md`.

## Recognise
- ID: `#<n>` within a repo, or `<org>/<repo>#<n>`. URL: `https://<host>/<org>/<repo>/issues/<n>`.
- Ticket dir name: `<repo>-<n>` (e.g. `tickets/api-123/`) so IDs from different repos don't collide.

## Access
- `gh` CLI authenticated to the host (`gh auth status`). Interactive login (`gh auth login --web`) is
  run by the human; tokens are fed via `--with-token` from a temp file, never on the command line.
- For a self-hosted host set `GH_HOST`, or run from inside a clone: outside a repo, `-R owner/repo` can
  fall back to the public host and return 404 for a repo you can see.
- Some CLIs check classic token scopes and reject fine-grained tokens with equivalent permissions;
  note which type works.

## Fetch
`gh issue view <n> -R <org>/<repo> --json title,body,state,assignees,labels,comments,milestone,url`

| Standard field | Field |
|---|---|
| Title / description / status | `title` / `body` / `state` (+ project board column if used) |
| Assignee | `assignees[].login` |
| Priority, type | labels (per business label scheme) |
| Acceptance criteria | a section of `body` (task list) |
| Comments | `comments[]` |
| Links | cross-references in body/comments, `gh issue develop --list <n>` for linked branches |

## Search
`gh search issues "<key noun>" --repo <org>/<repo>`; `gh issue list -R <org>/<repo> --label <l> --state all`.

## Write (with authorisation)
- `gh issue comment <n> -R <org>/<repo> --body-file <file>` (body from a file, not inline).
- `gh issue edit` for labels/assignees; `gh issue close` with a closing comment.
- PRs link issues with `Fixes #<n>` in the PR body.

## Gotchas
- Closing via `Fixes #n` only happens when the PR merges into the default branch.
- Project-board fields (status, iteration) are separate from issue state; read them via `gh project`
  if the team works from the board.
