#!/bin/bash
# tools/eval: the mirror of business/ and user/ never harms the originals; the judge's deterministic checks.
. "$(dirname "$0")/lib.sh"

test_mirror_is_hardlinks_and_removal_keeps_originals() {
  d=$(new_tmp); mkdir -p "$d/src/a/b" "$d/src/node_modules"
  echo keep > "$d/src/a/b/f.txt"; echo ro > "$d/src/a/ro.txt"; chmod a-w "$d/src/a/ro.txt"; echo x > "$d/src/node_modules/m.js"
  R="$REPO" D="$d" PYTHONIOENCODING=utf-8 python3 - <<'EOF' || fail "mirror/remove raised"
import os, sys
sys.path.insert(0, os.path.join(os.environ["R"], "tools", "eval")); sys.argv = ["replay.py"]
import replay
d = os.environ["D"]
n = replay.mirror(os.path.join(d, "src"), os.path.join(d, "dst"))
assert n == 1, f"expected 1 linked file (read-only and node_modules skipped), got {n}"
assert os.path.samefile(os.path.join(d, "src/a/b/f.txt"), os.path.join(d, "dst/a/b/f.txt")), "not a hardlink"
assert not os.path.exists(os.path.join(d, "dst/a/ro.txt")), "read-only file mirrored"
assert not os.path.exists(os.path.join(d, "dst/node_modules")), "skipped dir mirrored"
replay.remove_mirror(os.path.join(d, "dst"), os.path.join(d, "src"))
assert not os.path.exists(os.path.join(d, "dst")), "mirror not removed"
EOF
  assert_eq "$(cat "$d/src/a/b/f.txt")" "keep" "original intact after removal"
  assert_eq "$(cat "$d/src/a/ro.txt")" "ro" "read-only original intact"
  [ -w "$d/src/a/ro.txt" ] && fail "read-only original became writable"
  chmod u+w "$d/src/a/ro.txt"
}

test_remove_mirror_refuses_directory_links() {
  . "$REPO/tools/lib/link.sh"
  d=$(new_tmp); mkdir -p "$d/target"; echo precious > "$d/target/p"; dir_link "$d/target" "$d/lnk"
  out=$(R="$REPO" D="$d" PYTHONIOENCODING=utf-8 python3 - 2>&1 <<'EOF'
import os, sys
sys.path.insert(0, os.path.join(os.environ["R"], "tools", "eval")); sys.argv = ["replay.py"]
import replay
d = os.environ["D"]
try:
    replay.remove_mirror(os.path.join(d, "lnk"), os.path.join(d, "target"))
    print("REMOVED")
except RuntimeError as e:
    print("REFUSED", e)
EOF
)
  assert_contains "$out" "REFUSED"
  assert_eq "$(cat "$d/target/p")" "precious" "link target intact"
  [ "$(os_variant)" = win ] && cmd //c rmdir "$(cygpath -w "$d/lnk")" >/dev/null
  true
}

test_judge_auto_checks() {
  out=$(R="$REPO" PYTHONIOENCODING=utf-8 python3 - <<'EOF'
import os, sys
sys.path.insert(0, os.path.join(os.environ["R"], "tools", "eval")); import judge
c = {"auto": {"contains_any": ["42"], "calls_any": ["Read"], "max_calls": 2}}
print(judge.auto_check(c, "There are 42.", [{"name": "Read", "input": ""}])[0],
      judge.auto_check(c, "There are 41.", [{"name": "Read", "input": ""}])[0],
      judge.auto_check(c, "42", [])[0],
      judge.auto_check(c, "42", [{"name": "Read", "input": ""}] * 3)[0],
      judge.auto_check({}, "x", [])[0])
EOF
)
  assert_eq "$out" "True False False False None" "pass, wrong value, no read, too many calls, no auto block"
}

test_readonly_guard_allowlist() {
  for t in Read Grep Glob WebSearch WebFetch; do
    printf '{"tool_name":"%s"}' "$t" | python3 "$REPO/tools/eval/readonly_guard.py" 2>/dev/null || fail "$t blocked"
  done
  for t in Edit Write Bash PowerShell Artifact Agent mcp__x__y SomeFutureTool; do
    printf '{"tool_name":"%s"}' "$t" | python3 "$REPO/tools/eval/readonly_guard.py" 2>/dev/null
    [ $? = 2 ] || fail "$t not blocked with exit 2"
  done
}

