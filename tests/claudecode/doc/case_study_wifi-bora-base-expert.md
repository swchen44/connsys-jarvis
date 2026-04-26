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
3. Claude Code 執行 76.2 秒，產出回應
4. 6 層 assertion checks 逐一驗證
5. TokenAnalyzer 解析 token 使用量
6. ReportEngine 生成 L1/L2/L3 三層報告
7. 報告存到 .results/reports/2026-04-26_23-08-01_wifi-bora-base-expert_sonnet/
```

## 4. AI 的實際輸出

Claude 的回應（節錄）：

```
假設你有 WiFi Bora firmware source，以下是完整的 Hello World + Size 分析 SOP：

## Step 1：寫 Hello World

在 firmware 裡沒有 printf，通常是透過 log macro：

  /* hello_world.c */
  #include "wifi_log.h"
  void hello_world_init(void)
  {
      wifi_log_info("Hello World from WiFi Bora firmware!\n");
  }

## Step 2：Build

  export CROSS_COMPILE=arm-none-eabi-
  export WIFI_BORA_CHIP=bora_b0
  make -j$(nproc)

## Step 3：檢查 Size 影響

  arm-none-eabi-size build/wifi_bora.elf

  | Section   | 增加量     | 原因                          |
  |-----------|-----------|-------------------------------|
  | .text     | ~48 bytes | hello_world_init() 函式本體    |
  | .rodata   | ~40 bytes | 字串 "Hello World from..."    |
  | .bss/.data| 0         | 沒有全域變數                   |
