"""Plugin dependency chain verification.

Recursively resolves Expert dependencies, verifies plugin.json
existence, skills directory completeness, and symlink integrity
in installed workspaces.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExpertNode:
    """A node in the dependency graph."""

    name: str
    source: str = ""              # Relative path from jarvis root
    version: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    has_plugin_json: bool = False
    has_expert_json: bool = False
    has_skills_dir: bool = False


@dataclass
class CheckResult:
    """Result of a single dependency check."""

    passed: bool
    expert: str
    check_type: str               # "plugin_json", "skills_dir", "symlink"
    message: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class DependencyReport:
    """Complete dependency verification report."""

    expert_name: str = ""
    chain: list[ExpertNode] = field(default_factory=list)
    total_skills: int = 0
    all_skill_names: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    all_passed: bool = False


# ---------------------------------------------------------------------------
# Dependency Checker
# ---------------------------------------------------------------------------

class DependencyChecker:
    """Verify plugin dependency chain completeness.

    Resolves the full dependency tree for an Expert, checks that
    all plugin.json files exist, skills directories are populated,
    and (optionally) symlinks are correctly created in a workspace.
    """

    def __init__(self, jarvis_root: Path | None = None):
        """Initialize the checker.

        Args:
            jarvis_root: Root of the connsys-jarvis repository.
        """
        self.jarvis_root = jarvis_root or config.JARVIS_ROOT
        self.marketplace = self._load_marketplace()

    def _load_marketplace(self) -> dict:
        """Load marketplace.json.

        Returns:
            Parsed marketplace data.
        """
        mp_path = self.jarvis_root / ".claude-plugin" / "marketplace.json"
        if not mp_path.exists():
            logger.error("marketplace.json not found: %s", mp_path)
            return {}
        with open(mp_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def resolve_chain(self, expert_name: str) -> list[ExpertNode]:
        """Recursively resolve dependency chain with topological sort.

        Performs depth-first traversal, deduplicates, and returns
        dependencies in installation order (leaves first).

        Args:
            expert_name: The root Expert to resolve.

        Returns:
            Topologically sorted list of ExpertNodes.
        """
        visited: dict[str, ExpertNode] = {}
        order: list[str] = []
        self._resolve_recursive(expert_name, visited, order, set())

        chain = [visited[name] for name in order if name in visited]
        logger.info(
            "Dependency chain for '%s': %s",
            expert_name,
            " → ".join(n.name for n in chain),
        )
        return chain

    def _resolve_recursive(
        self,
        expert_name: str,
        visited: dict[str, ExpertNode],
        order: list[str],
        in_stack: set[str],
    ) -> None:
        """Depth-first recursive resolution.

        Args:
            expert_name: Current Expert name.
            visited: Already-resolved nodes.
            order: Topological order accumulator.
            in_stack: Cycle detection set.
        """
        if expert_name in visited:
            return
        if expert_name in in_stack:
            logger.warning("Circular dependency detected: %s", expert_name)
            return

        in_stack.add(expert_name)

        # Find in marketplace
        plugin_entry = None
        for plugin in self.marketplace.get("plugins", []):
            if plugin.get("name") == expert_name:
                plugin_entry = plugin
                break

        if not plugin_entry:
            logger.warning(
                "Expert '%s' not found in marketplace.json", expert_name
            )
            in_stack.discard(expert_name)
            return

        source = plugin_entry.get("source", "").lstrip("./")
        expert_dir = self.jarvis_root / source

        # Load expert.json for dependencies
        expert_json_path = expert_dir / "expert.json"
        deps = []
        skills = []

        if expert_json_path.exists():
            with open(expert_json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Extract dependency names
            for dep in data.get("dependencies", []):
                dep_path = dep.get("expert", "")
                dep_name = (
                    dep_path.split("/")[-1]
                    if "/" in dep_path
                    else dep_path
                )
                if dep_name:
                    deps.append(dep_name)
            # Extract skill names
            internal_skills = data.get("internal", {}).get("skills", [])
            if internal_skills == ["ALL"] or internal_skills == "ALL":
                skills_dir = expert_dir / "skills"
                if skills_dir.exists():
                    skills = [
                        d.name for d in sorted(skills_dir.iterdir())
                        if d.is_dir() and (d / "SKILL.md").exists()
                    ]
            elif isinstance(internal_skills, list):
                skills = internal_skills

        # Resolve dependencies first (depth-first)
        for dep_name in deps:
            self._resolve_recursive(dep_name, visited, order, in_stack)

        # Create node
        node = ExpertNode(
            name=expert_name,
            source=source,
            version=plugin_entry.get("version", ""),
            description=plugin_entry.get("description", ""),
            dependencies=deps,
            skills=skills,
            has_plugin_json=(expert_dir / ".claude-plugin" / "plugin.json").exists(),
            has_expert_json=expert_json_path.exists(),
            has_skills_dir=(expert_dir / "skills").exists(),
        )

        visited[expert_name] = node
        order.append(expert_name)
        in_stack.discard(expert_name)

    def check_plugin_dirs(
        self, chain: list[ExpertNode]
    ) -> list[CheckResult]:
        """Verify plugin.json and skills directory for each Expert in chain.

        Args:
            chain: Resolved dependency chain.

        Returns:
            List of check results.
        """
        results = []

        for node in chain:
            expert_dir = self.jarvis_root / node.source

            # Check plugin.json
            plugin_json = expert_dir / ".claude-plugin" / "plugin.json"
            results.append(CheckResult(
                passed=plugin_json.exists(),
                expert=node.name,
                check_type="plugin_json",
                message=(
                    f"plugin.json {'exists' if plugin_json.exists() else 'MISSING'}"
                    f": {plugin_json}"
                ),
            ))

            # Check expert.json
            expert_json = expert_dir / "expert.json"
            results.append(CheckResult(
                passed=expert_json.exists(),
                expert=node.name,
                check_type="expert_json",
                message=(
                    f"expert.json {'exists' if expert_json.exists() else 'MISSING'}"
                    f": {expert_json}"
                ),
            ))

            # Check skills directory
            skills_dir = expert_dir / "skills"
            if node.skills:
                for skill_name in node.skills:
                    skill_dir = skills_dir / skill_name
                    skill_md = skill_dir / "SKILL.md"
                    exists = skill_md.exists()
                    results.append(CheckResult(
                        passed=exists,
                        expert=node.name,
                        check_type="skill_dir",
                        message=(
                            f"Skill '{skill_name}' SKILL.md "
                            f"{'exists' if exists else 'MISSING'}"
                        ),
                        details={
                            "skill": skill_name,
                            "path": str(skill_md),
                        },
                    ))

        return results

    def check_symlinks(
        self, workspace: Path, chain: list[ExpertNode]
    ) -> list[CheckResult]:
        """Verify symlinks in an installed workspace.

        After setup.py --init, skills should be symlinked into
        the workspace's .claude/ directory.

        Args:
            workspace: Root of the installed workspace.
            chain: Resolved dependency chain.

        Returns:
            List of check results.
        """
        results = []
        claude_dir = workspace / ".claude"

        if not claude_dir.exists():
            results.append(CheckResult(
                passed=False,
                expert="workspace",
                check_type="symlink",
                message=f".claude/ directory missing: {claude_dir}",
            ))
            return results

        for node in chain:
            for skill_name in node.skills:
                # Check if skill symlink exists (pattern may vary)
                # Common patterns: .claude/skills/{skill-name} or
                # .claude/{skill-name}
                found = False
                for search_dir in [claude_dir, claude_dir / "skills"]:
                    if not search_dir.exists():
                        continue
                    for item in search_dir.iterdir():
                        if item.name == skill_name and item.is_symlink():
                            found = True
                            break
                    if found:
                        break

                results.append(CheckResult(
                    passed=found,
                    expert=node.name,
                    check_type="symlink",
                    message=(
                        f"Symlink for skill '{skill_name}' "
                        f"{'found' if found else 'MISSING'} in workspace"
                    ),
                    details={"skill": skill_name, "workspace": str(workspace)},
                ))

        return results

    def check_skill_availability(
        self, chain: list[ExpertNode]
    ) -> dict:
        """Summarize all available skills across the dependency chain.

        Args:
            chain: Resolved dependency chain.

        Returns:
            Dict with total count, skill list, and per-expert breakdown.
        """
        all_skills: list[str] = []
        per_expert: dict[str, list[str]] = {}

        for node in chain:
            per_expert[node.name] = node.skills
            all_skills.extend(node.skills)

        # Deduplicate while preserving order
        seen = set()
        unique_skills = []
        for skill in all_skills:
            if skill not in seen:
                seen.add(skill)
                unique_skills.append(skill)

        return {
            "total": len(unique_skills),
            "skills": unique_skills,
            "per_expert": per_expert,
        }

    def full_check(self, expert_name: str) -> DependencyReport:
        """Run complete dependency verification.

        Args:
            expert_name: Expert to verify.

        Returns:
            DependencyReport with all check results.
        """
        chain = self.resolve_chain(expert_name)
        checks = self.check_plugin_dirs(chain)
        skill_info = self.check_skill_availability(chain)

        report = DependencyReport(
            expert_name=expert_name,
            chain=chain,
            total_skills=skill_info["total"],
            all_skill_names=skill_info["skills"],
            checks=checks,
            all_passed=all(c.passed for c in checks),
        )

        logger.info(
            "Dependency check for '%s': %d experts, %d skills, %s",
            expert_name,
            len(chain),
            report.total_skills,
            "ALL PASSED" if report.all_passed else "SOME FAILED",
        )

        return report
