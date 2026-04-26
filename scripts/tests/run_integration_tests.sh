#!/usr/bin/env bash
# ============================================================
# Connsys Jarvis — Integration Test Runner
# 依據 doc/test_plan.md 執行 TC-01 ~ TC-16
#
# 用法（從任意目錄執行）：
#   bash connsys-jarvis/scripts/tests/run_integration_tests.sh
#
# 用 tmux 在背景執行並等待完成：
#   SESSION="connsys-jarvis"
#   tmux new-session -d -s "$SESSION" -x 200 -y 60
#   tmux send-keys -t "$SESSION" \
#     "bash connsys-jarvis/scripts/tests/run_integration_tests.sh; tmux wait-for -S ${SESSION}-done" Enter
#   tmux wait-for "${SESSION}-done"
#
# 需求：
#   - Python 3.8+
#   - macOS / Linux（需要 symlink 支援）
# ============================================================

# ── 自動定位 connsys-jarvis 根目錄 ──────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARVIS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"   # scripts/tests → scripts → connsys-jarvis
SETUP="python3 ${JARVIS_DIR}/scripts/setup.py"

# ── 測試 workspace ──────────────────────────────────────────
WS="/tmp/connsys-jarvis-test"
WS_LEGACY="/tmp/connsys-jarvis-legacy"

# ── 計數 ────────────────────────────────────────────────────
PASS=0; FAIL=0

# ── helpers ──────────────────────────────────────────────────
ok()   { echo "  ✅ $*"; PASS=$((PASS+1)); }
fail() { echo "  ❌ $* — FAIL"; FAIL=$((FAIL+1)); }

hr() {
    echo
    echo "═══════════════════════════════════════════════════"
    echo "$1"
    echo "═══════════════════════════════════════════════════"
}

assert_contains() {
    local label="$1" val="$2" pattern="$3"
    if echo "$val" | grep -qF "$pattern"; then ok "$label"
    else fail "$label (expected: '$pattern')"; fi
}

assert_exists()     { if [ -e "$1" ]; then ok "exists: $1"; else fail "not found: $1"; fi; }
assert_not_exists() { if [ ! -e "$1" ]; then ok "not exists: $1"; else fail "should not exist: $1"; fi; }

assert_eq() {
    local label="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then ok "$label ($actual)"
    else fail "$label (expected=$expected, actual=$actual)"; fi
}

# ============================================================
echo "Connsys Jarvis Integration Tests"
echo "JARVIS_DIR : $JARVIS_DIR"
echo "Workspace  : $WS"
echo "Date       : $(date '+%Y-%m-%d %H:%M:%S')"

# ============================================================
hr "TC-01: --init (framework-base-expert)"
# ============================================================
rm -rf "$WS" && mkdir -p "$WS"
ln -sfn "$JARVIS_DIR" "$WS/connsys-jarvis"

out=$(cd "$WS" && $SETUP --init framework/framework-base-expert/expert.json 2>&1)
assert_contains "TC-01-1 success message"            "$out" "Done! Expert 'framework-base-expert' installed"
assert_exists   "$WS/.claude"
assert_exists   "$WS/CLAUDE.md"
assert_exists   "$WS/.connsys-jarvis/.env"
assert_exists   "$WS/.connsys-jarvis/.installed-experts.json"
assert_contains "TC-01-2 CLAUDE.md has using-knowhow" "$(cat "$WS/CLAUDE.md")" "using-knowhow"
assert_contains "TC-01-3 CLAUDE.md has Guidelines"   "$(cat "$WS/CLAUDE.md")" "## Expert Guidelines"
assert_contains "TC-01-4 CLAUDE.md has MUST"         "$(cat "$WS/CLAUDE.md")" "MUST use the skill"
assert_contains "TC-01-6 .env has CONNSYS_JARVIS_PATH" "$(cat "$WS/.connsys-jarvis/.env")" "CONNSYS_JARVIS_PATH"
assert_contains "TC-01-7 .installed-experts.json"   "$(cat "$WS/.connsys-jarvis/.installed-experts.json")" "framework-base-expert"
# ── 新增：自動建立的目錄 ──
assert_exists   "$WS/codespace"
assert_exists   "$WS/.connsys-jarvis/memory"

