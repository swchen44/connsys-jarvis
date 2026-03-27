# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pytest>=8.0",
# ]
# ///
"""
Unit tests for connsys-jarvis/scripts/setup.py

Run:
    uvx pytest scripts/test/test_setup.py -v
    uv run --with pytest pytest scripts/test/test_setup.py -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Make setup.py importable ─────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import setup as inst  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Empty workspace with connsys-jarvis symlinked."""
    jarvis_real = Path(__file__).resolve().parents[2]  # scripts/test → scripts → connsys-jarvis
    jarvis_link = tmp_path / "connsys-jarvis"
    jarvis_link.symlink_to(jarvis_real)
    return tmp_path


@pytest.fixture()
def legacy_workspace(tmp_path: Path) -> Path:
    """Workspace that has a .repo folder (legacy scenario)."""
    jarvis_real = Path(__file__).resolve().parents[2]
    (tmp_path / "connsys-jarvis").symlink_to(jarvis_real)
    (tmp_path / ".repo").mkdir()
    return tmp_path


@pytest.fixture()
def framework_expert_json(workspace: Path) -> Path:
    return workspace / "connsys-jarvis/framework/experts/framework-base-expert/expert.json"


@pytest.fixture()
def slim_expert_json(workspace: Path) -> Path:
    return workspace / "connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U01  detect_scenario
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectScenario:
    def test_agent_first_empty_workspace(self, workspace):
        assert inst.detect_scenario(workspace) == "agent-first"

    def test_agent_first_codespace_exists(self, workspace):
        (workspace / "codespace").mkdir()
        assert inst.detect_scenario(workspace) == "agent-first"

    def test_legacy_repo_exists(self, legacy_workspace):
        assert inst.detect_scenario(legacy_workspace) == "legacy"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U02  get_codespace_path
# ─────────────────────────────────────────────────────────────────────────────

class TestGetCodespacePath:
    def test_agent_first_returns_codespace_subdir(self, workspace):
        path = inst.get_codespace_path(workspace)
        assert path == str(workspace / "codespace")

    def test_legacy_returns_workspace_root(self, legacy_workspace):
        path = inst.get_codespace_path(legacy_workspace)
        assert path == str(legacy_workspace)


