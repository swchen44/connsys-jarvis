---
name: wifi-bora-symbolmap-knowhow
description: "WiFi Bora map 檔（.map）解讀方法，找出 ROM/RAM 使用量最大的 symbol 和模組"
version: "1.0.0"
domain: wifi-bora
type: knowhow
scope: wifi-bora-base-expert
tags: [wifi, bora, map, symbol, nm, objdump, footprint, analysis]
---

# WiFi Bora Symbol Map Knowhow

## Map 檔概覽

`wifi_bora.map` 是 linker 產生的完整 symbol 位址和 section 分配記錄，是分析 ROM/RAM 用量的最重要工具。

## Map 檔結構

```
Archive member included to satisfy reference by file (symbol)

Allocating common symbols

Discarded input sections

Memory map

.text           0x00000000    0x8000
 *(.vectors)
 .vectors       0x00000000      0x40  startup.o
                0x00000000                __Vectors
 .text          0x00000040    0x1000  mac/edca.o
                0x00000040                mac_edca_init
                0x000000a0                mac_edca_enqueue
 ...
```

## 常用分析技巧

### 找出最大的函式（ROM 分析）

```bash
# 方法 1：使用 nm（最直觀）
arm-none-eabi-nm --size-sort --print-size --radix=d wifi_bora.elf \
    | grep " T " \
    | sort -k1 -rn \
    | head -30

# 方法 2：從 map 檔提取
grep -E "^\s+0x[0-9a-f]+\s+0x[0-9a-f]+" wifi_bora.map \
    | awk '{print $2, $3}' \
    | sort -k2 -rn \
    | head -30
```

### 找出各模組的 ROM 用量

```bash
# 按 object file 統計 .text 大小
arm-none-eabi-size wifi_bora.elf -A \
    | grep "\.text" \
    | sort -k2 -rn
```

### 找出最大的全域變數（RAM 分析）

```bash
# 找 .bss 和 .data 中的大型變數
arm-none-eabi-nm --size-sort --print-size --radix=d wifi_bora.elf \
    | grep -E " [bBdD] " \
    | sort -k1 -rn \
    | head -20
```

## Symbol 類型說明

| nm 輸出 | 說明 |
|---------|------|
| `T` / `t` | .text（程式碼，ROM） |
| `R` / `r` | .rodata（唯讀資料，ROM） |
| `D` / `d` | .data（有初值全域變數，ROM+RAM） |
| `B` / `b` | .bss（無初值全域變數，RAM） |
| `W` / `w` | Weak symbol |
| `U` | Undefined（外部 symbol） |

大寫 = global，小寫 = static/local

## 實際分析範例

### 分析前 10 大 ROM 消耗模組

```bash
# 產出格式：<size_bytes> <module_path>
arm-none-eabi-size -t wifi_bora.elf -A \
    | grep "\.text" \
    | awk '{print $2, $1}' \
    | sort -rn \
    | head -10
```

範例輸出：
```
45678 mac/ba_rx.o
38912 mlme/sta_mgmt.o
27345 mac/edca.o
...
```

### 找到可放入 ROM 的大型 BSS 變數

```bash
# 找到可以從 RAM 搬到 ROM 的常數（誤放在 .bss 的 const 陣列）
arm-none-eabi-nm --print-size wifi_bora.elf \
    | grep " [bB] " \
    | awk '{if ($2+0 > 1000) print $2, $4}'
```

## 與 wifi-bora-memory-slim-expert 的關係

此 skill 提供讀懂 map 檔的基礎知識。進行系統性記憶體精簡分析時，
請使用 `wifi-bora-memory-slim-expert`，它提供：
- 自動化 map 分析工具（`wifi-bora-memslim-flow`）
- AST 分析工具找出未使用程式碼（`wifi-bora-ast-tool`）
- LSP-based symbol 追蹤（`wifi-bora-lsp-tool`）
