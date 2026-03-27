# Connsys Jarvis — 測試計畫

**文件版本**：v1.4
**日期**：2026-03-27
**依據**：agents-requirements.md v3.3, agents-design.md v3.3
**變更說明**：
- v1.1 — setup.py 路徑改為 scripts/setup.py；新增 TC-12 pytest 單元測試
- v1.2 — 修正 TC-02 Step 6（預設 identity-only，無 count header）；更新 TC-12 測試數 57→61（含 --with-all-experts tests）；新增 TC-13（--with-all-experts 整合）、TC-14（--debug 日誌）
- v1.3 — TC-02 補充 Step 8、9（驗證 include_all_experts=false 及 install_order）；對齊需求書 FR-02-4 reference count 與 FR-02-8 dependencies/internal 定義
- v1.4 — 更新 TC-05（--remove 改全清再重建）；更新 TC-08（--list 顯示 installed+available，新增 --format json）；新增 TC-15（--query）、TC-16（--list --format json）

---

## 測試環境

| 項目 | 規格 |
|------|------|
| OS | macOS Darwin 24.3.0 |
| Python | 3.13.2 |
| Shell | zsh |
| Test Workspace | /tmp/cj-test |
| Connsys Jarvis | /Users/swchen.tw/git/testing/agents/connsys-jarvis |

---

## TC-01：全新安裝（--init）— framework-base-expert

**目的**：驗證 `--init` 能正確建立 symlinks、生成 CLAUDE.md 與 .env
**對應需求**：FR-02-2, FR-05-1, FR-05-2, US-01

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | `rm -rf /tmp/cj-test && mkdir /tmp/cj-test` | 建立空 workspace |
| 2 | `ln -s <jarvis> /tmp/cj-test/connsys-jarvis` | connsys-jarvis 可用 |
| 3 | `cd /tmp/cj-test && python3 ./connsys-jarvis/scripts/setup.py --init framework/experts/framework-base-expert/expert.json` | 輸出「完成！Expert 'framework-base-expert' 已安裝」 |
| 4 | `ls .claude/skills/` | 3 個 skills symlinks |
| 5 | `ls .claude/hooks/` | 5 個 hooks symlinks |
| 6 | `ls .claude/commands/` | 2 個 commands symlinks |
| 7 | `cat CLAUDE.md` | 含 @include soul.md, rules.md, duties.md, expert.md |
| 8 | `cat .connsys-jarvis/.env` | 含 CONNSYS_JARVIS_* 6 個變數 |
| 9 | `cat .connsys-jarvis/.installed-experts.json` | experts 陣列含 framework-base-expert |

---

## TC-02：疊加安裝（--add）— wifi-bora-memory-slim-expert

**目的**：驗證 `--add` 跨 3 個 expert 的依賴解析、idempotent（已存在跳過）
**對應需求**：FR-02-3, FR-02-8, US-06

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後 | workspace 已有 framework-base-expert |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --add wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json` | 輸出「完成！Expert 'wifi-bora-memory-slim-expert' 已加入」 |
| 3 | 確認輸出含 `[=]`（既有跳過）| framework 的 3 skills + 5 hooks + 2 commands 顯示 `[=]` |
| 4 | 確認輸出含 `[+]`（新建） | wifi-bora 5 skills + sys-bora 2 skills + internal 3 skills |
| 5 | `ls .claude/skills/ \| wc -l` | 13 |
| 6 | `cat CLAUDE.md` | 預設 identity-only 格式：只含 wifi-bora-memory-slim-expert 的 soul/rules/duties/expert.md，**不含**「N Experts 已安裝」count header |
| 7 | `cat .connsys-jarvis/.installed-experts.json` | experts 陣列含 2 個 Expert，wifi-bora-memory-slim-expert 的 is_identity=true |
| 8 | `python3 -c "import json; d=json.load(open('.connsys-jarvis/.installed-experts.json')); print(d.get('include_all_experts'))"` | `False`（預設 identity-only）|
| 9 | 驗證 install_order：framework-base-expert=1、wifi-bora-memory-slim-expert=2 | 符合（依安裝順序遞增）|

---

## TC-03：健康診斷（--doctor）

**目的**：驗證 `--doctor` 能正確檢查 symlink 健康與環境
**對應需求**：FR-02-7

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-02 完成後 | 13 symlinks 存在 |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --doctor` | 輸出「=== Connsys Jarvis Doctor ===」 |
| 3 | 確認 Skills 欄位 | 13 個 ✅ 全部 OK |
| 4 | 確認 Commands 欄位 | 2 個 ✅ 全部 OK |
| 5 | 確認 Hooks 欄位 | 5 個 ✅ 全部 OK |
| 6 | 確認環境檢查 | Python ✅, uv ✅, uvx ✅, .env ✅, CLAUDE.md ✅ |
| 7 | 確認最後一行 | 「總體狀態：✅ 健康」 |

