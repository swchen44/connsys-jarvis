"""Integration tests for wifi-bora-memory-slim-expert.

Tests dependency chain integrity, skill triggering, and cross-dependency
skill access. This Expert has the deepest dependency chain:

  wifi-bora-memory-slim-expert
  ├── framework-base-expert (5 skills + hooks + commands + agents + rules)
  ├── wifi-bora-base-expert (6 skills)
  │   └── sys-bora-base-expert (2 skills)
  └── sys-bora-preflight-expert (2 skills)
      └── sys-bora-base-expert (2 skills)  ← deduplicated

Total: 5 Experts, 18 Skills
"""

import json
import logging
import unittest
from pathlib import Path

from tests.claudecode import config
from tests.claudecode.assertions import run_all_checks, AssertResult
from tests.claudecode.dependency_checker import DependencyChecker
from tests.claudecode.runner import ClaudeRunner, SessionResult
from tests.claudecode.skill_checker import SkillChecker
from tests.claudecode.token_analyzer import TokenAnalyzer

logger = logging.getLogger(__name__)

EXPERT_NAME = "wifi-bora-memory-slim-expert"
EXPERT_DIR = config.TESTS_ROOT / EXPERT_NAME
TEST_CASES_FILE = EXPERT_DIR / "test_cases.json"

# Expected dependency chain (topological order, leaves first)
EXPECTED_CHAIN = [
    "sys-bora-base-expert",
    "framework-base-expert",
    "wifi-bora-base-expert",
    "sys-bora-preflight-expert",
    "wifi-bora-memory-slim-expert",
]


def load_test_cases() -> list[dict]:
    """Load test cases from JSON file.

    Returns:
        List of test case dictionaries.
    """
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("test_cases", [])


