# Connsys Jarvis

Connsys Jarvis 是一個多 Expert AI 助理框架，為 ConnSys 工程師提供領域專屬的 AI 協作能力。

## 架構概覽

```
connsys-jarvis/
├── setup.py          ← 安裝程式（Python stdlib only）
├── registry.json       ← 所有 Expert 的全域清單
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

### 列出已安裝的 Experts

```bash
python connsys-jarvis/setup.py --list
```

### 健康檢查

```bash
python connsys-jarvis/setup.py --doctor
```

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

## 場景支援

- **Agent First**：workspace 根目錄有 `codespace/` 子目錄，AI 在獨立環境操作
- **Legacy**：workspace 根目錄有 `.repo` 目錄，傳統 Android repo 結構