# ============================================================
hr "TC-02: --add (wifi-bora-memory-slim-expert)"
# ============================================================
out=$(cd "$WS" && $SETUP --add wifi-bora/wifi-bora-memory-slim-expert/expert.json 2>&1)
assert_contains "TC-02-1 success message"            "$out" "Done! Expert 'wifi-bora-memory-slim-expert' added"
assert_contains "TC-02-2 idempotent [=] markers"     "$out" "[=]"
assert_contains "TC-02-3 new [+] markers"            "$out" "[+]"

installed=$(python3 -c "import json; d=json.load(open('$WS/.connsys-jarvis/.installed-experts.json')); print(len(d['experts']))")
assert_eq "TC-02-4 2 experts installed" "$installed" "2"

is_id=$(python3 -c "import json; d=json.load(open('$WS/.connsys-jarvis/.installed-experts.json')); e=[x for x in d['experts'] if x['name']=='wifi-bora-memory-slim-expert'][0]; print(e['is_identity'])")
assert_contains "TC-02-5 wifi-bora is identity"      "$is_id" "True"

# v2.0: include_all_experts removed

# ============================================================
hr "TC-03: --doctor (正常狀態)"
# ============================================================
out=$(cd "$WS" && $SETUP --doctor 2>&1)
assert_contains "TC-03-1 doctor header"              "$out" "Connsys Jarvis Doctor"
assert_contains "TC-03-2 overall healthy"            "$out" "Overall: ✅ Healthy"
assert_contains "TC-03-3 section A"                  "$out" "A. System Info"
assert_contains "TC-03-4 section B"                  "$out" "B. Environment Variables"
assert_contains "TC-03-5 section C"                  "$out" "C. Symlink Integrity"
assert_contains "TC-03-6 section D"                  "$out" "D. CLAUDE.md Validation"
assert_contains "TC-03-7 section E"                  "$out" "E. Tools"
assert_contains "TC-03-8 section F"                  "$out" "F. Expert Structure"

# ============================================================
hr "TC-04: .env 環境變數"
# ============================================================
env_content=$(cat "$WS/.connsys-jarvis/.env")
assert_contains "TC-04-1 CONNSYS_JARVIS_PATH"        "$env_content" "CONNSYS_JARVIS_PATH"
assert_contains "TC-04-2 WORKSPACE_ROOT_PATH"         "$env_content" "WORKSPACE_ROOT_PATH"
assert_contains "TC-04-3 CODE_SPACE_PATH"             "$env_content" "CODE_SPACE_PATH"
assert_contains "TC-04-4 MEMORY_PATH"                 "$env_content" "MEMORY_PATH"
assert_contains "TC-04-5 EMPLOYEE_ID"                 "$env_content" "EMPLOYEE_ID"
assert_contains "TC-04-6 ACTIVE_EXPERT"               "$env_content" "ACTIVE_EXPERT"
assert_contains "TC-04-7 CODE_SPACE=codespace"        "$env_content" "codespace"

# ============================================================
hr "TC-05: --remove (wifi-bora-memory-slim-expert)"
# ============================================================
out=$(cd "$WS" && $SETUP --remove wifi-bora-memory-slim-expert 2>&1)
assert_contains "TC-05-1 success message"            "$out" "Done! Expert 'wifi-bora-memory-slim-expert' removed"
assert_contains "TC-05-2 symlinks cleared"           "$out" "All symlinks cleared"

remaining=$(python3 -c "import json; d=json.load(open('$WS/.connsys-jarvis/.installed-experts.json')); print(len(d['experts']))")
assert_eq "TC-05-3 1 expert remains" "$remaining" "1"

remaining_name=$(python3 -c "import json; d=json.load(open('$WS/.connsys-jarvis/.installed-experts.json')); print(d['experts'][0]['name'])")
assert_contains "TC-05-4 framework still installed"  "$remaining_name" "framework-base-expert"