test_readonly_guard_confine() {
  d=$(new_tmp); mkdir -p "$d/wt/sub"
  wt=$(cd "$d/wt" && pwd -W 2>/dev/null || pwd)
  probe() {  # tool, input json -> exit code
    printf '{"tool_name":"%s","cwd":"%s","tool_input":%s}' "$1" "${wt//\\/\\\\}" "$2" \
      | python3 "$REPO/tools/eval/readonly_guard.py" --confine 2>/dev/null; echo $?
  }
  assert_eq "$(probe Read '{"file_path":"sub/a.md"}')" 0 "relative read inside"
  assert_eq "$(probe Glob '{"pattern":"**/*.md"}')" 0 "relative glob inside"
  assert_eq "$(probe Grep '{"pattern":"x","path":"sub"}')" 0 "grep inside"
  assert_eq "$(probe Read '{"file_path":"../outside.md"}')" 2 "read escaping with .."
  assert_eq "$(probe Glob '{"pattern":"../../**/*.md"}')" 2 "glob pattern escaping with .."
  assert_eq "$(probe Glob '{"pattern":"*.md","path":".."}')" 2 "glob path escaping"
  assert_eq "$(probe WebSearch '{"query":"x"}')" 2 "web is offline"
  if [ "$(uname -o 2>/dev/null)" = Msys ]; then
    assert_eq "$(probe Read '{"file_path":"/c/Windows/win.ini"}')" 2 "git-bash drive path"
    assert_eq "$(probe Read '{"file_path":"C:\\\\Windows\\\\win.ini"}')" 2 "absolute path elsewhere"
    assert_eq "$(probe Read '{"file_path":"/Windows/win.ini"}')" 2 "drive-relative path"
  fi
}

test_scoreboard_baseline_compare_and_fingerprint() {
  d=$(new_tmp)
  out=$(R="$REPO" H="$d" PYTHONIOENCODING=utf-8 python3 - 2>&1 <<'PY'
import json, os, subprocess, sys
R, H = os.environ["R"], os.environ["H"]
g = os.path.join(H, "golden"); os.makedirs(os.path.join(H, "data"))
cases = {f"H{i}": "holdout" for i in range(6)} | {f"D{i}": "dev" for i in range(4)} | {f"G{i}": "guard" for i in range(3)}
for cid, sp in cases.items():
    os.makedirs(os.path.join(g, cid)); json.dump({"id": cid, "kind": "target", "split": sp, "cls": "x"}, open(os.path.join(g, cid, "case.json"), "w"))
json.dump({"version": "t1", "world_sha256": "ab" * 32, "cases": {c: {} for c in cases}}, open(os.path.join(g, "manifest.json"), "w"))
json.dump({"core": list(cases), "extended": []}, open(os.path.join(g, "tiers.json"), "w"))
J = {"model": "sonnet", "votes": 3, "sha256": "f" * 16}
def runs(tag, rev, passes, cli="2.1.312", score=lambda c: 1.0):
    d = os.path.join(H, "runs", tag); os.makedirs(d)
    for cid in cases:
        for i in range(1, 5):
            ok = i <= passes(cid)
            json.dump({"case": cid, "run": i, "rev": rev, "model": "m", "cli": cli, "golden": "t1", "cost_usd": 0.1}, open(os.path.join(d, f"{cid}.{i}.json"), "w"))
            json.dump({"verdict": "PASS" if ok else "FAIL", "score": score(cid) if ok else 0.0, "judge": J}, open(os.path.join(d, f"{cid}.{i}.verdict.json"), "w"))
    return d
sb = lambda *a: subprocess.run([sys.executable, os.path.join(R, "tools", "eval", "scoreboard.py"), *a, "--cases", g, "--tier", "core"],
                               capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, WS_EVAL_HOME=H))
a = runs("A", "aaa", lambda c: 2 if c.startswith("H") else 4)
print(sb("compare", "--runs", a).returncode)                       # no baseline yet -> 2
print(sb("add", "--runs", a, "--baseline").returncode)             # 0
print(sb("add", "--runs", a, "--baseline").returncode)             # duplicate -> 1
b = runs("B", "bbb", lambda c: 4 if c.startswith("H") else 4)
print("GATE PASSED" in sb("compare", "--runs", b).stdout)          # holdout 50% -> 100%, guards kept
c = runs("C", "ccc", lambda c: 4 if c.startswith("H") else (0 if c == "G0" else 4))
print("fell from" in sb("compare", "--runs", c).stdout)            # a guard collapses
e = runs("E", "bbb", lambda c: 4, cli="9.9.9")
print(sb("compare", "--runs", e).returncode)                       # other CLI: no comparable baseline -> 2
f = runs("F", "fff", lambda c: 2 if c.startswith("H") else 4, score=lambda c: 0.6 if c[0] in "HD" else 1.0)
print("process:" in sb("compare", "--runs", f).stdout)             # same pass rates, process scores fall
json.dump({"core": [c for c in cases if c != "G2"], "extended": ["G2"]}, open(os.path.join(g, "tiers.json"), "w"))
print(sb("compare", "--runs", b).returncode)                       # core membership changed: no comparable baseline -> 2
print(os.path.exists(os.path.join(H, "data", "scoreboard.md")))
PY
)
  assert_eq "$(echo $out | tr -d '\r')" "2 0 1 True True 2 True 2 True" "scoreboard: baseline, duplicate, gate pass, guard fall, fingerprint mismatch, process fall, tier change"
}

