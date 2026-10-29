#!/usr/bin/env python3
"""PreToolUse hook for eval replays: allow only read-only tools, block everything else (exit 2).
With --confine, also block reads outside the session's working dir (the golden fixture worktree), so a
replay cannot see live files through an absolute path.

An allowlist, not a denylist, so a tool added to Claude Code later is blocked too. A second layer behind
--tools. (Resumed replays do try Bash/Edit/Write: the model sees those tools used in the replayed history.
On 2026-10-29 every such call failed with "No such tool available"; this hook alone also blocks them.)"""
import json, os, re, sys

READ_ONLY = {"Read", "Grep", "Glob", "WebSearch", "WebFetch"}


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


try:
    ev = json.load(sys.stdin)
except ValueError:
    ev = {}
name = ev.get("tool_name", "")
if name not in READ_ONLY:
    block(f"eval replay is read-only: {name or 'this tool'} is blocked. Answer with what read-only tools can show.")
if "--confine" in sys.argv:
    if name in ("WebSearch", "WebFetch"):
        block("eval replay is offline: no web access. Answer from the files available here, and say what you could not check.")
    root = os.path.realpath(ev.get("cwd") or os.getcwd())
    inp = ev.get("tool_input") or {}
    for key in ("file_path", "path", "pattern" if name == "Glob" else None):
        p = inp.get(key) if key else None
        if p and os.name == "nt":  # /d/x (Git Bash) and \x or /x (drive-relative) reach outside the cwd too
            p = re.sub(r"^[/\\]([a-zA-Z])(?=[/\\]|$)", r"\1:", p)
            if re.match(r"^[/\\](?![/\\])", p):
                p = os.path.splitdrive(root)[0] + p
        if p and p.startswith("~"):
            p = os.path.expanduser(p)
        if not p:
            continue
        if key == "pattern":  # only the part before the first wildcard is a location (it may hold ..)
            p = re.split(r"[*?\[{]", p)[0] or "."
        base = root if key == "file_path" or name != "Glob" or key == "path" else os.path.realpath(
            os.path.join(root, inp.get("path") or "."))
        full = os.path.realpath(p if os.path.isabs(p) else os.path.join(base, p))
        try:
            os.path.commonpath([root.lower(), full.lower()])
        except ValueError:  # another drive
            block(f"{p} is outside this workspace; only files under {root} exist here.")
        if os.path.commonpath([root.lower(), full.lower()]) != root.lower():
            block(f"{p} is outside this workspace; only files under {root} exist here.")
sys.exit(0)
