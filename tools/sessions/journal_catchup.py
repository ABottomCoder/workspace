#!/usr/bin/env python3
"""
Journal catch-up: for every finished day that has conversation but no journal entry or no judged
errors yet, run a headless Claude worker (journal-day.md) on that day's extract, write the entry into
the month's journal file and the errors into <out>/errors/<day>.json, then rebuild the stats.

    python3 tools/sessions/journal_catchup.py [--max N] [--day YYYY-MM-DD ...] [--model M] [--dry-run]

--day forces those days (re-judging them); otherwise all pending days, newest first. One run at a
time (lock dir <out>/.catchup.lock, stale after 6 h). Writes <out>/.catchup_date when nothing is left
pending, so the SessionStart hook (journal-hook.sh) starts it at most once a day.
Worker: `claude -p` with no tools, no MCP, user settings only and no session persistence, from a
working dir outside the workspace: its own run is never journaled. Cost per day goes to
<out>/.worker_runs.jsonl.
"""
import glob, json, os, re, shutil, subprocess, sys, tempfile, time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_sessions as scan  # noqa: E402

SIGNALS = ("fix-marker", "user-correction", "agent-admission")
STALE_LOCK_S = 6 * 3600


def lessons_list():
    items = []
    for p in sorted(glob.glob(os.path.join(scan.MAIN, "lessons", "*.md"))) + [os.path.join(scan.MAIN, "user", "lessons.md")]:
        if not os.path.exists(p):
            continue
        stem = os.path.relpath(p, scan.MAIN).replace("\\", "/")[:-3]
        for line in open(p, encoding="utf-8", errors="replace"):
            if line.startswith("### "):
                items.append(f"{stem}: {line[4:].strip()}")
    return items


def parse_result(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in worker output")
    return json.loads(m.group(0))


def validate(day, r, lessons):
    log = r.get("log")
    if not isinstance(log, list) or not log or not all(isinstance(x, str) and x.strip() for x in log):
        raise ValueError("log must be a non-empty list of strings")
    if len(log) > 3 or sum(len(x) for x in log) > 700:  # prompt says 3 bullets / 600 chars; some slack
        raise ValueError(f"log too long: {len(log)} bullets, {sum(len(x) for x in log)} chars")
    errors = []
    for e in r.get("errors") or []:
        if e.get("category") not in scan.CATEGORIES or e.get("signal") not in SIGNALS:
            raise ValueError(f"bad category/signal: {e}")
        if e.get("lesson") not in lessons:
            e["lesson"] = None
        e["day"] = day
        errors.append({k: e.get(k) for k in ("day", "session", "time", "category", "signal", "quote", "what", "root_cause", "lesson")})
    return [x.strip() for x in log], errors


def run_worker(day, extract, lessons, model):
    prompt = open(os.path.join(HERE, "journal-day.md"), encoding="utf-8").read()
    prompt = prompt.replace("{{DAY}}", day).replace("{{LESSONS}}", "\n".join(f"- {x}" for x in lessons))
    claude = shutil.which("claude") or "claude"
    env = dict(os.environ, JOURNAL_WORKER="1")
    with tempfile.TemporaryDirectory(prefix="journal-worker-") as cwd:
        sp = os.path.join(cwd, "system.md")
        open(sp, "w", encoding="utf-8").write(prompt)
        cmd = [claude, "-p", "--no-session-persistence", "--setting-sources", "user", "--strict-mcp-config",
               "--tools", "", "--model", model, "--output-format", "json", "--system-prompt-file", sp]
        p = subprocess.run(cmd, input=extract, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f"claude exited {p.returncode}: {(p.stderr or p.stdout)[-500:]}")
    meta = json.loads(p.stdout)
    if meta.get("is_error"):
        raise RuntimeError(f"worker error: {str(meta.get('result'))[:500]}")
    return parse_result(meta.get("result", "")), meta


def write_journal(journal, day, bullets):
    os.makedirs(journal, exist_ok=True)
    path = os.path.join(journal, f"{day[:7]}.md")
    sections = {}
    if os.path.exists(path):
        cur = None
        for line in open(path, encoding="utf-8").read().split("\n"):
            m = re.match(r"## (\d{4}-\d{2}-\d{2})\b", line)
            if m:
                cur = m.group(1)
                sections[cur] = [line]
            elif cur:
                sections[cur].append(line)
    sections[day] = [f"## {day}"] + [f"- {b.lstrip('- ').strip()}" for b in bullets] + [""]
    body = [f"# Journal {day[:7]}", ""]
    for d in sorted(sections, reverse=True):
        lines = sections[d]
        while lines and not lines[-1].strip():
            lines.pop()
        body += lines + [""]
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(body))


