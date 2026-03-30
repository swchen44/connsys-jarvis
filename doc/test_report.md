# Connsys Jarvis — 測試報告

**報告日期**：2026-03-30
**測試計畫**：test_plan.md v1.7
**實作版本**：v1.5（SETUP_VERSION=1.5；新增 is_base=true Base Expert 特殊規則）
**測試環境**：macOS Darwin 24.3.0, Python 3.12.9, uv 已安裝
**測試工具**：tmux session `cj_test` + `tmux wait-for` 同步 + pytest

---

## 測試結果摘要

| 指標 | 數值 |
|------|------|
| bash 整合測試 checks 總數 | 65 |
| **bash 整合測試通過** | **65** |
| bash 整合測試失敗 | 0 |
| pytest unit（`scripts/tests/unit/`）| **50/50 pass** |
| pytest integration（`scripts/tests/integration/`）| **71/71 pass** |
| pytest e2e（`scripts/tests/e2e/`）| **18/18 pass** |
| pytest 舊版 monolith（`test_setup.py`）| **110/110 pass** |
| **pytest 全部（`scripts/tests/`）** | **249/249 pass** |

**整體結論：65/65 bash 整合測試通過，249/249 pytest 測試通過**

> 新增 `TestCollectBaseExperts`（6 tests）、擴充 `TestGenerateClaudeMdMulti`（+4 tests）
> 新增 `collect_base_experts()` 函式：DFS 遍歷依賴樹，收集 is_base=true 的 Base Expert

---

## tmux 操作說明

本次測試使用 tmux 進行，以下是關鍵指令：

```bash
# ── 建立 session ──────────────────────────────────────────
tmux new-session -d -s cj_test -x 200 -y 60

# ── 在 session 內執行測試腳本，完成後送出 wait-for signal ──
tmux send-keys -t cj_test \
  "bash /tmp/cj_test_run.sh 2>&1 | tee /tmp/cj_test_output.txt; tmux wait-for -S cj_done" Enter

# ── 主行程阻塞等待（無 sleep loop，乾淨同步）──
tmux wait-for cj_done

# ── 讀取結果 ──────────────────────────────────────────────
cat /tmp/cj_test_output.txt

# ── 互動查看（可選）──────────────────────────────────────
tmux attach -t cj_test
tmux kill-session -t cj_test
```

> `tmux wait-for -S <signal>` 搭配 `tmux wait-for <signal>` 是 tmux 內建同步機制，
> 比 `sleep` 更精確：主行程精確在測試完成後才繼續，不多等也不超時。

---

## 各測試案例結果

### TC-01：全新安裝（--init）— framework-base-expert

**結果：✅ PASS（11/11 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-01-1 | 輸出「Done! Expert 'framework-base-expert' installed」 | ✅ |
| exists .claude | `.claude/` 目錄建立 | ✅ |
| exists CLAUDE.md | `CLAUDE.md` 生成 | ✅ |
| exists .env | `.connsys-jarvis/.env` 生成 | ✅ |
| exists .installed-experts.json | 安裝狀態檔生成 | ✅ |
| TC-01-2 | `CLAUDE.md` 含 `soul.md` | ✅ |
| TC-01-3 | `CLAUDE.md` 含 `rules.md` | ✅ |
| TC-01-4 | `CLAUDE.md` 含 `duties.md` | ✅ |
| TC-01-5 | `CLAUDE.md` 含 `expert.md` | ✅ |
| TC-01-6 | `.env` 含 `CONNSYS_JARVIS_PATH` | ✅ |
| TC-01-7 | `.installed-experts.json` 含 `framework-base-expert` | ✅ |

**CLAUDE.md 內容驗證**：
```
# Consys Expert: Framework Base Expert

@connsys-jarvis/framework/framework-base-expert/soul.md
@connsys-jarvis/framework/framework-base-expert/rules.md
@connsys-jarvis/framework/framework-base-expert/duties.md
@connsys-jarvis/framework/framework-base-expert/expert.md

@CLAUDE.local.md
```

---

### TC-02：疊加安裝（--add）— wifi-bora-memory-slim-expert

