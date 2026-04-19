# framework-skill-create-flow

在 connsys-jarvis expert 生態系中，互動式建立高品質 skill 的標準流程。

## Owner

framework-team

## 功能

- 確認開發者已提供足夠資訊（目標 expert、用途、skill 類型）才開始建立檔案
- 強制執行 `{domain}-{skill-name}-{type}` 命名規則
- 建立 Layer 5 完整目錄結構（SKILL.md、README.md、test/）
- 將新 skill 註冊到目標 expert 的 `expert.json` 和 `expert.md`
- 執行 eval/迭代迴圈，在發布前量化衡量並改善 skill 品質
- 對 skill 的 trigger description 進行最佳化，提升 Claude 呼叫準確率

## 目標

讓任何團隊成員都能建立結構正確、可測試、並且正確註冊的 connsys-jarvis skill，不需要熟記整個架構細節。核心成果：

1. **命名正確** — skill 在各 domain 中可被一致地搜尋和識別
2. **註冊才生效** — 沒有登錄在 `expert.json` 的 skill 不會被 `setup.py` symlink，永遠不會觸發
3. **測試品質** — 每個 skill 至少完成一輪 eval 迭代
4. **Trigger 調校** — description 經過優化，Claude 在正確時機呼叫此 skill

## 設計理念與開發方法

此 skill 以上游 `skill-creator` plugin（`claude-plugins-official`）為基礎，核心迴圈（draft → test → review → improve → repeat）不變，新增的是 connsys-jarvis 專屬慣例：

1. **前置資訊把關** — 必須先確認目標 expert、用途、命名，才能建立任何檔案。避免出現孤立或命名錯誤的 skill。
2. **命名強制規範** — `{domain}-{name}-{type}` 格式讓 `setup.py` 能一致地 glob 所有 skill，命名本身即可傳達意圖。
3. **expert.json 註冊為必要步驟** — 非事後補做。遺漏這步，skill 對整個系統來說是不存在的。
4. **Eval 品質門檻** — 未執行任何 eval 就發布 skill 不被鼓勵。此 flow 內建 eval 迴圈，並將其定義為必要步驟。

### 如何加 Test Case 與驗證

**Eval cases（evals/evals.json）**：針對真實使用情境的功能性 test prompt。加入步驟：
1. 在 `evals/evals.json` 新增 `id`、`prompt`、`expected_output`
2. 執行 eval loop 後，補充 `assertions`（格式見 `references/schemas.md`）
3. 用 `agents/grader.md` 評分，在 eval viewer 中逐一複查

| 驗證項目 | 方法 | 時機 |
|---------|------|------|
| Skill 行為 | Eval loop（SKILL.md Step 6–7） | 建立時、重大修改後 |
| Trigger 準確度 | `scripts/run_loop.py`（SKILL.md Step 9） | 行為穩定後 |

### Eval 與 Trigger 優化

- **Eval**：驗證 skill 對特定 prompt 的輸出是否正確
- **Trigger 優化**：驗證 Claude 是否在正確時機呼叫此 skill

兩者都是 skill 上線前的必要條件。

Trigger 優化流程：產生 20 組 query（10 should-trigger、10 should-not-trigger）→ 經 `scripts/run_loop.py` 以 60/40 train/test 分割迭代最佳化 → 選出 test set 得分最高的 description。

### Benchmark

`scripts/aggregate_benchmark.py` 產出 `benchmark.json`，包含：
- 各 assertion 通過率
- With-skill vs. baseline (no skill) 的 delta
- Token 用量與執行時間（mean ± stddev）

用 `eval-viewer/generate_review.py` 在瀏覽器中以視覺化方式檢視結果。每次迭代都應在自行修改 skill 前，先讓人類在 viewer 中複查。

---

## TODO / 限制

- [ ] 加入 connsys-jarvis 專屬的 eval assertions（例如「SKILL.md frontmatter 為有效 YAML」、「expert.json 已正確更新」）
- [ ] 自動建立 `report/` 目錄的 scaffold
- [ ] 支援 domain 專屬的 SKILL.md stub template（例如 `wifi` domain 預填 Wi-Fi 相關 context）
- [ ] 建立檔案前，驗證目標 expert 目錄確實存在於磁碟
- [ ] 驗證新 skill 名稱不與現有 skill 衝突

**已知限制：**
- Trigger description 最佳化（`run_loop.py`）需要 `claude` CLI，無法在 Claude.ai 使用
- 平行 subagent eval 需要 Claude Code；Claude.ai 中改為循序執行
- Eval viewer 需要有顯示器；在 Cowork / headless 環境中改用 `--static` flag
- `expert.json` 由 Claude 透過 Edit tool 直接修改，儲存前無 JSON 語法驗證

---

## 風險

### 最大風險

此 skill 會修改 `expert.json`。若編輯後產生無效的 JSON（語法錯誤、key 錯誤），將導致 `setup.py` 無法為整個 expert 產生 symlink，使該 expert 的所有 skill 靜默失效。

**緩解方式**：修改前先讀取現有 `expert.json`；儲存前與使用者確認 diff；修改後執行 `uv run ./connsys-jarvis/scripts/setup.py --doctor` 驗證。

### 失敗條件

| 情況 | 症狀 | 修復方式 |
|------|------|---------|
| `expert.json` 編輯後格式錯誤 | `setup.py --doctor` 回報 JSON parse error | `git restore` 還原該檔案 |
| Skill 名稱與既有 skill 衝突 | `--add` 時 symlink 碰撞 | 重新命名新 skill 並更新 `expert.json` |
| Domain prefix 錯誤 | Skill 未與同 domain 的 skill 歸類在一起 | 更名目錄並更新 `expert.json` |
| 目標 expert 不存在 | Skill 被登錄到錯誤或不存在的 expert | 移動 skill 目錄並更新 `expert.json` |
| `eval-viewer` 找不到 | Benchmark 步驟出現 `ModuleNotFoundError` | 確認 `eval-viewer/generate_review.py` 存在於此 skill 目錄 |
| `claude` CLI 未安裝 | `run_loop.py` 失敗 | 安裝 Claude Code CLI，或跳過 description 優化步驟 |

### 替代方案

- **手動建立**：複製現有 skill 目錄（例如 `framework-memory-tool`），更名後手動編輯。適合簡單 skill；不含 eval loop。
- **上游 `skill-creator`**：直接使用 `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/`。無 connsys-jarvis 整合，但適合與 framework 無關的通用 skill。
- **Template 複製**（規劃中）：未來的 `--template` 選項，預填 domain 專屬內容，不需執行完整互動流程。

---

## 來源

以 `claude-plugins-official` 的 `skill-creator` plugin 為基礎。
路徑：`~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/`

此 skill 在上游基礎上新增的 connsys-jarvis 專屬步驟：
- Prerequisite Check（目標 expert、用途、命名確認）
- 命名規則區段（`{domain}-{name}-{type}` 強制規範）
- Layer 5 目錄結構建立（SKILL.md + README.md）
- `expert.json` 和 `expert.md` 的 skill 註冊
- README.md 台灣繁體中文模板（含完整章節結構）
