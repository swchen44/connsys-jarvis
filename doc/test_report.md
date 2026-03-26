# Connsys Jarvis — 測試報告

**報告日期**：2026-03-26
**測試計畫**：test_plan.md v1.0
**實作版本**：v1.0（commit: 8490158）
**測試環境**：macOS Darwin 24.3.0, Python 3.13.2, uv 已安裝
**測試工具**：tmux session `connsys-verify` + bash

---

## 測試結果摘要

| 指標 | 數值 |
|------|------|
| 測試案例總數 | 11 |
| **通過** | **11** |
| 失敗 | 0 |
| Skill 測試腳本 | 16/16 pass |
| Skill 測試 checks | 41/41 pass |

**整體結論：✅ 全部通過**

---

## 各測試案例結果

### TC-01：全新安裝（--init）— framework-base-expert

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 3 | 輸出「完成！Expert 'framework-base-expert' 已安裝」 | 符合 | ✅ |
| 4 | `.claude/skills/` 有 3 個 symlinks | 3 | ✅ |
| 5 | `.claude/hooks/` 有 5 個 symlinks | 5 | ✅ |
| 6 | `.claude/commands/` 有 2 個 symlinks | 2 | ✅ |
| 7 | `CLAUDE.md` 有 4 個 `@connsys-jarvis` @include 行 | 4 | ✅ |
| 8 | `.env` 含 6 個 `CONNSYS_JARVIS_*` 變數 | 6 | ✅ |
| 9 | `.installed-experts.json` 含 framework-base-expert | 符合 | ✅ |

**CLAUDE.md 內容驗證**：
```
# Consys Expert: Framework Base Expert

@connsys-jarvis/framework/experts/framework-base-expert/soul.md
@connsys-jarvis/framework/experts/framework-base-expert/rules.md
@connsys-jarvis/framework/experts/framework-base-expert/duties.md
@connsys-jarvis/framework/experts/framework-base-expert/expert.md

@CLAUDE.local.md
```

---

### TC-02：疊加安裝（--add）— wifi-bora-memory-slim-expert

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 3 | 既有 symlinks 顯示 `[=]`（idempotent）| 10 個 `[=]` | ✅ |
| 4 | 新 symlinks 顯示 `[+]` | 10 個 `[+]` | ✅ |
| 5 | `.claude/skills/` 共 13 個 | 13 | ✅ |
| 6 | `CLAUDE.md` 含「2 Experts 已安裝」 | 符合 | ✅ |
| 7 | `wifi-bora-memory-slim-expert` 的 `is_identity=true` | 符合 | ✅ |

**依賴解析驗證**：

| 來源 Expert | 貢獻 | 解析結果 |
|------------|------|---------|
| framework-base-expert | 3 skills (列表) + all hooks + 2 commands | ✅ |
| wifi-bora-base-expert | 5 skills (列表) | ✅ |
| sys-bora-preflight-expert | 2 skills (列表) | ✅ |
| internal | 3 skills | ✅ |

---

### TC-03：健康診斷（--doctor）

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 3 | 13 個 Skills 全部 ✅ OK | 13 ✅ | ✅ |
| 4 | 2 個 Commands 全部 ✅ OK | 2 ✅ | ✅ |
| 5 | 5 個 Hooks 全部 ✅ OK | 5 ✅ | ✅ |
| 6 | Python/uv/uvx/.env/CLAUDE.md ✅ | 全部 ✅ | ✅ |
| 7 | 總體狀態「✅ 健康」 | 符合 | ✅ |

```
doctor_ok=26（含環境項）  doctor_fail=0
```

---

### TC-04：環境變數驗證

**結果：✅ PASS**

| 變數 | 預期值 | 實際值 | 狀態 |
|------|--------|--------|------|
| CONNSYS_JARVIS_PATH | /private/tmp/cj-test/connsys-jarvis | 符合 | ✅ |
| CONNSYS_JARVIS_WORKSPACE_ROOT_PATH | /private/tmp/cj-test | 符合 | ✅ |
| CONNSYS_JARVIS_CODE_SPACE_PATH | /private/tmp/cj-test/codespace（agent-first）| 符合 | ✅ |
| CONNSYS_JARVIS_MEMORY_PATH | /private/tmp/cj-test/.connsys-jarvis/memory | 符合 | ✅ |
| CONNSYS_JARVIS_EMPLOYEE_ID | Shaowei Chen（git config user.name）| 符合 | ✅ |
| CONNSYS_JARVIS_ACTIVE_EXPERT | wifi-bora-memory-slim-expert | 符合 | ✅ |