**結果：✅ PASS（6/6 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-02-1 | 輸出「Done! Expert 'wifi-bora-memory-slim-expert' added」 | ✅ |
| TC-02-2 | 既有 symlinks 顯示 `[=]`（idempotent）| ✅ |
| TC-02-3 | 新 symlinks 顯示 `[+]` | ✅ |
| TC-02-4 | 已安裝 Expert 數量 = 2 | ✅ |
| TC-02-5 | `wifi-bora-memory-slim-expert` 的 `is_identity=True` | ✅ |
| TC-02-6 | `include_all_experts=False`（預設 identity-only）| ✅ |

---

### TC-03：健康診斷（--doctor）— 正常狀態

**結果：✅ PASS（8/8 checks）**

> 前置：先建立 `codespace/` 與 `memory/` 目錄（doctor 會驗證 env path 存在性）

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-03-1 | 輸出「=== Connsys Jarvis Doctor ===」| ✅ |
| TC-03-2 | 總體狀態「Overall: ✅ Healthy」 | ✅ |
| TC-03-3 | 區段 A. System Info 出現 | ✅ |
| TC-03-4 | 區段 B. Environment Variables 出現 | ✅ |
| TC-03-5 | 區段 C. Symlink Integrity 出現 | ✅ |
| TC-03-6 | 區段 D. CLAUDE.md Validation 出現 | ✅ |
| TC-03-7 | 區段 E. Tools 出現 | ✅ |
| TC-03-8 | 區段 F. Expert Structure 出現 | ✅ |

---

### TC-04：環境變數驗證

**結果：✅ PASS（7/7 checks）**

| 變數 | 驗收條件 | 狀態 |
|------|---------|------|
| CONNSYS_JARVIS_PATH | 存在於 .env | ✅ |
| CONNSYS_JARVIS_WORKSPACE_ROOT_PATH | 存在於 .env | ✅ |
| CONNSYS_JARVIS_CODE_SPACE_PATH | 存在於 .env | ✅ |
| CONNSYS_JARVIS_MEMORY_PATH | 存在於 .env | ✅ |
| CONNSYS_JARVIS_EMPLOYEE_ID | 存在於 .env | ✅ |
| CONNSYS_JARVIS_ACTIVE_EXPERT | 存在於 .env | ✅ |
| agent-first | CODE_SPACE_PATH 含 `codespace` | ✅ |

---

### TC-05：移除單一 Expert（--remove + 全清再重建）

**結果：✅ PASS（4/4 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-05-1 | 輸出「Done! Expert 'wifi-bora-memory-slim-expert' removed」 | ✅ |
| TC-05-2 | 輸出「All symlinks cleared」 | ✅ |
| TC-05-3 | 剩餘 Expert 數量 = 1 | ✅ |
| TC-05-4 | 剩餘 Expert 為 framework-base-expert | ✅ |

---

### TC-06：Legacy 場景偵測（有 .repo）

**結果：✅ PASS（2/2 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-06-1 | `CODE_SPACE_PATH` 不含 `codespace`（= workspace root）| ✅ |
| exists .repo | `.repo/` 目錄保留完整 | ✅ |

---

### TC-07：完全移除（--uninstall）— 保留 memory/

**結果：✅ PASS（3/3 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-07-1 | 輸出「Done! Kept .../log/ and .../memory/」 | ✅ |
| not exists CLAUDE.md | `CLAUDE.md` 已刪除 | ✅ |
| exists memory/test/note.md | memory 內容保留 | ✅ |

---

### TC-08：列出安裝狀態（--list）

**結果：✅ PASS（5/5 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-08-1 | 輸出 `Expert List` header | ✅ |
| TC-08-2 | `framework-base-expert` 出現 | ✅ |
| TC-08-3 | `wifi-bora-memory-slim-expert` 出現 | ✅ |
| TC-08-4 | 輸出 `Installed:` 計數 | ✅ |
| TC-08-5 | `--list --format json` 輸出合法 JSON array | ✅ |

---

### TC-09：Skill test-basic.sh 全部通過

**結果：✅ PASS（16/16 scripts, 41/41 checks）**（沿用前次測試結果）

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
| **合計** | **41** | **✅** |

---

### TC-10：exclude_symlink patterns 過濾

