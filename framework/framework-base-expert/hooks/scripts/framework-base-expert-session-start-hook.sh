#!/usr/bin/env bash
# Connsys Jarvis - Session Start Hook
# 載入上次摘要

set -euo pipefail
source "$(dirname "$0")/framework-base-expert-shared-utils.sh"

MEMORY_PATH="${CONNSYS_JARVIS_MEMORY_PATH:-}"
ACTIVE_EXPERT="${CONNSYS_JARVIS_ACTIVE_EXPERT:-unknown}"

if [ -z "$MEMORY_PATH" ]; then
    log_warn "CONNSYS_JARVIS_MEMORY_PATH 未設定，跳過 session-start hook"
    exit 0
fi

log_info "Session start: $ACTIVE_EXPERT"

# 讀取最新 session 摘要
WORKING_DIR="$MEMORY_PATH/working/$ACTIVE_EXPERT"
if [ -d "$WORKING_DIR" ]; then
    LATEST=$(find "$WORKING_DIR" -name "*.md" -type f | sort -r | head -1)
    if [ -n "$LATEST" ]; then
        log_info "最新記憶: $LATEST"
    fi
fi

touch "$MEMORY_PATH/.last-session" 2>/dev/null || true