---

## TC-04：環境變數驗證

**目的**：驗證 .env 的所有變數正確，agent-first 場景下 CODE_SPACE_PATH 為 codespace/
**對應需求**：FR-03, FR-05-1

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | `grep CONNSYS_JARVIS_PATH .connsys-jarvis/.env` | = /private/tmp/cj-test/connsys-jarvis |
| 2 | `grep WORKSPACE_ROOT .connsys-jarvis/.env` | = /private/tmp/cj-test |
| 3 | `grep CODE_SPACE .connsys-jarvis/.env` | = /private/tmp/cj-test/codespace（agent-first） |
| 4 | `grep MEMORY_PATH .connsys-jarvis/.env` | = /private/tmp/cj-test/.connsys-jarvis/memory |
| 5 | `grep EMPLOYEE_ID .connsys-jarvis/.env` | = git config user.name |
| 6 | `grep ACTIVE_EXPERT .connsys-jarvis/.env` | = wifi-bora-memory-slim-expert |

---

## TC-05：移除單一 Expert（--remove + 全清再重建）

**目的**：驗證 `--remove` 採全清再重建策略，正確清除所有 symlinks 再依剩餘 Expert 重建
**對應需求**：FR-02-4, US-07

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-02 完成後（13 skills） | |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --remove wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json` | 輸出「完成！Expert 'wifi-bora-memory-slim-expert' 已移除」 |
| 3 | 確認輸出：所有既有 symlinks 先清除，再依剩餘 Expert 重建 | 移除 wifi-bora-memslim-flow 等 10 個，重建 framework 的 3 個 |
| 4 | `ls .claude/skills/ \| wc -l` | 3（framework-base-expert 的 3 個被重建） |
| 5 | `ls .claude/skills/` | framework-expert-discovery-knowhow, framework-handoff-flow, framework-memory-tool |
| 6 | `cat CLAUDE.md` | 退回單 Expert 格式，identity 改為 framework-base-expert |
| 7 | `cat .connsys-jarvis/.installed-experts.json` | experts 陣列只剩 1 個（framework-base-expert） |

---

## TC-06：Legacy 場景偵測（有 .repo）

**目的**：驗證有 `.repo` 時 CODE_SPACE_PATH 等於 workspace root
**對應需求**：US-02, FR-03

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | `rm -rf /tmp/cj-legacy && mkdir -p /tmp/cj-legacy/.repo` | 建立 legacy workspace |
| 2 | `ln -s <jarvis> /tmp/cj-legacy/connsys-jarvis` | |
| 3 | `cd /tmp/cj-legacy && python3 ./connsys-jarvis/scripts/setup.py --init framework/experts/framework-base-expert/expert.json` | 安裝成功 |
| 4 | `grep CODE_SPACE .connsys-jarvis/.env` | = /private/tmp/cj-legacy（同 workspace root，無 codespace/） |
| 5 | 確認原有 .repo 未被破壞 | `ls .repo` 仍存在 |

---

## TC-07：完全移除（--uninstall）

**目的**：驗證 `--uninstall` 清除 symlinks 和 CLAUDE.md，但保留 memory/
**對應需求**：FR-02-5

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（任意 Expert 已安裝） | |
| 2 | 手動建立記憶假資料：`mkdir -p .connsys-jarvis/memory/test && touch .connsys-jarvis/memory/test/note.md` | |
| 3 | `python3 ./connsys-jarvis/scripts/setup.py --uninstall` | 輸出「完成！保留 .../log/ 和 .../memory/」 |
| 4 | `ls CLAUDE.md 2>/dev/null \|\| echo "NOT FOUND"` | NOT FOUND |
| 5 | `ls .claude/skills/ \| wc -l` | 0 |
| 6 | `ls .claude/hooks/ \| wc -l` | 0 |
| 7 | `ls .connsys-jarvis/memory/test/note.md` | 存在（memory 保留） |

---

## TC-08：列出安裝狀態（--list）

**目的**：驗證 `--list` 顯示所有 Expert（已安裝 + 可用），以及 --format json 輸出
**對應需求**：FR-02-6, FR-02-19

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-02 完成後（2 Experts 已安裝） | |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --list` | 輸出 Expert 清單（已安裝 + 可用） |
| 3 | 確認已安裝 Expert 清單及 status | framework-base-expert status=installed, wifi-bora-memory-slim-expert status=installed ← identity |
| 4 | 確認可用但未安裝的 Expert 也顯示 | 其他掃描到的 Expert 標注 status=available |
| 5 | 確認 Skills 數量 | Skills (13): 全部 ✅ |
| 6 | 確認 Hooks 數量 | Hooks (5): 全部 ✅ |
| 7 | 確認 Commands 數量 | Commands (2): 全部 ✅ |
| 8 | `python3 ./connsys-jarvis/scripts/setup.py --list --format json` | 輸出合法 JSON array，含 status 欄位 |

