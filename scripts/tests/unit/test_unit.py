"""
Unit Tests — connsys-jarvis setup.py
=====================================
測試最小可獨立執行單元（function / method level）。
不呼叫 cmd_* 函式，不依賴完整安裝流程。

Run:
    uvx pytest scripts/tests/unit/ -v
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# `inst` is injected via scripts/tests/conftest.py sys.path setup
import setup as inst


# ─────────────────────────────────────────────────────────────────────────────
# TC-U01  detect_scenario
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectScenario:
    """detect_scenario() 根據 workspace 中 .repo 是否存在，回傳正確 scenario。"""

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
    """get_codespace_path() 在 agent-first 回傳 codespace/ subdir，legacy 回傳 workspace root。"""

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
    """resolve_items() 將 spec（None / list / "all"）展開為實際名稱清單。"""

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
        (hooks_dir / "README.md").touch()   # should be excluded
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
    """apply_exclude_patterns() 用 regex 過濾不需要的 symlink 名稱。"""

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
    """generate_claude_md() 在單 Expert 情境下的輸出格式。"""

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
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
            "Framework Base Expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "@connsys-jarvis/framework/framework-base-expert/soul.md" in content
        assert "@connsys-jarvis/framework/framework-base-expert/rules.md" in content
        assert "@connsys-jarvis/framework/framework-base-expert/duties.md" in content
        assert "@connsys-jarvis/framework/framework-base-expert/expert.md" in content

    def test_single_expert_ends_with_claude_local(self, workspace):
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
            "Framework Base Expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert content.strip().endswith("@CLAUDE.local.md")

    def test_single_expert_header_contains_display_name(self, workspace, framework_expert_json):
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
            "Framework Base Expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "Framework Base Expert" in content


# ─────────────────────────────────────────────────────────────────────────────
# TC-U06  generate_claude_md — 多 Expert
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateClaudeMdMulti:
    """generate_claude_md() 在多 Expert 情境下的兩種模式：
      - 預設（include_all_experts=False）：identity 四份文件 + Base Experts 區段
      - --with-all-experts（include_all_experts=True）：Identity + Base Experts + Capabilities
    """

    def _two_experts(self, include_all: bool = False) -> dict:
        return {
            "include_all_experts": include_all,
            "experts": [
                {
                    "name": "framework-base-expert",
                    "path": "framework/framework-base-expert/expert.json",
                    "is_identity": False,
                    "install_order": 1,
                },
                {
                    "name": "wifi-bora-memory-slim-expert",
                    "path": "wifi-bora/wifi-bora-memory-slim-expert/expert.json",
                    "is_identity": True,
                    "install_order": 2,
                },
            ]
        }

    # ── 預設模式（include_all_experts=False）──

    def test_default_identity_four_files_present(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "@connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/soul.md" in content
        assert "@connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/rules.md" in content
        assert "@connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/duties.md" in content
        assert "@connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/expert.md" in content

    def test_default_base_expert_section_present(self, workspace):
        # framework-base-expert is_base=True (non-identity) → must appear in Base Experts section
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "## Base Experts" in content

    def test_default_base_expert_has_all_four_files(self, workspace):
        # framework-base-expert is explicitly installed with is_base=True → all 4 files
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "@connsys-jarvis/framework/framework-base-expert/soul.md" in content
        assert "@connsys-jarvis/framework/framework-base-expert/rules.md" in content
        assert "@connsys-jarvis/framework/framework-base-expert/duties.md" in content
        assert "@connsys-jarvis/framework/framework-base-expert/expert.md" in content

    def test_default_dep_base_expert_has_all_four_files(self, workspace):
        # wifi-bora-base-expert is a dependency of identity (is_base=True) → all 4 files
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "@connsys-jarvis/wifi-bora/wifi-bora-base-expert/soul.md" in content
        assert "@connsys-jarvis/wifi-bora/wifi-bora-base-expert/expert.md" in content

    def test_default_no_expert_count_header(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert "2 Experts" not in content

    def test_default_ends_with_claude_local(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=False))
        assert content.strip().endswith("@CLAUDE.local.md")

    # ── --with-all-experts 模式（include_all_experts=True）──

    def test_with_all_experts_header_shows_count(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "2 Experts" in content

    def test_with_all_experts_identity_soul_present(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "@connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/soul.md" in content

    def test_with_all_experts_base_expert_expert_md_present(self, workspace):
        # framework-base-expert is_base=True → expert.md appears in Base Experts section
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "@connsys-jarvis/framework/framework-base-expert/expert.md" in content

    def test_with_all_experts_non_base_expert_md_in_capabilities(self, workspace):
        # wifi-bora-memory-slim-expert is_base=False (identity) → expert.md in Capabilities
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "@connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/expert.md" in content

    def test_with_all_experts_section_headers(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        assert "Expert Identity" in content
        assert "Base Experts" in content
        assert "Expert Capabilities" in content

    def test_with_all_experts_base_not_duplicated_in_capabilities(self, workspace):
        # framework-base-expert is_base=True → only in Base Experts, NOT in Capabilities
        content = inst.generate_claude_md(workspace, self._two_experts(include_all=True))
        cap_start = content.index("## Expert Capabilities")
        cap_section = content[cap_start:]
        assert "framework/framework-base-expert/expert.md" not in cap_section


# ─────────────────────────────────────────────────────────────────────────────
# TC-U06b  collect_base_experts
# ─────────────────────────────────────────────────────────────────────────────

class TestCollectBaseExperts:
    """collect_base_experts() 正確遍歷依賴樹，收集 is_base=True 的非 identity expert。"""

    def test_empty_experts_returns_empty(self, workspace):
        result = inst.collect_base_experts(workspace, {"experts": []})
        assert result == []

    def test_identity_base_expert_excluded(self, workspace):
        # framework-base-expert is identity AND is_base=True → excluded (already in main section)
        installed = {"experts": [{
            "name": "framework-base-expert",
            "path": "framework/framework-base-expert/expert.json",
            "is_identity": True,
            "install_order": 1,
        }]}
        result = inst.collect_base_experts(workspace, installed)
        fw_path = next((p for p in result if "framework-base-expert" in str(p)), None)
        assert fw_path is None

    def test_installed_non_identity_base_expert_included(self, workspace):
        # framework-base-expert is NOT identity and is_base=True → included
        installed = {
            "experts": [
                {
                    "name": "framework-base-expert",
                    "path": "framework/framework-base-expert/expert.json",
                    "is_identity": False,
                    "install_order": 1,
                },
                {
                    "name": "wifi-bora-memory-slim-expert",
                    "path": "wifi-bora/wifi-bora-memory-slim-expert/expert.json",
                    "is_identity": True,
                    "install_order": 2,
                },
            ]
        }
        result = inst.collect_base_experts(workspace, installed)
        result_strs = [str(p) for p in result]
        assert any("framework-base-expert" in s for s in result_strs)

    def test_dependency_base_expert_included(self, workspace):
        # wifi-bora-memory-slim-expert depends on wifi-bora-base-expert (is_base=True)
        installed = {"experts": [{
            "name": "wifi-bora-memory-slim-expert",
            "path": "wifi-bora/wifi-bora-memory-slim-expert/expert.json",
            "is_identity": True,
            "install_order": 1,
        }]}
        result = inst.collect_base_experts(workspace, installed)
        result_strs = [str(p) for p in result]
        assert any("wifi-bora-base-expert" in s for s in result_strs)

    def test_transitive_dependency_base_expert_included(self, workspace):
        # wifi-bora-memory-slim-expert → sys-bora-preflight-expert → sys-bora-base-expert (is_base=True)
        installed = {"experts": [{
            "name": "wifi-bora-memory-slim-expert",
            "path": "wifi-bora/wifi-bora-memory-slim-expert/expert.json",
            "is_identity": True,
            "install_order": 1,
        }]}
        result = inst.collect_base_experts(workspace, installed)
        result_strs = [str(p) for p in result]
        assert any("sys-bora-base-expert" in s for s in result_strs)

    def test_no_duplicates_in_result(self, workspace):
        # Both explicitly installed AND dependency → should appear only once
        installed = {
            "experts": [
                {
                    "name": "framework-base-expert",
                    "path": "framework/framework-base-expert/expert.json",
                    "is_identity": False,
                    "install_order": 1,
                },
                {
                    "name": "wifi-bora-memory-slim-expert",
                    "path": "wifi-bora/wifi-bora-memory-slim-expert/expert.json",
                    "is_identity": True,
                    "install_order": 2,
                },
            ]
        }
        result = inst.collect_base_experts(workspace, installed)
        result_strs = [str(p) for p in result]
        assert len(result_strs) == len(set(result_strs))


# ─────────────────────────────────────────────────────────────────────────────
# TC-U07  write_env_file
# ─────────────────────────────────────────────────────────────────────────────

class TestWriteEnvFile:
    """write_env_file() 產生正確的 .env 內容與變數格式。"""

    def _read_env(self, workspace: Path) -> dict:
        env_path = workspace / ".connsys-jarvis" / ".env"
        result = {}
        for line in env_path.read_text().splitlines():
            if line.startswith("export "):
                key, _, val = line[len("export "):].partition("=")
                result[key] = val.strip('"')
        return result

    def test_env_contains_all_six_vars(self, workspace):
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
        inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_PATH"].endswith("connsys-jarvis")

    def test_workspace_root_equals_workspace(self, workspace):
        inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_WORKSPACE_ROOT_PATH"] == str(workspace)

    def test_agent_first_codespace_path_has_codespace(self, workspace):
        inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_CODE_SPACE_PATH"].endswith("codespace")

    def test_legacy_codespace_path_equals_workspace(self, legacy_workspace):
        inst.write_env_file(legacy_workspace, "x")
        env_path = legacy_workspace / ".connsys-jarvis" / ".env"
        result = {}
        for line in env_path.read_text().splitlines():
            if line.startswith("export "):
                key, _, val = line[len("export "):].partition("=")
                result[key] = val.strip('"')
        assert result["CONNSYS_JARVIS_CODE_SPACE_PATH"] == str(legacy_workspace)

    def test_memory_path_inside_dot_dir(self, workspace):
        inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert ".connsys-jarvis/memory" in env["CONNSYS_JARVIS_MEMORY_PATH"]

    def test_employee_id_from_login_name(self, workspace):
        inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_EMPLOYEE_ID"] == Path.home().name

    def test_employee_id_fallback_when_login_unavailable(self, workspace):
        with patch.object(inst, "get_login_name", return_value="unknown"):
            inst.write_env_file(workspace, "x")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_EMPLOYEE_ID"] == "unknown"

    def test_active_expert_reflects_argument(self, workspace):
        inst.write_env_file(workspace, "wifi-bora-memory-slim-expert")
        env = self._read_env(workspace)
        assert env["CONNSYS_JARVIS_ACTIVE_EXPERT"] == "wifi-bora-memory-slim-expert"

    def test_all_vars_use_connsys_jarvis_prefix(self, workspace):
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
    """load/save_installed_experts() 的 JSON schema 格式與 round-trip 正確性。"""

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
        inst.save_installed_experts(workspace, data)
        reloaded = inst.load_installed_experts(workspace)
        assert "updated_at" in reloaded
