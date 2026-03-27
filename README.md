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
python connsys-jarvis/setup.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json

# 載入環境變數
source .connsys-jarvis/.env
```

### 新增 Expert

```bash
python connsys-jarvis/setup.py --add sys-bora/experts/sys-bora-preflight-expert/expert.json
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

## 場景支援

- **Agent First**：workspace 根目錄有 `codespace/` 子目錄，AI 在獨立環境操作
- **Legacy**：workspace 根目錄有 `.repo` 目錄，傳統 Android repo 結構
