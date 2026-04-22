"""Skill invocation verification and improvement suggestions.

Loads expected skills from expert.json and marketplace.json,
then verifies which skills were invoked, failed, or missed
during a Claude Code session.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .runner import SessionResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillInfo:
    """Information about a single skill."""

    name: str
    expert: str                   # Owning Expert name
    source: str = "internal"      # "internal" or "dependency"
    skill_dir: Path = field(default_factory=Path)


@dataclass
class SkillReport:
    """Result of skill invocation verification."""

    expected: list[SkillInfo] = field(default_factory=list)
    invoked: list[str] = field(default_factory=list)
    not_invoked: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)
    coverage_rate: float = 0.0
    suggestions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Skill Checker
# ---------------------------------------------------------------------------

class SkillChecker:
    """Verify skill invocations against expected skill set.

    Loads the expected skill set from expert.json (including recursive
    dependencies), then checks a session result to see which skills
    were actually invoked.
    """

    def __init__(self, expert_name: str, jarvis_root: Path | None = None):
        """Initialize with an Expert name.

        Args:
            expert_name: Name of the Expert to check.
            jarvis_root: Root path of connsys-jarvis repo.
        """
        self.expert_name = expert_name
        self.jarvis_root = jarvis_root or config.JARVIS_ROOT
        self.expected_skills: list[SkillInfo] = []
        self._load_expected_skills()

    def _load_expected_skills(self) -> None:
        """Load expected skills from expert.json and dependencies."""
        # Find Expert path from marketplace.json
        marketplace = self._load_marketplace()
        expert_source = self._find_expert_source(
            marketplace, self.expert_name
        )
        if not expert_source:
            logger.warning(
                "Expert '%s' not found in marketplace.json",
                self.expert_name,
            )
            return

        expert_dir = self.jarvis_root / expert_source
        self._collect_skills_recursive(
            expert_dir, self.expert_name, visited=set()
        )

        logger.info(
            "Expected skills for '%s': %d total (%s)",
            self.expert_name,
            len(self.expected_skills),
            ", ".join(s.name for s in self.expected_skills),
        )

    def _load_marketplace(self) -> dict:
        """Load marketplace.json.

        Returns:
            Parsed marketplace data.
        """
        mp_path = config.MARKETPLACE_JSON
        if not mp_path.exists():
            logger.error("marketplace.json not found: %s", mp_path)
            return {}
        with open(mp_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def _find_expert_source(marketplace: dict, expert_name: str) -> str:
        """Find the source path of an Expert in marketplace.json.

        Args:
            marketplace: Parsed marketplace data.
            expert_name: Expert name to find.

        Returns:
            Source path string, or empty string if not found.
        """
        for plugin in marketplace.get("plugins", []):
            if plugin.get("name") == expert_name:
                # Remove leading "./" from source path
                source = plugin.get("source", "")
                return source.lstrip("./")
        return ""

    def _collect_skills_recursive(
        self,
        expert_dir: Path,
        expert_name: str,
        visited: set,
    ) -> None:
        """Recursively collect skills from Expert and dependencies.

        Args:
            expert_dir: Path to the Expert directory.
            expert_name: Name of the Expert.
            visited: Set of already-visited Expert names to avoid cycles.
        """
        if expert_name in visited:
            return
        visited.add(expert_name)

        expert_json_path = expert_dir / "expert.json"
        if not expert_json_path.exists():
            logger.warning("expert.json not found: %s", expert_json_path)
            return

        with open(expert_json_path, "r", encoding="utf-8") as fh:
            expert_data = json.load(fh)

        # Collect internal skills
        internal = expert_data.get("internal", {})
        internal_skills = internal.get("skills", [])

        if internal_skills == ["ALL"] or internal_skills == "ALL":
            # Discover all skills from skills/ directory
            skills_dir = expert_dir / "skills"
            if skills_dir.exists():
                for skill_dir in sorted(skills_dir.iterdir()):
                    if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                        self.expected_skills.append(SkillInfo(
                            name=skill_dir.name,
                            expert=expert_name,
                            source="internal",
                            skill_dir=skill_dir,
                        ))
        elif isinstance(internal_skills, list):
            skills_dir = expert_dir / "skills"
            for skill_name in internal_skills:
                skill_path = skills_dir / skill_name
                self.expected_skills.append(SkillInfo(
                    name=skill_name,
                    expert=expert_name,
                    source="internal",
                    skill_dir=skill_path,
                ))

        # Recursively collect dependency skills
        deps = expert_data.get("dependencies", [])
        marketplace = self._load_marketplace()

        for dep in deps:
            dep_expert_path = dep.get("expert", "")
            dep_name = dep_expert_path.split("/")[-1] if "/" in dep_expert_path else dep_expert_path
            dep_skills = dep.get("skills", [])

            dep_source = self._find_expert_source(marketplace, dep_name)
            if not dep_source:
                logger.warning("Dependency '%s' not found in marketplace", dep_name)
                continue

            dep_dir = self.jarvis_root / dep_source

            if dep_skills == "ALL" or dep_skills == "all" or dep_skills == ["ALL"]:
                # Collect all skills from dependency
                self._collect_skills_recursive(dep_dir, dep_name, visited)
            elif isinstance(dep_skills, list):
                # Collect specific skills
                for skill_name in dep_skills:
                    skill_path = dep_dir / "skills" / skill_name
                    self.expected_skills.append(SkillInfo(
                        name=skill_name,
                        expert=dep_name,
                        source="dependency",
                        skill_dir=skill_path,
                    ))

    def check(self, session: SessionResult) -> SkillReport:
        """Check which skills were invoked in a session.

        Args:
            session: The Claude Code session result.

        Returns:
            SkillReport with invoked/not_invoked/failed/unexpected lists.
        """
        # Extract invoked skills from session
        invoked_skills = self._extract_invoked_skills(session)

        # Extract failed skills (invoked but tool_result had error)
        failed_skills = self._extract_failed_skills(session)

        expected_names = {s.name for s in self.expected_skills}
        invoked_set = set(invoked_skills)
        failed_set = set(failed_skills)

        report = SkillReport(
            expected=self.expected_skills,
            invoked=sorted(invoked_set & expected_names),
            not_invoked=sorted(expected_names - invoked_set - failed_set),
            failed=sorted(failed_set & expected_names),
            unexpected=sorted(invoked_set - expected_names),
        )

        total = len(expected_names) if expected_names else 1
        report.coverage_rate = len(report.invoked) / total

        # Generate improvement suggestions
        report.suggestions = self.suggest_improvements(report)

        logger.info(
            "Skill check: %d invoked, %d not invoked, %d failed, "
            "%d unexpected (coverage=%.0f%%)",
            len(report.invoked),
            len(report.not_invoked),
            len(report.failed),
            len(report.unexpected),
            report.coverage_rate * 100,
        )
        return report

    @staticmethod
    def _extract_invoked_skills(session: SessionResult) -> list[str]:
        """Extract names of skills invoked in the session.

        Args:
            session: The session result.

        Returns:
            List of skill names.
        """
        skills = []
        for line in session.raw_json_lines:
            if line.get("type") != "assistant":
                continue
            content = line.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if (
                    block.get("type") == "tool_use"
                    and block.get("name") == "Skill"
                ):
                    skill_name = block.get("input", {}).get("skill", "")
                    if skill_name:
                        skills.append(skill_name)
        return skills

    @staticmethod
    def _extract_failed_skills(session: SessionResult) -> list[str]:
        """Extract skills that were invoked but failed.

        Args:
            session: The session result.

        Returns:
            List of failed skill names.
        """
        # Map tool_use_id → skill name
        skill_call_map: dict[str, str] = {}
        failed: list[str] = []

        for line in session.raw_json_lines:
            if line.get("type") == "assistant":
                content = line.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if (
                        block.get("type") == "tool_use"
                        and block.get("name") == "Skill"
                    ):
                        use_id = block.get("id", "")
                        skill_name = block.get("input", {}).get("skill", "")
                        if use_id and skill_name:
                            skill_call_map[use_id] = skill_name

            elif line.get("type") == "tool_result":
                content = line.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if block.get("type") != "tool_result":
                        continue
                    use_id = block.get("tool_use_id", "")
                    result_text = block.get("content", "")
                    if (
                        use_id in skill_call_map
                        and isinstance(result_text, str)
                        and any(
                            kw in result_text.lower()
                            for kw in ["error", "failed", "not found"]
                        )
                    ):
                        failed.append(skill_call_map[use_id])

        return failed

    @staticmethod
    def suggest_improvements(report: SkillReport) -> list[str]:
        """Generate improvement suggestions based on skill report.

        Args:
            report: The skill verification report.

        Returns:
            List of suggestion strings.
        """
        suggestions = []

        for skill_name in report.not_invoked:
            suggestions.append(
                f"Skill '{skill_name}' was never invoked. "
                f"Consider reviewing its SKILL.md trigger keywords "
                f"or description to improve discoverability."
            )

        for skill_name in report.failed:
            suggestions.append(
                f"Skill '{skill_name}' was invoked but failed. "
                f"Check the skill implementation and its allowed-tools."
            )

        for skill_name in report.unexpected:
            suggestions.append(
                f"Unexpected skill '{skill_name}' was invoked. "
                f"This skill is not in the expected set for this Expert."
            )

        if report.coverage_rate < 0.5:
            suggestions.append(
                f"Overall skill coverage is low ({report.coverage_rate:.0%}). "
                f"Consider improving test prompts to exercise more skills, "
                f"or review skill trigger keywords."
            )

        return suggestions
