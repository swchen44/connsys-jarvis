# WiFi Bora Memory Slim Expert

分析和精簡 Wi-Fi Bora 韌體的 ROM/RAM footprint。

## 安裝

```bash
python connsys-jarvis/setup.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json
```

## 包含的 Skills

- `wifi-bora-memslim-flow` — 記憶體精簡 SOP
- `wifi-bora-ast-tool` — AST 分析工具
- `wifi-bora-lsp-tool` — LSP symbol 追蹤工具

## 依賴的 Experts

- `framework-base-expert`
- `wifi-bora-base-expert`
- `sys-bora-preflight-expert`
