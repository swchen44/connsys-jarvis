#!/usr/bin/env bash
# Test: framework-memory-tool basic test

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "true" ]; then
        echo "  PASS: $desc"
        ((PASS++))
    else
        echo "  FAIL: $desc"
        ((FAIL++))
    fi
}

echo "=== Test: framework-memory-tool ==="

[ -f "$SKILL_DIR/SKILL.md" ] && check "SKILL.md exists" "true" || check "SKILL.md exists" "false"

# Test memory path env var handling
if [ -z "${CONNSYS_JARVIS_MEMORY_PATH:-}" ]; then
    check "CONNSYS_JARVIS_MEMORY_PATH unset (graceful degradation expected)" "true"
else
    [ -d "$CONNSYS_JARVIS_MEMORY_PATH" ] && check "memory path exists" "true" || check "memory path exists" "false"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
