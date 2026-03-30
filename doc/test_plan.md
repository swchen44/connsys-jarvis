# Connsys Jarvis — 測試計畫

**文件版本**：v1.7
**日期**：2026-03-30
**依據**：agents-requirements.md v3.6, agents-design.md v3.6
**變更說明**：
- v1.1 — setup.py 路徑改為 scripts/setup.py；新增 TC-12 pytest 單元測試
- v1.2 — 修正 TC-02 Step 6（預設 identity-only，無 count header）；更新 TC-12 測試數 57→61（含 --with-all-experts tests）；新增 TC-13（--with-all-experts 整合）、TC-14（--debug 日誌）
- v1.3 — TC-02 補充 Step 8、9（驗證 include_all_experts=false 及 install_order）；對齊需求書 FR-02-4 reference count 與 FR-02-8 dependencies/internal 定義
- v1.4 — 更新 TC-05（--remove 改全清再重建）；更新 TC-08（--list 顯示 installed+available，新增 --format json）；新增 TC-15（--query）、TC-16（--list --format json）
- v1.5 — TC-01 補充 Step 10（--init memory 保留驗證）；新增 TC-18（--reset 整合測試）
- v1.6 — TC-12 更新（三層金字塔架構，239 tests）；新增 TC-E01~E06（E2E subprocess 測試）
- v1.7 — TC-12 更新（unit 50 / integration 71 / e2e 18）；更新 TC-02 Step 6（Base Experts 區段）；更新 TC-13（Base Experts 區段說明）；新增 TC-19（Base Expert is_base=true 特殊規則）

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
| 3 | `cd /tmp/cj-test && python3 ./connsys-jarvis/scripts/setup.py --init framework/framework-base-expert/expert.json` | 輸出「完成！Expert 'framework-base-expert' 已安裝」 |
| 4 | `ls .claude/skills/` | 3 個 skills symlinks |
| 5 | `ls .claude/hooks/` | 5 個 hooks symlinks |
| 6 | `ls .claude/commands/` | 2 個 commands symlinks |
| 7 | `cat CLAUDE.md` | 含 @include soul.md, rules.md, duties.md, expert.md |
| 8 | `cat .connsys-jarvis/.env` | 含 CONNSYS_JARVIS_* 6 個變數 |
| 9 | `cat .connsys-jarvis/.installed-experts.json` | experts 陣列含 framework-base-expert |
| 10 | 手動建立記憶：`mkdir -p .connsys-jarvis/memory/test && echo "note" > .connsys-jarvis/memory/test/note.md`，再執行 `--init framework/framework-base-expert/expert.json` | .connsys-jarvis/memory/test/note.md **仍存在**（memory 不受 --init 影響） |

---

## TC-02：疊加安裝（--add）— wifi-bora-memory-slim-expert

**目的**：驗證 `--add` 跨 3 個 expert 的依賴解析、idempotent（已存在跳過）
**對應需求**：FR-02-3, FR-02-8, US-06

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（framework-base-expert 已安裝） | workspace 已有 framework-base-expert |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --add wifi-bora/wifi-bora-memory-slim-expert/expert.json` | 輸出「完成！Expert 'wifi-bora-memory-slim-expert' 已加入」 |
| 3 | 確認輸出含 `[=]`（既有跳過）| framework 的 3 skills + 5 hooks + 2 commands 顯示 `[=]` |
| 4 | 確認輸出含 `[+]`（新建） | wifi-bora 5 skills + sys-bora 2 skills + internal 3 skills |
| 5 | `ls .claude/skills/ \| wc -l` | 13 |
| 6 | `cat CLAUDE.md` | 預設格式：identity wifi-bora-memory-slim-expert 的 soul/rules/duties/expert.md，加上 `## Base Experts` 區段（framework-base-expert、wifi-bora-base-expert 等 is_base=true 的四份文件），**不含**「N Experts 已安裝」count header |
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
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --remove wifi-bora/wifi-bora-memory-slim-expert/expert.json` | 輸出「完成！Expert 'wifi-bora-memory-slim-expert' 已移除」 |
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
| 3 | `cd /tmp/cj-legacy && python3 ./connsys-jarvis/scripts/setup.py --init framework/framework-base-expert/expert.json` | 安裝成功 |
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
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --init wifi-bora/wifi-bora-memory-slim-expert/expert.json` | 安裝成功 |
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

## TC-12：pytest 三層測試架構（scripts/tests/）

**目的**：驗證三層測試金字塔（unit / integration / e2e）全部通過
**對應需求**：FR-02-17

### 架構說明

