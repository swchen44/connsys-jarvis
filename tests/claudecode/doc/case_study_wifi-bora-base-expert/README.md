# Case Study: wifi-bora-base-expert 整合測試

本文以一個真實測試案例，說明整合測試框架的完整流程、報告解讀方法與改善建議。

---

## 1. 背景

connsys-jarvis 的 Expert 安裝後，使用者輸入一句話，Claude Code 應該自動觸發對應的 Skills 來完成任務。但我們如何驗證「正確的 Skills 有被觸發」以及「回應品質夠好」？

這就是整合測試框架要解決的問題。

## 2. 測試案例設計

### 2.1 場景來源

一位工程師在安裝了 `wifi-bora-base-expert` 後，輸入：

> 寫一個 hello world 並檢查 size in wifi firmware

這句話看似簡單，但涵蓋兩個子任務：
1. **寫 hello world** — 需要知道韌體架構和 build 方法
2. **檢查 size** — 需要知道 ROM/RAM 記憶體分析方法

### 2.2 預期行為分析

根據 skill 的 description，我們預期 Claude 應該讀取以下 skills：

| # | Skill | 觸發理由 | 必要性 |
|---|-------|---------|--------|
| 1 | `wifi-bora-base-expert-using-knowhow` | MANDATORY，所有 wifi-bora skill 使用前必讀 | required |
| 2 | `wifi-bora-build-flow` | 寫 hello world → 需要 build 知識 | required |
| 3 | `wifi-bora-memory-knowhow` | 檢查 size = 記憶體分析 | required |
| 4 | `wifi-bora-arch-knowhow` | 了解韌體模組架構，決定 code 放在哪裡 | optional |

### 2.3 test_cases.json 定義

```json
{
  "id": "WB-001",
  "name": "hello_world_with_size_check",
  "prompt": "prompts/WB-001_hello_world_size.md",
  "timeout": 360,
  "token_budget": 80000,
  "checks": {
    "skills_invoked": [
      {"skill": "wifi-bora-base-expert-using-knowhow", "required": true},
      {"skill": "wifi-bora-build-flow", "required": true},
      {"skill": "wifi-bora-memory-knowhow", "required": true},
      {"skill": "wifi-bora-arch-knowhow", "required": false}
    ],
    "tools_called": [
      {"tool": "Read",  "min_count": 1},
      {"tool": "Write", "min_count": 1},
      {"tool": "Bash",  "min_count": 1}
    ],
    "output_contains": ["hello"],
    "nl_checks": [
      {
        "id": "nl-01", "aspect": "completeness",
        "question": "回應是否完整涵蓋兩個子任務？...",
        "min_pass": 7, "reference": "golden/WB-001_expected.md"
      },
      {
        "id": "nl-02", "aspect": "skill_usage",
        "question": "回應中是否有使用 build-flow 和 memory-knowhow 的知識？",
        "min_pass": 6
      }
    ],
    "judge": {
      "enabled": true, "rubric": "rubrics/WB-001_rubric.md", "min_score": 7
    }
  }
}
```

**六層檢查（Six-Layer Checks）說明：**

| Layer | 檢查什麼 | 如何判定 |
|-------|---------|---------|
| 1. files_created | 預期檔案是否被建立 | 本案例未使用 |
| 2. skills_invoked | 預期 Skills 是否被觸發 | 從 stream-json 偵測 Skill tool_use 或 Read SKILL.md |
| 3. tools_called | 預期工具是否被呼叫足夠次數 | 從 stream-json 計數 tool_use |
| 4. output_contains | 輸出是否包含關鍵字 | 文字搜尋 |
| 5. nl_checks | NL 品質評估（LLM-as-judge） | 用 haiku 模型評分 1-10 |
| 6. judge | 整體品質評分（按 rubric） | 用 haiku 模型按評分標準打分 |

## 3. 執行

```bash
python3 -m tests.claudecode.cli --expert wifi-bora-base-expert -v --no-analysis
```

執行流程：

```
1. CLI 載入 test_cases.json（1 個 test case）
2. ClaudeRunner 啟動 headless session（claude -p "..." --output-format stream-json）
3. Claude Code 執行任務，產出回應
4. 6 層 assertion checks 逐一驗證
5. NL checks + Judge 呼叫 haiku 模型評分（各一次 claude -p）
6. TokenAnalyzer 解析 token 使用量
7. ReportEngine 生成 L1/L2/L3 三層報告（markdown + JSON）
8. 報告存到 .results/reports/{timestamp}_{expert}_{model}/
```

