#!/usr/bin/env python3
"""
Replay eval cases against one version of the workspace framework.

    python3 tools/eval/replay.py --rev <git rev> --cases <cases.json> [--only id,id] [--k 3]
                                 [--model M] [--tag name] [--out <dir>] [--slot n]
                                 [--patch <file>]   candidate = <rev> + patch, applied in the worktree only
    python3 tools/eval/replay.py --rev <git rev> --golden <data/golden/<version>> [--tier core|extended] ...
                                 frozen offline set: each case's world and conversation prefix are fixed copies

Each case is a fresh headless session (`claude -p`) started in a git worktree of <rev>, so that
version's CLAUDE.md, lessons, principles, skills and hooks load exactly as they would in real use.
business/ and user/ (untracked) are mirrored into it as file hardlinks, rebuilt on every run: both
versions see the same world, only the framework differs. Not directory links: Glob does not follow
junctions, so the agent would conclude user/ is missing. Heavy or private dirs are left out (MIRROR_SKIP).
Tools are read-only (Read, Grep, Glob, WebSearch, WebFetch), no MCP servers, and the session is not
persisted. Results: <out>/<tag>/<case id>.<run>.json with the final answer, the tool calls, cost and a
version fingerprint.

Eval home (WS_EVAL_HOME, default: <workspace>-eval next to the workspace, so on the same volume as hardlinks
need): worktrees/<sha> and data/runs/<tag>. Removing worktrees (`--cleanup`) deletes only hardlinks and the
checkout, never the originals.

Case file: JSON list of {"id", "prompt", ...}; other fields are for the judge (judge.py).
A case with "session" (transcript id under user/sessions/) and "cut" (UTC timestamp of the user message
to answer) replays mid-conversation: the transcript is copied up to that message into the worktree's
project dir and resumed with --fork-session, the message sent as the prompt. The stored CLAUDE.md block in
the copy is replaced by the worktree's CLAUDE.md, so no old-version text stays in context. Lesson or
principle files read earlier in that conversation keep the old text: only what is read live is versioned.
"""
import glob, hashlib, json, os, re, shutil, stat, subprocess, sys, time, uuid
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.dirname(os.path.dirname(HERE))
# All eval data lives outside the workspace, in one dir next to it: worktrees/ and data/ (cases, runs, reports)
EVAL_HOME = os.environ.get("WS_EVAL_HOME") or os.path.join(os.path.dirname(MAIN), os.path.basename(MAIN) + "-eval")
MIRRORED = ("business", "user")
EVAL_SETS = ("tools/eval/golden", "tools/eval/golden-src")  # committed portable sets: removed from a golden worktree
MIRROR_SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build", ".cache",
               ".pytest_cache", "target", "sessions", "eval", ".secrets"}
TOOLS = "Read,Grep,Glob,WebSearch,WebFetch"
NL = chr(10)
OFFLINE_TOOLS = "Read,Grep,Glob"  # golden mode: no web, the frozen world is the whole input
DENY = ["Bash", "PowerShell", "Edit", "Write", "NotebookEdit", "MultiEdit", "Agent", "Task", "Workflow", "Artifact",
        "ArtifactData", "ArtifactComments", "SendUserFile", "Skill", "ScheduleWakeup", "CronCreate", "RemoteTrigger",
        "SendMessage", "PushNotification", "EnterWorktree", "Monitor"]


class UnsafeReplay(RuntimeError):
    pass