---

### TC-05：移除單一 Expert（--remove + Reference Count）

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 2 | 輸出「完成！Expert 'wifi-bora-memory-slim-expert' 已移除」 | 符合 | ✅ |
| 3 | 輸出 10 個 `[-]` 移除項目 | 10 個 `[-]` | ✅ |
| 4 | `.claude/skills/` 剩 3 個 | 3 | ✅ |
| 5 | 剩餘 skills 為 framework-base-expert 的 3 個 | 符合 | ✅ |
| 6 | `CLAUDE.md` 退回單 Expert 格式 | 符合 | ✅ |
| 7 | `.installed-experts.json` 剩 1 個 Expert | 1 | ✅ |

**Reference Count 驗證**：

| Skill | 只有 wifi-bora-slim 聲明 | 結果 |
|-------|------------------------|------|
| wifi-bora-memslim-flow | ✅ | 已刪除 ✅ |
| wifi-bora-ast-tool | ✅ | 已刪除 ✅ |
| wifi-bora-lsp-tool | ✅ | 已刪除 ✅ |
| framework-expert-discovery-knowhow | ❌ (framework 仍聲明) | 保留 ✅ |
| session-start.sh | ❌ (framework 仍聲明) | 保留 ✅ |

---

### TC-06：Legacy 場景偵測（有 .repo）

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 3 | 安裝成功 | 符合 | ✅ |
| 4 | CODE_SPACE_PATH = workspace root（無 codespace/）| `/private/tmp/cj-legacy` | ✅ |
| 5 | `.repo/` 未被破壞 | 存在 | ✅ |

**場景對比**：

| 場景 | CODE_SPACE_PATH | 偵測方式 |
|------|-----------------|---------|
| Agent First | `<workspace>/codespace` | workspace 根目錄無 `.repo` |
| Legacy | `<workspace>` | workspace 根目錄有 `.repo` |

---

### TC-07：完全移除（--uninstall）

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 3 | 輸出「完成！保留 .../log/ 和 .../memory/」 | 符合 | ✅ |
| 4 | `CLAUDE.md` 不存在 | GONE | ✅ |
| 5 | `.claude/skills/` 有 0 個 | 0 | ✅ |
| 6 | `.claude/hooks/` 有 0 個 | 0 | ✅ |
| 7 | `.connsys-jarvis/memory/test/note.md` 仍存在 | 存在 | ✅ |

---

### TC-08：列出安裝狀態（--list）

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 2 | 輸出「=== 已安裝的 Experts ===」 | 符合 | ✅ |
| 3 | 2 個 Expert 清單，identity 標記正確 | 符合 | ✅ |
| 4 | Skills (13) 全部 ✅ | 13 ✅ | ✅ |
| 5 | Hooks (5) 全部 ✅ | 5 ✅ | ✅ |
| 6 | Commands (2) 全部 ✅ | 2 ✅ | ✅ |

---

### TC-09：Skill test-basic.sh 全部通過

**結果：✅ PASS（16/16 scripts, 41/41 checks）**

| Skill | Checks | 結果 |
|-------|--------|------|
| framework-expert-discovery-knowhow | 3 | ✅ |
| framework-handoff-flow | 4 | ✅ |
| framework-memory-tool | 2 | ✅ |
| sys-bora-gerrit-tool | 2 | ✅ |
| sys-bora-repo-tool | 2 | ✅ |
| sys-bora-gerrit-commit-flow | 2 | ✅ |
| sys-bora-preflight-flow | 2 | ✅ |
| wifi-bora-arch-knowhow | 3 | ✅ |
| wifi-bora-build-flow | 3 | ✅ |
| wifi-bora-linkerscript-knowhow | 3 | ✅ |
| wifi-bora-memory-knowhow | 3 | ✅ |
| wifi-bora-protocol-knowhow | 3 | ✅ |
| wifi-bora-symbolmap-knowhow | 3 | ✅ |
| wifi-bora-ast-tool | 2 | ✅ |
| wifi-bora-lsp-tool | 2 | ✅ |
| wifi-bora-memslim-flow | 2 | ✅ |
| **合計** | **41** | **✅ 全通過** |

---

### TC-10：exclude_symlink patterns 過濾

