# /handoff — Expert 交接指令

## 指令說明

觸發 Expert 切換流程，生成結構化 hand-off 文件並傳遞上下文給接手的 Expert。

## 用法

```
/handoff
/handoff to <expert-name>
/handoff status
```

## 行為定義

### `/handoff`

互動式 hand-off 流程：

```
準備 Hand-off...

當前 Expert：wifi-bora-base-expert
請選擇接手的 Expert：
  1. wifi-bora-memory-slim-expert
  2. sys-bora-preflight-expert
  3. 輸入自訂 Expert 名稱

選擇（1-3）：
```

### `/handoff to <expert-name>`

直接指定接手 Expert：

```
生成 Hand-off 文件...

  From: wifi-bora-base-expert
  To:   wifi-bora-memory-slim-expert
  File: .connsys-jarvis/memory/handoffs/2026-03-26T10:30:00Z-wifi-bora-base-to-memory-slim.md

Hand-off 已完成。接手 Expert 將在下次 session 開始時自動讀取。
```

### `/handoff status`

查看待接收的 hand-off：

```
=== 待接收的 Hand-offs ===

[1] 2026-03-26T10:30:00Z - 來自 wifi-bora-base-expert
    任務：ROM footprint 分析
    狀態：IN_PROGRESS

是否立即讀取？(y/N)
```

## Hand-off 文件格式

詳見 `framework-handoff-flow` skill。

## 實作說明

1. 讀取當前對話上下文，萃取任務狀態
2. 生成 hand-off 文件到 `$CONNSYS_JARVIS_MEMORY_PATH/handoffs/`
3. 提示工程師後續切換步驟
4. （可選）自動更新 `CONNSYS_JARVIS_ACTIVE_EXPERT`
