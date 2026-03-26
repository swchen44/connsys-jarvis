---
name: framework-expert-discovery-knowhow
description: "列出所有可用 Expert 及其能力，協助工程師選擇合適的 Expert 處理當前任務"
version: "1.0.0"
domain: framework
type: knowhow
scope: framework-base-expert
tags: [framework, discovery, expert-selection]
---

# Framework Expert Discovery Knowhow

## 用途

此 skill 提供 Connsys Jarvis 中所有可用 Expert 的完整清單，協助工程師和 AI 快速找到適合當前任務的 Expert。

## 可用 Expert 一覽

### Framework Layer

| Expert | 功能 | 觸發關鍵字 |
|--------|------|-----------|
| `framework-base-expert` | 生態系管理、記憶管理、hand-off 協調 | （框架層，預設載入） |

### WiFi Bora Domain

| Expert | 功能 | 觸發關鍵字 |
|--------|------|-----------|
| `wifi-bora-base-expert` | WiFi Bora 協議、架構、build 流程 | WiFi, 802.11, Bora, firmware |
| `wifi-bora-memory-slim-expert` | ROM/RAM footprint 分析與精簡 | memory slim, ROM 優化, RAM 分析, footprint, 記憶體 |

### Sys Bora Domain

| Expert | 功能 | 觸發關鍵字 |
|--------|------|-----------|
| `sys-bora-base-expert` | SoC/OS/build system、manifest 下載 | repo sync, build system, manifest |
| `sys-bora-preflight-expert` | Gerrit commit、CI/CD、preflight 分析 | gerrit, preflight, CR, code review |

### 其他 Domain

| Expert | 功能 |
|--------|------|
| `bt-bora-base-expert` | Bluetooth Bora 基礎知識 |
| `lrwpan-bora-base-expert` | LR-WPAN (802.15.4/Zigbee/Thread) 知識 |
| `wifi-gen4m-base-expert` | WiFi Gen4M 基礎知識 |
| `wifi-logan-base-expert` | WiFi Logan 基礎知識 |

## Expert 選擇指南

1. **任務分析**：確認任務屬於哪個技術領域（WiFi/BT/LR-WPAN/SoC）
2. **場景確認**：是否有特定場景（memory optimization、preflight、build）
3. **Expert 匹配**：參考觸發關鍵字選擇最合適的 Expert
4. **依賴確認**：確認 Expert 的 dependencies 也已安裝

## 安裝新 Expert

```bash
# 查看可用 Expert
cat connsys-jarvis/registry.json

# 安裝 Expert
python connsys-jarvis/setup.py --add <domain>/experts/<expert-name>/expert.json
```

## 注意事項

- 多個 Expert 可同時安裝，但以最後安裝的 Expert 為主 identity
- 若不確定選哪個 Expert，優先選擇 base expert 後再依需求升級
- Expert 之間有依賴關係（`dependencies` 欄位），setup.py 會自動處理