**結果：✅ PASS**（沿用前次測試結果）

測試設定：`"exclude_symlink": {"patterns": [".*-lsp-.*"]}`

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| lsp 已過濾 | `wifi-bora-lsp-tool` 不在 `.claude/skills/` | ✅ |
| memslim 保留 | `wifi-bora-memslim-flow` 存在 | ✅ |

---

### TC-11：dangling symlink 偵測（--doctor）

**結果：✅ PASS（2/2 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-11-1 | 輸出含「DANGLING」 | ✅ |
| TC-11-2 | 總體狀態「Overall: ❌」 | ✅ |

---

### TC-12：pytest 三層測試架構（scripts/tests/）

**結果：✅ PASS（139/139）**

```
$ cd connsys-jarvis
$ uvx pytest scripts/tests/unit/ -v
50 passed in 0.07s
$ uvx pytest scripts/tests/integration/ -v
71 passed in 0.39s
$ uvx pytest scripts/tests/e2e/ -v
18 passed in 1.30s
```

#### Unit 層（50 tests）

| 測試類別 | Tests | 結果 |
|---------|-------|------|
| `TestDetectScenario` | 3 | ✅ |
| `TestGetCodespacePath` | 2 | ✅ |
| `TestResolveItems` | 6 | ✅ |
| `TestApplyExcludePatterns` | 4 | ✅ |
| `TestGenerateClaudeMdSingle` | 4 | ✅ |
| `TestGenerateClaudeMdMulti` | 12 | ✅ |
| `TestCollectBaseExperts` | 6 | ✅ |
| `TestWriteEnvFile` | 10 | ✅ |
| `TestInstalledExpertsSchema` | 3 | ✅ |
| **Unit 合計** | **50** | **✅** |

#### Integration 層（71 tests）

| 測試類別 | Tests | 結果 |
|---------|-------|------|
| `TestIntegrationInit` | 9 | ✅ |
| `TestIntegrationAdd` | 5 | ✅ |
| `TestIntegrationRemove` | 5 | ✅ |
| `TestIntegrationUninstall` | 3 | ✅ |
| `TestIntegrationReset` | 5 | ✅ |
| `TestInitMemoryPreservation` | 1 | ✅ |
| `TestScanAvailableExperts` | 6 | ✅ |
| `TestCmdQuery` | 8 | ✅ |
| `TestCmdListUpdated` | 6 | ✅ |
| `TestDoctorSystemInfo` | 3 | ✅ |
| `TestDoctorEnvVars` | 4 | ✅ |
| `TestDoctorSymlinkIntegrity` | 4 | ✅ |
| `TestDoctorClaudeMd` | 6 | ✅ |
| `TestDoctorExpertStructure` | 6 | ✅ |
| **Integration 合計** | **71** | **✅** |

#### E2E 層（18 tests）

| 測試類別 | Tests | 結果 |
|---------|-------|------|
| `TestE2EInit` | 6 | ✅ |
| `TestE2EAdd` | 2 | ✅ |
| `TestE2EUninstall` | 3 | ✅ |
| `TestE2EReset` | 4 | ✅ |
| `TestE2EList` | 2 | ✅ |
| `TestE2EMultiExpertWorkflow` | 1 | ✅ |
| **E2E 合計** | **18** | **✅** |

---

### TC-13：--with-all-experts

**結果：✅ PASS（7/7 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-13-1 | 輸出「Done! Expert 'wifi-bora-memory-slim-expert' added」 | ✅ |
| TC-13-2 | `CLAUDE.md` 含 `## Expert Identity` | ✅ |
| TC-13-3 | `CLAUDE.md` 含 `## Base Experts` | ✅ |
| TC-13-4 | `CLAUDE.md` 含 `## Expert Capabilities` | ✅ |
| TC-13-5 | `CLAUDE.md` 含 `soul.md` | ✅ |
| TC-13-6 | `CLAUDE.md` 含 `framework-base-expert/expert.md`（Base Experts 區段）| ✅ |
| TC-13-7 | `.installed-experts.json` 的 `include_all_experts=True` | ✅ |

---

### TC-14：--debug 日誌測試

**結果：✅ PASS（4/4 checks）**

