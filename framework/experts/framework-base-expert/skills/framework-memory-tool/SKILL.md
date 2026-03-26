---
name: framework-memory-tool
description: "操作 Connsys Jarvis 本地記憶系統，提供讀取、寫入、搜尋記憶的標準介面"
version: "1.0.0"
domain: framework
type: tool
scope: framework-base-expert
tags: [framework, memory, persistence, context]
---

# Framework Memory Tool

## 用途

提供操作 Connsys Jarvis 本地三區記憶系統的標準介面，確保跨 session 和跨 Expert 的知識持久化。

## 記憶系統架構

```
$CONNSYS_JARVIS_MEMORY_PATH/
├── shared/          ← 跨 Expert 共用的長期知識
│   ├── project-context.md    專案背景與重要決策
│   ├── team-conventions.md   團隊規範與慣例
│   └── known-issues.md       已知問題與解決方案
├── working/         ← 當前工作任務的暫存記錄
│   └── <expert>/
│       └── <YYYY-MM-DD>/
│           └── <task-name>.md
├── handoffs/        ← Expert 交接文件
│   └── <timestamp>-<from>-to-<to>.md
└── .last-session    ← 最後 session 的時間戳記
```

## 記憶操作指南

### 讀取記憶

**讀取最新 session 摘要：**
```bash
ls -lt $CONNSYS_JARVIS_MEMORY_PATH/working/<expert>/ | head -5
cat $CONNSYS_JARVIS_MEMORY_PATH/working/<expert>/<date>/<latest-file>.md
```

**讀取共用知識：**
```bash
cat $CONNSYS_JARVIS_MEMORY_PATH/shared/project-context.md
```

**搜尋特定記憶：**
```bash
grep -r "<關鍵字>" $CONNSYS_JARVIS_MEMORY_PATH/
```

### 寫入記憶

**寫入 working memory：**
```bash
mkdir -p $CONNSYS_JARVIS_MEMORY_PATH/working/<expert>/$(date +%Y-%m-%d)
cat > $CONNSYS_JARVIS_MEMORY_PATH/working/<expert>/$(date +%Y-%m-%d)/<task>.md << EOF
---
expert: <expert-name>
date: $(date +%Y-%m-%d)
task: <task-name>
status: IN_PROGRESS
---

# <任務標題>

## 當前狀態
<狀態說明>

## 重要發現
<關鍵資訊>
EOF
```

**更新共用知識：**
```bash
# 在 shared/known-issues.md 新增已知問題
cat >> $CONNSYS_JARVIS_MEMORY_PATH/shared/known-issues.md << EOF

## 問題：<問題標題>
- **發現時間**：$(date +%Y-%m-%d)
- **Expert**：<expert-name>
- **描述**：<問題描述>
- **解決方案**：<解決方案>
EOF
```

## Memory 文件格式規範

所有記憶文件使用 YAML frontmatter + Markdown 格式：

```yaml
---
expert: <expert-name>        # 寫入的 Expert
date: YYYY-MM-DD             # 日期
time: HH:MM                  # 時間（可選）
task: <task-name>            # 任務名稱（可選）
status: IN_PROGRESS|DONE     # 狀態（可選）
tags: [tag1, tag2]           # 標籤（可選）
---
```

## 注意事項

- Memory 路徑由 `CONNSYS_JARVIS_MEMORY_PATH` 環境變數決定
- 若環境變數未設定，hooks 會跳過記憶操作（不報錯）
- `shared/` 下的文件被所有 Expert 共享，修改時需謹慎
- `handoffs/` 下的文件由 framework-handoff-flow 管理，不要手動修改
- 記憶文件不儲存密碼、token 等敏感資訊
