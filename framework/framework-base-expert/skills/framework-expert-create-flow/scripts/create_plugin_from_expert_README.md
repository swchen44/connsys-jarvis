# create_plugin_from_expert.py

將 connsys-jarvis 的 `expert.json` 轉換為 Claude Code `plugin.json`，實現 Expert = Plugin 的 1:1 映射。

## 快速開始

```bash
# 從 connsys-jarvis repo 根目錄執行
python scripts/create_plugin_from_expert/create_plugin_from_expert.py

# 預覽不寫入
python scripts/create_plugin_from_expert/create_plugin_from_expert.py --dry-run

# 驗證正確性（需要 claude CLI）
python scripts/create_plugin_from_expert/create_plugin_from_expert.py --doctor
```

## 產出檔案

| 檔案 | 位置 | 說明 |
|------|------|------|
| `plugin.json` | `{expert}/.claude-plugin/plugin.json` | 每個 Expert 的 Claude Code plugin manifest |
| `marketplace.json` | `.claude-plugin/marketplace.json` | repo 層級的 marketplace registry |

## 欄位映射

```
expert.json                    → plugin.json
─────────────────────────────────────────────
name                           → name
version                        → version
description                    → description
owner                          → author.name
triggers                       → keywords
internal.skills[]              → (auto-detected from skills/ directory)
dependencies[].expert          → dependencies[] + skills[] (additional paths)
```

## 設計理念

### 為什麼需要這個腳本？

connsys-jarvis 使用 `expert.json` 描述 Expert 的 metadata 和依賴關係，但 Claude Code Plugin 系統使用 `plugin.json`。此腳本橋接兩者。

### Skills 路徑解析

- Expert 自身的 `skills/` 目錄由 Claude Code **自動偵測**，不需要列在 plugin.json 中
- `plugin.json` 的 `skills` 欄位只列出**依賴 Expert 的 skills 目錄**（額外路徑）
- 所有路徑使用 `./` 開頭（plugin.json 規範要求）

### Marketplace 安裝

使用者可以透過 Git URL 安裝整個 marketplace：

```bash
claude plugin add --marketplace https://github.com/your-org/connsys-jarvis.git
```

或指定單一 plugin：

```bash
claude --plugin-dir ./framework/framework-base-expert
```

## CLI 參數

| 參數 | 說明 |
|------|------|
| `--doctor` | 驗證 plugin.json 與 expert.json 是否一致（需要 claude CLI） |
| `--dry-run` | 預覽產出但不寫入檔案 |
| `--verbose` | 開啟詳細 log |
| `--expert-dir PATH` | 指定掃描根目錄（預設：auto-detect repo root） |
| `--help` | 顯示使用說明 |

## 依賴

- Python 3.8+ (stdlib only, no pip dependencies)
- claude CLI (僅 `--doctor` 模式需要)
