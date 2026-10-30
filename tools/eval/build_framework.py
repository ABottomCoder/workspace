#!/usr/bin/env python3
"""Build a portable golden set from its source: tools/eval/golden-src/<version>/ -> tools/eval/golden/<version>/.

The private sets (data/golden/v1, ...) are built from real sessions and stay outside git. A framework set is
rebuilt from them by hand, de-identified: each case keeps its failure pattern and rubric, its scene moves into a
fictional world, and its conversation prefix is written as a few turns. The output has the golden-set layout
replay.py, judge.py and report.py already read (world/, world.json, manifest.json, <case>/case.json,
<case>/prefix.jsonl). The build is deterministic (uuids and timestamps derive from the case), so a rebuild of a
committed version must be byte-identical: tests/test_eval.sh checks it.

  python3 tools/eval/build_framework.py <version> [--out DIR]

Source layout:
  golden-src/<v>/world/{business,user}/...   the shared fictional world
  golden-src/<v>/cases/<id>.json             case fields (kind, cls, split, prompt, pass, fail, auto, ...) plus
    "turns": [{"user": "..."} | {"assistant": ["text", {"tool": "Read", "input": {...}, "result": "...",
              "error": false}, "text"]}, ...]   paths as {{WTF}} (forward slashes) or {{WT}}
    "start": "2026-10-20T09:00:00Z"            first timestamp; a turn may carry "at" to set its own
    "asserts": [["isdir", rel] | ["isfile", rel] | ["contains", rel, text] | ["listdir", rel, [names]]
                | ["count_type", "memory type", n]]   the world must hold the case's answer, or the build fails
"""
import datetime, hashlib, json, os, re, shutil, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NS = uuid.UUID("6f1c3d1e-9a52-4c1b-8d1e-2f4a7b9c0e11")
CASE_KEYS = ("id", "derived_from", "kind", "cls", "split", "prompt", "pass", "fail", "auto", "auto_only", "note")
sha = lambda b: hashlib.sha256(b).hexdigest()


def records(case):
    """The prefix as Claude Code transcript records: a parentUuid chain of user and assistant messages."""
    cid, out, parent, n = case["id"], [], None, 0
    t = datetime.datetime.fromisoformat(case.get("start", "2026-10-20T09:00:00Z").replace("Z", "+00:00"))
    sid = str(uuid.uuid5(NS, cid + "/session"))

    def emit(kind, message, **extra):
        nonlocal parent, n, t
        n += 1
        u = str(uuid.uuid5(NS, f"{cid}/{n}"))
        rec = {"parentUuid": parent, "isSidechain": False, "type": kind, "message": message, "uuid": u,
               "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "userType": "external", "cwd": "{{WT}}",
               "sessionId": sid, "version": "2.1.215", "gitBranch": "HEAD", **extra}
        out.append(rec)
        parent, t = u, t + datetime.timedelta(seconds=20)

    def assistant(content, mid, stop):
        emit("assistant", {"model": "claude-opus-5-5", "id": mid, "type": "message", "role": "assistant", "content": content,
                           "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 0, "output_tokens": 0}})

    for ti, turn in enumerate(case.get("turns") or []):
        if turn.get("at"):
            t = datetime.datetime.fromisoformat(turn["at"].replace("Z", "+00:00"))
        if "user" in turn:
            emit("user", {"role": "user", "content": turn["user"]})
            continue
        steps, seg = turn["assistant"], 0
        for si, step in enumerate(steps):
            mid = f"msg_synth_{sha(f'{cid}/{ti}/{seg}'.encode())[:20]}"
            last = si == len(steps) - 1
            if isinstance(step, str):
                assistant([{"type": "text", "text": step}], mid, "end_turn" if last else "tool_use")
                continue
            tid = f"toolu_synth_{sha(f'{cid}/{ti}/{si}'.encode())[:20]}"
            assistant([{"type": "tool_use", "id": tid, "name": step["tool"], "input": step["input"]}], mid, "tool_use")
            emit("user", {"role": "user", "content": [{"tool_use_id": tid, "type": "tool_result", "content": step["result"],
                                                       "is_error": bool(step.get("error"))}]},
                 sourceToolAssistantUUID=parent)
            seg += 1
        if isinstance(steps[-1], dict):
            raise SystemExit(f"{cid}: assistant turn {ti} ends on a tool call; end it with text")
    return out


def count_type(world, typ):
    d = os.path.join(world, "user", "memory")
    return sum(1 for f in os.listdir(d) if f.endswith(".md") and f != "MEMORY.md"
               and re.search(rf"(?m)^\s*type:\s*{typ}\s*$", open(os.path.join(d, f), encoding="utf-8").read()))


def check(world, a):
    p = os.path.join(world, *a[1].split("/")) if a[0] != "count_type" else None
    return {"isdir": lambda: os.path.isdir(p), "isfile": lambda: os.path.isfile(p),
            "contains": lambda: os.path.isfile(p) and a[2] in open(p, encoding="utf-8").read(),
            "listdir": lambda: os.path.isdir(p) and sorted(os.listdir(p)) == sorted(a[2]),
            "count_type": lambda: count_type(world, a[1]) == a[2]}[a[0]]()


def write(p, body):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(body)


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    version = args[0]
    src = os.path.join(HERE, "golden-src", version)
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(HERE, "golden", version)
    sworld = os.path.join(src, "world")
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(sworld, os.path.join(out, "world"))
    world = {}
    for root, _, files in os.walk(os.path.join(out, "world")):
        for f in files:
            p = os.path.join(root, f)
            world[os.path.relpath(p, os.path.join(out, "world")).replace(os.sep, "/")] = sha(open(p, "rb").read())
    world = dict(sorted(world.items()))
    write(os.path.join(out, "world.json"), json.dumps(world, indent=1).encode())
    world_sha = sha(json.dumps(world, sort_keys=True).encode())

    manifest, bad = {}, []
    for f in sorted(os.listdir(os.path.join(src, "cases"))):
        c = json.load(open(os.path.join(src, "cases", f), encoding="utf-8"))
        bad += [f"{c['id']}: {a}" for a in c.get("asserts") or [] if not check(sworld, a)]
        case = {k: c[k] for k in CASE_KEYS if k in c}
        if c.get("turns"):
            body = ("\n".join(json.dumps(r, ensure_ascii=False) for r in records(c)) + "\n").encode("utf-8")
            write(os.path.join(out, c["id"], "prefix.jsonl"), body)
            case["prefix_sha256"], case["prefix_lines"] = sha(body), body.count(b"\n")
        case["world_sha256"] = world_sha
        body = json.dumps(case, ensure_ascii=False, indent=1).encode("utf-8")
        write(os.path.join(out, c["id"], "case.json"), body)
        manifest[c["id"]] = {"case_sha256": sha(body), "prefix_sha256": case.get("prefix_sha256"), "kind": c["kind"]}
    if bad:
        raise SystemExit("world does not hold the answers:\n  " + "\n  ".join(bad))
    write(os.path.join(out, "manifest.json"), json.dumps({"version": version, "world_sha256": world_sha,
                                                          "world_files": len(world), "cases": manifest}, indent=1).encode())
    tiers = os.path.join(src, "tiers.json")  # re-derived from each A/A; outside the hashes, as in the private sets
    if os.path.exists(tiers):
        shutil.copyfile(tiers, os.path.join(out, "tiers.json"))
    print(f"{len(manifest)} cases, {len(world)} world files -> {out}")


if __name__ == "__main__":
    main()