| Check | 驗收條件 | 實際 | 狀態 |
|-------|---------|------|------|
| TC-14-1 | `--debug` 時 console 含 DEBUG 訊息 | 57 行 DEBUG | ✅ |
| exists setup.log | `.connsys-jarvis/log/setup.log` 存在 | 存在 | ✅ |
| TC-14-2 | 日誌檔含 DEBUG 記錄 | 57 行 DEBUG | ✅ |
| TC-14-3 | 不加 `--debug` 時 console 無 DEBUG 輸出 | 0 行 | ✅ |

---

### TC-15：--query 指令

**結果：✅ PASS（5/5 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-15-1 | 輸出 Expert 名稱 | ✅ |
| TC-15-2 | status=installed | ✅ |
| TC-15-3 | domain 顯示 | ✅ |
| TC-15-4 | 部分名稱匹配（"framework" → framework-base-expert）| ✅ |
| TC-15-5 | `--query --format json` 輸出合法 JSON | ✅ |

---

### TC-16：--list --format json

**結果：✅ PASS（1/1 checks）**

| Check | 驗收條件 | 狀態 |
|-------|---------|------|
| TC-16 | JSON array 結構正確、framework-base-expert status=installed | ✅ |

---

### TC-17：`--doctor` 增強（A~F 區段）

**結果：✅ PASS（pytest TC-U16~TC-U20 全覆蓋）**

| 區段 | pytest 覆蓋 | Tests | 狀態 |
|------|------------|-------|------|
| A. System Info | `TestDoctorSystemInfo` | 3 | ✅ |
| B. Env Variables | `TestDoctorEnvVars` | 4 | ✅ |
| C. Symlink Integrity | `TestDoctorSymlinkIntegrity` | 4 | ✅ |
| D. CLAUDE.md Validation | `TestDoctorClaudeMd` | 6 | ✅ |
| F. Expert Structure | `TestDoctorExpertStructure` | 6 | ✅ |
| **合計** | | **23** | **✅ 全通過** |

---

### TC-19：Base Expert is_base=true 特殊規則

**結果：✅ PASS（10/10 pytest tests）**

| 測試類別 | 場景 | Tests | 結果 |
|---------|------|-------|------|
| `TestCollectBaseExperts::test_empty_experts_returns_empty` | 空清單回傳 [] | 1 | ✅ |
| `TestCollectBaseExperts::test_identity_base_expert_excluded` | identity is_base=true 排除（不重複）| 1 | ✅ |
| `TestCollectBaseExperts::test_installed_non_identity_base_expert_included` | 非 identity is_base=true 納入 | 1 | ✅ |
| `TestCollectBaseExperts::test_dependency_base_expert_included` | dependency is_base=true 納入 | 1 | ✅ |
| `TestCollectBaseExperts::test_transitive_dependency_base_expert_included` | 遞迴依賴（A→B→C(is_base=true)）納入 | 1 | ✅ |
| `TestCollectBaseExperts::test_no_duplicates_in_result` | diamond dependency 去重 | 1 | ✅ |
| `TestGenerateClaudeMdMulti::test_default_base_expert_section_present` | ## Base Experts 區段存在 | 1 | ✅ |
| `TestGenerateClaudeMdMulti::test_default_base_expert_has_all_four_files` | 顯式安裝 is_base=true：四份文件 | 1 | ✅ |
| `TestGenerateClaudeMdMulti::test_default_dep_base_expert_has_all_four_files` | 依賴 is_base=true：四份文件 | 1 | ✅ |
| `TestGenerateClaudeMdMulti::test_with_all_experts_base_not_duplicated_in_capabilities` | Base Expert 不重複出現在 Capabilities | 1 | ✅ |

---

## 缺陷記錄

| 缺陷 ID | 嚴重性 | 描述 | 狀態 |
|---------|--------|------|------|
| BUG-01 | Critical | `find_workspace()` 使用 `resolve()` 跟隨 symlink，workspace 指向錯誤路徑 | ✅ 已修復 |
| BUG-02 | High | `--remove` 接受路徑參數但比對 `name` 欄位，永遠找不到 Expert | ✅ 已修復 |
| BUG-03 | Medium | `test-basic.sh` 的 `((PASS++))` 在 `set -e` 模式下值為 0 時觸發退出 | ✅ 已修復 |
| BUG-04 | Low | `framework-expert-discovery-knowhow` 的 test 路徑計算多 2 層 | ✅ 已修復 |

