---
name: framework-session-analyzer-tool
description: "分析 Claude Code Session JSONL 紀錄，產出 token 消耗、tool/skill 調用、行為階段、cache 效率等三層報告。當使用者提到分析 session、查看 token 用量、檢查 Claude Code 對話效率、理解 AI 行為模式、或想知道為什麼 session 花了太多 token 時使用此 skill。即使使用者只是說「剛才那次對話效率怎麼樣」或「幫我看一下 token 用在哪裡」也應觸發。"
version: "1.0.0"
domain: framework
type: tool
scope: framework-base-expert
tags: [framework, session, analyzer, token, tool]
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - Write
---

# Framework Session Analyzer Tool

分析 Claude Code 的 Session JSONL 紀錄，從數字統計到行為語意，產出三層報告。

## 使用時機

- 使用者想知道 session 的 token 消耗分佈
- 使用者想了解 AI 花時間在做什麼（設計？探索？除錯？）
- 使用者想找出 token 浪費的原因（重試、timeout、Edit 失敗）
- 使用者想比較不同 model 的效率
- 使用者想檢查 cache 命中率和 subagent 效能
- 整合測試後需要分析測試結果

## Session JSONL 檔案位置

```
~/.claude/projects/<encoded-project-dir>/<session-id>.jsonl
```

每個 subagent 有獨立 JSONL：
```
~/.claude/projects/<dir>/<session-id>/subagents/agent-<agentId>.jsonl
```

如果使用者沒指定路徑，用以下方式找到最近的 session：
```bash
ls -lt ~/.claude/projects/*//*.jsonl | head -5
```

## 分析流程

### Step 1: 找到 Session 檔案

如果使用者提供了路徑，直接使用。否則列出最近的 session 讓使用者選擇。

### Step 2: 執行數字分析

用 `scripts/analyze_session.py` 做第一層分析：

```bash
python3 <skill-dir>/scripts/analyze_session.py <jsonl-path>
```

或指定輸出目錄：
```bash
python3 <skill-dir>/scripts/analyze_session.py <jsonl-path> --output-dir /tmp/session-report/
```

script 會產出 `report.json`（機器可讀）和 `report.txt`（人類可讀）。

### Step 3: 用 LLM 做語意分析

讀取 `report.json`，針對以下面向做進一步分析：

1. **效率診斷**：token 浪費的根本原因是什麼？是 skill 設計問題、prompt 不夠清楚、還是工具限制？
2. **行為模式**：AI 是否在正確的時間做正確的事？探索/實作/除錯的比例是否合理？
3. **改善建議**：具體可執行的改善方案（修改哪個 skill 的 trigger、調整哪個 prompt）

### Step 4: 產出報告

整合數字分析和語意分析，產出完整報告給使用者。

## 三層報告結構

### L1 品質概覽

回答：「這個 session 整體表現如何？」

- Session 基本資訊（model、duration、total turns）
- Token 總量與估算成本
- Cache 命中率（cache_read / total_input）
- 有效 token 比例 vs 浪費比例
- Skill 觸發成功率

### L2 詳細統計

回答：「具體發生了什麼事？」

- **Model 使用分佈**：每個 model 被調用的次數和 token 量
- **Tool 調用統計**：每個 tool 的次數、成功率、is_error 數量、token 花費
- **Skill 調用統計**：每個 skill 的次數、成功率、token 花費
- **Subagent 統計**：每個 agentId 的 token 消耗、tool 調用數、成功率
- **API 錯誤統計**：錯誤類型分佈、重試次數、等待時間
- **Hook 執行統計**：每個 hookEvent 的次數、耗時、exitCode 分佈
- **失敗分佈表**：按失敗類型（timeout、edit_retry、permission_denied 等）彙總

### L3 行為分析

回答：「AI 把時間花在哪裡？為什麼？」

- **行為階段分類**：每個 assistant 訊息歸類到 understanding/designing/exploring/implementing/debugging/verifying
- **Phase timeline**：時間線上標注每段的行為階段
- **Token 效率分析**：有效 / 探索 / 浪費的明細
- **Cache 效率**：ephemeral_5m vs ephemeral_1h 的分佈，cache 命中趨勢
- **Context 壓縮事件**：compact_boundary 出現的次數和位置
- **Turn 耗時分佈**：每個 turn 的耗時，找出異常慢的 turn

## JSONL 關鍵欄位速查

供分析時參考的欄位對照表：

| 分析維度 | 欄位路徑 | 說明 |
|---------|----------|------|
| Token 統計 | `message.usage.input_tokens` | 輸入 token |
| Token 統計 | `message.usage.output_tokens` | 輸出 token |
| Cache 統計 | `message.usage.cache_creation_input_tokens` | 建立 cache 的 token |
| Cache 統計 | `message.usage.cache_read_input_tokens` | 從 cache 讀取的 token |
| Cache TTL | `message.usage.cache_creation.ephemeral_5m_input_tokens` | 5 分鐘 TTL cache |
| Cache TTL | `message.usage.cache_creation.ephemeral_1h_input_tokens` | 1 小時 TTL cache |
| Model | `message.message.model` | 此訊息使用的模型 |
| Stop reason | `message.message.stop_reason` | end_turn / tool_use / stop_sequence |
| Tool 調用 | `message.content[].type == "tool_use"` | 工具名稱在 `.name`，參數在 `.input` |
| Tool 錯誤 | `message.content[].is_error` | 精確的工具失敗標記 |
| Thinking | `message.content[].type == "thinking"` | 思考過程（行為分類依據） |
| Subagent | `agentId`, `agentName`, `isSidechain` | 子 agent 識別 |
| API 錯誤 | `type == "system"`, `subtype == "api_error"` | API 失敗事件 |
| 重試 | `retryAttempt`, `maxRetries`, `retryInMs` | 重試次數和間隔 |
| Hook | `attachment.hookEvent`, `attachment.durationMs` | Hook 執行事件 |
| Compaction | `subtype == "compact_boundary"` | Context 壓縮事件 |
| Turn 耗時 | `durationMs`（turn_duration subtype） | 每個 turn 的耗時 |
| 檔案變更 | `type == "file-history-snapshot"` | 檔案修改追蹤 |
| Speculation | `type == "speculation-accept"` | 推測執行節省時間 |

## 行為階段分類規則

根據 `thinking` 內容關鍵字和 `tool_use` 模式推斷：

| 階段 | Thinking 關鍵字 | Tool 模式 |
|------|-----------------|----------|
| understanding | understand, 理解, 需求, the user wants | （初期訊息） |
| designing | plan, design, 架構, 設計, strategy | 無 tool 調用 |
| exploring | search, find, look for, 探索 | Read, Grep, Glob, Agent |
| implementing | implement, write, create, 實作 | Write, Edit, Bash |
| debugging | retry, fix, error, failed, 重試 | 連續相同 tool 或 error 後重試 |
| verifying | verify, check, confirm, 驗證 | Bash(test/pytest) |