```

## 5. 測試報告解讀

### 5.1 Layer 1: Quality Report — 「測試有沒有過？」

```markdown
| Field | Value |
|-------|-------|
| Expert | wifi-bora-base-expert |
| Model | sonnet |
| Pass Rate | 0/1 (0%) |
| Judge Score | 8.0/10 |
```

**解讀：**
- Pass Rate 0% 看起來很差，但只因為 11 項 check 中有 2 項 FAIL，整體判定為 FAIL
- Judge Score 8.0/10 代表 AI 的回應品質其實不錯
- **重點：不要只看 pass/fail，要看具體哪些 check 失敗**

### 5.2 逐項 Check 結果分析

| Check | Result | 解讀 |
|-------|--------|------|
| skills_invoked: using-knowhow | PASS | MANDATORY skill 正確觸發，good |
| skills_invoked: build-flow | PASS | 寫 code 前先讀 build 知識，correct |
| skills_invoked: memory-knowhow | PASS | 檢查 size 前先讀 memory 知識，correct |
| skills_invoked: arch-knowhow | PASS (optional) | 沒被觸發但標記為 optional，不扣分 |
| tools_called: Read >= 1 | PASS (4 calls) | 讀了 4 次檔案，合理 |
| **tools_called: Write >= 1** | **FAIL (0 calls)** | **AI 沒有實際寫檔，只用文字描述程式碼** |
| tools_called: Bash >= 1 | PASS (8 calls) | 執行了 8 次命令，合理 |
| output_contains: "hello" | PASS | 輸出包含 hello 關鍵字 |
| **nl_checks: completeness** | **FAIL (6/10, min=7)** | **差 1 分：缺少 Makefile 修改範例和 baseline 比較** |
| nl_checks: skill_usage | PASS (7/10, min=6) | 正確使用了 ARM toolchain 和 size 分析知識 |
| judge | PASS (8/10, min=7) | 整體品質好，程式碼位置正確 |

### 5.3 FAIL 項目深度分析

**FAIL 1: Write tool 未被呼叫**

```
Expected: >= 1 calls
Actual:   0 calls
```

AI 選擇用 markdown code block 描述程式碼，而非使用 Write tool 實際寫入檔案。
這在「沒有實際 firmware repo」的情境下是合理行為 — AI 判斷 workspace 中沒有
firmware source code，因此改為提供 SOP 指引。

> **判讀建議**：此 FAIL 是 test case 對「行為模式」的期待與 AI 實際判斷的落差。
> 若要讓 AI 一定寫檔，prompt 應明確說 "請在 workspace 中建立檔案"。
> 或者，將 Write 的 min_count 改為 0（不要求一定寫檔）。

**FAIL 2: NL completeness 6/10（門檻 7）**

```
AI 涵蓋了兩個子任務的理論框架和步驟，但缺少 Makefile 修改的具體範例、
實際執行過程、baseline 比較結果，以及完整的 symbol size 分佈分析。
```

haiku judge 認為 AI 的回應缺少：
1. Makefile 修改的具體範例（`obj-y += hello.o`）
2. 實際執行 build + size 的結果（只有預估值）
3. Baseline vs 修改後的 diff 比較

> **判讀建議**：6 分離 7 分只差 1 分，屬於邊界值。
> 可以考慮 (a) 降低 min_pass 到 6，或 (b) 改善 prompt 讓 AI 更完整。

### 5.4 Layer 2: Token Statistics — 「花了多少 token？」

```markdown
| Category | Tokens |
|----------|-------:|
| Input | 15 |
| Output | 2,786 |
| Cache Creation | 15,725 |
| Cache Read | 289,166 |
| **Total** | **307,692** |
```

**解讀：**
- Cache Read 佔 94% — 大部分 token 來自 cache（便宜），因為 CLAUDE.md 和 skill 內容都被 cache 了
- Output 只有 2,786 — AI 的實際生成量很小
- Total 307,692 超過 token_budget 80,000 — 但 budget 主要是對 output token 的軟限制，cache read 不算在成本中

### 5.5 Layer 3: Behavior Analysis — 「AI 怎麼花時間的？」

```markdown
| Phase | Messages | Tokens | Ratio |
|-------|--------:|-------:|------:|
| understanding | 3 | 0 | 0.0% |
| implementing | 11 | 0 | 0.0% |
| exploring | 6 | 0 | 0.0% |
```

**解讀：**
- 20 個 messages：3 個理解需求、6 個探索 codebase、11 個實作回應
- Token 為 0 是因為 behavior phase 的 token 歸因尚未完整實作（per-phase token 未從 stream-json 的 usage 欄位拆分）
- Wasted 0% — 沒有偵測到重試或錯誤浪費

> **判讀建議**：若 debugging phase 超過 20%，代表 AI 卡在某處反覆嘗試，
> 應檢查是哪個 tool call 失敗。本次測試沒有此問題。

## 6. 改善建議

根據測試結果，以下是具體可行的改善方向：

### 6.1 Test Case 調整

| 問題 | 建議 | 修改位置 |
|------|------|---------|
| Write tool FAIL 不合理 | 將 `min_count` 改為 0，或新增條件判斷 | `test_cases.json` tools_called |
| NL completeness 門檻太高 | 將 `min_pass` 從 7 降為 6 | `test_cases.json` nl_checks |
| Prompt 太模糊 | 加入 "請在 workspace 中實際建立檔案" | `prompts/WB-001_hello_world_size.md` |

### 6.2 Skill 改善

| 觀察 | 建議 |
|------|------|
| using-knowhow 正確觸發 | MANDATORY 模式有效，維持 |
| build-flow 正確觸發 | skill description 中的 "build" 關鍵字觸發成功 |
| memory-knowhow 正確觸發 | "size" 和 "記憶體" 成功映射到此 skill |
| arch-knowhow 沒觸發 | 非必要，但可在 description 加入 "hello world" 或 "code placement" 增加觸發率 |

### 6.3 跨模型比較（未來）

```bash
# 比較 sonnet vs opus 的表現
python3 -m tests.claudecode.cli --expert wifi-bora-base-expert \
    --models sonnet,opus --no-analysis
```

預期差異：
- Opus：completeness 分數可能更高（更詳細的輸出），但 token 成本更高
- Haiku：completeness 分數可能更低，但速度最快

## 7. 總結

| 面向 | 結論 |
|------|------|
| Skill 觸發 | 3/3 required skills 全部正確觸發 |
| 回應品質 | Judge 8/10，整體良好，細節有改善空間 |
| Token 效率 | 94% cache read，成本控制良好 |
| 測試框架 | 六層檢查有效抓出「知道 vs 做到」的差異（AI 知道怎麼做但沒有實際執行） |

**核心發現：** 整合測試最大的價值不在於判定 pass/fail，而在於揭示 AI 行為模式 —
它選擇用「說明」而非「執行」來回應，以及它引用了哪些 skill 的知識。
這些洞察可以回饋到 skill description 和 prompt 設計的改善循環中。
