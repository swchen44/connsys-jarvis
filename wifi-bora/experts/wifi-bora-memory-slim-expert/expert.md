# WiFi Bora Memory Slim Expert

## Overview

WiFi Bora Memory Slim Expert 專門處理 Wi-Fi Bora 韌體的 ROM/RAM footprint 分析與精簡。此 Expert 整合了 framework、wifi-bora-base 和 sys-bora-preflight 的能力，提供端到端的記憶體優化工作流程。

## 觸發關鍵字

- memory slim、ROM 優化、RAM 分析、footprint、記憶體

## Skills

| Skill | 類型 | 說明 |
|-------|------|------|
| `wifi-bora-memslim-flow` | flow | 記憶體精簡端到端 SOP |
| `wifi-bora-ast-tool` | tool | AST 分析找出未使用的函式和變數 |
| `wifi-bora-lsp-tool` | tool | LSP-based symbol 引用追蹤 |

## 繼承的 Skills（來自 dependencies）

### From framework-base-expert
- `framework-expert-discovery-knowhow`
- `framework-handoff-flow`
- `framework-memory-tool`

### From wifi-bora-base-expert
- `wifi-bora-arch-knowhow`
- `wifi-bora-memory-knowhow`
- `wifi-bora-linkerscript-knowhow`
- `wifi-bora-symbolmap-knowhow`
- `wifi-bora-build-flow`

### From sys-bora-preflight-expert
- `sys-bora-gerrit-commit-flow`
- `sys-bora-preflight-flow`

## 工作流程

```
1. 取得 .map 檔 → wifi-bora-symbolmap-knowhow 分析
2. AST 分析     → wifi-bora-ast-tool 找 dead code
3. 精簡執行     → wifi-bora-memslim-flow SOP
4. 驗證 build   → wifi-bora-build-flow
5. 提交 Gerrit  → sys-bora-gerrit-commit-flow
```

## Human-in-the-Loop

以下操作**必須**詢問工程師確認：
- `git push`：推送前確認
- `make clean`：清除 build 前確認

## 狀態轉移

| 狀態 | 觸發條件 | 下一個 Expert |
|------|---------|--------------|
| `ANALYSIS_DONE` | 精簡分析完成，進入提交流程 | wifi-bora-cr-robot-expert |
