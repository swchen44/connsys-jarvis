# Connsys Jarvis

## 什麼是 connsys-jarvis

Connsys Jarvis 是一個 **Multi-Expert AI 協作框架**，讓 firmware 工程師透過 AI coding tools 加速開發。
每個 Expert 封裝特定領域的知識、技能與行為規範，由 AI 在對話中自動載入並執行。
框架支援多 Expert 同時安裝、跨 domain 共用 skill，並相容 Claude Code Plugin 生態系。

---

## 三種安裝方法

| 方法 | 適合工具 | 優點 | 缺點 |
|------|---------|------|------|
| ① `setup.py` | Claude Code / Open Code / Gemini | 跨 AI 工具通用、支援 multi-expert、可產生 CLAUDE.md | 需要 Python、需 clone repo |
| ② Claude Marketplace CLI | Claude Code | 兩行安裝、自動遞迴安裝 dependencies、不需 clone repo | 僅 Claude Code、無法安裝 CLAUDE.md |
| ③ `npx skills add` | Claude Code / Open Code | 單一 skill 快速安裝 | 僅安裝 skills（不含 hooks/MCP）、容易混亂需小心管理 |

> **重要**：所有方法都建議安裝到 **project folder**（加 `--scope project`），不要安裝到 `~/.claude/`。

### 方法一：setup.py

```bash
cd /path/to/workspace
git clone https://github.com/swchen44/connsys-jarvis.git
python connsys-jarvis/scripts/setup.py --init wifi-bora/wifi-bora-base-expert/expert.json
source .connsys-jarvis/.env
```

常用操作：

```bash
# 新增 Expert
python connsys-jarvis/scripts/setup.py --add sys-bora/sys-bora-preflight-expert/expert.json

# 移除 Expert
python connsys-jarvis/scripts/setup.py --remove sys-bora-preflight-expert

# 列出所有 Expert（已安裝 + 可用）
python connsys-jarvis/scripts/setup.py --list

# 查詢指定 Expert
python connsys-jarvis/scripts/setup.py --query framework-base-expert

# 健康診斷
python connsys-jarvis/scripts/setup.py --doctor

# 卸載
python connsys-jarvis/scripts/setup.py --uninstall
```

### 方法二：Claude Plugin Marketplace CLI

使用 Claude Code CLI 兩行安裝。Claude Code 會**自動遞迴安裝**所有 dependencies，無需手動處理順序。

```bash
# 1. 加入 Marketplace（安裝到 project scope，只需執行一次）
claude plugin marketplace add "https://github.com/swchen44/connsys-jarvis.git" --scope project

# 2. 安裝 Expert（Claude Code 自動安裝所有 dependencies）
claude plugin install wifi-bora-memory-slim-expert@connsys-jarvis --scope project
```

> 第一次安裝後，之後只需執行第 2 行即可安裝其他 Expert。

其他常用操作：

```bash
# 查看可用 Plugin
claude plugin list --available --json

# 更新已安裝的 Plugin
claude plugin update wifi-bora-memory-slim-expert@connsys-jarvis --scope project

# 移除 Plugin
claude plugin uninstall wifi-bora-memory-slim-expert@connsys-jarvis --scope project

# 移除 Marketplace
claude plugin marketplace remove connsys-jarvis
```

### 方法三：npx skills (vercel-labs/skills)

```bash
npx skills add swchen44/connsys-jarvis --agent claude-code
```

---

## Expert 結構

```
{domain}/{expert-name}/
├── .claude-plugin/plugin.json   # Plugin manifest（由腳本生成）
├── expert.json                  # 必要
├── soul.md / expert.md          # 可選
├── skills/                      # 主要（跨工具通用）
├── commands/                    # 扁平 .md（slash commands）
├── hooks/hooks.json + scripts/  # 生命週期 hooks
├── rules/                       # 扁平 .md → .claude/rules/
├── agents/                      # 扁平 .md
└── scripts/                     # 輔助腳本
```

> **Skills 為主要機制（跨工具通用）。commands/hooks/rules/agents 為 Claude Code Plugin 相容層。**

### 命名規則

