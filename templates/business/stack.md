# Stack — <Business name>

> Systems this business uses and how to reach them. Secrets are referenced by **name** only
> (`.secrets/<name>`), never by value.

## Ticket system

- **System:** <Jira / GitHub Issues / Linear / internal> · adapter: `docs/process/tickets/<system>.md`
- **URL pattern:** <https://example.atlassian.net/browse/{id}> · **Prefixes:** <ABC->
- **Fetch method:** <MCP server name / CLI / REST + `.secrets/<token-file>`>

## VCS

- **Host:** <github.com / gitlab.com / bitbucket.org / self-hosted> · **Org/workspace:** <org>
- **Auth:** <SSH key alias / CLI login / `.secrets/<token-file>`>
- **Branching model:** <Git Flow / trunk-based> · **Default base branch:** <main/develop>
- **Branch convention:** <ABC-{id}-description> · **PR convention:** <ABC-{id} description>
- **Project state policy:** <in-repo `docs/HANDOFF.md` | orphan branch `state/<user>` | local `DEVDOC.md`> (`tools/work/README.md` → Project state policy; orphan branch only if the company allows personal branches)
- **Merge methods:** <feature → develop squash; release → main merge commit>
- Per-repo deviations: in the repo table below and that project's `CLAUDE.md`.

| Repo | Local dir | Remote | Base branch | Purpose |
|---|---|---|---|---|
| | `business/<co>/<project>/` | | | |

## Chat

- **Tool:** <Slack / Teams / …> · **Workspace:** <name> · **Access:** <MCP server / app token `.secrets/apps/<channel>_<name>.env`>

## CI/CD and environments

| Environment | URL / host | Deploys from | How to deploy | Who may deploy |
|---|---|---|---|---|
| dev | | | | |
| prod | | | | |

## Cloud and infra

- <provider, account alias, region, CLI profile name — no keys>

## MCP servers and CLIs

| Name | Used for | Auth | Notes |
|---|---|---|---|
| | | | |

## Wiki / docs

- <Confluence space / Notion / Google Drive folder>

## Secrets (names only)

| Secret file | What it is | Scopes | Owner / rotation |
|---|---|---|---|
| `.secrets/<name>` | | | |
