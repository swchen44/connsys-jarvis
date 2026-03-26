# Framework Base Expert

Connsys Jarvis 框架層 Expert，提供跨 domain 共用的 skill/hook/command。

## 安裝

```bash
python connsys-jarvis/install.py --init framework/experts/framework-base-expert/expert.json
```

## 包含的 Skills

- `framework-expert-discovery-knowhow` — Expert 探索與選擇
- `framework-handoff-flow` — Expert 交接 SOP
- `framework-memory-tool` — 記憶系統操作工具

## 包含的 Hooks

- `session-start.sh` — session 開始時載入摘要
- `session-end.sh` — session 結束時儲存摘要
- `pre-compact.sh` — context 壓縮前快照
- `mid-session-checkpoint.sh` — 定期 checkpoint
- `shared-utils.sh` — hook 共用工具

## 包含的 Commands

- `framework-experts-tool` — `/experts` 指令實作
- `framework-handoff-tool` — `/handoff` 指令實作
