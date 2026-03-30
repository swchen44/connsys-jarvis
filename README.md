# Connsys Jarvis

Connsys Jarvis 是一個多 Expert AI 助理框架，為 ConnSys 工程師提供領域專屬的 AI 協作能力。

## 架構概覽

```
connsys-jarvis/
├── setup.py          ← 安裝程式（Python stdlib only）
├── framework/          ← 框架層 Expert（跨 domain 共用）
├── wifi-bora/          ← WiFi Bora domain Experts
├── sys-bora/           ← Sys Bora domain Experts
├── bt-bora/            ← Bluetooth Bora domain Experts
├── lrwpan-bora/        ← LR-WPAN Bora domain Experts
├── wifi-gen4m/         ← WiFi Gen4M domain Experts
└── wifi-logan/         ← WiFi Logan domain Experts
```

## 快速開始

### 初始化（安裝單一 Expert）

```bash
# 從 workspace 根目錄執行
python connsys-jarvis/setup.py --init wifi-bora/wifi-bora-memory-slim-expert/expert.json

# 載入環境變數
source .connsys-jarvis/.env
```

### 新增 Expert

```bash
python connsys-jarvis/setup.py --add sys-bora/sys-bora-preflight-expert/expert.json
```

### 移除 Expert

```bash
python connsys-jarvis/setup.py --remove sys-bora-preflight-expert
```

### 列出所有 Expert（已安裝 + 可用）

```bash
python connsys-jarvis/setup.py --list

# JSON 格式輸出（供 LLM 或 skill 呼叫）
python connsys-jarvis/setup.py --list --format json
```

> 不依賴 registry.json，每次即時掃描

### 查詢指定 Expert

```bash
python connsys-jarvis/setup.py --query framework-base-expert

# JSON 格式輸出
python connsys-jarvis/setup.py --query framework-base-expert --format json
```

### 健康診斷（--doctor）

```bash
python connsys-jarvis/setup.py --doctor
```

`--doctor` 執行 6 個診斷區段，只回報問題與修正建議，不自動修復：

| 區段 | 說明 |
|------|------|
| A. 系統資訊 | OS 版本、Python 版本、connsys-jarvis 版本 |
| B. 環境變數 | 6 個 `CONNSYS_JARVIS_*` 變數存在性與路徑合法性 |
| C. Symlink 完整性 | missing / orphan / dangling；已建 skill link 的 SKILL.md |
| D. CLAUDE.md | @include 與已安裝 Expert 比對、target 檔案存在性 |
| E. 環境工具 | uv / uvx 是否安裝 |
| F. Expert 結構 | 掃描 repo 中所有 expert folder：必要檔案、必要欄位、skill SKILL.md、orphan skill |

### 卸載

```bash
python connsys-jarvis/setup.py --uninstall
```

## Expert 結構

每個 Expert 包含：

| 檔案 | 說明 |
|------|------|
| `expert.json` | Expert 的 metadata 和依賴宣告 |
| `expert.md` | Expert 的能力說明（給 AI 讀） |
| `soul.md` | Expert 的身份與價值觀 |
| `rules.md` | Expert 的行為規範 |
| `duties.md` | Expert 的職責說明 |
| `skills/` | 技能知識庫 |
| `hooks/` | 生命週期 hook 腳本 |
| `commands/` | 自定義指令 |
| `agents/` | 子 agent 定義 |

### expert.json 必要欄位

| 欄位 | 說明 |
|------|------|
| `name` | Expert 的唯一識別名稱（kebab-case） |
| `domain` | 所屬 domain（例如 `framework`、`wifi-bora`）|
| `owner` | 負責維護的團隊（例如 `wifi-team`）|
| `internal.skills` | 此 Expert 自身提供的 skill 清單（可為空 `[]`）|

`--doctor` 的 F2 區段會驗證以上欄位是否齊全。

## 建立新 Expert

使用 `framework-expert-create-flow` skill 互動式引導建立。觸發方式：在對話中說「create expert」或「新增 expert」。

### 步驟概覽

| 步驟 | 說明 |
|------|------|
| Step 0 | 確認 domain、命名、owner、dependencies、is_base |
| Step 1 | 建立目錄骨架（expert.json、soul.md、rules.md、duties.md、expert.md、README.md） |
| Step 2 | 填寫 expert.json（含完整 schema） |
| Step 3 | 撰寫 soul.md — Expert 身份、價值觀、溝通風格 |
| Step 4 | 撰寫 rules.md — 必做 / 禁止 / 輸出規範 / 職責邊界 |
| Step 5 | 撰寫 duties.md — 主要職責、職責分界 |
| Step 6 | 撰寫 expert.md — 公開能力說明（每 session 被讀取） |
| Step 7 | 建立 skills/、hooks/、agents/、commands/ 內容 |
| Step 8 | 撰寫 README.md（台灣繁體中文） |
| Step 9 | 安裝 `setup.py --init` / `--add`，驗證 `--doctor` |
| Step 10 | 執行 A–F Checklist（26 項）確認完整性 |