**結果：✅ PASS**

測試設定：`"exclude_symlink": {"patterns": [".*-lsp-.*"]}`

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 3 | `wifi-bora-lsp-tool` 不在 `.claude/skills/` | 已過濾（lsp_excluded=0）| ✅ |
| 4 | `wifi-bora-memslim-flow` 存在 | 存在（memslim_present=1）| ✅ |
| 5 | 還原 expert.json | patterns=[] | ✅ |

---

### TC-11：dangling symlink 偵測（--doctor）

**結果：✅ PASS**

| Step | 驗收條件 | 實際結果 | 狀態 |
|------|---------|---------|------|
| 3 | `--doctor` 輸出「❌ fake-skill → ... DANGLING」 | 符合 | ✅ |
| 4 | 總體狀態非「✅ 健康」 | 「❌ 有 dangling symlinks，請重新執行 --init 或 --add」 | ✅ |
| 5 | 清理後 doctor 恢復健康 | 符合（dangling 移除後重測）| ✅ |

---

## 缺陷記錄

在測試過程中發現並修復的缺陷：

| 缺陷 ID | 嚴重性 | 描述 | 狀態 |
|---------|--------|------|------|
| BUG-01 | Critical | `find_workspace()` 使用 `resolve()` 跟隨 symlink，workspace 指向錯誤路徑 | ✅ 已修復（commit 8490158）|
| BUG-02 | High | `--remove` 接受路徑參數但比對 `name` 欄位，永遠找不到 Expert | ✅ 已修復（commit 8490158）|
| BUG-03 | Medium | `test-basic.sh` 的 `((PASS++))` 在 `set -e` 模式下值為 0 時觸發退出 | ✅ 已修復（commit 8490158）|
| BUG-04 | Low | `framework-expert-discovery-knowhow` 的 test 路徑計算多 2 層，registry.json 找不到 | ✅ 已修復（commit 8490158）|

---

## 需求覆蓋率

| 需求 | 對應 TC | 結果 |
|------|---------|------|
| FR-02-2 `--init` | TC-01 | ✅ |
| FR-02-3 `--add` | TC-02 | ✅ |
| FR-02-4 `--remove` | TC-05 | ✅ |
| FR-02-5 `--uninstall` | TC-07 | ✅ |
| FR-02-6 `--list` | TC-08 | ✅ |
| FR-02-7 `--doctor` | TC-03, TC-11 | ✅ |
| FR-02-8 dependency 解析 | TC-02 | ✅ |
| FR-02-9 exclude_symlink | TC-10 | ✅ |
| FR-02-10 .env 生成 | TC-04 | ✅ |
| FR-03 環境變數 | TC-04, TC-06 | ✅ |
| FR-04-6/8 Skill test/ | TC-09 | ✅ |
| FR-05-2/3 CLAUDE.md | TC-01, TC-02, TC-05 | ✅ |
| US-01 Agent First | TC-01, TC-04 | ✅ |
| US-02 Legacy | TC-06 | ✅ |
| US-06 --add | TC-02 | ✅ |
| US-07 --remove | TC-05 | ✅ |

**覆蓋率：16/16 需求項目（100%）**

---

## 附錄：tmux 驗證指令

```bash
# 建立驗證 session
tmux new-session -d -s connsys-verify -x 220 -y 50

# 設定 workspace
tmux send-keys -t connsys-verify \
  "rm -rf /tmp/cj-test && mkdir /tmp/cj-test && ln -s <jarvis_path> /tmp/cj-test/connsys-jarvis && cd /tmp/cj-test" Enter

# 執行各 TC
tmux send-keys -t connsys-verify \
  "python3 ./connsys-jarvis/setup.py --init framework/experts/framework-base-expert/expert.json" Enter
tmux send-keys -t connsys-verify \
  "python3 ./connsys-jarvis/setup.py --add wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json" Enter
tmux send-keys -t connsys-verify \
  "python3 ./connsys-jarvis/setup.py --doctor" Enter
tmux send-keys -t connsys-verify \
  "python3 ./connsys-jarvis/setup.py --remove wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json" Enter
tmux send-keys -t connsys-verify \
  "python3 ./connsys-jarvis/setup.py --list" Enter
tmux send-keys -t connsys-verify \
  "python3 ./connsys-jarvis/setup.py --uninstall" Enter

# 查看輸出
tmux capture-pane -t connsys-verify -p
```
