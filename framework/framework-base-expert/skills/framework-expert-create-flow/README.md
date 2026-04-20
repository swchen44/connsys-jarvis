# framework-expert-create-flow

互動式引導工程師從零建立一個完整、符合 connsys-jarvis 規範的 Expert。

## Owner

framework-team

## 功能

- 確認目標 domain、命名、是否為 base expert 等前置資訊再建立檔案
- 強制執行 `{domain}-{purpose}-expert` 命名規則
- 逐步引導撰寫 expert.json（含完整 schema）、soul.md、rules.md、duties.md、expert.md
- 提供各資料夾（skills/、hooks/、agents/、commands/）的適合內容說明
- 指示使用 `framework-skill-create-flow` 建立每個 skill
- 提供完整的 Expert 建立 Checklist（A–F 共 26 項）
- 引導用 `setup.py --init`/`--add`/`--doctor` 驗證安裝

## 目標

讓任何團隊成員都能建立結構正確、內容完整、可被 `setup.py` 正確安裝的 connsys-jarvis Expert，不需要熟記規範細節。核心成果：

1. **命名正確** — expert 和其下的 skill 都遵循命名規則，可被 setup.py glob 一致掃描
2. **身份完整** — soul.md / rules.md / duties.md 清楚定義 expert 的性格、邊界、職責
3. **可安裝** — expert.json 格式正確，setup.py 能成功建立 symlink 和 CLAUDE.md
4. **品質驗證** — Checklist 確保沒有遺漏必要檔案或必要欄位

## 設計理念與開發方法

此 skill 依據以下設計原則：

1. **Wizard 模式**：Expert 建立是一次性流程（不像 skill 需要 eval 迭代）。採用逐步引導（Step 0–10）而非 eval 迴圈。
2. **Schema 先行**：先呈現 expert.json 完整 schema，讓工程師理解各欄位意義再填入，避免建立後才修正格式。
3. **Soul / Rules / Duties 三角**：參考 [gitagent SPECIFICATION](https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md) 的設計哲學，三份文件分別管理身份（是誰）、規則（不能做什麼）、職責（負責什麼）。
4. **Checklist 作為品質門檻**：26 項 Checklist 覆蓋目錄結構、expert.json 驗證、內容品質、skill 命名、安裝驗證、需求對齊，取代傳統測試腳本。
5. **Skill 委外**：每個 skill 由 `framework-skill-create-flow` 建立，不在此 skill 重複 skill 建立邏輯。

### 如何驗證 Expert 正確性

| 驗證項目 | 方法 | 時機 |
|---------|------|------|
| 目錄結構與檔案完整性 | Checklist A（7 項）| 所有檔案建立後 |
| expert.json 格式與欄位 | Checklist B（8 項）| 寫完 expert.json 後 |
| 內容品質 | Checklist C（5 項）| 所有 md 文件完成後 |
| Skill 命名與註冊 | Checklist D（3 項）| 建立每個 skill 後 |
| 安裝可運作 | `setup.py --doctor`（Checklist E）| 安裝後 |
| 需求對齊 | Checklist F（4 項）| 完成前最終確認 |

---

## Plugin 安裝時的 Skill 命名

透過 Claude Code Plugin（Marketplace）安裝時，所有 skill/command/agent 的全名會加上 plugin 前綴（如 `framework-base-expert:framework-expert-create-flow`）。但使用者**只需輸入短名**（如 `/framework-expert-create-flow`），Claude Code 會自動匹配。

**原因**：Claude Code 的 `findCommand()` 除了比對全名，也會比對 frontmatter 的 `name` 欄位。只要 SKILL.md / command.md / agent.md 的 frontmatter 有 `name` 欄位，短名就能匹配。

**因此建立 Expert 時，務必確保所有 SKILL.md 都有 `name` frontmatter 欄位。**

---

## TODO / 限制

- [ ] 支援從現有 expert 複製為範本（`--from-template` 模式）
- [ ] 自動產生 hooks/ 的 session-start.sh / session-end.sh 基本骨架
- [ ] 驗證 expert.json 的 JSON 語法（目前由 Claude Edit tool 寫入，無預先驗證）
- [ ] 支援批次建立多個 skill（目前一次一個，委外給 framework-skill-create-flow）
- [ ] Checklist 自動化：部分項目（如 JSON 格式、symlink 存在）可由腳本驗證

**已知限制：**
- Checklist F（需求對齊）需要工程師主動閱讀需求文件，無法自動化
- `setup.py --doctor` 是最終驗證，建立期間的 JSON 錯誤只能靠工程師注意
- Sub-agents（agents/ 資料夾）的用途說明較少，因 Phase 1 尚未有具體案例

---

## 風險

### 最大風險

expert.json 格式錯誤或欄位遺漏，導致 `setup.py` 無法解析，整個 expert 安裝失敗且無明確錯誤訊息。

**緩解方式**：依照 SKILL.md 中的 schema 範例逐欄填寫；完成後立即執行 `setup.py --doctor` 驗證。

### 失敗條件

| 情況 | 症狀 | 修復方式 |
|------|------|---------|
| expert.json 格式錯誤 | `setup.py` 拋出 JSON parse error 或 KeyError | `git restore` 還原，重新依 schema 填寫 |
| expert 命名不符規則 | setup.py glob 掃不到此 expert | 更名目錄，同步更新 expert.json `name` 欄位 |
| dependencies 引用不存在的 expert | `setup.py` 找不到依賴路徑 | 確認依賴 expert 存在，或移除不存在的依賴 |
| is_base=true 但有 dependencies | doctor D2 警告，CLAUDE.md 可能重複 | 移除 dependencies（base expert 不依賴其他 expert）|
| soul.md 缺少必要章節 | CLAUDE.md 語意不完整，影響 AI 行為 | 補齊 Identity、Values、Communication Style |

### 替代方案

- **手動複製**：複製現有 expert 目錄（如 `wifi-bora-base-expert`），更名後逐一修改。速度快但容易遺漏欄位。
- **從空骨架開始**：只建立 expert.json + 4 個 md 文件，其餘資料夾視需要才加。適合 prototype 階段。

---

## 來源

依據以下文件設計：
- `connsys-jarvis/doc/agents-design.md` §2.4–§2.5、§4（expert 命名、結構、expert.json schema）
- `connsys-jarvis/doc/agents-requirements.md` FR-01、FR-03、FR-05（Expert 規範）
- [gitagent SPECIFICATION](https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md)（SOUL / RULES / DUTIES 設計哲學）
- `framework-skill-create-flow`（Skill 建立委外，命名規則參考）
