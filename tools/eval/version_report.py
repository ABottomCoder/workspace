#!/usr/bin/env python3
"""Version run reports: one HTML page per scored run set, the shared history of how each workspace version did.

Written by `scoreboard.py add` into tools/eval/history/ as <YYYYMMDD-HHMM>_<rev8>_<golden>-<tier>.html, next to the
scoreboard itself; history/index.html lists them. A candidate's page carries its comparison with the baseline and
the gate verdict; a baseline's page carries the comparison with the previous baseline when one shares its fingerprint.

    python3 tools/eval/version_report.py <tag> [--tier core|all]    rewrite the page of a recorded entry
"""
import html, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.dirname(os.path.dirname(HERE))
HISTORY = os.path.join(HERE, "history")

CSS = """
:root{--bg:#f7f6f3;--surface:#fff;--ink:#1f2328;--muted:#6b6f76;--faint:#9a9ea5;--line:#e6e3dd;--line-strong:#d4d0c8;
--accent:#3b5b7a;--accent-soft:#e8eef4;--up:#2f6b4f;--up-soft:#e6f0ea;--down:#9a3b33;--down-soft:#f6e7e5;
--mono:ui-monospace,"SFMono-Regular","Cascadia Mono",Consolas,monospace;
--sans:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17191c;--surface:#1f2226;--ink:#e6e4df;--muted:#a0a3a8;
--faint:#73777d;--line:#2d3136;--line-strong:#3a3f45;--accent:#8fb0cf;--accent-soft:#24303b;--up:#7fbf9c;--up-soft:#1f2e27;
--down:#e09a91;--down-soft:#352321}}
:root[data-theme="dark"]{--bg:#17191c;--surface:#1f2226;--ink:#e6e4df;--muted:#a0a3a8;--faint:#73777d;--line:#2d3136;
--line-strong:#3a3f45;--accent:#8fb0cf;--accent-soft:#24303b;--up:#7fbf9c;--up-soft:#1f2e27;--down:#e09a91;--down-soft:#352321}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.7 var(--sans)}
.page{max-width:960px;margin:0 auto;padding:48px 24px 80px}.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;
color:var(--faint);margin:0 0 8px}h1{font-size:26px;line-height:1.3;font-weight:600;margin:0 0 10px}
h2{font-size:17px;font-weight:600;margin:40px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.muted{color:var(--muted)}code{font:13px/1.5 var(--mono);background:var(--accent-soft);color:var(--accent);padding:1px 5px;
border-radius:4px;word-break:break-all}.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:24px 0 4px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px}.tile .k{font-size:12px;color:var(--muted)}
.tile .v{font-size:24px;font-weight:600;font-variant-numeric:tabular-nums}.tile .n{font-size:12px;color:var(--faint)}
.table-wrap{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:8px 14px;text-align:left;border-bottom:1px solid var(--line);
white-space:nowrap}tr:last-child td{border-bottom:0}th{font-size:12px;font-weight:600;color:var(--muted);background:var(--bg)}
.num{text-align:right;font-variant-numeric:tabular-nums}.up{color:var(--up)}.down{color:var(--down)}.ci{color:var(--faint)}
.pill{display:inline-block;font-size:12px;line-height:1;padding:5px 9px;border-radius:999px;font-weight:600}
.pill.pass{color:var(--up);background:var(--up-soft)}.pill.fail{color:var(--down);background:var(--down-soft)}
.pill.base{color:var(--accent);background:var(--accent-soft)}.verdict{background:var(--surface);border:1px solid var(--line);
border-radius:10px;padding:14px 18px;margin:12px 0}a{color:var(--accent)}
@media (max-width:720px){.page{padding:32px 16px 60px}.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""


def esc(x):
    return html.escape(str(x))


def page(title, body):
    return (f'<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{esc(title)}</title>\n'
            f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"page\">\n{body}\n</div>\n</body>\n</html>\n")


def name_of(e):
    stamp = e["date"][:16].replace("-", "").replace("T", "-").replace(":", "")
    return f"{stamp}_{e['rev'][:8]}_{e['golden']}-{e['tier']}.html"


def changed_files(base_rev, rev):
    """The framework files that differ between two versions (the eval kit itself excluded)."""
    try:
        out = subprocess.run(["git", "-C", MAIN, "diff", "--stat=120", f"{base_rev}..{rev}", "--", ".",
                              ":(exclude)tools/eval"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except (subprocess.CalledProcessError, OSError):
        return None
    return [l.strip() for l in out.splitlines() if l.strip()]


def pct(x):
    return "—" if x is None else f"{x:.0%}"


def signed(x, fmt="{:+.0%}"):
    cls = "up" if x > 0 else "down" if x < 0 else ""
    return f'<span class="{cls}">{fmt.format(x)}</span>'


def render(e, base=None, comparison=None):
    """comparison: (rows, score, verdict) from scoreboard.compare_data, or None."""
    g = e["groups"]
    role = '<span class="pill base">基线</span>' if e.get("baseline") else "候选"
    verdict_pill = ""
    if comparison:
        ok = comparison[2].startswith("GATE PASSED") or comparison[2].startswith("no drift")
        verdict_pill = f'<span class="pill {"pass" if ok else "fail"}">{esc(comparison[2].split(":")[0].split(".")[0])}</span>'
    tiles = [("holdout", pct(g.get("holdout", {}).get("pass")), f"{g.get('holdout', {}).get('cases', 0)} 题"),
             ("dev", pct(g.get("dev", {}).get("pass")), f"{g.get('dev', {}).get('cases', 0)} 题"),
             ("guard", pct(g.get("guard", {}).get("pass")), f"{g.get('guard', {}).get('cases', 0)} 题"),
             ("每次运行", f"${e['cost_per_run']:.3f}", f"共 ${e['cost_usd']:.2f}")]
    b = [f'<p class="eyebrow">workspace 版本运行报告 · {esc(e["date"][:16].replace("T", " "))}</p>',
         f"<h1><code>{esc(e['rev'][:12])}</code> 在 {esc(e['golden'])} / {esc(e['tier'])} 上的成绩 {role}</h1>",
         f'<p class="muted">k = {e["k"]} · 模型 {esc(e["model"])} · CLI {esc(e["cli"])} · 判官 {esc(e["judge"].get("model"))}'
         f' ×{esc(e["judge"].get("votes"))} <code>{esc(e["judge"].get("sha256", "")[:8])}</code> · 运行集 {esc(e["tag"])}</p>',
         '<div class="tiles">' + "".join(f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="n">{n}</div></div>'
                                          for k, v, n in tiles) + "</div>"]
    if e.get("note"):
        b.append(f'<p class="muted">{esc(e["note"])}</p>')
    if base:
        b.append(f"<h2>对比 {'上一个基线' if e.get('baseline') else '当前基线'} <span class=\"muted\">· "
                 f"<code>{esc(base['rev'][:12])}</code> {esc(base['date'][:10])} · {esc(base['tag'])}</span> {verdict_pill}</h2>")
        rows, score, verdict = comparison
        t = ['<div class="table-wrap"><table><tr><th>组</th><th class="num">题数</th><th class="num">基线</th>'
             '<th class="num">本版本</th><th class="num">差</th><th class="num">95% CI</th></tr>']
        for name, n, mb, mn, lo, hi in rows:
            t.append(f'<tr><td>{esc(name)}</td><td class="num">{n}</td><td class="num">{pct(mb)}</td><td class="num">{pct(mn)}</td>'
                     f'<td class="num">{signed(mn - mb)}</td><td class="num ci">[{lo:+.0%}, {hi:+.0%}]</td></tr>')
        if score:
            n, sb, sn, d, lo, hi = score
            t.append(f'<tr><td>过程分（dev + holdout）</td><td class="num">{n}</td><td class="num">{sb:.2f}</td><td class="num">{sn:.2f}</td>'
                     f'<td class="num">{signed(d, "{:+.2f}")}</td><td class="num ci">[{lo:+.2f}, {hi:+.2f}]</td></tr>')
        b.append("".join(t) + "</table></div>")
        b.append(f'<div class="verdict">{esc(verdict)}</div>')
        files = changed_files(base["rev"], e["rev"])
        if files is not None:
            b.append("<h2>相对该基线改动的框架文件 <span class=\"muted\">· 不含 tools/eval</span></h2>")
            b.append('<div class="table-wrap"><table>' + ("".join(f"<tr><td><code>{esc(l)}</code></td></tr>" for l in files)
                                                          or '<tr><td class="muted">无（同一版本或只改了评测工具）</td></tr>') + "</table></div>")
    else:
        b.append('<h2>对比</h2><p class="muted">没有同一指纹的更早基线：这是该测试集、模型、CLI、判官组合下的第一份成绩。</p>')
    b.append("<h2>各组</h2>")
    t = ['<div class="table-wrap"><table><tr><th>组</th><th class="num">题数</th><th class="num">通过率</th><th class="num">分数</th></tr>']
    for name, s in g.items():
        sc = "—" if s["score"] is None else f"{s['score']:.2f}"
        t.append(f'<tr><td>{esc(name)}</td><td class="num">{s["cases"]}</td><td class="num">{pct(s["pass"])}</td>'
                 f'<td class="num">{sc}</td></tr>')
    b.append("".join(t) + "</table></div>")
    b.append("<h2>每题</h2>")
    t = ['<div class="table-wrap"><table><tr><th>题</th><th>分组</th><th class="num">通过</th><th class="num">分数</th>'
         + ('<th class="num">基线通过</th>' if base else "") + "</tr>"]
    split = {i: s for s, ids in (e.get("group_ids") or {}).items() if s in ("holdout", "dev", "guard") for i in ids}
    for cid in sorted(e["cases"]):
        p, n, sc = e["cases"][cid]
        bp = base["cases"].get(cid) if base else None
        t.append(f"<tr><td>{esc(cid)}</td><td class=\"muted\">{esc(split.get(cid, ''))}</td><td class=\"num\">{p}/{n}</td>"
                 f"<td class=\"num\">{'—' if sc is None else f'{sc:.2f}'}</td>"
                 + (f"<td class=\"num ci\">{bp[0]}/{bp[1]}</td>" if base and bp else ("<td></td>" if base else "")) + "</tr>")
    b.append("".join(t) + "</table></div>")
    b.append('<p class="muted">只读回放、单轮：长任务里的多步错误、真实动作和判官看不到的判断不在测量范围内。'
             '原始运行与判分留在本地 eval 数据目录，本页只存汇总。</p>')
    return page(f"{e['rev'][:8]} · {e['golden']} {e['tier']}", "\n".join(b))


def write_index(entries):
    rows = []
    for e in reversed(entries):
        g = e["groups"]
        role = '<span class="pill base">基线</span>' if e.get("baseline") else "候选"
        rows.append(f"<tr><td>{esc(e['date'][:16].replace('T', ' '))}</td><td><code>{esc(e['rev'][:8])}</code></td>"
                    f"<td>{role}</td><td>{esc(e['golden'])} / {esc(e['tier'])}</td>"
                    f"<td class=\"num\">{pct(g.get('holdout', {}).get('pass'))}</td><td class=\"num\">{pct(g.get('dev', {}).get('pass'))}</td>"
                    f"<td class=\"num\">{pct(g.get('guard', {}).get('pass'))}</td><td><a href=\"{esc(e.get('report') or '')}\">报告</a></td></tr>")
    body = ('<p class="eyebrow">workspace 评测历史</p><h1>各版本成绩</h1>'
            '<p class="muted">每行一个打过分的运行集，新的在上。只比较同一测试集、分层、模型、CLI、判官下的行（指纹见各报告）。</p>'
            '<div class="table-wrap"><table><tr><th>时间</th><th>版本</th><th>角色</th><th>测试集 / 分层</th><th class="num">holdout</th>'
            '<th class="num">dev</th><th class="num">guard</th><th></th></tr>' + "".join(rows) + "</table></div>")
    open(os.path.join(HISTORY, "index.html"), "w", encoding="utf-8", newline="\n").write(page("评测历史", body))


def main():
    sys.path.insert(0, HERE)
    import scoreboard
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    tier = args[args.index("--tier") + 1] if "--tier" in args else None
    hits = [e for e in scoreboard.board() if e["tag"] == args[0] and (not tier or e["tier"] == tier)]
    if not hits:
        sys.exit(f"no entry {args[0]} on {scoreboard.BOARD}")
    for e in hits:
        print(scoreboard.write_report(e))


if __name__ == "__main__":
    main()
