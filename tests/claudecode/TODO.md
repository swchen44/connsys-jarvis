# Integration Test - Progress Tracker

## Phase 0 — Documents & Skeleton ✅
- [x] Create `tests/claudecode/` directory structure
- [x] Write `doc/requirements.md`
- [x] Write `doc/design.md`
- [x] Create `TODO.md`
- [x] git commit (3ab60fa)

## Phase 1 — Core Runner ✅
- [x] `config.py` — constants, paths, model definitions, pricing
- [x] `runner.py` — HeadlessExecutor + TmuxExecutor + ClaudeRunner
- [x] `cli.py` — argparse entry point (--mode, --model, --expert, -v)
- [x] `__init__.py` + `__main__.py`
- [x] git commit (67137cd)

## Phase 2 — Analysis & Verification Modules ✅
- [x] `assertions.py` — 6-layer assertion library with LLM-as-judge
- [x] `token_analyzer.py` — token classification, waste detection, behavior phases
- [x] `skill_checker.py` — recursive skill loading, invocation verification
- [x] `dependency_checker.py` — topological dependency resolution
- [x] git commit (17a7bd4)

## Phase 3 — framework-base-expert Tests ✅
- [x] `framework-base-expert/test_cases.json` (4 test cases: FW-001~FW-004)
- [x] `framework-base-expert/test_framework_base.py`
- [x] `framework-base-expert/prompts/` — FW-001, FW-002
- [x] `framework-base-expert/golden/` — FW-001 expected
- [x] `framework-base-expert/rubrics/` — FW-001, FW-002
- [ ] Verify headless mode output format (requires runtime test)
- [ ] Verify tmux output capture (requires runtime test)
- [x] git commit (80fc3ce)

## Phase 4 — wifi-bora-memory-slim-expert Tests ✅
- [x] `wifi-bora-memory-slim-expert/test_cases.json` (4 test cases: MEM-001~MEM-004)
- [x] `wifi-bora-memory-slim-expert/test_memory_slim.py`
- [x] `wifi-bora-memory-slim-expert/prompts/` — MEM-002, MEM-003
- [x] `wifi-bora-memory-slim-expert/golden/` — MEM-002 expected
- [x] `wifi-bora-memory-slim-expert/rubrics/` — MEM-002
- [x] Verify 5-Expert dependency chain resolution (in test code)
- [x] Verify symlink completeness (in dependency_checker)
- [x] git commit (b86ea97)

## Phase 5 — Report & Template
- [x] `report.py` — three-layer report generator
- [x] `templates/expert_test_template.py`
- [x] `conftest.py` — pytest fixtures
- [ ] pylint pass (>= 9.0)
- [ ] git commit

## Future — Session Analysis as Skill (out of scope)
- [ ] Extract token_analyzer + BehaviorClassifier into reusable module
- [ ] Create new skill in framework-base-expert for session analysis
- [ ] Allow any Expert to invoke session analysis skill
