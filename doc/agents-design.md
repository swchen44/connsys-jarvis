# Consys Experts — 設計書

**文件版本**：v3.8
**狀態**：Draft
**依據**：agents-requirements.md v3.8

> **注意**：本文件中所列的 expert、skill 名稱均為**示例**，用於說明命名規則與架構設計。實際 expert 與 skill 的規劃以團隊討論為準。

---

## 1. 系統架構總覽

### 1.1 Harness 架構觀

本系統依據 **Harness Engineering** 的精神設計（參考：[Birgitta Böckeler / Martin Fowler Blog](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)）。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Consys Expert Harness                        │
│                                                                     │
│  上下文工程  SKILL.md / expert.md / expert.local.md                 │
│  架構約束    Hooks（pre-compact）/ Expert 行為規範                   │
│  垃圾回收    session-end 整理記憶 / push connsys-memory              │
│                                                                     │
│         ↓ 透過以上三層強化 AI 核心能力（Think/Plan/Act/Learn）       │
│                                                                     │
│     Claude Code（現在）→ OpenClaw（Phase 2）→ ADK/SDK（Phase 3）    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Script 實作語言優先策略

詳見 [§8 Script 實作語言優先策略](#8-script-實作語言優先策略)。

### 1.3 Consys Expert 組成

```
Consys Expert = Agent 核心能力 + Workflow（hooks）+ Tool（commands）+ Knowledge（skills）
              + Sub-Agent（agents）

每個 Expert 的內容分三個來源：
  ① framework-base-expert  → 跨所有 domain 共用
  ② {domain}-base-expert   → 該 domain 內部共用
  ③ {expert} internal        → 該 Expert 自己的私有內容

全部透過 symlink 接入 workspace/.claude/（project level）
```

### 1.4 為什麼採用 Symlink 架構

**Agent 生態圈變化極快，設計必須有最大彈性。**

外部 Agent 框架（Claude Code、OpenClaw、ADK、gitagent 等）持續快速演進，採用 symlink 安裝模式的理由：

| 優點 | 說明 |
|------|------|
| **即換即生效** | 更改 expert 內容，下次 Claude 啟動即可看到，不需重裝 |
| **多版本共存** | 可以同時維護多個 Expert 版本，切換只需重新 link |
| **零侵入性** | Workspace 的 `.claude/` 只有 symlink，不污染 expert repo |
| **跨平台** | Linux/macOS 用 symlink；Windows 用 copy（自動降級） |
| **未來框架遷移** | 換成 OpenClaw 或其他框架時，setup.py 只需改寫 target 路徑 |

參考：[open-gitagent/gitagent](https://github.com/open-gitagent/gitagent)

---

## 2. 五層資料夾設計（Layer 1–5）

### 2.1 層次總覽

```
connsys-jarvis/
│
├── {domain}/                              Layer 1：domain
│   ├── {domain}-{name}-expert/            Layer 2：internal expert（命名含 domain prefix）
│   │   ├── skills/                        Layer 3：工具資料夾
│   │   │   └── {domain}-{name}-{type}/    Layer 4：skill（命名含 domain + type）
│   │   │       └── SKILL.md
│   │   ├── hooks/
│   │   ├── commands/
│   │   │   └── {domain}-{name}-tool/
│   │   │       └── COMMAND.md
│   │   ├── agents/
│   │   │   └── {agent-name}.md
│   │   ├── test/
│   │   ├── report/
│   │   │   ├── execution-report.md    ← 人工維護
│   │   │   └── test-report.md     ← 人工維護
│   │   ├── expert.json            ← Manifest（必要）
│   │   ├── soul.md                ← Identity & personality（可選）
│   │   ├── expert.md              ← Key behaviors & tools（可選）
│   │   └── README.md
│   └── {domain}-external-expert/        Layer 2：external expert（名字含 external 識別）
│       └── {original-tool-name}/         Layer 3：原始名稱（照 git submodule 命名）
```

### 2.2 Layer 1：Domain 定義

| Domain | 用途 |
|--------|------|
| `framework` | 管理 Expert 用的 Expert（建立/強化 skill、memory、learn、反思回饋、找尋 expert） |
| `wifi` | Wi-Fi 相關開發 Expert（fw / driver / debug / CI/CD） |
| `bt` | Bluetooth 相關開發 Expert |
| `system` | System / Platform 相關開發 Expert |

### 2.3 Layer 2：Internal vs External

所有 Expert（internal + external）統一放在 domain 下，命名均以 `-expert` 結尾：

```
{domain}/
├── {domain}-{name}-expert/          ← 內部 Expert（team 自行維護）
└── {domain}-external-expert/        ← 外部工具 Expert（git submodule，名字含 external 識別）
    （可加入工具名：{domain}-{tool}-external-expert/，通常用 {domain}-external-expert/ 即可）
```

**統一命名的好處**：
- `setup.py` 的 `*/*-expert` glob 一次掃描所有 Expert（internal + external）
- 名字本身標示身份：`{domain}-external-expert` 含 `external` 即為外部工具

**External expert 的歸屬原則**：
- 討論後，各 domain 代表同意 → 放 `framework/framework-external-expert/`（共用）
- 各 domain 自行維護 → 放各自的 `{domain}-external-expert/`（命名不能衝突）

### 2.4 Layer 3：Expert 命名規則

**Internal expert**：
```
{domain}-{description}-expert

範例：
  framework-base-expert              ← 跨 domain 共用容器
  sys-bora-base-expert               ← sys-bora domain 共用容器
  sys-bora-preflight-expert
  wifi-bora-base-expert              ← wifi-bora domain 共用容器
  wifi-bora-memory-slim-expert
  wifi-bora-cr-robot-expert
  wifi-bora-coverity-expert
  bt-bora-base-expert                ← bt-bora domain 共用容器
  bt-bora-security-expert
  lrwpan-bora-base-expert
  wifi-gen4m-base-expert
  wifi-logan-base-expert
```

**`{domain}-base-expert` 的特殊規則**：
- 每個 domain 必有一個 `{domain}-base-expert`
- 作用：存放該 domain 內所有 expert 共用的 skill / hook / command
- `install.sh` 無作用（此 expert 僅作為容器，不直接安裝）
- `framework-base-expert` 特別：存放跨所有 domain 共用的 skill / hook

**External expert**：
```
照原始工具名稱（不加 domain prefix）

範例：
  skill-creator
  claude-memory-engine
  defuddle
```

### 2.5 Layer 4：Expert 內部資料夾

每個 expert 的資料夾結構（**expert 資料夾本身不含 install.sh 和 CLAUDE.md**，由頂層 `connsys-jarvis/setup.py` 統一管理）：

```
{expert}/
│   # ── Core Identity (required) ────────────────────────────
├── .claude-plugin/plugin.json  ← Plugin manifest（由 create_plugin_from_expert.py 生成）
├── expert.json    ← Manifest（必要）：name, version, owner, model, skills, tools,
│                     transitions, dependencies, exclude_symlink
│
│   # ── Optional Identity & Behavior ─────────────────────
├── soul.md        ← （可選）Identity, personality, communication style,
│                     Values & Principles, Collaboration Style
├── expert.md      ← （可選）Key Behaviors, Constraints, Tools Available, Skills
│                     （setup.py 讀此檔產生 CLAUDE.md @include）
│
│   # ── Content Folders ────────────────────────────────────
├── skills/        ← Knowledge（主要機制，跨工具通用）：多個 skill 資料夾（每個 skill 見 Layer 5）
│   └── {domain}-{name}-{type}/
│       ├── SKILL.md
│       ├── README.md
│       ├── test/
│       └── report/
│
├── hooks/         ← Workflow：生命週期 hooks（可選）
│   ├── hooks.json             ← Hook 定義（Claude Code Plugin 格式）
│   └── scripts/               ← Hook 腳本
│       └── {expert-name}-{action}-hook.sh  ← Shell 優先；複雜邏輯用 .py
│
├── agents/        ← Sub-Agents：Claude subagent 定義（可選）
│   └── {agent-name}.md    ← subagent 的 prompt / 描述
│
├── commands/      ← Slash Commands（扁平 .md，Claude Code Plugin 相容層）
│   └── {expert-name}-{action}-cmd.md
│
├── rules/         ← Rules（扁平 .md → .claude/rules/，可選）
│   └── {expert-name}-{topic}-rule.md
│
├── scripts/       ← 輔助腳本（可選）
├── test/          ← Expert 層級測試腳本
├── report/        ← 執行過程、結果（人工維護）
└── README.md      ← History、使用說明、設計說明

> **Skills 為主要機制（跨工具通用）。commands/hooks/rules/agents 為 Claude Code Plugin 相容層。**
>
> Hook 腳本可透過 `${CLAUDE_PLUGIN_ROOT}` 環境變數取得 plugin 根目錄路徑，
> 避免在路徑中使用 `..` 相對路徑。
```

**`{domain}-base-expert` 的資料夾結構**（同上，作為共用資源容器）：

```
{domain}-base-expert/
├── .claude-plugin/plugin.json  ← Plugin manifest（由腳本生成）
├── expert.json    ← is_base: true
├── soul.md        ← （可選）
├── expert.md      ← （可選）
├── skills/        ← 此 domain 共用的 skills
├── hooks/         ← 此 domain 共用的 hooks（可選）
│   ├── hooks.json
│   └── scripts/
├── agents/        ← 此 domain 共用的 subagents（可選）
├── commands/      ← 此 domain 共用的 commands（扁平 .md，可選）
├── rules/         ← 此 domain 共用的 rules（扁平 .md，可選）
├── test/
├── report/
└── README.md
```

> **agents/ 資料夾**：存放 Claude subagent 的 prompt 描述文件。subagent 是由主 Expert 呼叫的子任務 Agent，適合拆分為獨立工作單元（如：自動分析 log、自動查找 document）。參考：[open-gitagent/gitagent](https://github.com/open-gitagent/gitagent)

### 2.6 Layer 5：Skill 命名規則

**命名格式**：`[domain]-[skill-name]-[type]`

| 部分 | 說明 | 範例 |
|------|------|------|
| `[domain]` | Layer 1 的 domain 名稱 | `wifi-bora`, `wifi-gen4m`, `wifi-logan`, `bt-bora`, `sys-bora`, `lrwpan-bora`, `framework` |
| `[skill-name]` | 描述性名稱（英文，用 `-` 分隔） | `build`, `coredump`, `memory` |
| `[type]` | `flow` / `knowhow` / `tool` | `flow` |

**Type 定義**：

| Type | 用途 | 範例內容 |
|------|------|---------|
| `flow` | 有清楚步驟的工作流程 | 下載程式碼→編譯→解決 build error 的 SOP |
| `knowhow` | 基礎知識與背景資料 | Wi-Fi 協定知識、SW/HW 架構、程式碼規則、linker script rule、rom/ram patch rule、decode coredump、symbol map |
| `tool` | 外部工具的操作方法 | repo / gerrit 操作、preflight dashboard 查詢、tmux/ssh/uart/adb 控制裝置、AUTOTEST 操作、抓取 uart log、讀寫 Wiki / Gerrit / CR 系統 |

**Skill 命名範例**（以下為示例，非完整清單）：

```
# framework domain（跨 domain 共用）
framework-expert-discovery-knowhow   ← 有哪些 Expert 及各自能力
framework-memory-tool                ← connsys-memory 操作
framework-skill-create-flow          ← 互動式建立符合規範的 Skill（SKILL.md + 目錄結構）
framework-expert-create-flow         ← 互動式建立符合規範的 Expert（expert.json + 可選 soul.md/expert.md）

# wifi domain
wifi-bora-protocol-knowhow                ← Wi-Fi 協定基礎知識
wifi-bora-arch-knowhow                    ← Wi-Fi SW/HW 架構
wifi-bora-coderule-knowhow                ← 程式碼撰寫規則
wifi-bora-build-flow                 ← fw 下載/編譯流程 SOP
wifi-gen4m-build-flow                ← gen4m driver build 流程
wifi-bora-ast-tool              ← 特殊 compile error 處理
wifi-bora-linkerscript-knowhow       ← Linker script 規則
wifi-bora-rompatch-knowhow           ← ROM/RAM patch 規則
wifi-bora-coredump-knowhow           ← Decode coredump 方法
wifi-bora-symbolmap-knowhow          ← Symbol map 解讀
wifi-bora-memory-knowhow             ← 觀察 memory 使用
wifi-bora-uart-tool                  ← 抓取 uart log
wifi-bora-adbshell-tool              ← adb shell 控制
wifi-bora-ast-tool                   ← AUTOTEST 平台操作
wifi-bora-coverity-flow                       ← CI/CD 流程 SOP

# bt domain
bt-bora-protocol-knowhow
bt-bora-arch-knowhow
bt-bora-coderule-knowhow             ← bt 程式碼撰寫規則
bt-bora-build-flow
bt-bora-fw-build-flow                ← bt fw 完整 build 流程

# system domain（跨 wifi/bt/system 共用工具）
sys-bora-gerrit-tool                   ← Gerrit 操作（原 wifi-gerrit-tool）
sys-bora-repo-tool          ← Android repo / multi-repo 操作（原 wifi-repo-tool）
sys-bora-preflight-flow                ← Preflight dashboard 查詢（原 wifi-preflight-tool）
sys-bora-core-tracer-gdb-tool        ← CoreTracer / GDB 工具操作
sys-bora-device-tool                 ← 裝置控制（tmux/ssh/uart/adb）
sys-bora-cicd-tool
```

### 2.7 Layer 5：Skill 內部資料夾

每個 Skill 資料夾（`{domain}-{name}-{type}/`）的標準結構：

```
{domain}-{name}-{type}/          Layer 5：skill 資料夾
├── SKILL.md                     ← Skill 主體（YAML frontmatter + 內容）【必要】
├── README.md                    ← 台灣繁體中文；介紹/Owner/功能/目標/設計理念/風險 【必要】
├── test/                        ← Skill 測試【非必要，品質管理啟用後成為必要】
│   ├── test_{skill_name}.py     ← Python pytest：unit test（有複雜邏輯時加）
│   ├── conftest.py              ← pytest fixtures（可選）
│   └── test-data.json           ← 測試輸入資料（可選）
└── report/                      ← 執行過程、結果、token 用量【非必要，品質管理啟用後成為必要】
    ├── execution-report.md      ← 人工維護
    └── test-report.md           ← 人工或 CI 自動生成
```

> **`test/` 與 `report/` 目前非必要**，但當 Skill 品質管理機制啟用（eval loop、CI 驗證）時將成為必要。建立 Skill 時可預先建立空目錄，待有內容時再填入。

| 檔案/資料夾 | 用途 | 必要性 | 維護方式 |
|-----------|------|-------|---------|
| `SKILL.md` | Skill 主體，Claude 在執行時讀取 | **必要** | 人工撰寫，`framework-learn-expert` 未來可自動更新 |
| `README.md` | 台灣繁體中文；介紹、Owner、功能、目標、設計理念、風險、替代方案 | **必要** | 人工維護 |
| `test/test_xxx.py` | pytest unit test，適用有 Python helper 的 skill | 非必要，未來必要 | 人工撰寫，`pytest test/` 自動執行 |
| `report/` | 每次執行的過程記錄、結果摘要、token 用量統計 | 非必要，未來必要 | 人工或 hook 自動寫入 |

**Command 命名規則**（扁平 .md，命名含 expert-name）：
```
{expert-name}-{action}-cmd.md

範例：
  framework-base-experts-cmd.md    ← /experts 指令
```

**Hook 命名規則**：
```
hooks/
├── hooks.json                              ← Hook 定義（Claude Code Plugin 格式）
└── scripts/
    └── {expert-name}-{action}-hook.sh      ← Shell 優先

範例：
  hooks/scripts/framework-base-precompact-hook.sh
```

**Rule 命名規則**（扁平 .md → .claude/rules/）：
```
{expert-name}-{topic}-rule.md

範例：
  wifi-bora-base-coding-rule.md
```

> **命名慣例小結**：commands/hooks/rules 的檔名均以 `{expert-name}-` 為前綴，確保全域唯一，避免跨 Expert 衝突。

### 2.8 using-knowhow Skill 模式

#### 問題背景

setup.py 安裝模式會產生 CLAUDE.md，原本透過 `@include` 載入各 expert 的 soul.md（方法論）和 expert.md（技術約束）。但 **Claude Plugin Marketplace** 和 **npx skills** 安裝模式不會產生 CLAUDE.md，導致 expert 的指導原則在這兩種模式下完全遺失。

#### 解決方案

為每個擁有 soul.md 和/或 expert.md 的 expert 建立一個 `{expert-name}-using-knowhow` companion skill，將指導原則封裝為標準 skill：

| 項目 | 說明 |
|------|------|
| 命名 | `{expert-name}-using-knowhow` |
| Type | `knowhow` |
| 內容 | soul.md + expert.md 合併 |
| 觸發 | SKILL.md description 設計為在使用同 domain 任何 skill 時自動觸發 |
| 可選性 | soul.md / expert.md 為可選，因此 using-knowhow 也是**可選** |

#### 三種安裝模式下的行為

| 模式 | CLAUDE.md | using-knowhow skill |
|------|-----------|---------------------|
| setup.py | 生成，包含 `MUST use the skill` 指示 | 透過 symlink 安裝 |
| Plugin Marketplace | 不生成 | 作為標準 skill 安裝 |
| npx skills | 不生成 | 作為標準 skill 安裝 |

#### CLAUDE.md v3.0 格式

setup.py v3.0 不再 `@include` soul.md / expert.md，改為對每個已安裝 expert 輸出 skill 指示：

```markdown
## Expert Guidelines

MUST use the skill {expert-name}-using-knowhow for expert guidelines and methodology, if the skill exists.
```

#### AGENTS.md Symlink

setup.py 在生成 CLAUDE.md 後，額外建立 `AGENTS.md → CLAUDE.md` 相對路徑 symlink。目的是讓其他 AI coding 工具（Open Code、Gemini 等）透過 AGENTS.md 讀取相同的 context。卸載時會一併清理。

#### Description 設計原則

description 使用強語氣措辭（MANDATORY / MUST），最大化模型自動讀取的機率。參考 [superpowers/using-superpowers](https://github.com/obra/superpowers) 的 aggressive 語言模式：

- 使用 "MANDATORY" 和 "MUST" 字眼
- 明確提及 domain prefix（如 "wifi-bora"）
- 包含 "Once read... no need to re-read" 以減少重複載入

#### 維護規則

- soul.md / expert.md 簡化為 HTML 註解，禁止直接修改：
  ```html
  <!-- ⚠️ 請勿直接修改本檔案。
       本檔內容已轉換至 {expert-name}-using-knowhow skill。
       如需修改指導原則，請編輯該 skill 的 SKILL.md。
       原因詳見 doc/agents-design.md §2.8「using-knowhow Skill 模式」。 -->
  ```
- 修改指導原則時，應直接編輯 using-knowhow skill 的 SKILL.md
- 新建 expert 時，`framework-expert-create-flow` Step 4.5 會引導建立 using-knowhow skill（可選）

#### ⚠️ 風險

此設計依賴模型的 skill description matching 機制，**不保證 100% 觸發率**。Claude 可能忽略 description 而不自動讀取 using-knowhow skill，導致指導原則在 Plugin / npx 模式下遺失。

**緩解措施**：
- 使用 MANDATORY / MUST 強語氣措辭
- Pilot 驗證觸發率後再推廣至所有 expert
- 使用者可手動呼叫 `/{expert-name}-using-knowhow` 確保載入

---

## 3. 完整目錄結構

connsys-jarvis/
├── scripts/                        ← 安裝程式與測試
│   ├── setup.py                  ← 唯一安裝程式（Python stdlib）
│   └── test/
│       ├── conftest.py           ← 共用 fixtures（全層共用）
│       ├── test_setup.py         ← 舊版 monolith（向後相容，仍可執行）
│       ├── unit/                 ← 單元測試（TC-U01~U08，38 tests）
│       │   └── test_unit.py
│       ├── integration/          ← 整合測試（TC-U09~U22，73 tests）
│       │   ├── conftest.py
│       │   └── test_integration.py
│       └── e2e/                  ← 端對端測試（TC-E01~E06，18 tests）
│           └── test_e2e.py
├── README.md
│
├── framework/                      ← 框架 domain（跨所有 domain 共用）
│   └── framework-base-expert/      ← 共用 skill/hook/agent 容器
│       ├── expert.json
│       ├── soul.md                 ← （可選）
│       ├── expert.md               ← （可選）
│       ├── skills/
│       │   ├── framework-expert-discovery-knowhow/
│       │   ├── framework-memory-tool/
│       │   ├── framework-skill-create-flow/
│       │   └── framework-expert-create-flow/
│       ├── hooks/
│       │   ├── session-start.sh
│       │   ├── session-end.sh
│       │   ├── pre-compact.sh
│       │   └── mid-session-checkpoint.sh
│       ├── agents/
│       ├── commands/
│       │   └── framework-experts-tool/
│       ├── test/ └── report/ └── README.md
│
├── sys-bora/                       ← System / SoC platform domain
│   ├── sys-bora-base-expert/       ← sys domain 共用知識容器
│   │   ├── expert.json
│   │   ├── skills/
│   │   │   ├── sys-bora-gerrit-tool/
│   │   │   ├── sys-bora-repo-tool/
│   │   │   ├── sys-bora-build-knowhow/
│   │   │   ├── sys-bora-arch-knowhow/
│   │   │   ├── sys-bora-ld-knowhow/
│   │   │   ├── sys-bora-config-knowhow/
│   │   │   └── sys-bora-manifest-build-knowhow/
│   │   ├── hooks/ ├── agents/ ├── commands/ ├── test/ └── report/
│   │
│   └── sys-bora-preflight-expert/  ← 跨 domain 共用工具（非 base）
│       ├── expert.json             ← depends on sys-bora-base-expert
│       ├── skills/
│       │   ├── sys-bora-preflight-flow/
│       │   ├── sys-bora-preflight-result-tool/
│       │   ├── sys-bora-gerrit-commit-flow/
│       │   └── sys-bora-ci-label-knowhow/
│       ├── agents/
│       │   └── preflight-monitor.md
│       ├── hooks/ ├── commands/ ├── test/ └── report/
│
├── wifi-bora/                      ← WiFi Bora firmware domain
│   ├── wifi-bora-base-expert/      ← wifi-bora 共用知識容器
│   │   ├── expert.json
│   │   ├── skills/
│   │   │   ├── wifi-bora-protocol-knowhow/
│   │   │   ├── wifi-bora-arch-knowhow/
│   │   │   ├── wifi-bora-coderule-knowhow/
│   │   │   ├── wifi-bora-build-flow/
│   │   │   ├── wifi-bora-rompatch-knowhow/
│   │   │   ├── wifi-bora-linkerscript-knowhow/
│   │   │   ├── wifi-bora-symbolmap-knowhow/
│   │   │   ├── wifi-bora-memory-knowhow/
│   │   │   └── wifi-bora-sds-knowhow/
│   │   ├── hooks/ ├── agents/ ├── commands/ ├── test/ └── report/
│   │
│   ├── wifi-bora-memory-slim-expert/
│   │   ├── expert.json   ← depends: wifi-bora-base, sys-bora-preflight
│   │   ├── skills/
│   │   │   ├── wifi-bora-memslim-flow/
│   │   │   ├── wifi-bora-ast-tool/
│   │   │   ├── wifi-bora-lsp-tool/
│   │   │   └── wifi-bora-wut-tool/
│   │   ├── agents/ ├── hooks/ ├── commands/ ├── test/ └── report/
│   │
│   ├── wifi-bora-cr-robot-expert/
│   │   ├── expert.json   ← depends: wifi-bora-base, sys-bora-preflight
│   │   ├── skills/
│   │   │   ├── wifi-bora-debug-sop-flow/
│   │   │   ├── wifi-bora-coredump-knowhow/
│   │   │   ├── wifi-bora-ast-tool/
│   │   │   ├── wifi-bora-lsp-tool/
│   │   │   ├── wifi-bora-wut-tool/
│   │   │   └── wifi-bora-risk-report-flow/
│   │   ├── agents/ ├── hooks/ ├── commands/ ├── test/ └── report/
│   │
│   ├── wifi-bora-coverity-expert/
│   │   ├── expert.json   ← depends: wifi-bora-base, sys-bora-preflight
│   │   ├── skills/
│   │   │   ├── wifi-bora-coverity-flow/
│   │   │   ├── wifi-bora-coverity-cr-tool/
│   │   │   └── wifi-bora-risk-report-flow/
│   │   ├── agents/ ├── hooks/ ├── commands/ ├── test/ └── report/
│   │
│   └── wifi-bora-external-expert/   ← 外部工具（git submodule）
│
├── bt-bora/                        ← Bluetooth Bora firmware domain
│   ├── bt-bora-base-expert/        ← bt-bora 共用知識容器
│   │   ├── expert.json
│   │   ├── skills/
│   │   │   ├── bt-bora-protocol-knowhow/
│   │   │   ├── bt-bora-arch-knowhow/
│   │   │   ├── bt-bora-coderule-knowhow/
│   │   │   ├── bt-bora-build-flow/
│   │   │   └── bt-bora-sds-knowhow/
│   │   ├── hooks/ ├── agents/ ├── commands/ ├── test/ └── report/
│   │
│   ├── bt-bora-security-expert/
│   │   ├── expert.json   ← depends: bt-bora-base, sys-bora-preflight
│   │   ├── skills/
│   │   │   ├── bt-bora-security-rule-knowhow/
│   │   │   ├── bt-bora-security-analysis-flow/
│   │   │   ├── bt-bora-ast-tool/
│   │   │   └── bt-bora-lsp-tool/
│   │   ├── agents/ ├── hooks/ ├── commands/ ├── test/ └── report/
│   │
│   └── bt-external-expert/          ← 外部工具（通用命名）
│       （可細化：bt-xxx-external-expert/）
│
├── lrwpan-bora/                    ← LR-WPAN (802.15.4) Bora firmware domain
│   └── lrwpan-bora-base-expert/
│       ├── expert.json
│       ├── skills/
│       │   ├── lrwpan-bora-protocol-knowhow/
│       │   ├── lrwpan-bora-arch-knowhow/
│       │   ├── lrwpan-bora-build-flow/
│       │   └── lrwpan-bora-sds-knowhow/
│       ├── hooks/ ├── agents/ ├── commands/ ├── test/ └── report/
│
├── wifi-gen4m/                     ← WiFi Gen4M driver domain
│   └── wifi-gen4m-base-expert/
│       ├── expert.json
│       ├── skills/
│       │   ├── wifi-gen4m-protocol-knowhow/
│       │   ├── wifi-gen4m-arch-knowhow/
│       │   ├── wifi-gen4m-build-flow/
│       │   └── wifi-gen4m-sds-knowhow/
│       ├── hooks/ ├── agents/ ├── commands/ ├── test/ └── report/
│
└── wifi-logan/                     ← WiFi Logan driver domain
    └── wifi-logan-base-expert/
        ├── expert.json
        ├── skills/
        │   ├── wifi-logan-protocol-knowhow/
        │   ├── wifi-logan-arch-knowhow/
        │   ├── wifi-logan-build-flow/
        │   └── wifi-logan-sds-knowhow/
        ├── hooks/ ├── agents/ ├── commands/ ├── test/ └── report/

```

> **cross-domain dependency 範例**：`wifi-bora-cr-robot-expert` 的 expert.json 列出
> `sys-bora-preflight-expert` 作為 dependency，並指定只繼承其特定 skills，實現跨 domain 共用。

---

## 4. `expert.json` 格式

### 4.1 一般 Expert（有 dependencies）

```json
{
  "name": "wifi-bora-memory-slim-expert",
  "display_name": "WiFi Bora Memory Slim Expert",
  "domain": "wifi-bora",
  "owner": "wifi-bora-team",
  "description": "分析 Wi-Fi Bora ROM/RAM footprint，協助精簡記憶體用量",
  "version": "1.0.0",
  "triggers": ["memory slim", "ROM 優化", "RAM 分析", "footprint", "記憶體"],
  "transitions": {
    "ANALYSIS_DONE": "wifi-bora-cr-robot-expert"
  },
  "dependencies": [
    {
      "expert": "framework/framework-base-expert",
      "skills": ["framework-expert-discovery-knowhow", "framework-memory-tool"],
      "hooks": ["all"],
      "agents": [],
      "commands": ["framework-experts-tool"]
    },
    {
      "expert": "wifi-bora/wifi-bora-base-expert",
      "skills": ["wifi-bora-arch-knowhow", "wifi-bora-memory-knowhow",
                 "wifi-bora-linkerscript-knowhow", "wifi-bora-symbolmap-knowhow",
                 "wifi-bora-build-flow"],
      "hooks": [],
      "agents": [],
      "commands": []
    },
    {
      "expert": "sys-bora/sys-bora-preflight-expert",
      "skills": ["sys-bora-gerrit-commit-flow", "sys-bora-preflight-flow"],
      "hooks": [],
      "agents": [],
      "commands": []
    }
  ],
  "internal": {
    "skills": [
      "wifi-bora-memslim-flow",
      "wifi-bora-ast-tool",
      "wifi-bora-lsp-tool",
      "wifi-bora-wut-tool"
    ],
    "hooks": [],
    "agents": [],
    "commands": []
  },
  "scenarios": ["agent-first", "legacy"],
  "human_in_the_loop": {
    "require_confirm": ["git push", "make clean"]
  }
}
```

### 4.2 Base Expert（共用資源容器）

Base expert 本身無 dependencies，作為該 domain 共用 skill/hook/agent/command 的容器。其他 expert 透過 `dependencies` 引用它。

```json
{
  "name": "wifi-bora-base-expert",
  "display_name": "WiFi Bora Base",
  "domain": "wifi-bora",
  "description": "wifi-bora domain 共用 skill/hook/command/agent 的容器",
  "version": "1.0.0",
  "is_base": true,
  "dependencies": [],
  "internal": {
    "skills":   ["wifi-bora-protocol-knowhow", "wifi-bora-arch-knowhow", "wifi-bora-coderule-knowhow",
                 "wifi-bora-build-flow", "wifi-bora-rompatch-knowhow", "wifi-bora-linkerscript-knowhow",
                 "wifi-bora-symbolmap-knowhow", "wifi-bora-memory-knowhow", "wifi-bora-sds-knowhow"],
    "hooks":    ["session-start", "session-end", "pre-compact", "mid-session-checkpoint"],
    "agents":   [],
    "commands": []
  },
  "exclude_symlink": {
    "patterns": []
  }
}
```

### 4.3 exclude_symlink 設計（全域 regex 過濾）

`exclude_symlink.patterns` 是**全域正則表達式清單**，在所有 symlink 建立完成後，移除名稱符合任一 pattern 的 link。

**執行順序**：
```
Step 1：依每個 dependency 的 skills/hooks/agents/commands 選擇清單建立 link
Step 2：建立本 expert 自己的 internal skills/hooks/agents/commands 的 link
Step 3：套用 exclude_symlink.patterns，移除名稱符合任一 regex 的 link（全域過濾）
```

範例：
```json
"exclude_symlink": {
  "patterns": [
    ".*-linkerscript-.*",   // 移除所有含 linkerscript 的 link
    ".*-debug-.*"           // 移除所有含 debug 的 link
  ]
}
```

### 4.4 dependencies 選擇規則

| 情況 | 寫法 | 效果 |
|------|------|------|
| **繼承全部** | `"skills": ["all"]` | symlink 該 expert 的所有 skills |
| **正面表列** | `"skills": ["foo-tool", "bar-flow"]` | 只 symlink 指定的 skills |
| **省略 key** | `"skills"` 欄位不寫 | 不繼承該 expert 的任何 skills（空集合）|

> `"hooks"`, `"agents"`, `"commands"` 同理。四個 key 各自獨立控制。

---

## 5. scripts/setup.py 設計

`scripts/setup.py` 是 **connsys-jarvis 唯一的安裝程式**，位於 `connsys-jarvis/scripts/setup.py`，以 Python stdlib 實作，用 `uv run` 執行。Expert 資料夾**不再含 install.sh**。

### 5.1 執行方式與參數

```bash
# 安裝指令（所有指令後都需 source .env）
uv run ./connsys-jarvis/scripts/setup.py --init   framework/framework-base-expert/expert.json
uv run ./connsys-jarvis/scripts/setup.py --add    wifi-bora/wifi-bora-memory-slim-expert/expert.json
uv run ./connsys-jarvis/scripts/setup.py --remove wifi-bora/wifi-bora-memory-slim-expert/expert.json
uv run ./connsys-jarvis/scripts/setup.py --uninstall
uv run ./connsys-jarvis/scripts/setup.py --reset

# 查詢 / 診斷
uv run ./connsys-jarvis/scripts/setup.py --list
uv run ./connsys-jarvis/scripts/setup.py --list --format json
uv run ./connsys-jarvis/scripts/setup.py --query framework-base-expert
uv run ./connsys-jarvis/scripts/setup.py --query framework-base-expert --format json
uv run ./connsys-jarvis/scripts/setup.py --doctor

# source 環境變數（每次執行 setup.py 後都需要）
source .connsys-jarvis/.env
```

| 指令 | 說明 | 影響範圍 |
|------|------|---------|
| `--init <expert.json>` | **全新安裝**：清除所有既有 link，重建 CLAUDE.md，建立 symlink；**memory 不受影響** | 全部重建 |
| `--add <expert.json>` | **疊加安裝**：保留既有 link，加入此 Expert 的 link，更新 CLAUDE.md | 新增 |
| `--remove <expert.json>` | **移除**：移除此 Expert 的 link，重建 CLAUDE.md（若有其他 Expert 仍保留） | 重建 link |
| `--uninstall` | **完全清除**：移除所有 link 和 CLAUDE.md，保留 `.connsys-jarvis/memory/` 和 `log/` | 清 link |
| `--reset` | **徹底重置**：比 `--uninstall` 更激進，額外刪除 `.connsys-jarvis/memory/`，僅保留 `log/` | 清一切 |
| `--list [--format json]` | 即時掃描列出所有 Expert（已安裝 + 可用），支援 `--format json` 輸出 | 唯讀 |
| `--query <expert-name> [--format json]` | 即時掃描查詢指定 Expert 的 metadata；支援部分名稱匹配；支援 `--format json` | 唯讀 |
| `--doctor` | 診斷 symlink 健康、環境版本（Python/uv/uvx）| 唯讀 |

> 每次 `--init`、`--add`、`--remove` 後，setup.py 自動印出提示：
> ```
> ✅ 安裝完成。請執行：source .connsys-jarvis/.env
> ```

### 5.2 setup.py 的 Symlink 建立邏輯

setup.py 讀取 `expert.json` 的 `dependencies` + `internal`，依序在 workspace `.claude/` 建立 symlinks：

```
安裝 wifi-bora-memory-slim-expert 時的 .claude/ 結果：

.claude/
├── skills/
│   ├── framework-expert-discovery-knowhow → $CONNSYS_JARVIS_PATH/framework/framework-base-expert/skills/framework-expert-discovery-knowhow/
│   ├── framework-memory-tool              → $CONNSYS_JARVIS_PATH/framework/framework-base-expert/skills/framework-memory-tool/
│   ├── wifi-bora-arch-knowhow             → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-base-expert/skills/wifi-bora-arch-knowhow/
│   ├── wifi-bora-memory-knowhow           → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-base-expert/skills/wifi-bora-memory-knowhow/
│   ├── wifi-bora-linkerscript-knowhow     → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-base-expert/skills/wifi-bora-linkerscript-knowhow/
│   ├── wifi-bora-symbolmap-knowhow        → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-base-expert/skills/wifi-bora-symbolmap-knowhow/
│   ├── wifi-bora-build-flow               → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-base-expert/skills/wifi-bora-build-flow/
│   ├── sys-bora-gerrit-commit-flow        → $CONNSYS_JARVIS_PATH/sys-bora/sys-bora-preflight-expert/skills/sys-bora-gerrit-commit-flow/
│   ├── sys-bora-preflight-flow            → $CONNSYS_JARVIS_PATH/sys-bora/sys-bora-preflight-expert/skills/sys-bora-preflight-flow/
│   ├── wifi-bora-memslim-flow             → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-memory-slim-expert/skills/wifi-bora-memslim-flow/
│   ├── wifi-bora-ast-tool                 → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-memory-slim-expert/skills/wifi-bora-ast-tool/
│   ├── wifi-bora-lsp-tool                 → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-memory-slim-expert/skills/wifi-bora-lsp-tool/
│   └── wifi-bora-wut-tool                 → $CONNSYS_JARVIS_PATH/wifi-bora/wifi-bora-memory-slim-expert/skills/wifi-bora-wut-tool/
│
├── hooks/                                  ← 來自 framework-base-expert（Shell 優先）
│   ├── session-start.sh          → $CONNSYS_JARVIS_PATH/framework/framework-base-expert/hooks/session-start.sh
│   ├── session-end.sh            → .../framework-base-expert/hooks/session-end.sh
│   ├── pre-compact.sh            → .../framework-base-expert/hooks/pre-compact.sh
│   ├── mid-session-checkpoint.sh → .../framework-base-expert/hooks/mid-session-checkpoint.sh
│   ├── shared-utils.sh           → .../framework-base-expert/hooks/shared-utils.sh
│   └── memory-helper.py          → .../framework-base-expert/hooks/memory-helper.py
│
├── commands/
│   └── framework-experts-tool    → .../framework-base-expert/commands/framework-experts-tool/
```

> 本地二區記憶（shared / working）存放於 `.connsys-jarvis/memory/`，詳見 §5.3 與 §10.3。

### 5.3 .connsys-jarvis/ 隱藏資料夾設計

setup.py 在 workspace 根目錄建立隱藏資料夾 `.connsys-jarvis/`，存放所有 runtime 資料：

```
workspace/
├── .connsys-jarvis/              ← setup.py 建立（.gitignore 排除）
│   ├── .env                      ← 環境變數（source .connsys-jarvis/.env）
│   ├── .installed-experts.json   ← 已安裝 Expert 狀態清單（JSON，schema 詳見 §5.3.1）
│   ├── log/                      ← setup.py 執行 debug log
│   │   └── 2026-03-26/
│   │       └── install.log
│   └── memory/                   ← 本地記憶（session-stop 時上傳 connsys-memory repo）
│       └── {expert-name}/
│           └── 2026-03-26/
│               └── 10:30-wifi-bora-memory-slim-expert-memory.md
└── CLAUDE.md                     ← setup.py 生成（@include expert.md 等）
```

> Windows 不支援 symlink 時，setup.py 自動降級為 copy 模式（功能相同，但更新 expert 後需重新安裝）。

### 5.3.1 .installed-experts.json Schema

setup.py 在每次 `--init` / `--add` / `--remove` 後更新此檔，記錄完整安裝狀態供後續操作使用。

**欄位說明**：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `schema_version` | string | 格式版本，目前為 `"1.0"` |
| `updated_at` | string（ISO 8601） | 最後一次 setup.py 更新的時間 |
| `experts[].name` | string | 對應 expert.json 的 `name` |
| `experts[].domain` | string | 對應 expert.json 的 `domain` |
| `experts[].version` | string | 對應 expert.json 的 `version` |
| `experts[].path` | string | 相對 connsys-jarvis 根目錄的 expert.json 路徑 |
| `experts[].installed_at` | string（ISO 8601） | 此 Expert 被安裝的時間 |
| `experts[].install_order` | integer | 安裝順序（越大越新）；CLAUDE.md identity 以最大值的 Expert 為主 |
| `experts[].is_identity` | boolean | 是否以此 Expert 的 soul/rules/duties 作為 CLAUDE.md 主 identity（`install_order` 最大者為 `true`） |
| `experts[].declared_symlinks` | object | 此 Expert 宣告的所有 symlink（dependencies + internal，套用 exclude_symlink 後）；`--remove` 時採全清再重建策略，無需維護 reference count |

**全清再重建策略**：`--remove expert-A` 時，先清除 `.claude/` 下所有 symlinks，再依剩餘 Expert（按 install_order 遞增）逐一重建，確保 symlink 集合與已安裝清單完全同步。與 `--add` 策略一致，邏輯簡單可靠。

**完整範例**（已安裝 framework-base-expert + wifi-bora-memory-slim-expert）：

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-03-26T10:30:00Z",
  "experts": [
    {
      "name": "framework-base-expert",
      "domain": "framework",
      "version": "1.0.0",
      "path": "framework/framework-base-expert/expert.json",
      "installed_at": "2026-03-26T09:00:00Z",
      "install_order": 1,
      "is_identity": false,
      "declared_symlinks": {
        "skills":   ["framework-expert-discovery-knowhow", "framework-memory-tool"],
        "hooks":    ["session-start.sh", "session-end.sh", "pre-compact.sh", "mid-session-checkpoint.sh", "shared-utils.sh"],
        "agents":   [],
        "commands": ["framework-experts-tool"]
      }
    },
    {
      "name": "wifi-bora-memory-slim-expert",
      "domain": "wifi-bora",
      "version": "1.0.0",
      "path": "wifi-bora/wifi-bora-memory-slim-expert/expert.json",
      "installed_at": "2026-03-26T10:30:00Z",
      "install_order": 2,
      "is_identity": true,
      "declared_symlinks": {
        "skills": [
          "framework-expert-discovery-knowhow", "framework-memory-tool",
          "wifi-bora-arch-knowhow", "wifi-bora-memory-knowhow", "wifi-bora-linkerscript-knowhow",
          "wifi-bora-symbolmap-knowhow", "wifi-bora-build-flow",
          "sys-bora-gerrit-commit-flow", "sys-bora-preflight-flow",
          "wifi-bora-memslim-flow", "wifi-bora-ast-tool", "wifi-bora-lsp-tool", "wifi-bora-wut-tool"
        ],
        "hooks":    ["session-start.sh", "session-end.sh", "pre-compact.sh", "mid-session-checkpoint.sh"],
        "agents":   [],
        "commands": ["framework-experts-tool"]
      }
    }
  ]
}
```

**移除範例**：若執行 `--remove wifi-bora-memory-slim-expert`：
- `wifi-bora-memslim-flow`, `wifi-bora-ast-tool`, `wifi-bora-lsp-tool`, `wifi-bora-wut-tool` → 只有 memory-slim 聲明 → count=0 → **刪除**
- `framework-expert-discovery-knowhow`, `session-start.sh` 等 → framework-base-expert 仍聲明 → count=1 → **保留**

### 5.4 .env 環境變數設計

setup.py 執行後，將環境變數寫入 `.connsys-jarvis/.env`：

```bash
# .connsys-jarvis/.env（由 setup.py 生成，勿手動編輯）
export CONNSYS_JARVIS_PATH="/Users/john.doe/workspace/connsys-jarvis"
export CONNSYS_JARVIS_WORKSPACE_ROOT_PATH="/Users/john.doe/workspace"
export CONNSYS_JARVIS_CODE_SPACE_PATH="/Users/john.doe/workspace/codespace"
export CONNSYS_JARVIS_MEMORY_PATH="/Users/john.doe/workspace/.connsys-jarvis/memory"
export CONNSYS_JARVIS_EMPLOYEE_ID="john.doe"
export CONNSYS_JARVIS_ACTIVE_EXPERT="wifi-bora-memory-slim-expert"
```

使用者每次執行 setup.py 後需手動 source：
```bash
source .connsys-jarvis/.env
```

> setup.py 執行結束後自動印出提示，避免忘記 source。

### 5.5 多 Expert 安裝設計（--init / --add）

**設計原則**：`--init` 是全新安裝（清除重建）；`--add` 是疊加安裝（保留既有，加入新的）。每次安裝完成後，`.claude/` 中的所有 link 皆對應到目前已安裝的 Expert 集合。

**依賴解析流程**：

```
setup.py --add wifi-bora/wifi-bora-memory-slim-expert/expert.json

Step 1：讀取 expert.json，取得 dependencies 與 internal

  dependencies 的每個元素對四個 key（skills/hooks/agents/commands）各自套用選擇規則：
    "all"            → 繼承該 Expert 資料夾下的全部項目
    ["name1","name2"] → 只繼承指定清單
    省略 key          → 不繼承（空集合）

  範例（wifi-bora-memory-slim-expert 的 dependencies）：
    framework-base-expert  → skills: [指定 3 個], hooks: "all", commands: [指定 2 個]
    wifi-bora-base-expert  → skills: [指定 5 個]
    sys-bora-preflight     → skills: [指定 2 個]

  internal 下的項目永遠全部建立（不需選擇規則）：
    wifi-bora-memory-slim-expert → skills/: 3 個私有 skill

Step 2：遞迴讀取所有依賴的 expert.json，合併所有要建立的 link
  framework-base-expert          → skills（指定清單）、hooks（all）、commands（指定清單）
  wifi-bora-base-expert          → skills（指定清單）
  sys-bora-preflight-expert      → skills（指定清單）
  wifi-bora-memory-slim-expert   → skills/*（internal，全部）

Step 3：套用 exclude_symlink 過濾不需要的 link
  wifi-bora-memory-slim-expert.json 中若設定 patterns: [".*-lsp-.*"]
  則不建立符合 pattern 的 skill link

Step 4：清除舊 link，重建 .claude/skills/、hooks/、agents/、commands/

Step 5：更新 .connsys-jarvis/.installed-experts.json
Step 6：重新生成 workspace/CLAUDE.md（詳見 §9）
Step 7：更新 .connsys-jarvis/.env
Step 8：印出變更清單（新增/移除/保留）+ source 提示
```

**推薦安裝流程**：

```bash
# 全新安裝（第一次）
uv run ./connsys-jarvis/scripts/setup.py --init framework/framework-base-expert/expert.json
source .connsys-jarvis/.env

# 加入 wifi-bora-memory-slim-expert（自動帶入 dependencies）
uv run ./connsys-jarvis/scripts/setup.py --add wifi-bora/wifi-bora-memory-slim-expert/expert.json
source .connsys-jarvis/.env

# 查看安裝結果
uv run ./connsys-jarvis/scripts/setup.py --list
```

### 5.6 --doctor 診斷輸出

```
$ uv run ./connsys-jarvis/scripts/setup.py --doctor

=== Connsys Jarvis Doctor ===

已安裝的 Experts：
  [1] framework-base-expert          (framework/framework-base-expert)
  [2] wifi-bora-memory-slim-expert   (wifi-bora/wifi-bora-memory-slim-expert)

Symlinks 健康狀態：
  Skills：
    ✅ framework-expert-discovery-knowhow  → .../framework-base-expert/skills/...              OK
    ✅ wifi-bora-memslim-flow              → .../wifi-bora-memory-slim-expert/skills/...        OK
    ❌ wifi-bora-lsp-tool                  → .../wifi-bora-memory-slim-expert/skills/...        DANGLING
  Hooks：
    ✅ session-start.sh  → .../framework-base-expert/hooks/session-start.sh  OK
    ✅ session-end.sh    → .../framework-base-expert/hooks/session-end.sh    OK
  Agents：
    ✅ log-analyzer.md   → .../framework-base-expert/agents/log-analyzer.md  OK

環境檢查：
  Python (system): 3.11.8  ✅ (>= 3.11)
  uv:              0.4.2   ✅ 已安裝
  uvx:             0.4.2   ✅ 已安裝

建議修復：
  → 刪除 dangling link: .claude/skills/wifi-bora-lsp-tool
    python3 -c "import os; os.remove('.claude/skills/wifi-bora-lsp-tool')"
```

### 5.7 scripts/ 目錄設計與測試架構

`connsys-jarvis/scripts/` 目錄集中管理所有可執行腳本，測試採**三層金字塔**設計：

```
scripts/
├── setup.py                ← 主安裝程式（Python stdlib，PEP 723）
└── test/
    ├── conftest.py         ← 共用 fixtures（workspace / legacy_workspace / …）
    ├── test_setup.py       ← 舊版 monolith（向後相容）
    ├── unit/               ← Layer 1：單元測試（純函式邏輯）
    │   └── test_unit.py
    ├── integration/        ← Layer 2：整合測試（cmd_* 多模組協作）
    │   ├── conftest.py     ← build_mini_jarvis helper
    │   └── test_integration.py
    └── e2e/                ← Layer 3：端對端測試（subprocess CLI 黑箱）
        └── test_e2e.py
```

**三層設計原則**：

| 層級 | 測試對象 | 特性 | 數量 |
|------|----------|------|------|
| Unit | 單一 function（`apply_exclude_patterns` 等）| 不碰磁碟，ms 級 | 38 |
| Integration | cmd_* 函式協作（真實 tmp_path）| 驗證 symlink/JSON 實際建立 | 73 |
| E2E | CLI 黑箱（`subprocess.run`）| 驗證 stdout + 檔案系統 | 18 |

**執行測試**：

```bash
# 全部三層（從 connsys-jarvis 目錄）
uvx pytest scripts/tests/ -v                       # 239 tests

# 只跑某一層（快速反饋）
uvx pytest scripts/tests/unit/ -v                  # 38 tests, ~0.1s
uvx pytest scripts/tests/integration/ -v           # 73 tests, ~0.4s
uvx pytest scripts/tests/e2e/ -v                   # 18 tests, ~1.3s

# 舊版（向後相容）
uvx pytest scripts/tests/test_setup.py -v          # 110 tests
```

**測試覆蓋範圍**：

| 層 | 測試類 | 函式 / 場景 | 測試數 |
|----|--------|------------|--------|
| Unit | `TestDetectScenario` | `detect_scenario()` | 3 |
| Unit | `TestGetCodespacePath` | `get_codespace_path()` | 2 |
| Unit | `TestResolveItems` | `resolve_items()` | 6 |
| Unit | `TestApplyExcludePatterns` | `apply_exclude_patterns()` | 4 |
| Unit | `TestGenerateClaudeMdSingle` | `generate_claude_md()` 單 Expert | 4 |
| Unit | `TestGenerateClaudeMdMulti` | `generate_claude_md()` 多 Expert + Base Experts 區段 | 12 |
| Unit | `TestWriteEnvFile` | `write_env_file()` + 變數驗證 | 10 |
| Unit | `TestInstalledExpertsSchema` | `.installed-experts.json` 讀寫 | 3 |
| Integration | `TestIntegrationInit` | `cmd_init()` + memory 保留 | 9 |
| Integration | `TestIntegrationAdd` | `cmd_add()` 冪等疊加 | 5 |
| Integration | `TestIntegrationRemove` | `cmd_remove()` 全清再重建 | 5 |
| Integration | `TestIntegrationUninstall` | `cmd_uninstall()` 保留 memory | 3 |
| Integration | `TestIntegrationReset` | `cmd_reset()` 刪除 memory | 5 |
| Integration | `TestInitMemoryPreservation` | `--init` memory 保留效果 | 1 |
| Integration | `TestScanAvailableExperts` | `scan_available_experts()` | 6 |
| Integration | `TestCmdQuery` | `cmd_query()` | 8 |
| Integration | `TestCmdListUpdated` | `cmd_list()` | 6 |
| Integration | `TestDoctorSystemInfo/EnvVars/Symlink/ClaudeMd/ExpertStructure` | `cmd_doctor()` A~F 區段 | 24 |
| E2E | `TestE2EInit` | `--init` CLI 完整流程 | 6 |
| E2E | `TestE2EAdd` | `--add` CLI 流程 | 2 |
| E2E | `TestE2EUninstall` | `--uninstall` CLI 流程 | 3 |
| E2E | `TestE2EReset` | `--reset` CLI 流程 | 4 |
| E2E | `TestE2EList` | `--list --format json` | 2 |
| E2E | `TestE2EMultiExpertWorkflow` | init→add→list→remove 完整流程 | 1 |

---

## 6. 環境變數設計

setup.py 執行後將環境變數寫入 `workspace/.connsys-jarvis/.env`，使用者手動 source 後即可在 skill、hook、agent 中使用。
所有變數統一使用 `CONNSYS_JARVIS_` 前綴：

```bash
export CONNSYS_JARVIS_PATH="..."                              # connsys-jarvis repo 路徑
export CONNSYS_JARVIS_WORKSPACE_ROOT_PATH="$(pwd)"           # workspace 根目錄（.claude/ 所在）
export CONNSYS_JARVIS_CODE_SPACE_PATH="..."                  # 程式碼路徑（agent-first: codespace/；legacy: workspace root）
export CONNSYS_JARVIS_MEMORY_PATH="$(pwd)/connsys-memory"     # connsys-memory repo 路徑
export CONNSYS_JARVIS_EMPLOYEE_ID="swchen.tw"                # 員工工號（OS 登入帳號，即 home 目錄名稱）
```

| 變數 | Agent First | Legacy |
|------|-------------|--------|
| `CONNSYS_JARVIS_WORKSPACE_ROOT_PATH` | `~/workspace` | `~/workspace` |
| `CONNSYS_JARVIS_CODE_SPACE_PATH` | `~/workspace/codespace` | `~/workspace` |

---

## 7. SKILL.md 格式

```yaml
---
name: wifi-bora-memslim-flow
description: "分析 Wi-Fi Bora ROM/RAM footprint 並協助精簡記憶體用量的主流程"
version: "1.0.0"
domain: wifi-bora
type: flow
scope: wifi-bora-memory-slim-expert
tags: [internal]
---

# WiFi Bora Memory Slim Flow

## 步驟 1：分析 Symbol Map
使用 wifi-bora-symbolmap-knowhow 讀取 .map 檔並找出最大佔用符號。

## 步驟 2：AST 靜態分析
呼叫 wifi-bora-ast-tool 找出未使用 / 可精簡的函式。

## 步驟 3：驗證與報告
參考 wifi-bora-lsp-tool 和 wifi-bora-wut-tool 輸出結果，生成 slim 報告。
```

**Type 欄位值**：`flow` / `knowhow` / `tool`

---

## 8. Framework Expert/Skill 建立工具設計

`framework-base-expert` 內建兩個輔助建立 flow，供工程師快速產出符合規範的 Expert / Skill 內容。兩個 flow 均作為 `framework-base-expert` 的 internal skill，安裝 framework-base-expert 後即可使用。

---

### 8.1 `framework-skill-create-flow`

**目的**：互動式引導工程師建立一個完整、符合規範的 Skill，避免遺漏必要章節或放錯目錄。

**觸發詞**（範例）：
- 「幫我建立一個 skill」
- 「create skill」
- 「我要新增一個 \<名稱> 的 skill」

**互動流程**：

```
1. 詢問 Skill 基本資訊
   - Skill 名稱（{domain}-{name}-{type}，提示命名規則）
   - 所屬 Expert（internal 還是 base expert）
   - Type：flow / knowhow / tool（解釋三種類型差異）
   - 一句話描述（寫入 YAML description）

2. 詢問 Skill 內容
   - 觸發條件：什麼情況下 AI 應呼叫此 Skill？
   - How it works：主要執行步驟（逐步引導）
   - 有哪些相依 Skill？
   - 有什麼邊界或限制？
   - 請給一個使用範例

3. 產生輸出
   ├── {skill-dir}/SKILL.md         ← 含完整 frontmatter + 各章節
   ├── {skill-dir}/README.md        ← 歷史、目的、開發說明
   └── {skill-dir}/test/

```

**SKILL.md 章節標準**（framework-skill-create-flow 確保全部存在）：

| 章節 | 說明 | 必要 |
|------|------|------|
| YAML frontmatter | name / description / version / domain / type / scope / tags | ✅ |
| `## Trigger` | 觸發詞與觸發條件 | ✅ |
| `## How it works` | 執行步驟（numbered list）| ✅ |
| `## 範例` | 至少 1 個完整範例 | ✅ |
| `## 相依 Skills` | 列出依賴的其他 Skill | 有則加 |
| `## 限制與邊界` | 什麼情況不適用 | ✅ |

---

### 8.2 `framework-expert-create-flow`

**目的**：互動式引導工程師建立一個新 Expert 的完整資料夾結構，把使用者的自然語言描述轉化為品質好、符合 connsys-jarvis 規範的四個核心文件（soul / rules / duties / expert.md）與 expert.json。

**觸發詞**（範例）：
- 「幫我建立一個新的 expert」
- 「create expert」
- 「我要新增一個 \<名稱> 的 expert」

**互動流程**：

```
1. 詢問 Expert 基本定義
   - Expert 名稱（{domain}-{name}-expert，提示命名規則）
   - 所屬 Domain
   - 一句話描述（這個 Expert 的核心任務）

2. 引導 soul.md 內容（可選）
   - 這個 Expert 的身分認同是什麼？（Identity）
   - 它的核心價值和原則？（Values & Principles）
   - 溝通風格？主動/被動？正式/非正式？
   - 有什麼獨特的個性特質？（Personality）

3. 產生 expert.md（可選）
   - 自動根據以上輸入生成 Overview、Key Behaviors、Tools Available
   - Skills 表格（初始空白，待工程師填入）
   - Hooks 表格（預設繼承 framework-base-expert 的 hooks）

4. 產生 expert.json 初稿
   - 自動填入 name / version / description / domain
   - dependencies 預設包含 framework-base-expert
   - internal skills/hooks 空白，待工程師填入

5. 建立資料夾骨架
   {domain}/{expert-name}/
   ├── .claude-plugin/plugin.json  ← 由 create_plugin_from_expert.py 生成
   ├── expert.json    ← 初稿（必要）
   ├── soul.md        ← 可選
   ├── expert.md      ← 可選
   ├── skills/        ← 主要實作機制（待建立 Skill）
   ├── commands/      ← 扁平 .md（slash commands，可選）
   ├── hooks/         ← hooks.json + scripts/（可選）
   ├── rules/         ← 扁平 .md（可選）
   ├── agents/        ← 扁平 .md（可選）
   ├── scripts/       ← 輔助腳本（可選）
   └── README.md      ← 初稿（含安裝指令）
```

**核心文件標準章節**（framework-expert-create-flow 確保全部存在）：

| 文件 | 必要章節 | 必要性 |
|------|---------|-------|
| `expert.json` | name, domain, version, dependencies, internal | **必要** |
| `soul.md` | `## Identity` / `## Values & Principles` / `## Communication Style` / `## Personality` | 可選 |
| `expert.md` | `## Overview` / `## Key Behaviors` / `## Tools Available` / `## Skills` 表格 / `## Hooks` 表格 | 可選 |

---

### 8.3 兩個 Flow 的定位差異

| | `framework-skill-create-flow` | `framework-expert-create-flow` |
|--|-------------------------------|-------------------------------|
| **建立對象** | 單一 Skill（SKILL.md + test）| 整個 Expert 資料夾（expert.json + 可選 soul.md/expert.md）|
| **互動深度** | 中（著重 trigger / steps / 範例）| 中（著重身分定義與 Skill 規劃）|
| **輸出物** | SKILL.md / README.md | expert.json / 可選 soul.md + expert.md / 資料夾骨架 |
| **後續動作** | 加入 expert.json 的 internal.skills 清單 | 執行 `setup.py --init` 安裝 |

---

## 9. Script 實作語言優先策略

適用範圍：所有 Hook（`hooks/`）與 Skill 內的可執行腳本（`test/`、helper scripts）。

### 8.1 語言優先順序

```
優先順序：Shell（預設）→ Python（複雜邏輯）→ JS（OpenClaw 遷移備用）

判斷原則：
  ① 能用 Shell 解決的，就用 Shell
     - 適合：git 操作、檔案讀寫、環境變數、簡單字串處理、基本功能驗證
     - 優點：所有開發環境普遍存在，無需額外 runtime，韌體工程師熟悉

  ② Shell 難以維護時，改用 Python
     - 適合：JSON/YAML 解析、複雜字串處理、API 呼叫、跨平台邏輯、unit test
     - 優點：韌體團隊的第二語言，函式庫豐富（GitPython、requests、pyyaml）
     - 慣例：Shell hook 以 subprocess 呼叫 Python helper（同名 .py 檔）

  ③ JS 為最後考慮，保留作為 OpenClaw 遷移路徑
     - 適合：Phase 2 OpenClaw 遷移時，TypeScript 重寫的過渡期
     - 原則：Phase 1 不主動新增 JS hooks
```

### 8.2 檔案命名慣例

| 情況 | 命名 | 範例 |
|------|------|------|
| 純 Shell hook | `{name}.sh` | `session-start.sh` |
| Shell + Python helper | `{name}.sh` + `{name}-helper.py` | `session-end.sh` + `session-end-helper.py` |
| 複雜邏輯獨立為 Python | `{name}.py`（由 Shell wrapper 呼叫）| `compress-memory.py` |
| Skill pytest | `test_{name}.py` | Python unit test，放 `test/` 下 |

### 8.3 Python 規範：PEP 723

所有 Hook helper 與 Skill 內的 Python 腳本，**強制採用 PEP 723 Inline Script Metadata**。

> **stdlib 優先原則**：儘量使用 Python 標準內建 library（`os`、`pathlib`、`json`、`subprocess` 等），減少 `dependencies` 欄位的外部套件，讓使用者可直接 `uv run` 一鍵執行，無需等待大量套件安裝。

參考：[PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/)

#### 標準模板

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6.0",
#   "requests>=2.31",
# ]
# ///

import sys
# 依賴在頂端 metadata 宣告後正常 import

def main() -> None:
    pass

if __name__ == "__main__":
    main()
```

| 好處 | 說明 |
|------|------|
| **零 venv 管理** | 不需 `requirements.txt`、不需建 venv，依賴宣告在腳本本身 |
| **直接執行** | `uv run script.py` 自動安裝依賴並執行 |
| **自帶文件** | 查看腳本即知依賴版本，降低環境不一致問題 |
| **CI 友善** | CI 環境只需安裝 `uv`，不需管理每個 skill 的 venv |

#### 執行方式

| 方式 | 指令 | 說明 |
|------|------|------|
| **推薦：uv run** | `uv run script.py` | 自動讀取 inline metadata，安裝依賴後執行 |
| 已有環境 | `python3 script.py` | 依賴已安裝時可直接執行 |
| pytest | `pytest test/` | 執行 `test/` 下所有 `test_*.py` |

> 安裝 `uv`：`curl -LsSf https://astral.sh/uv/install.sh | sh`

### 8.4 Skill pytest 範例（test_xxx.py）

```python
# test/test_wifi_bora_memslim_flow.py
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=8.0",
# ]
# ///
"""wifi-bora-memslim-flow skill 的 unit test"""

import json
from pathlib import Path
import pytest


@pytest.fixture
def test_data():
    data_file = Path(__file__).parent / "test-data.json"
    return json.loads(data_file.read_text())


def test_build_command_format(test_data):
    """驗證 build 指令格式正確"""
    cmd = test_data["build_cmd"]
    assert "make" in cmd
    assert "-j" in cmd


def test_output_dir_path():
    """驗證 build 輸出目錄路徑格式"""
    path = f"$CONNSYS_JARVIS_CODE_SPACE_PATH/fw/bora/build/out"
    assert "build/out" in path
```

### 8.5 Hook Python Helper 範例（含 PEP 723）

更新後的 `memory-helper.py`（由 `session-end.sh` 呼叫）：

```python
# memory-helper.py
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""connsys-memory 複雜操作 helper
由 Shell hooks 呼叫，處理 YAML frontmatter 解析、token 計算等 Shell 難以完成的邏輯。
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    # Future: add memory helper commands here
```

---

## 9. CLAUDE.md 生成機制

setup.py 在 `$CONNSYS_JARVIS_WORKSPACE_ROOT_PATH`（workspace 根目錄）生成 `CLAUDE.md`，並建立 `AGENTS.md → CLAUDE.md` symlink（支援 Open Code、Gemini 等）。

### 9.1 CLAUDE.md v3.0 格式

v3.0 不再 `@include` soul.md / expert.md，改為對每個已安裝 Expert 輸出 using-knowhow skill 指示：

```markdown
<!-- connsys-jarvis CLAUDE.md — Auto-generated by setup.py v3.0
     Experts: wifi-bora-memory-slim-expert, framework-base-expert, wifi-bora-base-expert
     Generated: 2026-04-26T... -->

# Connsys Experts

## Expert Guidelines

MUST use the skill wifi-bora-memory-slim-expert-using-knowhow for expert guidelines and methodology, if the skill exists.
MUST use the skill framework-base-expert-using-knowhow for expert guidelines and methodology, if the skill exists.
MUST use the skill wifi-bora-base-expert-using-knowhow for expert guidelines and methodology, if the skill exists.

@CLAUDE.local.md
```

> 指導原則（原 soul.md + expert.md 內容）改由各 expert 的 `{expert-name}-using-knowhow` skill 提供。詳見 §2.8「using-knowhow Skill 模式」。

### 9.2 AGENTS.md Symlink

setup.py 在寫完 CLAUDE.md 後，建立 `AGENTS.md → CLAUDE.md` 相對路徑 symlink，讓其他 AI coding 工具透過 AGENTS.md 讀取相同 context。卸載（`--uninstall` / `--reset`）時一併清理。

### 9.3 v2.0 → v3.0 遷移

v3.0 不相容 v2.0 格式（不再有 `@include` soul.md / expert.md 行）。升級後需重新執行 `--init` 或 `--add` 重新生成 CLAUDE.md。

### 9.4 CLAUDE.local.md（個人客製化）

`CLAUDE.local.md` 放在 workspace 根目錄，不納入 `connsys-jarvis` repo，供同仁個人客製化：

```markdown
# 個人客製化（CLAUDE.local.md）
- 我偏好用 Python 3.11 做腳本
- 測試環境：172.16.0.x 系列
```

> setup.py 在 CLAUDE.md 末尾加入 `@CLAUDE.local.md`，若檔案不存在 Claude Code 會忽略。

---

## 10. 記憶系統設計

### 10.1 四個 Hook 存檔點（Shell 優先實作，project level）

```
存檔可靠性：
1. pre-compact.sh      ← 最可靠（context 壓縮前）
2. mid-checkpoint.sh   ← 每 20 訊息
3. session-end.sh      ← best-effort
4. session-start.sh    ← 載入（不存檔）

複雜邏輯（JSON 解析、記憶壓縮）：呼叫 memory-helper.py
```

Hooks 設定於 project level（`workspace/.claude/settings.json`），由 `setup.py` 在 `--init` / `--add` 時寫入。

### 10.2 connsys-memory Repo 結構（後臺遠端）

```
connsys-memory/ (git)
├── README.md
└── employees/
    ├── john.doe/
    │   ├── sessions/
    │   │   └── 2026-03-23.md
    │   └── summary.md
    └── jane.smith/
```

> **多人衝突**：每人有自己的 `employees/{id}/` 資料夾，帳號不同所以 push 不衝突。同一人多視窗使用時，以 Claude Session ID 為 run-id（詳見 §10.3）確保唯一性。

### 10.3 本地二區記憶（Local Two-Zone Memory）

本地記憶存放於 `workspace/.connsys-jarvis/memory/`，分為兩個區域：

| 用途 | 路徑 | 說明 |
|------|------|------|
| 跨 Expert 共用 | `.connsys-jarvis/memory/shared/` | project.md, conventions.md 等 |
| 當前 Expert | `.connsys-jarvis/memory/working/{expert-name}/{date}/` | 飛行中狀態，切換時歸檔 |

**session-stop hook** 負責將 `.connsys-jarvis/memory/` 上傳到遠端 `connsys-memory` repo（git push 同一 repo）。

```
workspace/.connsys-jarvis/memory/
├── shared/                         ← Zone 1：跨 Expert 共用知識（持久）
│   ├── project.md                  ← 專案背景、目標、重要決策
│   ├── conventions.md              ← 跨 Expert 約定的規範
│   └── decisions.md                ← 重要架構決策記錄（ADR）
│
└── working/                        ← Zone 2：當前 Expert 的飛行中狀態（切換時清除）
    └── wifi-bora-memory-slim-expert/          ← 以 expert 名稱為子資料夾
        └── working.md              ← in-flight 工作日誌、當前進度、未完成項目
```

**兩個區域的設計原則**：

| 區域 | 生命週期 | 讀寫規則 | 負責 Hook |
|------|---------|---------|---------|
| `shared/` | 長期持久，不因 Expert 切換而清除 | 所有 Expert 可讀寫 | 任何 hook 皆可更新 |
| `working/{expert}/` | 隨 Expert 生命週期，切換時清除（或歸檔） | 僅當前 Expert 寫入，其他可讀 | session-end、pre-compact |

### 10.4 本地記憶 vs connsys-memory 的分工

```
┌─────────────────────────────────────────────────────────────────┐
│               記憶系統雙層架構                                    │
│                                                                 │
│  本地（workspace/.connsys-jarvis/memory/）                              │
│  ─────────────────────────────                                  │
│  即時讀寫，Expert 直接存取                                        │
│  • shared/     ← 跨 Expert 知識（環境設定、慣例）                  │
│  • working/    ← 飛行中狀態（進度、筆記、暫存）                    │
│                                                                 │
│  ↓ session-end / pre-compact hook 定期同步                       │
│                                                                 │
│  遠端（connsys-memory/ git repo）                                 │
│  ─────────────────────────────                                  │
│  後臺收集，跨裝置同步，供 framework-learn-expert 分析              │
│  • sessions/   ← 每次 session 的完整摘要                         │
│  • summary.md  ← 滾動式個人知識總覽                              │
└─────────────────────────────────────────────────────────────────┘
```

**為什麼需要本地二區，不直接用 connsys-memory**：
- 本地二區是 Expert 的「工作桌」：即時讀寫，不需 git push，不依賴網路
- connsys-memory 是「歸檔書架」：異步同步，跨裝置，管理者可查閱
- Zone 2（working）設計為「揮發性」：Expert 切換時可以清除，避免記憶污染

### 10.5 週期性記憶收集設計（Lightweight Periodic Collection）

目標：讓記憶能累積供未來 `framework-learn-expert` 分析，同時**不造成即時使用的負擔**。

```
觸發時機（不干擾主流程）：
  1. session-end hook：每次 session 結束時，同步 memory/ 到 connsys-memory
  2. mid-session-checkpoint hook：每 20 訊息更新 working/，不 push 到遠端
  3. pre-compact hook：context 壓縮前存快照到 working/，是最可靠的存檔點
  4. 排程同步（未來）：透過 cron 或 CI，每日彙整 working/ + shared/ 到 connsys-memory

輕量化設計原則：
  • 非同步：git push 在背景執行，不阻塞 Expert 的 Think/Plan/Act
  • 增量：只 push 變動的部分，不全量覆寫
  • 限制大小：session summary < 5000 tokens
  • 失敗容忍：push 失敗不影響 Expert 繼續工作，下次重試
```

---

## 11. Expert 狀態機設計

每個 Expert 在 `expert.json` 的 `transitions` 中宣告狀態轉移規則。當 Expert 完成工作後，根據結果事件觸發不同的下一步：

```
expert.json（以 wifi-bora-memory-slim-expert 為例）：

"transitions": {
  "BUILD_SUCCESS": "wifi-bora-cr-robot-expert",   ← 成功 → 自動切換到 CI/CD 專家
  "BUILD_FAILED":  null                  ← 失敗 → null 表示需人工介入
}
```

**事件來源**：
- 事件名稱在 `expert.json` 的 `transitions` 中定義（大寫慣例，如 BUILD_SUCCESS）
- Stage 1 由人工確認後執行 `--init`；Stage 2 未來可自動觸發

### 11.1 session-start.sh：共用記憶注入

`session-start.sh` 是 Expert 啟動的第一件事，負責將共用記憶注入新的 Expert session。
採用 **Shell 優先**策略：基本邏輯用 Shell，複雜的 JSON 解析或記憶操作呼叫 `memory-helper.py`。

```bash
#!/usr/bin/env bash
# session-start.sh
# Claude Code hook：session 開始時載入共用記憶

MEMORY_DIR="${CONNSYS_JARVIS_WORKSPACE_ROOT_PATH}/.connsys-jarvis/memory"
SHARED_DIR="${MEMORY_DIR}/shared"

# 1. 載入共用記憶
if [[ -f "${SHARED_DIR}/project.md" ]]; then
  echo "## 專案共用知識"
  cat "${SHARED_DIR}/project.md"
  echo ""
fi

if [[ -f "${SHARED_DIR}/conventions.md" ]]; then
  echo "## 跨 Expert 約定"
  cat "${SHARED_DIR}/conventions.md"
  echo ""
fi
```

> `memory-helper.py` 完整實作（含 PEP 723 inline metadata）見 **§8.4**。

---

## 13. 安全與權限設計

| 考量 | 設計 |
|------|------|
| **客戶資料隔離** | 客戶相關資料（manifest、設定、credentials）存於**獨立 git repo**，不放入 `connsys-jarvis` |
| **無客戶名稱** | `connsys-jarvis` 所有 SKILL.md / CLAUDE.md 內容均不含客戶名稱 |
| **權限管理** | 依 domain 分資料夾，方便對不同 domain 設定不同的 git access control |
| **安全掃描** | domain 層級的清楚分隔，方便對 wifi / bt / system 各自執行 secret scan |
| **命名不衝突** | Layer 1-5 的命名規則確保全域唯一（domain prefix + type postfix）|
| **External 隔離** | 外部工具放 `{domain}-external-expert/`，與 internal 清楚分開，方便掃描外部依賴 |

---

## 13.5 已知限制

| 限制 | 說明 | 對應 Future Work |
|------|------|-----------------|
| **Skill 版本向後相容** | SKILL.md `version` 欄位僅供顯示，Skill 升版後的相容性未定義；breaking change 需人工審查 | 無（列為設計邊界） |
| **Local Memory 無 GC** | `memory/shared/`、`memory/working/` 無自動清理機制，長期使用後可能無限增長 | FW-04 |
| **registry.json 已移除** | registry.json 已廢棄並移除（v3.3），由 setup.py 即時掃描取代；expert-discovery skill 可呼叫 `--list --format json` 取得結構化資料 | FW-05 |
| **connsys-memory 同帳號多開衝突** | 同一人同時開多個 Claude 視窗時，若 Session ID 無法取得，timestamp fallback 仍有極小衝突機率 | FR-06-9（優先用 Session ID）|
| **Windows symlink** | Windows 不支援 symlink，setup.py 自動降級為 copy 模式；copy 模式下更新 expert 內容後需重新執行 setup.py | 無（自動處理）|
| **Human in the Loop 無超時機制** | 目前 HitL 確認行為由 prompt 驅動，無自動超時或「不再詢問」機制 | Phase 2 設計 |

---

## 14. 遷移路線

### 14.1 三階段遷移

| 機制 | Phase 1：Claude Code | Phase 2：OpenClaw | Phase 3：ADK/SDK |
|------|---------------------|------------------|-----------------|
| 安裝 | `install.sh` symlink | `install.sh --target openclaw` | `AgentDefinition` 自動 |
| Hooks | **Shell（優先）+ Python（複雜邏輯）** | TypeScript `handler.ts`（此階段重寫）| `PostToolUse callback` |
| Skills | SKILL.md | SKILL.md + `metadata.openclaw` | `system_prompt` 注入 |
| Commands | COMMAND.md（相容層，Phase 1 不新增）| user-invocable Skill | SDK tool 定義 |
| Memory | Markdown + Git | MEMORY.md + LanceDB | JSON output |
| Human in Loop | 手動確認 | Hook 觸發確認 | 風險評分自動決定 |

### 14.2 Skill 與 Command 的邊界設計

**原則**：**Skill 是主要實作單位，`commands/` 資料夾為 Claude plugin format 的相容層**。Phase 1 新開發的 Expert 不需建立獨立的 command 資料夾。

| 情況 | 做法 |
|------|------|
| 需要自動觸發的知識/流程 | 使用 Skill，不加 `disable-model-invocation` |
| 需要像 Command 一樣由使用者主動呼叫 | 使用 Skill，在 SKILL.md frontmatter 加 `disable-model-invocation: true` |
| 已有 `commands/` 資料夾的 Expert | 保留（相容），不主動遷移，Phase 2 統一處理 |
| 新建 Expert | 只用 Skill，不建 commands/ |

**`disable-model-invocation` 範例**：

```yaml
---
name: framework-experts-tool
type: tool
disable-model-invocation: true   # 使用者主動輸入 /experts 才觸發，不自動觸發
description: 列出所有可用的 Expert
---
```

### 14.3 plugin.json 生成規則

`create_plugin_from_expert.py` 從 `expert.json` 生成 `.claude-plugin/plugin.json`，需遵守以下規則：

| 規則 | 說明 |
|------|------|
| **不使用 `..` 路徑** | plugin.json 內所有路徑必須為相對於 plugin 根目錄的正向路徑，不允許 `../` 向上跳層 |
| **跨 Expert 引用用 dependencies** | 若需要其他 Expert 的資源，透過 `expert.json` 的 `dependencies` 機制，不在 plugin.json 中直接引用其他 Expert 的檔案 |
| **`${CLAUDE_PLUGIN_ROOT}` 環境變數** | Hook 腳本中可使用 `${CLAUDE_PLUGIN_ROOT}` 取得 plugin 根目錄的絕對路徑，避免 hardcode 路徑或使用 `..` |

### 14.4 Plugin Skill 命名與短名呼叫

Plugin 安裝後，所有 skill/command/agent 的內部全名為 `pluginName:skillDirName`（如 `framework-base-expert:framework-skill-create-flow`）。但使用者只需輸入短名（如 `/framework-skill-create-flow`）即可呼叫。

**原理**：Claude Code 的 `findCommand()` 比對邏輯（`src/commands.ts`）除了精確比對 `_.name`（全名），也會比對 `getCommandName()`，而 `getCommandName()` 回傳 `userFacingName()` = SKILL.md frontmatter 的 `name` 欄位。

因此：
- SKILL.md / command.md / agent.md 的 frontmatter **務必包含 `name` 欄位**
- `name` 欄位的值就是使用者輸入的短名
- 使用 `setup.py` 安裝（symlink）和 Plugin 安裝（marketplace）在使用體驗上沒有差異

### 14.5 SKILL.md 遷移格式

加入 `metadata.openclaw` 區塊即可，內容不需修改：

```yaml
---
name: wifi-bora-memslim-flow
# ... 現有欄位不變 ...
metadata:
  openclaw:
    emoji: "🔨"
    always: false
    user-invocable: false
---
```

---

## 15. 名詞定義

| 術語 | 定義 |
|------|------|
| Domain | 技術領域分類（framework / wifi / bt / system） |
| `{domain}-base-expert` | 存放該 domain 共用 skill/hook 的容器，install.sh 無作用 |
| `framework-base-expert` | 存放跨所有 domain 共用 skill/hook 的容器 |
| `flow` skill | 有清楚步驟的工作流程 SOP |
| `knowhow` skill | 基礎知識與背景資料 |
| `tool` skill | 外部工具的操作方法 |
| Layer 1-5 | connsys-jarvis 的五層資料夾命名規則 |
| `CONNSYS_JARVIS_WORKSPACE_ROOT_PATH` | workspace 根目錄，`.claude/` 所在 |
| `CONNSYS_JARVIS_CODE_SPACE_PATH` | 程式碼路徑（兩個場景值不同） |
| Human in the Loop | 對高風險操作暫停等待人類確認的機制 |
| Local Two-Zone Memory | 本地二區記憶：`shared/`（持久共用）+ `working/`（飛行中） |
| `memory/shared/` | 跨 Expert 共用知識，Expert 切換後持續存在 |
| `memory/working/{expert}/` | 當前 Expert 的飛行中工作狀態，切換時清除 |
| transitions | `expert.json` 中定義的事件→下一個 Expert 狀態機轉移規則 |
| connsys-memory | 後臺遠端 git repo，供跨裝置同步與 framework-learn-expert 分析 |

---

## 16. Future Work

### 16.1 Security：Expert 安全審計機制

**動機**：

AI Agent 生態系統的成長速度遠超其安全工具：
- 2026 年 1 月，一個主要 Agent 技能市場的 **12% 技能為惡意**（2,857 個社區技能中有 341 個惡意）
- 一個 **CVSS 8.8** 的 CVE 暴露了 17,500+ 個面向網路的實例
- Moltbook 漏洞跨 770,000 個 Agent 洩露了 **150 萬個 API token**

**現況問題**：

同仁在安裝社區技能（external-expert）、連接 MCP 伺服器、配置 hooks 時，沒有任何自動化方式來審計設定的安全性。

**目標**：

建立 `framework-security-expert`，提供以下能力：

```
framework/
└── framework-security-expert/
    ├── skills/
    │   ├── framework-security-audit-flow/     ← 審計流程 SOP
    │   │   └── SKILL.md
    │   ├── framework-skill-scan-tool/         ← 掃描已安裝 skills 的安全性
    │   │   └── SKILL.md
    │   ├── framework-hook-scan-tool/          ← 掃描 hooks 是否有惡意行為
    │   │   └── SKILL.md
    │   └── framework-supply-chain-knowhow/    ← 供應鏈攻擊知識
    │       └── SKILL.md
    ├── hooks/
    │   └── pre-install-check.sh               ← 安裝前自動掃描
    ├── commands/
    │   └── framework-security-audit-tool/     ← /security-audit 指令
    │       └── COMMAND.md
    ├── test/
    └── report/
```

**設計方向**（參考 AgentShield）：

| 功能 | 說明 |
|------|------|
| 靜態分析 | 掃描 SKILL.md / COMMAND.md 是否有 prompt injection、資料外洩指令 |
| Hook 掃描 | 檢查 `.sh` / `.py` hooks 是否有可疑的網路呼叫、檔案讀寫 |
| External 審計 | 安裝 external-expert 前，比對已知惡意 skill fingerprint |
| Pre-install hook | 在 install.sh 執行前觸發安全檢查，阻止高風險安裝 |
| 報告產生 | 自動更新 `report/execution-report.md`，記錄安全掃描結果 |

**參考實作**：[AgentShield](https://github.com/affaan-m/agentshield)

---

### 16.2 Memory + Learn：自我檢討的 Expert

**動機**：

目前 Expert 的 knowledge（SKILL.md）是靜態的，由人工撰寫和維護。未來希望 Expert 能**從使用記憶中自動學習**，持續改善自己的 skills。

**設計方向**：

```
使用記憶（connsys-memory/employees/{id}/sessions/）
    ↓ framework-learn-expert 分析
找出 pattern（常見錯誤、成功解法、反覆遇到的問題）
    ↓
自動產生或更新 SKILL.md（howknow / flow 類型）
    ↓
framework-skill-create-expert 驗證格式
    ↓
PR 給人工 review → merge → 所有人受益
```

**三個層次的記憶演進**：

| 層次 | 機制 | 實作 |
|------|------|------|
| **短期**：session 記憶 | session-end hook 自動儲存 | 已實作（claude-memory-engine 模式）|
| **中期**：跨 session 學習 | framework-learn-expert 定期分析 sessions/ | 未來工作 |
| **長期**：知識固化 | 分析結果→新增/更新 SKILL.md→PR | 未來工作 |

**`framework-learn-expert` 強化方向**：

```
framework/framework-learn-expert/skills/
├── framework-learn-flow/           ← 分析記憶→找 pattern 的 SOP
│   └── SKILL.md
├── framework-feedback-knowhow/     ← 如何從錯誤記錄中萃取知識
│   └── SKILL.md
└── framework-skill-improve-flow/   ← 自動產生 skill PR 的流程（新增）
    └── SKILL.md
```

**目標效果**：Expert 不只是靜態知識庫，而是能透過累積的使用資料**持續自我強化**的系統，實現真正的 `Think → Plan → Act → Learn` 循環。

**參考實作**：[claude-mem](https://github.com/thedotmack/claude-mem)

---

### 16.3 Skill README 開發說明範本

**現況**：Skill README.md 的開發說明章節目前無標準格式，各 Skill 寫法不一致。

**目標**：提供統一的 Skill README 範本，包含：如何新增 case、測試覆蓋率目標、已知問題記錄方式，由 `framework-skill-create-expert` 在建立新 Skill 時自動生成。

**參考資料**：

- [Skill Best Practices（Claude 官方）](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [SKILL.md 範例（Anthropic skills repo）](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)

> 待真實使用後再補齊完整範本與步驟說明。

---

### 16.4 Local Memory GC 機制

**現況**：`memory/shared/`、`memory/working/` 無自動清理，長期使用後可能無限增長。

**設計方向**：

| 區域 | GC 策略 |
|------|---------|
| `memory/shared/` | 超過閾值（如 100KB）時，由 session-end hook 呼叫 Python helper 自動摘要壓縮 |
| `memory/working/` | Expert 切換時清除（已有設計），無需額外 GC |

> 待累積足夠使用資料後再行實作。

---

### 16.5 Expert 探索機制（registry.json 已移除）

**v3.3 更新**：`registry.json` 已廢棄並移除。所有 Expert 探索功能改由 `setup.py` 即時掃描實作：

- `setup.py --list [--format json]`：掃描 `connsys-jarvis/*/*/expert.json`，回傳所有 Expert（已安裝 + 可用）
- `setup.py --query <name> [--format json]`：讀取指定 Expert 的完整 metadata

`framework-expert-discovery-knowhow` skill 可直接 `subprocess` 呼叫上述指令取得 JSON 資料。

---

## 17. 參考資料

### 核心概念

| 資料 | 說明 |
|------|------|
| [Harness Engineering（Martin Fowler Blog）](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) | 本系統架構的核心啟發：為 AI 打造自動化治理體系 |
| [AgentShield](https://github.com/affaan-m/agentshield) | Agent 生態系統安全審計參考實作 |
| [claude-memory-engine](https://github.com/HelloRuru/claude-memory-engine) | 8-step 學習循環記憶引擎，hooks 設計參考 |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 輕量記憶系統，memory → learn 機制參考 |

### 技術文件

| 資料 | 說明 |
|------|------|
| [Claude Plugin 文件](https://code.claude.com/docs/en/plugins) | Expert 資料夾結構參考（skills/hooks/commands 格式）|
| [Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | Skill 資料夾設計參考 |

### 延伸閱讀（個人知識庫，連結待更新）

| 資料 | 說明 |
|------|------|
| [Lessons from Building Claude Code — How We Use Skills](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/AI/2026-03-17-LESSONS-FROM-BUILDING-CLAUDE-CODE-HOW-WE-USE-SKILLS.md) | 實戰經驗：Claude Code 中 Skills 的使用心得 |
| [5 Agent Skill Design Patterns Every ADK Developer Should Know](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/AI/2026-03-18-5-AGENT-SKILL-DESIGN-PATTERNS-EVERY-ADK-DEVELOPER-SHOULD-KNOW.md) | ADK 開發者必知的 5 種 Skill 設計模式 |
| [Claude-mem Code Analysis](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/CodeAnalysis/2025-08-31-CLAUDE-MEM-CODE-ANALYSIS.md) | claude-mem 原始碼深度分析 |

---

## 18. Expert 總覽表

### 表一：Domain / Expert / Internal Skills

| Domain | Expert | Internal Skills（該 Expert 自己擁有的 skills） |
|--------|--------|-----------------------------------------------|
| framework | framework-base-expert | framework-expert-discovery-knowhow, framework-memory-tool, framework-skill-create-flow, framework-expert-create-flow |
| sys-bora | sys-bora-base-expert | sys-bora-gerrit-tool, sys-bora-repo-tool, sys-bora-build-knowhow, sys-bora-arch-knowhow, sys-bora-ld-knowhow, sys-bora-config-knowhow, sys-bora-manifest-build-knowhow |
| sys-bora | sys-bora-preflight-expert | sys-bora-preflight-flow, sys-bora-preflight-result-tool, sys-bora-gerrit-commit-flow, sys-bora-ci-label-knowhow |
| wifi-bora | wifi-bora-base-expert | wifi-bora-protocol-knowhow, wifi-bora-arch-knowhow, wifi-bora-coderule-knowhow, wifi-bora-build-flow, wifi-bora-rompatch-knowhow, wifi-bora-linkerscript-knowhow, wifi-bora-symbolmap-knowhow, wifi-bora-memory-knowhow, wifi-bora-sds-knowhow |
| wifi-bora | wifi-bora-memory-slim-expert | wifi-bora-memslim-flow, wifi-bora-ast-tool, wifi-bora-lsp-tool, wifi-bora-wut-tool |
| wifi-bora | wifi-bora-cr-robot-expert | wifi-bora-debug-sop-flow, wifi-bora-coredump-knowhow, wifi-bora-ast-tool, wifi-bora-lsp-tool, wifi-bora-wut-tool, wifi-bora-risk-report-flow |
| wifi-bora | wifi-bora-coverity-expert | wifi-bora-coverity-flow, wifi-bora-coverity-cr-tool, wifi-bora-risk-report-flow |
| bt-bora | bt-bora-base-expert | bt-bora-protocol-knowhow, bt-bora-arch-knowhow, bt-bora-coderule-knowhow, bt-bora-build-flow, bt-bora-sds-knowhow |
| bt-bora | bt-bora-security-expert | bt-bora-security-rule-knowhow, bt-bora-security-analysis-flow, bt-bora-ast-tool, bt-bora-lsp-tool |
| lrwpan-bora | lrwpan-bora-base-expert | lrwpan-bora-protocol-knowhow, lrwpan-bora-arch-knowhow, lrwpan-bora-build-flow, lrwpan-bora-sds-knowhow |
| wifi-gen4m | wifi-gen4m-base-expert | wifi-gen4m-protocol-knowhow, wifi-gen4m-arch-knowhow, wifi-gen4m-build-flow, wifi-gen4m-sds-knowhow |
| wifi-logan | wifi-logan-base-expert | wifi-logan-protocol-knowhow, wifi-logan-arch-knowhow, wifi-logan-build-flow, wifi-logan-sds-knowhow |

> 備註：`*-ast-tool`、`*-lsp-tool`、`*-wut-tool` 跨多個 wifi-bora expert 共用；若後續多個 expert 均有相同工具，可考慮移至 wifi-bora-base-expert。

---

### 表二：Expert 相依圖

| Expert | 依賴的 Expert |
|--------|--------------|
| framework-base-expert | —（無依賴，作為根節點） |
| sys-bora-base-expert | —（無依賴） |
| sys-bora-preflight-expert | sys-bora-base-expert |
| wifi-bora-base-expert | —（無依賴） |
| wifi-bora-memory-slim-expert | framework-base-expert, wifi-bora-base-expert, sys-bora-preflight-expert |
| wifi-bora-cr-robot-expert | framework-base-expert, wifi-bora-base-expert, sys-bora-preflight-expert |
| wifi-bora-coverity-expert | framework-base-expert, wifi-bora-base-expert, sys-bora-preflight-expert |
| bt-bora-base-expert | —（無依賴） |
| bt-bora-security-expert | framework-base-expert, bt-bora-base-expert, sys-bora-preflight-expert |
| lrwpan-bora-base-expert | —（無依賴） |
| wifi-gen4m-base-expert | —（無依賴） |
| wifi-logan-base-expert | —（無依賴） |

> 說明：`sys-bora-preflight-expert` 是跨 domain 的共用 preflight 工具，被 wifi-bora、bt-bora、lrwpan-bora 的功能型 expert 所依賴。`framework-base-expert` 提供 memory、expert discovery 等基礎設施，所有功能型 expert 均應依賴。