test_stage_world_applies_overlay_as_of_cut() {
  d=$(new_tmp)
  out=$(R="$REPO" H="$d" PYTHONIOENCODING=utf-8 python3 - 2>&1 <<'PY'
import json, os, sys
R, H = os.environ["R"], os.environ["H"]
sys.path.insert(0, os.path.join(R, "tools", "eval")); sys.argv = ["replay.py"]
import replay
w = lambda p, s: (os.makedirs(os.path.dirname(p), exist_ok=True), open(p, "w").write(s))
g = os.path.join(H, "golden", "v"); case = os.path.join(g, "C1"); wt = os.path.join(H, "wt")
w(os.path.join(g, "world", "business", "a.py"), "today")
w(os.path.join(g, "world", "business", "new.py"), "added after the cut")
w(os.path.join(g, "world", "user", "u.md"), "u")
w(os.path.join(case, "overlay", "business", "a.py"), "at the cut")
json.dump({"overlay_deleted": ["business/new.py"]}, open(os.path.join(case, "case.json"), "w"))
os.makedirs(wt)
replay.stage_world(wt, case)
r = lambda *p: open(os.path.join(wt, *p)).read()
print(r("business", "a.py"), "|", os.path.exists(os.path.join(wt, "business", "new.py")), "|", r("user", "u.md"))
print(open(os.path.join(g, "world", "business", "a.py")).read())  # the frozen world itself is untouched
PY
)
  assert_eq "$(echo $out | tr -d '\r')" "at the cut | False | u today" "overlay wins, absent-then removed, world untouched"
}

test_verify_golden_catches_any_edit() {
  d=$(new_tmp)
  out=$(R="$REPO" H="$d" PYTHONIOENCODING=utf-8 python3 - 2>&1 <<'PY'
import hashlib, json, os, sys
R, H = os.environ["R"], os.environ["H"]
sys.path.insert(0, os.path.join(R, "tools", "eval")); sys.argv = ["replay.py"]
import replay
h = lambda b: hashlib.sha256(b).hexdigest()
g = os.path.join(H, "g"); os.makedirs(os.path.join(g, "world", "business")); os.makedirs(os.path.join(g, "C1"))
open(os.path.join(g, "world", "business", "a.md"), "wb").write(b"x")
world = {"business/a.md": h(b"x")}; json.dump(world, open(os.path.join(g, "world.json"), "w"))
case = json.dumps({"id": "C1"}).encode(); open(os.path.join(g, "C1", "case.json"), "wb").write(case)
json.dump({"version": "t", "world_sha256": h(json.dumps(world, sort_keys=True).encode()), "cases": {"C1": {"case_sha256": h(case)}}},
          open(os.path.join(g, "manifest.json"), "w"))
res = []
for edit in (None, ("world", "business", "a.md"), ("C1", "case.json")):
    if edit:
        p = os.path.join(g, *edit); b = open(p, "rb").read(); open(p, "wb").write(b + b" ")
    try:
        replay.verify_golden(g); res.append("ok")
    except RuntimeError:
        res.append("refused")
    if edit:
        open(p, "wb").write(b)
print(*res)
PY
)
  assert_eq "$(echo $out | tr -d '\r')" "ok refused refused" "intact set verifies; an edited world file or case is refused"
}

test_audit_stops_on_a_write_that_ran() {
  d=$(new_tmp)
  out=$(R="$REPO" WS_EVAL_HOME="$d" PYTHONIOENCODING=utf-8 python3 - 2>&1 <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ["R"], "tools", "eval")); sys.argv = ["replay.py"]
import replay
replay.EVAL_HOME = os.environ["WS_EVAL_HOME"]; os.makedirs(os.path.join(replay.EVAL_HOME, "data"))
replay.audit({"calls": [{"name": "Read", "ok": True}, {"name": "Edit", "ok": False}]}, "blocked-is-fine")
try:
    replay.audit({"calls": [{"name": "Edit", "ok": True}]}, "x")
    print("NOT STOPPED")
except replay.UnsafeReplay:
    print("STOPPED", os.path.exists(os.path.join(replay.EVAL_HOME, "data", "ALERT-unsafe-replay.json")))
PY
)
  assert_eq "$out" "STOPPED True" "a write that ran stops the eval and leaves an alert"
}

run_tests
