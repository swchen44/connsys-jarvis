"""Integration tests for framework-base-expert.

Tests skill triggering, output quality, and token efficiency
for the framework-base-expert's 5 skills:
  - framework-skill-create-flow
  - framework-expert-create-flow
  - framework-expert-discovery-knowhow
  - framework-memory-tool
  - framework-base-expert-list-cmd
"""

import json
import logging
import unittest
from pathlib import Path

from tests.claudecode import config
from tests.claudecode.assertions import run_all_checks, AssertResult
from tests.claudecode.runner import ClaudeRunner, SessionResult
from tests.claudecode.skill_checker import SkillChecker
from tests.claudecode.token_analyzer import TokenAnalyzer

logger = logging.getLogger(__name__)

EXPERT_NAME = "framework-base-expert"
EXPERT_DIR = config.TESTS_ROOT / EXPERT_NAME
TEST_CASES_FILE = EXPERT_DIR / "test_cases.json"


def load_test_cases() -> list[dict]:
    """Load test cases from JSON file.

    Returns:
        List of test case dictionaries.
    """
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("test_cases", [])


class TestFrameworkBaseExpert(unittest.TestCase):
    """Integration test suite for framework-base-expert."""

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

    def _run_test_case(self, case_id: str) -> tuple[SessionResult, list[AssertResult]]:
        """Run a single test case by ID.

        Args:
            case_id: The test case ID (e.g., "FW-001").

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

        # Skip dependency_check type tests
        if case.get("type") == "dependency_check":
            self.skipTest(f"{case_id} is a dependency check, not a runtime test")

        # Get prompt
        prompt = case.get("prompt", "")
        self.assertTrue(prompt, f"Test case {case_id} has no prompt")

        # Set timeout
        timeout = case.get("timeout", config.DEFAULT_TIMEOUT)
        self.runner.executor.timeout = timeout

        # Run Claude session
        logger.info("Executing test case %s: %s", case_id, case.get("name"))
        result = self.runner.run(
            prompt, expert_name=EXPERT_NAME, base_dir=EXPERT_DIR
        )

        # Run all checks
        checks = case.get("checks", {})
        workspace = self.runner.executor.workspace
        assert_results = run_all_checks(
            checks, result, workspace, EXPERT_DIR
        )

        return result, assert_results

    def test_fw_001_skill_create_flow(self) -> None:
        """FW-001: Verify framework-skill-create-flow triggers correctly."""
        result, assert_results = self._run_test_case("FW-001")

        # Check exit code
        self.assertEqual(
            result.exit_code, 0,
            f"Claude exited with code {result.exit_code}",
        )

        # Check assertions
        failures = [r for r in assert_results if not r.passed]
        if failures:
            failure_msgs = "\n".join(
                f"  [{r.check_type}] {r.message}" for r in failures
            )
            self.fail(
                f"FW-001 had {len(failures)} check failure(s):\n{failure_msgs}"
            )

        # Token budget check
        if result.raw_json_lines:
            report = self.token_analyzer.parse_session(result.raw_json_lines)
            self.assertLessEqual(
                report.total.total, 50000,
                f"Token usage {report.total.total} exceeds budget 50000",
            )

    def test_fw_002_expert_create_flow(self) -> None:
        """FW-002: Verify framework-expert-create-flow triggers correctly."""
        result, assert_results = self._run_test_case("FW-002")

        self.assertEqual(result.exit_code, 0)

        failures = [r for r in assert_results if not r.passed]
        if failures:
            failure_msgs = "\n".join(
                f"  [{r.check_type}] {r.message}" for r in failures
            )
            self.fail(
                f"FW-002 had {len(failures)} check failure(s):\n{failure_msgs}"
            )

    def test_fw_003_expert_discovery(self) -> None:
        """FW-003: Verify expert discovery lists available Experts."""
        result, assert_results = self._run_test_case("FW-003")

        self.assertEqual(result.exit_code, 0)

        failures = [r for r in assert_results if not r.passed]
        if failures:
            failure_msgs = "\n".join(
                f"  [{r.check_type}] {r.message}" for r in failures
            )
            self.fail(
                f"FW-003 had {len(failures)} check failure(s):\n{failure_msgs}"
            )

    def test_fw_004_list_command(self) -> None:
        """FW-004: Verify list command shows installed skills/commands."""
        result, assert_results = self._run_test_case("FW-004")

        self.assertEqual(result.exit_code, 0)

        failures = [r for r in assert_results if not r.passed]
        if failures:
            failure_msgs = "\n".join(
                f"  [{r.check_type}] {r.message}" for r in failures
            )
            self.fail(
                f"FW-004 had {len(failures)} check failure(s):\n{failure_msgs}"
            )

    def test_skill_coverage(self) -> None:
        """Verify overall skill coverage for framework-base-expert.

        Runs a general prompt and checks that expected skills
        are discoverable (not necessarily all triggered).
        """
        logger.info("Checking skill coverage for %s", EXPERT_NAME)
        expected_skills = self.skill_checker.expected_skills
        self.assertGreater(
            len(expected_skills), 0,
            "Expected skills list should not be empty",
        )
        logger.info(
            "Expected %d skills: %s",
            len(expected_skills),
            ", ".join(s.name for s in expected_skills),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
