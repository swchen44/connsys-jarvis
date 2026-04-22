"""Claude Code execution runner with headless and tmux modes.

Provides a unified interface for running Claude Code sessions,
capturing output, and collecting session metadata for analysis.
"""

import json
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SessionResult:
    """Complete result from a Claude Code session."""

    output: str = ""                          # Final text output
    exit_code: int = 0                        # Process exit code
    raw_json_lines: list[dict] = field(default_factory=list)  # stream-json
    raw_text: str = ""                        # Raw captured text (tmux)
    duration: float = 0.0                     # Seconds elapsed
    model: str = ""                           # Model used
    mode: str = ""                            # "headless" or "tmux"
    session_id: str = ""                      # Claude session ID
    timestamp: str = ""                       # ISO timestamp
    log_path: Path = field(default_factory=Path)  # Saved session log


@dataclass
class JudgeResult:
    """Result from LLM judge evaluation."""

    score: float = 0.0                        # 1-10 (or custom scale)
    reason: str = ""                          # One-line explanation
    model: str = ""                           # Judge model used
    aspect: str = ""                          # Evaluation aspect


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _resolve_prompt(prompt_value: str, base_dir: Path) -> str:
    """Resolve prompt: if ends with .md, read from file; else use inline.

    Args:
        prompt_value: Inline prompt text or path to .md file.
        base_dir: Base directory for resolving relative paths.

    Returns:
        The prompt text content.
    """
    if prompt_value.endswith(".md"):
        prompt_path = base_dir / prompt_value
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}"
            )
        logger.debug("Loading prompt from file: %s", prompt_path)
        return prompt_path.read_text(encoding="utf-8").strip()
    return prompt_value


