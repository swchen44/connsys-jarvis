---
name: wifi-bora-ast-tool
description: "使用 AST（抽象語法樹）分析 WiFi Bora C 原始碼，找出未被呼叫的函式和未使用的全域變數"
version: "1.0.0"
---

# WiFi Bora AST Tool

## 用途

透過 AST（Abstract Syntax Tree）靜態分析，找出 WiFi Bora 韌體中未被任何程式碼呼叫的函式和變數，協助識別可安全移除的 dead code。

## 工具需求

```bash
# 需要 clang 和 clang-tools
clang --version     # >= 14.x
clang-tidy --version

# 或使用 bear 生成 compilation database
bear --version
```

## 使用方法

### Step 1：生成 Compilation Database

```bash
# 使用 bear 追蹤 make 的編譯指令
bear -- make -j$(nproc)
# 產出 compile_commands.json
```

### Step 2：分析 Dead Functions

```bash
# 使用 clang-check 分析
python3 connsys-jarvis/tools/ast-analyzer.py \
    --compile-db compile_commands.json \
    --find-dead-functions \
    --output report/dead-functions.json

# 結果範例：
# [
#   {"name": "wifi_legacy_scan_handler", "file": "mlme/scan.c", "line": 342, "size_bytes": 256},
#   {"name": "mac_ba_debug_dump", "file": "mac/ba_rx.c", "line": 890, "size_bytes": 512}
# ]
```

### Step 3：驗證 Dead Code

在移除任何函式前，使用 `wifi-bora-lsp-tool` 交叉確認是否有動態呼叫（function pointer）：

```bash
python3 connsys-jarvis/tools/lsp-checker.py \
    --symbol wifi_legacy_scan_handler \
    --check-function-pointers
```

### Step 4：生成精簡報告

```bash
python3 connsys-jarvis/tools/ast-analyzer.py \
    --compile-db compile_commands.json \
    --report-summary \
    --min-size 100 \
    --output report/slim-opportunities.md
```

## 分析限制

| 限制 | 說明 |
|------|------|
| Function pointers | 透過 function pointer 呼叫的函式可能被誤判為 dead code |
| Weak symbols | Weak symbol 的實際使用需額外確認 |
| 跨編譯單元 | 需要完整的 compile_commands.json，不能只分析單一檔案 |
| 條件編譯 | `#ifdef` 未啟用的路徑不在分析範圍 |

## 輸出格式

```json
{
  "analysis_date": "2026-03-26T10:00:00Z",
  "total_functions": 2847,
  "potentially_dead": 142,
  "confirmed_dead": 38,
  "dead_functions": [
    {
      "name": "wifi_legacy_scan_handler",
      "file": "mlme/scan.c",
      "line": 342,
      "size_bytes": 256,
      "confidence": "high",
      "reason": "no callers found, not exported"
    }
  ]
}
```

## 注意事項

- **確信度 high**：安全移除，無 function pointer 引用
- **確信度 medium**：需人工確認後移除
- **確信度 low**：謹慎處理，可能有動態呼叫
- 移除前，**必須**先 build 驗證
