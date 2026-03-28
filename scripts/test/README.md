# connsys-jarvis 測試架構

## 設計精神：測試金字塔

```
        ▲
       /E2E\        ← 18 tests  慢但最接近真實使用
      /─────\
     /  Integ\      ← 73 tests  中速，驗證模組協作
    /──────────\
   /    Unit    \   ← 38 tests  快速，純邏輯驗證
  ──────────────────
```

**越底層越快、越多；越上層越慢、越少。** 三層互補：

- **Unit**：快速反饋，確認單一函式邏輯正確
- **Integration**：確認多個函式組合運作正確（cmd_init 是否真的建立 symlink？）
- **E2E**：確認「各模組沒問題但組合起來可能壞掉」的場景，從 CLI 入口跑到底

## 資料夾結構

```
scripts/test/
├── README.md                       ← 本文件
├── conftest.py                     ← 共用 fixtures（所有層自動載入）
│
├── unit/                           ← Layer 1：單元測試
│   ├── __init__.py
│   └── test_unit.py                ← TC-U01~U08（38 tests）
│
├── integration/                    ← Layer 2：整合測試
│   ├── __init__.py
│   ├── conftest.py                 ← build_mini_jarvis helper
│   └── test_integration.py        ← TC-U09~U22（73 tests）
│
├── e2e/                            ← Layer 3：端對端測試
│   ├── __init__.py
│   └── test_e2e.py                 ← TC-E01~E06（18 tests）
│
├── test_setup.py                   ← 舊版 monolith（110 tests，向後相容）
└── run_integration_tests.sh        ← bash 手動整合驗證腳本
```

### 各層說明

#### Unit（`unit/test_unit.py`）

- **測試對象**：單一 function / method，不依賴多模組協作
- **不碰磁碟**（除少量 tmp_path 建立目錄結構外），不呼叫 cmd_* 函式
- **速度**：~0.1s
- **涵蓋**：`detect_scenario`、`get_codespace_path`、`resolve_items`、`apply_exclude_patterns`、`generate_claude_md`、`write_env_file`、`load/save_installed_experts`

#### Integration（`integration/test_integration.py`）

- **測試對象**：呼叫 cmd_* 函式，驗證多模組協作的實際結果
- **使用 tmp_path**：驗證 symlink / JSON / CLAUDE.md 確實被正確建立或刪除
- **速度**：~0.4s
- **涵蓋**：`cmd_init/add/remove/uninstall/reset`、`scan_available_experts`、`cmd_query/list`、`cmd_doctor`（A~F 區段）
- `integration/conftest.py` 提供 `build_mini_jarvis()` helper 和 `mini_workspace` fixture，供 doctor 結構測試使用

#### E2E（`e2e/test_e2e.py`）

- **測試對象**：透過 `subprocess.run()` 呼叫 `setup.py` CLI，完全黑箱
- **驗證**：returncode、stdout 關鍵字、最終檔案系統狀態
- **速度**：~1.3s（subprocess 啟動開銷）
- **涵蓋**：`--init`、`--add`、`--uninstall`、`--reset`、`--list --format json`、完整多 Expert 工作流

### 共用 Fixtures（`conftest.py`）

根目錄 `conftest.py` 提供所有層共用的 fixtures，pytest 自動向上搜尋：

| Fixture | 說明 |
|---------|------|
| `workspace` | tmp_path + connsys-jarvis symlink（最常用） |
| `legacy_workspace` | 含 `.repo` 目錄，觸發 legacy 場景 |
| `framework_expert_json` | framework-base-expert/expert.json 路徑 |
| `slim_expert_json` | wifi-bora-memory-slim-expert/expert.json 路徑 |

`integration/conftest.py` 額外提供：

| Fixture / Helper | 說明 |
|------------------|------|
| `build_mini_jarvis(root)` | 建立可寫的 mini jarvis（供 doctor 測試用） |
| `mini_workspace` | `build_mini_jarvis` 的 fixture 版本 |

---

## 驗證方式

### 快速（CI 推薦）

```bash
# 從 connsys-jarvis/ 根目錄執行
uvx pytest scripts/test/ -q
# 預期：239 passed
```

### 分層執行（開發時）

```bash
# Layer 1：只改了純邏輯函式 → 只跑 unit
uvx pytest scripts/test/unit/ -v

# Layer 2：改了 cmd_* 函式 → 跑 integration
uvx pytest scripts/test/integration/ -v

# Layer 3：改了 CLI parsing / main() → 跑 e2e
uvx pytest scripts/test/e2e/ -v
```

### 精確執行（鎖定測試類或函式）

```bash
# 只跑某個測試類
uvx pytest scripts/test/integration/test_integration.py::TestIntegrationReset -v

# 只跑上次失敗的測試
uvx pytest scripts/test/ --last-failed -v

# 詳細 traceback
uvx pytest scripts/test/ --tb=long
```

### 舊版 monolith（向後相容）

```bash
uvx pytest scripts/test/test_setup.py -v
# 預期：110 passed
```

> **注意**：執行 `uvx pytest scripts/test/` 時，pytest 同時收集 `test_setup.py`（110）+ `unit/`（38）+ `integration/`（73）+ `e2e/`（18）= 239 tests。
> unit/ 和 integration/ 的測試與 test_setup.py 部分重疊（相同邏輯，不同檔案），這是刻意的：確保分層後行為一致。

---

## 新增測試的指引

### 新增 Unit Test

適合：純函式邏輯（沒有副作用、不碰磁碟）

```python
# scripts/test/unit/test_unit.py
class TestMyNewFunction:
    def test_basic_case(self):
        result = inst.my_new_function(...)
        assert result == expected
```

### 新增 Integration Test

適合：驗證 cmd_* 函式對檔案系統的實際影響

```python
# scripts/test/integration/test_integration.py
class TestMyNewCommand:
    def test_creates_expected_files(self, workspace):
        inst.cmd_my_command(workspace, ...)
        assert (workspace / "expected_file").exists()
```

### 新增 E2E Test

適合：驗證 CLI 整體行為（exit code、stdout、組合流程）

```python
# scripts/test/e2e/test_e2e.py
class TestE2EMyScenario:
    def test_full_flow(self, ws):
        result = run_setup(ws, "--my-command", ...)
        assert result.returncode == 0
        assert "expected text" in result.stdout
        assert (ws / "expected_file").exists()
```