---

## TC-09：Skill test-basic.sh 全部通過

**目的**：驗證所有 16 個 skill 的 test-basic.sh 執行無錯誤
**對應需求**：FR-04-6, FR-04-8

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | `find connsys-jarvis -name "test-basic.sh" \| sort` | 列出 16 個測試腳本 |
| 2 | 逐一執行每個 test-basic.sh | 各自輸出 Results: N passed, 0 failed |
| 3 | 統計總 PASS 數 | 41 PASS, 0 FAIL |

---

## TC-10：exclude_symlink patterns 過濾

**目的**：驗證 expert.json 的 exclude_symlink.patterns（regex）能正確過濾 symlinks
**對應需求**：FR-02-9, §4.3

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 暫時修改 wifi-bora-memory-slim-expert 的 expert.json，加入 `"exclude_symlink": {"patterns": [".*-lsp-.*"]}` | |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json` | 安裝成功 |
| 3 | `ls .claude/skills/ \| grep lsp` | 無結果（wifi-bora-lsp-tool 被過濾） |
| 4 | `ls .claude/skills/ \| grep memslim` | wifi-bora-memslim-flow 存在（未被過濾） |
| 5 | 還原 expert.json | `"exclude_symlink": {"patterns": []}` |

---

## TC-11：dangling symlink 偵測（--doctor）

**目的**：驗證 `--doctor` 能偵測失效的 symlink（dangling）
**對應需求**：FR-02-7

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後 | |
| 2 | 手動建立假 dangling symlink：`ln -s /nonexistent/path .claude/skills/fake-skill` | |
| 3 | `python3 ./connsys-jarvis/scripts/setup.py --doctor` | 輸出「❌ fake-skill → /nonexistent/path DANGLING」 |
| 4 | 確認總體狀態 | 非「✅ 健康」（有 dangling） |
| 5 | 刪除假 symlink：`rm .claude/skills/fake-skill` | 清理 |

---

## TC-12：pytest 單元測試（scripts/test/test_setup.py）

**目的**：驗證 `setup.py` 核心函式的單元測試全部通過，含環境變數生成、`--with-all-experts` 模式測試
**對應需求**：FR-02-17

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | `cd /Users/swchen.tw/git/testing/agents/connsys-jarvis` | 進入 jarvis 目錄 |
| 2 | `uvx pytest scripts/test/test_setup.py -v` | 執行所有 61 個測試 |
| 3 | 確認 `TestDetectScenario`（3 tests）| 3 passed |
| 4 | 確認 `TestGetCodespacePath`（2 tests）| 2 passed |
| 5 | 確認 `TestResolveItems`（6 tests）| 6 passed |
| 6 | 確認 `TestApplyExcludePatterns`（4 tests）| 4 passed |
| 7 | 確認 `TestGenerateClaudeMdSingle`（4 tests）| 4 passed |
| 8 | 確認 `TestGenerateClaudeMdMulti`（8 tests）含預設 identity-only（4）與 `--with-all-experts`（4）| 8 passed |
| 9 | 確認 `TestWriteEnvFile`（10 tests）含環境變數前綴 `CONNSYS_JARVIS_` 驗證 | 10 passed |
| 10 | 確認 `TestInstalledExpertsSchema`（3 tests）| 3 passed |
| 11 | 確認整合測試 `TestIntegrationInit/Add/Remove/Uninstall`（21 tests）| 21 passed |
| 12 | 最終輸出 | `61 passed in X.XXs` |

---

## TC-13：--with-all-experts 整合測試

**目的**：驗證 `--add --with-all-experts` 時 CLAUDE.md 包含所有 Expert 的 expert.md，且偏好儲存在 `.installed-experts.json`
**對應需求**：US-06, FR-05-2

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（framework-base-expert 已安裝）| |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --add --with-all-experts wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json` | 輸出「完成！Expert 'wifi-bora-memory-slim-expert' 已加入」 |
| 3 | `cat CLAUDE.md \| grep "2 Experts"` | 含「2 Experts 已安裝」count header |
| 4 | `cat CLAUDE.md \| grep "framework-base-expert/expert.md"` | 含 framework-base-expert/expert.md（Capabilities 區段）|
| 5 | `cat CLAUDE.md \| grep "wifi-bora-memory-slim-expert/soul.md"` | 含 wifi-bora-memory-slim-expert/soul.md（Identity 區段）|
| 6 | `cat CLAUDE.md \| grep "Expert Identity"` | 含 `## Expert Identity` 區段 header |
| 7 | `cat CLAUDE.md \| grep "Expert Capabilities"` | 含 `## Expert Capabilities` 區段 header |
| 8 | `python3 -c "import json; d=json.load(open('.connsys-jarvis/.installed-experts.json')); print(d['include_all_experts'])"` | `True` |

