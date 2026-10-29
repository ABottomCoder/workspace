#!/usr/bin/env python3
"""
Per-day session extractor for the journal and intervention tracking.

Deterministic extraction only, NO judgment about "was the agent wrong?". Every run re-reads all
transcripts (a full pass takes seconds) and rebuilds one compact extract per finished local day
that had conversation: user and assistant text only, tool calls/results and injected context
dropped, obvious secrets redacted. A worker (tools/sessions/journal-catchup.sh) reads an extract
and writes that day's journal entry and judged errors.

Paths (no hardcoding; <main> = two levels above this script):
  transcripts: --proj <dir> | $CC_TRANSCRIPT_DIR | <main>/user/sessions (if it has *.jsonl)
               | ~/.claude/projects/<encoded main dir>   (encoding: tools/lib/cc-internals.sh)
  output:      --out <dir>  | $INTERVENTION_OUT  | <main>/user/intervention
  journal:     --journal <dir> | <main>/user/logs/journal   (YYYY-MM.md, one "## YYYY-MM-DD" per day)

Usage:
    python3 tools/sessions/scan_sessions.py              # rebuild extracts, print a one-line summary
    python3 tools/sessions/scan_sessions.py --pending    # rebuild, then print days still to judge
                                                        # (no journal entry or no errors file), oldest first

Outputs:
    <out>/days/YYYY-MM-DD.md    compact extract of that day (may contain conversation content)
    <out>/days/index.json       {day: {"sessions": n, "user_msgs": n, "chars": n}}

Days are local dates of the message timestamps, not file times: a session that spans days lands in
each day it was active. Today is never extracted (it is not over). Lines copied into another
transcript (fork, resume) are counted once.

Categories: `// fix:[<category>]` markers in user turns; keys as in docs/process/intervention-tracking.md
(change them there, here, in journal-day.md and in intervention_stats.py together).
"""
import glob, hashlib, json, os, re, subprocess, sys
from datetime import datetime

CATEGORIES = ("requirements", "approach", "implementation", "testing", "tooling")
MAIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.path.join(MAIN, "tools", "lib", "cc-internals.sh")
NOISE = re.compile(r"<(system-reminder|local-command-stdout|local-command-caveat|command-message|"
                   r"task-notification|pasted_content[^>]*)>.*?</\1>", re.S)
SECRETS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\b(sk-ant-[\w-]{10,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}"
               r"|xox[abposr]-[\w-]{10,}|xapp-[\w-]{10,}|AKIA[0-9A-Z]{16}|AIza[\w-]{30,}"
               r"|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,})"),
    re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)(\s*[:=]\s*)(\"[^\"]+\"|'[^']+'|\S+)"),
]
USER_CAP, ASSIST_CAP, LAST_CAP = 1500, 800, 3000


def cc(fn, *args):
    """Claude Code internals live in one shell helper; ask it instead of re-implementing."""
    return subprocess.run(["bash", CC, fn, *args], capture_output=True, text=True, check=True).stdout.strip()


