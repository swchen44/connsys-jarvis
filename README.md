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

---

## 開發者指南

本章節說明如何在本地開發新的 Expert 或 Skill，並完成從建立到發佈的完整流程。

### 步驟 1：建立 Workspace 資料夾

```bash
mkdir ~/workspace && cd ~/workspace
```

> Workspace 是所有 Expert repo 和工作目錄的共同根目錄，**不要**在已有 git repo 的資料夾內建立。

---

### 步驟 2：Clone Repo 並安裝 framework-base-expert

```bash
# Clone repo
git clone https://github.com/swchen44/connsys-jarvis.git

# 至少安裝 framework-base-expert（提供 skill/expert 建立流程）
python3 connsys-jarvis/scripts/setup.py --init framework/framework-base-expert/expert.json

# 啟動環境變數（每次開新 shell 都要執行）
source .connsys-jarvis/.env
```

> `framework-base-expert` 包含 `framework-skill-create-flow` 和 `framework-expert-create-flow`，是開發的最小必要基礎。

若需要安裝其他 Expert（例如你要在 wifi-bora domain 下開發）：

```bash
python3 connsys-jarvis/scripts/setup.py --add wifi-bora/wifi-bora-base-expert/expert.json
```

---

### 步驟 3：使用 AI 引導建立 Skill 或 Expert

啟動 Claude Code，在對話中輸入以下短名即可觸發引導流程：

```
/framework-skill-create-flow    ← 建立新 Skill
/framework-expert-create-flow   ← 建立新 Expert
```

**建立 Skill 的注意事項：**
- Skill 命名格式：`{domain}-{name}-{type}`（type = flow / knowhow / tool）
- SKILL.md frontmatter **務必加上 `name` 欄位**，否則短名呼叫會失敗：
  ```yaml
  ---
  name: my-skill-name
  description: ...
  ---
  ```
- 使用 `framework-skill-create-flow` 的 **eval 功能**自動產生 test case，驗證 skill 的觸發條件和預期輸出
- 建立後檢查 skill 目錄下的 `README.md` 是否完整

---

### 步驟 4：手動 Symlink 快速測試

不需要走完整安裝流程，直接 symlink skill 到 `.claude/skills/` 即可在 Claude Code 中立即測試：

```bash
# 建立 symlink（從 workspace 根目錄執行）
ln -s $(pwd)/connsys-jarvis/<domain>/<expert>/skills/<skill-name> \
      .claude/skills/<skill-name>

# 範例：測試 wifi-bora-memslim-flow
ln -s $(pwd)/connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/skills/wifi-bora-memslim-flow \
      .claude/skills/wifi-bora-memslim-flow
```

**測試時觀察 Token 用量：**

在 Claude Code 對話中執行：
```
/context
```
可查看當前 context 使用量。測試 skill 載入前後對比，確認 SKILL.md 內容精簡不過度膨脹 context。

> 測試完畢記得移除暫時 symlink，再用 `setup.py --add` 正式安裝。

---

### 步驟 5：生成 plugin.json 和 marketplace.json

開發完成後，執行腳本更新 Plugin 清單：

```bash
# 預覽（不寫檔）
python3 connsys-jarvis/framework/framework-base-expert/skills/framework-expert-create-flow/scripts/create_plugin_from_expert.py --dry-run

# 正式生成
python3 connsys-jarvis/framework/framework-base-expert/skills/framework-expert-create-flow/scripts/create_plugin_from_expert.py
```

生成的檔案：
- `<expert>/.claude-plugin/plugin.json` — 每個 expert 的 Claude Code Plugin 宣告（含 dependencies）
- `.claude-plugin/marketplace.json` — Marketplace 總覽（含各 expert 的直接依賴）

---

### 步驟 6：執行 Doctor 檢查

Push 前執行完整健康診斷，確認所有結構正確：

```bash
python3 connsys-jarvis/scripts/setup.py --doctor
```

重點檢查項目：
- **F2** expert.json 必要欄位齊全
- **F3** 所有 skill 資料夾都有 SKILL.md
- **F5 Plugin JSON Dependency Sync** — 確認 expert.json / plugin.json / marketplace.json 三份 JSON 的 dependencies 一致。若出現 ❌，執行步驟 5 重新生成即可

所有項目顯示 `✅` 才可繼續。

---

### 步驟 7：Push for Review

**GitHub PR：**
```bash
git checkout -b feat/my-new-skill
git add connsys-jarvis/<domain>/<expert>/
git commit -m "feat: add <skill-name> skill to <expert>"
git push origin feat/my-new-skill
# 到 GitHub 開 PR
```

**Gerrit：**
```bash
git add connsys-jarvis/<domain>/<expert>/
git commit -m "feat: add <skill-name> skill to <expert>"
git push origin HEAD:refs/for/main
```

---

### 步驟 8：使用者角度安裝測試

Push 合併後，以使用者身份從頭測試安裝流程：

```bash
# 1. 加入 Marketplace
claude plugin marketplace add "https://github.com/swchen44/connsys-jarvis.git" --scope project

# 2. 安裝目標 Expert（Claude Code 自動安裝所有 dependencies）
claude plugin install <expert-name>@connsys-jarvis --scope project

# 3. 確認安裝結果
claude plugin list --json
```

確認安裝的 plugin 數量符合預期（目標 expert + 所有遞移依賴），重啟 Claude Code 後驗證 skill 可正常呼叫。