def _save_session_log(result: SessionResult, expert_name: str) -> Path:
    """Save session output to .results/ directory for debugging.

    Args:
        result: The session result to save.
        expert_name: Name of the Expert being tested.

    Returns:
        Path to the saved log directory.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    log_dir = config.RESULTS_DIR / ts / expert_name
    log_dir.mkdir(parents=True, exist_ok=True)

    # Save raw output
    (log_dir / "output.txt").write_text(result.output, encoding="utf-8")

    # Save raw text (tmux mode)
    if result.raw_text:
        (log_dir / "raw_text.txt").write_text(
            result.raw_text, encoding="utf-8"
        )

    # Save JSON lines (headless mode)
    if result.raw_json_lines:
        with open(log_dir / "stream.jsonl", "w", encoding="utf-8") as fh:
            for line in result.raw_json_lines:
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    # Save metadata
    meta = {
        "model": result.model,
        "mode": result.mode,
        "duration": result.duration,
        "exit_code": result.exit_code,
        "session_id": result.session_id,
        "timestamp": result.timestamp,
    }
    (log_dir / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info("Session log saved to: %s", log_dir)
    return log_dir


# ---------------------------------------------------------------------------
# Executor base class
# ---------------------------------------------------------------------------

class ExecutorBase(ABC):
    """Abstract base for Claude Code executors."""

    def __init__(
        self,
        model: str = config.DEFAULT_MODEL,
        timeout: int = config.DEFAULT_TIMEOUT,
        workspace: Path | None = None,
        allowed_tools: list[str] | None = None,
        verbose: bool = False,
    ):
        self.model_key = model
        self.model_id = config.MODELS.get(model, model)
        self.timeout = timeout
        self.workspace = workspace or Path.cwd()
        self.allowed_tools = allowed_tools
        self.verbose = verbose

    @abstractmethod
    def execute(self, prompt: str) -> SessionResult:
        """Execute a Claude Code session with the given prompt.

        Args:
            prompt: The prompt text to send to Claude.

        Returns:
            SessionResult with captured output and metadata.
        """


# ---------------------------------------------------------------------------
# Headless executor
# ---------------------------------------------------------------------------

class HeadlessExecutor(ExecutorBase):
    """Execute Claude Code in headless mode using -p flag.

    Uses ``claude -p --output-format stream-json`` for structured output.
    Each line of stdout is a JSON object containing message content,
    tool calls, thinking blocks, and token usage.
    """

    def execute(self, prompt: str) -> SessionResult:
        """Run Claude Code headless and parse stream-json output.

        Args:
            prompt: The prompt to send.

        Returns:
            SessionResult with parsed JSON lines and extracted text.
        """
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "stream-json",
            "--model", self.model_id,
        ]

        if self.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self.allowed_tools)])

        if self.verbose:
            cmd.append("--verbose")

        logger.info("Running headless: %s", " ".join(cmd[:6]) + " ...")
        logger.debug("Full command: %s", cmd)
        logger.debug("Working directory: %s", self.workspace)

        start_time = time.monotonic()
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.workspace),
                env={**os.environ, "CLAUDE_CODE_HEADLESS": "1"},
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start_time
            logger.error("Headless execution timed out after %.1fs", elapsed)
            return SessionResult(
                output="[TIMEOUT]",
                exit_code=-1,
                duration=elapsed,
                model=self.model_id,
                mode="headless",
                timestamp=timestamp,
            )

        elapsed = time.monotonic() - start_time
        logger.info(
            "Headless completed in %.1fs with exit code %d",
            elapsed, proc.returncode,
        )

        # Parse stream-json output line by line
        json_lines: list[dict] = []
        text_parts: list[str] = []
        session_id = ""

        for raw_line in proc.stdout.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                obj = json.loads(raw_line)
                json_lines.append(obj)

                # Extract session ID
                if not session_id and "sessionId" in obj:
                    session_id = obj["sessionId"]

                # Extract text content from assistant messages
                if obj.get("type") == "assistant":
                    content = obj.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))

            except json.JSONDecodeError:
                logger.debug("Non-JSON line: %s", raw_line[:100])
                # Might be plain text output
                text_parts.append(raw_line)

        # Log stderr if present
        if proc.stderr:
            logger.debug("stderr:\n%s", proc.stderr[:2000])

        return SessionResult(
            output="\n".join(text_parts),
            exit_code=proc.returncode,
            raw_json_lines=json_lines,
            duration=elapsed,
            model=self.model_id,
            mode="headless",
            session_id=session_id,
            timestamp=timestamp,
        )


# ---------------------------------------------------------------------------
# Tmux executor
# ---------------------------------------------------------------------------

class TmuxExecutor(ExecutorBase):
    """Execute Claude Code inside a tmux session.

    Creates a tmux session, launches Claude Code, sends the prompt,
    polls for completion, then captures and cleans up.
    Suitable for manual observation and debugging.
    """

    POLL_INTERVAL: float = 3.0  # seconds between capture-pane polls
    STARTUP_WAIT: float = 5.0   # seconds to wait for Claude to start
    # Markers indicating Claude has finished responding
    COMPLETION_MARKERS: list[str] = [
        "❯",      # Claude Code prompt marker
        "$ ",      # Shell prompt fallback
    ]

    def execute(self, prompt: str) -> SessionResult:
        """Run Claude Code in tmux and capture output via capture-pane.

        Args:
            prompt: The prompt to send.

        Returns:
            SessionResult with captured text output.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        session_name = f"jarvis_test_{ts}"
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.info("Creating tmux session: %s", session_name)
        logger.debug("Working directory: %s", self.workspace)

        start_time = time.monotonic()

        try:
            # 1. Create tmux session
            subprocess.run(
                [
                    "tmux", "new-session",
                    "-d",                    # detached
                    "-s", session_name,
                    "-x", "220",             # wide enough for output
                    "-y", "50",
                ],
                check=True,
                cwd=str(self.workspace),
            )

            # 2. Launch Claude Code in the session
            claude_cmd = f"claude --model {self.model_id}"
            subprocess.run(
                ["tmux", "send-keys", "-t", session_name, claude_cmd, "Enter"],
                check=True,
            )

            # 3. Wait for Claude Code to start
            logger.debug(
                "Waiting %.1fs for Claude Code startup...",
                self.STARTUP_WAIT,
            )
            time.sleep(self.STARTUP_WAIT)

            # 4. Send the prompt
            # Escape special characters for tmux send-keys
            escaped_prompt = prompt.replace("'", "'\\''")
            subprocess.run(
                [
                    "tmux", "send-keys", "-t", session_name,
                    escaped_prompt, "Enter",
                ],
                check=True,
            )
            logger.info("Prompt sent to tmux session")

            # 5. Poll for completion
            captured_text = self._poll_for_completion(
                session_name, start_time
            )

            elapsed = time.monotonic() - start_time
            logger.info("Tmux session completed in %.1fs", elapsed)

            return SessionResult(
                output=captured_text,
                exit_code=0,
                raw_text=captured_text,
                duration=elapsed,
                model=self.model_id,
                mode="tmux",
                session_id=session_name,
                timestamp=timestamp,
            )

        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start_time
            logger.error("Tmux execution timed out after %.1fs", elapsed)
            captured = self._capture_pane(session_name)
            return SessionResult(
                output=captured or "[TIMEOUT]",
                exit_code=-1,
                raw_text=captured or "",
                duration=elapsed,
                model=self.model_id,
                mode="tmux",
                session_id=session_name,
                timestamp=timestamp,
            )

        finally:
            # 6. Kill the tmux session
            self._kill_session(session_name)

    def _poll_for_completion(
        self, session_name: str, start_time: float
    ) -> str:
        """Poll tmux capture-pane until completion marker or timeout.

        Args:
            session_name: The tmux session name.
            start_time: Monotonic time when execution started.

        Returns:
            The captured pane text.
        """
        previous_text = ""
        stable_count = 0

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > self.timeout:
                logger.warning("Tmux poll timeout reached")
                break

            captured = self._capture_pane(session_name)
            if not captured:
                time.sleep(self.POLL_INTERVAL)
                continue

            # Check for completion markers in the last few lines
            last_lines = captured.strip().split("\n")[-3:]
            last_text = "\n".join(last_lines)

            for marker in self.COMPLETION_MARKERS:
                if marker in last_text and captured != previous_text:
                    # Marker found and output changed — might be done
                    # Wait one more poll to confirm stability
                    if stable_count > 0:
                        logger.debug(
                            "Completion marker found and output stable"
                        )
                        return captured

            # Check if output has stabilized (same text for 2+ polls)
            if captured == previous_text:
                stable_count += 1
                if stable_count >= 3:
                    logger.debug(
                        "Output stabilized after %d polls", stable_count
                    )
                    return captured
            else:
                stable_count = 0
                previous_text = captured

            time.sleep(self.POLL_INTERVAL)

        return self._capture_pane(session_name) or ""

    @staticmethod
    def _capture_pane(session_name: str) -> str | None:
        """Capture the current tmux pane content.

        Args:
            session_name: The tmux session name.

        Returns:
            Captured text or None on failure.
        """
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", session_name, "-p"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout if result.returncode == 0 else None
        except (subprocess.SubprocessError, OSError):
            return None

    @staticmethod
    def _kill_session(session_name: str) -> None:
        """Kill the tmux session gracefully.

        Args:
            session_name: The tmux session name.
        """
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                timeout=10,
            )
            logger.debug("Killed tmux session: %s", session_name)
        except (subprocess.SubprocessError, OSError):
            logger.warning(
                "Failed to kill tmux session: %s", session_name
            )