def audit(r, where):
    """Stop everything if a non-read-only tool call ran (its result was not an error)."""
    ran = [c for c in r["calls"] if c["name"] not in TOOLS.split(",") and c.get("ok") is not False]
    if ran:
        alert = os.path.join(EVAL_HOME, "data", "ALERT-unsafe-replay.json")
        json.dump({"where": where, "calls": ran}, open(alert, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        raise UnsafeReplay(f"{where}: non-read-only call(s) not shown as blocked: {[c['name'] for c in ran]} -> {alert}")
sys.path.insert(0, os.path.join(MAIN, "tools", "sessions"))
from scan_sessions import redact  # noqa: E402


def flag(args, name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


def git(*a, cwd=MAIN):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, check=True).stdout.strip()


def lp(p):
    """Extended-length path on Windows: the mirror root is longer than the workspace root, so deep originals
    (browser caches, node trees) pass the 260-character limit there."""
    p = os.path.abspath(p)
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p


def remove_mirror(p, original):
    """Delete a mirror: its files are hardlinks, so the originals keep their data. A read-only link (its
    attribute is shared with the original) is made writable to unlink it, then the original's mode is put back."""
    if os.path.islink(p) or (hasattr(os.path, "isjunction") and os.path.isjunction(p)):
        raise RuntimeError(f"refusing: {p} is a directory link; removing it recursively would reach the original")
    p, original = lp(p), lp(original)

    def onexc(fn, path, exc):
        if fn is not os.unlink or not isinstance(exc, PermissionError):
            raise exc
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IWRITE)
        os.unlink(path)
        orig = os.path.join(original, os.path.relpath(path, p))
        if os.path.exists(orig):
            os.chmod(orig, mode)
    shutil.rmtree(p, onexc=onexc) if sys.version_info >= (3, 12) else shutil.rmtree(p, onerror=lambda f, x, e: onexc(f, x, e[1]))


def mirror(src, dst):
    if os.path.exists(dst):
        remove_mirror(dst, src)
    n = 0
    src, dst = lp(src), lp(dst)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in MIRROR_SKIP and not os.path.islink(os.path.join(root, d))]
        out = os.path.join(dst, os.path.relpath(root, src))
        os.makedirs(out, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            if not os.access(s, os.W_OK):
                continue  # read-only: its link could not be removed without touching the original's attribute
            try:
                os.link(s, os.path.join(out, f))
                n += 1
            except OSError:
                pass  # locked or special file: leave it out
    return n


def worktree(rev, slot="", patch=None, live_world=True):
    """A worktree of rev, optionally with a patch applied inside it only: a candidate change is evaluated
    without a commit or branch in the workspace repo."""
    sha = git("rev-parse", rev)
    tag = ("-p" + hashlib.sha1(open(patch, "rb").read()).hexdigest()[:6]) if patch else ""
    wt = os.path.join(EVAL_HOME, "worktrees", sha[:8] + tag + slot)
    if not os.path.isdir(wt):
        os.makedirs(os.path.dirname(wt), exist_ok=True)
        git("worktree", "add", "--detach", wt, sha)
        if patch:
            git("apply", "--whitespace=nowarn", os.path.abspath(patch), cwd=wt)
            if not git("status", "--porcelain", cwd=wt):
                raise RuntimeError(f"{patch} changed nothing in {wt}")
    if live_world:
        n = sum(mirror(os.path.join(MAIN, d), os.path.join(wt, d)) for d in MIRRORED)
        print(f"worktree {wt}: {n} file(s) mirrored", flush=True)
    return sha + tag, wt


def cleanup():
    root = os.path.join(EVAL_HOME, "worktrees")
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if name.endswith(".lock"):
            continue
        wt = os.path.join(root, name)
        for d in MIRRORED:
            if os.path.lexists(os.path.join(wt, d)):
                remove_mirror(os.path.join(wt, d), os.path.join(MAIN, d))
        git("worktree", "remove", "--force", wt)
        print(f"removed {wt}")


CLAUDE_MD_BLOCK = re.compile(r"(CLAUDE\.md \(project instructions, checked into the codebase\):\\n\\n)(.*?)(\\n\\nContents of |\\n</system-reminder>)", re.S)


def scrub(x):
    """Redact secret shapes in every string of a transcript record (scan_sessions.redact)."""
    if isinstance(x, str):
        return redact(x)
    if isinstance(x, list):
        return [scrub(v) for v in x]
    if isinstance(x, dict):
        return {k: scrub(v) for k, v in x.items()}
    return x


def craft_session(case, wt):
    """Copy the case's transcript up to its cut into wt's project dir; return (session id, path)."""
    src = next(iter(sorted(glob.glob(os.path.join(MAIN, "user", "sessions", case["session"] + "*.jsonl")))), None)
    if not src:
        raise RuntimeError(f"{case['id']}: no transcript {case['session']}")
    sid = str(uuid.uuid4())
    md = json.dumps(open(os.path.join(wt, "CLAUDE.md"), encoding="utf-8").read(), ensure_ascii=False)[1:-1]
    lines, swapped = [], 0
    for line in open(src, encoding="utf-8", errors="replace"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") == "user" and not o.get("isMeta") and o.get("timestamp", "") >= case["cut"]:
            break
        if "sessionId" in o:
            o["sessionId"] = sid
        if "cwd" in o:
            o["cwd"] = wt
        o = scrub(o)  # pasted keys in the history must not be resent
        s, n = CLAUDE_MD_BLOCK.subn(lambda m: m.group(1) + md + m.group(3), json.dumps(o, ensure_ascii=False))
        swapped += n
        lines.append(s)
    # No stored block (older transcripts) is fine: resume loads the worktree's CLAUDE.md from disk either way
    # (probed 2026-10-28: a marker added only to the worktree's CLAUDE.md was obeyed after resume).
    proj = os.path.join(os.path.expanduser("~"), ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", wt))
    os.makedirs(proj, exist_ok=True)
    path = os.path.join(proj, sid + ".jsonl")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return sid, path, swapped


def stage_world(wt, case_dir):
    """Golden mode: the worktree's business/ and user/ become the frozen world (copies, never links): the
    version's shared world/, or a case's own world/ if it has one."""
    world = os.path.join(case_dir, "world")
    if not os.path.isdir(world):
        world = os.path.join(os.path.dirname(case_dir), "world")
    for d in EVAL_SETS:  # the committed framework sets hold every case's rubric: an answer key inside the worktree
        p = os.path.join(wt, *d.split("/"))
        if os.path.isdir(p):
            shutil.rmtree(lp(p))
    for d in MIRRORED:
        p = os.path.join(wt, d)
        if os.path.lexists(p):
            remove_mirror(p, os.path.join(MAIN, d))  # copies or an old hardlink mirror: both are safe to remove
        src = os.path.join(world, d)
        if os.path.isdir(src):
            shutil.copytree(lp(src), lp(p))
    # a resumed case sees the files it reads as they were at its cut (later fixes would hand it the answer)
    ov = os.path.join(case_dir, "overlay")
    if os.path.isdir(ov):
        shutil.copytree(lp(ov), lp(wt), dirs_exist_ok=True)
    case = json.load(open(os.path.join(case_dir, "case.json"), encoding="utf-8"))
    for r in case.get("overlay_deleted") or []:
        p = lp(os.path.join(wt, *r.split("/")))
        if os.path.isfile(p):
            os.remove(p)


def verify_golden(golden):
    """A frozen set is checked before every run: every case, prefix, world and overlay file against its recorded
    sha256. Any difference means the set was edited (or damaged) and its scores would not be comparable."""
    sha = lambda p: hashlib.sha256(open(lp(p), "rb").read()).hexdigest()
    man, bad = json.load(open(os.path.join(golden, "manifest.json"), encoding="utf-8")), []
    world = json.load(open(os.path.join(golden, "world.json"), encoding="utf-8"))
    if hashlib.sha256(json.dumps(world, sort_keys=True).encode()).hexdigest() != man["world_sha256"]:
        bad.append("world.json")
    bad += [r for r, h in world.items() if sha(os.path.join(golden, "world", *r.split("/"))) != h]
    for cid, m in man["cases"].items():
        d = os.path.join(golden, cid)
        if sha(os.path.join(d, "case.json")) != m["case_sha256"]:
            bad.append(f"{cid}/case.json")
        c = json.load(open(os.path.join(d, "case.json"), encoding="utf-8"))
        if c.get("prefix_sha256") and sha(os.path.join(d, "prefix.jsonl")) != c["prefix_sha256"]:
            bad.append(f"{cid}/prefix.jsonl")
        bad += [f"{cid}/overlay/{r}" for r, h in (c.get("overlay") or {}).items() if sha(os.path.join(d, "overlay", *r.split("/"))) != h]
    if bad:
        raise RuntimeError(f"{golden} differs from its manifest ({len(bad)}: {bad[:5]}): a frozen set is never edited")
    return man


def craft_golden_session(case, wt):
    """Golden mode: the frozen prefix, its {{WT}} placeholders pointed at this worktree."""
    sid = str(uuid.uuid4())
    md = json.dumps(open(os.path.join(wt, "CLAUDE.md"), encoding="utf-8").read(), ensure_ascii=False)[1:-1]
    esc, fwd = wt.replace("\\", "\\\\"), wt.replace("\\", "/")
    lines, swapped = [], 0
    for line in open(os.path.join(case["_dir"], "prefix.jsonl"), encoding="utf-8"):
        o = json.loads(line.replace("{{WT}}", esc).replace("{{WTF}}", fwd))
        if "sessionId" in o:
            o["sessionId"] = sid
        if "cwd" in o:
            o["cwd"] = wt
        s2, n = CLAUDE_MD_BLOCK.subn(lambda m: m.group(1) + md + m.group(3), json.dumps(o, ensure_ascii=False))
        swapped += n
        lines.append(s2)
    proj = os.path.join(os.path.expanduser("~"), ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", wt))
    os.makedirs(proj, exist_ok=True)
    path = os.path.join(proj, sid + ".jsonl")
    open(path, "w", encoding="utf-8").write(NL.join(lines) + NL)
    return sid, path, swapped


def run_case(case, wt, model, timeout, golden=False):
    env = {k: v for k, v in os.environ.items() if not (k.startswith("CLAUDE_CODE_") or k in ("CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT"))}
    env["JOURNAL_WORKER"] = "1"  # the journal hook must not start inside a replay
    # dontAsk denies whatever is not allowed, so the read-only tools are allowed explicitly; no MCP servers
    # (a browser MCP would bypass the read-only set)
    # Read-only, in layers (each probed alone with canary writes): --tools registers only read-only tools
    # (resumed replays still try Bash/Edit/Write seen in their history; those fail as unknown tools); a
    # PreToolUse allowlist hook blocks any other tool, also ones added later; deny rules name the known
    # write-capable ones; dontAsk denies what is not allowed; audit() stops the eval if one ever succeeds.
    settings = json.dumps({"permissions": {"deny": DENY, "defaultMode": "dontAsk"},
                           "hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "timeout": 10,
                                     "command": f'python3 "{os.path.join(HERE, "readonly_guard.py").replace(os.sep, "/")}"' + (" --confine" if golden else "")}]}]}})
    deny = [] if os.environ.get("WS_EVAL_PROBE_HOOK_ONLY") else ["--disallowedTools", ",".join(DENY)]  # layer test only
    if os.environ.get("WS_EVAL_PROBE_HOOK_ONLY"):
        settings = json.dumps({**json.loads(settings), "permissions": {"defaultMode": "dontAsk"}})
    tools = os.environ.get("WS_EVAL_PROBE_TOOLS", TOOLS) if os.environ.get("WS_EVAL_PROBE_HOOK_ONLY") else (OFFLINE_TOOLS if golden else TOOLS)
    cmd = [shutil.which("claude") or "claude", "-p", "--no-session-persistence", "--model", model, "--tools", tools,
           "--allowedTools", tools, *deny, "--settings", settings,
           "--strict-mcp-config", "--permission-mode", "dontAsk", "--output-format", "stream-json", "--verbose"]
    crafted, swapped = None, None
    if golden and os.path.exists(os.path.join(case["_dir"], "prefix.jsonl")):
        sid, crafted, swapped = craft_golden_session(case, wt)
        cmd += ["--resume", sid, "--fork-session"]
    elif case.get("session"):
        sid, crafted, swapped = craft_session(case, wt)
        cmd += ["--resume", sid, "--fork-session"]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, input=case["prompt"], capture_output=True, text=True, encoding="utf-8", cwd=wt, env=env, timeout=timeout)
    finally:
        if crafted and os.path.exists(crafted):
            os.remove(crafted)
    calls, texts, result, by_id, thinking = [], [], {}, {}, []
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "user":  # tool results: did a call run or was it blocked?
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in by_id:
                    by_id[b["tool_use_id"]]["ok"] = not b.get("is_error", False)
                    body = b.get("content")
                    body = body if isinstance(body, str) else NL.join(x.get("text", "") for x in body or [] if isinstance(x, dict))
                    by_id[b["tool_use_id"]]["result"] = redact(body)[:1500]
        if ev.get("type") == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if b.get("type") == "tool_use":
                    calls.append({"name": b.get("name"), "input": json.dumps(b.get("input"), ensure_ascii=False)[:300], "ok": None})
                    by_id[b.get("id")] = calls[-1]
                elif b.get("type") == "thinking" and b.get("thinking", "").strip():
                    thinking.append(b["thinking"][:4000])
                elif b.get("type") == "text" and b.get("text", "").strip():
                    texts.append(b["text"])
        elif ev.get("type") == "result":
            result = ev
    return {"answer": result.get("result") or (texts[-1] if texts else ""), "texts": texts, "calls": calls, "thinking": thinking,
            "cost_usd": result.get("total_cost_usd"), "is_error": result.get("is_error", p.returncode != 0), "claude_md_swapped": swapped,
            "seconds": round(time.time() - t0), "stderr": p.stderr[-500:] if p.returncode else ""}