# ============================================================
hr "TC-06: Legacy 場景 (.repo)"
# ============================================================
rm -rf "$WS_LEGACY" && mkdir -p "$WS_LEGACY/.repo"
ln -sfn "$JARVIS_DIR" "$WS_LEGACY/connsys-jarvis"
cd "$WS_LEGACY" && $SETUP --init framework/framework-base-expert/expert.json > /dev/null 2>&1
env_legacy=$(cat "$WS_LEGACY/.connsys-jarvis/.env")
if echo "$env_legacy" | grep "CODE_SPACE_PATH" | grep -qv "codespace"; then
    ok "TC-06-1 legacy CODE_SPACE_PATH has no codespace/"
else
    fail "TC-06-1 legacy CODE_SPACE_PATH should not contain codespace"
fi
assert_exists "$WS_LEGACY/.repo"
# legacy 不應建立 codespace/
assert_not_exists "$WS_LEGACY/codespace"

# ============================================================
hr "TC-07: --uninstall (保留 memory/)"
# ============================================================
mkdir -p "$WS/.connsys-jarvis/memory/test"
touch "$WS/.connsys-jarvis/memory/test/note.md"
out=$(cd "$WS" && $SETUP --uninstall 2>&1)
assert_contains "TC-07-1 done message"               "$out" "Done! Kept"
assert_not_exists "$WS/CLAUDE.md"
assert_exists   "$WS/.connsys-jarvis/memory/test/note.md"

# ============================================================
hr "TC-08: --list (installed + available)"
# ============================================================
rm -rf "$WS" && mkdir -p "$WS"
ln -sfn "$JARVIS_DIR" "$WS/connsys-jarvis"
cd "$WS" && $SETUP --init framework/framework-base-expert/expert.json > /dev/null 2>&1
cd "$WS" && $SETUP --add  wifi-bora/wifi-bora-memory-slim-expert/expert.json > /dev/null 2>&1

out=$(cd "$WS" && $SETUP --list 2>&1)
assert_contains "TC-08-1 Expert List header"         "$out" "Expert List"
assert_contains "TC-08-2 framework-base-expert"      "$out" "framework-base-expert"
assert_contains "TC-08-3 wifi-bora listed"           "$out" "wifi-bora-memory-slim-expert"
assert_contains "TC-08-4 Installed count"            "$out" "Installed:"

cd "$WS" && $SETUP --list --format json > /tmp/cj_list.json 2>&1
if python3 -c "import json,sys; data=json.load(open('/tmp/cj_list.json')); assert isinstance(data,dict); assert 'experts' in data; assert 'skills' in data" 2>/dev/null; then
    ok "TC-08-5 --list --format json valid JSON object with experts+skills"
else
    fail "TC-08-5 --list --format json invalid"
fi

# ============================================================
hr "TC-11: dangling symlink 偵測 (--doctor)"
# ============================================================
ln -sf /nonexistent/path "$WS/.claude/skills/fake-dangling-skill"
out=$(cd "$WS" && $SETUP --doctor 2>&1)
assert_contains "TC-11-1 DANGLING detected"          "$out" "DANGLING"
assert_contains "TC-11-2 overall not healthy"        "$out" "Overall: ❌"
rm -f "$WS/.claude/skills/fake-dangling-skill"

# ============================================================
hr "TC-13: CLAUDE.md v2.0 format (## Identity + ## Technical Reference)"
# ============================================================
rm -rf "$WS" && mkdir -p "$WS"
ln -sfn "$JARVIS_DIR" "$WS/connsys-jarvis"
cd "$WS" && $SETUP --init framework/framework-base-expert/expert.json > /dev/null 2>&1
cd "$WS" && $SETUP --add wifi-bora/wifi-bora-memory-slim-expert/expert.json > /dev/null 2>&1

claude_content=$(cat "$WS/CLAUDE.md")
assert_contains "TC-13-1 Expert Guidelines section"  "$claude_content" "## Expert Guidelines"
assert_contains "TC-13-2 using-knowhow directive"    "$claude_content" "using-knowhow"
assert_contains "TC-13-3 framework expert"           "$claude_content" "framework-base-expert-using-knowhow"
assert_contains "TC-13-4 wifi-bora expert"           "$claude_content" "wifi-bora-memory-slim-expert-using-knowhow"
assert_contains "TC-13-5 HTML comment header"        "$claude_content" "<!-- connsys-jarvis CLAUDE.md"

