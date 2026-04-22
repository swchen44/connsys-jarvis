"""Template for creating new Expert integration tests.

Copy this file to tests/claudecode/{expert-name}/ and customize:
1. Update EXPERT_NAME to match the target Expert
2. Modify test methods to match test_cases.json
3. Adjust expected skill count for the Expert's dependency chain

Usage:
    python -m tests.claudecode.cli --scaffold {new-expert} \\
        --reference framework-base-expert
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

# TODO: Update these for the target Expert
EXPERT_NAME = "REPLACE_WITH_EXPERT_NAME"
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


class TestExpertTemplate(unittest.TestCase):
    """Integration test suite template.

    Rename this class to match the Expert, e.g., TestWifiLoganBase.
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

    # TODO: Add test methods for each test case in test_cases.json
    # Example:
    #
    # def test_case_001(self) -> None:
    #     """TC-001: Description."""
    #     result, assert_results = self._run_test_case("TC-001")
    #     self.assertEqual(result.exit_code, 0)
    #     failures = [r for r in assert_results if not r.passed]
    #     if failures:
    #         self.fail(f"TC-001: {len(failures)} check failures")

    def test_skill_coverage(self) -> None:
        """Verify expected skill set for this Expert."""
        expected = self.skill_checker.expected_skills
        self.assertGreater(
            len(expected), 0,
            "Expected skills list should not be empty",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
