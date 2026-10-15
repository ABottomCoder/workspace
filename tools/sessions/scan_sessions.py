#!/usr/bin/env python3
"""
Incremental session scanner for intervention tracking (lazy mode).

Deterministic extraction only, NO judgment about "was the agent wrong?". It writes compact
per-session digests that the agent then reads to judge errors and update the stats and tracking
files (skill: .claude/skills/scan-sessions).

Paths (no hardcoding; <main> = two levels above this script):
  transcripts: --proj <dir> | $CC_TRANSCRIPT_DIR | <main>/user/sessions (if it has *.jsonl)
               | ~/.claude/projects/<encoded main dir>   (encoding: tools/lib/cc-internals.sh)
  output:      --out <dir>  | $INTERVENTION_OUT  | <main>/user/intervention

Usage:
    python3 tools/sessions/scan_sessions.py            # scan new/changed sessions
    python3 tools/sessions/scan_sessions.py --all      # force re-scan everything
    python3 tools/sessions/scan_sessions.py --list     # just list what would be scanned

Outputs:
    <out>/digests/<sessionId>.md   compact digest per session
    <out>/.scan_state.json         {sessionId: line_count} already processed

Categories: `// fix:[<category>]` markers in user turns; keys as in docs/process/intervention-tracking.md
(change them there, here and in the scan-sessions skill together). To accept localised
labels, put {"<label>": "<key>"} in <out>/aliases.json.
"""
import json, sys, os, glob, re, subprocess
from datetime import datetime, timezone

CATEGORIES = ("requirements", "approach", "implementation", "testing", "tooling")
FIX_RE = re.compile(r'//\s*fix:\[([^\]]+)\]', re.IGNORECASE)
MAIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.path.join(MAIN, "tools", "lib", "cc-internals.sh")


def cc(fn, *args):
    """Claude Code internals live in one shell helper; ask it instead of re-implementing."""
    return subprocess.run(["bash", CC, fn, *args], capture_output=True, text=True, check=True).stdout.strip()


def resolve_paths(args):
    def flag(name):
        if name in args:
            i = args.index(name)
            if i + 1 < len(args):
                return args[i + 1]
        return None

    out = flag("--out") or os.environ.get("INTERVENTION_OUT") or os.path.join(MAIN, "user", "intervention")
    proj = flag("--proj") or os.environ.get("CC_TRANSCRIPT_DIR")
    if not proj:
        local = os.path.join(MAIN, "user", "sessions")
        proj = local if glob.glob(os.path.join(local, "*.jsonl")) else cc("transcript_dir", MAIN)
    return proj, out


