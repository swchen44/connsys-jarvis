#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
create_plugin_from_expert.py — Generate Claude Code plugin.json from expert.json
================================================================================

Scans all expert.json files in the connsys-jarvis repo and generates:
  1. .claude-plugin/plugin.json      per expert (Claude Code plugin manifest)
  2. .claude-plugin/marketplace.json  at repo root (marketplace registry)
  3. install_claudecode.sh            per expert (one-command installer)

Usage:
  python create_plugin_from_expert.py                   # Generate all files
  python create_plugin_from_expert.py --dry-run          # Preview without writing
  python create_plugin_from_expert.py --doctor           # Verify plugin correctness
  python create_plugin_from_expert.py --verbose          # Enable detailed logging
  python create_plugin_from_expert.py --expert-dir /path # Custom scan root
  python create_plugin_from_expert.py --help             # Show this help

Design:
  - Expert = Claude Code Plugin (1:1 mapping)
  - plugin.json lists metadata, component directories (skills/, commands/, agents/),
    and dependency plugin names
  - marketplace.json uses relative paths from repo root to each expert directory
  - install_claudecode.sh installs marketplace + all dependencies + expert itself

Known limitation (as of 2026-04):
  Claude Code `plugin install --scope project` does NOT auto-install plugin
  dependencies. install_claudecode.sh works around this by installing each
  dependency explicitly in topological order. This behavior may change in
  future Claude Code versions.

Reference: https://code.claude.com/docs/zh-TW/plugins-reference

Dependencies: Python stdlib only (no pip install required)
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("create_plugin")

# ─── Path Helpers ─────────────────────────────────────────────────────────────

def find_repo_root(start: Path = None) -> Path:
    """Find connsys-jarvis repo root by looking for known markers.

    Script location: framework/.../framework-expert-create-flow/scripts/
    → repo root is 5 levels up from this file.
    """
    if start is None:
        # Walk up from script location until we find the repo root marker
        current = Path(__file__).resolve().parent
        for _ in range(8):  # max 8 levels up
            if (current / "scripts" / "setup.py").exists():
                return current
            current = current.parent
    else:
        for candidate in [start, start.parent, start.parent.parent]:
            if (candidate / "scripts" / "setup.py").exists():
                return candidate
    # Fallback: cwd
    return Path.cwd()


def scan_expert_jsons(repo_root: Path) -> list:
    """Scan repo for all expert.json files (pattern: domain/expert-name/expert.json)."""
    results = []
    for expert_json in sorted(repo_root.glob("*/*/expert.json")):
        # Skip test directories
        if "test-team" in str(expert_json) or "test" in expert_json.parent.name:
            continue
        results.append(expert_json)
    return results


# ─── Plugin.json Generation ──────────────────────────────────────────────────

def generate_plugin_json(expert_json_path: Path, expert_data: dict,
                          repo_root: Path) -> dict:
    """Generate a Claude Code plugin.json manifest from expert.json.

    Only emits metadata and dependency plugin names.
    Claude Code auto-detects skills/, commands/, agents/ directories.
    """
    plugin = {
        "name": expert_data["name"],
    }

    # Optional metadata
    if expert_data.get("version"):
        plugin["version"] = expert_data["version"]
    if expert_data.get("description"):
        plugin["description"] = expert_data["description"]
    if expert_data.get("owner"):
        plugin["author"] = {"name": expert_data["owner"]}

    # Keywords from triggers
    if expert_data.get("triggers"):
        plugin["keywords"] = expert_data["triggers"]

    # Component directories: explicitly list if they exist
    # Note: hooks/hooks.json, .mcp.json, .lsp.json are auto-loaded by Claude Code
    # — do NOT list them in plugin.json or it causes "Duplicate" errors.
    # Only skills/, commands/, agents/ need explicit listing.
    # Ref: https://code.claude.com/docs/zh-TW/plugins-reference
    expert_dir = expert_json_path.parent
    if (expert_dir / "skills").is_dir():
        plugin["skills"] = ["./skills/"]
    if (expert_dir / "commands").is_dir():
        plugin["commands"] = ["./commands/"]
    if (expert_dir / "agents").is_dir():
        plugin["agents"] = ["./agents/"]
    # monitors is NOT auto-detected, so list it explicitly
    if (expert_dir / "monitors" / "monitors.json").is_file():
        plugin["monitors"] = "./monitors/monitors.json"

    # Dependencies: map to plugin dependency names
    dep_names = []
    for dep in expert_data.get("dependencies", []):
        dep_expert_rel = dep.get("expert", "") if isinstance(dep, dict) else str(dep)
        if dep_expert_rel:
            dep_json = repo_root / dep_expert_rel / "expert.json"
            if dep_json.exists():
                try:
                    with open(dep_json) as f:
                        dep_data = json.load(f)
                    dep_names.append(dep_data["name"])
                except (json.JSONDecodeError, KeyError, OSError):
                    pass
    if dep_names:
        plugin["dependencies"] = dep_names

    return plugin


