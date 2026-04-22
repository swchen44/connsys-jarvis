"""Shared pytest fixtures for integration tests.

Provides workspace scaffolding, runner instances, and
common test utilities across all Expert test suites.
"""

import json
import logging
import subprocess
from pathlib import Path

import pytest

from . import config
from .runner import ClaudeRunner
from .dependency_checker import DependencyChecker
from .skill_checker import SkillChecker
from .token_analyzer import TokenAnalyzer

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def jarvis_root() -> Path:
    """Path to the connsys-jarvis repository root.

    Returns:
        Absolute path to connsys-jarvis.
    """
    return config.JARVIS_ROOT


@pytest.fixture(scope="session")
def marketplace(jarvis_root: Path) -> dict:
    """Load marketplace.json.

    Args:
        jarvis_root: Path to repo root.

    Returns:
        Parsed marketplace data.
    """
    mp_path = jarvis_root / ".claude-plugin" / "marketplace.json"
    with open(mp_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def workspace(tmp_path: Path, jarvis_root: Path) -> Path:
    """Create a temporary workspace with connsys-jarvis symlinked.

    Symlinks connsys-jarvis into a temp directory, simulating
    a real workspace where setup.py can be run.

    Args:
        tmp_path: pytest-provided temporary directory.
        jarvis_root: Path to connsys-jarvis repo.

    Returns:
        Path to the workspace root.
    """
    jarvis_link = tmp_path / "connsys-jarvis"
    jarvis_link.symlink_to(jarvis_root)
    return tmp_path


@pytest.fixture
def installed_workspace(
    workspace: Path, jarvis_root: Path
) -> Path:
    """Create a workspace with an Expert installed via setup.py.

    Runs setup.py --init with framework-base-expert as default.
    Useful for testing symlink creation and runtime behavior.

    Args:
        workspace: Temp workspace with connsys-jarvis symlinked.
        jarvis_root: Path to connsys-jarvis repo.

    Returns:
        Path to the workspace root with Expert installed.
    """
    expert_json = (
        jarvis_root / "framework" / "framework-base-expert" / "expert.json"
    )
    setup_py = jarvis_root / "scripts" / "setup.py"

    try:
        subprocess.run(
            ["python", str(setup_py), "--init", str(expert_json)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        logger.info("Workspace initialized at: %s", workspace)
    except subprocess.CalledProcessError as exc:
        logger.error("setup.py --init failed: %s", exc.stderr)
        pytest.skip(f"setup.py --init failed: {exc.stderr[:200]}")

    return workspace


@pytest.fixture(scope="session")
def headless_runner() -> ClaudeRunner:
    """Create a ClaudeRunner in headless mode.

    Returns:
        Configured ClaudeRunner for headless execution.
    """
    return ClaudeRunner(
        mode="headless",
        model=config.DEFAULT_MODEL,
        verbose=True,
    )


@pytest.fixture(scope="session")
def tmux_runner() -> ClaudeRunner:
    """Create a ClaudeRunner in tmux mode.

    Returns:
        Configured ClaudeRunner for tmux execution.
    """
    return ClaudeRunner(
        mode="tmux",
        model=config.DEFAULT_MODEL,
        verbose=True,
    )


@pytest.fixture(scope="session")
def token_analyzer() -> TokenAnalyzer:
    """Create a TokenAnalyzer instance.

    Returns:
        TokenAnalyzer for session analysis.
    """
    return TokenAnalyzer()


@pytest.fixture(scope="session")
def dependency_checker() -> DependencyChecker:
    """Create a DependencyChecker instance.

    Returns:
        DependencyChecker for dependency validation.
    """
    return DependencyChecker()


def skill_checker_factory(expert_name: str) -> SkillChecker:
    """Create a SkillChecker for a specific Expert.

    Args:
        expert_name: Name of the Expert.

    Returns:
        Configured SkillChecker.
    """
    return SkillChecker(expert_name)
