#!/usr/bin/env bash
# Connsys Jarvis - Mid-Session Checkpoint Hook
# 每 20 訊息存一次

set -euo pipefail
source "$(dirname "$0")/framework-base-expert-shared-utils.sh"

MEMORY_PATH="${CONNSYS_JARVIS_MEMORY_PATH:-}"
ACTIVE_EXPERT="${CONNSYS_JARVIS_ACTIVE_EXPERT:-unknown}"
TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H:%M)

if [ -z "$MEMORY_PATH" ]; then
    exit 0
fi

mkdir -p "$MEMORY_PATH/$ACTIVE_EXPERT/$TODAY"
CHECKPOINT_FILE="$MEMORY_PATH/$ACTIVE_EXPERT/$TODAY/${NOW}-checkpoint.md"

cat > "$CHECKPOINT_FILE" << EOF
---
type: mid-session-checkpoint
expert: $ACTIVE_EXPERT
timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
---

# Mid-Session Checkpoint
EOF

log_info "Checkpoint saved: $CHECKPOINT_FILE"
