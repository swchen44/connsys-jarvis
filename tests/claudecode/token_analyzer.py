"""Token usage analysis and behavior classification.

Parses Claude Code session JSONL data to produce token statistics,
conversation classification, per-skill breakdowns, waste detection,
and behavior phase timelines.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    """Token counts for a single message or aggregated."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total(self) -> int:
        """Total tokens across all categories."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )

    def add(self, other: "TokenUsage") -> None:
        """Accumulate another TokenUsage into this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_creation_tokens += other.cache_creation_tokens
        self.cache_read_tokens += other.cache_read_tokens

    def estimated_cost(self, model_id: str) -> float:
        """Estimate cost in USD based on model pricing.

        Args:
            model_id: Full model identifier for pricing lookup.

        Returns:
            Estimated cost in USD.
        """
        pricing = config.MODEL_PRICING.get(model_id, {})
        if not pricing:
            return 0.0
        cost = (
            self.input_tokens * pricing.get("input", 0)
            + self.output_tokens * pricing.get("output", 0)
            + self.cache_read_tokens * pricing.get("cache_read", 0)
            + self.cache_creation_tokens * pricing.get("cache_creation", 0)
        ) / 1_000_000
        return round(cost, 4)


@dataclass
class ToolCallRecord:
    """Record of a single tool call with outcome."""

    name: str
    tool_use_id: str = ""
    input_args: dict = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    timestamp: str = ""


@dataclass
class WasteRecord:
    """A detected instance of wasted tokens."""

    waste_type: str       # e.g., "edit_retry", "timeout_retry", "empty_read"
    tokens: int = 0
    description: str = ""
    message_index: int = 0


@dataclass
class PhaseSegment:
    """A segment of the conversation classified into a behavior phase."""

    phase: str            # understanding, designing, exploring, etc.
    start_index: int = 0
    end_index: int = 0
    message_count: int = 0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    timestamp: str = ""
    description: str = ""


@dataclass
class TokenReport:
    """Complete token analysis report for a session."""

    total: TokenUsage = field(default_factory=TokenUsage)
    per_message: list[TokenUsage] = field(default_factory=list)
    per_tool: dict[str, TokenUsage] = field(default_factory=dict)
    per_skill: dict[str, TokenUsage] = field(default_factory=dict)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    waste: list[WasteRecord] = field(default_factory=list)
    phases: list[PhaseSegment] = field(default_factory=list)
    classification: dict[str, int] = field(default_factory=dict)
    model: str = ""
    estimated_cost: float = 0.0


# ---------------------------------------------------------------------------
# Token Analyzer
# ---------------------------------------------------------------------------