# ---------------------------------------------------------------------------
# ClaudeRunner — main interface
# ---------------------------------------------------------------------------

class ClaudeRunner:
    """Main interface for running Claude Code integration tests.

    Supports both headless and tmux execution modes, result saving,
    and LLM-as-judge evaluation.

    Usage::

        runner = ClaudeRunner(mode="headless", model="sonnet")
        result = runner.run("請幫我分析 ROM 用量", expert_name="wifi-bora-memory-slim-expert")
    """

    def __init__(
        self,
        mode: str = config.DEFAULT_MODE,
        model: str = config.DEFAULT_MODEL,
        timeout: int = config.DEFAULT_TIMEOUT,
        workspace: Path | None = None,
        allowed_tools: list[str] | None = None,
        verbose: bool = False,
    ):
        """Initialize the runner.

        Args:
            mode: Execution mode, "headless" or "tmux".
            model: Model key (sonnet, opus, haiku) or full model ID.
            timeout: Maximum seconds per session.
            workspace: Working directory for Claude Code.
            allowed_tools: List of tool names to allow.
            verbose: Enable verbose output.
        """
        self.mode = mode
        self.model = model
        self.verbose = verbose

        executor_cls = HeadlessExecutor if mode == "headless" else TmuxExecutor
        self.executor = executor_cls(
            model=model,
            timeout=timeout,
            workspace=workspace,
            allowed_tools=allowed_tools,
            verbose=verbose,
        )
        logger.info(
            "ClaudeRunner initialized: mode=%s, model=%s", mode, model
        )

    def run(
        self,
        prompt: str,
        expert_name: str = "unknown",
        base_dir: Path | None = None,
    ) -> SessionResult:
        """Execute a Claude Code session.

        Args:
            prompt: Prompt text or path to .md file.
            expert_name: Expert name for log organization.
            base_dir: Base directory for resolving prompt file paths.

        Returns:
            SessionResult with complete output and metadata.
        """
        # Resolve prompt (file or inline)
        resolved = _resolve_prompt(
            prompt, base_dir or config.TESTS_ROOT
        )
        logger.info(
            "Running test for expert=%s, prompt_len=%d",
            expert_name, len(resolved),
        )

        # Execute
        result = self.executor.execute(resolved)

        # Save session log
        result.log_path = _save_session_log(result, expert_name)

        return result

    def run_with_judge(
        self,
        prompt: str,
        judge_prompt: str,
        expert_name: str = "unknown",
        judge_model: str = config.DEFAULT_JUDGE_MODEL,
        base_dir: Path | None = None,
    ) -> tuple[SessionResult, JudgeResult]:
        """Execute a session then evaluate with a judge model.

        Args:
            prompt: Main prompt text or path.
            judge_prompt: Evaluation prompt for the judge.
            expert_name: Expert name.
            judge_model: Model to use for judging (default: haiku).
            base_dir: Base directory for resolving paths.

        Returns:
            Tuple of (main session result, judge evaluation result).
        """
        # Run main session
        result = self.run(prompt, expert_name, base_dir)

        # Run judge evaluation using headless mode (always)
        judge_executor = HeadlessExecutor(
            model=judge_model,
            timeout=60,
            workspace=self.executor.workspace,
        )

        full_judge_prompt = (
            f"{judge_prompt}\n\n"
            f"## AI 的回應：\n{result.output}"
        )

        logger.info("Running judge evaluation with model=%s", judge_model)
        judge_session = judge_executor.execute(full_judge_prompt)

        # Parse judge response
        judge_result = self._parse_judge_response(
            judge_session.output, judge_model
        )

        return result, judge_result

    @staticmethod
    def _parse_judge_response(
        output: str, model: str
    ) -> JudgeResult:
        """Parse the judge model's JSON response.

        Args:
            output: Raw judge output text.
            model: Model used for judging.

        Returns:
            JudgeResult with score and reason.
        """
        try:
            # Try to find JSON in the output
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    return JudgeResult(
                        score=float(data.get("score", 0)),
                        reason=data.get("reason", ""),
                        model=model,
                    )
            # Fallback: try parsing entire output as JSON
            data = json.loads(output.strip())
            return JudgeResult(
                score=float(data.get("score", 0)),
                reason=data.get("reason", ""),
                model=model,
            )
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning("Failed to parse judge response: %s", exc)
            return JudgeResult(
                score=0.0,
                reason=f"Parse error: {exc}",
                model=model,
            )
