#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Connsys Jarvis Install Script
Usage: python connsys-jarvis/install.py [--init|--add|--remove|--uninstall|--list|--doctor] [expert.json]
"""

import os
import sys
import json
import re
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone


# ─── Constants ───────────────────────────────────────────────────────────────

JARVIS_DIR_NAME = "connsys-jarvis"
DOT_DIR_NAME = ".connsys-jarvis"
CLAUDE_DIR_NAME = ".claude"
INSTALLED_EXPERTS_FILE = ".installed-experts.json"
CLAUDE_MD = "CLAUDE.md"
ENV_FILE = ".env"
SCHEMA_VERSION = "1.0"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def find_workspace(script_path: Path) -> Path:
    """
    install.py is at <workspace>/connsys-jarvis/install.py
    So workspace = parent of connsys-jarvis/
    """
    return script_path.resolve().parent.parent


def get_dot_dir(workspace: Path) -> Path:
    return workspace / DOT_DIR_NAME


def get_claude_dir(workspace: Path) -> Path:
    return workspace / CLAUDE_DIR_NAME


def get_jarvis_dir(workspace: Path) -> Path:
    return workspace / JARVIS_DIR_NAME


def get_installed_experts_path(workspace: Path) -> Path:
    return get_dot_dir(workspace) / INSTALLED_EXPERTS_FILE


def load_installed_experts(workspace: Path) -> dict:
    path = get_installed_experts_path(workspace)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now_iso(),
        "experts": []
    }


def save_installed_experts(workspace: Path, data: dict):
    path = get_installed_experts_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_expert_json(expert_json_path: Path) -> dict:
    with open(expert_json_path) as f:
        return json.load(f)


def load_registry(workspace: Path) -> dict:
    registry_path = get_jarvis_dir(workspace) / "registry.json"
    if registry_path.exists():
        with open(registry_path) as f:
            return json.load(f)
    return {"experts": []}


def run_git_config(key: str) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return ""


def detect_scenario(workspace: Path) -> str:
    """Detect agent-first or legacy scenario."""
    if (workspace / ".repo").exists():
        return "legacy"
    if (workspace / "codespace").exists():
        return "agent-first"
    return "agent-first"


def get_codespace_path(workspace: Path) -> str:
    scenario = detect_scenario(workspace)
    if scenario == "legacy":
        return str(workspace)
    return str(workspace / "codespace")


# ─── Symlink Logic ────────────────────────────────────────────────────────────

def resolve_items(expert_dir: Path, kind: str, spec) -> list:
    """
    Resolve a dependency's skill/hook/agent/command list.
    spec can be:
      - "all" or ["all"] → return all items
      - list of names → return those names
      - None / missing → return []
    Returns list of item names.
    """
    if spec is None:
        return []
    if spec == "all" or spec == ["all"]:
        kind_dir = expert_dir / kind
        if not kind_dir.exists():
            return []
        if kind == "hooks":
            # hooks: individual files (.sh, .py)
            return [f.name for f in kind_dir.iterdir()
                    if f.is_file() and f.suffix in (".sh", ".py")]
        else:
            # skills, agents, commands: subdirectories
            return [d.name for d in kind_dir.iterdir() if d.is_dir()]
    if isinstance(spec, list):
        return spec
    return []


def apply_exclude_patterns(items: list, patterns: list) -> list:
    """Filter out items matching any exclude pattern."""
    if not patterns:
        return items
    compiled = [re.compile(p) for p in patterns]
    result = []
    for item in items:
        if not any(pat.search(item) for pat in compiled):
            result.append(item)
    return result


def create_symlink(link_path: Path, target_path: Path) -> str:
    """
    Create a symlink: link_path → target_path.
    Returns status string: 'created', 'exists', 'updated', 'error'.
    """
    try:
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_symlink() and os.readlink(link_path) == str(target_path):
                return "exists"
            link_path.unlink()
        link_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(target_path), str(link_path))
        return "created"
    except Exception as e:
        return f"error: {e}"


def remove_symlink(link_path: Path):
    if link_path.is_symlink():
        link_path.unlink()


def build_symlinks_for_expert(
    workspace: Path,
    expert_json_path: Path,
    expert_data: dict,
    exclude_patterns: list = None
) -> dict:
    """
    Build symlink specs for one expert (dependencies + internal).
    Returns dict: {'skills': [...], 'hooks': [...], 'agents': [...], 'commands': [...]}
    Each entry: {'name': str, 'link': Path, 'target': Path}
    """
    if exclude_patterns is None:
        exclude_patterns = expert_data.get("exclude_symlink", {}).get("patterns", [])

    jarvis_dir = get_jarvis_dir(workspace)
    claude_dir = get_claude_dir(workspace)
    symlinks = {"skills": [], "hooks": [], "agents": [], "commands": []}

    # Helper: expert_json_path relative to jarvis_dir → expert_dir
    def get_dep_expert_dir(dep_expert_rel: str) -> Path:
        return jarvis_dir / dep_expert_rel

    def add_symlinks_for_kind(expert_dir: Path, kind: str, spec):
        items = resolve_items(expert_dir, kind, spec)
        items = apply_exclude_patterns(items, exclude_patterns)
        for item_name in items:
            if kind == "hooks":
                target = expert_dir / "hooks" / item_name
                link = claude_dir / "hooks" / item_name
            elif kind == "skills":
                target = expert_dir / "skills" / item_name
                link = claude_dir / "skills" / item_name
            elif kind == "agents":
                target = expert_dir / "agents" / item_name
                link = claude_dir / "agents" / item_name
            elif kind == "commands":
                target = expert_dir / "commands" / item_name
                link = claude_dir / "commands" / item_name
            else:
                continue

            # Only add if target exists
            if target.exists():
                symlinks[kind].append({
                    "name": item_name,
                    "link": link,
                    "target": target
                })

    # Process dependencies
    for dep in expert_data.get("dependencies", []):
        dep_expert_rel = dep.get("expert", "")
        dep_expert_dir = get_dep_expert_dir(dep_expert_rel)
        if not dep_expert_dir.exists():
            print(f"  [WARN] Dependency expert dir not found: {dep_expert_dir}", file=sys.stderr)
            continue

        for kind in ["skills", "hooks", "agents", "commands"]:
            spec = dep.get(kind)
            add_symlinks_for_kind(dep_expert_dir, kind, spec)

    # Process internal (all items in each category)
    expert_dir = expert_json_path.parent
    internal = expert_data.get("internal", {})
    for kind in ["skills", "hooks", "agents", "commands"]:
        internal_items = internal.get(kind, [])
        if internal_items:
            add_symlinks_for_kind(expert_dir, kind, internal_items)

    return symlinks


def apply_symlinks(symlinks: dict) -> list:
    """Create all symlinks. Returns list of (name, status) tuples."""
    results = []
    for kind, items in symlinks.items():
        for item in items:
            status = create_symlink(item["link"], item["target"])
            results.append((kind, item["name"], status))
    return results


def clear_claude_symlinks(workspace: Path):
    """Remove all symlinks in .claude/{skills,hooks,agents,commands}/"""
    claude_dir = get_claude_dir(workspace)
    for kind in ["skills", "hooks", "agents", "commands"]:
        kind_dir = claude_dir / kind
        if not kind_dir.exists():
            continue
        for item in kind_dir.iterdir():
            if item.is_symlink():
                item.unlink()


# ─── CLAUDE.md Generation ─────────────────────────────────────────────────────

def generate_claude_md(workspace: Path, installed: dict) -> str:
    """Generate CLAUDE.md content."""
    experts = installed.get("experts", [])
    if not experts:
        return "# Connsys Jarvis\n\n（未安裝任何 Expert）\n\n@CLAUDE.local.md\n"

    # Find identity expert (last installed, is_identity=True or last in list)
    identity_expert = None
    for e in experts:
        if e.get("is_identity", False):
            identity_expert = e
    if identity_expert is None and experts:
        identity_expert = experts[-1]

    if len(experts) == 1:
        e = experts[0]
        expert_json_path = get_jarvis_dir(workspace) / e["path"]
        expert_data = load_expert_json(expert_json_path)
        display_name = expert_data.get("display_name", e["name"])
        ep = Path(e["path"]).parent  # path to expert dir relative to jarvis_dir

        lines = [
            f"# Consys Expert: {display_name}",
            "",
            f"@connsys-jarvis/{ep}/soul.md",
            f"@connsys-jarvis/{ep}/rules.md",
            f"@connsys-jarvis/{ep}/duties.md",
            f"@connsys-jarvis/{ep}/expert.md",
            "",
            "@CLAUDE.local.md",
            "",
        ]
    else:
        n = len(experts)
        lines = [
            f"# Consys Experts（{n} Experts 已安裝）",
            "",
        ]

        # Identity section
        if identity_expert:
            ep = Path(identity_expert["path"]).parent
            lines += [
                "## Expert Identity（以最後安裝的 Expert 為主）",
                f"@connsys-jarvis/{ep}/soul.md",
                f"@connsys-jarvis/{ep}/rules.md",
                f"@connsys-jarvis/{ep}/duties.md",
                "",
            ]

        # Capabilities section
        lines.append("## Expert Capabilities")
        for e in experts:
            ep = Path(e["path"]).parent
            lines.append(f"@connsys-jarvis/{ep}/expert.md")
        lines += ["", "@CLAUDE.local.md", ""]

    return "\n".join(lines)


def write_claude_md(workspace: Path, installed: dict):
    content = generate_claude_md(workspace, installed)
    claude_md_path = workspace / CLAUDE_MD
    with open(claude_md_path, "w") as f:
        f.write(content)
    print(f"  CLAUDE.md 已更新: {claude_md_path}")


# ─── .env Generation ──────────────────────────────────────────────────────────

def write_env_file(workspace: Path, active_expert_name: str):
    dot_dir = get_dot_dir(workspace)
    dot_dir.mkdir(parents=True, exist_ok=True)
    env_path = dot_dir / ENV_FILE

    jarvis_path = get_jarvis_dir(workspace)
    codespace_path = get_codespace_path(workspace)
    memory_path = dot_dir / "memory"
    employee_id = run_git_config("user.name") or "unknown"

    lines = [
        f'export CONNSYS_JARVIS_PATH="{jarvis_path}"',
        f'export CONNSYS_JARVIS_WORKSPACE_ROOT_PATH="{workspace}"',
        f'export CONNSYS_JARVIS_CODE_SPACE_PATH="{codespace_path}"',
        f'export CONNSYS_JARVIS_MEMORY_PATH="{memory_path}"',
        f'export CONNSYS_JARVIS_EMPLOYEE_ID="{employee_id}"',
        f'export CONNSYS_JARVIS_ACTIVE_EXPERT="{active_expert_name}"',
        "",
    ]
    with open(env_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  .env 已寫入: {env_path}")
    print(f"  請執行: source {env_path}")


# ─── .installed-experts.json ─────────────────────────────────────────────────

def make_expert_entry(
    workspace: Path,
    expert_json_path: Path,
    expert_data: dict,
    install_order: int,
    is_identity: bool,
    declared_symlinks: dict
) -> dict:
    jarvis_dir = get_jarvis_dir(workspace)
    rel_path = os.path.relpath(expert_json_path, jarvis_dir)
    domain_parts = Path(rel_path).parts
    domain = domain_parts[0] if domain_parts else "unknown"

    return {
        "name": expert_data["name"],
        "domain": expert_data.get("domain", domain),
        "version": expert_data.get("version", "1.0.0"),
        "path": rel_path,
        "installed_at": now_iso(),
        "install_order": install_order,
        "is_identity": is_identity,
        "declared_symlinks": {
            kind: [item["name"] for item in items]
            for kind, items in declared_symlinks.items()
        }
    }


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_init(workspace: Path, expert_json_rel: str):
    """--init: clean everything, install one expert."""
    print(f"\n=== Connsys Jarvis Init ===")
    print(f"Workspace: {workspace}")
    print(f"Expert: {expert_json_rel}")

    expert_json_path = workspace / expert_json_rel
    if not expert_json_path.exists():
        # Try relative to jarvis_dir
        expert_json_path = get_jarvis_dir(workspace) / expert_json_rel
    if not expert_json_path.exists():
        print(f"ERROR: expert.json not found: {expert_json_rel}", file=sys.stderr)
        sys.exit(1)

    expert_data = load_expert_json(expert_json_path)

    # 1. Clear all symlinks
    print("\n[1] 清除既有 symlinks...")
    clear_claude_symlinks(workspace)

    # 2. Clear installed-experts.json
    print("[2] 清除 .installed-experts.json...")
    installed = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now_iso(),
        "experts": []
    }

    # 3. Build symlinks
    print("[3] 建立 symlinks...")
    symlinks = build_symlinks_for_expert(workspace, expert_json_path, expert_data)
    results = apply_symlinks(symlinks)

    # Report
    for kind, name, status in results:
        icon = "+" if status == "created" else ("=" if status == "exists" else "!")
        print(f"  [{icon}] {kind}/{name} → {status}")

    # 4. Update installed-experts.json
    print("[4] 更新 .installed-experts.json...")
    entry = make_expert_entry(
        workspace, expert_json_path, expert_data,
        install_order=1, is_identity=True,
        declared_symlinks=symlinks
    )
    installed["experts"] = [entry]
    save_installed_experts(workspace, installed)

    # 5. Generate CLAUDE.md
    print("[5] 生成 CLAUDE.md...")
    write_claude_md(workspace, installed)

    # 6. Write .env
    print("[6] 寫入 .env...")
    write_env_file(workspace, expert_data["name"])

    print(f"\n完成！Expert '{expert_data['name']}' 已安裝。")


def cmd_add(workspace: Path, expert_json_rel: str):
    """--add: add one expert to existing installation."""
    print(f"\n=== Connsys Jarvis Add ===")
    print(f"Expert: {expert_json_rel}")

    expert_json_path = workspace / expert_json_rel
    if not expert_json_path.exists():
        expert_json_path = get_jarvis_dir(workspace) / expert_json_rel
    if not expert_json_path.exists():
        print(f"ERROR: expert.json not found: {expert_json_rel}", file=sys.stderr)
        sys.exit(1)

    expert_data = load_expert_json(expert_json_path)
    installed = load_installed_experts(workspace)

    # Check if already installed
    existing_names = [e["name"] for e in installed["experts"]]
    if expert_data["name"] in existing_names:
        print(f"Expert '{expert_data['name']}' 已安裝，更新...")
        installed["experts"] = [e for e in installed["experts"]
                                 if e["name"] != expert_data["name"]]

    # Mark previous identity as non-identity
    for e in installed["experts"]:
        e["is_identity"] = False

    # Build new expert symlinks
    symlinks = build_symlinks_for_expert(workspace, expert_json_path, expert_data)

    # Rebuild all symlinks (clear first, then rebuild all)
    clear_claude_symlinks(workspace)

    # Rebuild existing experts' symlinks
    for e in installed["experts"]:
        ep = get_jarvis_dir(workspace) / e["path"]
        if ep.exists():
            ed = load_expert_json(ep)
            sl = build_symlinks_for_expert(workspace, ep, ed)
            apply_symlinks(sl)

    # Apply new expert symlinks
    results = apply_symlinks(symlinks)
    for kind, name, status in results:
        icon = "+" if status == "created" else ("=" if status == "exists" else "!")
        print(f"  [{icon}] {kind}/{name} → {status}")

    # Add to installed
    new_order = max((e["install_order"] for e in installed["experts"]), default=0) + 1
    entry = make_expert_entry(
        workspace, expert_json_path, expert_data,
        install_order=new_order, is_identity=True,
        declared_symlinks=symlinks
    )
    installed["experts"].append(entry)
    save_installed_experts(workspace, installed)

    # Regenerate CLAUDE.md
    write_claude_md(workspace, installed)

    # Update .env active expert
    write_env_file(workspace, expert_data["name"])

    print(f"\n完成！Expert '{expert_data['name']}' 已加入。")


def cmd_remove(workspace: Path, expert_name: str):
    """--remove: remove one expert."""
    print(f"\n=== Connsys Jarvis Remove ===")
    print(f"Expert: {expert_name}")

    installed = load_installed_experts(workspace)
    target = next((e for e in installed["experts"] if e["name"] == expert_name), None)
    if not target:
        print(f"ERROR: Expert '{expert_name}' 未安裝", file=sys.stderr)
        sys.exit(1)

    # Remove from list
    remaining = [e for e in installed["experts"] if e["name"] != expert_name]

    # Reference count: build all symlinks that remaining experts would create
    symlink_ref_count = {}  # (kind, name) → count
    for e in remaining:
        ep = get_jarvis_dir(workspace) / e["path"]
        if ep.exists():
            ed = load_expert_json(ep)
            sl = build_symlinks_for_expert(workspace, ep, ed)
            for kind, items in sl.items():
                for item in items:
                    key = (kind, item["name"])
                    symlink_ref_count[key] = symlink_ref_count.get(key, 0) + 1

    # Remove symlinks that are only used by the removed expert (ref count = 0)
    claude_dir = get_claude_dir(workspace)
    for kind, sym_name in target.get("declared_symlinks", {}).items():
        if isinstance(sym_name, list):
            for name in sym_name:
                key = (kind, name)
                if symlink_ref_count.get(key, 0) == 0:
                    if kind == "hooks":
                        link = claude_dir / "hooks" / name
                    elif kind == "skills":
                        link = claude_dir / "skills" / name
                    elif kind == "agents":
                        link = claude_dir / "agents" / name
                    elif kind == "commands":
                        link = claude_dir / "commands" / name
                    else:
                        continue
                    remove_symlink(link)
                    print(f"  [-] 移除 {kind}/{name}")

    # Update identity
    if remaining and target.get("is_identity"):
        remaining[-1]["is_identity"] = True

    installed["experts"] = remaining
    save_installed_experts(workspace, installed)
    write_claude_md(workspace, installed)

    new_active = remaining[-1]["name"] if remaining else "none"
    write_env_file(workspace, new_active)

    print(f"\n完成！Expert '{expert_name}' 已移除。")


def cmd_uninstall(workspace: Path):
    """--uninstall: remove all symlinks and CLAUDE.md, keep logs and memory."""
    print(f"\n=== Connsys Jarvis Uninstall ===")

    print("[1] 清除所有 symlinks...")
    clear_claude_symlinks(workspace)

    print("[2] 清除 CLAUDE.md...")
    claude_md = workspace / CLAUDE_MD
    if claude_md.exists():
        claude_md.unlink()
        print(f"  已刪除 {claude_md}")

    print("[3] 清除 .installed-experts.json...")
    installed_path = get_installed_experts_path(workspace)
    if installed_path.exists():
        installed_path.unlink()

    dot_dir = get_dot_dir(workspace)
    env_path = dot_dir / ENV_FILE
    if env_path.exists():
        env_path.unlink()

    print(f"\n完成！保留 {dot_dir}/log/ 和 {dot_dir}/memory/")


def cmd_list(workspace: Path):
    """--list: show installed experts and symlinks."""
    installed = load_installed_experts(workspace)
    experts = installed.get("experts", [])
    claude_dir = get_claude_dir(workspace)

    print("\n=== 已安裝的 Experts ===\n")
    if not experts:
        print("（未安裝任何 Expert）")
    else:
        for e in experts:
            ep = Path(e["path"]).parent
            identity_marker = " ← identity" if e.get("is_identity") else ""
            print(f"[{e['install_order']}] {e['name']} ({ep}){identity_marker}")

    print("\n=== .claude/ 中的 Symlinks ===\n")
    for kind in ["skills", "agents", "commands", "hooks"]:
        kind_dir = claude_dir / kind
        if not kind_dir.exists():
            continue
        items = sorted([i for i in kind_dir.iterdir() if i.is_symlink()])
        if not items:
            continue
        kind_label = kind.capitalize()
        print(f"{kind_label} ({len(items)}):")
        for item in items:
            target = Path(os.readlink(item))
            status = "✅" if item.exists() else "❌"
            print(f"  {status} {item.name} → {target}")
        print()


def cmd_doctor(workspace: Path):
    """--doctor: health check."""
    installed = load_installed_experts(workspace)
    experts = installed.get("experts", [])
    claude_dir = get_claude_dir(workspace)

    print("\n=== Connsys Jarvis Doctor ===\n")

    print("已安裝的 Experts：")
    if not experts:
        print("  （未安裝任何 Expert）")
    else:
        for e in experts:
            print(f"  [{e['install_order']}] {e['name']} ({e['domain']})")

    print("\nSymlinks 健康狀態：")
    all_ok = True
    for kind in ["skills", "agents", "commands", "hooks"]:
        kind_dir = claude_dir / kind
        if not kind_dir.exists():
            continue
        items = sorted([i for i in kind_dir.iterdir() if i.is_symlink()])
        if not items:
            continue
        print(f"  {kind.capitalize()}：")
        for item in items:
            target = Path(os.readlink(item))
            if item.exists():
                print(f"    ✅ {item.name} → {target} OK")
            else:
                print(f"    ❌ {item.name} → {target} DANGLING")
                all_ok = False

    print("\n環境檢查：")

    # Python version
    pv = platform.python_version()
    py_ok = tuple(int(x) for x in pv.split(".")[:2]) >= (3, 8)
    py_icon = "✅" if py_ok else "❌"
    print(f"  Python: {pv} {py_icon}")

    # uv
    uv_path = shutil.which("uv")
    if uv_path:
        print(f"  uv: 找到 ({uv_path}) ✅")
    else:
        print("  uv: 未找到 ⚠️")

    # uvx
    uvx_path = shutil.which("uvx")
    if uvx_path:
        print(f"  uvx: 找到 ({uvx_path}) ✅")
    else:
        print("  uvx: 未找到 ⚠️")

    # .env
    env_path = get_dot_dir(workspace) / ENV_FILE
    env_icon = "✅" if env_path.exists() else "❌"
    print(f"  .env: {env_path} {env_icon}")

    # CLAUDE.md
    claude_md = workspace / CLAUDE_MD
    claude_icon = "✅" if claude_md.exists() else "❌"
    print(f"  CLAUDE.md: {claude_md} {claude_icon}")

    print()
    if all_ok:
        print("總體狀態：✅ 健康")
    else:
        print("總體狀態：❌ 有 dangling symlinks，請重新執行 --init 或 --add")


# ─── Main ────────────────────────────────────────────────────────────────────

def print_usage():
    print("""