---

## 需求覆蓋率

| 需求 | 對應 TC | 結果 |
|------|---------|------|
| FR-02-2 `--init` | TC-01 | ✅ |
| FR-02-3 `--add` | TC-02 | ✅ |
| FR-02-4 `--remove` | TC-05 | ✅ |
| FR-02-5 `--uninstall` | TC-07 | ✅ |
| FR-02-6 `--list` | TC-08 | ✅ |
| FR-02-7 `--doctor` | TC-03, TC-11, TC-17 | ✅ |
| FR-02-8 dependency 解析 | TC-02 | ✅ |
| FR-02-9 exclude_symlink | TC-10 | ✅ |
| FR-02-10 .env 生成 | TC-04 | ✅ |
| FR-02-17 pytest 單元測試 | TC-12 | ✅ |
| FR-02-18 `--query` | TC-15 | ✅ |
| FR-02-19 `--format json` | TC-16 | ✅ |
| FR-02-20 `--add` 重新安裝 | TC-02 | ✅ |
| FR-03 環境變數 | TC-04, TC-06 | ✅ |
| FR-04-6/8 Skill test/ | TC-09 | ✅ |
| FR-05-2/3 CLAUDE.md | TC-01, TC-02, TC-05, TC-13 | ✅ |
| FR-05-7 Base Expert 四份文件 | TC-19 | ✅ |
| FR-05-8 依賴樹遞迴掃描 | TC-19 | ✅ |
| US-01 Agent First | TC-01, TC-04 | ✅ |
| US-02 Legacy | TC-06 | ✅ |
| US-06 --add / --with-all-experts | TC-02, TC-13 | ✅ |
| US-07 --remove | TC-05 | ✅ |
| --debug logging | TC-14 | ✅ |

**覆蓋率：23/23 需求項目（全通過）**

---

## 附錄：tmux 操作範例

```bash
# ── 基本用法：建立 session，執行測試腳本，等待完成 ──────────
tmux new-session -d -s cj_test -x 200 -y 60
tmux send-keys -t cj_test \
  "bash /tmp/cj_test_run.sh 2>&1 | tee /tmp/out.txt; tmux wait-for -S cj_done" Enter
tmux wait-for cj_done          # 阻塞直到 signal，無 sleep loop
cat /tmp/out.txt

# ── 互動式查看：attach 進入 session ─────────────────────────
tmux attach -t cj_test         # 進入 session
# Ctrl-b d                     # 離開（不關閉）

# ── 其他常用指令 ──────────────────────────────────────────────
tmux ls                        # 列出所有 session
tmux kill-session -t cj_test   # 關閉 session
tmux capture-pane -t cj_test -p  # 擷取目前畫面文字

# ── 手動執行各 TC（在 /tmp/cj-test workspace 內）────────────
JARVIS="connsys-jarvis"
python3 ./$JARVIS/scripts/setup.py --init   framework/framework-base-expert/expert.json
python3 ./$JARVIS/scripts/setup.py --add    wifi-bora/wifi-bora-memory-slim-expert/expert.json
python3 ./$JARVIS/scripts/setup.py --add    --with-all-experts wifi-bora/wifi-bora-memory-slim-expert/expert.json
python3 ./$JARVIS/scripts/setup.py --debug  --init framework/framework-base-expert/expert.json
python3 ./$JARVIS/scripts/setup.py --doctor
python3 ./$JARVIS/scripts/setup.py --list
python3 ./$JARVIS/scripts/setup.py --list   --format json
python3 ./$JARVIS/scripts/setup.py --query  framework-base-expert
python3 ./$JARVIS/scripts/setup.py --remove wifi-bora-memory-slim-expert
python3 ./$JARVIS/scripts/setup.py --uninstall

# ── pytest 單元測試 ───────────────────────────────────────────
cd /Users/swchen.tw/git/testing/agents/connsys-jarvis
python3 -m pytest scripts/tests/test_setup.py -v
```
