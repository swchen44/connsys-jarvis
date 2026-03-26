---
name: wifi-bora-memslim-flow
description: "WiFi Bora 記憶體精簡端到端 SOP，從分析到驗證的完整流程"
version: "1.0.0"
domain: wifi-bora
type: flow
scope: wifi-bora-memory-slim-expert
tags: [wifi, bora, memory, slim, ROM, RAM, optimization, SOP]
---

# WiFi Bora Memory Slim Flow

## 流程概覽

```
Phase 1: 現況分析
  ↓
Phase 2: 機會識別
  ↓
Phase 3: 精簡執行（迭代）
  ↓
Phase 4: 驗證
  ↓
Phase 5: 提交
```

## Phase 1：現況分析

### 1.1 確認目標

```
問工程師：
- 目標節省量：ROM 減少多少 KB？RAM 減少多少 KB？
- 時間限制：何時需要完成？
- 功能限制：有哪些功能不能關閉？
```

### 1.2 取得基線數據

```bash
# Build 一個 baseline（確保 map 檔是最新的）
make -j$(nproc)

# 記錄基線大小
arm-none-eabi-size wifi_bora.elf
# 儲存到 memory/working/YYYY-MM-DD/baseline.txt
```

### 1.3 分析 Map 檔

使用 `wifi-bora-symbolmap-knowhow` 技術：

```bash
# Top 20 ROM consumers（函式）
arm-none-eabi-nm --size-sort --print-size --radix=d wifi_bora.elf \
    | grep " T " | sort -rn | head -20 \
    > memory/working/YYYY-MM-DD/top-rom-functions.txt

# Top 20 RAM consumers（全域變數）
arm-none-eabi-nm --size-sort --print-size --radix=d wifi_bora.elf \
    | grep -E " [bBdD] " | sort -rn | head -20 \
    > memory/working/YYYY-MM-DD/top-ram-vars.txt
```

## Phase 2：機會識別

### 2.1 Dead Code 分析

使用 `wifi-bora-ast-tool`：

```bash
# 找出未被呼叫的函式
uvx wifi-bora-ast-tool --find-dead-functions wifi_bora.elf

# 找出未使用的全域變數
uvx wifi-bora-ast-tool --find-dead-globals wifi_bora.elf
```

### 2.2 機會優先排序

| 優先級 | 類型 | 預估效益 | 風險 |
|--------|------|---------|------|
| P1 | Kconfig 關閉未使用功能 | 大（>10KB） | Low |
| P2 | 移除確認 dead code | 中（1-10KB） | Medium |
| P3 | 字串/table 搬到 ROM | 中（1-5KB） | Low |
| P4 | Stack 大小優化 | 小（<1KB） | Low |
| P5 | 演算法優化 | 不定 | High |

## Phase 3：精簡執行

### 3.1 Kconfig 優化（P1，最安全）

```bash
# 檢視可關閉的功能
make menuconfig
# 搜尋 CONFIG_WIFI_* 選項，確認未使用的功能模組
```

### 3.2 Dead Code 移除（P2）

```bash
# 每次移除後立即驗證 build
make -j$(nproc)
arm-none-eabi-size wifi_bora.elf
```

### 3.3 記錄每個步驟

```markdown
| 步驟 | 操作 | ROM Before | ROM After | 節省 |
|------|------|-----------|----------|------|
| 1 | 關閉 CONFIG_WIFI_P2P | 512000 | 498000 | 14000 |
```

## Phase 4：驗證

```bash
# Build 驗證
make -j$(nproc) && echo "Build OK"

# Functional test（如有自動化測試）
make test

# 確認 map 差異合理
diff baseline.map current.map | grep "^[<>]" | grep -E "\.(text|bss|data)"
```

## Phase 5：提交

完成驗證後，使用 `sys-bora-gerrit-commit-flow` 提交：

1. **確認工程師同意提交**（human-in-the-loop）
2. 生成 commit message（包含 before/after 數據）
3. 提交到 Gerrit，觸發 preflight

**注意**：`git push` 前**必須**詢問工程師確認。
