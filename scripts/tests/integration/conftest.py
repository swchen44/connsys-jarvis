"""
Integration test helpers.

_build_mini_jarvis() 建立最小化、完全可寫的 connsys-jarvis 結構，
供 doctor 結構測試（TC-U18、TC-U20）使用，不依賴真實 repo 的唯讀檔案。
"""

import json
from pathlib import Path

import pytest


def build_mini_jarvis(root: Path) -> Path:
    """在 root/ 建立可寫的 mini connsys-jarvis 結構。

    結構：
      root/connsys-jarvis/
        framework/mini-expert/
          expert.json  (完整欄位：name, domain, owner, internal.skills)
          expert.md, soul.md
          skills/mini-skill-a/SKILL.md
          hooks/session-start.sh

    Returns:
        root（workspace path）
    """
    jarvis  = root / "connsys-jarvis"
    exp_dir = jarvis / "framework" / "mini-expert"
    exp_dir.mkdir(parents=True)
    (exp_dir / "expert.json").write_text(json.dumps({
        "name": "mini-expert",
        "display_name": "Mini Expert",
        "domain": "framework",
        "owner": "test-team",
        "version": "1.0.0",
        "is_base": True,
        "dependencies": [],
        "internal": {"skills": ["mini-skill-a"], "hooks": []},
        "exclude_symlink": {"patterns": []}
    }))
    for f in ["expert.md", "soul.md"]:
        (exp_dir / f).write_text(f"# {f}\n")
    skill_dir = exp_dir / "skills" / "mini-skill-a"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# mini-skill-a\n")
    hooks_dir = exp_dir / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "session-start.sh").write_text("#!/bin/bash\n")
    return root


@pytest.fixture()
def mini_workspace(tmp_path: Path) -> Path:
    """完全可寫的 mini jarvis workspace（不含真實 connsys-jarvis）。"""
    return build_mini_jarvis(tmp_path)
