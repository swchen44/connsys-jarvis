"""Assertion library for integration test verification.

Provides six layers of checks: file creation, skill invocation,
tool calls, output content, natural language evaluation, and judge scoring.
Each assertion returns an AssertResult with pass/fail and context.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .runner import ClaudeRunner, HeadlessExecutor, JudgeResult, SessionResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------------------

@dataclass
class AssertResult:
    """Result of a single assertion check."""

    passed: bool
    check_type: str              # e.g., "files_created", "skills_invoked"
    check_id: str = ""           # e.g., "FW-001:nl-01"
    message: str = ""            # Human-readable description
    expected: str = ""           # What was expected
    actual: str = ""             # What was found
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Layer 1: File creation checks
# ---------------------------------------------------------------------------

def check_files_created(
    checks: list[dict],
    workspace: Path,
) -> list[AssertResult]:
    """Verify expected files were created with correct content.

    Args:
        checks: List of file check specs from test_cases.json.
        workspace: Root directory to resolve relative paths.

    Returns:
        List of assertion results.
    """
    results = []
    for spec in checks:
        file_path = workspace / spec["path"]
        exists = file_path.exists()

        if spec.get("exists") is not None:
            # Simple existence check
            results.append(AssertResult(
                passed=exists == spec["exists"],
                check_type="files_created",
                message=f"File {'exists' if exists else 'missing'}: {spec['path']}",
                expected=f"exists={spec['exists']}",
                actual=f"exists={exists}",
            ))
            continue

        if not exists:
            results.append(AssertResult(
                passed=False,
                check_type="files_created",
                message=f"File not found: {spec['path']}",
                expected=f"File at {spec['path']}",
                actual="File does not exist",
            ))
            continue

        # Content keyword checks
        contains_keywords = spec.get("contains", [])
        if contains_keywords:
            content = file_path.read_text(encoding="utf-8")
            missing = [kw for kw in contains_keywords if kw not in content]
            results.append(AssertResult(
                passed=len(missing) == 0,
                check_type="files_created",
                message=(
                    f"File {spec['path']}: "
                    f"{'all keywords found' if not missing else f'missing: {missing}'}"
                ),
                expected=f"Contains: {contains_keywords}",
                actual=f"Missing: {missing}" if missing else "All found",
                details={"path": spec["path"], "missing_keywords": missing},
            ))
        else:
            results.append(AssertResult(
                passed=True,
                check_type="files_created",
                message=f"File exists: {spec['path']}",
                expected=f"File at {spec['path']}",
                actual="File exists",
            ))

    return results


# ---------------------------------------------------------------------------
# Layer 2: Skill invocation checks
# ---------------------------------------------------------------------------

def _extract_skill_invocations(session: SessionResult) -> list[dict]:
    """Extract Skill invocations from session JSON lines.

    Detects skills triggered via two patterns:
      1. Skill tool_use (explicit skill invocation)
      2. Read tool_use reading a SKILL.md file (implicit skill loading)

    Both patterns count as the skill being "invoked" because Claude
    accesses the skill's content either way.

    Args:
        session: The session result to analyze.

    Returns:
        List of skill invocation records.
    """
    invocations = []
    seen_skills: set = set()
    for line in session.raw_json_lines:
        if line.get("type") != "assistant":
            continue
        content = line.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") != "tool_use":
                continue
            tool_name = block.get("name", "")
            tool_input = block.get("input", {})

            skill_name = ""

            # Pattern 1: Skill tool invocations
            if tool_name == "Skill":
                skill_name = tool_input.get("skill", "")

            # Pattern 2: Read of SKILL.md (implicit skill loading)
            elif tool_name == "Read":
                file_path = tool_input.get("file_path", "")
                if "/skills/" in file_path and "SKILL.md" in file_path:
                    # Extract skill name from path:
                    # .../skills/{skill-name}/SKILL.md
                    parts = file_path.split("/skills/")
                    if len(parts) > 1:
                        skill_name = parts[1].split("/")[0]

            if skill_name and skill_name not in seen_skills:
                seen_skills.add(skill_name)
                invocations.append({
                    "tool": tool_name,
                    "skill": skill_name,
                    "id": block.get("id", ""),
                })
    return invocations


def check_skills_invoked(
    checks: list[dict],
    session: SessionResult,
) -> list[AssertResult]:
    """Verify expected skills were invoked during the session.

    Args:
        checks: List of skill check specs.
        session: The session result to verify.

    Returns:
        List of assertion results.
    """
    invocations = _extract_skill_invocations(session)
    invoked_names = {inv["skill"] for inv in invocations}
    logger.debug("Skills invoked: %s", invoked_names)

    results = []
    for spec in checks:
        skill_name = spec["skill"]
        required = spec.get("required", True)
        was_invoked = skill_name in invoked_names

        if required:
            results.append(AssertResult(
                passed=was_invoked,
                check_type="skills_invoked",
                message=(
                    f"Skill '{skill_name}': "
                    f"{'invoked' if was_invoked else 'NOT invoked (required)'}"
                ),
                expected=f"Skill '{skill_name}' invoked",
                actual=f"{'Invoked' if was_invoked else 'Not invoked'}",
                details={"skill": skill_name, "required": True},
            ))
        else:
            # Optional — just report, always pass
            results.append(AssertResult(
                passed=True,
                check_type="skills_invoked",
                message=(
                    f"Skill '{skill_name}' (optional): "
                    f"{'invoked' if was_invoked else 'not invoked'}"
                ),
                expected="Optional",
                actual=f"{'Invoked' if was_invoked else 'Not invoked'}",
                details={"skill": skill_name, "required": False},
            ))

    return results


# ---------------------------------------------------------------------------
# Layer 3: Tool call checks
# ---------------------------------------------------------------------------

def _extract_tool_calls(session: SessionResult) -> list[dict]:
    """Extract all tool calls from session JSON lines.

    Args:
        session: The session result.

    Returns:
        List of tool call records with name, input, and id.
    """
    calls = []
    for line in session.raw_json_lines:
        if line.get("type") != "assistant":
            continue
        content = line.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_use":
                calls.append({
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                    "id": block.get("id", ""),
                })
    return calls


def check_tools_called(
    checks: list[dict],
    session: SessionResult,
) -> list[AssertResult]:
    """Verify expected tools were called with correct patterns.

    Args:
        checks: List of tool check specs.
        session: The session result.

    Returns:
        List of assertion results.
    """
    tool_calls = _extract_tool_calls(session)
    results = []

    for spec in checks:
        tool_name = spec["tool"]
        min_count = spec.get("min_count", 1)
        args_contain = spec.get("args_contain", "")

        # Count matching calls
        matching = []
        for call in tool_calls:
            if call["name"] != tool_name:
                continue
            if args_contain:
                input_str = json.dumps(call["input"], ensure_ascii=False)
                if args_contain not in input_str:
                    continue
            matching.append(call)

        count = len(matching)
        passed = count >= min_count

        msg_parts = [f"Tool '{tool_name}': {count} call(s)"]
        if args_contain:
            msg_parts.append(f"(args contain '{args_contain}')")
        msg_parts.append(f"{'>=' if passed else '<'} {min_count} required")

        results.append(AssertResult(
            passed=passed,
            check_type="tools_called",
            message=" ".join(msg_parts),
            expected=f">= {min_count} calls",
            actual=f"{count} calls",
            details={
                "tool": tool_name,
                "count": count,
                "min_count": min_count,
            },
        ))

    return results


# ---------------------------------------------------------------------------
# Layer 4: Output content checks
# ---------------------------------------------------------------------------

def check_output_contains(
    patterns: list[str],
    output: str,
) -> list[AssertResult]:
    """Verify output contains expected patterns.

    Args:
        patterns: List of strings that should be in the output.
        output: The session output text.

    Returns:
        List of assertion results.
    """
    results = []
    for pattern in patterns:
        found = pattern.lower() in output.lower()
        results.append(AssertResult(
            passed=found,
            check_type="output_contains",
            message=f"Output {'contains' if found else 'MISSING'}: '{pattern}'",
            expected=f"Contains '{pattern}'",
            actual=f"{'Found' if found else 'Not found'}",
        ))
    return results


def check_output_not_contains(
    patterns: list[str],
    output: str,
) -> list[AssertResult]:
    """Verify output does NOT contain unwanted patterns.

    Args:
        patterns: List of strings that should NOT be in the output.
        output: The session output text.

    Returns:
        List of assertion results.
    """
    results = []
    for pattern in patterns:
        found = pattern.lower() in output.lower()
        results.append(AssertResult(
            passed=not found,
            check_type="output_not_contains",
            message=(
                f"Output {'unexpectedly contains' if found else 'correctly excludes'}"
                f": '{pattern}'"
            ),
            expected=f"Does not contain '{pattern}'",
            actual=f"{'Found (bad)' if found else 'Not found (good)'}",
        ))
    return results


# ---------------------------------------------------------------------------
# Layer 5: Natural language checks (LLM-as-judge)
# ---------------------------------------------------------------------------

def check_nl(
    nl_checks: list[dict],
    session: SessionResult,
    base_dir: Path,
) -> list[AssertResult]:
    """Run natural language evaluations using LLM-as-judge.

    Each nl_check defines an aspect, question, scale, and min_pass.
    A cheap model evaluates the session output and returns a 1-N score.

    Args:
        nl_checks: List of NL check specs from test_cases.json.
        session: The session result being evaluated.
        base_dir: Base directory for resolving reference file paths.

    Returns:
        List of assertion results with scores.
    """
    results = []

    for check in nl_checks:
        check_id = check.get("id", "nl-?")
        aspect = check.get("aspect", "quality")
        question = check.get("question", "")
        model = check.get("model", config.DEFAULT_JUDGE_MODEL)
        scale = check.get("scale", 10)
        min_pass = check.get("min_pass", 5)

        # Load reference if specified
        reference_section = ""
        ref_path = check.get("reference", "")
        if ref_path:
            ref_file = base_dir / ref_path
            if ref_file.exists():
                ref_content = ref_file.read_text(encoding="utf-8").strip()
                reference_section = f"## 參考答案：\n{ref_content}"
            else:
                logger.warning(
                    "Reference file not found: %s", ref_file
                )

        # Build evaluation prompt
        prompt = config.NL_CHECK_PROMPT_TEMPLATE.format(
            scale=scale,
            aspect=aspect,
            question=question,
            reference_section=reference_section,
            output=session.output[:5000],  # Truncate to avoid token waste
        )

        # Execute judge via headless mode
        logger.info("Running NL check %s (aspect=%s)", check_id, aspect)
        judge_executor = HeadlessExecutor(model=model, timeout=60)
        judge_session = judge_executor.execute(prompt)

        # Parse score
        judge_result = _parse_nl_score(judge_session.output, model, aspect)

        passed = judge_result.score >= min_pass
        results.append(AssertResult(
            passed=passed,
            check_type="nl_checks",
            check_id=check_id,
            message=(
                f"NL[{aspect}]: {judge_result.score}/{scale} "
                f"{'PASS' if passed else 'FAIL'} (min={min_pass}) "
                f"— {judge_result.reason}"
            ),
            expected=f">= {min_pass}/{scale}",
            actual=f"{judge_result.score}/{scale}",
            details={
                "aspect": aspect,
                "score": judge_result.score,
                "reason": judge_result.reason,
                "min_pass": min_pass,
                "scale": scale,
                "model": model,
            },
        ))

    return results


def _parse_nl_score(output: str, model: str, aspect: str) -> JudgeResult:
    """Parse the NL check judge response.

    Args:
        output: Raw judge output.
        model: Judge model name.
        aspect: The evaluation aspect.

    Returns:
        JudgeResult with score and reason.
    """
    try:
        # Try to extract JSON from output
        json_match = re.search(r'\{[^}]*"score"[^}]*\}', output)
        if json_match:
            data = json.loads(json_match.group())
            return JudgeResult(
                score=float(data.get("score", 0)),
                reason=data.get("reason", ""),
                model=model,
                aspect=aspect,
            )
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("NL score parse error: %s", exc)

    return JudgeResult(score=0.0, reason="Parse error", model=model, aspect=aspect)


# ---------------------------------------------------------------------------
# Layer 6: Judge overall scoring
# ---------------------------------------------------------------------------

def check_judge(
    judge_spec: dict,
    session: SessionResult,
    base_dir: Path,
) -> AssertResult:
    """Run overall quality judge evaluation.

    Args:
        judge_spec: Judge configuration from test_cases.json.
        session: The session result.
        base_dir: Base directory for rubric file.

    Returns:
        Single assertion result.
    """
    if not judge_spec.get("enabled", False):
        return AssertResult(
            passed=True,
            check_type="judge",
            message="Judge disabled for this test case",
        )

    model = judge_spec.get("model", config.DEFAULT_JUDGE_MODEL)
    min_score = judge_spec.get("min_score", 5)
    rubric_path = judge_spec.get("rubric", "")

    # Load rubric
    rubric_text = ""
    if rubric_path:
        rubric_file = base_dir / rubric_path
        if rubric_file.exists():
            rubric_text = rubric_file.read_text(encoding="utf-8").strip()
        else:
            logger.warning("Rubric file not found: %s", rubric_file)

    # Build judge prompt
    prompt = (
        "你是一個 AI 回應品質總評者。\n"
        f"請對以下 AI 回應做整體品質評分 1-10 分。\n\n"
    )
    if rubric_text:
        prompt += f"## 評分標準：\n{rubric_text}\n\n"
    prompt += (
        f"## AI 的實際回應：\n{session.output[:5000]}\n\n"
        '請嚴格按照 JSON 格式回答：\n'
        '{"score": <整數 1-10>, "reason": "<一句話說明理由>"}'
    )

    logger.info("Running judge evaluation with model=%s", model)
    judge_executor = HeadlessExecutor(model=model, timeout=60)
    judge_session = judge_executor.execute(prompt)

    judge_result = _parse_nl_score(judge_session.output, model, "overall")
    passed = judge_result.score >= min_score

    return AssertResult(
        passed=passed,
        check_type="judge",
        message=(
            f"Judge: {judge_result.score}/10 "
            f"{'PASS' if passed else 'FAIL'} (min={min_score}) "
            f"— {judge_result.reason}"
        ),
        expected=f">= {min_score}/10",
        actual=f"{judge_result.score}/10",
        details={
            "score": judge_result.score,
            "reason": judge_result.reason,
            "min_score": min_score,
            "model": model,
        },
    )


# ---------------------------------------------------------------------------
# Master check runner
# ---------------------------------------------------------------------------

def run_all_checks(
    checks: dict,
    session: SessionResult,
    workspace: Path,
    base_dir: Path,
) -> list[AssertResult]:
    """Run all six layers of checks for a test case.

    Args:
        checks: The "checks" object from test_cases.json.
        session: The session result.
        workspace: Workspace root for file checks.
        base_dir: Expert test directory for resolving paths.

    Returns:
        Flat list of all assertion results.
    """
    all_results: list[AssertResult] = []

    # Layer 1: File creation
    if "files_created" in checks:
        all_results.extend(
            check_files_created(checks["files_created"], workspace)
        )

    # Layer 2: Skill invocation
    if "skills_invoked" in checks:
        all_results.extend(
            check_skills_invoked(checks["skills_invoked"], session)
        )

    # Layer 3: Tool calls
    if "tools_called" in checks:
        all_results.extend(
            check_tools_called(checks["tools_called"], session)
        )

    # Layer 4: Output content
    if "output_contains" in checks:
        all_results.extend(
            check_output_contains(checks["output_contains"], session.output)
        )
    if "output_not_contains" in checks:
        all_results.extend(
            check_output_not_contains(
                checks["output_not_contains"], session.output
            )
        )

    # Layer 5: NL checks
    if "nl_checks" in checks:
        all_results.extend(
            check_nl(checks["nl_checks"], session, base_dir)
        )

    # Layer 6: Judge
    if "judge" in checks:
        all_results.append(
            check_judge(checks["judge"], session, base_dir)
        )

    # Summary
    passed = sum(1 for r in all_results if r.passed)
    total = len(all_results)
    logger.info("Checks completed: %d/%d passed", passed, total)

    return all_results