Connsys Jarvis Install Script

用法（從 workspace 根目錄執行）：
  python connsys-jarvis/install.py --init   <expert.json>   初始化並安裝 Expert
  python connsys-jarvis/install.py --add    <expert.json>   新增 Expert
  python connsys-jarvis/install.py --remove <expert-name>   移除 Expert
  python connsys-jarvis/install.py --uninstall              卸載所有
  python connsys-jarvis/install.py --list                   列出已安裝
  python connsys-jarvis/install.py --doctor                 健康檢查

範例：
  python connsys-jarvis/install.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json
  python connsys-jarvis/install.py --add  sys-bora/experts/sys-bora-preflight-expert/expert.json
  python connsys-jarvis/install.py --remove framework-base-expert
  python connsys-jarvis/install.py --list
  python connsys-jarvis/install.py --doctor

注意：expert.json 路徑可以是相對於 workspace 或相對於 connsys-jarvis/ 目錄。
""")


def main():
    script_path = Path(sys.argv[0])
    workspace = find_workspace(script_path)

    args = sys.argv[1:]
    if not args:
        print_usage()
        sys.exit(0)

    cmd = args[0]

    if cmd == "--init":
        if len(args) < 2:
            print("ERROR: --init 需要指定 expert.json 路徑", file=sys.stderr)
            sys.exit(1)
        cmd_init(workspace, args[1])

    elif cmd == "--add":
        if len(args) < 2:
            print("ERROR: --add 需要指定 expert.json 路徑", file=sys.stderr)
            sys.exit(1)
        cmd_add(workspace, args[1])

    elif cmd == "--remove":
        if len(args) < 2:
            print("ERROR: --remove 需要指定 expert name", file=sys.stderr)
            sys.exit(1)
        cmd_remove(workspace, args[1])

    elif cmd == "--uninstall":
        cmd_uninstall(workspace)

    elif cmd == "--list":
        cmd_list(workspace)

    elif cmd == "--doctor":
        cmd_doctor(workspace)

    elif cmd in ("-h", "--help"):
        print_usage()

    else:
        print(f"ERROR: 未知指令 '{cmd}'", file=sys.stderr)
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
