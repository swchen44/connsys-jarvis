#!/usr/bin/env python3
"""Claude Code Session JSONL Analyzer.

Parses a Claude Code session JSONL file and produces a three-layer
analysis report covering token usage, tool/skill statistics, cache
efficiency, subagent tracking, and behavior phase classification.

Usage:
    python3 analyze_session.py <jsonl_path> [--output-dir <dir>] [--verbose]

Output:
    report.json  — machine-readable full report
    report.txt   — human-readable summary

Requires: Python 3.10+ (stdlib only, no external dependencies)
"""

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model pricing (USD per million tokens)
# ---------------------------------------------------------------------------

MODEL_PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_creation": 18.75},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_creation": 3.75},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0, "cache_read": 0.08, "cache_creation": 1.0},
    # Older models
    "claude-sonnet-4-5-20250514": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_creation": 3.75},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_creation": 3.75},
}

# ---------------------------------------------------------------------------
# Behavior classification keywords
# ---------------------------------------------------------------------------

BEHAVIOR_PHASES = {
    "understanding": {
        "thinking": ["understand", "理解", "需求", "分析問題", "the user wants", "let me understand"],
        "tools": [],
    },
    "designing": {
        "thinking": ["plan", "design", "架構", "設計", "strategy", "approach", "步驟"],
        "tools": [],
    },
    "exploring": {
        "thinking": ["search", "find", "look for", "探索", "check if", "let me check"],
        "tools": ["Read", "Grep", "Glob", "Agent", "WebSearch", "WebFetch"],
    },
    "implementing": {
        "thinking": ["implement", "write", "create", "實作", "build", "generate"],
        "tools": ["Write", "Edit", "Bash", "NotebookEdit"],
    },
    "debugging": {
        "thinking": ["retry", "fix", "error", "failed", "重試", "not found", "mismatch", "try again"],
        "tools": [],
    },
    "verifying": {
        "thinking": ["verify", "check", "confirm", "確認", "驗證", "test", "looks good"],
        "tools": [],
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    """Token counts."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    ephemeral_5m_tokens: int = 0
    ephemeral_1h_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens + self.cache_read_tokens

    def add(self, other: "TokenUsage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_creation_tokens += other.cache_creation_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.ephemeral_5m_tokens += other.ephemeral_5m_tokens
        self.ephemeral_1h_tokens += other.ephemeral_1h_tokens

    def cost(self, model_id: str) -> float:
        pricing = MODEL_PRICING.get(model_id, {})
        if not pricing:
            return 0.0
        return round((
            self.input_tokens * pricing.get("input", 0)
            + self.output_tokens * pricing.get("output", 0)
            + self.cache_read_tokens * pricing.get("cache_read", 0)
            + self.cache_creation_tokens * pricing.get("cache_creation", 0)
        ) / 1_000_000, 4)


@dataclass
class ToolStat:
    """Statistics for a single tool."""
    name: str = ""
    calls: int = 0
    success: int = 0
    errors: int = 0
    tokens: int = 0


@dataclass
class PhaseSegment:
    """A classified behavior segment."""
    phase: str = ""
    message_count: int = 0
    tokens: int = 0
    start_time: str = ""
    end_time: str = ""


@dataclass
class WasteRecord:
    """A detected token waste instance."""
    waste_type: str = ""
    tokens: int = 0
    description: str = ""
    index: int = 0


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    """Load and parse a JSONL file."""
    lines = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if raw:
                try:
                    lines.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
    logger.info("Loaded %d lines from %s", len(lines), path)
    return lines


def extract_usage(line: dict) -> TokenUsage | None:
    """Extract token usage from a JSONL line."""
    # Usage can be at top level or nested in message
    usage = line.get("usage") or (line.get("message", {}) or {}).get("usage")
    if not usage:
        return None
    cache_creation = usage.get("cache_creation", {}) or {}
    return TokenUsage(
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        cache_read_tokens=usage.get("cache_read_input_tokens", 0),
        ephemeral_5m_tokens=cache_creation.get("ephemeral_5m_input_tokens", 0),
        ephemeral_1h_tokens=cache_creation.get("ephemeral_1h_input_tokens", 0),
    )


def extract_model(line: dict) -> str:
    """Extract model name from a JSONL line."""
    msg = line.get("message", {}) or {}
    return msg.get("model", "") or line.get("model", "")


def extract_content_blocks(line: dict) -> list[dict]:
    """Extract content blocks from assistant message."""
    msg = line.get("message", {}) or {}
    content = msg.get("content", [])
    if isinstance(content, list):
        return content
    return []


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def analyze_tokens(lines: list[dict]) -> dict:
    """L1: Token usage summary."""
    total = TokenUsage()
    per_model: dict[str, TokenUsage] = {}
    message_count = 0
    models_seen = set()

    for line in lines:
        usage = extract_usage(line)
        if not usage:
            continue
        total.add(usage)
        message_count += 1

        model = extract_model(line)
        if model:
            models_seen.add(model)
            if model not in per_model:
                per_model[model] = TokenUsage()
            per_model[model].add(usage)

    # Cache hit ratio
    total_input = total.input_tokens + total.cache_creation_tokens + total.cache_read_tokens
    cache_hit_ratio = total.cache_read_tokens / max(total_input, 1)

    # Determine primary model for cost
    primary_model = ""
    if per_model:
        primary_model = max(per_model, key=lambda m: per_model[m].total)

    return {
        "total": asdict(total),
        "total_tokens": total.total,
        "estimated_cost_usd": total.cost(primary_model),
        "message_count": message_count,
        "cache_hit_ratio": round(cache_hit_ratio, 3),
        "ephemeral_5m_tokens": total.ephemeral_5m_tokens,
        "ephemeral_1h_tokens": total.ephemeral_1h_tokens,
        "per_model": {m: {**asdict(u), "cost_usd": u.cost(m)} for m, u in per_model.items()},
        "models_seen": sorted(models_seen),
        "primary_model": primary_model,
    }


def analyze_tools(lines: list[dict]) -> dict:
    """L2: Tool call statistics."""
    stats: dict[str, ToolStat] = {}
    # Map tool_use_id -> tool_name for matching results
    call_map: dict[str, str] = {}

    for line in lines:
        msg_type = line.get("type", "")

        if msg_type == "assistant":
            usage = extract_usage(line)
            msg_tokens = usage.total if usage else 0
            blocks = extract_content_blocks(line)
            tool_count_in_msg = sum(1 for b in blocks if b.get("type") == "tool_use")

            for block in blocks:
                if block.get("type") != "tool_use":
                    continue
                name = block.get("name", "unknown")
                use_id = block.get("id", "")

                if name not in stats:
                    stats[name] = ToolStat(name=name)
                stats[name].calls += 1
                if tool_count_in_msg > 0:
                    stats[name].tokens += msg_tokens // tool_count_in_msg

                if use_id:
                    call_map[use_id] = name

        # Match tool results for error detection
        if msg_type in ("user", "tool_result"):
            blocks = extract_content_blocks(line)
            for block in blocks:
                if block.get("type") != "tool_result":
                    continue
                use_id = block.get("tool_use_id", "")
                is_error = block.get("is_error", False)
                tool_name = call_map.get(use_id, "")

                if tool_name and tool_name in stats:
                    if is_error:
                        stats[tool_name].errors += 1
                    else:
                        stats[tool_name].success += 1

    # Convert to sorted list
    tool_list = sorted(stats.values(), key=lambda t: t.tokens, reverse=True)
    total_calls = sum(t.calls for t in tool_list)

    return {
        "tools": [
            {
                **asdict(t),
                "ratio": round(t.calls / max(total_calls, 1), 3),
                "error_rate": round(t.errors / max(t.calls, 1), 3),
            }
            for t in tool_list
        ],
        "total_calls": total_calls,
        "total_errors": sum(t.errors for t in tool_list),
    }


def analyze_skills(lines: list[dict]) -> dict:
    """L2: Skill invocation statistics."""
    skill_stats: dict[str, ToolStat] = {}
    skill_call_map: dict[str, str] = {}

    for line in lines:
        if line.get("type") != "assistant":
            continue
        for block in extract_content_blocks(line):
            if block.get("type") != "tool_use" or block.get("name") != "Skill":
                continue
            skill_name = block.get("input", {}).get("skill", "unknown")
            use_id = block.get("id", "")
            if skill_name not in skill_stats:
                skill_stats[skill_name] = ToolStat(name=skill_name)
            skill_stats[skill_name].calls += 1
            if use_id:
                skill_call_map[use_id] = skill_name

    return {
        "skills": [asdict(s) for s in sorted(skill_stats.values(), key=lambda s: s.calls, reverse=True)],
        "total_skill_calls": sum(s.calls for s in skill_stats.values()),
    }


def analyze_subagents(lines: list[dict]) -> dict:
    """L2: Subagent statistics."""
    agents: dict[str, dict] = {}

    for line in lines:
        agent_id = line.get("agentId", "")
        if not agent_id:
            continue
        if agent_id not in agents:
            agents[agent_id] = {
                "agent_id": agent_id,
                "agent_name": line.get("agentName", ""),
                "tokens": TokenUsage(),
                "message_count": 0,
                "tool_calls": 0,
            }
        agents[agent_id]["message_count"] += 1
        usage = extract_usage(line)
        if usage:
            agents[agent_id]["tokens"].add(usage)

        for block in extract_content_blocks(line):
            if block.get("type") == "tool_use":
                agents[agent_id]["tool_calls"] += 1

    result = []
    for info in agents.values():
        tokens = info["tokens"]
        result.append({
            "agent_id": info["agent_id"],
            "agent_name": info["agent_name"],
            "message_count": info["message_count"],
            "tool_calls": info["tool_calls"],
            "total_tokens": tokens.total,
            "input_tokens": tokens.input_tokens,
            "output_tokens": tokens.output_tokens,
        })

    return {"subagents": sorted(result, key=lambda a: a["total_tokens"], reverse=True)}


def analyze_errors(lines: list[dict]) -> dict:
    """L2: API errors and retries."""
    api_errors: list[dict] = []
    retry_count = 0
    total_retry_wait_ms = 0

    for line in lines:
        if line.get("type") == "system" and line.get("subtype") == "api_error":
            error = line.get("error", {}) or {}
            cause = line.get("cause", {}) or {}
            api_errors.append({
                "message": error.get("message", "") or line.get("content", ""),
                "code": cause.get("code", ""),
                "retry_attempt": line.get("retryAttempt", 0),
                "max_retries": line.get("maxRetries", 0),
                "retry_in_ms": line.get("retryInMs", 0),
                "timestamp": line.get("timestamp", ""),
            })
            if line.get("retryAttempt", 0) > 0:
                retry_count += 1
                total_retry_wait_ms += line.get("retryInMs", 0)

    # Error type distribution
    error_codes = Counter(e.get("code", "unknown") for e in api_errors)

    return {
        "api_errors": api_errors,
        "error_count": len(api_errors),
        "retry_count": retry_count,
        "total_retry_wait_ms": total_retry_wait_ms,
        "error_code_distribution": dict(error_codes),
    }


def analyze_hooks(lines: list[dict]) -> dict:
    """L2: Hook execution statistics."""
    hook_stats: dict[str, dict] = {}

    for line in lines:
        attachment = line.get("attachment")
        if not attachment or not isinstance(attachment, dict):
            continue
        hook_event = attachment.get("hookEvent", "")
        if not hook_event:
            continue

        if hook_event not in hook_stats:
            hook_stats[hook_event] = {
                "event": hook_event,
                "count": 0,
                "total_duration_ms": 0,
                "exit_codes": Counter(),
            }
        hook_stats[hook_event]["count"] += 1
        hook_stats[hook_event]["total_duration_ms"] += attachment.get("durationMs", 0)
        exit_code = attachment.get("exitCode", 0)
        hook_stats[hook_event]["exit_codes"][str(exit_code)] += 1

    result = []
    for info in hook_stats.values():
        avg_ms = info["total_duration_ms"] / max(info["count"], 1)
        result.append({
            "event": info["event"],
            "count": info["count"],
            "avg_duration_ms": round(avg_ms, 1),
            "total_duration_ms": info["total_duration_ms"],
            "exit_codes": dict(info["exit_codes"]),
        })

    return {"hooks": sorted(result, key=lambda h: h["count"], reverse=True)}


def analyze_file_changes(lines: list[dict]) -> dict:
    """L2: File change tracking from file-history-snapshot entries."""
    snapshots: list[dict] = []
    all_files: set[str] = set()

    for line in lines:
        if line.get("type") != "file-history-snapshot":
            continue
        snapshot = line.get("snapshot", {})
        tracked = snapshot.get("trackedFileBackups", {})
        timestamp = line.get("timestamp", "")
        files_in_snapshot = list(tracked.keys())
        all_files.update(files_in_snapshot)
        snapshots.append({
            "timestamp": timestamp,
            "file_count": len(files_in_snapshot),
            "files": files_in_snapshot[:20],  # Limit for report size
        })

    return {
        "snapshot_count": len(snapshots),
        "unique_files_modified": len(all_files),
        "files": sorted(all_files),
        "snapshots": snapshots[:10],  # Last 10 snapshots
    }


def analyze_aggregated_stats(lines: list[dict]) -> dict:
    """L2: Aggregated tool stats from collapsed_read_search entries."""
    totals = {
        "searchCount": 0, "readCount": 0, "listCount": 0,
        "bashCount": 0, "gitOpBashCount": 0, "replCount": 0,
        "memorySearchCount": 0, "memoryReadCount": 0, "memoryWriteCount": 0,
        "mcpCallCount": 0, "hookCount": 0, "hookTotalMs": 0,
    }
    mcp_servers: set[str] = set()
    entry_count = 0

    for line in lines:
        if line.get("type") != "collapsed_read_search":
            continue
        entry_count += 1
        for key in totals:
            totals[key] += line.get(key, 0)
        for server in line.get("mcpServerNames", []):
            mcp_servers.add(server)

    return {
        "entry_count": entry_count,
        "totals": totals,
        "mcp_servers": sorted(mcp_servers),
    }


def analyze_speculation(lines: list[dict]) -> dict:
    """L2: Speculation accept events (time saved by speculative execution)."""
    events: list[dict] = []
    total_saved_ms = 0

    for line in lines:
        # Check for speculation-accept type or SpeculationAcceptMessage
        line_type = line.get("type", "")
        if "speculation" not in line_type.lower() and "speculation" not in str(line.get("subtype", "")).lower():
            # Also check content for speculation data
            content = line.get("content", "")
            if isinstance(content, str) and "timeSaved" not in content:
                continue

        time_saved = line.get("timeSavedMs", 0)
        if time_saved > 0:
            total_saved_ms += time_saved
            events.append({
                "timestamp": line.get("timestamp", ""),
                "time_saved_ms": time_saved,
            })

    return {
        "event_count": len(events),
        "total_time_saved_ms": total_saved_ms,
        "total_time_saved_seconds": round(total_saved_ms / 1000, 1),
        "events": events[:20],
    }


def find_subagent_jsonls(session_jsonl_path: Path) -> list[dict]:
    """Find subagent JSONL files relative to the session file.

    Subagent files are at: <session-id>/subagents/agent-<agentId>.jsonl
    """
    session_dir = session_jsonl_path.parent
    session_id = session_jsonl_path.stem
    subagent_dir = session_dir / session_id / "subagents"

    results = []
    if subagent_dir.exists():
        for jsonl_file in sorted(subagent_dir.rglob("agent-*.jsonl")):
            size = jsonl_file.stat().st_size
            # Read meta file if exists
            meta_file = jsonl_file.with_suffix(".meta.json")
            meta = {}
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as fh:
                        meta = json.load(fh)
                except (json.JSONDecodeError, OSError):
                    pass
            results.append({
                "path": str(jsonl_file),
                "filename": jsonl_file.name,
                "size_bytes": size,
                "agent_type": meta.get("agentType", ""),
                "description": meta.get("description", ""),
            })

    return results


def analyze_behavior(lines: list[dict]) -> dict:
    """L3: Behavior phase classification."""
    phases: dict[str, PhaseSegment] = {}
    timeline: list[dict] = []
    total_tokens = 0
    waste_records: list[WasteRecord] = []

    prev_tool = ""
    prev_was_error = False
    compact_count = 0

    for idx, line in enumerate(lines):
        msg_type = line.get("type", "")
        timestamp = line.get("timestamp", "")

        # Track compact boundaries
        if msg_type == "system" and line.get("subtype") == "compact_boundary":
            compact_count += 1
            timeline.append({"time": timestamp, "event": "compact_boundary", "index": idx})
            continue

        if msg_type != "assistant":
            # Track tool errors for waste detection
            if msg_type in ("user", "tool_result"):
                for block in extract_content_blocks(line):
                    if block.get("type") == "tool_result" and block.get("is_error"):
                        prev_was_error = True
            continue

        usage = extract_usage(line)
        msg_tokens = usage.total if usage else 0
        total_tokens += msg_tokens

        blocks = extract_content_blocks(line)
        thinking_text = ""
        tool_names = []

        for block in blocks:
            if block.get("type") == "thinking":
                thinking_text += block.get("thinking", "")
            elif block.get("type") == "tool_use":
                tool_names.append(block.get("name", ""))

        # Classify phase
        phase = _classify_phase(thinking_text, tool_names, idx, prev_was_error, prev_tool)

        if phase not in phases:
            phases[phase] = PhaseSegment(phase=phase)
        phases[phase].message_count += 1
        phases[phase].tokens += msg_tokens

        # Detect waste: same tool retry after error
        if prev_was_error and tool_names and tool_names[0] == prev_tool:
            waste_records.append(WasteRecord(
                waste_type="error_retry",
                tokens=msg_tokens,
                description=f"Retry {tool_names[0]} after error",
                index=idx,
            ))

        # Timeline entry
        timeline.append({
            "time": timestamp,
            "phase": phase,
            "tools": tool_names,
            "tokens": msg_tokens,
            "index": idx,
        })

        prev_tool = tool_names[0] if tool_names else ""
        prev_was_error = False

    # Calculate ratios
    phase_list = sorted(phases.values(), key=lambda p: p.tokens, reverse=True)
    waste_tokens = sum(w.tokens for w in waste_records)
    effective_tokens = total_tokens - waste_tokens

    # Stop reason distribution
    stop_reasons = Counter()
    for line in lines:
        msg = line.get("message", {}) or {}
        sr = msg.get("stop_reason", "")
        if sr:
            stop_reasons[sr] += 1

    # Turn durations
    turn_durations: list[int] = []
    for line in lines:
        if line.get("type") == "system" and line.get("subtype") == "turn_duration":
            dur = line.get("durationMs", 0)
            if dur > 0:
                turn_durations.append(dur)

    return {
        "phases": [
            {
                "phase": p.phase,
                "message_count": p.message_count,
                "tokens": p.tokens,
                "ratio": round(p.tokens / max(total_tokens, 1), 3),
            }
            for p in phase_list
        ],
        "efficiency": {
            "total_tokens": total_tokens,
            "effective_tokens": effective_tokens,
            "effective_ratio": round(effective_tokens / max(total_tokens, 1), 3),
            "wasted_tokens": waste_tokens,
            "wasted_ratio": round(waste_tokens / max(total_tokens, 1), 3),
        },
        "waste_details": [asdict(w) for w in waste_records],
        "compact_boundary_count": compact_count,
        "stop_reason_distribution": dict(stop_reasons),
        "turn_durations_ms": turn_durations,
        "avg_turn_duration_ms": round(sum(turn_durations) / max(len(turn_durations), 1), 1),
        "timeline_sample": timeline[:50],  # First 50 entries
    }


def _classify_phase(
    thinking: str, tool_names: list[str], msg_idx: int,
    prev_error: bool, prev_tool: str,
) -> str:
    """Classify a message into a behavior phase."""
    thinking_lower = thinking.lower()

    # Priority 1: debugging (error retry context)
    if prev_error and tool_names and tool_names[0] == prev_tool:
        return "debugging"

    # Score each phase
    best_phase = ""
    best_score = 0

    for phase_name, phase_def in BEHAVIOR_PHASES.items():
        score = 0
        for kw in phase_def["thinking"]:
            if kw.lower() in thinking_lower:
                score += 2
        for pattern in phase_def["tools"]:
            if any(pattern in tn for tn in tool_names):
                score += 1
        if score > best_score:
            best_score = score
            best_phase = phase_name

    # Heuristic: early messages likely "understanding"
    if msg_idx < 2 and best_score == 0:
        return "understanding"

    return best_phase or "implementing"


def analyze_session_metadata(lines: list[dict]) -> dict:
    """Extract session metadata."""
    session_id = ""
    version = ""
    git_branch = ""
    cwd = ""
    first_timestamp = ""
    last_timestamp = ""
    total_messages = len(lines)

    for line in lines:
        if not session_id:
            session_id = line.get("sessionId", "")
        if not version:
            version = line.get("version", "")
        if not git_branch:
            git_branch = line.get("gitBranch", "")
        if not cwd:
            cwd = line.get("cwd", "")
        if not first_timestamp:
            first_timestamp = line.get("timestamp", "")
        last_timestamp = line.get("timestamp", "") or last_timestamp

    # Calculate duration
    duration_seconds = 0
    if first_timestamp and last_timestamp:
        try:
            t1 = datetime.fromisoformat(first_timestamp.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
            duration_seconds = (t2 - t1).total_seconds()
        except (ValueError, TypeError):
            pass

    return {
        "session_id": session_id,
        "version": version,
        "git_branch": git_branch,
        "cwd": cwd,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "duration_seconds": round(duration_seconds, 1),
        "total_lines": total_messages,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(lines: list[dict], jsonl_path: Path | None = None) -> dict:
    """Generate the full three-layer report."""
    metadata = analyze_session_metadata(lines)
    tokens = analyze_tokens(lines)
    tools = analyze_tools(lines)
    skills = analyze_skills(lines)
    subagents = analyze_subagents(lines)
    errors = analyze_errors(lines)
    hooks = analyze_hooks(lines)
    behavior = analyze_behavior(lines)
    file_changes = analyze_file_changes(lines)
    aggregated = analyze_aggregated_stats(lines)
    speculation = analyze_speculation(lines)
    subagent_files = find_subagent_jsonls(jsonl_path) if jsonl_path else []

    return {
        "metadata": metadata,
        "L1_quality": {
            "total_tokens": tokens["total_tokens"],
            "estimated_cost_usd": tokens["estimated_cost_usd"],
            "cache_hit_ratio": tokens["cache_hit_ratio"],
            "effective_ratio": behavior["efficiency"]["effective_ratio"],
            "wasted_ratio": behavior["efficiency"]["wasted_ratio"],
            "models_seen": tokens["models_seen"],
            "primary_model": tokens["primary_model"],
            "duration_seconds": metadata["duration_seconds"],
            "total_tool_calls": tools["total_calls"],
            "total_tool_errors": tools["total_errors"],
            "total_skill_calls": skills["total_skill_calls"],
            "api_error_count": errors["error_count"],
            "compact_count": behavior["compact_boundary_count"],
            "files_modified": file_changes["unique_files_modified"],
            "speculation_saved_ms": speculation["total_time_saved_ms"],
        },
        "L2_statistics": {
            "tokens": tokens,
            "tools": tools,
            "skills": skills,
            "subagents": subagents,
            "errors": errors,
            "hooks": hooks,
            "file_changes": file_changes,
            "aggregated_stats": aggregated,
            "speculation": speculation,
            "subagent_files": subagent_files,
        },
        "L3_behavior": behavior,
    }


def format_text_report(report: dict) -> str:
    """Format the report as human-readable text."""
    lines = []
    meta = report["metadata"]
    l1 = report["L1_quality"]
    l2 = report["L2_statistics"]
    l3 = report["L3_behavior"]

    # Header
    lines.append("=" * 70)
    lines.append("  Claude Code Session Analysis Report")
    lines.append("=" * 70)
    lines.append(f"Session:  {meta['session_id'][:16]}...")
    lines.append(f"Branch:   {meta['git_branch']}")
    lines.append(f"Duration: {meta['duration_seconds']:.0f}s ({meta['duration_seconds']/60:.1f}min)")
    lines.append(f"Version:  {meta['version']}")
    lines.append("")

    # L1: Quality Overview
    lines.append("-" * 70)
    lines.append("  L1: Quality Overview")
    lines.append("-" * 70)
    lines.append(f"Total Tokens:    {l1['total_tokens']:>10,}")
    lines.append(f"Estimated Cost:  ${l1['estimated_cost_usd']:>9.4f}")
    lines.append(f"Cache Hit Ratio: {l1['cache_hit_ratio']:>9.1%}")
    lines.append(f"Effective Ratio: {l1['effective_ratio']:>9.1%}")
    lines.append(f"Wasted Ratio:    {l1['wasted_ratio']:>9.1%}")
    lines.append(f"Models Used:     {', '.join(l1['models_seen'])}")
    lines.append(f"Tool Calls:      {l1['total_tool_calls']} ({l1['total_tool_errors']} errors)")
    lines.append(f"Skill Calls:     {l1['total_skill_calls']}")
    lines.append(f"API Errors:      {l1['api_error_count']}")
    lines.append(f"Compactions:     {l1['compact_count']}")
    lines.append("")

    # L2: Model distribution
    per_model = l2["tokens"].get("per_model", {})
    if per_model:
        lines.append("-" * 70)
        lines.append("  L2: Model Usage Distribution")
        lines.append("-" * 70)
        lines.append(f"  {'Model':<40} {'Tokens':>10} {'Cost':>8}")
        lines.append("  " + "-" * 60)
        for model, data in sorted(per_model.items(), key=lambda x: x[1].get("output_tokens", 0), reverse=True):
            total = data["input_tokens"] + data["output_tokens"] + data["cache_creation_tokens"] + data["cache_read_tokens"]
            lines.append(f"  {model:<40} {total:>10,} ${data.get('cost_usd', 0):>7.4f}")
        lines.append("")

    # L2: Tool statistics
    tool_list = l2["tools"].get("tools", [])
    if tool_list:
        lines.append("-" * 70)
        lines.append("  L2: Tool Statistics")
        lines.append("-" * 70)
        lines.append(f"  {'Tool':<25} {'Calls':>5} {'OK':>5} {'Err':>4} {'ErrR':>5} {'Tokens':>9}")
        lines.append("  " + "-" * 55)
        for t in tool_list[:20]:
            lines.append(
                f"  {t['name']:<25} {t['calls']:>5} {t['success']:>5} "
                f"{t['errors']:>4} {t['error_rate']:>4.0%} {t['tokens']:>9,}"
            )
        lines.append("")

    # L2: Skill statistics
    skill_list = l2["skills"].get("skills", [])
    if skill_list:
        lines.append("-" * 70)
        lines.append("  L2: Skill Statistics")
        lines.append("-" * 70)
        for s in skill_list:
            lines.append(f"  {s['name']}: {s['calls']} call(s)")
        lines.append("")

    # L2: Subagent statistics
    subagents = l2["subagents"].get("subagents", [])
    if subagents:
        lines.append("-" * 70)
        lines.append("  L2: Subagent Statistics")
        lines.append("-" * 70)
        for a in subagents:
            name = a['agent_name'] or a['agent_id'][:16]
            lines.append(f"  {name}: {a['total_tokens']:,} tokens, {a['tool_calls']} tool calls")
        lines.append("")

    # L2: Error distribution
    errors = l2["errors"]
    if errors["error_count"] > 0:
        lines.append("-" * 70)
        lines.append("  L2: API Errors")
        lines.append("-" * 70)
        lines.append(f"  Total errors: {errors['error_count']}, retries: {errors['retry_count']}")
        for code, count in errors.get("error_code_distribution", {}).items():
            lines.append(f"  {code}: {count}")
        lines.append("")

    # L2: Hook statistics
    hook_list = l2["hooks"].get("hooks", [])
    if hook_list:
        lines.append("-" * 70)
        lines.append("  L2: Hook Execution")
        lines.append("-" * 70)
        for h in hook_list:
            lines.append(f"  {h['event']}: {h['count']}x, avg {h['avg_duration_ms']:.0f}ms")
        lines.append("")

    # L3: Behavior Analysis
    phases = l3.get("phases", [])
    if phases:
        lines.append("-" * 70)
        lines.append("  L3: Behavior Phases")
        lines.append("-" * 70)
        lines.append(f"  {'Phase':<18} {'Msgs':>5} {'Tokens':>10} {'Ratio':>6}")
        lines.append("  " + "-" * 41)
        for p in phases:
            lines.append(f"  {p['phase']:<18} {p['message_count']:>5} {p['tokens']:>10,} {p['ratio']:>5.1%}")
        lines.append("")

    # L3: Efficiency
    eff = l3.get("efficiency", {})
    if eff:
        lines.append("-" * 70)
        lines.append("  L3: Token Efficiency")
        lines.append("-" * 70)
        lines.append(f"  Effective: {eff.get('effective_tokens', 0):>10,} ({eff.get('effective_ratio', 0):.1%})")
        lines.append(f"  Wasted:    {eff.get('wasted_tokens', 0):>10,} ({eff.get('wasted_ratio', 0):.1%})")
        lines.append(f"  Total:     {eff.get('total_tokens', 0):>10,}")
        lines.append("")

    # L3: Waste details
    waste = l3.get("waste_details", [])
    if waste:
        lines.append("  Waste Details:")
        for w in waste[:10]:
            lines.append(f"    [{w['waste_type']}] {w['description']} ({w['tokens']:,} tokens)")
        lines.append("")

    # L3: Stop reason distribution
    stop_reasons = l3.get("stop_reason_distribution", {})
    if stop_reasons:
        lines.append(f"  Stop Reasons: {stop_reasons}")
        lines.append("")

    # L3: Turn durations
    avg_turn = l3.get("avg_turn_duration_ms", 0)
    if avg_turn > 0:
        lines.append(f"  Avg Turn Duration: {avg_turn:.0f}ms ({avg_turn/1000:.1f}s)")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze Claude Code Session JSONL files",
    )
    parser.add_argument("jsonl_path", help="Path to .jsonl session file")
    parser.add_argument("--output-dir", "-o", help="Output directory (default: same as input)")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    jsonl_path = Path(args.jsonl_path)
    if not jsonl_path.exists():
        logger.error("File not found: %s", jsonl_path)
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else jsonl_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load and analyze
    lines = load_jsonl(jsonl_path)
    if not lines:
        logger.error("No data in %s", jsonl_path)
        sys.exit(1)

    report = generate_report(lines, jsonl_path)

    # Save JSON report
    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    logger.info("JSON report: %s", json_path)

    # Save text report
    text_path = output_dir / "report.txt"
    text_content = format_text_report(report)
    text_path.write_text(text_content, encoding="utf-8")
    logger.info("Text report: %s", text_path)

    # Generate HTML report
    if not args.no_html:
        try:
            script_dir = Path(__file__).resolve().parent
            # Import generate_html from sibling script
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "generate_html_report",
                script_dir / "generate_html_report.py",
            )
            html_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(html_mod)
            html_content = html_mod.generate_html(report)
            html_path = output_dir / "report.html"
            html_path.write_text(html_content, encoding="utf-8")
            logger.info("HTML report: %s", html_path)
        except Exception as exc:
            logger.warning("HTML generation failed: %s", exc)

    # Print summary to stdout
    print(text_content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
