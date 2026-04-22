# framework-session-analyzer-tool

通用的 Claude Code Session JSONL 分析工具，分析 token 消耗、工具調用、行為模式，產出三層報告。

## Owner

framework-team

## 功能

- 解析 Claude Code 的 session JSONL 紀錄
- Token 統計（含 cache ephemeral 5m/1h TTL 分佈）
- Model 使用分佈（每個訊息實際使用的模型）
- Tool/Skill 調用統計（次數、成功率、is_error 精確標記）
- Subagent 追蹤（每個 agentId 的 token 消耗）
- API 錯誤與重試分析
- Hook 執行效能統計
- 行為階段分類（understanding/designing/exploring/implementing/debugging/verifying）
- Token 浪費偵測（error retry、Edit mismatch、timeout）
- Context 壓縮事件追蹤
- Turn 耗時分佈

## 目標

讓任何 Expert 都能分析自己的 session 品質，找出 token 浪費原因，理解 AI 行為模式，
作為持續改善 Expert 和 Skill 品質的基礎。

## 設計理念與開發方法

選擇 `tool` 類型是因為這是一個工具操作指南，指導如何使用分析腳本。
核心邏輯放在 `scripts/analyze_session.py`，Python stdlib only，可獨立執行。

分析分三層：
1. **L1 品質概覽**：快速判斷 session 好壞（token 效率、cache 命中率、成本）
2. **L2 詳細統計**：per-tool/skill/agent/hook 的精確數據
3. **L3 行為分析**：理解 AI 把時間花在哪裡、為什麼浪費

### 如何加 Test Case 與驗證

**Eval cases（evals/evals.json）**：功能性 test prompt，加入步驟：
1. 在 `evals/evals.json` 新增 `id`、`prompt`、`expected_output`
2. 執行 eval loop 後，補充 `assertions`
3. 用 `agents/grader.md` 評分

| 驗證項目 | 方法 | 時機 |
|---------|------|------|
| Script 正確性 | 用已知 JSONL 執行 | 每次修改 script |
| 報告完整度 | 檢查三層報告欄位 | 新增分析維度後 |
| Skill 觸發 | 不同 prompt 測試 | 修改 description 後 |

### Benchmark

可用 `scripts/analyze_session.py` 分析多個 session，比較不同版本的 Expert 效能。

---

## TODO / 限制

- [ ] 支援 subagent JSONL 遞迴分析
- [ ] 支援多個 session 比較
- [ ] 產出視覺化 HTML 報告

**已知限制：**
- tmux 模式的 session 沒有結構化 JSON，需從 `~/.claude/projects/` 讀取 JSONL
- 行為分類基於關鍵字匹配，非精確語意理解

---

## 風險

### 最大風險

JSONL 格式隨 Claude Code 版本更新可能變動，需要追蹤新欄位。

### 失敗條件

| 情況 | 症狀 | 修復方式 |
|------|------|---------|
| JSONL 格式變更 | 解析錯誤或欄位缺失 | 更新 extract 函式 |
| 大型 session（>50MB） | 記憶體用量高 | 改用 streaming 解析 |
| 無 thinking 區塊 | 行為分類全部 fallback | 改用 tool 模式推斷 |

### 替代方案

- **ccusage**：社群 CLI 工具，專注 token/cost，無行為分析
- **Claude Code /cost 命令**：即時查看，但無歷史分析

---

## 來源

- 從 `tests/claudecode/token_analyzer.py` 演化而來
- 參考 Claude Code 原始碼（`~/git/claude-code/src/`）中的 session 結構
- 參考 [ccusage](https://github.com/ryoppippi/ccusage) 的 JSONL 解析模式
