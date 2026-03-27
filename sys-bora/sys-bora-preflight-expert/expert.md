# Sys Bora Preflight Expert

## Overview

Sys Bora Preflight Expert 管理 ConnSys Gerrit change 的提交和 CI/CD preflight 流程。

## Skills

| Skill | 類型 | 說明 |
|-------|------|------|
| `sys-bora-preflight-flow` | flow | Preflight 觸發、監控、結果分析 SOP |
| `sys-bora-gerrit-commit-flow` | flow | Gerrit change 提交完整流程 |

## 繼承的 Skills（來自 sys-bora-base-expert）

- `sys-bora-gerrit-tool`
- `sys-bora-repo-tool`

## 工作流程

```
1. 準備 commit message
2. git push 到 Gerrit（確認後執行）
3. 觸發 preflight
4. 監控 CI 結果
5. 分析失敗（若有）
6. 獲取 CR+2 後 submit
```