## 4. 測試報告（實際輸出）

以下是 2026-04-26 的實際測試報告：

### 總覽

| Field | Value |
|-------|-------|
| Expert | `wifi-bora-base-expert` |
| Model | `sonnet` (claude-sonnet-4-6) |
| Pass Rate | **1/1** (100%) |
| Judge Score | 10.0/10 |

### 逐項 Check 結果

| Check | Result | Detail |
|-------|--------|--------|
| skills_invoked | PASS | Skill 'wifi-bora-base-expert-using-knowhow': invoked |
| skills_invoked | PASS | Skill 'wifi-bora-build-flow': invoked |
| skills_invoked | PASS | Skill 'wifi-bora-memory-knowhow': invoked |
| skills_invoked | PASS | Skill 'wifi-bora-arch-knowhow' (optional): invoked |
| tools_called | PASS | Tool 'Read': 6 call(s) >= 1 required |
| tools_called | PASS | Tool 'Write': 3 call(s) >= 1 required |
| tools_called | PASS | Tool 'Bash': 23 call(s) >= 1 required |
| output_contains | PASS | Output contains: 'hello' |
| nl_checks | PASS | NL[completeness]: 7.0/10 PASS (min=7) |
| nl_checks | PASS | NL[skill_usage]: 9.0/10 PASS (min=6) |
| judge | PASS | Judge: 10.0/10 PASS (min=7) |

### Token & Cost

#### Test Session Cost

Model: `claude-sonnet-4-6`

| Category | Tokens | Unit Price (per 1M) | Cost (USD) |
|----------|-------:|--------------------:|-----------:|
| Input | 42 | $3.00 | $0.0001 |
| Output | 9,786 | $15.00 | $0.1468 |
| Cache Creation | 29,976 | $3.75 | $0.1124 |
| Cache Read | 1,039,663 | $0.30 | $0.3119 |
| **Subtotal** | **1,079,467** | | **$0.5712** |

#### Verification Cost (NL Checks + Judge)

| Model | Calls | Tokens | Cost (USD) |
|-------|------:|-------:|-----------:|
| `claude-haiku-4-5-20251001` | 3 | 255,488 | $0.0605 |
| **Subtotal** | | **255,488** | **$0.0605** |

#### Grand Total

| Item | Tokens | Cost (USD) |
|------|-------:|-----------:|
| Test Session | 1,079,467 | $0.5712 |
| Verification | 255,488 | $0.0605 |
| **Total** | **1,334,955** | **$0.6317** |

## 5. 報告解讀指南

### 5.1 Layer 1: Quality Report — 「測試有沒有過？」

- **Pass Rate** — 所有 check 都通過才算 PASS。本次 11/11 = 100%
- **Judge Score** — rubric 評分，10/10 代表 AI 回應在每個維度都達標
- **不要只看 pass/fail** — 看具體哪些 check 的分數邊界值（例如 completeness 7/10 剛好及格）

### 5.2 逐項 Check 解讀

| Check 類型 | 怎麼讀 | 失敗時該做什麼 |
|-----------|--------|--------------|
| skills_invoked | 預期的 skill 有沒有被讀取 | 檢查 skill description 是否包含觸發關鍵字 |
| tools_called | AI 有沒有用到預期的工具 | 調整 prompt 讓 AI 實際執行而非只描述 |
| output_contains | 輸出是否包含必要關鍵字 | 檢查 AI 是否偏離主題 |
| nl_checks | LLM judge 給的品質分數 | 看 reason 欄位了解扣分原因 |
| judge | rubric 總評分數 | 對照 rubric 各項配分找出弱項 |

### 5.3 Cost 解讀

**Test Session Cost** — 實際跑 Claude Code 的花費：
- **Cache Read 佔 94%**（$0.31）— 大部分 token 來自 cache，單價最低（$0.30/1M），這是正常行為
- **Output** 佔 $0.15 — AI 實際生成的內容
- **Cache Creation** 佔 $0.11 — 首次載入 CLAUDE.md 和 skill 內容

**Verification Cost** — NL check + Judge 的 haiku 評分花費：
- 3 次 haiku 呼叫（2 NL checks + 1 Judge）共 $0.06
- haiku 單價便宜（output $4/1M vs sonnet $15/1M），驗證成本只佔總成本 10%