def load_aliases(out):
    p = os.path.join(out, "aliases.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def load_state(state_file):
    if os.path.exists(state_file):
        return json.load(open(state_file))
    return {}


def save_state(state_file, out, s):
    os.makedirs(out, exist_ok=True)
    json.dump(s, open(state_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def text_of(content):
    """Flatten a message.content (str or list of blocks) to plain text + tool names."""
    if isinstance(content, str):
        return content, []
    texts, tools = [], []
    if isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text":
                texts.append(b.get("text", ""))
            elif t == "tool_use":
                tools.append(b.get("name", "?"))
            elif t == "tool_result":
                pass  # skip bulky results
    return "\n".join(texts), tools


def scan_file(path, start_line=0):
    """Return dict with extracted fields, scanning from start_line onward."""
    user_turns = []
    asst_snips = []
    tool_counts = {}
    fix_markers = []
    title = custom = None
    branch = None
    first_ts = last_ts = None
    line_no = 0

    with open(path, errors="replace") as fh:
        for line in fh:
            line_no += 1
            if line_no <= start_line:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            typ = o.get("type")
            if typ == "custom-title":
                custom = o.get("customTitle") or custom
            if typ == "ai-title":
                title = o.get("aiTitle")
            if o.get("gitBranch"):
                branch = o.get("gitBranch")
            ts = o.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            msg = o.get("message")
            if typ == "user" and isinstance(msg, dict):
                content = msg.get("content")
                txt, _ = text_of(content)
                if txt.strip():
                    user_turns.append(txt.strip())
                    for m in FIX_RE.finditer(txt):
                        fix_markers.append(m.group(1).strip())
            elif typ == "assistant" and isinstance(msg, dict):
                txt, tools = text_of(msg.get("content"))
                for t in tools:
                    tool_counts[t] = tool_counts.get(t, 0) + 1
                if txt.strip():
                    asst_snips.append(txt.strip())

    return {
        "title": custom or title, "branch": branch,
        "first_ts": first_ts, "last_ts": last_ts,
        "user_turns": user_turns, "asst_snips": asst_snips,
        "tool_counts": tool_counts, "fix_markers": fix_markers,
        "end_line": line_no,
    }


def fmt_ts(ts):
    if not ts:
        return "?"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


def trunc(s, n):
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "…"


def write_digest(digests, sid, d, aliases):
    os.makedirs(digests, exist_ok=True)
    norm = [aliases.get(c, c).lower() for c in d["fix_markers"]]
    real_fix = [c for c in norm if c in CATEGORIES]
    lines = []
    lines.append(f"# Session {sid}")
    lines.append("")
    lines.append(f"- **Title:** {d['title'] or '(none)'}")
    lines.append(f"- **Branch:** {d['branch'] or '(none)'}")
    lines.append(f"- **Time:** {fmt_ts(d['first_ts'])} → {fmt_ts(d['last_ts'])}")
    lines.append(f"- **User turns:** {len(d['user_turns'])}")
    tc = ", ".join(f"{k}×{v}" for k, v in sorted(d['tool_counts'].items(), key=lambda x: -x[1]))
    lines.append(f"- **Tools:** {tc or '(none)'}")
    lines.append(f"- **`// fix:` markers (real):** {', '.join(real_fix) if real_fix else '(none)'}")
    lines.append("")
    lines.append("## Conversation flow (user turns, truncated)")
    lines.append("")
    for i, ut in enumerate(d["user_turns"], 1):
        lines.append(f"{i}. **U:** {trunc(ut, 280)}")
    lines.append("")
    lines.append("## Assistant text snippets (truncated, for context)")
    lines.append("")
    for i, a in enumerate(d["asst_snips"][:40], 1):
        lines.append(f"- {trunc(a, 200)}")
    path = os.path.join(digests, f"{sid}.md")
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path, len(real_fix)


def main():
    args = sys.argv[1:]
    force = "--all" in args
    list_only = "--list" in args

    proj, out = resolve_paths(args)
    digests = os.path.join(out, "digests")
    state_file = os.path.join(out, ".scan_state.json")

    if not os.path.isdir(proj):
        print(f"transcript dir not found: {proj}")
        print("Pass --proj <dir> or set CC_TRANSCRIPT_DIR.")
        return

    state = {} if force else load_state(state_file)
    aliases = load_aliases(out)

    files = sorted(glob.glob(os.path.join(proj, "*.jsonl")))
    new_or_changed = []
    for path in files:
        sid = os.path.basename(path)[:-6]
        total = sum(1 for _ in open(path, errors="replace"))
        seen = state.get(sid, 0)
        if total > seen:
            new_or_changed.append((sid, path, seen, total))

    if list_only:
        print(f"proj: {proj}")
        print(f"out:  {out}")
        print(f"{len(new_or_changed)} session(s) new/changed:")
        for sid, _, seen, total in new_or_changed:
            print(f"  {sid}  (+{total-seen} lines, {seen}->{total})")
        return

    summary = []
    for sid, path, seen, total in new_or_changed:
        d = scan_file(path, start_line=0)
        dpath, nfix = write_digest(digests, sid, d, aliases)
        state[sid] = d["end_line"]
        summary.append((sid, d, dpath, nfix))

    save_state(state_file, out, state)

    print(f"Scanned {len(summary)} new/changed session(s). Digests in {digests}/\n")
    for sid, d, dpath, nfix in summary:
        print(f"• {sid}")
        print(f"    title: {d['title'] or '(none)'}")
        print(f"    {fmt_ts(d['first_ts'])} | {len(d['user_turns'])} user turns | fix markers: {nfix}")
        print(f"    digest: {dpath}")
    if not summary:
        print("(nothing new — all sessions already scanned)")


if __name__ == "__main__":
    main()
