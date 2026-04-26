# framework-base-skill-craftsman-flow

管理 Claude Skill 完整生命週期的四合一工具組 — 從盤點到維護，每個關鍵動作都有對應的引導流程。

## Owner

framework-team

## 功能

- **auditor**：用三信號測試（重複性、domain knowledge、出錯成本）盤點工作流，產出按 ROI 排序的 skill 候選清單
- **reverse-engineer**：從 session / brain dump / output 反推第一版完整 SKILL.md
- **diagnostician**：診斷 skill description 觸發問題（under-trigger / over-trigger），產出修正版
- **retro**：復盤 workflow 執行結果，按四層分類產出 patch 清單

## 目標

解決「skill 從零到一走完整個 lifecycle」的問題。每個階段都有盲點（哪個值得做？怎麼寫？為什麼不觸發？跑完怎麼改？），這個 skill 把每個階段的最佳實踐封裝成引導式流程。

## 設計理念與開發方法

- **手動觸發**：設定 `disable-model-invocation: true`，避免 Claude 在不相關情境自動載入
- **參數化選擇**：用 `arguments` + `argument-hint` 讓使用者選擇 4 種功能之一
- **Reference 分離**：4 個 prompt 各自獨立成 reference 檔案，SKILL.md body 只做路由和簡要說明，避免超過 500 行限制
- **來源**：基於 Gary Chen 的 Skill Craftsman Toolkit（https://garytalksstuff.com/20260421_skill_promptset_1）

### 使用方式

```bash
# 盤點哪些工作流值得做成 skill
/framework-base-skill-craftsman-flow auditor

# 從零製作第一版 SKILL.md
/framework-base-skill-craftsman-flow reverse-engineer

# 診斷觸發問���
/framework-base-skill-craftsman-flow diagnostician

# 執行後復盤迭代
/framework-base-skill-craftsman-flow retro
```

### 如何加 Test Case 與驗證

**Eval cases（evals/evals.json）**：功能性 test prompt，加入步驟：
1. 在 `evals/evals.json` 新增 `id`、`prompt`、`expected_output`
2. 執行 eval loop 後，補充 `assertions`
3. 用 grader 評分，在 eval viewer 複查

| 驗證項目 | 方法 | 時機 |
|---------|------|------|
| Skill 行為 | 手動執行 4 種功能 | 建立時、重大修改後 |
| Reference 完整性 | 比對原始網頁 prompt | 建立時 |

---

## TODO / 限制

- [ ] 建立 evals/evals.json 測試案例
- [ ] 考慮加入中文版 prompt 作為替代 reference

**已知限制：**
- Prompt 原文為英文，中文使用者需要英文閱讀能力
- 手動觸發設計，不會在相關對話中自動載入

---

## 風險

### 最大風險

Reference 中的 prompt 內容與原始網頁版本脫節（原作者更新時需手動同步）。

### 失敗條件

| 情況 | 症狀 | 修復方式 |
|------|------|---------|
| 參數拼錯 | skill 不知道要載入哪個 reference | 檢查 argument-hint 提示 |
| Reference 檔案遺失 | 讀取失敗 | 確認 references/ 目錄完整 |

### 替代方案

- **直接複製 prompt**：不使用 skill，直接從網頁複製 prompt 到對話中
- **framework-skill-create-flow**：使用內建的 skill 建立流程（功能重疊但方法不同）

---

## 來源

基於 Gary Chen 的 Skill Craftsman Toolkit prompts。
原始出處：https://garytalksstuff.com/20260421_skill_promptset_1
