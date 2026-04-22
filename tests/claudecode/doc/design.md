# Connsys Jarvis Expert Integration Test - Design Document

## 1. Architecture Overview

```
                          CLI (cli.py)
                             │
                    ┌────────┴────────┐
                    │   ClaudeRunner   │
                    │    (runner.py)   │
                    ├─────────────────┤
                    │ HeadlessExecutor │ ← claude -p --output-format stream-json
                    │   TmuxExecutor   │ ← tmux send-keys + capture-pane
                    └────────┬────────┘
                             │ SessionResult
            ┌────────────────┼────────────────┐
            │                │                │
     ┌──────┴──────┐ ┌──────┴──────┐ ┌───────┴───────┐
     │ Assertions  │ │   Token     │ │    Skill      │
     │(assertions  │ │  Analyzer   │ │   Checker     │
     │    .py)     │ │(token_      │ │(skill_checker │
     │             │ │analyzer.py) │ │    .py)       │
     └──────┬──────┘ └──────┬──────┘ └───────┬───────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                    ┌────────┴────────┐
                    │  Report Engine  │
                    │   (report.py)   │
                    ├─────────────────┤
                    │ L1: Quality     │
                    │ L2: Statistics  │
                    │ L3: Behavior    │
                    └─────────────────┘
```

## 2. Data Flow

```
test_cases.json
    │
    ├── prompt (inline or .md file)
    │       │
    │       ▼
    │   ClaudeRunner.run(prompt)
    │       │
    │       ├── HeadlessExecutor → stream-json lines → SessionResult
    │       └── TmuxExecutor    → capture-pane text  → SessionResult
    │
    ├── checks.files_created     → FileChecker.verify()
    ├── checks.skills_invoked    → SkillChecker.check()
    ├── checks.tools_called      → ToolCallChecker.verify()
    ├── checks.output_contains   → Assertions.assert_contains()
    ├── checks.nl_checks         → NLChecker.evaluate() → LLM judge (1-10)
    └── checks.judge             → JudgeChecker.score() → LLM rubric judge
            │
            ▼
      TestCaseResult (per test case)
            │
            ▼
      ReportEngine.generate()
            │
            ├── L1: QualityReport
            ├── L2: StatisticsReport
            └── L3: BehaviorReport
```

## 3. Module Specifications

### 3.1 config.py

```python
# Path constants
JARVIS_ROOT: Path        # connsys-jarvis repo root
TESTS_ROOT: Path         # tests/claudecode/
RESULTS_DIR: Path        # tests/claudecode/.results/
MARKETPLACE_JSON: Path   # .claude-plugin/marketplace.json

# Model definitions
MODELS = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

# Default settings
DEFAULT_MODEL = "sonnet"
DEFAULT_MODE = "headless"
DEFAULT_TIMEOUT = 300
DEFAULT_LOG_LEVEL = "INFO"
```

### 3.2 runner.py — Key Data Classes

```python
@dataclass
class SessionResult:
    """Complete result from a Claude Code session."""
    output: str                    # Final text output
    exit_code: int                 # Process exit code
    raw_json_lines: list[dict]     # Parsed stream-json lines (headless)
    raw_text: str                  # Raw captured text (tmux)
    duration: float                # Seconds elapsed
    model: str                     # Model used
    mode: str                      # "headless" or "tmux"
    session_id: str                # Claude session ID
    timestamp: str                 # ISO timestamp
    log_path: Path                 # Path to saved session log

@dataclass
class JudgeResult:
    """Result from LLM judge evaluation."""
    score: float                   # 1-10
    reason: str                    # One-line explanation
    model: str                     # Judge model used
    aspect: str                    # Evaluation aspect (for nl_checks)
```

### 3.3 Executor Interface

```python
class ExecutorBase(ABC):
    def __init__(self, model, timeout, workspace, allowed_tools, verbose): ...

    @abstractmethod
    def execute(self, prompt: str) -> SessionResult: ...

class HeadlessExecutor(ExecutorBase):
    """
    Command: claude -p "{prompt}" --output-format stream-json
             --model {model} --allowedTools {tools}

    Parsing: Read stdout line-by-line, each line is JSON.
    Key fields per line:
      - type: "assistant" → has usage{} and content[]
      - content[].type: "tool_use" → name, input
      - content[].type: "thinking" → thinking text
      - usage: input_tokens, output_tokens, cache_*
    """

class TmuxExecutor(ExecutorBase):
    """
    Steps:
    1. tmux new-session -d -s {session_name} -x 200 -y 50
    2. tmux send-keys -t {session_name} 'claude' Enter
    3. Wait for Claude Code prompt
    4. tmux send-keys -t {session_name} '{prompt}' Enter
    5. Poll: tmux capture-pane -t {session_name} -p
    6. Detect completion markers
    7. tmux kill-session -t {session_name}

    Note: tmux mode has no structured JSON output.
    Token analysis requires reading JSONL from ~/.claude/projects/
    """
```

### 3.4 BehaviorClassifier

Classifies each assistant message into a behavior phase based on:

