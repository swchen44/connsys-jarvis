"""
E2E Tests — connsys-jarvis setup.py
=====================================
端對端測試：透過 subprocess.run() 模擬真實使用者操作，
從 CLI 入口到最終檔案系統狀態，整個系統跑一遍。

特性：
- 不 import setup.py，完全透過 CLI 黑箱測試
- 驗證 stdout / returncode
- 驗證最終檔案系統狀態
- 最慢，數量最少（只覆蓋關鍵流程）

Run:
    uvx pytest scripts/tests/e2e/ -v
"""

import subprocess
import sys
from pathlib import Path

import pytest

# ── jarvis repo path ──────────────────────────────────────────────────────────
# This file: scripts/tests/e2e/test_e2e.py
# parents[0] = e2e/
# parents[1] = test/
# parents[2] = scripts/
# parents[3] = connsys-jarvis/
JARVIS_REAL = Path(__file__).resolve().parents[3]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    """E2E workspace：connsys-jarvis symlinked，模擬真實使用者環境。"""
    (tmp_path / "connsys-jarvis").symlink_to(JARVIS_REAL)
    return tmp_path


def run_setup(ws: Path, *args) -> subprocess.CompletedProcess:
    """呼叫 setup.py CLI，回傳 CompletedProcess（含 stdout、returncode）。"""
    return subprocess.run(
        [sys.executable,
         str(ws / "connsys-jarvis/scripts/setup.py"),
         *args],
        cwd=ws,
        capture_output=True,
        text=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-E01  --init 基本流程（Agent First）
# ─────────────────────────────────────────────────────────────────────────────

class TestE2EInit:
    """驗證 --init 的完整 CLI 流程。"""

    def test_returns_zero_exit_code(self, ws):
        result = run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_stdout_contains_source_hint(self, ws):
        result = run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        # setup.py 輸出絕對路徑，如 "Run: source /path/.connsys-jarvis/.env"
        assert "source" in result.stdout
        assert ".connsys-jarvis/.env" in result.stdout

    def test_claude_md_created(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        assert (ws / "CLAUDE.md").exists()

    def test_env_file_created(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        assert (ws / ".connsys-jarvis" / ".env").exists()

    def test_installed_experts_json_created(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        assert (ws / ".connsys-jarvis" / ".installed-experts.json").exists()

    def test_skills_symlinks_exist(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        skills_dir = ws / ".claude" / "skills"
        assert skills_dir.exists()
        assert len(list(skills_dir.iterdir())) == 6


# ─────────────────────────────────────────────────────────────────────────────
# TC-E02  --add 流程
# ─────────────────────────────────────────────────────────────────────────────

class TestE2EAdd:
    """驗證 --add 疊加安裝的完整 CLI 流程。"""

    def test_add_after_init_succeeds(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        result = run_setup(ws, "--add", "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_add_increases_skill_count(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        run_setup(ws, "--add", "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        count = len(list((ws / ".claude" / "skills").iterdir()))
        assert count == 18


# ─────────────────────────────────────────────────────────────────────────────
# TC-E03  --uninstall 流程
# ─────────────────────────────────────────────────────────────────────────────

class TestE2EUninstall:
    """驗證 --uninstall 的完整 CLI 流程（memory 保留）。"""

    def test_uninstall_returns_zero(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        result = run_setup(ws, "--uninstall")
        assert result.returncode == 0

    def test_uninstall_removes_claude_md(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        run_setup(ws, "--uninstall")
        assert not (ws / "CLAUDE.md").exists()

    def test_uninstall_preserves_memory(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        note = ws / ".connsys-jarvis/memory/note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("keep me")
        run_setup(ws, "--uninstall")
        assert note.exists()


# ─────────────────────────────────────────────────────────────────────────────
# TC-E04  --reset 流程
# ─────────────────────────────────────────────────────────────────────────────

class TestE2EReset:
    """驗證 --reset 的完整 CLI 流程（memory 刪除，log 保留）。"""

    def test_reset_returns_zero(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        result = run_setup(ws, "--reset")
        assert result.returncode == 0

    def test_reset_removes_claude_md(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        run_setup(ws, "--reset")
        assert not (ws / "CLAUDE.md").exists()

    def test_reset_removes_memory(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        note = ws / ".connsys-jarvis/memory/note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("should be gone")
        run_setup(ws, "--reset")
        assert not (ws / ".connsys-jarvis/memory").exists()

    def test_reset_preserves_log(self, ws):
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        # --init 已建立 log/，run reset 後 log/ 應保留
        log_dir = ws / ".connsys-jarvis/log"
        run_setup(ws, "--reset")
        assert log_dir.exists()


# ─────────────────────────────────────────────────────────────────────────────
# TC-E05  --list 流程
# ─────────────────────────────────────────────────────────────────────────────

class TestE2EList:
    """驗證 --list 輸出格式。"""

    def test_list_json_is_valid(self, ws):
        import json
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        result = run_setup(ws, "--list", "--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_list_shows_installed_and_available(self, ws):
        import json
        run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        result = run_setup(ws, "--list", "--format", "json")
        data = json.loads(result.stdout)
        statuses = {e["name"]: e["status"] for e in data}
        assert statuses.get("framework-base-expert") == "installed"
        assert statuses.get("wifi-bora-memory-slim-expert") == "available"


# ─────────────────────────────────────────────────────────────────────────────
# TC-E06  完整多 Expert 工作流
# ─────────────────────────────────────────────────────────────────────────────

class TestE2EMultiExpertWorkflow:
    """完整流程：--init → --add → --remove → verify。"""

    def test_full_workflow(self, ws):
        import json

        # 1. init
        r = run_setup(ws, "--init", "framework/framework-base-expert/expert.json")
        assert r.returncode == 0

        # 2. add
        r = run_setup(ws, "--add", "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        assert r.returncode == 0
        assert len(list((ws / ".claude/skills").iterdir())) == 18

        # 3. list → 兩個 installed
        r = run_setup(ws, "--list", "--format", "json")
        data = json.loads(r.stdout)
        installed = [e for e in data if e["status"] == "installed"]
        assert len(installed) == 2

        # 4. remove wifi-bora expert
        r = run_setup(ws, "--remove", "wifi-bora-memory-slim-expert")
        assert r.returncode == 0
        assert len(list((ws / ".claude/skills").iterdir())) == 6

        # 5. list → 一個 installed
        r = run_setup(ws, "--list", "--format", "json")
        data = json.loads(r.stdout)
        installed = [e for e in data if e["status"] == "installed"]
        assert len(installed) == 1
        assert installed[0]["name"] == "framework-base-expert"
