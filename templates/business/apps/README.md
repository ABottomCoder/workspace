# Apps — <Business name>

One directory per app (bot) this business runs: `apps/<channel>_<name>/` (e.g. `slack_helper`).
The app framework code lives in the main dir `apps/`; read `apps/RULES.md` before running one.

```
apps/<channel>_<name>/
├── app.yaml        channel kind, listen filters, owner, allowlist (from apps/templates/app.yaml)
└── .runtime/       logs, offsets, owner, .session-id (gitignored, never edit by hand)
```

Credentials: `.secrets/apps/<channel>_<name>.env` (mode 600). Apps have no persona.

| App | Channel | Purpose | Owner |
|---|---|---|---|
| | | | |