```
scripts/tests/
├── conftest.py          ← 共用 fixtures（所有層共用）
├── unit/                ← Layer 1：純函式邏輯（50 tests）
├── integration/         ← Layer 2：cmd_* 多模組協作（71 tests）
└── e2e/                 ← Layer 3：subprocess CLI 黑箱（18 tests）
```

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | `cd /Users/swchen.tw/git/testing/agents/connsys-jarvis` | 進入 jarvis 目錄 |
| 2 | `uvx pytest scripts/tests/unit/ -v` | `50 passed`（< 0.2s） |
| 3 | `uvx pytest scripts/tests/integration/ -v` | `71 passed`（< 1s） |
| 4 | `uvx pytest scripts/tests/e2e/ -v` | `18 passed`（< 3s） |
| 5 | `uvx pytest scripts/tests/ -v` | `139 passed` |
| 6 | 確認 unit/：TC-U01~U08 各類均 passed | 50 passed |
| 7 | 確認 integration/：TC-U09~U22 各類均 passed | 71 passed |
| 8 | 確認 e2e/：TC-E01~E06 各類均 passed | 18 passed |

---

## TC-13：--with-all-experts 整合測試

**目的**：驗證 `--add --with-all-experts` 時 CLAUDE.md 包含 Identity + Base Experts + Capabilities 三區段，且偏好儲存在 `.installed-experts.json`
**對應需求**：US-06, FR-05-2, FR-05-7, FR-05-8

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（framework-base-expert 已安裝）| |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --add --with-all-experts wifi-bora/wifi-bora-memory-slim-expert/expert.json` | 輸出「完成！Expert 'wifi-bora-memory-slim-expert' 已加入」 |
| 3 | `cat CLAUDE.md \| grep "2 Experts"` | 含「2 Experts 已安裝」count header |
| 4 | `cat CLAUDE.md \| grep "framework-base-expert/expert.md"` | 含 framework-base-expert/expert.md（Base Experts 區段，is_base=true）|
| 5 | `cat CLAUDE.md \| grep "wifi-bora-memory-slim-expert/soul.md"` | 含 wifi-bora-memory-slim-expert/soul.md（Identity 區段）|
| 6 | `cat CLAUDE.md \| grep "Expert Identity"` | 含 `## Expert Identity` 區段 header |
| 7 | `cat CLAUDE.md \| grep "Base Experts"` | 含 `## Base Experts` 區段 header |
| 8 | `cat CLAUDE.md \| grep "Expert Capabilities"` | 含 `## Expert Capabilities` 區段 header |
| 9 | `python3 -c "import json; d=json.load(open('.connsys-jarvis/.installed-experts.json')); print(d['include_all_experts'])"` | `True` |

---

## TC-14：--debug 日誌測試

**目的**：驗證 `--debug` 開啟後 DEBUG 訊息寫入日誌檔，無 `--debug` 時日誌檔仍存在但 console 只顯示 WARNING+
**對應需求**：FR-02 (logging)

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（workspace 已建立）| |
| 2 | `python3 ./connsys-jarvis/scripts/setup.py --debug --init framework/framework-base-expert/expert.json 2>&1 \| grep -c DEBUG` | console 輸出包含多行 DEBUG 訊息（> 0）|
| 3 | `ls .connsys-jarvis/log/setup.log` | 日誌檔案存在 |
| 4 | `grep -c DEBUG .connsys-jarvis/log/setup.log` | 日誌檔含多行 DEBUG 記錄（> 0）|
| 5 | `python3 ./connsys-jarvis/scripts/setup.py --init framework/framework-base-expert/expert.json 2>&1 \| grep -c DEBUG \|\| echo 0` | console 無 DEBUG 輸出（輸出 0）|
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

---

### TC-17：`--doctor` 增強（系統資訊 / 環境變數 / Symlink / CLAUDE.md / Expert 結構）

**測試目標**：驗證 --doctor 的 6 個診斷區段（A~F）均能正確偵測問題並給出修正建議。

**前置條件**：
- workspace 已安裝 framework-base-expert（TC-01 完成）
- workspace_mini fixture（pytest 用，可寫的 mini connsys-jarvis 結構）

| Step | 操作 | 驗收條件 |
|------|------|---------|
| 1 | `--doctor`（正常狀態） | 輸出 6 個區段標題（A~F）；總體狀態「✅ 健康」 |
| 2 | 區段 A | 輸出 OS、Python 版本、connsys-jarvis vX.X |
| 3 | 區段 B — 刪除 .env | 輸出「.env 不存在」+ `--init` 修正提示 |
| 4 | 區段 B — 路徑無效 | 輸出「路徑不存在」+ 具體路徑 |
| 5 | 區段 C — 刪除 symlink | 輸出「❌ [缺少]」+ 修正提示 |
| 6 | 區段 C — 新增 orphan symlink | 輸出「⚠️ [多餘]」+ 修正提示 |
| 7 | 區段 C — skill link 無 SKILL.md | 輸出「SKILL.md 不存在」|
| 8 | 區段 D — 刪除 CLAUDE.md | 輸出「CLAUDE.md 不存在」|
| 9 | 區段 D — 修改 CLAUDE.md（缺 include） | 輸出「缺少 @include」|
| 10 | 區段 D — 修改 CLAUDE.md（多 include） | 輸出「多餘 @include」|
| 11 | 區段 F1 — 刪除 soul.md | 輸出「soul.md」+ 缺少提示 |
| 12 | 區段 F2 — 刪除 owner 欄位 | 輸出「owner」|
| 13 | 區段 F2 — 刪除 internal.skills | 輸出「internal.skills」|
| 14 | 區段 F3 — skill 無 SKILL.md | 輸出「SKILL.md」|
| 15 | 區段 F4 — orphan skill folder | 輸出「未被任何 expert.json 引用」|

