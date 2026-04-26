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
from datetime import datetime
from pathlib import Path

from . import config
from .assertions import run_all_checks, AssertResult
from .report import ReportEngine
from .runner import ClaudeRunner, SessionResult
from .token_analyzer import TokenAnalyzer

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
    """Execute a single test case, run assertion checks, and collect results.

    Args:
        runner: The configured ClaudeRunner instance.
        test_case: Test case definition from test_cases.json.
        expert_name: Expert name for context.

    Returns:
        Dictionary with test results including session, assert_results,
        and token_report for report generation.
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
            "status": "skipped",
            "session": None,
            "assert_results": [],
            "token_report": None,
        }

    # Get prompt
    prompt = test_case.get("prompt", "")
    if not prompt:
        logger.warning("Test case %s has no prompt, skipping", case_id)
        return {
            "id": case_id,
            "name": case_name,
            "status": "skipped",
            "session": None,
            "assert_results": [],
            "token_report": None,
        }

    # Resolve prompt base directory
    base_dir = config.TESTS_ROOT / expert_name

    # Execute Claude session
    timeout = test_case.get("timeout", config.DEFAULT_TIMEOUT)
    runner.executor.timeout = timeout
    session = runner.run(prompt, expert_name=expert_name, base_dir=base_dir)

    # Run 6-layer assertion checks
    checks = test_case.get("checks", {})
    workspace = runner.executor.workspace
    assert_results = run_all_checks(checks, session, workspace, base_dir)

    # Token analysis
    token_report = None
    if session.raw_json_lines:
        analyzer = TokenAnalyzer()
        token_report = analyzer.parse_session(session.raw_json_lines)

    # Determine pass/fail
    required_checks = [r for r in assert_results
                       if r.details.get("required", True)]
    all_passed = all(r.passed for r in required_checks) if required_checks else True
    status = "pass" if all_passed else "fail"

    return {
        "id": case_id,
        "name": case_name,
        "status": status,
        "session": session,
        "assert_results": assert_results,
        "token_report": token_report,
        "exit_code": session.exit_code,
        "duration": session.duration,
        "output_length": len(session.output),
        "json_lines_count": len(session.raw_json_lines),
        "model": session.model,
        "mode": session.mode,
        "log_path": str(session.log_path),
        "session_id": session.session_id,
        "token_budget": test_case.get("token_budget"),
    }


def cmd_run(args: argparse.Namespace) -> int:
    """Execute integration tests, run checks, and generate reports.

    Flow:
      1. For each (model, expert) combination, execute test cases
      2. Run 6-layer assertion checks on each result
      3. Feed results into ReportEngine
      4. Generate L1/L2/L3 reports (JSON + text)
      5. Print text report to stdout
      6. Optionally run session analysis

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 = all passed, 1 = any failures).
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

    has_failures = False
    all_raw_results = []  # for session analysis

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

            report_engine = ReportEngine()

            for test_case in test_data.get("test_cases", []):
                result = run_test_case(runner, test_case, expert_name)
                result["expert"] = expert_name
                result["model_key"] = model
                all_raw_results.append(result)

                # Feed into report engine
                report_engine.add_result(
                    case_id=result["id"],
                    case_name=result["name"],
                    session=result.get("session"),
                    assert_results=result.get("assert_results", []),
                    token_report=result.get("token_report"),
                )

                # Log per-case summary
                status = result.get("status", "unknown")
                duration = result.get("duration", 0)
                n_checks = len(result.get("assert_results", []))
                n_passed = sum(
                    1 for r in result.get("assert_results", []) if r.passed
                )
                logger.info(
                    "  [%s] %s: %s (%d/%d checks, %.1fs)",
                    result["id"], result["name"],
                    status, n_passed, n_checks, duration,
                )
                if status == "fail":
                    has_failures = True
                    for ar in result.get("assert_results", []):
                        if not ar.passed:
                            logger.warning(
                                "    FAIL [%s] %s", ar.check_type, ar.message
                            )

            # Generate reports for this (model, expert) pair
            reports = report_engine.generate(expert_name, model)

            # Save reports
            run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            report_dir = config.RESULTS_DIR / "reports" / f"{run_ts}_{expert_name}_{model}"
            report_engine.save(reports, report_dir)

            # Print text report to stdout
            text_report = report_engine.format_text(reports)
            print("\n" + text_report)

    # Save raw results for reference
    if all_raw_results:
        results_file = config.RESULTS_DIR / "latest_results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        # Serialize without non-serializable objects
        serializable = []
        for r in all_raw_results:
            sr = {
                k: v for k, v in r.items()
                if k not in ("session", "assert_results", "token_report")
            }
            # Add assert summary
            sr["checks_total"] = len(r.get("assert_results", []))
            sr["checks_passed"] = sum(
                1 for ar in r.get("assert_results", []) if ar.passed
            )
            sr["checks_failed"] = sr["checks_total"] - sr["checks_passed"]
            sr["check_details"] = [
                {
                    "type": ar.check_type,
                    "passed": ar.passed,
                    "message": ar.message,
                    "expected": ar.expected,
                    "actual": ar.actual,
                }
                for ar in r.get("assert_results", [])
            ]
            serializable.append(sr)
        with open(results_file, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2, ensure_ascii=False)
        logger.info("Results saved to: %s", results_file)

    # Session analysis
    if all_raw_results and not args.no_analysis:
        _run_session_analysis(all_raw_results)

    return 1 if has_failures else 0


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


def cmd_report(args: argparse.Namespace) -> int:
    """Display the latest saved report.

    Args:
        args: Parsed CLI arguments with --report and --format.

    Returns:
        Exit code.
    """
    # Find most recent report directory
    reports_base = config.RESULTS_DIR / "reports"
    if not reports_base.exists():
        logger.error("No reports found. Run tests first with --expert.")
        return 1

    # Find the latest report by modification time
    ext = "report.json" if args.format == "json" else "report.md"
    report_files = sorted(
        reports_base.glob(f"**/{ext}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not report_files:
        logger.error("No %s found under %s", ext, reports_base)
        return 1

    latest = report_files[0]
    logger.info("Loading report: %s", latest)
    print(latest.read_text(encoding="utf-8"))

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
    if args.report:
        return cmd_report(args)
    if args.scaffold:
        return cmd_scaffold(args)
    if args.expert or args.all:
        return cmd_run(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
