#!/usr/bin/env bash
# Connsys Jarvis - Pre-Compact Hook
# Context 壓縮前儲存快照（最可靠存檔點）

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
SNAPSHOT_FILE="$MEMORY_PATH/$ACTIVE_EXPERT/$TODAY/${NOW}-pre-compact-snapshot.md"

cat > "$SNAPSHOT_FILE" << EOF
---
type: pre-compact-snapshot
expert: $ACTIVE_EXPERT
timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
---

# Pre-Compact Snapshot

Context 壓縮前自動儲存。
EOF

log_info "Pre-compact snapshot saved: $SNAPSHOT_FILE"
