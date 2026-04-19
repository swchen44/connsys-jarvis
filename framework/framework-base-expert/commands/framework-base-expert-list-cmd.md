---
description: 列出所有可用 Expert 及其能力，協助選擇合適的 Expert
argument-hint: "[list|info <name>|recommend <task>]"
allowed-tools: Read, Bash(python3:*)
---

# /framework-base-expert-list-cmd — Expert 探索指令

列出所有已安裝的 Expert 及其能力，協助工程師選擇合適的 Expert 處理當前任務。

## 用法

- `/framework-base-expert-list-cmd` — 列出所有已安裝 Expert
- `/framework-base-expert-list-cmd info <expert-name>` — 顯示特定 Expert 詳細能力
- `/framework-base-expert-list-cmd recommend <task-description>` — 根據任務推薦 Expert

## 行為

### 列出 Expert

讀取 `.connsys-jarvis/.installed-experts.json` 和 `connsys-jarvis/` 目錄，顯示：

```
=== 已安裝的 Experts ===

[1] framework-base-expert (framework)
    管理 connsys expert 生態系

[2] wifi-bora-memory-slim-expert (wifi-bora) ← 當前 Expert
    分析 Wi-Fi Bora ROM/RAM footprint
```

### 查詢 Expert 詳情

根據 `expert.json` 的 `internal` 欄位顯示 Skills、Hooks、Commands 清單。

### 推薦 Expert

根據任務描述比對 `triggers` 關鍵字和 `description`，推薦最合適的 Expert。

## 實作

此指令由 AI 根據已安裝的 `expert.json` 動態生成回應。
可搭配 `python connsys-jarvis/scripts/setup.py --list --format json` 取得 JSON 格式清單。