def main():
    args = sys.argv[1:]
    if "--cleanup" in args:
        cleanup()
        return
    rev, model, k = flag(args, "--rev", "HEAD"), flag(args, "--model", "claude-opus-5-5"), int(flag(args, "--k", "3"))
    golden = flag(args, "--golden")
    if golden:  # a frozen golden version: cases come from its dirs, in manifest order
        man = verify_golden(golden)
        cases = []
        for cid in man["cases"]:
            c = json.load(open(os.path.join(golden, cid, "case.json"), encoding="utf-8"))
            c["_dir"], c["_golden"] = os.path.join(golden, cid), man["version"]
            cases.append(c)
    else:
        cases = json.load(open(flag(args, "--cases"), encoding="utf-8"))
    only = set(filter(None, (s.strip() for s in (flag(args, "--only") or "").split(","))))
    unknown = only - {c["id"] for c in cases}
    if unknown:  # a silently dropped id is a case that never runs (seen: a CRLF slot file lost the last id per line)
        raise SystemExit(f"--only: no such case(s): {sorted(unknown)}")
    cases = [c for c in cases if not only or c["id"] in only]
    if flag(args, "--tier"):  # golden: core (the gate's set) or extended, from <version>/tiers.json
        tier = set(json.load(open(os.path.join(golden, "tiers.json"), encoding="utf-8"))[flag(args, "--tier")])
        cases = [c for c in cases if c["id"] in tier]
    slot = f"-{flag(args, '--slot')}" if flag(args, "--slot") else ""  # parallel runs of one rev: one worktree each
    patch = flag(args, "--patch")
    ptag = ("-p" + hashlib.sha1(open(patch, "rb").read()).hexdigest()[:6]) if patch else ""
    lock = os.path.join(EVAL_HOME, "worktrees", git("rev-parse", rev)[:8] + ptag + slot + ".lock")
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    try:  # one replay per worktree: a second one would rebuild the mirror under the first
        os.mkdir(lock)
    except FileExistsError:
        sys.exit(f"{lock} exists: another replay is using this worktree (remove the dir if that process is gone)")
    try:
        run(args, rev, model, k, cases, slot, patch)
    finally:
        os.rmdir(lock)


