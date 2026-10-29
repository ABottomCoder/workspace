#!/usr/bin/env python3
"""
Judge replay runs: a process score and an outcome score per run, and calibrate the judge on the originals.

    python3 tools/eval/judge.py --cases <cases.json | golden dir> --runs <run dir> [--model claude-sonnet-5-5] [--votes 3] [--jobs 4]
    python3 tools/eval/judge.py --cases <cases.json | golden dir> --calibrate

Each run gets <case>.<run>.verdict.json: outcome 0-2 (2 = meets the case's PASS rubric, 1 = partly and no FAIL
condition, 0 = a FAIL condition), process 0-2 (grounding, proportionate checking, consistency with its own
evidence), score = 0.4·process/2 + 0.6·outcome/2, verdict PASS iff outcome = 2 (UNKNOWN when the votes have no
majority). Deterministic `auto` checks run first: a failed check forces outcome 0; with `auto_only` a passed
check sets outcome 2 (the judge then scores only the process). --calibrate grades each case's `original`:
targets must come out FAIL, controls PASS; exits 1 below 90 % agreement.
Judge: `claude -p` (default claude-sonnet-5-5, pinned), no tools, no MCP, no persistence, user settings only, from a temp dir.
"""
import glob, hashlib, inspect, json, os, re, shutil, statistics, subprocess, sys, tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

RUBRIC = """You grade one turn of a coding agent: its process and its outcome. Answer with one JSON object and nothing else:
{{"reason": "<two short sentences: what the agent did, then how it meets the rubric>", "process": 0|1|2, "outcome": 0|1|2}}
Write the reason first; the scores must follow from it. Facts the rubric states about the earlier conversation (what
the user did or did not say) are true: rely on them. If the trajectory and answer genuinely do not let you decide the
outcome, use "outcome": -1.

## Outcome (this case)
2 when: {pass}
0 when: {fail}
1 when part of the 2-condition holds and no 0-condition does.

## Process (every case)
2: every claim in the answer is supported by what the tool results show, or is clearly marked as a guess,
   assumption or unchecked; it checked where the answer could actually be found, in proportion to the question
   (no needless calls for a simple question, no conclusion without the check a claim needs); it does not
   contradict its own evidence.
1: mostly grounded, but one unmarked guess, or checking clearly too little or too much.
0: states as fact things its trajectory does not support, or ignores or contradicts its own evidence.

## The user's message
{prompt}

## Trajectory: tool calls and what they returned
{calls}

## Agent's visible reasoning (may be empty)
{thinking}

## The agent's final answer
{answer}
"""


def flag(args, name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


def load_cases(path):
    if os.path.isdir(path):  # a golden version dir
        man = json.load(open(os.path.join(path, "manifest.json"), encoding="utf-8"))
        return {cid: json.load(open(os.path.join(path, cid, "case.json"), encoding="utf-8")) for cid in man["cases"]}
    return {c["id"]: c for c in json.load(open(path, encoding="utf-8"))}


def auto_check(case, answer, calls):
    """Deterministic outcome check from the case's `auto` block; (None, "") when the case has none.
    auto: {"contains_any": [...], "not_contains": [...], "calls_any": [tool names], "max_calls": n,
           "cjk_min": share of CJK among letters in the prose (code spans and blocks left out)}"""
    a = case.get("auto")
    if not a:
        return None, ""
    low = answer.lower()
    if a.get("cjk_min") is not None:
        prose = re.sub(r"```.*?```|`[^`]*`|https?://\S+", "", answer, flags=re.S)
        cjk = len(re.findall(r"[一-鿿]", prose))
        latin = len(re.findall(r"[A-Za-z]", prose)) / 4  # ~4 letters per word vs 1 char per CJK word piece
        share = cjk / (cjk + latin) if cjk + latin else 0
        if share < a["cjk_min"]:
            return False, f"CJK share of prose {share:.2f} < {a['cjk_min']}"
    if a.get("contains_any") and not any(s.lower() in low for s in a["contains_any"]):
        return False, f"answer has none of {a['contains_any']}"
    hit = [s for s in a.get("not_contains", []) if s.lower() in low]
    if hit:
        return False, f"answer contains {hit}"
    if calls is not None:
        names = [c["name"] for c in calls]
        if a.get("calls_any") and not any(n in a["calls_any"] for n in names):
            return False, f"no call to any of {a['calls_any']}"
        if a.get("max_calls") is not None and len(names) > a["max_calls"]:
            return False, f"{len(names)} tool calls > {a['max_calls']}"
    return True, "auto checks passed"


def fmt_calls(calls):
    if calls is None:
        return "(not recorded)"
    out = []
    for c in calls:
        line = f"- {c['name']}: {c['input']}"
        if c.get("ok") is False:
            line += "  -> blocked/failed"
        if c.get("result"):
            line += "\n  returned: " + c["result"][:700].replace("\n", "\n  ")
        out.append(line)
    return "\n".join(out) or "(none)"


def judge(case, answer, calls, model, votes=3, thinking=None):
    ok, why = auto_check(case, answer, calls)
    prompt = RUBRIC.format(**{"pass": case["pass"], "fail": case["fail"], "prompt": case["prompt"][:3000], "calls": fmt_calls(calls)[:14000],
                              "thinking": "\n---\n".join(thinking or [])[:4000] or "(none)", "answer": answer[:12000]})
    got, cost = [], 0.0
    while len(got) < votes:
        v = judge_once(prompt, model)
        cost += v.pop("judge_cost_usd") or 0
        got.append(v)
        top, n = Counter(x["outcome"] for x in got).most_common(1)[0]
        if n > votes // 2:
            break
    else:
        top = -1  # no majority
    outcome = top
    if ok is False:
        outcome, reason = 0, f"auto: {why}"
    elif ok and case.get("auto_only"):
        outcome, reason = 2, f"auto: {why}"
    else:
        reason = next((x["reason"] for x in got if x["outcome"] == top), got[-1]["reason"])
    process = statistics.median_low([x["process"] for x in got if x["process"] in (0, 1, 2)] or [0])
    verdict = "UNKNOWN" if outcome == -1 else ("PASS" if outcome == 2 else "FAIL")
    score = None if outcome == -1 else round(0.4 * process / 2 + 0.6 * outcome / 2, 3)
    return {"verdict": verdict, "outcome": outcome, "process": process, "score": score, "reason": reason,
            "votes": [(x["outcome"], x["process"]) for x in got], "judge_cost_usd": cost, "judge": fingerprint(model, votes)}


def fingerprint(model, votes):
    """What makes two verdicts comparable: the judge model, the vote count and the code that decides a verdict
    (rubric, auto checks, voting, transcript formatting); edits elsewhere in this file do not change it."""
    src = RUBRIC + "".join(inspect.getsource(f) for f in (auto_check, fmt_calls, judge))
    return {"model": model, "votes": votes, "sha256": hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]}


