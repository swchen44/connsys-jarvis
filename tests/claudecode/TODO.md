# Integration Test - Progress Tracker

## Phase 0 — Documents & Skeleton
- [x] Create `tests/claudecode/` directory structure
- [x] Write `doc/requirements.md`
- [x] Write `doc/design.md`
- [x] Create `TODO.md`
- [ ] git commit

## Phase 1 — Core Runner
- [ ] `config.py` — constants, paths, model definitions
- [ ] `runner.py` — HeadlessExecutor + TmuxExecutor + ClaudeRunner
- [ ] `cli.py` — argparse entry point (--mode, --model, --expert, -v)
- [ ] `__init__.py`
- [ ] git commit

## Phase 2 — Analysis & Verification Modules
- [ ] `assertions.py` — assertion library
- [ ] `token_analyzer.py` — token classification & statistics
- [ ] `skill_checker.py` — skill invocation verification
- [ ] `dependency_checker.py` — dependency chain verification
- [ ] git commit

## Phase 3 — framework-base-expert Tests
- [ ] `framework-base-expert/test_cases.json`
- [ ] `framework-base-expert/test_framework_base.py`
- [ ] `framework-base-expert/prompts/` — test prompts
- [ ] `framework-base-expert/golden/` — expected outputs
- [ ] `framework-base-expert/rubrics/` — scoring rubrics
- [ ] Verify headless mode output format
- [ ] Verify tmux output capture
- [ ] git commit

## Phase 4 — wifi-bora-memory-slim-expert Tests
- [ ] `wifi-bora-memory-slim-expert/test_cases.json`
- [ ] `wifi-bora-memory-slim-expert/test_memory_slim.py`
- [ ] `wifi-bora-memory-slim-expert/prompts/`
- [ ] `wifi-bora-memory-slim-expert/golden/`
- [ ] `wifi-bora-memory-slim-expert/rubrics/`
- [ ] Verify 5-Expert dependency chain resolution
- [ ] Verify symlink completeness
- [ ] git commit

## Phase 5 — Report & Template
- [ ] `report.py` — three-layer report generator
- [ ] `templates/expert_test_template.py`
- [ ] `conftest.py` — pytest fixtures
- [ ] pylint pass (>= 9.0)
- [ ] git commit

## Future — Session Analysis as Skill (out of scope)
- [ ] Extract token_analyzer + BehaviorClassifier into reusable module
- [ ] Create new skill in framework-base-expert for session analysis
- [ ] Allow any Expert to invoke session analysis skill
