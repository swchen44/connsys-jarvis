# Expected: Memory Slim Flow

## 預期分析輸出結構

### 1. 整體用量概覽
```
ROM Usage: XXX KB / YYY KB (ZZ%)
RAM Usage: XXX KB / YYY KB (ZZ%)
```

### 2. Section 分佈
| Section  | Size (KB) | Percentage |
|----------|-----------|-----------|
| .text    | ...       | ...       |
| .rodata  | ...       | ...       |
| .data    | ...       | ...       |
| .bss     | ...       | ...       |

### 3. Top 10 Symbols
列出佔用空間最大的 function/symbol，包含名稱和大小。

### 4. 優化建議
- 具體指出哪些 function 可以精簡
- 建議移除或合併的項目
- 預估節省的空間

## 關鍵驗證點
1. 必須涵蓋 ROM 和 RAM 兩方面
2. 數字需要有單位（bytes 或 KB）
3. 需提供可執行的優化建議（不只是列數字）
4. 應使用 memslim-flow skill 來執行分析