def flag(args, name, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def resolve_paths(args):
    out = flag(args, "--out") or os.environ.get("INTERVENTION_OUT") or os.path.join(MAIN, "user", "intervention")
    proj = flag(args, "--proj") or os.environ.get("CC_TRANSCRIPT_DIR")
    if not proj:
        local = os.path.join(MAIN, "user", "sessions")
        proj = local if glob.glob(os.path.join(local, "*.jsonl")) else cc("transcript_dir", MAIN)
    journal = flag(args, "--journal") or os.path.join(MAIN, "user", "logs", "journal")
    return proj, out, journal


def redact(s):
    s = SECRETS[0].sub("[REDACTED]", s)
    s = SECRETS[1].sub("[REDACTED]", s)
    return SECRETS[2].sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", s)


def texts(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def local(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()


def binding(proj, sid):
    p = os.path.join(proj, ".bindings", sid)
    if not os.path.exists(p):
        return None
    for line in open(p, encoding="utf-8", errors="replace"):
        if line.startswith("target="):
            return line[7:].strip()
    return None


def collect(proj, today):
    """{day: {sid: {"title", "work", "msgs": [(ts, role, body)]}}} for finished days."""
    days, seen = {}, set()
    for path in sorted(glob.glob(os.path.join(proj, "*.jsonl"))):
        sid = os.path.basename(path)[:-6]
        title = None
        per_day = {}
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"custom-title"' in line or '"ai-title"' in line:
                    try:
                        o = json.loads(line)
                        title = o.get("customTitle") or title or o.get("aiTitle")
                    except ValueError:
                        pass
                    continue
                if '"type":"user"' not in line and '"type":"assistant"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                role = o.get("type")
                if role not in ("user", "assistant") or o.get("isMeta") or o.get("isSidechain") or not o.get("timestamp"):
                    continue
                body = NOISE.sub("", texts((o.get("message") or {}).get("content"))).strip()
                if not body:
                    continue
                t = local(o["timestamp"])
                day = t.strftime("%Y-%m-%d")
                if day >= today:
                    continue
                key = (o["timestamp"], role, hashlib.sha1(body.encode("utf-8")).hexdigest())
                if key in seen:
                    continue
                seen.add(key)
                per_day.setdefault(day, []).append((t.strftime("%H:%M"), role, redact(body)))
        work = binding(proj, sid)
        for day, msgs in per_day.items():
            days.setdefault(day, {})[sid] = {"title": title, "work": work, "msgs": msgs}
    return days


def cap(s, n):
    return s if len(s) <= n else s[:n] + " …"


def render(day, sessions):
    n_user = sum(1 for s in sessions.values() for m in s["msgs"] if m[1] == "user")
    out = [f"# {day} · {len(sessions)} session(s) · {n_user} user message(s)", ""]
    for sid, s in sorted(sessions.items(), key=lambda kv: kv[1]["msgs"][0][0]):
        head = f"## session {sid[:8]} · {s['title'] or '(untitled)'}"
        if s["work"]:
            head += f" · work: {s['work']}"
        out += [head, ""]
        last_a = max((i for i, m in enumerate(s["msgs"]) if m[1] == "assistant"), default=-1)
        for i, (hhmm, role, body) in enumerate(s["msgs"]):
            limit = USER_CAP if role == "user" else (LAST_CAP if i == last_a else ASSIST_CAP)
            out.append(f"[{hhmm}] {'U' if role == 'user' else 'A'}: {cap(body, limit)}")
        out.append("")
    return "\n".join(out), n_user


def journal_days(journal):
    done = set()
    for p in glob.glob(os.path.join(journal, "*.md")):
        for line in open(p, encoding="utf-8", errors="replace"):
            m = re.match(r"## (\d{4}-\d{2}-\d{2})\b", line)
            if m:
                done.add(m.group(1))
    return done


def main():
    args = sys.argv[1:]
    proj, out, journal = resolve_paths(args)
    if not os.path.isdir(proj):
        print(f"transcript dir not found: {proj}\nPass --proj <dir> or set CC_TRANSCRIPT_DIR.")
        sys.exit(1)
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    days_dir = os.path.join(out, "days")
    os.makedirs(days_dir, exist_ok=True)

    index, changed = {}, 0
    for day, sessions in sorted(collect(proj, today).items()):
        text, n_user = render(day, sessions)
        index[day] = {"sessions": len(sessions), "user_msgs": n_user, "chars": len(text)}
        p = os.path.join(days_dir, f"{day}.md")
        old = open(p, encoding="utf-8").read() if os.path.exists(p) else None
        if old != text:
            open(p, "w", encoding="utf-8", newline="\n").write(text)
            changed += 1
    json.dump(index, open(os.path.join(days_dir, "index.json"), "w", encoding="utf-8"), indent=1)

    if "--pending" in args:
        logged = journal_days(journal)
        errs = os.path.join(out, "errors")
        for day in sorted(index):
            if day not in logged or not os.path.exists(os.path.join(errs, f"{day}.json")):
                print(day)
    else:
        total = sum(v["chars"] for v in index.values())
        print(f"{len(index)} day(s) with conversation before {today}, {total // 1000}k chars; {changed} extract(s) written to {days_dir}")


if __name__ == "__main__":
    main()
