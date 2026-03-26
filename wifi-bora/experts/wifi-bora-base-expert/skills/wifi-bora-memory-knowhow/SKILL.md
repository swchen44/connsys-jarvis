---
name: wifi-bora-memory-knowhow
description: "WiFi Bora ROM/RAM 記憶體佈局基礎知識，包含 section 劃分、SRAM 管理與使用量分析方法"
version: "1.0.0"
domain: wifi-bora
type: knowhow
scope: wifi-bora-base-expert
tags: [wifi, bora, memory, ROM, RAM, SRAM, section]
---

# WiFi Bora Memory Knowhow

## 記憶體架構概覽

WiFi Bora SoC 的記憶體系統：

```
┌─────────────────────────────────────────┐
│  ROM (Flash)      read-only            │
│  ├── .text        ← 程式碼             │
│  ├── .rodata      ← 唯讀資料（常數）   │
│  └── .data (init) ← 初始化資料初值     │
├─────────────────────────────────────────┤
│  SRAM             read-write           │
│  ├── .data        ← 已初始化全域變數   │
│  ├── .bss         ← 未初始化全域變數   │
│  ├── heap         ← 動態記憶體         │
│  └── stack        ← Task stacks       │
├─────────────────────────────────────────┤
│  ITCM / DTCM      (若有)              │
│  ├── 時間關鍵程式碼（ITCM）            │
│  └── 時間關鍵資料（DTCM）             │
└─────────────────────────────────────────┘
```

## Section 說明

| Section | 位置 | 說明 |
|---------|------|------|
| `.text` | ROM | 函式程式碼 |
| `.rodata` | ROM | const 字串、lookup table |
| `.data` | ROM+RAM | 有初始值的全域變數（ROM 存初值，RAM 存執行值） |
| `.bss` | RAM | 無初始值的全域變數（BSS 意為 Block Started by Symbol） |
| `.heap` | RAM | malloc/free 使用的動態記憶體 |
| `.stack` | RAM | Call stack（每個 task 獨立） |
| `.noinit` | RAM | 不需初始化的 RAM（watchdog reset 後保留） |

## 記憶體用量分析

### 快速查看 section 大小

```bash
arm-none-eabi-size wifi_bora.elf
#    text    data     bss     dec     hex filename
#  512000    8192   65536  585728   8F000 wifi_bora.elf
```

| 欄位 | 意義 |
|------|------|
| text | ROM 使用量（.text + .rodata） |
| data | ROM+RAM（有初值的全域變數） |
| bss | RAM（無初值全域變數） |
| dec | text + data + bss 總計 |

### 詳細分析

```bash
# 查看各 section 詳細大小
arm-none-eabi-objdump -h wifi_bora.elf

# 查看最大的函式（ROM 分析）
arm-none-eabi-nm --size-sort --print-size wifi_bora.elf | tail -20

# 查看各 object file 貢獻
arm-none-eabi-size wifi_bora.elf -A
```

## 常見記憶體問題

### ROM 超限（Text 太大）

原因：
- 內嵌大型 lookup table 在 .text 中
- 未啟用 link-time optimization (LTO)
- 過多 inline 函式展開

解法：
- 將 lookup table 移到 .rodata
- 啟用 `-Os` 或 `-Oz` 優化
- 使用 `wifi-bora-memory-slim-expert` 進行系統分析

### RAM 超限（BSS/Data 太大）

原因：
- 過大的 task stack 配置
- 靜態分配過大的緩衝區
- 過多的全域快取

解法：
- 使用 `uxTaskGetStackHighWaterMark()` 分析實際 stack 使用量
- 將大型緩衝區改為動態分配（注意 fragmentation）
