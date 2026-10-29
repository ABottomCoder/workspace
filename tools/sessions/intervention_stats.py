#!/usr/bin/env python3
"""
Rebuild the intervention stats from the judged days. Deterministic: same inputs, same output.

    python3 tools/sessions/intervention_stats.py [--out <dir>]

Inputs:  <out>/days/index.json (scan_sessions.py), <out>/errors/<day>.json (journal_catchup.py),
         git history of lessons/ (the date each lesson heading first appeared).
Outputs: <out>/stats.md     two-week periods side by side, categories per period, lesson efficacy
         <out>/tracking.md  one line per confirmed error, newest first
Periods are 14 days starting on the Monday on or before the first day with conversation. Metrics
count judged days only; the coverage column says how many of the active days that is.
"""
import glob, json, os, subprocess, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scan_sessions import CATEGORIES, MAIN, flag  # noqa: E402

SIGNALS = ("fix-marker", "user-correction", "agent-admission")


def lesson_dates():
    """{"lessons/<file>: <heading>": "YYYY-MM-DD"} from the commit that first added the heading."""
    try:
        log = subprocess.run(["git", "-C", MAIN, "log", "--reverse", "--format=@@%as", "-p", "--unified=0", "--", "lessons"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}
    dates, when, path = {}, None, None
    for line in log.split("\n"):
        if line.startswith("@@") and not line.startswith("@@ "):
            when = line[2:].strip()
        elif line.startswith("+++ b/"):
            path = line[6:].strip()[:-3]
        elif line.startswith("+### ") and path:
            dates.setdefault(f"{path}: {line[5:].strip()}", when)
    return dates


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "—"


def main():
    out = flag(sys.argv[1:], "--out") or os.environ.get("INTERVENTION_OUT") or os.path.join(MAIN, "user", "intervention")
    index_path = os.path.join(out, "days", "index.json")
    if not os.path.exists(index_path):
        print(f"no {index_path}: run scan_sessions.py first")
        sys.exit(1)
    index = json.load(open(index_path, encoding="utf-8"))
    judged = {}
    for p in sorted(glob.glob(os.path.join(out, "errors", "*.json"))):
        j = json.load(open(p, encoding="utf-8"))
        judged[j["day"]] = j["errors"]
    if not index:
        print("no days with conversation")
        return

    first = date.fromisoformat(min(index))
    anchor = first - timedelta(days=first.weekday())
    today = datetime.now().astimezone().date()
    periods = defaultdict(lambda: {"active": 0, "judged": 0, "sessions": 0, "msgs": 0, "errors": [], "clean": 0})
    for d, v in index.items():
        k = (date.fromisoformat(d) - anchor).days // 14
        p = periods[k]
        p["active"] += 1
        if d in judged:
            p["judged"] += 1
            p["sessions"] += v["sessions"]
            p["msgs"] += v["user_msgs"]
            p["errors"] += judged[d]
            p["clean"] += not judged[d]

    all_errors = [e for d in sorted(judged) for e in judged[d]]
    L = ["# Intervention stats", "",
         "> Rebuilt by `tools/sessions/intervention_stats.py` from judged days; do not edit by hand.",
         "> Confirmed errors only: a `// fix:` marker, an explicit user correction, or an explicit agent admission.",
         "> Silent fixes by the user are invisible here, so true error counts can only be higher. Periods with few",
         "> messages are noisy: compare rates, not counts, and only between periods with similar volume.", "",
         f"**Judged days:** {len(judged)} of {len(index)} · **Latest judged day:** {max(judged) if judged else '—'} · "
         f"**Errors:** {len(all_errors)}", "",
         "## Two-week periods", "",
         "| Period | Judged / active days | Session-days | User msgs | Errors | Errors per 100 msgs | Clean days | Top category | Signals (marker / correction / admission) |",
         "|---|---|---|---|---|---|---|---|---|"]
    cat_rows = []
    for k in sorted(periods):
        p = periods[k]
        start = anchor + timedelta(days=14 * k)
        end = start + timedelta(days=13)
        label = f"{start:%Y-%m-%d} – {end:%m-%d}" + (" (in progress)" if end >= today else "")
        cats = Counter(e["category"] for e in p["errors"])
        sig = Counter(e["signal"] for e in p["errors"])
        top = cats.most_common(1)[0][0] if cats else "—"
        rate = f"{100 * len(p['errors']) / p['msgs']:.1f}" if p["msgs"] else "—"
        L.append(f"| {label} | {p['judged']} / {p['active']} | {p['sessions']} | {p['msgs']} | {len(p['errors'])} | {rate} | "
                 f"{pct(p['clean'], p['judged'])} | {top} | {' / '.join(str(sig[s]) for s in SIGNALS)} |")
        cat_rows.append(f"| {label} | " + " | ".join(str(cats[c]) for c in CATEGORIES) + " |")
    L += ["", "## Categories per period", "", "| Period | " + " | ".join(CATEGORIES) + " |",
          "|---|" + "---|" * len(CATEGORIES)] + cat_rows

    dates = lesson_dates()
    by_lesson = defaultdict(list)
    for e in all_errors:
        if e.get("lesson"):
            by_lesson[e["lesson"]].append(e["day"])
    L += ["", "## Lesson efficacy", "",
          "Errors that violate an existing lesson, split by the date the lesson was added (first commit with its",
          "heading; a renamed heading counts from the rename). Errors after the date mean the lesson is not working.", "",
          "| Lesson | Added | Errors before | Errors after | Last seen |", "|---|---|---|---|---|"]
    rows = []
    for lesson, days in by_lesson.items():
        added = dates.get(lesson)
        after = sum(1 for d in days if added and d >= added)
        rows.append((-after, -len(days), lesson, added or "?", len(days) - after if added else "?", after if added else "?", max(days)))
    for _, _, lesson, added, before, after, last in sorted(rows):
        L.append(f"| {lesson} | {added} | {before} | {after} | {last} |")
    uncovered = Counter(e["category"] for e in all_errors if not e.get("lesson"))
    L += ["", "## Errors no lesson covers", "", "| Category | Count |", "|---|---|"]
    L += [f"| {c} | {uncovered[c]} |" for c in CATEGORIES]
    open(os.path.join(out, "stats.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

    T = ["# Confirmed errors", "", "> Rebuilt by `tools/sessions/intervention_stats.py`; newest first.", ""]
    for e in sorted(all_errors, key=lambda e: (e["day"], e.get("time") or ""), reverse=True):
        lesson = f" · lesson: {e['lesson']}" if e.get("lesson") else ""
        T.append(f"- {e['day']} {e.get('time') or ''} `{e.get('session') or '?'}` [{e['category']} · {e['signal']}] "
                 f"{e.get('what') or ''}; cause: {e.get('root_cause') or ''}{lesson}")
    open(os.path.join(out, "tracking.md"), "w", encoding="utf-8", newline="\n").write("\n".join(T) + "\n")
    print(f"stats: {len(judged)} judged day(s), {len(all_errors)} error(s) -> {out}/stats.md")


if __name__ == "__main__":
    main()
