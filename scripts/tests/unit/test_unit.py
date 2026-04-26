"""
Unit Tests — connsys-jarvis setup.py
=====================================
測試最小可獨立執行單元（function / method level）。
不呼叫 cmd_* 函式，不依賴完整安裝流程。

Run:
    uvx pytest scripts/tests/unit/ -v
"""

from pathlib import Path
from unittest.mock import patch

# `inst` is injected via scripts/tests/conftest.py sys.path setup
import setup as inst


# ─────────────────────────────────────────────────────────────────────────────
# TC-U01  detect_scenario
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectScenario:
    """detect_scenario() 根據 workspace 中 .repo / .git 是否存在，回傳正確 scenario。"""

    def test_agent_first_empty_workspace(self, workspace):
        assert inst.detect_scenario(workspace) == "agent-first"

    def test_agent_first_codespace_exists(self, workspace):
        (workspace / "codespace").mkdir()
        assert inst.detect_scenario(workspace) == "agent-first"

    def test_legacy_repo_exists(self, legacy_workspace):
        assert inst.detect_scenario(legacy_workspace) == "legacy"

    def test_legacy_git_exists(self, workspace):
        (workspace / ".git").mkdir()
        assert inst.detect_scenario(workspace) == "legacy"


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
        scripts_dir = tmp_path / "hooks" / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "session-start-hook.sh").touch()
        (scripts_dir / "helper.py").touch()
        (scripts_dir / "README.md").touch()   # should be excluded
        result = inst.resolve_items(tmp_path, "hooks", "all")
        assert sorted(result) == ["helper.py", "session-start-hook.sh"]

    def test_all_list_notation(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-x").mkdir(parents=True)
        result = inst.resolve_items(tmp_path, "skills", ["all"])
        assert result == ["skill-x"]

    def test_all_uppercase_string(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-a").mkdir(parents=True)
        result = inst.resolve_items(tmp_path, "skills", "ALL")
        assert result == ["skill-a"]

    def test_all_uppercase_list(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-b").mkdir(parents=True)
        result = inst.resolve_items(tmp_path, "skills", ["ALL"])
        assert result == ["skill-b"]

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
        items = ["wifi-bora-lsp-tool", "wifi-bora-ast-tool", "framework-init-flow"]
        result = inst.apply_exclude_patterns(items, [".*-lsp-.*"])
        assert result == ["wifi-bora-ast-tool", "framework-init-flow"]

    def test_multiple_patterns(self):
        items = ["wifi-bora-lsp-tool", "wifi-bora-debug-flow", "framework-init-flow"]
        result = inst.apply_exclude_patterns(items, [".*-lsp-.*", ".*-debug-.*"])
        assert result == ["framework-init-flow"]

    def test_pattern_filters_nothing_when_no_match(self):
        items = ["skill-a", "skill-b"]
        result = inst.apply_exclude_patterns(items, [".*-lsp-.*"])
        assert result == ["skill-a", "skill-b"]


# ─────────────────────────────────────────────────────────────────────────────
# TC-U05  generate_claude_md — 單 Expert
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateClaudeMdSingle:
    """generate_claude_md() v2.0 — 單 Expert 情境下的輸出格式。"""

    def _installed(self, path: str, name: str) -> dict:
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
        assert "@CLAUDE.local.md" not in content

    def test_single_expert_has_using_knowhow_directive(self, workspace, framework_expert_json):
        """v3.0: CLAUDE.md 包含 using-knowhow skill 指示。"""
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "framework-base-expert-using-knowhow" in content
        assert "MUST use the skill" in content

    def test_single_expert_no_rules_or_duties(self, workspace, framework_expert_json):
        """v3.0 不輸出 rules.md / duties.md / soul.md / expert.md。"""
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "rules.md" not in content
        assert "duties.md" not in content
        assert "@connsys-jarvis" not in content  # 不再有 @include 行

    def test_html_comment_header(self, workspace, framework_expert_json):
        """v3.0 輸出以 HTML 註解開頭。"""
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert content.startswith("<!-- connsys-jarvis CLAUDE.md")
        assert "Auto-generated by setup.py v3.0" in content

    def test_expert_guidelines_section_present(self, workspace, framework_expert_json):
        """v3.0: ## Expert Guidelines 區段取代 Identity / Technical Reference。"""
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "## Expert Guidelines" in content
        assert "## Identity" not in content
        assert "## Technical Reference" not in content

    def test_single_expert_no_claude_local(self, workspace):
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "@CLAUDE.local.md" not in content

    def test_single_expert_header_contains_name(self, workspace, framework_expert_json):
        installed = self._installed(
            "framework/framework-base-expert/expert.json",
            "framework-base-expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "framework-base-expert" in content

    def test_v3_no_include_lines(self, workspace, tmp_path):
        """v3.0: 不論 soul.md / expert.md 是否存在，都不產生 @include 行。"""
        fake_dir = workspace / "connsys-jarvis" / "test-team" / "test-no-soul-expert"
        fake_dir.mkdir(parents=True, exist_ok=True)
        (fake_dir / "expert.json").write_text('{"name": "test-no-soul-expert"}')
        (fake_dir / "expert.md").write_text("# Expert")
        installed = self._installed(
            "test-team/test-no-soul-expert/expert.json",
            "test-no-soul-expert",
        )
        content = inst.generate_claude_md(workspace, installed)
        assert "soul.md" not in content
        assert "@connsys-jarvis" not in content
        assert "test-no-soul-expert-using-knowhow" in content


# ─────────────────────────────────────────────────────────────────────────────
# TC-U06  generate_claude_md — 多 Expert (v2.0)
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateClaudeMdMulti:
    """generate_claude_md() v3.0 — 多 Expert 情境：
      - 所有 expert 輸出 using-knowhow skill 指示
      - 不再有 @include soul.md / expert.md
    """

    def _two_experts(self) -> dict:
        return {
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

    def test_expert_guidelines_has_all_experts(self, workspace):
        """v3.0: ## Expert Guidelines 包含所有 expert 的 using-knowhow 指示。"""
        content = inst.generate_claude_md(workspace, self._two_experts())
        assert "## Expert Guidelines" in content
        assert "framework-base-expert-using-knowhow" in content
        assert "wifi-bora-memory-slim-expert-using-knowhow" in content

    def test_no_include_lines(self, workspace):
        """v3.0: 不再有 @include soul.md / expert.md。"""
        content = inst.generate_claude_md(workspace, self._two_experts())
        assert "@connsys-jarvis" not in content
        assert "## Identity" not in content
        assert "## Technical Reference" not in content

    def test_no_base_experts_section(self, workspace):
        """v3.0 移除 Base Experts 區段。"""
        content = inst.generate_claude_md(workspace, self._two_experts())
        assert "## Base Experts" not in content

    def test_no_expert_capabilities_section(self, workspace):
        """v3.0 移除 Expert Capabilities 區段。"""
        content = inst.generate_claude_md(workspace, self._two_experts())
        assert "## Expert Capabilities" not in content

    def test_html_comment_header_with_expert_names(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts())
        assert "<!-- connsys-jarvis CLAUDE.md" in content
        assert "framework-base-expert" in content
        assert "wifi-bora-memory-slim-expert" in content

    def test_multi_expert_no_claude_local(self, workspace):
        content = inst.generate_claude_md(workspace, self._two_experts())
        assert "@CLAUDE.local.md" not in content

    def test_must_lines_include_dependency_experts(self, workspace):
        """MUST lines cover installed experts AND their direct dependencies."""
        content = inst.generate_claude_md(workspace, self._two_experts())
        must_lines = [l for l in content.splitlines() if l.startswith("MUST use the skill")]
        # framework-base-expert (no deps) + wifi-bora-memory-slim-expert (3 deps)
        # deps: framework-base-expert (dedup), wifi-bora-base-expert, sys-bora-preflight-expert
        assert len(must_lines) >= 2
        assert "framework-base-expert-using-knowhow" in content
        assert "wifi-bora-memory-slim-expert-using-knowhow" in content
        assert "wifi-bora-base-expert-using-knowhow" in content
        assert "sys-bora-preflight-expert-using-knowhow" in content


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
