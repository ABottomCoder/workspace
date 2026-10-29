#!/usr/bin/env python3
"""
Compare two judged run sets (A/A for noise, A/B for a change).

    python3 tools/eval/report.py --cases <cases.json> --a <run dir> --b <run dir> [--boot 10000]
    python3 tools/eval/report.py --cases <cases.json> --split <run dir>     A/A: odd runs vs even runs of one set
    --cases <data/golden/<version>> [--tier core|extended]                  a golden set, optionally one tier

Per case: pass rate in each set (UNKNOWN counts as not passed and is shown). Overall: mean per-case
pass rate for targets and for controls, the difference B - A, and a 95 % interval from a paired
bootstrap over cases (cases are the unit: runs of one case are not independent). Also cost per set.
"""
import glob, json, os, random, sys


def flag(args, name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


SCORES = {}  # (set id, case) -> [score]: filled by load


def load(d, parity=None):
    out, cost = {}, 0.0
    for p in glob.glob(os.path.join(d, "*.verdict.json")):
        r = json.load(open(p[:-len(".verdict.json")] + ".json", encoding="utf-8"))
        if parity is not None and r["run"] % 2 != parity:
            continue
        vj = json.load(open(p, encoding="utf-8"))
        v = vj["verdict"]
        out.setdefault(r["case"], []).append(v)
        if vj.get("score") is not None:
            SCORES.setdefault((d, parity, r["case"]), []).append(vj["score"])
        cost += r.get("cost_usd") or 0
    return out, cost


def rate(vs):
    return sum(v == "PASS" for v in vs) / len(vs) if vs else None


def main():
    args = sys.argv[1:]
    src = flag(args, "--cases")
    if os.path.isdir(src):  # a golden version dir
        man = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
        cases = {cid: json.load(open(os.path.join(src, cid, "case.json"), encoding="utf-8")) for cid in man["cases"]}
        if flag(args, "--tier"):  # the gate is computed on core
            tier = set(json.load(open(os.path.join(src, "tiers.json"), encoding="utf-8"))[flag(args, "--tier")])
            cases = {cid: c for cid, c in cases.items() if cid in tier}
    else:
        cases = {c["id"]: c for c in json.load(open(src, encoding="utf-8"))}
    if flag(args, "--split"):
        (A, ca), (B, cb) = load(flag(args, "--split"), 1), load(flag(args, "--split"), 0)
        ka, kb = (flag(args, "--split"), 1), (flag(args, "--split"), 0)
    else:
        (A, ca), (B, cb) = load(flag(args, "--a")), load(flag(args, "--b"))
        ka, kb = (flag(args, "--a"), None), (flag(args, "--b"), None)
    mean = lambda xs: sum(xs) / len(xs) if xs else None
    sa = {cid: mean(SCORES.get((*ka, cid), [])) for cid in cases}
    sb = {cid: mean(SCORES.get((*kb, cid), [])) for cid in cases}
    n_boot = int(flag(args, "--boot", "10000"))
    print(f"| Case | Kind | A | B |\n|---|---|---|---|")
    for cid, c in cases.items():
        fmt = lambda vs: f"{sum(v == 'PASS' for v in vs)}/{len(vs)}" + (f" ({vs.count('UNKNOWN')} unknown)" if 'UNKNOWN' in vs else "") if vs else "—"
        print(f"| {cid} | {c['kind']} | {fmt(A.get(cid, []))} | {fmt(B.get(cid, []))} |")
    rng = random.Random(0)

    def ci(diffs):
        boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n_boot))
        return boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]

    def line(label, ids):
        ids = [i for i in ids if A.get(i) and B.get(i)]
        if not ids:
            return
        diffs = [rate(B[i]) - rate(A[i]) for i in ids]
        ma = sum(rate(A[i]) for i in ids) / len(ids)
        mb = sum(rate(B[i]) for i in ids) / len(ids)
        lo, hi = ci(diffs)
        sc = [i for i in ids if sa.get(i) is not None and sb.get(i) is not None]
        stxt = "— | — | —"
        if sc:
            sd = [sb[i] - sa[i] for i in sc]
            slo, shi = ci(sd)
            stxt = (f"{sum(sa[i] for i in sc) / len(sc):.2f} | {sum(sb[i] for i in sc) / len(sc):.2f} | "
                    f"{sum(sd) / len(sd):+.2f} [{slo:+.2f}, {shi:+.2f}]")
        print(f"| {label} | {len(ids)} | {ma:.0%} | {mb:.0%} | {mb - ma:+.0%} | [{lo:+.0%}, {hi:+.0%}] | {stxt} |")

    print("\n| Group | Cases | Pass A | Pass B | B-A | 95% CI | Score A | Score B | Score B-A [95% CI] |\n"
          "|---|---|---|---|---|---|---|---|---|")
    for split in ("holdout", "dev", "guard"):  # holdout decides; dev only shows whether the change fit its own examples
        line(f"**{split}**", [i for i, c in cases.items() if c.get("split") == split])
    for cls in sorted({c.get("cls") for c in cases.values() if c.get("cls")}):
        line(cls, [i for i, c in cases.items() if c.get("cls") == cls])
    print(f"\ncost: A ${ca:.2f}, B ${cb:.2f}")
    print("\nCoverage: read-only replays of single turns. Errors in long multi-step tasks, in actions (commands, sends,\n"
          "deploys) and in judgment calls the judge cannot see are not measured here; a pass says nothing about them.")


if __name__ == "__main__":
    main()
