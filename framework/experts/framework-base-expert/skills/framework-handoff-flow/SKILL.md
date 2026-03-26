---
name: framework-handoff-flow
description: "Expert 交接的標準作業程序（SOP），確保上下文在 Expert 切換時完整傳遞"
version: "1.0.0"
domain: framework
type: flow
scope: framework-base-expert
tags: [framework, handoff, context-transfer, SOP]
---

# Framework Handoff Flow

## 用途

當需要從一個 Expert 切換到另一個 Expert 時，此 SOP 確保當前任務狀態、重要決策和待辦事項被完整記錄並傳遞給接手的 Expert。

## Hand-off 觸發條件

以下情況應觸發 hand-off：

1. 任務超出當前 Expert 的能力範圍
2. 工程師明確要求切換 Expert（`/handoff` 指令）
3. Expert 的 `transitions` 定義的狀態轉移發生（如 `ANALYSIS_DONE`）
4. 任務已完成，需要進入下一個工作流程階段

## Hand-off 文件格式

```markdown
---
type: handoff
from_expert: <發送方 expert 名稱>
to_expert: <接收方 expert 名稱>
timestamp: <ISO 8601 時間戳>
task_status: <IN_PROGRESS|COMPLETED|BLOCKED>
---

# Hand-off: <任務標題>

## 任務概述
<用 2-3 句話描述當前任務>

## 已完成的工作
- <完成項目 1>
- <完成項目 2>

## 當前狀態
<詳細說明目前的狀態和進展>

## 待辦事項
- [ ] <待辦 1>
- [ ] <待辦 2>

## 重要決策記錄
| 決策 | 原因 | 時間 |
|------|------|------|
| <決策內容> | <選擇原因> | <時間> |

## 注意事項
<接手 Expert 需要特別注意的事項>

## 相關檔案
- <重要檔案路徑 1>
- <重要檔案路徑 2>
```

## Hand-off 流程步驟

### Step 1：確認接手方

```
工程師：/handoff
AI：我需要將這個任務交接給哪個 Expert？
   可用的 Expert：
   1. wifi-bora-memory-slim-expert（記憶體優化）
   2. sys-bora-preflight-expert（Gerrit 提交）
   請選擇或輸入 Expert 名稱：
```

### Step 2：生成 Hand-off 文件

依據上述格式生成文件，儲存至：
```
.connsys-jarvis/memory/handoffs/<timestamp>-<from>-to-<to>.md
```

### Step 3：更新環境變數

```bash
export CONNSYS_JARVIS_ACTIVE_EXPERT="<新 Expert 名稱>"
```

### Step 4：通知工程師

```
Hand-off 文件已生成：.connsys-jarvis/memory/handoffs/...

請執行以下步驟切換 Expert：
1. 在 Claude 設定中將 expert 更換為 <新 Expert 名稱>
2. 或執行：python connsys-jarvis/install.py --add <新 expert.json 路徑>
3. 重新開啟 session 後，新 Expert 會自動讀取 hand-off 文件
```

## 接收 Hand-off

session 開始時，若偵測到 handoffs/ 資料夾中有新文件：

1. 讀取最新的 hand-off 文件
2. 在回應開頭摘要接手的任務狀態
3. 確認工程師準備好繼續工作

```
[Hand-off 偵測] 我接收到來自 wifi-bora-base-expert 的任務交接：
- 任務：分析 Bora ROM footprint
- 狀態：架構分析完成，正在進行 symbol map 解析
- 待辦：完成 linker script 優化方案

是否繼續這個任務？
```

## 注意事項

- Hand-off 文件使用 Markdown 格式，確保人類可讀
- 時間戳使用 UTC ISO 8601 格式
- 文件保留 30 天，之後歸檔至 `memory/archive/`
