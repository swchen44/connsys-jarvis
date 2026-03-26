# /experts — Expert 探索指令

## 指令說明

列出所有可用 Expert 及其能力，協助工程師選擇合適的 Expert 處理當前任務。

## 用法

```
/experts
/experts list
/experts info <expert-name>
/experts recommend <task-description>
```

## 行為定義

### `/experts` 或 `/experts list`

列出所有已安裝的 Expert：

```
=== 已安裝的 Experts ===

[1] framework-base-expert (framework)
    管理 connsys expert 生態系

[2] wifi-bora-memory-slim-expert (wifi-bora) ← 當前 Expert
    分析 Wi-Fi Bora ROM/RAM footprint

輸入 /experts info <name> 查看詳細能力
輸入 /experts recommend <任務描述> 獲取推薦
```

### `/experts info <expert-name>`

顯示特定 Expert 的詳細能力說明，包含：
- Skills 清單
- Hooks 清單
- 觸發關鍵字
- 適用場景

### `/experts recommend <task-description>`

根據任務描述推薦最合適的 Expert：

```
根據您的任務「分析 ROM 使用量並找出可精簡的 symbol」，推薦：

  wifi-bora-memory-slim-expert
  理由：此 Expert 專門處理 WiFi Bora 記憶體精簡任務

  相關 Skills：
  - wifi-bora-symbolmap-knowhow
  - wifi-bora-memslim-flow

是否要切換到此 Expert？
```

## 實作說明

此指令由 AI 根據 `registry.json` 和已安裝的 `expert.json` 動態生成回應。
讀取路徑：`$CONNSYS_JARVIS_PATH/registry.json`
