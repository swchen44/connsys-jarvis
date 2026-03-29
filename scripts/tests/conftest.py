"""
Shared pytest fixtures for all test layers (unit / integration / e2e).

Hierarchy:
  test/conftest.py          ← this file (loaded by all sub-tests)
  test/integration/conftest.py  ← integration-only helpers
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Make setup.py importable ─────────────────────────────────────────────────
# This file is at scripts/tests/conftest.py
# parents[0] = scripts/tests/
# parents[1] = scripts/    ← SCRIPTS_DIR
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import setup as inst  # noqa: E402  (available to all tests as `inst`)


# ─────────────────────────────────────────────────────────────────────────────
# Workspace fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Empty workspace with connsys-jarvis symlinked.

    Directory layout after fixture setup:
      tmp_path/
        connsys-jarvis -> <real connsys-jarvis repo>   (symlink)
    """
    # This file: scripts/tests/conftest.py
    # parents[2] = connsys-jarvis/
    jarvis_real = Path(__file__).resolve().parents[2]
    (tmp_path / "connsys-jarvis").symlink_to(jarvis_real)
    return tmp_path


@pytest.fixture()
def legacy_workspace(tmp_path: Path) -> Path:
    """Workspace with a .repo folder — triggers legacy scenario detection."""
    jarvis_real = Path(__file__).resolve().parents[2]
    (tmp_path / "connsys-jarvis").symlink_to(jarvis_real)
    (tmp_path / ".repo").mkdir()
    return tmp_path


@pytest.fixture()
def framework_expert_json(workspace: Path) -> Path:
    return workspace / "connsys-jarvis/framework/framework-base-expert/expert.json"


@pytest.fixture()
def slim_expert_json(workspace: Path) -> Path:
    return workspace / "connsys-jarvis/wifi-bora/wifi-bora-memory-slim-expert/expert.json"