1. **thinking content keywords** (primary signal)
2. **tool_use patterns** (secondary signal)
3. **sequential context** (e.g., same tool after error = debugging)

```
Phase Detection Priority:
1. If thinking contains debug keywords AND previous message had error → "debugging"
2. If thinking contains design keywords AND no tool_use → "designing"
3. If thinking contains understand keywords AND position < 3 → "understanding"
4. If tool_use in {Read, Grep, Glob, Agent(Explore)} → "exploring"
5. If tool_use in {Write, Edit, Bash(non-test)} → "implementing"
6. If tool_use in {Bash(test/pytest)} → "verifying"
7. Fallback: "implementing"
```

### 3.5 NL Check Execution

```python
class NLChecker:
    """Natural language evaluation using LLM-as-judge."""

    PROMPT_TEMPLATE = """
你是一個 AI 回應品質評估者。
請根據以下問題，對 AI 的回應評分 1-{scale} 分。

## 評估面向：{aspect}
## 問題：{question}
## 參考答案（如有）：
{reference}
## AI 的實際回應：
{output}

請嚴格按照以下 JSON 格式回答（不要加其他文字）：
{{"score": <整數 1-{scale}>, "reason": "<一句話說明理由>"}}
"""

    def evaluate(self, nl_check: dict, output: str) -> JudgeResult:
        """Run a single NL check via Claude headless mode."""
```

## 4. JSONL Session File Parsing

Claude Code stores sessions at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.

### Message Types and Key Fields

| Type | Key Fields | Use For |
|------|-----------|---------|
| `user` | message.content (str) | Track user prompts |
| `assistant` | message.content[] (array), usage{} | Token stats, tool/skill tracking |
| `tool_result` | message.content[].tool_use_id | Match tool results to calls |

### Content Block Types in Assistant Messages

| Block Type | Fields | Use For |
|-----------|--------|---------|
| `text` | text | Response quality analysis |
| `tool_use` | name, id, input | Skill/tool invocation tracking |
| `thinking` | thinking, signature | Behavior phase classification |

### Token Fields (per assistant message)

| Field | Description |
|-------|------------|
| `input_tokens` | Regular input tokens |
| `output_tokens` | Generated tokens |
| `cache_creation_input_tokens` | Cache creation tokens |
| `cache_read_input_tokens` | Cache hit tokens (cheaper) |

## 5. Report Schema

### L1 Quality Report (JSON)

```json
{
  "expert": "framework-base-expert",
  "model": "claude-sonnet-4-6",
  "timestamp": "2026-04-22T10:30:00Z",
  "summary": {
    "total_tests": 10,
    "passed": 8,
    "failed": 2,
    "pass_rate": 0.8
  },
  "skill_coverage": {
    "total": 18,
    "invoked": 14,
    "not_invoked": 3,
    "failed": 1,
    "coverage_rate": 0.78
  },
  "nl_scores": {
    "completeness": {"avg": 8.2, "min": 6, "max": 10},
    "accuracy": {"avg": 7.5, "min": 5, "max": 9},
    "actionability": {"avg": 6.8, "min": 4, "max": 9}
  },
  "judge_score": 7.4,
  "test_results": [...]
}
```

### L2 Statistics Report (JSON)

```json
{
  "skills": [
    {"name": "wifi-bora-memslim-flow", "calls": 3, "success": 3, "failed": 0, "tokens": 12450}
  ],
  "tools": [
    {"name": "Read", "calls": 45, "success": 45, "failed": 0, "ratio": 0.352, "tokens": 5600}
  ],
  "failures": [
    {"type": "tool_timeout", "count": 3, "ratio": 0.429, "examples": ["Bash: make build"]}
  ],
  "total_tokens": {
    "input": 45000,
    "output": 35250,
    "cache_creation": 5000,
    "cache_read": 5000,
    "total": 90250
  }
}
```

### L3 Behavior Report (JSON)

```json
{
  "phases": [
    {"phase": "understanding", "messages": 3, "tokens": 4200, "ratio": 0.047},
    {"phase": "designing", "messages": 5, "tokens": 12800, "ratio": 0.142},
    {"phase": "exploring", "messages": 12, "tokens": 18500, "ratio": 0.205},
    {"phase": "implementing", "messages": 18, "tokens": 35200, "ratio": 0.390},
    {"phase": "debugging", "messages": 8, "tokens": 15300, "ratio": 0.170},
    {"phase": "verifying", "messages": 4, "tokens": 4250, "ratio": 0.047}
  ],
  "efficiency": {
    "effective_tokens": 68950,
    "effective_ratio": 0.764,
    "exploration_tokens": 18500,
    "wasted_tokens": 2800,
    "wasted_ratio": 0.031,
    "waste_details": [
      {"type": "edit_retry", "tokens": 1200, "description": "old_string mismatch"}
    ]
  },
  "timeline": [
    {"time": "00:00", "phase": "understanding", "description": "Reading prompt"},
    {"time": "00:12", "phase": "designing", "description": "Planning analysis steps"}
  ]
}
```
