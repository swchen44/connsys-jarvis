#!/usr/bin/env bash
# Connsys Jarvis - Session End Hook
# 儲存 session 摘要

set -euo pipefail
source "$(dirname "$0")/shared-utils.sh"

MEMORY_PATH="${CONNSYS_JARVIS_MEMORY_PATH:-}"
ACTIVE_EXPERT="${CONNSYS_JARVIS_ACTIVE_EXPERT:-unknown}"
TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H:%M)

if [ -z "$MEMORY_PATH" ]; then
    log_warn "CONNSYS_JARVIS_MEMORY_PATH 未設定，跳過 session-end hook"
    exit 0
fi

mkdir -p "$MEMORY_PATH/$ACTIVE_EXPERT/$TODAY"
MEMORY_FILE="$MEMORY_PATH/$ACTIVE_EXPERT/$TODAY/${NOW}-${ACTIVE_EXPERT}-memory.md"

cat > "$MEMORY_FILE" << EOF
---
expert: $ACTIVE_EXPERT
date: $TODAY
time: $NOW
---

# Session Summary

Session ended at $NOW on $TODAY.
EOF

log_info "Session memory saved: $MEMORY_FILE"
touch "$MEMORY_PATH/.last-session"
