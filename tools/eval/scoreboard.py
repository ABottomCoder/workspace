#!/usr/bin/env python3
"""
Scoreboard: each framework version is scored once on a golden set; a new version runs only itself and is compared
with the recorded score of the current best. Old versions are never re-run, and nothing is back-filled when cases
change (a changed case set is a new golden version, so a new fingerprint).

    python3 tools/eval/scoreboard.py add     --cases <golden dir> --runs <judged run dir> [--tier core] [--baseline]
                                             [--report <path>] [--note "..."]      --baseline: this is the current best
    python3 tools/eval/scoreboard.py compare --cases <golden dir> --runs <judged run dir> [--tier core]
    python3 tools/eval/scoreboard.py render

An entry holds the fingerprint, the per-group pass rates and scores, and every case's passes, runs and mean score,
so a comparison is a paired bootstrap over cases against the stored numbers. Two run sets are comparable only when
their fingerprints match: golden version (and world hash), tier and its case list, model, `claude --version`, judge (model, votes,
verdict code hash). If none matches (the CLI auto-updated, the model or the judge changed), compare says so: the
current best is re-run once under the new fingerprint to set a new baseline.

Drift: an anchor run of the baseline's own rev (core, small k) is compared the same way; when it moves past the
A/A noise floor, the baseline is stale: re-baseline.

Files: tools/eval/history/scoreboard.jsonl (append-only, committed: the shared record of how each version did), one
HTML version report per entry written by `add` (version_report.py) and history/index.html. Only the committed
framework sets (tools/eval/golden/) are recorded there; raw runs and verdicts stay in the local eval data dir.
"""
import glob, hashlib, json, os, random, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.dirname(os.path.dirname(HERE))
EVAL_HOME = os.environ.get("WS_EVAL_HOME") or os.path.join(os.path.dirname(MAIN), os.path.basename(MAIN) + "-eval")
HISTORY = os.path.join(HERE, "history")
BOARD = os.environ.get("WS_EVAL_BOARD") or os.path.join(HISTORY, "scoreboard.jsonl")
# Gate (README "Gate"), from the A/A on golden v1 core (AA-v1, 5 vs 5 runs: holdout +3 % [-6, +11], guard +10 %
# [-7, +33]), for k = 10 per arm: B - A on the mean per-case pass rate, paired over cases. score_min_lo: the process
# check on dev + holdout mean scores (A/A floor about ±0.04; NEG-v1, the evidence rules removed, fell -0.14 on dev
# with flat pass rates). Decided by the user on 2026-10-29 together with C07 and C12 joining the core guards.
GATE = {"holdout_min_gain": 0.12, "guard_min_lo": -0.10, "guard_case_from": 0.8, "guard_case_to": 0.5,
        "score_min_lo": -0.05}
FLOOR = 0.10  # drift: an anchor run (core, k = 5) moving holdout by more than this means re-baseline


