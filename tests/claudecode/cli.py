"""CLI entry point for the integration test framework.

Provides command-line interface for running Expert integration tests,
analyzing results, generating reports, and scaffolding new tests.

Usage::

    # Run tests for a specific Expert
    python -m tests.claudecode.cli --expert framework-base-expert

    # Run with tmux mode
    python -m tests.claudecode.cli --expert framework-base-expert --mode tmux

    # Multi-model comparison
    python -m tests.claudecode.cli --expert framework-base-expert \\
        --models sonnet,opus,haiku

    # Analyze existing results
    python -m tests.claudecode.cli --analyze .results/2026-04-22_103000/

    # Scaffold new Expert test
    python -m tests.claudecode.cli --scaffold wifi-logan-base-expert \\
        --reference framework-base-expert
"""

import argparse
import importlib.util
import json
import logging
import subprocess
import sys
from pathlib import Path

from . import config
from .runner import ClaudeRunner, SessionResult

logger = logging.getLogger(__name__)


def setup_logging(level: str = config.DEFAULT_LOG_LEVEL) -> None:
    """Configure logging with timestamp and module info.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR).
    """
    fmt = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def load_test_cases(expert_name: str) -> dict:
    """Load test_cases.json for the given Expert.

    Args:
        expert_name: Name of the Expert directory under tests/claudecode/.

    Returns:
        Parsed test cases dictionary.

    Raises:
        FileNotFoundError: If test_cases.json doesn't exist.
    """
    test_file = config.TESTS_ROOT / expert_name / "test_cases.json"
    if not test_file.exists():
        raise FileNotFoundError(
            f"No test_cases.json found for Expert: {expert_name}\n"
            f"  Expected at: {test_file}"
        )
    with open(test_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    logger.info(
        "Loaded %d test cases for %s",
        len(data.get("test_cases", [])), expert_name,
    )
    return data


def run_test_case(
    runner: ClaudeRunner,
    test_case: dict,
    expert_name: str,
) -> dict:
    """Execute a single test case and collect results.

    Args:
        runner: The configured ClaudeRunner instance.
        test_case: Test case definition from test_cases.json.
        expert_name: Expert name for context.

    Returns:
        Dictionary with test results, checks, and session data.
    """
    case_id = test_case.get("id", "unknown")
    case_name = test_case.get("name", "unnamed")
    logger.info("Running test case: %s (%s)", case_id, case_name)

    # Dependency-only checks don't need Claude execution
    if test_case.get("type") == "dependency_check":
        logger.info("Dependency check test — skipping Claude execution")
        return {
            "id": case_id,
            "name": case_name,
            "type": "dependency_check",
            "status": "pending_verification",
            "checks": test_case.get("checks", {}),
        }

    # Get prompt
    prompt = test_case.get("prompt", "")
    if not prompt:
        logger.warning("Test case %s has no prompt, skipping", case_id)
        return {
            "id": case_id,
            "name": case_name,
            "status": "skipped",
            "reason": "no prompt",
        }

    # Resolve prompt base directory
    base_dir = config.TESTS_ROOT / expert_name

    # Execute
    timeout = test_case.get("timeout", config.DEFAULT_TIMEOUT)
    runner.executor.timeout = timeout

    result = runner.run(prompt, expert_name=expert_name, base_dir=base_dir)

    return {
        "id": case_id,
        "name": case_name,
        "status": "executed",
        "exit_code": result.exit_code,
        "duration": result.duration,
        "output_length": len(result.output),
        "json_lines_count": len(result.raw_json_lines),
        "model": result.model,
        "mode": result.mode,
        "log_path": str(result.log_path),
        "session_id": result.session_id,
        "checks": test_case.get("checks", {}),
    }


def cmd_run(args: argparse.Namespace) -> int:
    """Execute integration tests for specified Expert(s).

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 = success, 1 = failures).
    """
    models = [args.model]
    if args.models:
        models = [m.strip() for m in args.models.split(",")]

    experts = []
    if args.all:
        # Find all Expert test directories
        for child in config.TESTS_ROOT.iterdir():
            if child.is_dir() and (child / "test_cases.json").exists():
                experts.append(child.name)
        if not experts:
            logger.error("No Expert test directories found")
            return 1
    elif args.expert:
        experts = [args.expert]
    else:
        logger.error("Specify --expert <name> or --all")
        return 1

    all_results = []

    for model in models:
        for expert_name in experts:
            logger.info(
                "=== Testing Expert: %s with model: %s ===",
                expert_name, model,
            )

            try:
                test_data = load_test_cases(expert_name)
            except FileNotFoundError as exc:
                logger.error("%s", exc)
                continue

            runner = ClaudeRunner(
                mode=args.mode,
                model=model,
                verbose=args.verbose,
            )

            for test_case in test_data.get("test_cases", []):
                result = run_test_case(runner, test_case, expert_name)
                result["expert"] = expert_name
                result["model_key"] = model
                all_results.append(result)

                # Log summary
                status = result.get("status", "unknown")
                logger.info(
                    "  [%s] %s: %s (%.1fs)",
                    result.get("id", "?"),
                    result.get("name", "?"),
                    status,
                    result.get("duration", 0),
                )

    # Save aggregated results
    if all_results:
        results_file = config.RESULTS_DIR / "latest_results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, "w", encoding="utf-8") as fh:
            json.dump(all_results, fh, indent=2, ensure_ascii=False)
        logger.info("Results saved to: %s", results_file)

    # --- Session Analysis Report ---
    # Collect session JSONL paths from test results and run analyzer
    if all_results and not args.no_analysis:
        _run_session_analysis(all_results)

    return 0


def _run_session_analysis(results: list[dict]) -> None:
    """Run framework-session-analyzer-tool on each session JSONL.

    Finds the session JSONL files from test results (saved in .results/)
    and runs analyze_session.py to produce HTML reports.

    Args:
        results: List of test result dicts from cmd_run.
    """
    analyzer_script = (
        config.JARVIS_ROOT
        / "framework" / "framework-base-expert" / "skills"
        / "framework-session-analyzer-tool" / "scripts"
        / "analyze_session.py"
    )

    if not analyzer_script.exists():
        logger.warning(
            "Session analyzer not found: %s — skipping analysis",
            analyzer_script,
        )
        return

    # Collect unique session log directories
    log_dirs: set[str] = set()
    for result in results:
        log_path = result.get("log_path", "")
        if log_path:
            log_dirs.add(log_path)

    if not log_dirs:
        logger.info("No session logs to analyze")
        return

    # Also try to find the Claude Code session JSONL from ~/.claude/
    # by looking for the most recent JSONL matching our session IDs
    session_ids = {
        r.get("session_id", "") for r in results if r.get("session_id")
    }
    analyzed_count = 0

    for session_id in session_ids:
        if not session_id:
            continue
        # Search for JSONL file
        jsonl_path = _find_session_jsonl(session_id)
        if not jsonl_path:
            logger.debug("JSONL not found for session %s", session_id[:16])
            continue

        # Output to .results/ under the session ID
        output_dir = config.RESULTS_DIR / "analysis" / session_id[:16]
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "=== Running Session Analysis: %s ===", session_id[:16]
        )
        try:
            proc = subprocess.run(
                [
                    sys.executable, str(analyzer_script),
                    str(jsonl_path),
                    "--output-dir", str(output_dir),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0:
                analyzed_count += 1
                html_report = output_dir / "report.html"
                if html_report.exists():
                    logger.info("HTML report: %s", html_report)
                    # Try to open in browser
                    try:
                        subprocess.run(
                            ["open", str(html_report)],
                            capture_output=True,
                            timeout=5,
                        )
                    except (subprocess.SubprocessError, OSError):
                        pass
            else:
                logger.warning(
                    "Analyzer failed (exit %d): %s",
                    proc.returncode,
                    proc.stderr[:200] if proc.stderr else "",
                )
        except subprocess.TimeoutExpired:
            logger.warning("Analyzer timed out for session %s", session_id[:16])
        except OSError as exc:
            logger.warning("Failed to run analyzer: %s", exc)

    if analyzed_count > 0:
        logger.info(
            "Session analysis complete: %d session(s) analyzed. "
            "Reports in %s",
            analyzed_count,
            config.RESULTS_DIR / "analysis",
        )
    else:
        logger.info(
            "No Claude Code session JSONLs found for analysis. "
            "Session JSONLs are at ~/.claude/projects/"
        )


def _find_session_jsonl(session_id: str) -> Path | None:
    """Find a Claude Code session JSONL file by session ID.

    Searches ~/.claude/projects/ for a matching JSONL filename.

    Args:
        session_id: Claude session UUID.

    Returns:
        Path to the JSONL file, or None if not found.
    """
    sessions_dir = config.CLAUDE_SESSIONS_DIR
    if not sessions_dir.exists():
        return None

    # Session files are named <session-id>.jsonl
    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue
        jsonl_path = project_dir / f"{session_id}.jsonl"
        if jsonl_path.exists():
            return jsonl_path

    return None


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze existing test results.

    Args:
        args: Parsed CLI arguments with --analyze path.

    Returns:
        Exit code.
    """
    results_path = Path(args.analyze)
    if not results_path.exists():
        logger.error("Results path not found: %s", results_path)
        return 1

    logger.info("Analyzing results from: %s", results_path)
    # TODO: Implement with token_analyzer and report modules
    logger.warning("Analysis not yet implemented — coming in Phase 2/5")
    return 0


def cmd_scaffold(args: argparse.Namespace) -> int:
    """Scaffold a new Expert test from a reference.

    Args:
        args: Parsed CLI arguments with --scaffold and --reference.

    Returns:
        Exit code.
    """
    new_expert = args.scaffold
    reference = args.reference or "framework-base-expert"

    ref_dir = config.TESTS_ROOT / reference
    new_dir = config.TESTS_ROOT / new_expert

    if not ref_dir.exists():
        logger.error("Reference Expert not found: %s", ref_dir)
        return 1

    if new_dir.exists():
        logger.error("Target directory already exists: %s", new_dir)
        return 1

    logger.info(
        "Scaffolding %s from reference %s", new_expert, reference
    )
    # TODO: Implement scaffolding in Phase 5
    logger.warning("Scaffolding not yet implemented — coming in Phase 5")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="python -m tests.claudecode.cli",
        description="Connsys Jarvis Expert Integration Test Framework",
    )

    # Execution mode
    mode_group = parser.add_argument_group("execution mode")
    mode_group.add_argument(
        "--mode",
        choices=["headless", "tmux"],
        default=config.DEFAULT_MODE,
        help="Execution mode (default: %(default)s)",
    )

    # Expert selection
    expert_group = parser.add_argument_group("expert selection")
    expert_mutex = expert_group.add_mutually_exclusive_group()
    expert_mutex.add_argument(
        "--expert",
        help="Run tests for a specific Expert",
    )
    expert_mutex.add_argument(
        "--all",
        action="store_true",
        help="Run tests for all Experts with test_cases.json",
    )

    # Model selection
    model_group = parser.add_argument_group("model selection")
    model_mutex = model_group.add_mutually_exclusive_group()
    model_mutex.add_argument(
        "--model",
        default=config.DEFAULT_MODEL,
        help="Model to use (default: %(default)s)",
    )
    model_mutex.add_argument(
        "--models",
        help="Comma-separated models for comparison (e.g., sonnet,opus,haiku)",
    )

    # Analysis and reporting
    analysis_group = parser.add_argument_group("analysis & reporting")
    analysis_group.add_argument(
        "--analyze",
        metavar="PATH",
        help="Analyze existing results from PATH",
    )
    analysis_group.add_argument(
        "--report",
        action="store_true",
        help="Generate report from latest results",
    )
    analysis_group.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Report output format (default: %(default)s)",
    )
    analysis_group.add_argument(
        "--no-analysis",
        action="store_true",
        help="Skip session analysis report after tests",
    )

    # Scaffolding
    scaffold_group = parser.add_argument_group("scaffolding")
    scaffold_group.add_argument(
        "--scaffold",
        metavar="EXPERT",
        help="Scaffold new Expert test directory",
    )
    scaffold_group.add_argument(
        "--reference",
        metavar="EXPERT",
        help="Reference Expert for scaffolding (default: framework-base-expert)",
    )

    # Logging
    log_group = parser.add_argument_group("logging")
    log_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    log_group.add_argument(
        "--log-level",
        default=config.DEFAULT_LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: %(default)s)",
    )

    return parser


def main() -> int:
    """CLI main entry point.

    Returns:
        Exit code.
    """
    parser = build_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else args.log_level
    setup_logging(log_level)

    # Route to subcommand
    if args.analyze:
        return cmd_analyze(args)
    if args.scaffold:
        return cmd_scaffold(args)
    if args.expert or args.all:
        return cmd_run(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
