# Connsys Jarvis Expert Integration Test

## Concept

This framework validates Expert AI behavior by running real Claude Code sessions
and analyzing the results across six dimensions.

### Why Integration Test?

Unit tests verify `setup.py` installation logic (239 existing tests).
Integration tests verify **what the Expert actually does** when given a task —
does it trigger the right Skills? Is the output correct? How many tokens did it waste?

### Six-Layer Check Architecture

Each test case defines checks in `test_cases.json`. The six layers run in order:

| Layer | Field | What It Verifies |
|-------|-------|-----------------|
| 1. File Creation | `files_created` | Expected files exist with correct content keywords |
| 2. Skill Invocation | `skills_invoked` | Required Skills were triggered in the session |
| 3. Tool Calls | `tools_called` | Specific tools (Read, Write, Bash...) called N+ times |
| 4. Output Content | `output_contains` | Final text output includes/excludes patterns |
| 5. NL Evaluation | `nl_checks` | LLM-as-judge scores per aspect (1-10 scale) |
| 6. Judge Scoring | `judge` | Overall quality score via rubric-based LLM judge |

### Behavior Analysis

Beyond pass/fail, the framework classifies AI behavior from JSONL session data:

- **Understanding** — reading the prompt, analyzing requirements
- **Designing** — planning approach (detected via `thinking` keywords)
- **Exploring** — searching code (Read, Grep, Glob)
- **Implementing** — writing code (Write, Edit, Bash)
- **Debugging** — retrying after errors
- **Verifying** — running tests, confirming results

This answers: "Is the AI spending tokens on design or stuck in retry loops?"

### Execution Modes

| Mode | Flag | Best For |
|------|------|----------|
| Headless | `--mode headless` (default) | CI/automation, structured JSON output |
| tmux | `--mode tmux` | Manual debug, real-time observation |

---

## Run Flow

### Prerequisites

- Claude Code CLI installed and authenticated
- Python 3.10+
- Working directory: `connsys-jarvis/` repo root

### Basic Commands

```bash
# Run all tests for one Expert
python -m tests.claudecode.cli --expert framework-base-expert

# Run with a specific model
python -m tests.claudecode.cli --expert framework-base-expert --model opus

# Run in tmux mode (for debugging)
python -m tests.claudecode.cli --expert framework-base-expert --mode tmux

# Compare across models
python -m tests.claudecode.cli --expert framework-base-expert \
    --models sonnet,opus,haiku

# Run all Experts
python -m tests.claudecode.cli --all

# Verbose logging
python -m tests.claudecode.cli --expert framework-base-expert \
    -v --log-level DEBUG
```

### Analysis & Reporting

```bash
# Analyze saved results
python -m tests.claudecode.cli --analyze .results/2026-04-22_103000/

# Generate report from latest
python -m tests.claudecode.cli --report --format json
python -m tests.claudecode.cli --report --format text
```

### Scaffolding New Expert Tests

```bash
# Create test structure for a new Expert based on an existing one
python -m tests.claudecode.cli --scaffold wifi-logan-base-expert \
    --reference framework-base-expert
```

### Execution Flow (What Happens Internally)

```
1. CLI parses arguments (--expert, --model, --mode, -v)
2. Load Expert context (marketplace.json -> expert.json -> skills)
3. Read test_cases.json for the Expert
4. For each test case:
   a. Resolve prompt (inline text or .md file)
   b. ClaudeRunner.run(prompt) -> stream-json output
   c. Save full session log to .results/{timestamp}/
   d. Run 6-layer checks (files, skills, tools, output, NL, judge)
   e. TokenAnalyzer parses token usage
   f. SkillChecker verifies skill invocations
5. ReportEngine generates L1/L2/L3 reports
6. Save reports to .results/
```

---

## How to Read Reports

Reports are generated in three layers. Each layer answers different questions.

### Layer 1: Quality Report

**Question: "Did the Expert pass the tests?"**

```
=== Layer 1: Quality Report ===
Expert: wifi-bora-memory-slim-expert
Model:  claude-sonnet-4-6

Test Results: 8/10 passed (80%)
  [PASS] MEM-001 dependency_chain_integrity (0.2s)
  [PASS] MEM-002 memslim_flow_trigger (45.3s)
  [FAIL] MEM-003 lsp_tool_trigger (62.1s)

NL Check Scores:
  completeness:   8.2/10 (min=6, max=10)
  accuracy:       7.5/10 (min=5, max=9)
  actionability:  6.8/10 (min=4, max=9)

Judge Score: 7.4/10
```

**How to read:**
- `pass_rate` < 80% → investigate failing test cases
- NL scores < `min_pass` threshold → check the specific aspect
- Judge score < 7 → review the rubric and AI output in `.results/`