**Grand Total** — 一次完整測試的總花費 = **$0.63**

> **判讀建議**：
> - 若只做 smoke test（不需 NL check），成本可降到 $0.57
> - 若改用 opus 模型，預估 test session 成本會 x5（$2.85），但品質可能更高
> - 若改用 haiku 模型做 test session，成本約 $0.05，但品質可能大幅下降

### 5.4 Layer 3: Behavior — 「AI 怎麼花時間的？」

| Phase | Messages | 含義 |
|-------|--------:|------|
| understanding | 2 | 讀取 prompt，理解需求 |
| exploring | 11 | 搜尋 codebase（Read, Grep, Glob） |
| implementing | 45 | 寫程式碼和文字回應（Write, Edit, Bash） |
| verifying | 4 | 確認結果（跑測試、檢查 output） |
| designing | 1 | 規劃做法 |

> **判讀建議**：
> - implementing 佔最多 messages = AI 花最多時間在實作，正常
> - 若 debugging > 20% = AI 卡在某處反覆嘗試，需檢查錯誤來源
> - 若 exploring > 30% = AI 找不到需要的東西，可能需改善 prompt 或 skill description

## 6. 迭代過程：從 FAIL 到 PASS

本測試經過多次迭代才穩定通過，以下是過程中發現的問題和修正：

### 6.1 第一次執行（FAIL: 4/11）

| 問題 | 原因 | 修正 |
|------|------|------|
| skills_invoked 全部 NOT invoked | `_extract_skill_invocations` 只偵測 Skill tool_use，但 Claude 用 Read SKILL.md | 擴展偵測邏輯，支援 Read 模式 |
| NL check Parse error | HeadlessExecutor 缺少 `--verbose` flag | stream-json 必須搭配 --verbose |
| Judge Parse error | 同上 | 同上 |

### 6.2 第二次執行（FAIL: 2/11）

| 問題 | 原因 | 修正 |
|------|------|------|
| Write tool 0 calls | AI 用文字描述程式碼而非寫檔 | 考慮降低 min_count 或改善 prompt |
| NL completeness 6/10 | 缺少 Makefile 修改範例和 baseline 比較 | 邊界值，可調整 min_pass |

### 6.3 第三次執行（PASS: 11/11）

所有 skills 正確觸發，Write 3 次、Bash 23 次，NL 和 Judge 都通過。

> **學習**：整合測試的價值不僅在最終 PASS/FAIL，更在於迭代過程中發現的
> 框架問題（skill 偵測邏輯）和 AI 行為模式（描述 vs 執行）。

## 7. 跨模型成本預估

根據 config.py 中的定價，相同測試案例在不同模型下的預估成本：

| Model | Input (per 1M) | Output (per 1M) | Cache Read (per 1M) | 預估 Test Cost | 預估 Total |
|-------|---------------:|------------------:|--------------------:|---------------:|-----------:|
| Sonnet | $3.00 | $15.00 | $0.30 | $0.57 | $0.63 |
| Opus | $15.00 | $75.00 | $1.50 | ~$2.85 | ~$2.91 |
| Haiku | $0.80 | $4.00 | $0.08 | ~$0.05 | ~$0.11 |

> 可用 `--models sonnet,opus,haiku` 一次跑三個模型比較品質與成本。

## 8. 總結

| 面向 | 結論 |
|------|------|
| Skill 觸發 | 3/3 required + 1 optional 全部正確觸發 |
| 回應品質 | Judge 10/10，NL skill_usage 9/10 |
| Token 效率 | 94% cache read，成本控制良好 |
| 測試成本 | 一次完整測試 $0.63（test $0.57 + verification $0.06） |
| 測試框架 | 六層檢查 + 三層報告 + 完整 cost breakdown |

**核心發現：**

1. **Skill 觸發可靠性取決於 description 品質** — using-knowhow 的 MANDATORY 語言確保 100% 觸發率
2. **AI 行為不穩定** — 同樣的 prompt，有時會寫檔，有時只描述。整合測試可以量化這個不穩定性
3. **驗證成本可控** — haiku judge 只佔總成本 10%，是划算的品質保證投資
4. **報告的價值在於可追蹤** — 每次執行都有 timestamp 目錄，可以回溯和比較不同時間點的表現