**pytest 覆蓋**：TC-U16（3）+ TC-U17（4）+ TC-U18（4）+ TC-U19（4）+ TC-U20（6）= 21 tests

---

## TC-18：完全重置（--reset）

**目的**：驗證 `--reset` 清除所有狀態，包含 memory/，僅保留 log/
**對應需求**：FR-02-27

### Steps

| # | 步驟 | 預期結果 |
|---|------|---------|
| 1 | 前置：TC-01 完成後（任意 Expert 已安裝） | |
| 2 | 手動建立記憶假資料：`mkdir -p .connsys-jarvis/memory/test && touch .connsys-jarvis/memory/test/note.md` | |
| 3 | 手動建立 log 假資料：`mkdir -p .connsys-jarvis/log && touch .connsys-jarvis/log/setup.log` | |
| 4 | `python3 ./connsys-jarvis/scripts/setup.py --reset` | 輸出「Done! All state removed. Kept .../log/ only.」 |
| 5 | `ls CLAUDE.md 2>/dev/null \|\| echo "NOT FOUND"` | NOT FOUND |
| 6 | `ls .claude/skills/ \| wc -l` | 0 |
| 7 | `ls .claude/hooks/ \| wc -l` | 0 |
| 8 | `ls .connsys-jarvis/.installed-experts.json 2>/dev/null \|\| echo "NOT FOUND"` | NOT FOUND |
| 9 | `ls .connsys-jarvis/.env 2>/dev/null \|\| echo "NOT FOUND"` | NOT FOUND |
| 10 | `ls .connsys-jarvis/memory/ 2>/dev/null \|\| echo "NOT FOUND"` | NOT FOUND（memory 已刪除，與 --uninstall 差異）|
| 11 | `ls .connsys-jarvis/log/setup.log` | 存在（log 保留）|

**與 TC-07（--uninstall）的關鍵差異**：Step 10 memory/ 應為 NOT FOUND；TC-07 Step 7 memory/ 應存在。

**pytest 覆蓋**：新增 TC-U21（--reset 整合）= 5 tests

---

## TC-E01~E06：E2E 端對端測試（scripts/tests/e2e/）

**目的**：透過 `subprocess.run()` 模擬真實使用者 CLI 操作，從指令入口到最終檔案系統狀態，驗證整個系統的組合行為
**對應需求**：FR-02-17
**特性**：不 import setup.py，完全黑箱；驗證 returncode、stdout 關鍵字、檔案系統狀態

| TC | 測試類 | 場景 | 測試數 |
|----|--------|------|--------|
| TC-E01 | `TestE2EInit` | `--init` CLI 完整流程（exit code / env hint / symlinks）| 6 |
| TC-E02 | `TestE2EAdd` | `--add` CLI 流程（exit code / skill count）| 2 |
| TC-E03 | `TestE2EUninstall` | `--uninstall` CLI 流程（exit code / memory 保留）| 3 |
| TC-E04 | `TestE2EReset` | `--reset` CLI 流程（exit code / memory 刪除 / log 保留）| 4 |
| TC-E05 | `TestE2EList` | `--list --format json` 輸出驗證 | 2 |
| TC-E06 | `TestE2EMultiExpertWorkflow` | init→add→list→remove 完整工作流 | 1 |

**合計 E2E**：18 tests

**執行**：
```bash
uvx pytest scripts/tests/e2e/ -v   # ~1.3s
```

---

## TC-19：Base Expert is_base=true 特殊規則

**目的**：驗證 `is_base=true` 的 Expert（包含直接安裝及依賴樹中的 Expert）其四份文件必須出現在 CLAUDE.md 的 `## Base Experts` 區段
**對應需求**：FR-05-7, FR-05-8

### 測試情境

| # | 情境 | 驗證重點 |
|---|------|---------|
| 1 | 安裝單個 `is_base=true` Expert 作為 identity | 四份文件在主區段，無 Base Experts 區段（identity 不重複）|
| 2 | 安裝 `is_base=true` Expert（非 identity）+ identity | Base Experts 區段含其四份文件 |
| 3 | 安裝 identity，其 dependency 有 `is_base=true` Expert | dependency 的四份文件出現在 Base Experts 區段 |
| 4 | 依賴鏈：A → B（is_base=true）→ C（is_base=true）→ D（is_base=false）| B 和 C 的四份文件均在 Base Experts 區段；D 不出現 |
| 5 | Diamond dependency（兩個 Expert 共用同一 Base Expert）| Base Expert 只出現一次（DFS visited 去重）|

### pytest 覆蓋

| 測試類 | 場景 | 測試數 |
|--------|------|--------|
| `TestCollectBaseExperts` | DFS 遍歷、去重、遞迴依賴 | 6 |
| `TestGenerateClaudeMdMulti`（擴充）| Base Experts 區段、4 檔案驗證、--with-all-experts 模式 | 4 |

**合計**：10 tests（均在 unit 層）