def run(args, rev, model, k, cases, slot="", patch=None):
    golden = bool(cases and cases[0].get("_golden"))
    sha, wt = worktree(rev, slot, patch, live_world=not golden)
    tag = flag(args, "--tag", sha[:12])
    out = os.path.join(flag(args, "--out", os.path.join(EVAL_HOME, "data", "runs")), tag)
    os.makedirs(out, exist_ok=True)
    cli = subprocess.run([shutil.which("claude") or "claude", "--version"], capture_output=True, text=True).stdout.strip()
    total = 0.0
    for c in cases:
        if golden and any(not os.path.exists(os.path.join(out, f"{c['id']}.{i}.json")) for i in range(1, k + 1)):
            stage_world(wt, c["_dir"])
        for i in range(1, k + 1):
            path = os.path.join(out, f"{c['id']}.{i}.json")
            if os.path.exists(path):
                continue  # resumable
            r = run_case(c, wt, model, int(flag(args, "--timeout", "900")), golden)
            r.update({"case": c["id"], "run": i, "rev": sha, "model": model, "cli": cli, "golden": c.get("_golden"),
                      "at": datetime.now().astimezone().isoformat(timespec="seconds")})
            json.dump(r, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            audit(r, path)
            total += r["cost_usd"] or 0
            print(f"{c['id']}.{i}: {'ERROR ' if r['is_error'] else ''}{len(r['calls'])} tool call(s), ${r['cost_usd']}, {r['seconds']}s", flush=True)
    print(f"done: {len(cases)} case(s) x {k} at {sha[:12]} -> {out} (${total:.2f})")


if __name__ == "__main__":
    main()
