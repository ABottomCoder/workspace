#!/usr/bin/env python3
"""Check (and fix) a session's name against the convention <Desc>_<app>_<n>.

<app> is the app id the session holds (business/*/apps/<id>/.runtime/.session-id), else `None`.
Desc has no underscores. A wrong or missing app part is fixed by appending a custom-title record
to the transcript (the mechanism `/rename` uses; see tools/lib/cc-internals.sh), keeping Desc.

  name_check.py [--fix] [--hook]   session id from the hook's stdin JSON (--hook) or
                                   $CLAUDE_CODE_SESSION_ID / $CLAUDE_SESSION_ID
--hook prints SessionStart JSON (additionalContext) and only when something changed or needs the
user; otherwise prints one plain line. Never fails the caller: errors exit 0 with a note.
"""
import glob, json, os, re, sys

ROOT = os.environ.get("WORK_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.environ.get("CC_PROJECTS_BASE") or os.path.expanduser("~/.claude/projects")
TDIR = os.path.join(BASE, re.sub(r"[^A-Za-z0-9]", "-", ROOT))   # cc_encode_path
NAME = re.compile(r"^([A-Za-z0-9.-]+)_(None|[a-z0-9-]+_[a-z0-9][a-z0-9-]*)_(\d+)$")


def title_of(tp):
    t = ""
    try:
        for line in open(tp, encoding="utf-8", errors="replace"):
            if '"custom-title"' in line:
                try: t = json.loads(line).get("customTitle", "") or t
                except ValueError: pass
    except OSError: pass
    return t


def app_of(sid):
    for f in glob.glob(os.path.join(ROOT, "business", "*", "apps", "*", ".runtime", ".session-id")):
        if open(f).read().strip() == sid:
            home = os.path.dirname(os.path.dirname(f))
            tk = os.path.join(home, ".runtime", "ticket")
            return os.path.basename(home), (open(tk).read().strip() if os.path.exists(tk) else "")
    return None, ""


def bound_target(sid):
    p = os.path.join(ROOT, "user", "sessions", ".bindings", sid)
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("target="): return line[7:].strip()
    return ""


def clean(s):   # Desc: letters, digits, dot, hyphen; words joined
    return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^A-Za-z0-9.-]+", s) if w)[:40]


def next_n(prefix):
    n = 0
    pat = re.compile(r'"customTitle":"' + re.escape(prefix) + r'(\d+)"')
    for tp in glob.glob(os.path.join(TDIR, "*.jsonl")):
        try:
            with open(tp, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"custom-title"' in line:
                        m = pat.search(line)
                        if m: n = max(n, int(m.group(1)))
        except OSError: pass
    return n + 1


def main():
    fix, hook = "--fix" in sys.argv, "--hook" in sys.argv
    sid = ""
    if hook:
        try: sid = json.load(sys.stdin).get("session_id", "")
        except ValueError: pass
    sid = sid or os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or ""
    tp = os.path.join(TDIR, sid + ".jsonl")
    if not sid or not os.path.exists(tp):
        return say(hook, "", f"[session name] transcript not found for session '{sid}'; skipped")
    title = title_of(tp)
    app, ticket = app_of(sid)
    want = app or "None"
    m = NAME.match(title)
    # A name with an app part on a session that holds no app is left alone: a rollover successor
    # starts with its predecessor's name before `app up` registers it.
    if m and (m.group(2) == want or not app):
        return say(hook, "", f"[session name] ok: {title}")
    desc = (m.group(1) if m else clean(title)) or clean(ticket) or clean(os.path.basename(bound_target(sid)))
    if not desc:
        return say(hook, "", "[session name] unnamed and not attached; name it <Desc>_<app>_<n> once routed")
    new = f"{desc}_{want}_{next_n(f'{desc}_{want}_')}"
    if not fix:
        return say(hook, f"[session name] '{title or '(none)'}' does not follow <Desc>_<app>_<n>; run /rename {new}",
                   f"[session name] should be {new} (now '{title or '(none)'}')")
    with open(tp, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "custom-title", "customTitle": new, "sessionId": sid}) + "\n")
    return say(hook, f"[session name] renamed '{title or '(none)'}' -> '{new}' (convention <Desc>_<app>_<n>). "
               f"If the terminal title does not update, tell the user once: /rename {new}", f"renamed to {new}")


def say(hook, ctx, plain):
    if hook:
        if ctx: print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
    else:
        print(plain)
    return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as e:   # a naming check must never break session start
        print(f"[session name] check failed: {e}", file=sys.stderr); sys.exit(0)
