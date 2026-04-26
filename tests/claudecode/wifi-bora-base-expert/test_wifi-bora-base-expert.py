"""Integration tests for wifi-bora-base-expert.

Tests skill triggering, output quality, and token efficiency
for the wifi-bora-base-expert's skills:
  - wifi-bora-base-expert-using-knowhow (MANDATORY)
  - wifi-bora-build-flow
  - wifi-bora-arch-knowhow
  - wifi-bora-memory-knowhow
  - wifi-bora-protocol-knowhow
  - wifi-bora-linkerscript-knowhow
  - wifi-bora-symbolmap-knowhow
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

EXPERT_NAME = "wifi-bora-base-expert"
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


class TestWifiBoraBaseExpert(unittest.TestCase):
    """Integration test suite for wifi-bora-base-expert."""

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
            case_id: The test case ID (e.g., "WB-001").

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

    def test_wb_001_hello_world_with_size_check(self) -> None:
        """WB-001: Verify hello world + size check triggers correct skills.

        Expected skills:
          - wifi-bora-base-expert-using-knowhow (MANDATORY, first)
          - wifi-bora-build-flow (build knowledge)
          - wifi-bora-memory-knowhow (size analysis)
          - wifi-bora-arch-knowhow (firmware architecture, optional)
        """
        result, assert_results = self._run_test_case("WB-001")

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
                f"WB-001 had {len(failures)} check failure(s):\n{failure_msgs}"
            )

        # Token budget check
        if result.raw_json_lines:
            report = self.token_analyzer.parse_session(result.raw_json_lines)
            self.assertLessEqual(
                report.total.total, 80000,
                f"Token usage {report.total.total} exceeds budget 80000",
            )


if __name__ == "__main__":
    unittest.main()