# ─── Marketplace.json Generation ─────────────────────────────────────────────

def generate_marketplace_json(expert_jsons: list, repo_root: Path) -> dict:
    """Generate a marketplace.json registry for all experts."""
    plugins = []
    for expert_json_path in expert_jsons:
        try:
            with open(expert_json_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", expert_json_path, exc)
            continue

        expert_dir = expert_json_path.parent
        rel_source = "./" + str(expert_dir.relative_to(repo_root))

        entry = {
            "name": data["name"],
            "source": rel_source,
        }
        if data.get("version"):
            entry["version"] = data["version"]
        if data.get("description"):
            entry["description"] = data["description"]

        plugins.append(entry)

    return {
        "name": "connsys-jarvis",
        "owner": {"name": "connsys-team"},
        "plugins": plugins,
        "metadata": {
            "version": "1.0",
            "description": "Connsys Jarvis Expert Plugins for Claude Code",
        },
    }


# ─── Doctor Mode ──────────────────────────────────────────────────────────────

def run_doctor(repo_root: Path, expert_jsons: list) -> bool:
    """Verify plugin.json correctness against expert.json.

    Requires claude CLI to be installed.
    """
    # Check claude CLI availability
    claude_path = None
    for name in ("claude",):
        import shutil
        path = shutil.which(name)
        if path:
            claude_path = path
            break

    if not claude_path:
        print("ERROR: claude CLI not found. --doctor requires claude to be installed.",
              file=sys.stderr)
        print("  Install: https://docs.anthropic.com/en/docs/claude-code/getting-started",
              file=sys.stderr)
        sys.exit(1)

    print(f"Doctor mode — claude CLI: {claude_path}")
    all_ok = True

    for expert_json_path in expert_jsons:
        expert_dir = expert_json_path.parent
        expert_name = expert_dir.name
        plugin_json_path = expert_dir / ".claude-plugin" / "plugin.json"

        print(f"\n--- {expert_name} ---")

        # 1. Static check: plugin.json exists
        if not plugin_json_path.exists():
            print(f"  ❌ plugin.json missing (run without --doctor first)")
            all_ok = False
            continue

        # 2. Load and compare
        try:
            with open(expert_json_path) as f:
                expert_data = json.load(f)
            with open(plugin_json_path) as f:
                plugin_data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ❌ Failed to read: {exc}")
            all_ok = False
            continue

        # 3. Name match
        if expert_data.get("name") != plugin_data.get("name"):
            print(f"  ❌ Name mismatch: expert={expert_data.get('name')} plugin={plugin_data.get('name')}")
            all_ok = False
        else:
            print(f"  ✅ Name: {plugin_data['name']}")

        # 4. Check no stale skill paths remain in plugin.json
        if plugin_data.get("skills"):
            print(f"  ❌ plugin.json still has 'skills' field — regenerate to remove it")
            all_ok = False

        # 5. Check dependencies are listed
        dep_names = plugin_data.get("dependencies", [])
        if dep_names:
            print(f"  ✅ Dependencies: {', '.join(dep_names)}")

        # 6. Internal skills directory
        own_skills = expert_dir / "skills"
        if own_skills.is_dir():
            internal_skills = expert_data.get("internal", {}).get("skills", [])
            for skill_name in internal_skills:
                skill_dir = own_skills / skill_name
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    print(f"  ✅ Internal skill: {skill_name}")
                else:
                    print(f"  ❌ Internal skill missing: {skill_name}")
                    all_ok = False

        # 6. Dynamic verification with claude CLI
        print(f"  → Running claude --plugin-dir verification...")
        try:
            result = subprocess.run(
                [claude_path, "--plugin-dir", str(expert_dir), "-p",
                 f"List all skills available from the plugin {expert_name}. Just list the skill names, one per line."],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"  ✅ Claude CLI loaded plugin successfully")
                if result.stdout.strip():
                    lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
                    print(f"     Skills detected: {len(lines)}")
            else:
                print(f"  ⚠️  Claude CLI returned non-zero: {result.returncode}")
                if result.stderr:
                    print(f"     stderr: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Claude CLI timed out (30s)")
        except FileNotFoundError:
            print(f"  ❌ Claude CLI not found at {claude_path}")
            all_ok = False

    return all_ok


# ─── Install Script Generation ───────────────────────────────────────────────

def resolve_dep_order(expert_json_path: Path, repo_root: Path,
                       visited: set = None) -> list:
    """Recursively resolve dependency install order (topological sort).

    Returns list of dependency expert names in the order they should be
    installed (deepest dependencies first).
    """
    if visited is None:
        visited = set()

    try:
        with open(expert_json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    name = data.get("name", "")
    if name in visited:
        return []
    visited.add(name)

    result = []
    for dep in data.get("dependencies", []):
        dep_rel = dep.get("expert", "") if isinstance(dep, dict) else str(dep)
        if not dep_rel:
            continue
        dep_json = repo_root / dep_rel / "expert.json"
        if dep_json.exists():
            # Recurse into dependency's dependencies first
            result.extend(resolve_dep_order(dep_json, repo_root, visited))
            try:
                with open(dep_json) as f:
                    dep_data = json.load(f)
                dep_name = dep_data.get("name", "")
                if dep_name and dep_name not in [r for r in result]:
                    result.append(dep_name)
            except (json.JSONDecodeError, OSError):
                pass

    return result


def get_marketplace_url(repo_root: Path) -> str:
    """Get marketplace Git URL from git remote, with fallback."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "https://github.com/swchen44/connsys-jarvis.git"


def generate_install_script(expert_name: str, dep_names: list,
                             marketplace_url: str, marketplace_name: str) -> str:
    """Generate install_claudecode.sh content for an expert."""
    # Build PLUGINS array: deps first, then the expert itself
    all_plugins = dep_names + [expert_name]
    plugins_bash = "\n".join(f'  "{p}"' for p in all_plugins)

    return f'''#!/usr/bin/env bash
# install_claudecode.sh — Install {expert_name} via Claude Code Plugin
# Auto-generated by create_plugin_from_expert.py
#
# LIMITATION (as of 2026-04):
#   Claude Code `plugin install --scope project` does NOT auto-install
#   plugin dependencies. This script installs each dependency explicitly
#   in the correct topological order. This behavior may change in future
#   Claude Code versions.
#
# Usage:
#   bash install_claudecode.sh              # Install to project scope
#   bash install_claudecode.sh --scope user # Install to user scope
set -euo pipefail

MARKETPLACE_URL="{marketplace_url}"
MARKETPLACE_NAME="{marketplace_name}"
SCOPE="${{1:---scope}}"
[ "$SCOPE" = "--scope" ] && SCOPE="${{2:-project}}"
# Normalize: if first arg is not --scope, use project as default
[[ "$SCOPE" == "--scope" ]] && SCOPE="project"

echo "=== Installing {expert_name} (scope: $SCOPE) ==="

# 1. Check claude CLI
if ! command -v claude &>/dev/null; then
  echo "ERROR: claude CLI not found."
  echo "Install: https://docs.anthropic.com/en/docs/claude-code"
  exit 1
fi

# 2. Add or update marketplace
echo "[1/3] Setting up marketplace..."
if claude plugin marketplace list --json 2>/dev/null | grep -q "\\"$MARKETPLACE_NAME\\""; then
  claude plugin marketplace update "$MARKETPLACE_NAME" 2>/dev/null || true
else
  claude plugin marketplace add "$MARKETPLACE_URL" --scope "$SCOPE"
fi

# 3. Install dependencies in order, then the expert itself
# NOTE: Claude Code currently does NOT auto-resolve dependencies in project
# scope. Each plugin must be installed explicitly. (As of 2026-04)
echo "[2/3] Installing plugins..."
PLUGINS=(
{plugins_bash}
)
for plugin in "${{PLUGINS[@]}}"; do
  echo "  → $plugin"
  claude plugin install "${{plugin}}@${{MARKETPLACE_NAME}}" --scope "$SCOPE" 2>/dev/null || true
done

# 4. Validate
echo "[3/3] Validating..."
claude plugin list --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
target = [p for p in data if \'$MARKETPLACE_NAME\' in p[\'id\'] and p.get(\'enabled\')]
print(f\'  Enabled plugins: {{len(target)}}\')
for p in target:
    errors = p.get(\'errors\', [])
    status = \'⚠️  \' + errors[0] if errors else \'✅\'
    print(f\'    {{status}} {{p[\"id\"]}}\')
" 2>/dev/null || true

echo ""
echo "Done! Restart Claude Code to activate."
'''


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate Claude Code plugin.json from connsys-jarvis expert.json files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_plugin_from_expert.py                    # Generate all
  python create_plugin_from_expert.py --dry-run           # Preview
  python create_plugin_from_expert.py --doctor            # Verify
  python create_plugin_from_expert.py --verbose --dry-run # Verbose preview

Design rationale:
  Each connsys-jarvis Expert maps 1:1 to a Claude Code Plugin.
  The script bridges expert.json (connsys-jarvis format) to plugin.json
  (Claude Code format), enabling installation via Claude Marketplace.

  Key mapping:
    expert.json name/version/description → plugin.json metadata
    expert.json internal.skills[]        → auto-detected from skills/ directory
    expert.json dependencies[].expert    → plugin.json dependencies
""",
    )
    parser.add_argument("--doctor", action="store_true",
                       help="Verify plugin.json correctness (requires claude CLI)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Print generated files without writing to disk")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable detailed logging output")
    parser.add_argument("--expert-dir", type=str, default=None,
                       help="Root directory to scan (default: auto-detect repo root)")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Find repo root
    if args.expert_dir:
        repo_root = Path(args.expert_dir).resolve()
    else:
        repo_root = find_repo_root()

    if not (repo_root / "scripts" / "setup.py").exists():
        print(f"ERROR: Not a connsys-jarvis repo: {repo_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Repo root: {repo_root}")

    # Scan for expert.json files
    expert_jsons = scan_expert_jsons(repo_root)
    print(f"Found {len(expert_jsons)} expert(s)")

    if not expert_jsons:
        print("No expert.json files found.")
        sys.exit(0)

    # Doctor mode
    if args.doctor:
        ok = run_doctor(repo_root, expert_jsons)
        sys.exit(0 if ok else 1)

    # Generate plugin.json for each expert
    for expert_json_path in expert_jsons:
        try:
            with open(expert_json_path) as f:
                expert_data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  SKIP {expert_json_path}: {exc}", file=sys.stderr)
            continue

        expert_dir = expert_json_path.parent
        expert_name = expert_data.get("name", expert_dir.name)
        plugin = generate_plugin_json(expert_json_path, expert_data, repo_root)

        plugin_dir = expert_dir / ".claude-plugin"
        plugin_json_path = plugin_dir / "plugin.json"

        content = json.dumps(plugin, indent=2, ensure_ascii=False) + "\n"

        if args.dry_run:
            print(f"\n--- {expert_name}: {plugin_json_path} ---")
            print(content)
        else:
            plugin_dir.mkdir(exist_ok=True)
            with open(plugin_json_path, "w") as f:
                f.write(content)
            logger.info("Written: %s", plugin_json_path)
            print(f"  ✅ {expert_name} → {plugin_json_path.relative_to(repo_root)}")

    # Generate marketplace.json
    marketplace = generate_marketplace_json(expert_jsons, repo_root)
    marketplace_dir = repo_root / ".claude-plugin"
    marketplace_path = marketplace_dir / "marketplace.json"

    marketplace_content = json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n"

    if args.dry_run:
        print(f"\n--- marketplace.json: {marketplace_path} ---")
        print(marketplace_content)
    else:
        marketplace_dir.mkdir(exist_ok=True)
        with open(marketplace_path, "w") as f:
            f.write(marketplace_content)
        print(f"  ✅ marketplace.json → {marketplace_path.relative_to(repo_root)}")

    # Generate install_claudecode.sh for each expert
    marketplace_url = get_marketplace_url(repo_root)
    marketplace_name = "connsys-jarvis"
    for expert_json_path in expert_jsons:
        try:
            with open(expert_json_path) as f:
                expert_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        expert_dir = expert_json_path.parent
        expert_name = expert_data.get("name", expert_dir.name)
        dep_names = resolve_dep_order(expert_json_path, repo_root)
        script_content = generate_install_script(
            expert_name, dep_names, marketplace_url, marketplace_name
        )
        install_path = expert_dir / "install_claudecode.sh"

        if args.dry_run:
            print(f"\n--- {expert_name}: install_claudecode.sh ---")
            print(script_content[:300] + "...")
        else:
            with open(install_path, "w") as f:
                f.write(script_content)
            install_path.chmod(0o755)
            print(f"  ✅ {expert_name} → install_claudecode.sh")

    if not args.dry_run:
        print(f"\nDone! Generated {len(expert_jsons)} plugin(s) + marketplace.json + install scripts")


if __name__ == "__main__":
    main()
