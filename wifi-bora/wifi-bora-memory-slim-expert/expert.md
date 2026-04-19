# WiFi Bora Memory Slim Expert

## What This Expert Solves

- ROM/RAM footprint analysis and reduction for WiFi Bora firmware
- Dead code identification via AST analysis and LSP symbol tracing
- Linker script section optimization
- Symbol map analysis for identifying top consumers

## Critical Constraints

### Before Starting Any Slim Work
- Confirm the target: how much ROM/RAM to save, and is there a deadline?
- Always analyze the .map file first — never propose slim suggestions without data

### Risk Assessment Rules

| Operation | Risk | Required Verification |
|-----------|------|----------------------|
| Disable feature via Kconfig | Medium | Confirm feature is not in use |
| Modify linker script section | Medium | Build verification |
| Remove dead code | Medium | Static analysis confirmation |
| Modify struct layout | High | Binary compatibility check |
| git push | High | Human confirmation |

### Human-in-the-Loop (Mandatory)
- `git push` — must ask for confirmation before pushing
- `make clean` — must ask for confirmation before cleaning build

### AST Analysis Scope
- When using AST tool to find dead code, always confirm analysis scope to avoid false positives from cross-module references

## Commonly Forgotten Rules

- Backup linker script before modification and explain the impact of changes
- Compare map files before and after each slim step to confirm actual savings
- Never remove code on the critical protocol path, even if it appears unused
- Every slim proposal must include estimated savings (in bytes) and risk level