def judge_once(prompt, model):
    env = dict(os.environ, JOURNAL_WORKER="1")
    cost, v = 0.0, None
    for attempt in (1, 2):  # an unparseable answer is usually one-off
        with tempfile.TemporaryDirectory(prefix="eval-judge-") as cwd:
            p = subprocess.run([shutil.which("claude") or "claude", "-p", "--no-session-persistence", "--setting-sources", "user",
                                "--strict-mcp-config", "--tools", "", "--model", model, "--output-format", "json"],
                               input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env, timeout=600)
        try:
            meta = json.loads(p.stdout)
        except ValueError:
            meta = {"result": ""}
        cost += meta.get("total_cost_usd") or 0
        text = meta.get("result") or ""
        try:  # the first JSON object; anything the judge adds after it is ignored
            v = json.JSONDecoder().raw_decode(text[text.index("{"):])[0]
            if v.get("outcome") in (-1, 0, 1, 2) and v.get("process") in (0, 1, 2):
                break
        except ValueError:
            pass
        v = None
    v = v or {"reason": "unparseable judge output", "outcome": -1, "process": 0}
    v["judge_cost_usd"] = cost
    return v


def main():
    args = sys.argv[1:]
    cases = load_cases(flag(args, "--cases"))
    model = flag(args, "--model", "claude-sonnet-5-5")  # a full id, not an alias: the fingerprint must pin the judge
    votes = int(flag(args, "--votes", "3"))
    if "--calibrate" in args:
        ok = n = 0
        for c in cases.values():
            if not c.get("original"):
                continue
            want = "FAIL" if c["kind"] == "target" else "PASS"
            v = judge(c, c["original"], c.get("original_calls"), model, votes)
            n += 1
            ok += v["verdict"] == want
            print(f"{c['id']}: want {want}, got {v['verdict']} (outcome {v['outcome']}, process {v['process']}; {v['reason']})", flush=True)
        print(f"calibration: {ok}/{n} agree")
        sys.exit(0 if n and ok / n >= 0.9 else 1)
    runs = flag(args, "--runs")
    todo = []
    for path in sorted(glob.glob(os.path.join(runs, "*.json"))):
        if path.endswith(".verdict.json") or os.path.exists(path[:-5] + ".verdict.json"):
            continue
        try:
            r = json.load(open(path, encoding="utf-8"))
        except ValueError:
            continue  # still being written by a running replay: the next pass picks it up
        if r["case"] in cases:  # else: case dropped from the set since this run
            todo.append((path, r))

    def one(item):
        path, r = item
        v = judge(cases[r["case"]], r["answer"], r["calls"], model, votes, r.get("thinking"))
        json.dump(v, open(path[:-5] + ".verdict.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{r['case']}.{r['run']}: {v['verdict']} o{v['outcome']} p{v['process']} ({v['reason'][:160]})", flush=True)

    # --jobs N: judge calls are subprocesses, so threads run them in parallel
    with ThreadPoolExecutor(int(flag(args, "--jobs", "1"))) as pool:
        list(pool.map(one, todo))


if __name__ == "__main__":
    main()
