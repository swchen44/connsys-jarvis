"""Global configuration for the integration test framework.

Defines path constants, model definitions, default settings,
and pricing information for token cost estimation.
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

# Root of the connsys-jarvis repository
JARVIS_ROOT: Path = Path(__file__).resolve().parents[2]

# Root of the integration test framework
TESTS_ROOT: Path = JARVIS_ROOT / "tests" / "claudecode"

# Directory for storing test results (git-ignored)
RESULTS_DIR: Path = TESTS_ROOT / ".results"

# Central Expert registry
MARKETPLACE_JSON: Path = JARVIS_ROOT / ".claude-plugin" / "marketplace.json"

# Claude Code session files base directory
CLAUDE_SESSIONS_DIR: Path = Path.home() / ".claude" / "projects"

# Setup script for workspace provisioning
SETUP_SCRIPT: Path = JARVIS_ROOT / "scripts" / "setup.py"


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

MODELS: dict[str, str] = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

# Pricing per million tokens (USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input": 3.0,
        "output": 15.0,
        "cache_read": 0.30,
        "cache_creation": 3.75,
    },
    "claude-opus-4-6": {
        "input": 15.0,
        "output": 75.0,
        "cache_read": 1.50,
        "cache_creation": 18.75,
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.0,
        "cache_read": 0.08,
        "cache_creation": 1.0,
    },
}


# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------

DEFAULT_MODEL: str = "sonnet"
DEFAULT_MODE: str = "headless"
DEFAULT_TIMEOUT: int = 300  # seconds
DEFAULT_LOG_LEVEL: str = "INFO"

# Judge model for nl_checks and judge evaluations
DEFAULT_JUDGE_MODEL: str = "haiku"

# NL check prompt template
NL_CHECK_PROMPT_TEMPLATE: str = """你是一個 AI 回應品質評估者。
請根據以下問題，對 AI 的回應評分 1-{scale} 分。

## 評估面向：{aspect}
## 問題：{question}
{reference_section}
## AI 的實際回應：
{output}

請嚴格按照以下 JSON 格式回答（不要加其他文字）：
{{"score": <整數 1-{scale}>, "reason": "<一句話說明理由>"}}"""


# ---------------------------------------------------------------------------
# Behavior classification keywords
# ---------------------------------------------------------------------------

BEHAVIOR_PHASES: dict[str, dict[str, list[str]]] = {
    "understanding": {
        "thinking_keywords": [
            "understand", "理解", "需求", "分析問題", "the user wants",
            "let me understand",
        ],
        "tool_patterns": [],
    },
    "designing": {
        "thinking_keywords": [
            "plan", "design", "架構", "設計", "strategy", "approach",
            "let me plan", "步驟",
        ],
        "tool_patterns": [],
    },
    "exploring": {
        "thinking_keywords": [
            "search", "find", "look for", "探索", "check if",
        ],
        "tool_patterns": ["Read", "Grep", "Glob", "Agent"],
    },
    "implementing": {
        "thinking_keywords": [
            "implement", "write", "create", "實作", "build", "generate",
        ],
        "tool_patterns": ["Write", "Edit", "Bash"],
    },
    "debugging": {
        "thinking_keywords": [
            "retry", "fix", "error", "failed", "重試", "not found",
            "mismatch", "try again",
        ],
        "tool_patterns": [],
    },
    "verifying": {
        "thinking_keywords": [
            "verify", "check", "confirm", "確認", "驗證", "test",
        ],
        "tool_patterns": ["Bash"],
    },
}