| 類型 | 命名格式 | 範例 |
|------|---------|------|
| commands | `{expert-name}-{action}-cmd.md` | `wifi-bora-memory-slim-build-cmd.md` |
| hooks | `hooks/scripts/{expert-name}-{action}-hook.sh` | `hooks/scripts/wifi-bora-memory-slim-precompact-hook.sh` |
| rules | `{expert-name}-{topic}-rule.md` | `wifi-bora-memory-slim-coding-rule.md` |

### expert.json 必要欄位

| 欄位 | 說明 |
|------|------|
| `name` | Expert 的唯一識別名稱（kebab-case） |
| `domain` | 所屬 domain（例如 `framework`、`wifi-bora`）|
| `owner` | 負責維護的團隊（例如 `wifi-team`）|
| `internal.skills` | 此 Expert 自身提供的 skill 清單（可為空 `[]`）|

### Expert 命名規則

```
{domain}-{purpose}-expert
```

- Base expert：每個 domain 恰好一個，設 `is_base: true`，無 dependencies
- 目錄路徑：`connsys-jarvis/{domain}/{domain}-{purpose}-expert/`

---

## 建立新 Expert

使用 `framework-expert-create-flow` skill 互動式引導建立。觸發方式：在對話中說「create expert」或「新增 expert」。

簡化步驟：

1. **建立資料夾** — 依命名規則在對應 domain 目錄下建立
2. **建立 expert.json** — 填寫 name、domain、owner、dependencies、internal.skills
3. **（可選）建立 soul.md / expert.md** — 定義方法論、技術約束
4. **建立 skills** — 主要重點，每個 skill 一個子目錄 + SKILL.md
5. **執行 `create_plugin_from_expert.py`** — 生成 plugin.json 和 marketplace.json 供 Marketplace 使用

```bash
python connsys-jarvis/framework/framework-base-expert/skills/framework-expert-create-flow/scripts/create_plugin_from_expert.py
```

生成後即可用 `claude plugin install <name>@connsys-jarvis --scope project` 安裝。

---

## 建立新 Skill

使用 `framework-skill-create-flow` skill 互動式引導建立。觸發方式：在對話中說「create skill」或「新增 skill」。

Skill 命名規則：`{domain}-{name}-{type}`

| 類型 | 用途 |
|------|------|
| `flow` | 標準作業程序（SOP）、多步驟互動引導 |
| `knowhow` | 領域知識、架構參考、protocol 規範 |
| `tool` | 外部工具操作指南（git、CLI、API 等） |

---

## 場景支援

| 場景 | 判斷條件 | 說明 |
|------|---------|------|
| **Agent First** | workspace 根目錄有 `codespace/` 子目錄 | AI 在獨立環境操作 |
| **Legacy** | workspace 根目錄有 `.repo` 目錄 | 傳統 Android repo 結構 |

---

## Plugin 相容性

- **Expert = Claude Code Plugin**（1:1 映射）
- `create_plugin_from_expert.py` 從 expert.json 生成 `plugin.json` + `marketplace.json`（含 dependencies）
- Claude Code 安裝時自動遞迴解析 dependencies，無需手動指定安裝順序
- **限制**：Plugin 無法注入 CLAUDE.md，需額外執行 `setup.py` 補齊

### Skill 命名與短名呼叫

Plugin 安裝後，skill 全名會帶 plugin 前綴（如 `framework-base-expert:framework-skill-create-flow`）。但使用者**只需輸入短名即可呼叫**：

```
/framework-skill-create-flow        ← 短名，Claude Code 自動匹配
/framework-base-expert:framework-skill-create-flow  ← 全名，也可以用
```

**原理**：Claude Code 的 `findCommand()` 會比對 SKILL.md frontmatter 的 `name` 欄位。只要 frontmatter 有 `name`，短名就能匹配。這對 skills、commands、agents 都適用。

> **撰寫 SKILL.md 時，務必在 frontmatter 加上 `name` 欄位。**

---

## 執行測試

```bash
cd connsys-jarvis

# 全部測試
uvx pytest scripts/tests/ -v

# 只跑某一層
uvx pytest scripts/tests/unit/ -v           # 純函式單元測試
uvx pytest scripts/tests/integration/ -v   # cmd_* 整合測試
uvx pytest scripts/tests/e2e/ -v           # CLI 黑箱 E2E 測試
```

---

## Roadmap

- Skill 使用分析（收集頻率、錯誤率、缺失需求）
