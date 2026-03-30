#!/bin/bash
# Basic structural verification for framework-skill-create-flow
set -e

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

echo "=== framework-skill-create-flow: basic test ==="

# SKILL.md exists
[ -f "$SKILL_DIR/SKILL.md" ] && pass "SKILL.md exists" || fail "SKILL.md missing"

# Required frontmatter fields
for field in name description version domain type scope; do
  grep -q "^${field}:" "$SKILL_DIR/SKILL.md" && pass "frontmatter: $field" || fail "frontmatter missing: $field"
done

# README.md exists
[ -f "$SKILL_DIR/README.md" ] && pass "README.md exists" || fail "README.md missing"

# Key reference files from upstream skill-creator
[ -f "$SKILL_DIR/agents/grader.md" ]          && pass "agents/grader.md exists"      || fail "agents/grader.md missing"
[ -f "$SKILL_DIR/references/schemas.md" ]     && pass "references/schemas.md exists" || fail "references/schemas.md missing"
[ -f "$SKILL_DIR/assets/eval_review.html" ]   && pass "assets/eval_review.html exists" || fail "assets/eval_review.html missing"

echo ""
echo "All checks passed."
