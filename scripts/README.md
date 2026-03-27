# scripts/setup.py — 開發者指南

本文件幫助你快速理解 `setup.py` 的設計、開發流程與驗證方法。
閱讀時間：約 15 分鐘。

---

## 目錄

1. [快速上手](#1-快速上手)
2. [設計概覽](#2-設計概覽)
3. [核心概念詳解](#3-核心概念詳解)
4. [程式碼導讀](#4-程式碼導讀)
5. [開發方法](#5-開發方法)
6. [Debug 與日誌](#6-debug-與日誌)
7. [驗證方法](#7-驗證方法)
8. [常見錯誤排查](#8-常見錯誤排查)

---

## 1. 快速上手

### 需求

- Python 3.8+（setup.py 本身）
- `uv` 或 `uvx`（執行 PEP 723 inline script 與測試）
- macOS / Linux（Windows 在 symlink 受限環境下自動降級為 copy 模式）

### 最小執行範例

```bash
# 進入你的 workspace
cd /path/to/workspace

# connsys-jarvis 必須在 workspace 內（或以 symlink 存在）
ln -s /path/to/connsys-jarvis ./connsys-jarvis   # 若尚未建立

# 安裝一個 Expert
python ./connsys-jarvis/scripts/setup.py \
    --init framework/experts/framework-base-expert/expert.json

# 讓環境變數生效（每次安裝後需要）
source .connsys-jarvis/.env

# 確認安裝健康
python ./connsys-jarvis/scripts/setup.py --doctor
```

### 所有指令一覽

| 指令 | 說明 |
|------|------|
| `--init <expert.json>` | 全新安裝（清除既有，重建） |
| `--add <expert.json>` | 疊加安裝（預設：CLAUDE.md 只含最後 Expert）；重複 --add = 重新安裝 |
| `--add <expert.json> --with-all-experts` | 疊加安裝（CLAUDE.md 包含所有 Expert 的 expert.md） |
| `--remove <name or path>` | 移除指定 Expert（全清再重建剩餘 Expert symlinks） |
| `--uninstall` | 完全卸載（保留 memory/） |
| `--list` | 列出所有 Expert（已安裝 + 可用），即時掃描，不依賴 registry.json |
| `--list --format json` | 同上，JSON 格式輸出（供 LLM / skill 使用） |
| `--query <expert-name>` | 查詢指定 Expert 的完整 metadata（支援部分名稱匹配） |
| `--query <expert-name> --format json` | 同上，JSON 格式輸出 |
| `--doctor` | 健康診斷（系統資訊 / 環境變數 / symlink / CLAUDE.md / Expert 結構完整性） |
| `--debug <任何指令>` | 開啟 debug 日誌 |

---

## 2. 設計概覽

### 核心職責

```
setup.py
    │
    ├─ 讀取 expert.json（宣告此 expert 需要哪些 skills/hooks/commands）
    ├─ 在 workspace/.claude/ 建立 symlinks（指向 connsys-jarvis repo 中的實際資料夾）
    ├─ 生成 workspace/CLAUDE.md（Claude Code 啟動時載入的 context）
    ├─ 生成 .connsys-jarvis/.env（6 個 CONNSYS_JARVIS_* 環境變數）
    └─ 維護 .connsys-jarvis/.installed-experts.json（安裝狀態持久化）
```

### 資料夾關係圖

```
workspace/                          ← cwd（使用者執行指令的地方）
├── connsys-jarvis/                 ← git repo（或 symlink 指向 repo）
│   ├── scripts/
│   │   ├── setup.py              ← 本程式
│   │   └── test/test_setup.py   ← pytest 單元測試
│   ├── framework/experts/framework-base-expert/
│   │   ├── expert.json            ← Expert 宣告（被 setup.py 讀取）
│   │   ├── skills/                ← skill 子目錄
│   │   └── hooks/                 ← hook 腳本（.sh / .py）
│   └── (no registry.json)         ← Expert 清單由 setup.py 即時掃描產生
│
├── .claude/                        ← Claude Code 讀取的設定目錄
│   ├── skills/
│   │   └── framework-expert-discovery-knowhow → ../../connsys-jarvis/...  ← symlink
│   ├── hooks/
│   │   └── session-start.sh → ../../connsys-jarvis/...  ← symlink
│   └── commands/
│
├── .connsys-jarvis/                ← runtime 資料（.gitignore 排除）
│   ├── .env                        ← 環境變數（需手動 source）
│   ├── .installed-experts.json    ← 安裝狀態持久化
│   ├── log/install.log            ← debug log 檔
│   └── memory/                    ← AI 記憶資料（--uninstall 時保留）
│
└── CLAUDE.md                       ← Claude Code 載入的主要 context
```

### 設計原則

| 原則 | 說明 |
|------|------|
| **Pure stdlib** | 無第三方依賴，`python3 script.py` 即可執行 |
| **cwd = workspace** | workspace 定義為執行指令時的 cwd，不跟隨 symlink |
| **冪等性** | 重複執行相同指令結果相同，`[=]` 代表跳過已存在的 symlink；`--add` 重複 = 重新安裝 |
| **不依賴 registry.json** | Expert 探索（`--list`/`--query`）每次即時掃描 `*/experts/*/expert.json` |
| **保護記憶** | `--uninstall` 不刪 memory/，避免使用者知識損失 |
| **分離設定** | setup.py 不修改 settings.json（由 setup-claude.sh 負責）|

---

## 3. 核心概念詳解

### 3.1 expert.json 格式

```json
{
  "name": "wifi-bora-memory-slim-expert",
  "display_name": "WiFi Bora Memory Slim Expert",
  "domain": "wifi-bora",
  "owner": "wifi-team",
  "version": "1.0.0",
  "dependencies": [
    {
      "expert": "framework/experts/framework-base-expert",
      "skills": "all",
      "hooks": "all",
      "commands": ["framework-experts-tool"]
    },
    {
      "expert": "wifi-bora/experts/wifi-bora-base-expert",
      "skills": ["wifi-bora-build-flow", "wifi-bora-arch-knowhow"]
    }
  ],
  "internal": {
    "skills": ["wifi-bora-memslim-flow", "wifi-bora-ast-tool"],
    "hooks": []
  },
  "exclude_symlink": {
    "patterns": []
  }
}
```

**dependencies[].skills spec 對照**：

| spec 值 | 結果 |
|---------|------|
| `"all"` | 繼承該 expert 的全部 skills |
| `["all"]` | 同上（陣列格式） |
| `["foo", "bar"]` | 只繼承 foo 和 bar |
| 省略 key | 不繼承（空集合）|

### 3.2 三步驟 Symlink 建立邏輯

```
build_symlinks_for_expert()
    │
    ├─ Step 1: Dependencies
    │   for dep in dependencies[]:
    │       解析 dep.skills / dep.hooks / dep.commands → item 清單
    │       套用 exclude_patterns 過濾
    │       加入 symlink_map（後加入者可覆蓋同名）
    │
    ├─ Step 2: Internal
    │   解析 internal.skills / internal.hooks
    │   套用 exclude_patterns
    │   加入 symlink_map（覆蓋 dependency 的同名項目）
    │
    └─ Step 3: exclude_symlink（已在 Step 1/2 中套用）
        全域 regex 過濾，跨所有 dependency/internal 統一移除
```

**為什麼後加入者覆蓋**：internal 可以提供比 dependency 更精確的版本。
例如 dependency 的 `"skills": "all"` 包含了 skill-A，但 internal 也聲明
了 skill-A（指向不同路徑），後者會覆蓋前者。

### 3.3 --remove 邏輯（全清再重建）

```
移除 wifi-bora-memory-slim-expert 時：

已安裝：[framework-base-expert, wifi-bora-memory-slim-expert]
移除後剩餘：[framework-base-expert]

Step 1 — 全清：移除 .claude/ 下所有 symlinks（不論哪個 expert 聲明）
Step 2 — 重建：依剩餘 experts（framework-base-expert）的 declared_symlinks 重新建立

  framework-expert-discovery-knowhow  [+] 重建
  framework-handoff-flow              [+] 重建
  session-start.sh                    [+] 重建
  wifi-bora-memslim-flow              ← 不再重建（wifi-bora 已移除）
  wifi-bora-lsp-tool                  ← 不再重建
```

**為何改為全清再重建**：
- 設計更簡單，與 `--init` 邏輯一致
- 避免 reference counting 在複雜依賴下計算錯誤的風險
- 結果可預測：移除後的狀態等同「只安裝剩餘 experts」的全新安裝

### 3.4 Workspace 偵測（Agent First vs Legacy）

```python
detect_scenario(workspace):
    if (workspace / ".repo").exists():   → "legacy"   # Android repo tool 的標誌
    else:                                → "agent-first"

get_codespace_path(workspace):
    legacy:      CODE_SPACE_PATH = workspace          # code 在 workspace root
    agent-first: CODE_SPACE_PATH = workspace/codespace  # code 在子目錄
```

### 3.5 CLAUDE.md 生成格式

**單一 Expert**（最常見）：
```markdown
# Consys Expert: WiFi Bora Memory Slim Expert

@connsys-jarvis/wifi-bora/experts/.../soul.md
@connsys-jarvis/wifi-bora/experts/.../rules.md
@connsys-jarvis/wifi-bora/experts/.../duties.md
@connsys-jarvis/wifi-bora/experts/.../expert.md

@CLAUDE.local.md
```

**多 Expert**（--add 後）：
```markdown
# Consys Experts（2 Experts 已安裝）

## Expert Identity（以最後安裝的 Expert 為主）
@connsys-jarvis/.../soul.md
@connsys-jarvis/.../rules.md
@connsys-jarvis/.../duties.md

## Expert Capabilities
@connsys-jarvis/framework/.../expert.md
@connsys-jarvis/wifi-bora/.../expert.md

@CLAUDE.local.md
```

### 3.6 --doctor 診斷架構

`--doctor` 依序執行 6 個診斷區段，每個區段獨立輸出問題與修正建議：

```
cmd_doctor(workspace)
    │
    ├─ A. 系統資訊        OS / Python / SETUP_VERSION
    ├─ B. 環境變數        parse_env_file() → 驗證 REQUIRED_ENV_VARS + PATH_ENV_VARS
    ├─ C. Symlink 完整性  declared_symlinks（installed JSON） vs .claude/ 現況
    │     ├─ missing：expected 有但 .claude/ 沒有
    │     ├─ orphan： .claude/ 有但 expected 沒有
    │     ├─ dangling：symlink 存在但 target 不存在
    │     └─ skill link SKILL.md：.claude/skills/*/SKILL.md 存在性
    ├─ D. CLAUDE.md      generate_claude_md() 預期 vs 實際 @include 行
    ├─ E. 環境工具        shutil.which("uv") / shutil.which("uvx")
    └─ F. Expert 結構     掃描 jarvis_dir.glob("*/experts/*/")
          ├─ F1 必要檔案：expert.json, expert.md, rules.md, duties.md, soul.md
          ├─ F2 必要欄位：name, domain, owner, internal.skills（collect via json.loads）
          ├─ F3 Skill SKILL.md：glob("*/experts/*/skills/*/") 各 folder 有 SKILL.md
          └─ F4 Orphan skill：collect_skill_references() 計算未被引用的 skill folder
```

**設計原則**：
- 所有區段都使用現有函式（`parse_env_file`、`generate_claude_md`、`collect_skill_references`），不重複邏輯
- 只讀不寫：`--doctor` 是純診斷指令，不修改任何檔案
- Section C 依賴 `declared_symlinks`（已儲存在 `.installed-experts.json`），不重跑 `build_symlinks_for_expert()`

### 新增 doctor 檢查項目

以新增「驗證 CLAUDE.local.md 存在」為例：

```python
# 在 cmd_doctor() 的 D 區段末尾加入：
local_md = workspace / "CLAUDE.local.md"
if not local_md.exists():
    print(f"  ⚠️  CLAUDE.local.md 不存在（可選，但建議建立）")
    print(f"     → 修正：touch CLAUDE.local.md")
```

規則：
1. 問題用 `❌`（影響功能）或 `⚠️`（警告）標示
2. 每個 ❌/⚠️ 後面緊接「→ 修正：」行
3. 影響 `all_ok` 的問題（❌）才設 `all_ok = False`；純警告（⚠️）可依嚴重性決定

---

## 4. 程式碼導讀

### 函式呼叫關係圖

```
main()
├── setup_logging()          ← 設定 console + file handler
├── find_workspace()         ← 回傳 Path.cwd()
│
├── cmd_init()
│   ├── load_expert_json()
│   ├── clear_claude_symlinks()
│   ├── build_symlinks_for_expert()
│   │   ├── resolve_items()          ← 解析 spec ("all" / list / None)
│   │   └── apply_exclude_patterns() ← regex 過濾
│   ├── apply_symlinks()
│   │   └── create_symlink()         ← 冪等，returns "created"/"exists"/"error"
│   ├── make_expert_entry()
│   ├── save_installed_experts()
│   ├── write_claude_md()
│   │   └── generate_claude_md()     ← 單/多 Expert 格式
│   └── write_env_file()             ← 6 個 CONNSYS_JARVIS_* 變數
│
├── cmd_add()                ← 類似 init，但保留既有 experts
├── cmd_remove()             ← 全清再重建邏輯
├── cmd_uninstall()          ← 清除但保留 memory/
├── cmd_list()               ← 唯讀顯示
└── cmd_doctor()             ← 唯讀健康檢查
```

### 關鍵函式速查

| 函式 | 所在行（約） | 說明 |
|------|------------|------|
| `setup_logging()` | ~88 | 設定 console/file handler |
| `find_workspace()` | ~150 | 回傳 cwd（workspace 偵測） |
| `detect_scenario()` | ~190 | agent-first vs legacy |
| `resolve_items()` | ~240 | 解析 "all"/list/None spec |
| `apply_exclude_patterns()` | ~280 | regex 全域過濾 |
| `build_symlinks_for_expert()` | ~520 | 三步驟核心邏輯 |
| `generate_claude_md()` | ~680 | 生成 CLAUDE.md 內容 |
| `write_env_file()` | ~805 | 寫入 6 個環境變數 |
| `parse_env_file()` | ~855 | 解析 .env，回傳 {key:value}（供 cmd_doctor B 區段）|
| `collect_skill_references()` | ~880 | 收集 skill 引用集合（供 cmd_doctor F4 orphan 檢查）|
| `cmd_init()` | ~930 | --init 實作 |
| `cmd_add()` | ~1010 | --add 實作 |
| `cmd_remove()` | ~1080 | --remove 全清再重建 |
| `cmd_uninstall()` | ~1180 | 清除但保留 memory/ |
| `cmd_list()` | ~1230 | 列出所有 Expert（installed + available）|
| `cmd_query()` | ~1310 | 查詢指定 Expert metadata |
| `scan_available_experts()` | ~1350 | 即時掃描所有可用 Expert（無 registry.json）|
| `cmd_doctor()` | ~1390 | 6 區段健康診斷（A~F）|

---

## 5. 開發方法

### 5.1 新增 CLI 指令

以新增 `--update-registry` 為例：

```python
# 1. 在 Commands 區塊加入 cmd_update_registry()
def cmd_update_registry(workspace: Path) -> None:
    """更新 registry.json。"""
    logger.info("cmd_update_registry: workspace=%s", workspace)
    # ... 實作 ...

# 2. 在 main() 的分派區塊加入
elif cmd == "--update-registry":
    cmd_update_registry(workspace)

# 3. 在 print_usage() 加入說明
```

### 5.2 新增 expert.json 欄位支援

以新增 `"post_install_script"` 為例：

```python
# 在 cmd_init() 的最後加入：
post_script = expert_data.get("post_install_script")
if post_script:
    script_path = expert_json_path.parent / post_script
    logger.info("cmd_init: running post_install_script: %s", script_path)
    subprocess.run([str(script_path)], cwd=workspace, check=True)
```

### 5.3 修改 Symlink 建立邏輯

所有 symlink 建立邏輯集中在 `build_symlinks_for_expert()`。
修改時注意：
- Step 1（dependencies）和 Step 2（internal）都呼叫同一個 `add_items_for_kind()`
- 過濾邏輯在 `apply_exclude_patterns()`
- 後加入者覆蓋是透過 `symlink_map` dict 的 key 覆蓋實現

### 5.4 修改環境變數

所有環境變數在 `write_env_file()` 中定義。
**重要**：新增變數時必須：
1. 使用 `CONNSYS_JARVIS_` 前綴
2. 在 `test_setup.py` 的 `TestWriteEnvFile` 加入對應測試

### 5.5 本地快速開發迴圈

```bash
# 建立測試 workspace
mkdir /tmp/cj-dev && cd /tmp/cj-dev
ln -s /path/to/connsys-jarvis ./connsys-jarvis

# 修改 setup.py 後立即測試
python ./connsys-jarvis/scripts/setup.py --debug --init \
    framework/experts/framework-base-expert/expert.json

# 查看 debug log
cat .connsys-jarvis/log/install.log

# 清理後重試
python ./connsys-jarvis/scripts/setup.py --uninstall
```

---

## 6. Debug 與日誌

### 6.1 啟用 Debug 模式

```bash
# --debug 可放在任何位置
python ./connsys-jarvis/scripts/setup.py --debug --init expert.json
python ./connsys-jarvis/scripts/setup.py --init expert.json --debug
```

**Debug 模式效果**：
- Console（stderr）輸出 DEBUG 層級訊息，顯示每個步驟的詳細狀態
- 同時寫入 `.connsys-jarvis/log/setup.log`

### 6.2 日誌格式說明

```
2026-03-26T08:00:00Z [DEBUG  ] cmd_init:443 - workspace=/tmp/cj-test
2026-03-26T08:00:01Z [INFO   ] cmd_init:462 - Step 3 - building symlinks
2026-03-26T08:00:01Z [WARNING] build_symlinks:310 - dep dir not found: ...
2026-03-26T08:00:01Z [ERROR  ] create_symlink:350 - failed for ...: Permission denied
```

| 欄位 | 說明 |
|------|------|
| timestamp | UTC ISO 8601 |
| level | DEBUG/INFO/WARNING/ERROR，補空格對齊 |
| funcName:lineno | 發出 log 的函式與行號 |
| message | 詳細訊息 |

### 6.3 Log 層級使用規範

| 層級 | 使用時機 | 範例 |
|------|----------|------|
| `DEBUG` | 每個小步驟的詳細狀態 | `logger.debug("create_symlink: %s → %s", link, target)` |
| `INFO` | 主要步驟開始/完成 | `logger.info("cmd_init: Step 3 - building symlinks")` |
| `WARNING` | 非致命問題（安裝繼續）| `logger.warning("dep dir not found: %s", path)` |
| `ERROR` | 致命錯誤（通常後接 sys.exit）| `logger.error("expert.json not found: %s", path)` |

### 6.4 永久 Log 檔

不論是否加 `--debug`，所有 DEBUG+ 訊息都會寫入：

```
.connsys-jarvis/log/install.log
```

事後追查問題時：

```bash
# 查看最後 50 行
tail -50 .connsys-jarvis/log/install.log

# 搜尋 WARNING 以上
grep -E '\[WARNING|ERROR\]' .connsys-jarvis/log/install.log

# 搜尋特定函式的 log
grep 'cmd_remove' .connsys-jarvis/log/install.log
```

---

## 7. 驗證方法

### 7.1 Unit Test（pytest）

```bash
# 從 connsys-jarvis 目錄執行
cd /path/to/connsys-jarvis
uvx pytest scripts/test/test_setup.py -v

# 執行特定測試類
uvx pytest scripts/test/test_setup.py::TestWriteEnvFile -v
uvx pytest scripts/test/test_setup.py::TestIntegrationInit -v

# 若無 uvx，用 uv run
uv run --with pytest pytest scripts/test/test_setup.py -v
```

**測試涵蓋的函式與場景**：

| 測試類 | 涵蓋函式 | 重點 |
|--------|----------|------|
| `TestDetectScenario` | `detect_scenario()` | .repo 偵測 |
| `TestGetCodespacePath` | `get_codespace_path()` | agent-first vs legacy 路徑 |
| `TestResolveItems` | `resolve_items()` | "all"/list/None 三種 spec |
| `TestApplyExcludePatterns` | `apply_exclude_patterns()` | regex 過濾邏輯 |
| `TestGenerateClaudeMdSingle` | `generate_claude_md()` | 單 Expert 格式 |
| `TestGenerateClaudeMdMulti` | `generate_claude_md()` | 多 Expert 格式，含 --with-all-experts |
| `TestWriteEnvFile` | `write_env_file()` | 6 個環境變數，含前綴驗證 |
| `TestInstalledExpertsSchema` | `save/load_installed_experts()` | JSON 讀寫 roundtrip |
| `TestIntegrationInit` | `cmd_init()` | 完整 init 流程 |
| `TestIntegrationAdd` | `cmd_add()` | 冪等疊加安裝 |
| `TestIntegrationRemove` | `cmd_remove()` | 全清再重建 |
| `TestIntegrationUninstall` | `cmd_uninstall()` | 保留 memory/ |
| `TestScanAvailableExperts` | `scan_available_experts()` | 即時掃描，fields 驗證 |
| `TestCmdQuery` | `cmd_query()` | 安裝狀態、JSON 格式、部分匹配 |
| `TestCmdListUpdated` | `cmd_list()` | available experts、JSON 格式 |
| `TestDoctorSystemInfo` | `cmd_doctor()` A 區段 | OS / Python / version 顯示 |
| `TestDoctorEnvVars` | `cmd_doctor()` B 區段 + `parse_env_file()` | 6 vars 驗證、缺失偵測 |
| `TestDoctorSymlinkIntegrity` | `cmd_doctor()` C 區段 | missing/orphan/SKILL.md |
| `TestDoctorClaudeMd` | `cmd_doctor()` D 區段 | @include 對比 |
| `TestDoctorExpertStructure` | `cmd_doctor()` F 區段 + `collect_skill_references()` | F1~F4 結構驗證 |

### 7.2 手動整合測試（tmux）

參考 `test_plan.md` TC-01 ~ TC-12 的步驟，以下是快速驗證腳本：

```bash
# 建立乾淨 workspace
rm -rf /tmp/cj-test && mkdir /tmp/cj-test
ln -s /path/to/connsys-jarvis /tmp/cj-test/connsys-jarvis
cd /tmp/cj-test

# TC-01: --init
python ./connsys-jarvis/scripts/setup.py \
    --init framework/experts/framework-base-expert/expert.json
ls .claude/skills/ | wc -l   # 預期: 3
ls .claude/hooks/  | wc -l   # 預期: 5
ls .claude/commands/ | wc -l  # 預期: 2

# TC-02: --add
python ./connsys-jarvis/scripts/setup.py \
    --add wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json
ls .claude/skills/ | wc -l   # 預期: 13

# TC-03: --doctor
python ./connsys-jarvis/scripts/setup.py --doctor
# 預期最後一行: 總體狀態：✅ 健康

# TC-05: --remove
python ./connsys-jarvis/scripts/setup.py \
    --remove wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json
ls .claude/skills/ | wc -l   # 預期: 3

# TC-07: --uninstall
python ./connsys-jarvis/scripts/setup.py --uninstall
ls CLAUDE.md 2>/dev/null || echo "GONE"   # 預期: GONE
ls .claude/skills/ | wc -l                # 預期: 0
```

### 7.3 Debug 模式驗證

```bash
cd /tmp/cj-test

# 開啟 debug 看詳細流程
python ./connsys-jarvis/scripts/setup.py --debug \
    --init framework/experts/framework-base-expert/expert.json 2>&1 | head -30

# 確認 log 檔寫入
ls -la .connsys-jarvis/log/setup.log
tail -20 .connsys-jarvis/log/setup.log
```

### 7.4 Skill test-basic.sh 驗證

每個 skill 目錄下有 `test/test-basic.sh`，可獨立執行：

```bash
# 執行單一 skill 測試
bash connsys-jarvis/framework/experts/framework-base-expert/skills/\
framework-expert-discovery-knowhow/test/test-basic.sh

# 執行所有 skill 測試
find connsys-jarvis -name "test-basic.sh" | sort | while read f; do
    echo "--- $f ---"
    bash "$f"
done
# 預期: 16 個腳本，41 個 checks，全部 PASS
```

---

## 8. 常見錯誤排查

### Q: `ERROR: expert.json not found`

```bash
# setup.py 的搜尋順序:
# 1. workspace/expert_json_rel
# 2. workspace/connsys-jarvis/expert_json_rel

# 確認路徑存在
ls ./connsys-jarvis/framework/experts/framework-base-expert/expert.json

# 確認 cwd 是 workspace root（不是 connsys-jarvis 子目錄）
pwd  # 應顯示 workspace root
```

### Q: Symlink 建立後 `--doctor` 顯示 DANGLING

```bash
# 通常因為 connsys-jarvis 路徑改變（例如重新 clone）
# 重新執行 --init 重建所有 symlinks
python ./connsys-jarvis/scripts/setup.py \
    --init <your-expert.json>
```

### Q: `source .connsys-jarvis/.env` 後環境變數仍不對

```bash
# 確認 .env 內容
cat .connsys-jarvis/.env

# 確認 CONNSYS_JARVIS_PATH 指向正確位置
echo $CONNSYS_JARVIS_PATH
ls $CONNSYS_JARVIS_PATH/scripts/setup.py  # 應存在
```

### Q: `--remove` 找不到 Expert

```bash
# 確認安裝狀態
python ./connsys-jarvis/scripts/setup.py --list

# --remove 接受兩種格式：
# 1. Expert 名稱（建議）
python ./connsys-jarvis/scripts/setup.py --remove wifi-bora-memory-slim-expert
# 2. expert.json 路徑
python ./connsys-jarvis/scripts/setup.py \
    --remove wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json
```

### Q: 測試失敗（pytest）

```bash
# 開啟 pytest 的詳細輸出
uvx pytest scripts/test/test_setup.py -v -s

# 只執行失敗的測試
uvx pytest scripts/test/test_setup.py -v --last-failed

# 查看詳細 log（測試使用 tmp_path，不影響真實 workspace）
uvx pytest scripts/test/test_setup.py -v --tb=long
```

### Q: `--doctor` 顯示 env var `路徑不存在`

```bash
# 確認 .env 內容與實際路徑
cat .connsys-jarvis/.env

# 最常見原因：connsys-jarvis 路徑改變（重新 clone 或移動）
# 重新執行 --init 以重建 .env
python ./connsys-jarvis/scripts/setup.py \
    --init <your-expert.json>
```

### Q: `--doctor` 顯示 CLAUDE.md `缺少 @include`

```bash
# CLAUDE.md 被手動編輯或安裝後損壞
# 重新執行 --init 或 --add 重新生成 CLAUDE.md
python ./connsys-jarvis/scripts/setup.py \
    --init <your-expert.json>
```

### Q: `--doctor` 顯示 expert.json `缺少欄位：owner`

```bash
# expert.json 格式要求：必須有 name, domain, owner, internal.skills
# 編輯 expert.json 補充缺少的欄位：
{
  "name":   "your-expert",
  "domain": "your-domain",
  "owner":  "your-team",
  ...
  "internal": { "skills": [], "hooks": [] }
}
```

### Q: `--doctor` 顯示 `orphan skill`

```bash
# skill folder 存在但沒有被任何 expert.json 引用
# 選項 1：加入某個 expert.json 的 internal.skills：
#   "internal": { "skills": ["orphan-skill-name"], ... }
# 選項 2：刪除此 skill folder（確認不需要後）
```

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `doc/agents-requirements.md` | 功能需求（FR-02 系列） |
| `doc/agents-design.md` | 系統設計（§5 setup.py 設計） |
| `doc/test_plan.md` | 測試計畫（TC-01~TC-12） |
| `doc/test_report.md` | 測試報告（測試結果記錄） |
| `scripts/test/test_setup.py` | pytest 單元測試（102 tests，含 TC-U16~TC-U20）|
