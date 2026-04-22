"""Test report generator with three layers of analysis.

Produces quality reports (L1), invocation statistics (L2),
and behavior analysis (L3) from integration test results.
Supports JSON and plain text output formats.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .assertions import AssertResult
from .runner import SessionResult
from .token_analyzer import TokenAnalyzer, TokenReport, TokenUsage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report data classes
# ---------------------------------------------------------------------------

@dataclass
class TestCaseReport:
    """Report for a single test case."""

    case_id: str
    name: str
    status: str                  # "pass", "fail", "skip"
    check_results: list[dict] = field(default_factory=list)
    duration: float = 0.0
    token_usage: dict = field(default_factory=dict)
    nl_scores: dict = field(default_factory=dict)
    judge_score: float = 0.0


@dataclass
class L1QualityReport:
    """Layer 1: Quality assurance report."""

    expert: str
    model: str
    timestamp: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    skill_coverage: dict = field(default_factory=dict)
    nl_scores_avg: dict = field(default_factory=dict)
    judge_score_avg: float = 0.0
    test_results: list[TestCaseReport] = field(default_factory=list)


@dataclass
class L2StatisticsReport:
    """Layer 2: Invocation statistics report."""

    skills: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    total_tokens: dict = field(default_factory=dict)


@dataclass
class L3BehaviorReport:
    """Layer 3: Behavior analysis report."""

    phases: list[dict] = field(default_factory=list)
    efficiency: dict = field(default_factory=dict)
    timeline: list[dict] = field(default_factory=list)
    model_comparison: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Report Engine
# ---------------------------------------------------------------------------

class ReportEngine:
    """Generate three-layer reports from test results.

    Usage::

        engine = ReportEngine()
        engine.add_result("FW-001", session, assert_results, token_report)
        reports = engine.generate("framework-base-expert", "sonnet")
        engine.save(reports, output_dir)
    """

    def __init__(self):
        """Initialize report engine with empty result collectors."""
        self._results: list[dict] = []
        self._token_reports: list[TokenReport] = []
        self._all_assert_results: list[AssertResult] = []

    def add_result(
        self,
        case_id: str,
        case_name: str,
        session: SessionResult | None,
        assert_results: list[AssertResult],
        token_report: TokenReport | None = None,
    ) -> None:
        """Add a test case result.

        Args:
            case_id: Test case ID.
            case_name: Test case name.
            session: Claude Code session result.
            assert_results: List of assertion check results.
            token_report: Token analysis report (optional).
        """
        passed = all(r.passed for r in assert_results)
        self._results.append({
            "case_id": case_id,
            "name": case_name,
            "status": "pass" if passed else "fail",
            "assert_results": assert_results,
            "session": session,
            "token_report": token_report,
        })
        self._all_assert_results.extend(assert_results)
        if token_report:
            self._token_reports.append(token_report)

    def generate(
        self, expert_name: str, model: str
    ) -> dict:
        """Generate all three report layers.

        Args:
            expert_name: Expert being tested.
            model: Model used for testing.

        Returns:
            Dict with keys "L1", "L2", "L3" containing reports.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        l1 = self._generate_l1(expert_name, model, timestamp)
        l2 = self._generate_l2()
        l3 = self._generate_l3(model)

        return {"L1": l1, "L2": l2, "L3": l3}

    def _generate_l1(
        self, expert: str, model: str, timestamp: str
    ) -> L1QualityReport:
        """Generate Layer 1 quality report.

        Args:
            expert: Expert name.
            model: Model name.
            timestamp: ISO timestamp.

        Returns:
            L1QualityReport instance.
        """
        total = len(self._results)
        passed = sum(1 for r in self._results if r["status"] == "pass")
        failed = sum(1 for r in self._results if r["status"] == "fail")
        skipped = sum(1 for r in self._results if r["status"] == "skip")

        # Aggregate NL scores by aspect
        nl_scores: dict[str, list[float]] = {}
        judge_scores: list[float] = []

        for result in self._all_assert_results:
            if result.check_type == "nl_checks" and result.details:
                aspect = result.details.get("aspect", "unknown")
                score = result.details.get("score", 0)
                if aspect not in nl_scores:
                    nl_scores[aspect] = []
                nl_scores[aspect].append(score)
            elif result.check_type == "judge" and result.details:
                score = result.details.get("score", 0)
                if score > 0:
                    judge_scores.append(score)

        nl_avg = {}
        for aspect, scores in nl_scores.items():
            nl_avg[aspect] = {
                "avg": round(sum(scores) / len(scores), 1) if scores else 0,
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "count": len(scores),
            }

        judge_avg = (
            round(sum(judge_scores) / len(judge_scores), 1)
            if judge_scores else 0
        )

        # Build per-test-case reports
        test_reports = []
        for result in self._results:
            case_nl = {}
            case_judge = 0.0
            for ar in result["assert_results"]:
                if ar.check_type == "nl_checks" and ar.details:
                    case_nl[ar.details.get("aspect", "")] = ar.details.get("score", 0)
                elif ar.check_type == "judge" and ar.details:
                    case_judge = ar.details.get("score", 0)

            tr = result.get("token_report")
            test_reports.append(TestCaseReport(
                case_id=result["case_id"],
                name=result["name"],
                status=result["status"],
                check_results=[
                    {
                        "type": ar.check_type,
                        "passed": ar.passed,
                        "message": ar.message,
                    }
                    for ar in result["assert_results"]
                ],
                duration=result["session"].duration if result["session"] else 0,
                token_usage={
                    "total": tr.total.total if tr else 0,
                    "cost": tr.estimated_cost if tr else 0,
                },
                nl_scores=case_nl,
                judge_score=case_judge,
            ))

        return L1QualityReport(
            expert=expert,
            model=model,
            timestamp=timestamp,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=round(passed / max(total, 1), 2),
            nl_scores_avg=nl_avg,
            judge_score_avg=judge_avg,
            test_results=test_reports,
        )

    def _generate_l2(self) -> L2StatisticsReport:
        """Generate Layer 2 statistics report.

        Returns:
            L2StatisticsReport with skill/tool/failure statistics.
        """
        # Aggregate tool calls across all token reports
        tool_stats: dict[str, dict] = {}
        skill_stats: dict[str, dict] = {}
        failure_stats: dict[str, dict] = {}
        total_usage = TokenUsage()

        for tr in self._token_reports:
            total_usage.add(tr.total)

            # Tool statistics
            for tool_name, usage in tr.per_tool.items():
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {
                        "name": tool_name, "calls": 0,
                        "success": 0, "failed": 0, "tokens": 0,
                    }
                # Count calls for this tool
                tool_calls = [
                    c for c in tr.tool_calls if c.name == tool_name
                ]
                tool_stats[tool_name]["calls"] += len(tool_calls)
                tool_stats[tool_name]["success"] += sum(
                    1 for c in tool_calls if c.success
                )
                tool_stats[tool_name]["failed"] += sum(
                    1 for c in tool_calls if not c.success
                )
                tool_stats[tool_name]["tokens"] += usage.total

            # Skill statistics
            for skill_name, usage in tr.per_skill.items():
                if skill_name not in skill_stats:
                    skill_stats[skill_name] = {
                        "name": skill_name, "calls": 0,
                        "success": 0, "failed": 0, "tokens": 0,
                    }
                skill_calls = [
                    c for c in tr.tool_calls
                    if c.name == "Skill"
                    and c.input_args.get("skill") == skill_name
                ]
                skill_stats[skill_name]["calls"] += len(skill_calls)
                skill_stats[skill_name]["success"] += sum(
                    1 for c in skill_calls if c.success
                )
                skill_stats[skill_name]["failed"] += sum(
                    1 for c in skill_calls if not c.success
                )
                skill_stats[skill_name]["tokens"] += usage.total

            # Failure statistics
            for waste in tr.waste:
                wtype = waste.waste_type
                if wtype not in failure_stats:
                    failure_stats[wtype] = {
                        "type": wtype, "count": 0, "tokens": 0,
                        "examples": [],
                    }
                failure_stats[wtype]["count"] += 1
                failure_stats[wtype]["tokens"] += waste.tokens
                if len(failure_stats[wtype]["examples"]) < 3:
                    failure_stats[wtype]["examples"].append(
                        waste.description
                    )

        # Calculate ratios
        total_calls = sum(t["calls"] for t in tool_stats.values())
        for tool in tool_stats.values():
            tool["ratio"] = round(
                tool["calls"] / max(total_calls, 1), 3
            )

        return L2StatisticsReport(
            skills=sorted(
                skill_stats.values(),
                key=lambda x: x["tokens"], reverse=True,
            ),
            tools=sorted(
                tool_stats.values(),
                key=lambda x: x["tokens"], reverse=True,
            ),
            failures=sorted(
                failure_stats.values(),
                key=lambda x: x["count"], reverse=True,
            ),
            total_tokens={
                "input": total_usage.input_tokens,
                "output": total_usage.output_tokens,
                "cache_creation": total_usage.cache_creation_tokens,
                "cache_read": total_usage.cache_read_tokens,
                "total": total_usage.total,
            },
        )

    def _generate_l3(self, model: str) -> L3BehaviorReport:
        """Generate Layer 3 behavior analysis report.

        Args:
            model: Model name for cost calculation.

        Returns:
            L3BehaviorReport with phase and efficiency analysis.
        """
        # Aggregate phases
        phase_stats: dict[str, dict] = {}
        total_tokens = 0
        waste_tokens = 0

        for tr in self._token_reports:
            total_tokens += tr.total.total
            waste_tokens += sum(w.tokens for w in tr.waste)

            for phase in tr.phases:
                pname = phase.phase
                if pname not in phase_stats:
                    phase_stats[pname] = {
                        "phase": pname, "messages": 0,
                        "tokens": 0,
                    }
                phase_stats[pname]["messages"] += phase.message_count
                phase_stats[pname]["tokens"] += phase.tokens.total

        # Calculate ratios
        for phase in phase_stats.values():
            phase["ratio"] = round(
                phase["tokens"] / max(total_tokens, 1), 3
            )

        effective_tokens = total_tokens - waste_tokens

        return L3BehaviorReport(
            phases=sorted(
                phase_stats.values(),
                key=lambda x: x["tokens"], reverse=True,
            ),
            efficiency={
                "effective_tokens": effective_tokens,
                "effective_ratio": round(
                    effective_tokens / max(total_tokens, 1), 3
                ),
                "wasted_tokens": waste_tokens,
                "wasted_ratio": round(
                    waste_tokens / max(total_tokens, 1), 3
                ),
                "total_tokens": total_tokens,
            },
        )

    # ------------------------------------------------------------------
    # Output methods
    # ------------------------------------------------------------------

    def save(self, reports: dict, output_dir: Path) -> None:
        """Save reports to files.

        Args:
            reports: Dict with L1/L2/L3 report objects.
            output_dir: Directory to save reports.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON format
        json_data = {}
        for key, report in reports.items():
            json_data[key] = self._to_serializable(report)

        json_path = output_dir / "report.json"
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(json_data, fh, indent=2, ensure_ascii=False)
        logger.info("JSON report saved: %s", json_path)

        # Text format
        text_path = output_dir / "report.txt"
        text_content = self.format_text(reports)
        text_path.write_text(text_content, encoding="utf-8")
        logger.info("Text report saved: %s", text_path)

    @staticmethod
    def _to_serializable(obj) -> dict:
        """Convert dataclass to JSON-serializable dict.

        Args:
            obj: Dataclass instance.

        Returns:
            Serializable dict.
        """
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        return obj

    def format_text(self, reports: dict) -> str:
        """Format reports as human-readable text.

        Args:
            reports: Dict with L1/L2/L3 report objects.

        Returns:
            Formatted text string.
        """
        lines = []

        # L1: Quality
        l1 = reports.get("L1")
        if l1:
            lines.append("=" * 60)
            lines.append("  Layer 1: Quality Report")
            lines.append("=" * 60)
            lines.append(f"Expert: {l1.expert}")
            lines.append(f"Model:  {l1.model}")
            lines.append(f"Date:   {l1.timestamp}")
            lines.append("")
            lines.append(
                f"Test Results: {l1.passed}/{l1.total_tests} passed "
                f"({l1.pass_rate:.0%})"
            )
            for tr in l1.test_results:
                icon = "PASS" if tr.status == "pass" else "FAIL"
                lines.append(
                    f"  [{icon}] {tr.case_id} {tr.name} "
                    f"({tr.duration:.1f}s)"
                )
            lines.append("")
            if l1.nl_scores_avg:
                lines.append("NL Check Scores:")
                for aspect, stats in l1.nl_scores_avg.items():
                    lines.append(
                        f"  {aspect}: {stats['avg']}/10 "
                        f"(min={stats['min']}, max={stats['max']})"
                    )
            if l1.judge_score_avg:
                lines.append(f"Judge Score: {l1.judge_score_avg}/10")
            lines.append("")

        # L2: Statistics
        l2 = reports.get("L2")
        if l2:
            lines.append("=" * 60)
            lines.append("  Layer 2: Invocation Statistics")
            lines.append("=" * 60)

            if l2.skills:
                lines.append("\nSkill Statistics:")
                lines.append(
                    f"  {'Skill':<35} {'Calls':>5} {'OK':>4} "
                    f"{'Fail':>4} {'Tokens':>8}"
                )
                lines.append("  " + "-" * 58)
                for s in l2.skills:
                    lines.append(
                        f"  {s['name']:<35} {s['calls']:>5} "
                        f"{s['success']:>4} {s['failed']:>4} "
                        f"{s['tokens']:>8,}"
                    )

            if l2.tools:
                lines.append("\nTool Statistics:")
                lines.append(
                    f"  {'Tool':<20} {'Calls':>5} {'OK':>4} "
                    f"{'Fail':>4} {'Ratio':>6} {'Tokens':>8}"
                )
                lines.append("  " + "-" * 49)
                for t in l2.tools:
                    lines.append(
                        f"  {t['name']:<20} {t['calls']:>5} "
                        f"{t['success']:>4} {t['failed']:>4} "
                        f"{t['ratio']:>5.1%} {t['tokens']:>8,}"
                    )

            if l2.failures:
                lines.append("\nFailure Distribution:")
                for f in l2.failures:
                    lines.append(
                        f"  {f['type']}: {f['count']} occurrence(s), "
                        f"{f['tokens']:,} tokens"
                    )

            lines.append(
                f"\nTotal Tokens: {l2.total_tokens.get('total', 0):,}"
            )
            lines.append("")

        # L3: Behavior
        l3 = reports.get("L3")
        if l3:
            lines.append("=" * 60)
            lines.append("  Layer 3: Behavior Analysis")
            lines.append("=" * 60)

            if l3.phases:
                lines.append("\nBehavior Phases:")
                lines.append(
                    f"  {'Phase':<18} {'Messages':>8} "
                    f"{'Tokens':>8} {'Ratio':>6}"
                )
                lines.append("  " + "-" * 42)
                for p in l3.phases:
                    lines.append(
                        f"  {p['phase']:<18} {p['messages']:>8} "
                        f"{p['tokens']:>8,} {p['ratio']:>5.1%}"
                    )

            eff = l3.efficiency
            if eff:
                lines.append("\nToken Efficiency:")
                lines.append(
                    f"  Effective: {eff.get('effective_tokens', 0):,} "
                    f"({eff.get('effective_ratio', 0):.1%})"
                )
                lines.append(
                    f"  Wasted:    {eff.get('wasted_tokens', 0):,} "
                    f"({eff.get('wasted_ratio', 0):.1%})"
                )
                lines.append(
                    f"  Total:     {eff.get('total_tokens', 0):,}"
                )

        return "\n".join(lines)