### 命名規則

```
{domain}-{purpose}-expert
```

- Base expert：每個 domain 恰好一個，設 `is_base: true`，無 dependencies
- 目錄路徑：`connsys-jarvis/{domain}/{domain}-{purpose}-expert/`

### 常見 Tips

- **expert.json 是最高風險**：格式錯誤會讓 `setup.py` 無法解析，且無明確錯誤訊息。依 schema 逐欄填寫，完成後立即跑 `--doctor`
- **soul.md Identity 要精確**：一句話，不能模糊。AI 讀這份文件時會直接決定行為傾向
- **duties.md Segregation 明確**：把「這個 expert 不做什麼」寫清楚，避免多 expert 協作時職責重疊
- **不要跳過 Checklist**：26 項裡有幾項（如 `is_base` 和 `dependencies` 互斥）很容易忽略卻會造成安裝警告

---

## 建立新 Skill

使用 `framework-skill-create-flow` skill 互動式引導建立。觸發方式：在對話中說「create skill」或「新增 skill」。

### 步驟概覽

| 步驟 | 說明 |
|------|------|
| Step 0 | 確認 domain、skill 名稱（type: flow/knowhow/tool）、隸屬 expert |
| Step 1 | 撰寫 SKILL.md frontmatter（name、description、type、scope、tags） |
| Step 2 | 撰寫 SKILL.md 主體（觸發條件、SOP 步驟、輸出格式） |
| Step 3 | 建立目錄 `skills/{domain}-{name}-{type}/` + SKILL.md、README.md |
| Step 4 | 在 expert.json `internal.skills` 註冊 skill 名稱 |
| Step 5 | 跑 eval 驗證（對話測試 skill 是否如預期觸發與執行） |

### 命名規則

```
{domain}-{name}-{type}
```

類型說明：

| 類型 | 用途 |
|------|------|
| `flow` | 標準作業程序（SOP）、多步驟互動引導 |
| `knowhow` | 領域知識、架構參考、protocol 規範 |
| `tool` | 外部工具操作指南（git、CLI、API 等） |

### 常見 Tips

- **description 欄位決定觸發**：SKILL.md frontmatter 的 `description` 要含觸發關鍵字，Claude 靠這欄判斷何時載入此 skill
- **SKILL.md 全英文**：frontmatter 和主體都用英文，README.md 才用繁體中文
- **Scope 要填對**：`scope` 填隸屬的 expert name（如 `framework-base-expert`），否則 symlink 安裝對象錯誤
- **建完立刻在 expert.json 註冊**：`internal.skills` 沒加就不會被 `setup.py` 掃到，`--doctor` 會報 orphan skill
- **eval 要對話測試**：skill 是否被正確觸發，只能透過實際對話驗證，沒有自動化測試替代

---

## 場景支援

- **Agent First**：workspace 根目錄有 `codespace/` 子目錄，AI 在獨立環境操作
- **Legacy**：workspace 根目錄有 `.repo` 目錄，傳統 Android repo 結構

## 執行測試

### pytest 三層測試（推薦）

```bash
cd connsys-jarvis

# 全部三層（239 tests）
uvx pytest scripts/tests/ -v

# 只跑某一層（快速反饋）
uvx pytest scripts/tests/unit/ -v           # 38 tests, ~0.1s（純函式邏輯）
uvx pytest scripts/tests/integration/ -v   # 73 tests, ~0.4s（cmd_* 流程）
uvx pytest scripts/tests/e2e/ -v           # 18 tests, ~1.3s（CLI 黑箱）
```

詳細設計說明見 `scripts/tests/README.md`。

### bash 整合測試腳本（手動情境驗證）

```bash
# 從 workspace 根目錄執行（connsys-jarvis 需已存在或 symlink）
bash connsys-jarvis/scripts/tests/run_integration_tests.sh
```

輸出範例：
```
✅ TC-01-1 success message
✅ exists: /tmp/connsys-jarvis-test/codespace
...
🎉 All tests passed!
```

### 用 tmux 在背景執行

```bash
SESSION="connsys-jarvis"
tmux new-session -d -s "$SESSION" -x 200 -y 60
tmux send-keys -t "$SESSION" \
  "bash connsys-jarvis/scripts/tests/run_integration_tests.sh; tmux wait-for -S ${SESSION}-done" Enter
tmux wait-for "${SESSION}-done"
```

### 測試覆蓋範圍

| 測試 | 涵蓋 TC | 方式 |
|------|---------|------|
| `scripts/tests/unit/` | TC-U01~U08（38 tests）| pytest 純函式單元測試 |
| `scripts/tests/integration/` | TC-U09~U22（73 tests）| pytest cmd_* 整合測試 |
| `scripts/tests/e2e/` | TC-E01~E06（18 tests）| pytest subprocess E2E 測試 |
| `run_integration_tests.sh` | TC-01~08, TC-11, TC-13~16 | bash 手動整合驗證 |

詳細測試計畫見 `doc/test_plan.md`，測試結果見 `doc/test_report.md`。
