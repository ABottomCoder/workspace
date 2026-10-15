# Kits

Self-contained tools; each has its own README (what, install, usage, config, platform notes) and
no dependency on `apps/` or `business/`. Platform support: `docs/compatibility.md`.

- [page-chat-kit](page-chat-kit/README.md): login-gated page chat (1:1 + group, uploads, SSE) answered by an agent that tails an event log and replies with `reply.js`.
- [meeting-proxy](meeting-proxy/README.md): **macOS only**. AI stand-in that listens to a video meeting and answers in a synthetic or cloned voice from a pre-written context file.
- [mcp-scaffold](mcp-scaffold/README.md): minimal remote (Streamable HTTP) MCP server template with bearer-token auth.
- [deck-tools](deck-tools/README.md): markdown deck to styled editable pptx (`render_deck.py`); Figma PDF export to editable pptx (`figma-to-pptx.py`).
- [contrast-check](contrast-check/README.md): list hex colours in a site's JS bundles that would fail text contrast (candidates, not defects).
- [slack-app-provision](slack-app-provision/README.md): create Slack apps from a manifest and read their tokens by driving a logged-in Chrome over CDP.
