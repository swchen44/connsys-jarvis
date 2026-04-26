---
name: framework-base-skill-craftsman-flow
description: "Skill 生命週期工具組 — 盤點哪些工作流值得做成 skill、從 session 反推 SKILL.md、診斷觸發失敗、執行後復盤迭代。涵蓋 skill 從零到維護的完整 lifecycle。"
version: "1.0.0"
disable-model-invocation: true
arguments: function
argument-hint: "[auditor|reverse-engineer|diagnostician|retro]"
---

# Skill Craftsman Toolkit

管理 Claude Skill 完整生命週期的四合一工具組，從盤點到維護每個關鍵動作都有對應的引導流程。

每個功能內建自己的 interview 流程跟 guardrails，跟著問就能拿到具體 artifact。

## 使用方式

```
/framework-base-skill-craftsman-flow auditor
/framework-base-skill-craftsman-flow reverse-engineer
/framework-base-skill-craftsman-flow diagnostician
/framework-base-skill-craftsman-flow retro
```

## 四種功能

| 參數 | 功能名稱 | 用途 | 產出 |
|------|---------|------|------|
| `auditor` | Skill Backlog Auditor | 用三信號（重複性、domain knowledge、高出錯成本）盤點工作流 | 按 ROI 排序的 skill 候選清單 |
| `reverse-engineer` | Skill Reverse-Engineer | 從 session/brain dump/output 反推第一版 SKILL.md | 完整的 SKILL.md + 驗證 test prompts |
| `diagnostician` | Skill Trigger Diagnostician | 診斷 skill 為何不觸發或過度觸發 | description 修正版 + 驗證測試 |
| `retro` | Skill Retro Facilitator | 復盤 workflow 執行結果，產出改進 patch | 四層分類的 patch 清單 + health check |

## 使用路徑

**Path A — 從零開始建第一個 skill：**
`auditor` → `reverse-engineer` → `diagnostician` → 跑一次任務 → `retro`

**Path B — 既有 skill 不穩，要除錯：**
`diagnostician` 先檢查觸發問題 → 如果觸發 OK 但產出不穩，`retro` 復盤找 patch

**Path C — 不知道哪個工作流值得做：**
只跑 `auditor`，拿到 backlog 後挑 ROI 最高的開始

## 功能指引

根據選擇的 `$function` 參數，讀取對應的 reference 檔案並遵循其中的完整流程。

### auditor

讀取 `${CLAUDE_SKILL_DIR}/references/skill-backlog-auditor.md` 並完整遵循其中的 interview 流程。

核心：用三信號測試（recurrence、domain knowledge density、error cost）逐一評估使用者的 AI 工作流，產出按 ROI 排序的 skill 建構清單。一次問一個問題，等使用者回答後再繼續。

### reverse-engineer

讀取 `${CLAUDE_SKILL_DIR}/references/skill-reverse-engineer.md` 並完整遵循其中的流程。

核心：三條起手分支任選 — session 反推、brain dump、output extraction。產出完整的 SKILL.md（YAML frontmatter + body + output format + edge cases + example）。

### diagnostician

讀取 `${CLAUDE_SKILL_DIR}/references/skill-trigger-diagnostician.md` 並完整遵循其中的流程。

核心：三規則審計（does+when、third-person、natural-language triggers）+ 三個技術陷阱檢查（single-line YAML、1024 字元限制、scope 適當性），產出 routing-optimized 修正版 description。

### retro

讀取 `${CLAUDE_SKILL_DIR}/references/skill-retro-facilitator.md` 並完整遵���其中的流程。

核心：四層分類復盤（methodology gap → body / reference gap → references/ / script gap → scripts/ / QA gap → subagent QA），產出按優先級排序的 patch 清單 + general health check。

## 來源

基於 Gary Chen 的 Skill Craftsman Toolkit prompts。
原始出處：https://garytalksstuff.com/20260421_skill_promptset_1