class TestDependencyChain(unittest.TestCase):
    """Test dependency chain integrity (MEM-001).

    Verifies that all 5 Experts in the dependency chain have
    correct plugin.json, expert.json, and skills directories.
    """

    checker: DependencyChecker

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize dependency checker."""
        cls.checker = DependencyChecker()

    def test_dependency_resolution(self) -> None:
        """MEM-001a: Verify dependency chain resolves correctly."""
        chain = self.checker.resolve_chain(EXPERT_NAME)
        chain_names = [n.name for n in chain]

        # All expected experts should be present
        for expected in EXPECTED_CHAIN:
            self.assertIn(
                expected, chain_names,
                f"Expected '{expected}' in dependency chain, "
                f"got: {chain_names}",
            )

        # Should have exactly 5 unique experts
        self.assertEqual(
            len(chain), 5,
            f"Expected 5 experts in chain, got {len(chain)}: {chain_names}",
        )

        logger.info(
            "Dependency chain: %s", " → ".join(chain_names)
        )

    def test_plugin_dirs_exist(self) -> None:
        """MEM-001b: Verify plugin.json exists for all Experts."""
        chain = self.checker.resolve_chain(EXPERT_NAME)
        results = self.checker.check_plugin_dirs(chain)

        plugin_checks = [
            r for r in results if r.check_type == "plugin_json"
        ]
        failures = [r for r in plugin_checks if not r.passed]

        if failures:
            msgs = "\n".join(f"  {r.message}" for r in failures)
            self.fail(f"Missing plugin.json:\n{msgs}")

    def test_expert_json_exist(self) -> None:
        """MEM-001c: Verify expert.json exists for all Experts."""
        chain = self.checker.resolve_chain(EXPERT_NAME)
        results = self.checker.check_plugin_dirs(chain)

        expert_checks = [
            r for r in results if r.check_type == "expert_json"
        ]
        failures = [r for r in expert_checks if not r.passed]

        if failures:
            msgs = "\n".join(f"  {r.message}" for r in failures)
            self.fail(f"Missing expert.json:\n{msgs}")

    def test_all_skills_dirs_exist(self) -> None:
        """MEM-001d: Verify SKILL.md exists for all skills in chain."""
        chain = self.checker.resolve_chain(EXPERT_NAME)
        results = self.checker.check_plugin_dirs(chain)

        skill_checks = [
            r for r in results if r.check_type == "skill_dir"
        ]
        failures = [r for r in skill_checks if not r.passed]

        if failures:
            msgs = "\n".join(f"  {r.message}" for r in failures)
            self.fail(
                f"{len(failures)} skill(s) missing SKILL.md:\n{msgs}"
            )

    def test_total_skill_count(self) -> None:
        """MEM-001e: Verify total skill count across chain is 18."""
        chain = self.checker.resolve_chain(EXPERT_NAME)
        availability = self.checker.check_skill_availability(chain)

        self.assertEqual(
            availability["total"], 18,
            f"Expected 18 skills, got {availability['total']}: "
            f"{availability['skills']}",
        )

        logger.info(
            "Total skills: %d — %s",
            availability["total"],
            ", ".join(availability["skills"]),
        )

    def test_full_check_report(self) -> None:
        """MEM-001f: Run full dependency check and verify all pass."""
        report = self.checker.full_check(EXPERT_NAME)
        self.assertTrue(
            report.all_passed,
            f"Dependency check had failures: "
            + "\n".join(
                f"  [{r.check_type}] {r.message}"
                for r in report.checks if not r.passed
            ),
        )


class TestMemorySlimSkills(unittest.TestCase):
    """Test skill triggering for wifi-bora-memory-slim-expert.

    Requires a properly configured workspace with the Expert installed.
    These tests invoke Claude Code and verify skill behavior.
    """

    runner: ClaudeRunner
    skill_checker: SkillChecker
    token_analyzer: TokenAnalyzer

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize shared test resources."""
        cls.runner = ClaudeRunner(
            mode=config.DEFAULT_MODE,
            model=config.DEFAULT_MODEL,
            verbose=True,
        )
        cls.skill_checker = SkillChecker(EXPERT_NAME)
        cls.token_analyzer = TokenAnalyzer()
        logger.info("Test suite initialized for %s", EXPERT_NAME)

    def _run_test_case(
        self, case_id: str
    ) -> tuple[SessionResult, list[AssertResult]]:
        """Run a single test case by ID.

        Args:
            case_id: The test case ID.

        Returns:
            Tuple of (session result, assertion results).
        """
        test_cases = load_test_cases()
        case = None
        for tc in test_cases:
            if tc.get("id") == case_id:
                case = tc
                break

        self.assertIsNotNone(case, f"Test case {case_id} not found")

        if case.get("type") == "dependency_check":
            self.skipTest(f"{case_id} is a dependency check")

        prompt = case.get("prompt", "")
        self.assertTrue(prompt, f"Test case {case_id} has no prompt")

        timeout = case.get("timeout", config.DEFAULT_TIMEOUT)
        self.runner.executor.timeout = timeout

        result = self.runner.run(
            prompt, expert_name=EXPERT_NAME, base_dir=EXPERT_DIR
        )

        checks = case.get("checks", {})
        workspace = self.runner.executor.workspace
        assert_results = run_all_checks(
            checks, result, workspace, EXPERT_DIR
        )

        return result, assert_results

    def test_mem_002_memslim_flow(self) -> None:
        """MEM-002: Verify memslim-flow skill triggers correctly."""
        result, assert_results = self._run_test_case("MEM-002")

        self.assertEqual(
            result.exit_code, 0,
            f"Claude exited with code {result.exit_code}",
        )

        failures = [r for r in assert_results if not r.passed]
        if failures:
            failure_msgs = "\n".join(
                f"  [{r.check_type}] {r.message}" for r in failures
            )
            self.fail(
                f"MEM-002 had {len(failures)} check failure(s):\n"
                f"{failure_msgs}"
            )

        # Token budget
        if result.raw_json_lines:
            report = self.token_analyzer.parse_session(
                result.raw_json_lines
            )
            self.assertLessEqual(
                report.total.total, 80000,
                f"Token usage {report.total.total} exceeds budget 80000",
            )

    def test_mem_003_lsp_tool(self) -> None:
        """MEM-003: Verify LSP tool skill triggers correctly."""
        result, assert_results = self._run_test_case("MEM-003")

        self.assertEqual(result.exit_code, 0)

        failures = [r for r in assert_results if not r.passed]
        if failures:
            failure_msgs = "\n".join(
                f"  [{r.check_type}] {r.message}" for r in failures
            )
            self.fail(
                f"MEM-003 had {len(failures)} check failure(s):\n"
                f"{failure_msgs}"
            )

    def test_mem_004_cross_dependency_access(self) -> None:
        """MEM-004: Verify cross-dependency skill access works."""
        result, assert_results = self._run_test_case("MEM-004")

        self.assertEqual(result.exit_code, 0)

        failures = [r for r in assert_results if not r.passed]
        if failures:
            failure_msgs = "\n".join(
                f"  [{r.check_type}] {r.message}" for r in failures
            )
            self.fail(
                f"MEM-004 had {len(failures)} check failure(s):\n"
                f"{failure_msgs}"
            )

    def test_skill_coverage(self) -> None:
        """Verify expected skill set for memory-slim expert.

        Checks that the SkillChecker correctly resolves all 18 skills
        from the dependency chain.
        """
        expected = self.skill_checker.expected_skills
        self.assertEqual(
            len(expected), 18,
            f"Expected 18 skills from dependency chain, "
            f"got {len(expected)}: "
            f"{[s.name for s in expected]}",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
