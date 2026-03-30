"""
Integration Tests — connsys-jarvis setup.py
============================================
測試多模組協作行為：呼叫 cmd_* 函式，碰真實暫存檔案系統（tmp_path），
驗證 symlink、JSON 和 CLAUDE.md 確實被正確建立/刪除。

Run:
    uvx pytest scripts/tests/integration/ -v
"""

import json
import platform as _platform
from pathlib import Path
from unittest.mock import patch

import pytest

import setup as inst
from .conftest import build_mini_jarvis


# ─────────────────────────────────────────────────────────────────────────────
# TC-U09  --init
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationInit:
    """cmd_init() 正確建立 symlinks、CLAUDE.md、.env、.installed-experts.json。"""

    def _run_init(self, workspace, expert_rel):
        expert_json = workspace / "connsys-jarvis" / expert_rel
        with patch("sys.argv", ["setup.py", "--init", expert_rel]), \
             patch.object(inst, "find_workspace", return_value=workspace):
            inst.cmd_init(workspace, expert_json)

    def test_skills_symlinks_created(self, workspace, framework_expert_json):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        skills = list((workspace / ".claude" / "skills").iterdir())
        assert len(skills) == 3

    def test_hooks_symlinks_created(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        hooks = list((workspace / ".claude" / "hooks").iterdir())
        assert len(hooks) == 5

    def test_commands_symlinks_created(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        cmds = list((workspace / ".claude" / "commands").iterdir())
        assert len(cmds) == 2

    def test_claude_md_is_generated(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        assert (workspace / "CLAUDE.md").exists()

    def test_env_file_is_generated(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        assert (workspace / ".connsys-jarvis" / ".env").exists()

    def test_installed_json_has_one_expert(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        assert len(data["experts"]) == 1
        assert data["experts"][0]["name"] == "framework-base-expert"

    def test_symlinks_point_to_real_targets(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        for link in (workspace / ".claude" / "skills").iterdir():
            assert link.is_symlink()
            assert link.resolve().exists(), f"Dangling symlink: {link}"

    def test_init_clears_previous_symlinks(self, workspace):
        # 安裝兩次，不應重複累積
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        skills = list((workspace / ".claude" / "skills").iterdir())
        assert len(skills) == 3

    def test_memory_preserved_after_init(self, workspace):
        """--init 不觸碰 memory/（handoff 效果）。"""
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        memory_note = workspace / ".connsys-jarvis/memory/test/note.md"
        memory_note.parent.mkdir(parents=True, exist_ok=True)
        memory_note.write_text("handoff note")
        # 再次 --init
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        assert memory_note.exists()
        assert memory_note.read_text() == "handoff note"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U10  --add (idempotent)
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationAdd:
    """cmd_add() 疊加安裝、冪等性（重複 --add 不重複計算）。"""

    def _run_init(self, workspace, rel):
        inst.cmd_init(workspace, workspace / "connsys-jarvis" / rel)

    def _run_add(self, workspace, rel):
        inst.cmd_add(workspace, workspace / "connsys-jarvis" / rel)

    def test_add_increases_skill_count(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        before = len(list((workspace / ".claude" / "skills").iterdir()))
        self._run_add(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        after = len(list((workspace / ".claude" / "skills").iterdir()))
        assert after > before

    def test_add_total_skills_is_13(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        count = len(list((workspace / ".claude" / "skills").iterdir()))
        assert count == 13

    def test_add_idempotent_second_call_no_error(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        self._run_add(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        count = len(list((workspace / ".claude" / "skills").iterdir()))
        assert count == 13

    def test_add_installed_json_has_two(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        assert len(data["experts"]) == 2

    def test_add_last_expert_is_identity(self, workspace):
        self._run_init(workspace, "framework/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        identity = next(e for e in data["experts"] if e.get("is_identity"))
        assert identity["name"] == "wifi-bora-memory-slim-expert"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U11  --remove（全清再重建）
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationRemove:
    """cmd_remove() 移除後全清再重建，symlink 集合與剩餘 Expert 完全同步。"""

    def _setup(self, workspace):
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")
        inst.cmd_add(workspace, workspace / "connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/expert.json")

    def test_remove_reduces_skills(self, workspace):
        self._setup(workspace)
        inst.cmd_remove(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        count = len(list((workspace / ".claude" / "skills").iterdir()))
        assert count == 3

    def test_shared_skills_preserved(self, workspace):
        self._setup(workspace)
        inst.cmd_remove(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        skills = [p.name for p in (workspace / ".claude" / "skills").iterdir()]
        assert "framework-expert-discovery-knowhow" in skills
        assert "framework-handoff-flow" in skills
        assert "framework-memory-tool" in skills

    def test_private_skills_removed(self, workspace):
        self._setup(workspace)
        inst.cmd_remove(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        skills = [p.name for p in (workspace / ".claude" / "skills").iterdir()]
        assert "wifi-bora-memslim-flow" not in skills
        assert "wifi-bora-lsp-tool" not in skills

    def test_installed_json_has_one_after_remove(self, workspace):
        self._setup(workspace)
        inst.cmd_remove(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        assert len(data["experts"]) == 1
        assert data["experts"][0]["name"] == "framework-base-expert"

    def test_claude_md_reverts_to_single(self, workspace):
        self._setup(workspace)
        inst.cmd_remove(workspace, "wifi-bora/wifi-bora-memory-slim-expert/expert.json")
        content = (workspace / "CLAUDE.md").read_text()
        assert "framework-base-expert" in content
        assert "Experts" not in content or "Expert:" in content


# ─────────────────────────────────────────────────────────────────────────────
# TC-U12  --uninstall
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationUninstall:
    """cmd_uninstall() 清除 symlinks + CLAUDE.md，但保留 memory/。"""

    def _setup(self, workspace):
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")
        memory_note = workspace / ".connsys-jarvis/memory/test/note.md"
        memory_note.parent.mkdir(parents=True, exist_ok=True)
        memory_note.write_text("memory")

    def test_claude_md_deleted(self, workspace):
        self._setup(workspace)
        inst.cmd_uninstall(workspace)
        assert not (workspace / "CLAUDE.md").exists()

    def test_skills_symlinks_cleared(self, workspace):
        self._setup(workspace)
        inst.cmd_uninstall(workspace)
        skills_dir = workspace / ".claude" / "skills"
        assert not any(True for _ in skills_dir.iterdir()) if skills_dir.exists() else True

    def test_memory_preserved(self, workspace):
        """--uninstall 不刪 memory/。"""
        self._setup(workspace)
        inst.cmd_uninstall(workspace)
        assert (workspace / ".connsys-jarvis/memory/test/note.md").exists()


# ─────────────────────────────────────────────────────────────────────────────
# TC-U21  --reset
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationReset:
    """cmd_reset() 清除所有狀態（含 memory/），僅保留 log/。"""

    def _setup(self, workspace):
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")
        memory_note = workspace / ".connsys-jarvis/memory/test/note.md"
        memory_note.parent.mkdir(parents=True, exist_ok=True)
        memory_note.write_text("memory")
        log_file = workspace / ".connsys-jarvis/log/setup.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("log")

    def test_claude_md_deleted(self, workspace):
        self._setup(workspace)
        inst.cmd_reset(workspace)
        assert not (workspace / "CLAUDE.md").exists()

    def test_skills_symlinks_cleared(self, workspace):
        self._setup(workspace)
        inst.cmd_reset(workspace)
        skills_dir = workspace / ".claude" / "skills"
        assert not any(True for _ in skills_dir.iterdir()) if skills_dir.exists() else True

    def test_memory_deleted(self, workspace):
        """--reset 應刪除 memory/（與 --uninstall 的關鍵差異）。"""
        self._setup(workspace)
        inst.cmd_reset(workspace)
        assert not (workspace / ".connsys-jarvis/memory").exists()

    def test_installed_experts_deleted(self, workspace):
        self._setup(workspace)
        inst.cmd_reset(workspace)
        assert not (workspace / ".connsys-jarvis/.installed-experts.json").exists()

    def test_log_preserved(self, workspace):
        """--reset 應保留 log/。"""
        self._setup(workspace)
        inst.cmd_reset(workspace)
        assert (workspace / ".connsys-jarvis/log/setup.log").exists()


# ─────────────────────────────────────────────────────────────────────────────
# TC-U22  --init memory preservation
# ─────────────────────────────────────────────────────────────────────────────

class TestInitMemoryPreservation:
    """--init 切換 Expert 時 memory/ 應保留（handoff 效果）。"""

    def test_memory_preserved_after_init(self, workspace):
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")
        memory_note = workspace / ".connsys-jarvis/memory/test/note.md"
        memory_note.parent.mkdir(parents=True, exist_ok=True)
        memory_note.write_text("handoff note")
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")
        assert memory_note.exists()
        assert memory_note.read_text() == "handoff note"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U13  scan_available_experts
# ─────────────────────────────────────────────────────────────────────────────

class TestScanAvailableExperts:
    """scan_available_experts() 即時掃描 connsys-jarvis 目錄，不依賴 registry.json。"""

    def test_returns_non_empty_list(self, workspace):
        result = inst.scan_available_experts(workspace)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_finds_framework_base_expert(self, workspace):
        names = [e["name"] for e in inst.scan_available_experts(workspace)]
        assert "framework-base-expert" in names

    def test_finds_wifi_bora_memory_slim_expert(self, workspace):
        names = [e["name"] for e in inst.scan_available_experts(workspace)]
        assert "wifi-bora-memory-slim-expert" in names

    def test_each_entry_has_required_fields(self, workspace):
        for e in inst.scan_available_experts(workspace):
            assert "name" in e
            assert "domain" in e
            assert "path" in e
            assert "description" in e
            assert "is_base" in e
            assert "version" in e

    def test_framework_expert_domain_is_framework(self, workspace):
        experts = inst.scan_available_experts(workspace)
        fw = next(e for e in experts if e["name"] == "framework-base-expert")
        assert fw["domain"] == "framework"

    def test_no_status_field_in_scan_result(self, workspace):
        """status 由 cmd_list 加入，scan 本身不含此欄位。"""
        for e in inst.scan_available_experts(workspace):
            assert "status" not in e


# ─────────────────────────────────────────────────────────────────────────────
# TC-U14  --query
# ─────────────────────────────────────────────────────────────────────────────

class TestCmdQuery:
    """--query：查詢指定 Expert 的 metadata，支援 table / json 格式。"""

    def _init_framework(self, workspace):
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")

    def test_query_table_contains_name(self, workspace, capsys):
        self._init_framework(workspace)
        inst.cmd_query(workspace, "framework-base-expert")
        out = capsys.readouterr().out
        assert "framework-base-expert" in out

    def test_query_installed_shows_installed_status(self, workspace, capsys):
        self._init_framework(workspace)
        inst.cmd_query(workspace, "framework-base-expert")
        out = capsys.readouterr().out
        assert "installed" in out

    def test_query_not_installed_shows_available_status(self, workspace, capsys):
        inst.cmd_query(workspace, "wifi-bora-memory-slim-expert")
        out = capsys.readouterr().out
        assert "available" in out

    def test_query_json_format_is_valid_json(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()
        inst.cmd_query(workspace, "framework-base-expert", output_format="json")
        data = json.loads(capsys.readouterr().out)
        assert data["name"] == "framework-base-expert"

    def test_query_json_has_required_fields(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()
        inst.cmd_query(workspace, "framework-base-expert", output_format="json")
        data = json.loads(capsys.readouterr().out)
        for field in ("name", "domain", "path", "description", "status",
                      "is_identity", "install_order", "dependencies", "internal"):
            assert field in data, f"Missing field: {field}"

    def test_query_json_installed_status_correct(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()
        inst.cmd_query(workspace, "framework-base-expert", output_format="json")
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "installed"
        assert data["is_identity"] is True

    def test_query_partial_name_match(self, workspace, capsys):
        inst.cmd_query(workspace, "framework-base")
        out = capsys.readouterr().out
        assert "framework-base-expert" in out

    def test_query_nonexistent_expert_exits(self, workspace):
        with pytest.raises(SystemExit):
            inst.cmd_query(workspace, "nonexistent-expert-xyz-abc")


# ─────────────────────────────────────────────────────────────────────────────
# TC-U15  --list
# ─────────────────────────────────────────────────────────────────────────────

class TestCmdListUpdated:
    """--list：即時掃描顯示 installed + available，支援 --format json。"""

    def _init_framework(self, workspace):
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")

    def test_list_shows_installed_expert(self, workspace, capsys):
        self._init_framework(workspace)
        inst.cmd_list(workspace)
        out = capsys.readouterr().out
        assert "framework-base-expert" in out

    def test_list_shows_available_experts_too(self, workspace, capsys):
        self._init_framework(workspace)
        inst.cmd_list(workspace)
        out = capsys.readouterr().out
        assert "wifi-bora-memory-slim-expert" in out

    def test_list_json_format_is_valid_json(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_json_all_entries_have_status(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        for item in data:
            assert "status" in item
            assert item["status"] in ("installed", "available")

    def test_list_json_installed_expert_correct_status(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        fw = next((e for e in data if e["name"] == "framework-base-expert"), None)
        assert fw is not None
        assert fw["status"] == "installed"
        assert fw["is_identity"] is True

    def test_list_json_available_expert_correct_status(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        slim = next((e for e in data if e["name"] == "wifi-bora-memory-slim-expert"), None)
        assert slim is not None
        assert slim["status"] == "available"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U16  --doctor: 系統資訊
# ─────────────────────────────────────────────────────────────────────────────

class TestDoctorSystemInfo:
    """--doctor 區段 A — 系統資訊顯示（OS、Python、connsys-jarvis 版本）。"""

    def _init_and_doctor(self, workspace, capsys):
        inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/framework-base-expert/expert.json")
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        return capsys.readouterr().out

    def test_shows_os(self, workspace, capsys):
        out = self._init_and_doctor(workspace, capsys)
        assert "OS:" in out

    def test_shows_python_version(self, workspace, capsys):
        out = self._init_and_doctor(workspace, capsys)
        assert "Python:" in out
        assert _platform.python_version() in out

    def test_shows_jarvis_version(self, workspace, capsys):
        out = self._init_and_doctor(workspace, capsys)
        assert "connsys-jarvis:" in out
        assert inst.SETUP_VERSION in out


# ─────────────────────────────────────────────────────────────────────────────
# TC-U17  --doctor: 環境變數
# ─────────────────────────────────────────────────────────────────────="────────

class TestDoctorEnvVars:
    """--doctor 區段 B — 環境變數驗證（存在性、路徑有效性）。"""

    def _fw_json(self, workspace):
        return workspace / "connsys-jarvis/framework/framework-base-expert/expert.json"

    def test_all_vars_ok_after_init(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        for var in inst.REQUIRED_ENV_VARS:
            assert var in out

    def test_missing_env_file_shows_error(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        (workspace / ".connsys-jarvis" / ".env").unlink()
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert ".env not found" in out

    def test_missing_env_file_shows_fix_hint(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        (workspace / ".connsys-jarvis" / ".env").unlink()
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "--init" in out

    def test_path_var_nonexistent_shows_error(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        env_path = workspace / ".connsys-jarvis" / ".env"
        content  = env_path.read_text()
        jarvis_real = str(workspace / "connsys-jarvis")
        content = content.replace(jarvis_real, "/nonexistent/__test_path__")
        env_path.write_text(content)
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "path does not exist" in out


# ─────────────────────────────────────────────────────────────────────────────
# TC-U18  --doctor: Symlink 完整性
# ─────────────────────────────────────────────────────────────────────────────

class TestDoctorSymlinkIntegrity:
    """--doctor 區段 C — Symlink 完整性（missing / orphan / dangling SKILL.md）。"""

    def _fw_json(self, workspace):
        return workspace / "connsys-jarvis/framework/framework-base-expert/expert.json"

    def test_clean_install_no_symlink_errors(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "missing]" not in out
        assert "orphan]" not in out

    def test_missing_symlink_shows_error(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        skills_dir = workspace / ".claude" / "skills"
        first_skill = sorted(skills_dir.iterdir())[0]
        first_skill.unlink()
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "missing]" in out

    def test_orphan_symlink_shows_warning(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        orphan = workspace / ".claude" / "skills" / "orphan-not-declared"
        orphan.symlink_to("/tmp")
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "orphan]" in out

    def test_installed_skill_link_without_skill_md_shows_warning(self, workspace, capsys, tmp_path):
        """已建 skill link 指向的 folder 缺少 SKILL.md → ⚠️。"""
        root = build_mini_jarvis(tmp_path / "mini_ws")
        inst.cmd_init(root, root / "connsys-jarvis/framework/mini-expert/expert.json")
        skill_md = root / "connsys-jarvis/framework/mini-expert/skills/mini-skill-a/SKILL.md"
        skill_md.unlink()
        capsys.readouterr()
        inst.cmd_doctor(root)
        out = capsys.readouterr().out
        assert "SKILL.md" in out
        assert "missing" in out


# ─────────────────────────────────────────────────────────────────────────────
# TC-U19  --doctor: CLAUDE.md 內容
# ─────────────────────────────────────────────────────────────────────────────

class TestDoctorClaudeMd:
    """--doctor 區段 D — CLAUDE.md 內容驗證（@include 正確性、目標存在性、Base Expert inclusion）。"""

    def _fw_json(self, workspace):
        return workspace / "connsys-jarvis/framework/framework-base-expert/expert.json"

    def _slim_json(self, workspace):
        return workspace / "connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/expert.json"

    def test_correct_claude_md_shows_ok(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "Content matches expected" in out

    def test_include_targets_all_exist_shows_checkmarks(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "@include target existence" in out
        assert "file not found" not in out

    def test_include_target_missing_shows_error(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        claude_md = workspace / "CLAUDE.md"
        claude_md.write_text(claude_md.read_text() + "@connsys-jarvis/nonexistent/ghost.md\n")
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "ghost.md" in out
        assert "file not found" in out

    def test_missing_claude_md_shows_error(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        (workspace / "CLAUDE.md").unlink()
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "CLAUDE.md not found" in out

    def test_missing_include_shows_error(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        claude_md = workspace / "CLAUDE.md"
        lines = [l for l in claude_md.read_text().splitlines()
                 if not l.strip().startswith("@connsys-jarvis")]
        claude_md.write_text("\n".join(lines))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "missing @include" in out

    def test_extra_include_shows_warning(self, workspace, capsys):
        inst.cmd_init(workspace, self._fw_json(workspace))
        claude_md = workspace / "CLAUDE.md"
        claude_md.write_text(claude_md.read_text() + "@connsys-jarvis/fake/expert.md\n")
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "extra @include" in out

    def test_base_expert_inclusion_section_present(self, workspace, capsys):
        # framework-base-expert is identity (is_base=True) → no base expert section needed
        inst.cmd_init(workspace, self._fw_json(workspace))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "Base Expert Inclusion" in out

    def test_base_expert_included_shows_ok(self, workspace, capsys):
        # wifi-bora-memory-slim-expert depends on framework-base-expert (is_base=True)
        inst.cmd_init(workspace, self._slim_json(workspace))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "Base Expert Inclusion" in out
        # framework-base-expert and wifi-bora-base-expert should be included
        assert "framework-base-expert" in out
        assert "wifi-bora-base-expert" in out
        assert "expert.md missing" not in out

    def test_base_expert_missing_shows_error(self, workspace, capsys):
        # Install slim expert, then remove base expert references from CLAUDE.md
        inst.cmd_init(workspace, self._slim_json(workspace))
        claude_md = workspace / "CLAUDE.md"
        # Remove all base expert lines from CLAUDE.md to simulate stale/old CLAUDE.md
        lines = [l for l in claude_md.read_text().splitlines()
                 if "framework-base-expert" not in l and "wifi-bora-base-expert" not in l
                 and "sys-bora-base-expert" not in l]
        claude_md.write_text("\n".join(lines))
        capsys.readouterr()
        inst.cmd_doctor(workspace)
        out = capsys.readouterr().out
        assert "expert.md missing in CLAUDE.md" in out
        assert "Fix" in out


# ─────────────────────────────────────────────────────────────────────────────
# TC-U20  --doctor: Expert 結構完整性
# ─────────────────────────────────────────────────────────────────────────────

class TestDoctorExpertStructure:
    """--doctor 區段 F — Expert 結構完整性（使用 mini_workspace fixture）。"""

    def _run_doctor(self, root, capsys):
        capsys.readouterr()
        inst.cmd_doctor(root)
        return capsys.readouterr().out

    def test_complete_expert_structure_shows_ok(self, mini_workspace, capsys):
        out = self._run_doctor(mini_workspace, capsys)
        assert "mini-expert" in out

    def test_missing_required_file_shows_error(self, mini_workspace, capsys):
        (mini_workspace / "connsys-jarvis/framework/mini-expert/soul.md").unlink()
        out = self._run_doctor(mini_workspace, capsys)
        assert "soul.md" in out
        assert "missing" in out

    def test_missing_owner_field_shows_error(self, mini_workspace, capsys):
        exp_json = mini_workspace / "connsys-jarvis/framework/mini-expert/expert.json"
        data = json.loads(exp_json.read_text())
        del data["owner"]
        exp_json.write_text(json.dumps(data))
        out = self._run_doctor(mini_workspace, capsys)
        assert "owner" in out

    def test_missing_internal_skills_field_shows_error(self, mini_workspace, capsys):
        exp_json = mini_workspace / "connsys-jarvis/framework/mini-expert/expert.json"
        data = json.loads(exp_json.read_text())
        del data["internal"]["skills"]
        exp_json.write_text(json.dumps(data))
        out = self._run_doctor(mini_workspace, capsys)
        assert "internal.skills" in out

    def test_skill_without_skill_md_shows_warning(self, mini_workspace, capsys):
        (mini_workspace / "connsys-jarvis/framework/mini-expert/skills/mini-skill-a/SKILL.md").unlink()
        out = self._run_doctor(mini_workspace, capsys)
        assert "SKILL.md" in out

    def test_orphan_skill_shows_warning(self, mini_workspace, capsys):
        orphan = mini_workspace / "connsys-jarvis/framework/mini-expert/skills/orphan-skill"
        orphan.mkdir(parents=True)
        (orphan / "SKILL.md").write_text("# orphan\n")
        out = self._run_doctor(mini_workspace, capsys)
        assert "orphan-skill" in out
        assert "not referenced by any expert.json" in out