---

## TC-14：--debug 日誌測試

**目的**：驗證 `--debug` 開啟後 DEBUG 訊息寫入日誌檔，無 `--debug` 時日誌檔仍存在但 console 只顯示 WARNING+
**對應需求**：FR-02 (logging)

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（workspace 已建立）| |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --debug --init framework/experts/framework-base-expert/expert.json 2>&1 \| grep -c DEBUG` | console 輸出包含多行 DEBUG 訊息（> 0）|
| 3 | `ls .connsys-jarvis/log/setup.log` | 日誌檔案存在 |
| 4 | `grep -c DEBUG .connsys-jarvis/log/setup.log` | 日誌檔含多行 DEBUG 記錄（> 0）|
| 5 | `python3 ./connsys-jarvis/scripts/setup.py --init framework/experts/framework-base-expert/expert.json 2>&1 \| grep -c DEBUG \|\| echo 0` | console 無 DEBUG 輸出（輸出 0）|
| 6 | `ls .connsys-jarvis/log/setup.log` | 日誌檔仍存在（file handler 不受 --debug 影響）|

---

## TC-15：--query 指令

**目的**：驗證 `--query` 能即時查詢 Expert metadata
**對應需求**：FR-02-18

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（framework-base-expert 已安裝） | |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --query framework-base-expert` | 輸出 Expert 名稱、domain、status=installed、description、dependencies、internal |
| 3 | `python3 ./connsys-jarvis/scripts/setup.py --query wifi-bora-memory-slim-expert` | 輸出 status=available（若尚未安裝） |
| 4 | `python3 ./connsys-jarvis/scripts/setup.py --query memory-slim` | 部分名稱匹配，輸出 wifi-bora-memory-slim-expert |
| 5 | `python3 ./connsys-jarvis/scripts/setup.py --query nonexistent-expert` | 輸出 ERROR 訊息，exit code 1 |

---

## TC-16：--list --format json

**目的**：驗證 `--list --format json` 輸出供 LLM 使用的 JSON
**對應需求**：FR-02-19

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-02 完成後（2 Experts 已安裝） | |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --list --format json` | 輸出合法 JSON array |
| 3 | 解析 JSON，確認已安裝 Expert status="installed" | framework-base-expert status=installed |
| 4 | 解析 JSON，確認未安裝 Expert status="available" | 其他掃描到的 expert status=available |
| 5 | `python3 ./connsys-jarvis/scripts/setup.py --query framework-base-expert --format json` | 輸出合法 JSON object，含 dependencies、internal |

