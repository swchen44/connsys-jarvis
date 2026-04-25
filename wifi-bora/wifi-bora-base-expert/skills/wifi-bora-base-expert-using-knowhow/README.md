# wifi-bora-base-expert-using-knowhow

WiFi Bora Base Expert 的指導原則 skill，封裝 soul.md 與 expert.md 的完整內容。

## Owner

wifi-bora-team

## 功能

- 提供 WiFi Bora domain 的方法論、價值觀、技術約束
- 在所有安裝模式（setup.py、Plugin Marketplace、npx skills）下均可讀取
- 透過 SKILL.md description 自動觸發：使用任何 `wifi-bora` 前綴的 skill 時，模型應先讀取本 skill

## 目標

解決 Claude Plugin Marketplace 和 npx skills 安裝模式無法載入 CLAUDE.md 的問題。原本 soul.md 和 expert.md 的內容透過 setup.py 注入 CLAUDE.md，但 Plugin/npx 模式下這些內容會遺失。本 skill 將指導原則封裝為標準 skill，確保跨安裝模式一致性。

## 設計理念與開發方法

### 為什麼需要這個 skill

| 安裝模式 | 原本行為 | 現在行為 |
|----------|---------|---------|
| setup.py | CLAUDE.md @include soul.md/expert.md | CLAUDE.md 指示讀取本 skill |
| Plugin Marketplace | soul.md/expert.md 不載入 | 本 skill 作為標準 skill 載入 |
| npx skills | soul.md/expert.md 不載入 | 本 skill 作為標準 skill 載入 |

### Description 設計

參考 [superpowers/using-superpowers](https://github.com/obra/superpowers) 的 aggressive 語言模式，使用 MANDATORY/MUST 措辭，最大化模型自動讀取的機率。

### 維護規則

- 修改指導原則時，請直接編輯本 skill 的 SKILL.md
- **請勿修改** soul.md 或 expert.md（已改為 HTML 註解指標）

## 風險

### 最大風險

模型可能忽略 SKILL.md 的 description 而不自動讀取本 skill。此設計依賴模型的 skill description matching 機制，不保證 100% 觸發率。

### 失敗條件

| 情境 | 症狀 | 修復 |
|------|------|------|
| 模型未讀取 using-knowhow | 回答缺乏 domain 約束（如未確認 SoC 版本） | 手動呼叫 `/wifi-bora-base-expert-using-knowhow` |
| 開發者修改了 soul.md 而非 SKILL.md | soul.md 有新內容但 skill 未同步 | 將 soul.md 變更合併至 SKILL.md |

### 替代方案

- **保留 @include**：setup.py 繼續 @include soul.md/expert.md，但 Plugin/npx 模式仍無法讀取
- **強制載入**：在 CLAUDE.md 中使用 @include 指向 SKILL.md，但這不適用於 Plugin/npx 模式

## 來源

- soul.md 和 expert.md 的原始內容合併而成
- Description 設計參考 [superpowers/using-superpowers/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/using-superpowers/SKILL.md)
- 詳見 `doc/agents-design.md` §2.8「using-knowhow Skill 模式」
