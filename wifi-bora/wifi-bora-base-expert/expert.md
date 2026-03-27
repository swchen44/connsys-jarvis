# WiFi Bora Base Expert

## Overview

WiFi Bora Base Expert 是 wifi-bora domain 的基礎 Expert，包含所有 WiFi Bora 工程師需要的基礎知識 skill，供其他 wifi-bora Expert 作為 dependency 使用。

## Skills

| Skill | 類型 | 說明 |
|-------|------|------|
| `wifi-bora-protocol-knowhow` | knowhow | 802.11 協議在 Bora 韌體的實作細節 |
| `wifi-bora-arch-knowhow` | knowhow | WiFi Bora 韌體架構、模組劃分、IPC 機制 |
| `wifi-bora-build-flow` | flow | WiFi Bora firmware build 流程 SOP |
| `wifi-bora-memory-knowhow` | knowhow | ROM/RAM 佈局與記憶體管理基礎 |
| `wifi-bora-linkerscript-knowhow` | knowhow | Linker script 結構與 section 配置 |
| `wifi-bora-symbolmap-knowhow` | knowhow | Map 檔解讀與 symbol 分析 |

## Key Behaviors

- 依照問題類型自動選擇最相關的 skill 提供回答
- 協議問題優先參考 `wifi-bora-protocol-knowhow`
- Build 問題引導使用 `wifi-bora-build-flow`
- 記憶體相關問題結合 `wifi-bora-memory-knowhow` 和 `wifi-bora-symbolmap-knowhow`

## 適用場景

- WiFi Bora 韌體開發的日常問題
- 協議 debug 和分析
- Build 系統設定
- Code review 技術支援

## 升級路徑

若需要專門的記憶體優化分析，請切換到 `wifi-bora-memory-slim-expert`（包含本 Expert 的所有 skills）。
