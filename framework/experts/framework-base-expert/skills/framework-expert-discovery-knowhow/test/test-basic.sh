#!/usr/bin/env bash
# Test: framework-expert-discovery-knowhow basic test
# Verifies registry.json is readable and contains expected experts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../../../../.." && pwd)"
REGISTRY="$REPO_ROOT/connsys-jarvis/registry.json"

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

echo "=== Test: framework-expert-discovery-knowhow ==="

# Test 1: registry.json exists
[ -f "$REGISTRY" ] && check "registry.json exists" "true" || check "registry.json exists" "false"

# Test 2: registry has experts
if command -v python3 &>/dev/null && [ -f "$REGISTRY" ]; then
    COUNT=$(python3 -c "import json; d=json.load(open('$REGISTRY')); print(len(d['experts']))")
    [ "$COUNT" -gt 0 ] && check "registry has experts (count=$COUNT)" "true" || check "registry has experts" "false"
fi

# Test 3: framework-base-expert exists in registry
if [ -f "$REGISTRY" ]; then
    python3 -c "
import json, sys
d = json.load(open('$REGISTRY'))
names = [e['name'] for e in d['experts']]
sys.exit(0 if 'framework-base-expert' in names else 1)
" && check "framework-base-expert in registry" "true" || check "framework-base-expert in registry" "false"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
