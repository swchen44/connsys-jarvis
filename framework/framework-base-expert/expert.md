# Framework Base Expert

## Overview

Framework Base Expert 是 Connsys Jarvis 生態系的基礎框架層，負責協調所有 domain Expert 的生命週期、記憶管理和知識交接。

## Key Behaviors

- 在對話開始時自動讀取 session 摘要和待接 hand-off（由 `session-start.sh` 觸發）
- 提供 `/experts` 指令讓工程師了解可用的 Expert 及能力
- 提供 `/handoff` 指令手動觸發 Expert 切換，生成結構化交接文件
- 每 20 訊息自動儲存 checkpoint（由 `mid-session-checkpoint.sh` 觸發）
- session 結束時自動儲存摘要（由 `session-end.sh` 觸發）

## Tools Available

| 指令 | 說明 |
|------|------|
| `/experts` | 列出所有可用 Expert 及其能力，協助選擇合適的 Expert |
| `/handoff` | 觸發 Expert 切換，生成 hand-off 文件並傳遞上下文 |

## Skills

| Skill | 類型 | 說明 |
|-------|------|------|
| `framework-expert-discovery-knowhow` | knowhow | 了解可用 Expert 的清單與能力說明 |
| `framework-handoff-flow` | flow | Expert 交接的標準作業程序（SOP） |
| `framework-memory-tool` | tool | 操作本地記憶系統（讀/寫/搜尋） |
| `framework-skill-create-flow` | flow | 互動式建立符合規範的 Skill（SKILL.md + 目錄結構 + expert.json 註冊） |
| `framework-expert-create-flow` | flow | 互動式建立符合規範的 Expert（soul/rules/duties/expert.md + expert.json + 資料夾骨架） |

## Hooks

| Hook | 觸發時機 | 說明 |
|------|----------|------|
| `session-start.sh` | session 開始 | 載入上次摘要，偵測待接 hand-off |
| `session-end.sh` | session 結束 | 儲存 session 摘要 |
| `pre-compact.sh` | context 壓縮前 | 儲存快照（最可靠存檔點） |
| `mid-session-checkpoint.sh` | 每 20 訊息 | 定期存檔 |
| `shared-utils.sh` | 被其他 hook source | 共用工具函式 |

## Memory Structure

```
.connsys-jarvis/memory/
├── shared/          ← 跨 Expert 共用知識
├── working/         ← 當前工作暫存
└── handoffs/        ← Expert 交接文件
```

## Environment Variables

| 變數 | 說明 |
|------|------|
| `CONNSYS_JARVIS_PATH` | connsys-jarvis repo 根目錄 |
| `CONNSYS_JARVIS_WORKSPACE_ROOT_PATH` | workspace 根目錄 |
| `CONNSYS_JARVIS_CODE_SPACE_PATH` | 程式碼操作路徑 |
| `CONNSYS_JARVIS_MEMORY_PATH` | memory 資料夾路徑 |
| `CONNSYS_JARVIS_EMPLOYEE_ID` | 工程師 ID（git user.name） |
| `CONNSYS_JARVIS_ACTIVE_EXPERT` | 當前啟用的 Expert 名稱 |
