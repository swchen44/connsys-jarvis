---
name: wifi-bora-linkerscript-knowhow
description: "WiFi Bora linker script 結構解析，包含 section 配置、MEMORY 定義、常見優化技巧"
version: "1.0.0"
domain: wifi-bora
type: knowhow
scope: wifi-bora-base-expert
tags: [wifi, bora, linker, linkerscript, ld, section, memory-layout]
---

# WiFi Bora Linker Script Knowhow

## Linker Script 基本結構

WiFi Bora 的 linker script（通常為 `wifi_bora.ld`）結構如下：

```ld
/* 記憶體區域定義 */
MEMORY {
    ROM  (rx)  : ORIGIN = 0x00000000, LENGTH = 512K
    RAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 256K
    ITCM (rx)  : ORIGIN = 0x00100000, LENGTH = 64K
    DTCM (rw)  : ORIGIN = 0x20080000, LENGTH = 32K
}

/* Section 輸出定義 */
SECTIONS {
    /* 程式碼放 ROM */
    .text : {
        *(.vectors)        /* 中斷向量表（必須最前面） */
        *(.text)           /* 一般函式 */
        *(.text.*)         /* 帶後綴的函式（如 .text.wifi_init） */
    } > ROM

    /* 唯讀資料放 ROM */
    .rodata : {
        *(.rodata)
        *(.rodata.*)
    } > ROM

    /* 有初始值的全域變數：初值在 ROM，執行時複製到 RAM */
    .data : {
        _data_start = .;
        *(.data)
        *(.data.*)
        _data_end = .;
    } > RAM AT > ROM   /* VMA=RAM, LMA=ROM */

    /* 無初始值的全域變數 */
    .bss : {
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        *(COMMON)
        _bss_end = .;
    } > RAM

    /* Task stacks（noinit，避免 BSS 初始化清零） */
    .noinit (NOLOAD) : {
        *(.noinit)
    } > RAM

    /* Heap */
    .heap : {
        _heap_start = .;
        . = . + HEAP_SIZE;
        _heap_end = .;
    } > RAM
}
```

## ITCM/DTCM 使用

將時間關鍵的函式放入 ITCM（Instruction Tightly Coupled Memory）可大幅降低 latency：

```c
/* 在 C 程式碼中標記放入 ITCM */
__attribute__((section(".itcm.text")))
void wifi_rx_irq_handler(void) {
    /* 時間關鍵的 RX 處理 */
}
```

Linker script 對應：
```ld
.itcm_text : {
    *(.itcm.text)
    *(.itcm.text.*)
} > ITCM
```

## 常見 Linker Script 優化

### 1. 合併小 Section

將散落的小函式合併，減少 padding：

```ld
.text : {
    /* 先放對齊需求大的 */
    . = ALIGN(64);
    *(.text.wifi_dma*)
    /* 再放一般函式 */
    *(.text)
    *(.text.*)
}
```

### 2. 使用 KEEP 避免 Dead Code Elimination

```ld
.vectors : {
    KEEP(*(.vectors))   /* 中斷向量表不能被 LTO 移除 */
} > ROM
```

### 3. 查看實際 Section 使用量

```bash
# 列出所有 section 及大小
arm-none-eabi-objdump -h wifi_bora.elf | grep -E "Idx|\.text|\.data|\.bss|\.rodata"

# 查看 LMA/VMA（AT 語法的結果）
arm-none-eabi-readelf -S wifi_bora.elf
```

## 重要符號

Linker script 中定義的符號供 startup code 使用：

| 符號 | 用途 |
|------|------|
| `_data_start`, `_data_end` | `.data` section 在 RAM 中的範圍 |
| `_data_load` | `.data` section 在 ROM 中的起始位址 |
| `_bss_start`, `_bss_end` | `.bss` section 範圍（startup 需清零） |
| `_heap_start`, `_heap_end` | heap 範圍（傳給 malloc） |
| `_stack_top` | Stack 頂端（MSP 初始值） |