# ============================================================
hr "TC-14: --debug 日誌"
# ============================================================
rm -rf "$WS" && mkdir -p "$WS"
ln -sfn "$JARVIS_DIR" "$WS/connsys-jarvis"

debug_out=$(cd "$WS" && $SETUP --debug --init framework/framework-base-expert/expert.json 2>&1)
debug_count=$(echo "$debug_out" | grep -c "DEBUG" || true)
if [ "$debug_count" -gt 0 ]; then ok "TC-14-1 DEBUG lines in console ($debug_count lines)"
else fail "TC-14-1 no DEBUG in console"; fi

assert_exists "$WS/.connsys-jarvis/log/setup.log"
log_debug=$(grep -c "DEBUG" "$WS/.connsys-jarvis/log/setup.log" || true)
if [ "$log_debug" -gt 0 ]; then ok "TC-14-2 DEBUG written to log ($log_debug lines)"
else fail "TC-14-2 no DEBUG in log"; fi

nodebug_out=$(cd "$WS" && $SETUP --init framework/framework-base-expert/expert.json 2>&1)
nodebug_count=$(echo "$nodebug_out" | grep -c "DEBUG" || true)
if [ "$nodebug_count" -eq 0 ]; then ok "TC-14-3 no DEBUG in console without --debug"
else fail "TC-14-3 DEBUG leaked ($nodebug_count lines)"; fi

# ============================================================
hr "TC-15: --query"
# ============================================================
out=$(cd "$WS" && $SETUP --query framework-base-expert 2>&1)
assert_contains "TC-15-1 name shown"                 "$out" "framework-base-expert"
assert_contains "TC-15-2 status=installed"           "$out" "installed"
assert_contains "TC-15-3 domain shown"               "$out" "framework"

out_partial=$(cd "$WS" && $SETUP --query framework 2>&1)
assert_contains "TC-15-4 partial match works"        "$out_partial" "framework-base-expert"

cd "$WS" && $SETUP --query framework-base-expert --format json > /tmp/cj_query.json 2>&1
if python3 -c "import json,sys; d=json.load(open('/tmp/cj_query.json')); assert 'name' in d" 2>/dev/null; then
    ok "TC-15-5 --query --format json valid"
else
    fail "TC-15-5 --query --format json invalid"
fi

# ============================================================
hr "TC-16: --list --format json"
# ============================================================
cd "$WS" && $SETUP --list --format json > /tmp/cj_list16.json 2>&1
if python3 - /tmp/cj_list16.json <<'PYEOF' 2>/dev/null; then
import json, sys
data = json.load(open(sys.argv[1]))
assert isinstance(data, dict), "not a dict"
experts = data['experts']
skills = data['skills']
names = [e['name'] for e in experts]
assert 'framework-base-expert' in names, "framework-base-expert missing"
assert any(e['status']=='installed' and e['name']=='framework-base-expert' for e in experts), "status error"
assert len(skills) > 0, "no skills"
assert all('expert' in s and 'status' in s for s in skills), "skill missing fields"
PYEOF
    ok "TC-16 --list --format json structure correct"
else
    fail "TC-16 json structure error"
fi

# ============================================================
hr "TC-12: pytest 單元測試"
# ============================================================
cd "$JARVIS_DIR"
pytest_out=$(python3 -m pytest "${JARVIS_DIR}/scripts/tests/test_setup.py" -v 2>&1)
passed=$(echo "$pytest_out" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | tail -1)
failed=$(echo "$pytest_out" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' | tail -1)
passed=${passed:-0}; failed=${failed:-0}
echo "$pytest_out" | tail -3
if [ "$failed" -eq 0 ]; then ok "TC-12 pytest: $passed passed, 0 failed"
else fail "TC-12 pytest: $passed passed, $failed failed"; fi

# ============================================================
hr "SUMMARY"
# ============================================================
total=$((PASS + FAIL))
echo "  Total : $total"
echo "  ✅ Pass : $PASS"
echo "  ❌ Fail : $FAIL"
echo
if [ "$FAIL" -eq 0 ]; then
    echo "🎉 All tests passed!"
    exit 0
else
    echo "⚠️  $FAIL test(s) failed — see ❌ above"
    exit 1
fi