def take_lock(out):
    lock = os.path.join(out, ".catchup.lock")
    try:
        os.mkdir(lock)
    except FileExistsError:
        if time.time() - os.path.getmtime(lock) < STALE_LOCK_S:
            return None
        os.utime(lock)  # stale: take it over
    open(os.path.join(lock, "pid"), "w").write(str(os.getpid()))
    return lock


def main():
    args = sys.argv[1:]
    proj, out, journal = scan.resolve_paths(args)
    model = scan.flag(args, "--model", "sonnet")
    limit = int(scan.flag(args, "--max", "0"))
    forced = [args[i + 1] for i, a in enumerate(args) if a == "--day" and i + 1 < len(args)]
    os.makedirs(out, exist_ok=True)

    lock = take_lock(out)
    if not lock:
        print("another catch-up is running")
        return
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, "scan_sessions.py"), "--pending", "--proj", proj, "--out", out,
                            "--journal", journal], capture_output=True, text=True, encoding="utf-8", check=True)
        pending = sorted(p.stdout.split(), reverse=True)
        todo = forced or pending
        if limit:
            todo = todo[:limit]
        print(f"{len(pending)} day(s) pending; doing {len(todo)}")
        if "--dry-run" in args:
            print("\n".join(todo))
            return
        lessons = lessons_list()
        errs_dir = os.path.join(out, "errors")
        os.makedirs(errs_dir, exist_ok=True)
        failed = streak = 0
        for day in todo:
            extract_path = os.path.join(out, "days", f"{day}.md")
            if not os.path.exists(extract_path):
                print(f"{day}: no extract (no conversation that day)")
                continue
            t0 = time.time()
            try:
                for attempt in (1, 2):  # a malformed answer (bad JSON, unknown category) is usually one-off
                    try:
                        result, meta = run_worker(day, open(extract_path, encoding="utf-8").read(), lessons, model)
                        bullets, errors = validate(day, result, lessons)
                        break
                    except ValueError as e:
                        if attempt == 2:
                            raise
                        print(f"{day}: retrying after {e}")
            except Exception as e:  # one bad day must not stop the rest; a broken worker (auth, CLI) must
                failed += 1
                streak += 1
                print(f"{day}: FAILED {e}")
                if streak >= 3:
                    print("3 failures in a row: stopping (check `claude -p` works, e.g. the login)")
                    break
                continue
            streak = 0
            write_journal(journal, day, bullets)
            json.dump({"day": day, "model": model, "errors": errors}, open(os.path.join(errs_dir, f"{day}.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            usage = meta.get("usage") or {}
            run = {"day": day, "at": datetime.now().astimezone().isoformat(timespec="seconds"), "model": model,
                   "cost_usd": meta.get("total_cost_usd"),
                   "input_tokens": sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
                   "output_tokens": usage.get("output_tokens"), "seconds": round(time.time() - t0), "errors": len(errors)}
            open(os.path.join(out, ".worker_runs.jsonl"), "a", encoding="utf-8").write(json.dumps(run) + "\n")
            os.utime(lock)
            print(f"{day}: {len(bullets)} bullet(s), {len(errors)} error(s), ${run['cost_usd']}, {run['seconds']}s")
        subprocess.run([sys.executable, os.path.join(HERE, "intervention_stats.py"), "--out", out], check=False)
        left = subprocess.run([sys.executable, os.path.join(HERE, "scan_sessions.py"), "--pending", "--proj", proj, "--out", out,
                               "--journal", journal], capture_output=True, text=True, encoding="utf-8").stdout.split()
        if not left and not failed:
            open(os.path.join(out, ".catchup_date"), "w").write(datetime.now().astimezone().strftime("%Y-%m-%d"))
        print(f"done: {len(left)} day(s) still pending, {failed} failed")
    finally:
        shutil.rmtree(lock, ignore_errors=True)


if __name__ == "__main__":
    main()