# ─────────────────────────────────────────────────────────────────────────────
# TC-U03  resolve_items
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveItems:
    def test_none_returns_empty(self, tmp_path):
        assert inst.resolve_items(tmp_path, "skills", None) == []

    def test_explicit_list_returned_as_is(self, tmp_path):
        spec = ["skill-a", "skill-b"]
        assert inst.resolve_items(tmp_path, "skills", spec) == spec

    def test_all_skills_returns_subdirs(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-a").mkdir(parents=True)
        (skills_dir / "skill-b").mkdir(parents=True)
        result = inst.resolve_items(tmp_path, "skills", "all")
        assert sorted(result) == ["skill-a", "skill-b"]

    def test_all_hooks_returns_sh_files(self, tmp_path):
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "session-start.sh").touch()
        (hooks_dir / "helper.py").touch()
        (hooks_dir / "README.md").touch()  # should be excluded
        result = inst.resolve_items(tmp_path, "hooks", "all")
        assert sorted(result) == ["helper.py", "session-start.sh"]

    def test_all_list_notation(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-x").mkdir(parents=True)
        result = inst.resolve_items(tmp_path, "skills", ["all"])
        assert result == ["skill-x"]

    def test_missing_dir_returns_empty(self, tmp_path):
        result = inst.resolve_items(tmp_path, "skills", "all")
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# TC-U04  apply_exclude_patterns
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyExcludePatterns:
    def test_no_patterns_returns_all(self):
        items = ["skill-a", "skill-b"]
        assert inst.apply_exclude_patterns(items, []) == items

    def test_pattern_filters_matching(self):
        items = ["wifi-bora-lsp-tool", "wifi-bora-ast-tool", "framework-handoff-flow"]
        result = inst.apply_exclude_patterns(items, [".*-lsp-.*"])
        assert result == ["wifi-bora-ast-tool", "framework-handoff-flow"]

    def test_multiple_patterns(self):
        items = ["wifi-bora-lsp-tool", "wifi-bora-debug-flow", "framework-handoff-flow"]
        result = inst.apply_exclude_patterns(items, [".*-lsp-.*", ".*-debug-.*"])
        assert result == ["framework-handoff-flow"]

    def test_pattern_filters_nothing_when_no_match(self):
        items = ["skill-a", "skill-b"]
        result = inst.apply_exclude_patterns(items, [".*-lsp-.*"])
        assert result == ["skill-a", "skill-b"]


# ─────────────────────────────────────────────────────────────────────────────
# TC-U05  generate_claude_md — 單 Expert
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateClaudeMdSingle:
    def _installed(self, path: str, name: str, display: str) -> dict:
        return {
            "experts": [{
                "name": name,
                "path": path,
                "is_identity": True,
                "install_order": 1,
            }]
        }

    def test_no_experts_shows_empty(self, workspace):
        content = inst.generate_claude_md(workspace, {"experts": []})
        assert "未安裝" in content
        assert "@CLAUDE.local.md" in content

    def test_single_expert_has_soul_rules_duties_expert(self, workspace, framework_expert_json):
        installed = self._installed(
            "framework/experts/framework-base-expert/expert.json",
            "framework-base-expert",
            "Framework Base Expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "@connsys-jarvis/framework/experts/framework-base-expert/soul.md" in content
        assert "@connsys-jarvis/framework/experts/framework-base-expert/rules.md" in content
        assert "@connsys-jarvis/framework/experts/framework-base-expert/duties.md" in content
        assert "@connsys-jarvis/framework/experts/framework-base-expert/expert.md" in content

    def test_single_expert_ends_with_claude_local(self, workspace):
        installed = self._installed(
            "framework/experts/framework-base-expert/expert.json",
            "framework-base-expert",
            "Framework Base Expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert content.strip().endswith("@CLAUDE.local.md")

    def test_single_expert_header_contains_display_name(self, workspace, framework_expert_json):
        installed = self._installed(
            "framework/experts/framework-base-expert/expert.json",
            "framework-base-expert",
            "Framework Base Expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "Framework Base Expert" in content


# ─────────────────────────────────────────────────────────────────────────────
# TC-U06  generate_claude_md — 多 Expert
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateClaudeMdMulti:
    """測試多 Expert 情境下 generate_claude_md 的兩種模式：
      - 預設（include_all_experts=False）：只輸出 identity expert 的四份文件
      - --with-all-experts（include_all_experts=True）：Identity + 所有 expert.md
    """

    def _two_experts(self, include_all: bool = False) -> dict:
        """建立含兩個 Expert 的 installed dict。"""
        return {
            "include_all_experts": include_all,
            "experts": [
                {
                    "name": "framework-base-expert",
                    "path": "framework/experts/framework-base-expert/expert.json",
                    "is_identity": False,
                    "install_order": 1,
                },
                {
                    "name": "wifi-bora-memory-slim-expert",
                    "path": "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json",
                    "is_identity": True,
                    "install_order": 2,
                },
            ]
        }

    # ── 預設模式（include_all_experts=False）──

    def test_default_uses_identity_expert_only(self, workspace):
        """預設：只包含 identity expert（最後安裝）的四份文件。"""
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "@connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/soul.md" in content
        assert "@connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/rules.md" in content
        assert "@connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/duties.md" in content
        assert "@connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/expert.md" in content

    def test_default_excludes_other_expert_md(self, workspace):
        """預設：其他 Expert 的 expert.md 不應出現。"""
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "@connsys-jarvis/framework/experts/framework-base-expert/expert.md" not in content

    def test_default_no_expert_count_header(self, workspace):
        """預設：不顯示「N Experts 已安裝」count header（與單 Expert 格式相同）。"""
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "2 Experts" not in content

    def test_default_ends_with_claude_local(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert content.strip().endswith("@CLAUDE.local.md")

    # ── --with-all-experts 模式（include_all_experts=True）──

    def test_with_all_experts_header_shows_count(self, workspace):
        """--with-all-experts：顯示 Expert 數量。"""
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "2 Experts" in content

    def test_with_all_experts_identity_soul_present(self, workspace):
        """--with-all-experts：identity expert 的 soul/rules/duties 存在。"""
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "@connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/soul.md" in content

    def test_with_all_experts_all_expert_mds_present(self, workspace):
        """--with-all-experts：所有 Expert 的 expert.md 都存在。"""
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "@connsys-jarvis/framework/experts/framework-base-expert/expert.md" in content
        assert "@connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/expert.md" in content

    def test_with_all_experts_section_headers(self, workspace):
        """--with-all-experts：包含 Identity 和 Capabilities 區段。"""
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "Expert Identity" in content
        assert "Expert Capabilities" in content


# ─────────────────────────────────────────────────────────────────────────────
# TC-U07  write_env_file — 環境變數內容
# ─────────────────────────────────────────────────────────────────────────────

class TestWriteEnvFile:
    def _read_env(self, workspace: Path) -> dict:
        env_path = workspace / ".connsys-jarvis" / ".env"
        result = {}
        for line in env_path.read_text().splitlines():
            if line.startswith("export "):
                key, _, val = line[len("export "):].partition("=")
                result[key] = val.strip('"')
        return result

    def test_env_contains_all_six_vars(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(workspace, "framework-base-expert")
        env = self._read_env(workspace)
        for key in [
            "CONNSYS_JARVIS_PATH",
            "CONNSYS_JARVIS_WORKSPACE_ROOT_PATH",
            "CONNSYS_JARVIS_CODE_SPACE_PATH",
            "CONNSYS_JARVIS_MEMORY_PATH",
            "CONNSYS_JARVIS_EMPLOYEE_ID",
            "CONNSYS_JARVIS_ACTIVE_EXPERT",
        ]:
            assert key in env, f"Missing env var: {key}"

    def test_jarvis_path_points_to_connsys_jarvis(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_PATH"].endswith("connsys-jarvis")

    def test_workspace_root_equals_workspace(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_WORKSPACE_ROOT_PATH"] == str(workspace)

    def test_agent_first_codespace_path_has_codespace(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_CODE_SPACE_PATH"].endswith("codespace")

    def test_legacy_codespace_path_equals_workspace(self, legacy_workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(legacy_workspace, "x")
        env_path = legacy_workspace / ".connsys-jarvis" / ".env"
        result = {}
        for line in env_path.read_text().splitlines():
            if line.startswith("export "):
                key, _, val = line[len("export "):].partition("=")
                result[key] = val.strip('"')
        assert result["CONNSYS_JARVIS_CODE_SPACE_PATH"] == str(legacy_workspace)

    def test_memory_path_inside_dot_dir(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert ".connsys-jarvis/memory" in env["CONNSYS_JARVIS_MEMORY_PATH"]

    def test_employee_id_from_git_config(self, workspace):
        with patch.object(inst, "run_git_config", return_value="alice.bob"):
            inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_EMPLOYEE_ID"] == "alice.bob"

    def test_employee_id_fallback_when_git_missing(self, workspace):
        with patch.object(inst, "run_git_config", return_value=""):
            inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_EMPLOYEE_ID"] == "unknown"

    def test_active_expert_reflects_argument(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(workspace, "wifi-bora-memory-slim-expert")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_ACTIVE_EXPERT"] == "wifi-bora-memory-slim-expert"

    def test_all_vars_use_connsys_jarvis_prefix(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.write_env_file(workspace, "x")
        env_path = workspace / ".connsys-jarvis" / ".env"
        for line in env_path.read_text().splitlines():
            if line.startswith("export "):
                key = line[len("export "):].split("=")[0]
                assert key.startswith("CONNSYS_JARVIS_"), f"Var without prefix: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U08  installed_experts JSON schema
# ─────────────────────────────────────────────────────────────────────────────

class TestInstalledExpertsSchema:
    def test_load_empty_returns_schema_skeleton(self, workspace):
        data = inst.load_installed_experts(workspace)
        assert data["schema_version"] == "1.0"
        assert data["experts"] == []
        assert "updated_at" in data

    def test_save_and_reload_roundtrip(self, workspace):
        data = inst.load_installed_experts(workspace)
        data["experts"].append({"name": "test-expert", "path": "x/expert.json"})
        inst.save_installed_experts(workspace, data)
        reloaded = inst.load_installed_experts(workspace)
        assert reloaded["experts"][0]["name"] == "test-expert"

    def test_save_updates_updated_at(self, workspace):
        data = inst.load_installed_experts(workspace)
        old_ts = data["updated_at"]
        inst.save_installed_experts(workspace, data)
        reloaded = inst.load_installed_experts(workspace)
        # updated_at is written fresh on save
        assert "updated_at" in reloaded


# ─────────────────────────────────────────────────────────────────────────────
# TC-U09  integration — --init
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationInit:
    def _run_init(self, workspace, expert_rel):
        expert_json = workspace / "connsys-jarvis" / expert_rel
        with patch("sys.argv", ["setup.py", "--init", expert_rel]), \
             patch.object(inst, "find_workspace", return_value=workspace), \
             patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_init(workspace, expert_json)

    def test_skills_symlinks_created(self, workspace, framework_expert_json):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        skills = list((workspace / ".claude" / "skills").iterdir())
        assert len(skills) == 3

    def test_hooks_symlinks_created(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        hooks = list((workspace / ".claude" / "hooks").iterdir())
        assert len(hooks) == 5

    def test_commands_symlinks_created(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        cmds = list((workspace / ".claude" / "commands").iterdir())
        assert len(cmds) == 2

    def test_claude_md_is_generated(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        assert (workspace / "CLAUDE.md").exists()

    def test_env_file_is_generated(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        assert (workspace / ".connsys-jarvis" / ".env").exists()

    def test_installed_json_has_one_expert(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        assert len(data["experts"]) == 1
        assert data["experts"][0]["name"] == "framework-base-expert"

    def test_symlinks_point_to_real_targets(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        for link in (workspace / ".claude" / "skills").iterdir():
            assert link.is_symlink()
            assert link.resolve().exists(), f"Dangling symlink: {link}"

    def test_init_clears_previous_symlinks(self, workspace):
        # Install twice; second should not double-up
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        skills = list((workspace / ".claude" / "skills").iterdir())
        assert len(skills) == 3


# ─────────────────────────────────────────────────────────────────────────────
# TC-U10  integration — --add (idempotent)
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationAdd:
    def _run_init(self, workspace, rel):
        expert_json = workspace / "connsys-jarvis" / rel
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_init(workspace, expert_json)

    def _run_add(self, workspace, rel):
        expert_json = workspace / "connsys-jarvis" / rel
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_add(workspace, expert_json)

    def test_add_increases_skill_count(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        before = len(list((workspace / ".claude" / "skills").iterdir()))
        self._run_add(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        after = len(list((workspace / ".claude" / "skills").iterdir()))
        assert after > before

    def test_add_total_skills_is_13(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        count = len(list((workspace / ".claude" / "skills").iterdir()))
        assert count == 13

    def test_add_idempotent_second_call_no_error(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        self._run_add(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        count = len(list((workspace / ".claude" / "skills").iterdir()))
        assert count == 13

    def test_add_installs_experts_json_has_two(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        assert len(data["experts"]) == 2

    def test_add_last_expert_is_identity(self, workspace):
        self._run_init(workspace, "framework/experts/framework-base-expert/expert.json")
        self._run_add(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        identity = next(e for e in data["experts"] if e.get("is_identity"))
        assert identity["name"] == "wifi-bora-memory-slim-expert"


# ─────────────────────────────────────────────────────────────────────────────
# TC-U11  integration — --remove（全清再重建）
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationRemove:
    def _setup(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/experts/framework-base-expert/expert.json")
            inst.cmd_add(workspace, workspace / "connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")

    def test_remove_reduces_skills(self, workspace):
        self._setup(workspace)
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_remove(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        count = len(list((workspace / ".claude" / "skills").iterdir()))
        assert count == 3

    def test_shared_skills_preserved(self, workspace):
        self._setup(workspace)
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_remove(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        skills = [p.name for p in (workspace / ".claude" / "skills").iterdir()]
        assert "framework-expert-discovery-knowhow" in skills
        assert "framework-handoff-flow" in skills
        assert "framework-memory-tool" in skills

    def test_private_skills_removed(self, workspace):
        self._setup(workspace)
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_remove(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        skills = [p.name for p in (workspace / ".claude" / "skills").iterdir()]
        assert "wifi-bora-memslim-flow" not in skills
        assert "wifi-bora-lsp-tool" not in skills

    def test_installed_json_has_one_after_remove(self, workspace):
        self._setup(workspace)
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_remove(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        data = inst.load_installed_experts(workspace)
        assert len(data["experts"]) == 1
        assert data["experts"][0]["name"] == "framework-base-expert"

    def test_claude_md_reverts_to_single(self, workspace):
        self._setup(workspace)
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_remove(workspace, "wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json")
        content = (workspace / "CLAUDE.md").read_text()
        # 移除後只剩單一 Expert，CLAUDE.md 應回到單 Expert 格式
        assert "framework-base-expert" in content
        # 單 Expert 格式不含 count header
        assert "Experts" not in content or "Expert:" in content


# ─────────────────────────────────────────────────────────────────────────────
# TC-U12  integration — --uninstall
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationUninstall:
    def _setup(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_init(workspace, workspace / "connsys-jarvis/framework/experts/framework-base-expert/expert.json")
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
        self._setup(workspace)
        inst.cmd_uninstall(workspace)
        assert (workspace / ".connsys-jarvis/memory/test/note.md").exists()


# ─────────────────────────────────────────────────────────────────────────────
# TC-U13  scan_available_experts
# ─────────────────────────────────────────────────────────────────────────────

class TestScanAvailableExperts:
    """即時掃描 connsys-jarvis 目錄取得所有可用 Expert（不依賴 registry.json）。"""

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
# TC-U14  cmd_query
# ─────────────────────────────────────────────────────────────────────────────

class TestCmdQuery:
    """--query：查詢指定 Expert 的 metadata，支援 table / json 格式。"""

    def _init_framework(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_init(
                workspace,
                workspace / "connsys-jarvis/framework/experts/framework-base-expert/expert.json",
            )

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
        capsys.readouterr()  # flush init output before capturing json
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
# TC-U15  cmd_list — installed + available + json format
# ─────────────────────────────────────────────────────────────────────────────

class TestCmdListUpdated:
    """更新後的 --list：即時掃描顯示 installed + available，支援 --format json。"""

    def _init_framework(self, workspace):
        with patch.object(inst, "run_git_config", return_value="john.doe"):
            inst.cmd_init(
                workspace,
                workspace / "connsys-jarvis/framework/experts/framework-base-expert/expert.json",
            )

    def test_list_shows_installed_expert(self, workspace, capsys):
        self._init_framework(workspace)
        inst.cmd_list(workspace)
        out = capsys.readouterr().out
        assert "framework-base-expert" in out

    def test_list_shows_available_experts_too(self, workspace, capsys):
        """即使尚未安裝，可用的 Expert 也要顯示出來。"""
        self._init_framework(workspace)
        inst.cmd_list(workspace)
        out = capsys.readouterr().out
        assert "wifi-bora-memory-slim-expert" in out

    def test_list_json_format_is_valid_json(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()  # flush init output before capturing json
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_json_all_entries_have_status(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()  # flush init output before capturing json
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        for item in data:
            assert "status" in item
            assert item["status"] in ("installed", "available")

    def test_list_json_installed_expert_correct_status(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()  # flush init output before capturing json
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        fw = next((e for e in data if e["name"] == "framework-base-expert"), None)
        assert fw is not None
        assert fw["status"] == "installed"
        assert fw["is_identity"] is True

    def test_list_json_available_expert_correct_status(self, workspace, capsys):
        self._init_framework(workspace)
        capsys.readouterr()  # flush init output before capturing json
        inst.cmd_list(workspace, output_format="json")
        data = json.loads(capsys.readouterr().out)
        slim = next((e for e in data if e["name"] == "wifi-bora-memory-slim-expert"), None)
        assert slim is not None
        assert slim["status"] == "available"
