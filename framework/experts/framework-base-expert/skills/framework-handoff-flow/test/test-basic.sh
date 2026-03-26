#!/usr/bin/env bash
# Test: framework-handoff-flow basic test
# Verifies handoff directory structure and SKILL.md format

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

echo "=== Test: framework-handoff-flow ==="

# Test 1: SKILL.md exists
[ -f "$SKILL_DIR/SKILL.md" ] && check "SKILL.md exists" "true" || check "SKILL.md exists" "false"

# Test 2: SKILL.md has frontmatter
if [ -f "$SKILL_DIR/SKILL.md" ]; then
    head -1 "$SKILL_DIR/SKILL.md" | grep -q "^---" && check "SKILL.md has YAML frontmatter" "true" || check "SKILL.md has YAML frontmatter" "false"
fi

# Test 3: SKILL.md has required fields
if [ -f "$SKILL_DIR/SKILL.md" ]; then
    grep -q "^name:" "$SKILL_DIR/SKILL.md" && check "SKILL.md has name field" "true" || check "SKILL.md has name field" "false"
    grep -q "^type:" "$SKILL_DIR/SKILL.md" && check "SKILL.md has type field" "true" || check "SKILL.md has type field" "false"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
