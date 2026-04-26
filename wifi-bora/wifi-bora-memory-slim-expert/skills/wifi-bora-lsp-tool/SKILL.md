---
name: wifi-bora-lsp-tool
description: "使用 LSP（Language Server Protocol）追蹤 WiFi Bora symbol 的所有引用，確認 dead code 分析結果"
version: "1.0.0"
---

# WiFi Bora LSP Tool

## 用途

使用 `clangd`（LLVM Language Server）的 `textDocument/references` 能力，精確找出 WiFi Bora 韌體中特定 symbol 的所有引用位置，包含 function pointer 引用，補足 AST 分析的盲點。

## 工具需求

```bash
# clangd（clang 的 language server）
clangd --version  # >= 14.x

# compile_commands.json（由 bear 生成）
ls compile_commands.json
```

## 使用方法

### Step 1：查詢 Symbol 的所有引用

```bash
# 使用 clangd LSP client 查詢
python3 connsys-jarvis/tools/lsp-checker.py \
    --symbol <symbol_name> \
    --file <file_path> \
    --line <line_number>

# 例：確認 wifi_legacy_scan_handler 是否有 function pointer 引用
python3 connsys-jarvis/tools/lsp-checker.py \
    --symbol wifi_legacy_scan_handler \
    --file mlme/scan.c \
    --line 342
```

### Step 2：批次確認 Dead Code 清單

```bash
# 從 ast-tool 的輸出批次確認
python3 connsys-jarvis/tools/lsp-checker.py \
    --batch report/dead-functions.json \
    --check-all-refs \
    --output report/confirmed-dead.json
```

### Step 3：解讀結果

```json
{
  "symbol": "wifi_legacy_scan_handler",
  "total_references": 0,
  "direct_calls": 0,
  "function_pointer_refs": 0,
  "macro_refs": 0,
  "verdict": "SAFE_TO_REMOVE",
  "details": []
}
```

```json
{
  "symbol": "mac_ba_debug_dump",
  "total_references": 2,
  "direct_calls": 0,
  "function_pointer_refs": 2,
  "macro_refs": 0,
  "verdict": "DO_NOT_REMOVE",
  "details": [
    {"file": "mac/debug.c", "line": 112, "context": "dbg_table[DBG_BA] = mac_ba_debug_dump;"}
  ]
}
```

## Verdict 說明

| Verdict | 說明 | 建議動作 |
|---------|------|---------|
| `SAFE_TO_REMOVE` | 零引用，包含 function pointer | 可安全移除 |
| `NEEDS_REVIEW` | 有引用但確信度低 | 人工 code review |
| `DO_NOT_REMOVE` | 確認有引用 | 保留 |

## 與 wifi-bora-ast-tool 的配合

```
ast-tool 找出候選 dead functions
    ↓
lsp-tool 逐一確認是否有 function pointer 引用
    ↓
confidence=high 的 → 安全移除清單
confidence=medium 的 → 人工確認
```

## 注意事項

- LSP 分析需要完整的 `compile_commands.json`，build 後才能分析
- 分析大型 codebase 可能需要數分鐘（clangd indexing）
- macro 中的 symbol 引用可能無法被 LSP 偵測，需額外確認
