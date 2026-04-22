# Connsys Jarvis Expert Integration Test - Requirements

## 1. Overview

Build an integration testing framework for connsys-jarvis Experts using Claude Code,
validating Skill triggering, response quality, token efficiency, and dependency integrity.

## 2. Functional Requirements

### FR-01: Test Structure
- Tests located at `tests/claudecode/{expert-name}/`
- Each Expert has similar directory format but different validation logic
- Sub-directories: `prompts/`, `golden/`, `fixtures/`, `rubrics/`
- Test cases defined in `test_cases.json` per Expert

### FR-02: Execution Modes
- **Headless mode**: `claude -p --output-format stream-json` for CI/automation
- **tmux mode**: `tmux new-session + send-keys + capture-pane` for manual debug
- Switchable via `--mode headless|tmux` CLI parameter

### FR-03: Multi-Model Support
- Support different models via `--model` parameter (sonnet, opus, haiku)
- Support multi-model comparison via `--models sonnet,opus,haiku`
- Use cheaper models (haiku) for result verification (judge)

### FR-04: Test Case Definition (test_cases.json)
- `prompt` field supports inline text or file reference (`prompts/*.md`)
- Six-layer check structure:
  1. `files_created` - verify file existence and content keywords
  2. `skills_invoked` - verify Skill tool invocations in stream-json
  3. `tools_called` - verify tool call counts and argument keywords
  4. `output_contains / output_not_contains` - simple text pattern matching
  5. `nl_checks` - natural language evaluation per aspect (1-10 scale)
  6. `judge` - overall quality scoring via LLM + rubric

### FR-05: Token Analysis
- Parse stream-json / JSONL for token usage (input/output/cache_read/cache_write)
- Classify conversations: effective, wasted_retry, tool_overhead, idle
- Per-skill token breakdown
- Identify wasted tokens (repeated errors, empty tool calls)
- Cross-model comparison

### FR-06: Skill Verification
- Load expected skills from `expert.json` + `marketplace.json` (recursive dependencies)
- Report: invoked, not_invoked, failed, unexpected
- Suggest improvements for skills with low trigger rates or failures

### FR-07: Dependency Chain Verification
- Recursive dependency resolution (topological sort)
- Verify plugin.json existence and skills directory completeness
- Verify symlink creation after workspace setup
- Target: wifi-bora-memory-slim-expert (5 Experts, 18 Skills chain)

### FR-08: Behavior Analysis
- Classify AI behavior phases from thinking + tool_use patterns:
  understanding, designing, exploring, implementing, debugging, verifying
- Build conversation timeline with phase annotations
- Calculate token efficiency (effective vs wasted ratio)

### FR-09: Responsiveness
- Read `marketplace.json` for Expert descriptions and dependencies
- Read `expert.json` for internal assets and dependency declarations
- Use responsiveness metadata in test validation

### FR-10: Report Generation
- Layer 1: Quality Report (pass/fail, skill coverage, NL scores, judge score)
- Layer 2: Invocation Statistics (skill/tool call counts, success rate, failure distribution)
- Layer 3: Behavior Analysis (phase breakdown, token efficiency, timeline, cross-model comparison)
- Output formats: JSON (machine-readable) + text summary (human-readable)

### FR-11: Natural Language Checks (nl_checks)
- Multiple independent aspect evaluations per test case
- Each check: aspect name, evaluation question, model, scale (1-10), min_pass threshold
- Optional reference file (golden answer) for comparison
- LLM-as-judge execution with structured prompt template

### FR-12: Scaffold / Template
- `--scaffold {expert} --reference {existing-expert}` to generate new Expert tests
- Copy and adapt test structure from reference Expert

## 3. Non-Functional Requirements

### NFR-01: Python stdlib only
- No external libraries (except pylint for code quality)
- Use: subprocess, json, logging, unittest, pathlib, argparse, dataclasses, abc, etc.

### NFR-02: Code Quality
- Pylint clean
- Docstrings on all public classes and functions
- Verbose logging for easy debugging
- Code comments where logic is non-obvious

### NFR-03: Logging & Debug
- Complete Claude Code session output saved to `.results/{timestamp}/`
- Verbose logging mode (`-v`, `--log-level DEBUG`)
- Error capture with full context for debugging

### NFR-04: Git Workflow
- Commit at each Phase completion (no push)
- Meaningful commit messages per Phase

## 4. Acceptance Criteria

| Requirement | Acceptance |
|-------------|-----------|
| FR-01 | Two Expert test directories created with correct structure |
| FR-02 | Both headless and tmux modes executable via CLI |
| FR-04 | test_cases.json parsed and all 6 check layers executed |
| FR-05 | Token report generated from real Claude Code session |
| FR-07 | 5-Expert dependency chain fully resolved and verified |
| FR-10 | Three-layer report generated with meaningful data |
| NFR-01 | No imports outside Python stdlib |
| NFR-02 | pylint score >= 9.0 |