### Layer 2: Invocation Statistics

**Question: "What did the AI do, and what failed?"**

```
=== Layer 2: Invocation Statistics ===

Skill Statistics:
  Skill                               Calls   OK Fail   Tokens
  wifi-bora-memslim-flow                  3    3    0   12,450
  wifi-bora-lsp-tool                      2    1    1   15,300

Tool Statistics:
  Tool                 Calls   OK Fail  Ratio   Tokens
  Read                    45   45    0  35.2%    5,600
  Bash                    28   25    3  21.9%   18,200
  Edit                     8    6    2   6.3%    2,100

Failure Distribution:
  tool_timeout: 3 occurrence(s), 3,300 tokens
  edit_retry: 2 occurrence(s), 1,200 tokens
```

**How to read:**
- High `Fail` count on a Skill → the Skill implementation needs fixing
- High `Fail` on Edit → likely `old_string` mismatch (common issue)
- `tool_timeout` → command takes too long, consider increasing timeout
- Compare `Ratio` column to understand where token budget goes

### Layer 3: Behavior Analysis

**Question: "How did the AI spend its time and tokens?"**

```
=== Layer 3: Behavior Analysis ===

Behavior Phases:
  Phase              Messages   Tokens  Ratio
  implementing             18   35,200  39.0%
  exploring                12   18,500  20.5%
  debugging                 8   15,300  17.0%
  designing                 5   12,800  14.2%
  understanding             3    4,200   4.7%
  verifying                 4    4,250   4.7%

Token Efficiency:
  Effective: 68,950 (76.4%)
  Wasted:     2,800 (3.1%)
  Total:     90,250
```

**How to read:**
- `debugging` > 20% → AI is struggling, check error patterns in L2
- `exploring` > 30% → AI can't find what it needs, improve prompt or skill description
- `Wasted` > 5% → check waste details (edit retries, timeouts)
- Compare across models to find the best cost/quality balance:

```
Cross-Model Comparison:
  Metric              Sonnet    Opus      Haiku
  Total Token          90,250   72,100    145,600
  Effective Ratio       76.4%    82.1%     61.3%
  Wasted Ratio           3.1%     1.8%      8.7%
  NL Avg Score            7.5      8.8       5.2
  Estimated Cost        $0.27    $0.54     $0.07
```

---

## Directory Structure

```
tests/claudecode/
├── doc/
│   ├── README.md              # This file
│   ├── requirements.md        # Formal requirements (FR/NFR)
│   └── design.md              # Architecture, data flow, module specs
├── config.py                  # Path constants, model definitions, pricing
├── runner.py                  # HeadlessExecutor + TmuxExecutor
├── cli.py                     # CLI entry point (argparse)
├── assertions.py              # 6-layer check system
├── token_analyzer.py          # Token stats, waste detection, behavior phases
├── skill_checker.py           # Recursive skill loading + verification
├── dependency_checker.py      # Topological dependency resolution
├── report.py                  # 3-layer report generator (L1/L2/L3)
├── conftest.py                # Shared pytest fixtures
├── TODO.md                    # Progress tracker
├── .results/                  # Test output logs (git-ignored)
├── templates/
│   └── expert_test_template.py
├── framework-base-expert/     # Test suite for framework-base-expert
│   ├── test_cases.json        # Test definitions (prompts + 6-layer checks)
│   ├── test_framework_base.py # unittest runner
│   ├── prompts/               # Markdown prompt files
│   ├── golden/                # Expected output references
│   ├── fixtures/              # Mock data (code repos, configs)
│   └── rubrics/               # Scoring rubrics for judge
└── wifi-bora-memory-slim-expert/  # Test suite (5-Expert dependency chain)
    ├── test_cases.json
    ├── test_memory_slim.py
    ├── prompts/
    ├── golden/
    ├── fixtures/
    └── rubrics/
```

---

## How to Add Tests for a New Expert

1. **Scaffold** from an existing Expert:
   ```bash
   python -m tests.claudecode.cli --scaffold {new-expert} \
       --reference framework-base-expert
   ```

2. **Edit `test_cases.json`** — define test cases with prompts and checks

3. **Write prompts** in `prompts/*.md` — describe the task for the AI

4. **Write golden outputs** in `golden/*.md` — reference answers for NL checks

5. **Write rubrics** in `rubrics/*.md` — scoring criteria (1-10) for the judge

6. **Implement test runner** in `test_{expert}.py` — or copy from template

7. **Run and iterate**:
   ```bash
   python -m tests.claudecode.cli --expert {new-expert} -v
   ```