class TokenAnalyzer:
    """Analyze token usage from Claude Code session data.

    Parses JSONL lines (from headless stream-json or session files)
    to produce comprehensive token statistics and behavior analysis.
    """

    def parse_session(self, json_lines: list[dict]) -> TokenReport:
        """Parse a complete session into a TokenReport.

        Args:
            json_lines: List of parsed JSON objects from the session.

        Returns:
            TokenReport with all analysis results.
        """
        report = TokenReport()

        for line in json_lines:
            usage = self._extract_usage(line)
            if usage:
                report.per_message.append(usage)
                report.total.add(usage)

        # Extract tool calls
        report.tool_calls = self._extract_all_tool_calls(json_lines)

        # Per-tool token attribution (approximate via surrounding messages)
        report.per_tool = self._attribute_tokens_to_tools(
            json_lines, report.tool_calls
        )

        # Per-skill breakdown
        report.per_skill = self._attribute_tokens_to_skills(
            json_lines, report.tool_calls
        )

        # Classify conversations
        report.classification = self.classify_conversations(json_lines)

        # Detect waste
        report.waste = self.identify_waste(json_lines)

        # Behavior phases
        report.phases = self._classify_behavior_phases(json_lines)

        # Model and cost
        for line in json_lines:
            if line.get("model"):
                report.model = line["model"]
                break
        report.estimated_cost = report.total.estimated_cost(report.model)

        logger.info(
            "Token analysis: total=%d, cost=$%.4f, phases=%d",
            report.total.total, report.estimated_cost, len(report.phases),
        )
        return report

    @staticmethod
    def _extract_usage(line: dict) -> TokenUsage | None:
        """Extract token usage from a JSONL line.

        Args:
            line: A single parsed JSON object.

        Returns:
            TokenUsage or None if no usage data.
        """
        usage = line.get("usage")
        if not usage:
            return None
        return TokenUsage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
        )

    def _extract_all_tool_calls(
        self, json_lines: list[dict]
    ) -> list[ToolCallRecord]:
        """Extract all tool calls and match with results.

        Args:
            json_lines: Session JSONL data.

        Returns:
            List of tool call records with success/failure status.
        """
        calls: list[ToolCallRecord] = []
        # Map tool_use_id → ToolCallRecord for result matching
        call_map: dict[str, ToolCallRecord] = {}

        for line in json_lines:
            timestamp = line.get("timestamp", "")

            # Find tool_use blocks in assistant messages
            if line.get("type") == "assistant":
                content = line.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if block.get("type") == "tool_use":
                        record = ToolCallRecord(
                            name=block.get("name", ""),
                            tool_use_id=block.get("id", ""),
                            input_args=block.get("input", {}),
                            timestamp=timestamp,
                        )
                        calls.append(record)
                        if record.tool_use_id:
                            call_map[record.tool_use_id] = record

            # Match tool_result to detect failures
            if line.get("type") == "tool_result":
                content = line.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if block.get("type") != "tool_result":
                        continue
                    use_id = block.get("tool_use_id", "")
                    result_content = block.get("content", "")
                    if use_id in call_map:
                        # Check for error indicators
                        if isinstance(result_content, str):
                            lower = result_content.lower()
                            if any(
                                kw in lower for kw in
                                ["error", "failed", "not found", "denied"]
                            ):
                                call_map[use_id].success = False
                                call_map[use_id].error_message = (
                                    result_content[:200]
                                )

        return calls

    def _attribute_tokens_to_tools(
        self,
        json_lines: list[dict],
        tool_calls: list[ToolCallRecord],
    ) -> dict[str, TokenUsage]:
        """Approximate token attribution per tool.

        Uses a simple heuristic: tokens in an assistant message are
        attributed to the tools called in that message.

        Args:
            json_lines: Session JSONL data.
            tool_calls: Extracted tool calls.

        Returns:
            Dict mapping tool name to attributed TokenUsage.
        """
        per_tool: dict[str, TokenUsage] = {}

        for line in json_lines:
            if line.get("type") != "assistant":
                continue
            usage = self._extract_usage(line)
            if not usage:
                continue

            content = line.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue

            # Find tools used in this message
            tools_in_msg = []
            for block in content:
                if block.get("type") == "tool_use":
                    tools_in_msg.append(block.get("name", "unknown"))

            if not tools_in_msg:
                tools_in_msg = ["_no_tool"]

            # Split tokens evenly among tools in this message
            share = TokenUsage(
                input_tokens=usage.input_tokens // len(tools_in_msg),
                output_tokens=usage.output_tokens // len(tools_in_msg),
                cache_creation_tokens=(
                    usage.cache_creation_tokens // len(tools_in_msg)
                ),
                cache_read_tokens=(
                    usage.cache_read_tokens // len(tools_in_msg)
                ),
            )
            for tool_name in tools_in_msg:
                if tool_name not in per_tool:
                    per_tool[tool_name] = TokenUsage()
                per_tool[tool_name].add(share)

        return per_tool

    def _attribute_tokens_to_skills(
        self,
        json_lines: list[dict],
        tool_calls: list[ToolCallRecord],
    ) -> dict[str, TokenUsage]:
        """Attribute tokens to specific skills.

        Args:
            json_lines: Session JSONL data.
            tool_calls: Extracted tool calls.

        Returns:
            Dict mapping skill name to attributed TokenUsage.
        """
        per_skill: dict[str, TokenUsage] = {}
        # Find Skill tool calls
        skill_calls = [c for c in tool_calls if c.name == "Skill"]

        for line in json_lines:
            if line.get("type") != "assistant":
                continue
            usage = self._extract_usage(line)
            if not usage:
                continue
            content = line.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") != "Skill":
                    continue
                skill_name = block.get("input", {}).get("skill", "unknown")
                if skill_name not in per_skill:
                    per_skill[skill_name] = TokenUsage()
                per_skill[skill_name].add(usage)

        return per_skill

    def classify_conversations(
        self, json_lines: list[dict]
    ) -> dict[str, int]:
        """Classify conversation segments by effectiveness.

        Categories:
        - effective: Contains skill trigger or meaningful tool output
        - wasted_retry: Error followed by retry of same action
        - tool_overhead: Tool call/result without direct user value
        - idle: No substantial progress

        Args:
            json_lines: Session JSONL data.

        Returns:
            Dict of category -> token count.
        """
        classification = {
            "effective": 0,
            "wasted_retry": 0,
            "tool_overhead": 0,
            "idle": 0,
        }

        prev_error = False
        prev_tool_name = ""

        for line in json_lines:
            usage = self._extract_usage(line)
            tokens = usage.total if usage else 0

            if line.get("type") == "assistant":
                content = line.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    classification["idle"] += tokens
                    continue

                has_tool = any(
                    b.get("type") == "tool_use" for b in content
                )
                has_text = any(
                    b.get("type") == "text" and len(b.get("text", "")) > 50
                    for b in content
                )
                has_skill = any(
                    b.get("type") == "tool_use" and b.get("name") == "Skill"
                    for b in content
                )

                # Check if this is a retry after error
                current_tools = [
                    b.get("name", "")
                    for b in content if b.get("type") == "tool_use"
                ]
                is_retry = (
                    prev_error
                    and current_tools
                    and current_tools[0] == prev_tool_name
                )

                if is_retry:
                    classification["wasted_retry"] += tokens
                elif has_skill or has_text:
                    classification["effective"] += tokens
                elif has_tool:
                    classification["tool_overhead"] += tokens
                else:
                    classification["idle"] += tokens

                # Track for next iteration
                prev_tool_name = current_tools[0] if current_tools else ""

            elif line.get("type") == "tool_result":
                content = line.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        result_text = block.get("content", "")
                        if isinstance(result_text, str):
                            prev_error = any(
                                kw in result_text.lower()
                                for kw in ["error", "failed", "not found"]
                            )

        return classification

    def identify_waste(self, json_lines: list[dict]) -> list[WasteRecord]:
        """Find instances of wasted tokens.

        Detects: consecutive same-tool retries after error,
        empty Read results, Edit mismatches, Bash timeouts.

        Args:
            json_lines: Session JSONL data.

        Returns:
            List of waste records.
        """
        waste: list[WasteRecord] = []
        prev_tool = ""
        prev_was_error = False

        for idx, line in enumerate(json_lines):
            if line.get("type") != "assistant":
                # Track errors from tool results
                if line.get("type") == "tool_result":
                    content = line.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            text = block.get("content", "")
                            if isinstance(text, str):
                                lower = text.lower()
                                if "old_string" in lower and "not found" in lower:
                                    usage = self._extract_usage(line)
                                    waste.append(WasteRecord(
                                        waste_type="edit_retry",
                                        tokens=usage.total if usage else 0,
                                        description="Edit old_string mismatch",
                                        message_index=idx,
                                    ))
                                elif "timeout" in lower:
                                    usage = self._extract_usage(line)
                                    waste.append(WasteRecord(
                                        waste_type="timeout_retry",
                                        tokens=usage.total if usage else 0,
                                        description="Command timeout",
                                        message_index=idx,
                                    ))
                                prev_was_error = any(
                                    kw in lower
                                    for kw in ["error", "failed", "not found"]
                                )
                continue

            content = line.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if block.get("type") != "tool_use":
                    continue
                tool_name = block.get("name", "")

                # Same tool retry after error
                if prev_was_error and tool_name == prev_tool:
                    usage = self._extract_usage(line)
                    waste.append(WasteRecord(
                        waste_type="error_retry",
                        tokens=usage.total if usage else 0,
                        description=f"Retry {tool_name} after error",
                        message_index=idx,
                    ))

                prev_tool = tool_name
                prev_was_error = False

        return waste

    def _classify_behavior_phases(
        self, json_lines: list[dict]
    ) -> list[PhaseSegment]:
        """Classify each assistant message into a behavior phase.

        Uses thinking content keywords and tool_use patterns from
        config.BEHAVIOR_PHASES to determine the phase.

        Args:
            json_lines: Session JSONL data.

        Returns:
            List of phase segments with token attribution.
        """
        segments: list[PhaseSegment] = []

        for idx, line in enumerate(json_lines):
            if line.get("type") != "assistant":
                continue

            usage = self._extract_usage(line) or TokenUsage()
            content = line.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue

            # Extract thinking text and tool names
            thinking_text = ""
            tool_names = []
            for block in content:
                if block.get("type") == "thinking":
                    thinking_text += block.get("thinking", "")
                elif block.get("type") == "tool_use":
                    tool_names.append(block.get("name", ""))

            phase = self._determine_phase(
                thinking_text, tool_names, idx, segments
            )

            timestamp = line.get("timestamp", "")

            # Merge with previous segment if same phase
            if segments and segments[-1].phase == phase:
                segments[-1].end_index = idx
                segments[-1].message_count += 1
                segments[-1].tokens.add(usage)
            else:
                segments.append(PhaseSegment(
                    phase=phase,
                    start_index=idx,
                    end_index=idx,
                    message_count=1,
                    tokens=usage,
                    timestamp=timestamp,
                ))

        return segments

    @staticmethod
    def _determine_phase(
        thinking: str,
        tool_names: list[str],
        msg_index: int,
        prev_segments: list[PhaseSegment],
    ) -> str:
        """Determine behavior phase for a single message.

        Priority order:
        1. Debugging keywords + previous error context
        2. Thinking keywords match
        3. Tool pattern match
        4. Fallback to "implementing"

        Args:
            thinking: Thinking block text.
            tool_names: Tools used in this message.
            msg_index: Index in the conversation.
            prev_segments: Previously classified segments.

        Returns:
            Phase name string.
        """
        thinking_lower = thinking.lower()

        # Check each phase definition
        best_phase = ""
        best_score = 0

        for phase_name, phase_def in config.BEHAVIOR_PHASES.items():
            score = 0

            # Thinking keyword matches
            for kw in phase_def["thinking_keywords"]:
                if kw.lower() in thinking_lower:
                    score += 2

            # Tool pattern matches
            for pattern in phase_def["tool_patterns"]:
                if any(pattern in tn for tn in tool_names):
                    score += 1

            if score > best_score:
                best_score = score
                best_phase = phase_name

        # Position heuristic: early messages are more likely "understanding"
        if msg_index < 2 and best_score == 0:
            return "understanding"

        return best_phase or "implementing"

    def compare_models(
        self, results: dict[str, TokenReport]
    ) -> dict:
        """Compare token usage across multiple models.

        Args:
            results: Dict of model_key -> TokenReport.

        Returns:
            Comparison dictionary with per-model metrics.
        """
        comparison = {}
        for model_key, report in results.items():
            total_waste = sum(w.tokens for w in report.waste)
            comparison[model_key] = {
                "total_tokens": report.total.total,
                "input_tokens": report.total.input_tokens,
                "output_tokens": report.total.output_tokens,
                "effective_ratio": (
                    report.classification.get("effective", 0)
                    / max(report.total.total, 1)
                ),
                "wasted_tokens": total_waste,
                "wasted_ratio": total_waste / max(report.total.total, 1),
                "estimated_cost": report.estimated_cost,
                "num_tool_calls": len(report.tool_calls),
                "tool_success_rate": (
                    sum(1 for c in report.tool_calls if c.success)
                    / max(len(report.tool_calls), 1)
                ),
                "num_phases": len(report.phases),
            }
        return comparison


def load_session_jsonl(path: Path) -> list[dict]:
    """Load and parse a JSONL session file.

    Args:
        path: Path to .jsonl file.

    Returns:
        List of parsed JSON objects.
    """
    lines = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if raw_line:
                try:
                    lines.append(json.loads(raw_line))
                except json.JSONDecodeError:
                    logger.debug("Skipping non-JSON line: %s", raw_line[:80])
    logger.info("Loaded %d lines from %s", len(lines), path)
    return lines