def flag(args, name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


def load_golden(src, tier):
    man = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
    cases = {cid: json.load(open(os.path.join(src, cid, "case.json"), encoding="utf-8")) for cid in man["cases"]}
    if tier:
        keep = set(json.load(open(os.path.join(src, "tiers.json"), encoding="utf-8"))[tier])
        cases = {cid: c for cid, c in cases.items() if cid in keep}
    return man, cases


def collect(runs, cases):
    """Per case [passes, runs, mean score]; plus the run-level facts the fingerprint needs (each must be unique)."""
    per, facts, cost = {}, {"rev": set(), "model": set(), "cli": set(), "golden": set(), "judge": set()}, 0.0
    for p in glob.glob(os.path.join(runs, "*.verdict.json")):
        r = json.load(open(p[:-len(".verdict.json")] + ".json", encoding="utf-8"))
        if r["case"] not in cases:
            continue
        v = json.load(open(p, encoding="utf-8"))
        s = per.setdefault(r["case"], [0, 0, []])
        s[0] += v["verdict"] == "PASS"
        s[1] += 1
        if v.get("score") is not None:
            s[2].append(v["score"])
        for k in ("rev", "model", "cli", "golden"):
            facts[k].add(r.get(k))
        facts["judge"].add(json.dumps(v.get("judge"), sort_keys=True))
        cost += r.get("cost_usd") or 0
    missing = sorted(set(cases) - set(per))
    if missing:
        sys.exit(f"{runs}: no judged runs for {missing}; run and judge the whole tier first")
    mixed = {k: v for k, v in facts.items() if len(v) != 1}
    if mixed:
        sys.exit(f"{runs}: mixed {sorted(mixed)} in one run set ({mixed}); not scorable as one entry")
    facts = {k: next(iter(v)) for k, v in facts.items()}
    facts["judge"] = json.loads(facts["judge"])
    if not facts["judge"]:
        sys.exit(f"{runs}: verdicts carry no judge fingerprint (judged before it was recorded); re-judge")
    per = {cid: [a, n, round(sum(sc) / len(sc), 4) if sc else None] for cid, (a, n, sc) in per.items()}
    return per, facts, cost


def groups(cases):
    g = {s: [i for i, c in cases.items() if c.get("split") == s] for s in ("holdout", "dev", "guard")}
    for cls in sorted({c.get("cls") for c in cases.values() if c.get("cls")}):
        g[cls] = [i for i, c in cases.items() if c.get("cls") == cls]
    return {k: v for k, v in g.items() if v}


def entry(args):
    src, tier, runs = flag(args, "--cases"), flag(args, "--tier"), flag(args, "--runs")
    man, cases = load_golden(src, tier)
    per, f, cost = collect(runs, cases)
    n_runs = sum(n for _, n, _ in per.values())
    summary = {}
    for name, ids in groups(cases).items():
        rates = [per[i][0] / per[i][1] for i in ids]
        scores = [per[i][2] for i in ids if per[i][2] is not None]
        summary[name] = {"cases": len(ids), "pass": round(sum(rates) / len(rates), 4),
                         "score": round(sum(scores) / len(scores), 4) if scores else None}
    return {"date": datetime.now().astimezone().isoformat(timespec="seconds"), "tag": os.path.basename(os.path.normpath(runs)),
            "rev": f["rev"], "golden": man["version"], "world": (man.get("world_sha256") or "")[:12], "tier": tier or "all",
            "k": max(n for _, n, _ in per.values()), "model": f["model"], "cli": f["cli"], "judge": f["judge"],
            "groups": summary, "cases": per, "cost_usd": round(cost, 2), "cost_per_run": round(cost / n_runs, 3),
            "report": flag(args, "--report"), "note": flag(args, "--note")}


def fingerprint(e):
    # the case list too: a tier whose membership changed (tiers.json is outside the golden hashes) is another set
    ids = hashlib.sha256(",".join(sorted(e["cases"])).encode()).hexdigest()[:12]
    return (e["golden"], e["world"], e["tier"], ids, e["model"], e["cli"], json.dumps(e["judge"], sort_keys=True))


def board():
    return [json.loads(l) for l in open(BOARD, encoding="utf-8")] if os.path.exists(BOARD) else []


def render():
    rows = board()
    out = ["# Eval scoreboard", "", "One line per scored run set (`tools/eval/scoreboard.py`). Compare only rows with the same",
           "fingerprint: golden version and world, tier, model, CLI, judge.", "",
           "| Date | Rev | Base | Golden | Tier | k | Model | CLI | Judge | Holdout | Dev | Guard | Score (holdout) | $/run | Tag | Report |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in rows:
        g = e["groups"]
        pct = lambda k: f"{g[k]['pass']:.0%}" if k in g else "—"
        sc = f"{g['holdout']['score']:.2f}" if g.get("holdout", {}).get("score") is not None else "—"
        j = e["judge"]
        out.append(f"| {e['date'][:16]} | {e['rev'][:12]} | {'★' if e.get('baseline') else ''} | {e['golden']} ({e['world']}) | {e['tier']} ({len(e['cases'])}) | {e['k']} | {e['model']} | "
                   f"{e['cli'].split()[0]} | {j['model']}×{j['votes']} {j['sha256'][:8]} | {pct('holdout')} | {pct('dev')} | "
                   f"{pct('guard')} | {sc} | {e['cost_per_run']:.2f} | {e['tag']} | {e.get('report') or ''} |")
    if os.path.dirname(os.path.abspath(BOARD)) == HISTORY:
        import version_report
        version_report.write_index(rows)
    print("\n".join(out))


def compare(new, base, boot=10000):
    """Paired bootstrap over cases on the stored per-case rates; the gate verdict for the new set."""
    rng, lines, ok, rows = random.Random(0), [], True, []
    ids_all = [i for i in new["cases"] if i in base["cases"]]

    def ci(d):
        b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(boot))
        return b[int(0.025 * boot)], b[int(0.975 * boot) - 1]

    rate = lambda e, i: e["cases"][i][0] / e["cases"][i][1]
    score = lambda e, i: e["cases"][i][2]
    lines.append(f"| Group | Cases | Base | New | New-Base | 95% CI |\n|---|---|---|---|---|---|")
    res = {}
    for name in new["groups"]:
        ids = [i for i in ids_all if i in base["cases"] and name in base["groups"]]
        ids = [i for i in ids if i in group_ids(new, name)]
        if not ids:
            continue
        d = [rate(new, i) - rate(base, i) for i in ids]
        lo, hi = ci(d)
        mb, mn = sum(rate(base, i) for i in ids) / len(ids), sum(rate(new, i) for i in ids) / len(ids)
        res[name] = (mn - mb, lo, hi)
        rows.append((name, len(ids), mb, mn, lo, hi))
        lines.append(f"| {name} | {len(ids)} | {mb:.0%} | {mn:.0%} | {mn - mb:+.0%} | [{lo:+.0%}, {hi:+.0%}] |")
    sids = [i for i in ids_all if (i in group_ids(new, "holdout") or i in group_ids(new, "dev"))
            and score(new, i) is not None and score(base, i) is not None]
    s, srow = None, None
    if sids:  # process: mean score (0.4 process + 0.6 outcome), which moves when pass rates do not
        d = [score(new, i) - score(base, i) for i in sids]
        s = (sum(d) / len(d), *ci(d))
        srow = (len(sids), sum(score(base, i) for i in sids) / len(sids), sum(score(new, i) for i in sids) / len(sids), *s)
        lines.append(f"\n| Score (dev + holdout) | {len(sids)} | {sum(score(base, i) for i in sids) / len(sids):.2f} | "
                     f"{sum(score(new, i) for i in sids) / len(sids):.2f} | {s[0]:+.2f} | [{s[1]:+.2f}, {s[2]:+.2f}] |")
    same_rev = new["rev"] == base["rev"]
    if same_rev:  # drift check: the same version again
        d, lo, hi = res.get("holdout", (0, 0, 0))
        verdict = (f"DRIFT: holdout moved {d:+.0%} beyond the ±{FLOOR:.0%} floor: re-baseline" if abs(d) > FLOOR
                   else f"no drift: holdout {d:+.0%} within ±{FLOOR:.0%}")
        return "\n".join(lines), verdict, (rows, srow, verdict)
    h, g = res.get("holdout"), res.get("guard")
    why = []
    if not h or h[0] < GATE["holdout_min_gain"] or h[1] <= 0:
        why.append(f"holdout gain below {GATE['holdout_min_gain']:+.0%} or its interval reaches 0")
    if g and g[1] < GATE["guard_min_lo"]:
        why.append(f"guard interval lower bound {g[1]:+.0%} < {GATE['guard_min_lo']:+.0%}")
    if s and s[1] < GATE["score_min_lo"]:
        why.append(f"process: dev + holdout score interval lower bound {s[1]:+.2f} < {GATE['score_min_lo']:+.2f}")
    for i in ids_all:
        if base["cases"][i] and rate(base, i) >= GATE["guard_case_from"] and rate(new, i) <= GATE["guard_case_to"] and \
                i in group_ids(new, "guard"):
            why.append(f"guard {i} fell from {rate(base, i):.0%} to {rate(new, i):.0%}")
    falls = [i for i in ids_all if rate(base, i) == 1 and rate(new, i) < 1]
    verdict = ("GATE PASSED" if not why else "GATE NOT PASSED: " + "; ".join(why)) + \
              (f". Read by hand before shipping (always passed, now not): {falls}" if falls else "")
    return "\n".join(lines), verdict, (rows, srow, verdict)


def write_report(e):
    """The entry's HTML version report (history/<time>_<rev>_<set>-<tier>.html); sets e["report"]. A candidate is
    compared with the current baseline, a baseline with the previous one of the same fingerprint, if any."""
    import version_report
    prior = [x for x in board() if fingerprint(x) == fingerprint(e) and x.get("baseline") and x["date"] < e["date"]
             and x["tag"] != e["tag"]]
    base = prior[-1] if prior else None
    e["report"] = version_report.name_of(e)
    out = os.path.join(os.path.dirname(os.path.abspath(BOARD)), e["report"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(version_report.render(e, base, compare(e, base)[2] if base else None))
    return out


def group_ids(e, name):
    return set(e.get("group_ids", {}).get(name, []))


def main():
    args = sys.argv[1:]
    sys.stdout.reconfigure(encoding="utf-8")  # a Windows console defaults to GBK
    cmd = args[0] if args else "render"
    if cmd == "render":
        render()
        return
    e = entry(args)
    man, cases = load_golden(flag(args, "--cases"), flag(args, "--tier"))
    e["group_ids"] = groups(cases)
    if cmd == "add":
        golden_root = os.path.join(HERE, "golden")
        if not os.environ.get("WS_EVAL_BOARD") and \
                os.path.commonpath([os.path.abspath(flag(args, "--cases")), golden_root]) != golden_root:
            sys.exit("the shared scoreboard records only the committed framework sets (tools/eval/golden/); "
                     "set WS_EVAL_BOARD to a local file for any other set")
        if any(x["tag"] == e["tag"] and fingerprint(x) == fingerprint(e) for x in board()):
            sys.exit(f"{e['tag']} is already on the board under this fingerprint")
        e["baseline"] = "--baseline" in args  # the current best (shipped) version; candidates are recorded without it
        print(write_report(e))
        with open(BOARD, "a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        render()
        return
    if cmd == "compare":
        base = [x for x in board() if fingerprint(x) == fingerprint(e) and x["tag"] != e["tag"] and x.get("baseline")]
        if not base:
            print(f"No baseline with this fingerprint ({e['golden']}/{e['tier']}, {e['model']}, {e['cli']}, judge "
                  f"{e['judge']}). Something changed (CLI auto-update, model, judge, golden version): re-run the current "
                  f"best version once on this fingerprint and `add` it as the new baseline, then compare again.")
            sys.exit(2)
        table, verdict, _ = compare(e, base[-1])
        print(f"New {e['tag']} ({e['rev'][:12]}) vs baseline {base[-1]['tag']} ({base[-1]['rev'][:12]}, {base[-1]['date'][:10]})\n")
        print(table + "\n\n" + verdict)
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
