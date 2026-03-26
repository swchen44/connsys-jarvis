#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PASS=0; FAIL=0
check() { local d="$1" r="$2"; if [ "$r" = "true" ]; then echo "  PASS: $d"; ((PASS++)); else echo "  FAIL: $d"; ((FAIL++)); fi; }
[ -f "$SKILL_DIR/SKILL.md" ] && check "SKILL.md exists" "true" || check "SKILL.md exists" "false"
head -1 "$SKILL_DIR/SKILL.md" | grep -q "^---" && check "SKILL.md has frontmatter" "true" || check "SKILL.md has frontmatter" "false"
grep -q "^name:" "$SKILL_DIR/SKILL.md" && check "name field present" "true" || check "name field present" "false"
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
