#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
connsys-jarvis/scripts/install.py — Connsys Jarvis 安裝管理程式
================================================================

**用途**：管理 Connsys Expert 在 workspace 中的安裝、更新與移除。
核心工作是在 workspace 的 `.claude/` 目錄建立 symlinks，指向
connsys-jarvis repo 中 Expert 的 skills / hooks / agents / commands，
並生成 CLAUDE.md 和 .connsys-jarvis/.env 等設定檔。

**執行方式（從 workspace 根目錄）**：
    uv run ./connsys-jarvis/scripts/install.py --init   <expert.json>
    uv run ./connsys-jarvis/scripts/install.py --add    <expert.json>
    uv run ./connsys-jarvis/scripts/install.py --remove <expert-name>
    uv run ./connsys-jarvis/scripts/install.py --uninstall
    uv run ./connsys-jarvis/scripts/install.py --list
    uv run ./connsys-jarvis/scripts/install.py --doctor
    uv run ./connsys-jarvis/scripts/install.py --debug --init <expert.json>

**Debug 模式**：加 --debug 旗標後，console 顯示 DEBUG 層級訊息；
同時寫入 .connsys-jarvis/log/install.log（不論是否加 --debug）。

**設計原則**：
  - Pure Python stdlib（無第三方依賴），相容 PEP 723 inline script metadata
  - workspace = cwd（使用者從 workspace root 執行），不跟隨 symlink
  - 所有安裝狀態持久化於 .connsys-jarvis/.installed-experts.json

**相關文件**：
  - agents-requirements.md  — 功能需求
  - agents-design.md        — 系統設計
  - scripts/README.md       — 開發者指南
  - scripts/test/test_install.py — pytest 單元測試
"""

import logging
import os
import sys
import json
import re
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone


# ─── Constants ────────────────────────────────────────────────────────────────
# 這些常數定義系統關鍵路徑和檔案名稱，集中管理方便未來修改。

JARVIS_DIR_NAME     = "connsys-jarvis"       # connsys-jarvis repo 的資料夾名稱
DOT_DIR_NAME        = ".connsys-jarvis"       # workspace 隱藏資料夾（.gitignore 排除）
CLAUDE_DIR_NAME     = ".claude"               # Claude Code 的設定資料夾
INSTALLED_EXPERTS_FILE = ".installed-experts.json"  # 安裝狀態持久化檔
CLAUDE_MD           = "CLAUDE.md"             # Claude Code 啟動時載入的 context 設定
ENV_FILE            = ".env"                  # 環境變數輸出檔
SCHEMA_VERSION      = "1.0"                   # .installed-experts.json 的 schema 版本

# ─── Logger ───────────────────────────────────────────────────────────────────
# 使用 module-level logger，方便 test_install.py 等 caller 注入 handler。
# 預設不加任何 handler（避免 "No handlers could be found" 警告），
# 由 setup_logging() 在 main() 中統一設定。
logger = logging.getLogger("connsys_jarvis.install")


# ─── Logging Setup ────────────────────────────────────────────────────────────

def setup_logging(debug: bool = False, log_file: Path = None) -> None:
    """設定 logging 的輸出格式與層級。

    架構：
      1. Console handler（stderr）：
           --debug 時輸出 DEBUG+；否則只輸出 WARNING+（不干擾正常輸出）
      2. File handler（.connsys-jarvis/log/install.log）：
           永遠記錄 DEBUG+，方便事後追查問題

    Args:
        debug:    True = 啟用 debug 模式，console 顯示 DEBUG 層級訊息
        log_file: log 檔路徑；None = 不建立 file handler（例如測試環境）

    日誌格式範例：
        2026-03-26T12:00:00Z [DEBUG  ] cmd_init:443 - workspace=/tmp/cj-test
        2026-03-26T12:00:00Z [WARNING] build_symlinks:244 - dep dir not found: ...
    """
    # 使用 UTC ISO 8601 timestamp，方便跨時區比對
    fmt = "%(asctime)s [%(levelname)-7s] %(funcName)s:%(lineno)d - %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%SZ"

    # root logger 設為最低層級，讓各 handler 自行過濾
    logger.setLevel(logging.DEBUG)

    # ── Console handler ──
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    console_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    # 避免重複加 handler（例如測試時多次呼叫）
    if not logger.handlers:
        logger.addHandler(console_handler)
    else:
        # 更新現有 console handler 的層級
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
                h.setLevel(logging.DEBUG if debug else logging.WARNING)

    # ── File handler ──
    # 永遠記錄 DEBUG，讓使用者事後可以翻閱詳細過程
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
            logger.addHandler(file_handler)
            logger.debug("Log file opened: %s", log_file)
        except OSError as exc:
            # log 檔開不了不應中斷安裝流程，只印警告
            logger.warning("Cannot open log file %s: %s", log_file, exc)


# ─── Time Helpers ─────────────────────────────────────────────────────────────

def now_iso() -> str:
    """回傳目前 UTC 時間的 ISO 8601 字串，用於 JSON 欄位 updated_at / installed_at。

    Returns:
        例如 "2026-03-26T08:00:00Z"
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    """回傳今日 UTC 日期的 ISO 8601 字串（YYYY-MM-DD）。

    Returns:
        例如 "2026-03-26"
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─── Path Helpers ─────────────────────────────────────────────────────────────

def find_workspace(script_path: Path) -> Path:
    """取得 workspace 根目錄（= cwd，即使用者執行指令的目錄）。

    **設計決策**：workspace 定義為 cwd 而非從 script_path 推導。
    原因：connsys-jarvis 通常以 symlink 形式存在於 workspace，
    若用 script_path.resolve().parent.parent 會跟隨 symlink，
    導致 workspace 指向 connsys-jarvis 真實 repo 而非使用者的 workspace。

    **使用約定**：使用者必須從 workspace root 執行，例如：
        cd /path/to/workspace
        python ./connsys-jarvis/scripts/install.py --init ...

    Args:
        script_path: sys.argv[0] 的 Path（保留此參數以維持介面一致性，目前未使用）

    Returns:
        workspace 根目錄的 Path（= Path.cwd()）
    """
    workspace = Path.cwd()
    logger.debug("find_workspace: cwd=%s", workspace)
    return workspace


def get_dot_dir(workspace: Path) -> Path:
    """取得 .connsys-jarvis/ 隱藏資料夾路徑（runtime 資料存放處）。"""
    return workspace / DOT_DIR_NAME


def get_claude_dir(workspace: Path) -> Path:
    """取得 .claude/ 目錄路徑（Claude Code 讀取 skills/hooks/commands 的位置）。"""
    return workspace / CLAUDE_DIR_NAME


def get_jarvis_dir(workspace: Path) -> Path:
    """取得 connsys-jarvis/ 目錄路徑（Expert repo 的根目錄）。"""
    return workspace / JARVIS_DIR_NAME


def get_installed_experts_path(workspace: Path) -> Path:
    """取得 .installed-experts.json 的完整路徑。"""
    return get_dot_dir(workspace) / INSTALLED_EXPERTS_FILE


# ─── JSON I/O Helpers ─────────────────────────────────────────────────────────

def load_installed_experts(workspace: Path) -> dict:
    """從 .installed-experts.json 讀取安裝狀態。

    若檔案不存在（首次安裝），回傳空白骨架，方便後續操作統一處理。

    Returns:
        dict，格式：{"schema_version": str, "updated_at": str, "experts": list}
    """
    path = get_installed_experts_path(workspace)
    if path.exists():
        logger.debug("load_installed_experts: reading %s", path)
        with open(path) as f:
            data = json.load(f)
        logger.debug("load_installed_experts: found %d experts", len(data.get("experts", [])))
        return data

    # 首次安裝，回傳空骨架
    logger.debug("load_installed_experts: file not found, returning empty skeleton")
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now_iso(),
        "experts": []
    }


def save_installed_experts(workspace: Path, data: dict) -> None:
    """將安裝狀態寫回 .installed-experts.json，並更新 updated_at 時間戳。

    Args:
        workspace: workspace 根目錄
        data: 安裝狀態 dict（會直接修改其 updated_at 欄位）
    """
    path = get_installed_experts_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    logger.debug("save_installed_experts: writing %d experts to %s",
                 len(data.get("experts", [])), path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # 確保檔案以 newline 結尾（符合 POSIX 規範）


def load_expert_json(expert_json_path: Path) -> dict:
    """讀取 expert.json 檔案。

    expert.json 結構（節錄）：
        {
          "name": "wifi-bora-memory-slim-expert",
          "display_name": "WiFi Bora Memory Slim Expert",
          "domain": "wifi-bora",
          "version": "1.0.0",
          "dependencies": [
            {"expert": "framework/experts/framework-base-expert", "skills": "all", "hooks": "all"}
          ],
          "internal": {"skills": ["wifi-bora-memslim-flow"], "hooks": []},
          "exclude_symlink": {"patterns": []}
        }

    Args:
        expert_json_path: expert.json 的絕對路徑

    Returns:
        解析後的 dict
    """
    logger.debug("load_expert_json: %s", expert_json_path)
    with open(expert_json_path) as f:
        return json.load(f)


def load_registry(workspace: Path) -> dict:
    """讀取 registry.json（所有可用 Expert 的目錄）。

    Args:
        workspace: workspace 根目錄

    Returns:
        {"experts": [...]} 或 {"experts": []}（檔案不存在時）
    """
    registry_path = get_jarvis_dir(workspace) / "registry.json"
    if registry_path.exists():
        logger.debug("load_registry: reading %s", registry_path)
        with open(registry_path) as f:
            return json.load(f)
    logger.warning("load_registry: registry.json not found at %s", registry_path)
    return {"experts": []}


# ─── Environment Helpers ──────────────────────────────────────────────────────

def run_git_config(key: str) -> str:
    """從 git config 讀取設定值（通常用來取得 user.name 作為工號）。

    Args:
        key: git config key，例如 "user.name"

    Returns:
        設定值字串；失敗（git 未安裝、key 不存在）時回傳空字串
    """
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True, text=True, check=True
        )
        value = result.stdout.strip()
        logger.debug("run_git_config: %s=%r", key, value)
        return value
    except Exception as exc:
        logger.debug("run_git_config: failed to get %s: %s", key, exc)
        return ""


def detect_scenario(workspace: Path) -> str:
    """偵測 workspace 屬於 Agent First 還是 Legacy 場景。

    判斷規則：
      - workspace 根目錄存在 .repo/  → Legacy
        （.repo 是 Android repo tool 的 manifest 目錄，代表已手動 clone）
      - 其他情況                     → Agent First
        （空白 workspace 或已有 codespace/ 目錄）

    **為何需要區分**：
      兩種場景的 CONNSYS_JARVIS_CODE_SPACE_PATH 不同（見 get_codespace_path）。
      Legacy 場景 code 在 workspace root，Agent First 則在 workspace/codespace/。

    Args:
        workspace: workspace 根目錄

    Returns:
        "legacy" 或 "agent-first"
    """
    if (workspace / ".repo").exists():
        logger.debug("detect_scenario: .repo found → legacy")
        return "legacy"
    if (workspace / "codespace").exists():
        logger.debug("detect_scenario: codespace/ found → agent-first")
        return "agent-first"
    logger.debug("detect_scenario: no .repo, no codespace/ → agent-first (default)")
    return "agent-first"


def get_codespace_path(workspace: Path) -> str:
    """取得程式碼所在路徑（CONNSYS_JARVIS_CODE_SPACE_PATH）。

    邏輯：
      - Agent First：code 由 Expert 引導下載到 workspace/codespace/
      - Legacy：code 已在 workspace root（.repo/ 存在）

    Args:
        workspace: workspace 根目錄

    Returns:
        絕對路徑字串
    """
    scenario = detect_scenario(workspace)
    if scenario == "legacy":
        logger.debug("get_codespace_path: legacy → %s", workspace)
        return str(workspace)
    path = str(workspace / "codespace")
    logger.debug("get_codespace_path: agent-first → %s", path)
    return path


# ─── Symlink Logic ─────────────────────────────────────────────────────────────
# 核心三步驟建立 symlink 的邏輯：
#   Step 1: 依序處理 expert.json 的 dependencies[]（每個依賴 expert 的貢獻）
#   Step 2: 處理 internal（此 expert 自身的 skills/hooks/commands）
#   Step 3: 套用 exclude_symlink.patterns（全域 regex 過濾，跨所有來源）

def resolve_items(expert_dir: Path, kind: str, spec) -> list:
    """將 expert.json 中的 spec 規格解析成實際的 item 名稱清單。

    **spec 格式對照**：
      - None 或省略 key  → [] （不繼承此 kind）
      - "all" 或 ["all"] → 目錄中所有 item（hooks 為 .sh/.py 檔；其他為子目錄）
      - ["name1","name2"] → 指定名稱清單（精確控制）

    **hooks 與 skills 的差異**：
      - hooks   是個別檔案（session-start.sh, memory-helper.py）
      - skills / agents / commands 是子目錄（每個 skill 是一個資料夾）

    Args:
        expert_dir: Expert 根目錄（expert.json 所在目錄）
        kind:       "skills" / "hooks" / "agents" / "commands"
        spec:       None、"all"、["all"]、或 ["name1", "name2"]

    Returns:
        item 名稱的 list（已解析，但尚未套用 exclude patterns）
    """
    logger.debug("resolve_items: expert_dir=%s, kind=%s, spec=%r", expert_dir, kind, spec)

    if spec is None:
        logger.debug("resolve_items: spec is None → []")
        return []

    if spec == "all" or spec == ["all"]:
        kind_dir = expert_dir / kind
        if not kind_dir.exists():
            logger.debug("resolve_items: %s does not exist → []", kind_dir)
            return []
        if kind == "hooks":
            # hooks 是個別執行檔，只收 .sh 和 .py（排除 __pycache__ 等）
            items = [f.name for f in kind_dir.iterdir()
                     if f.is_file() and f.suffix in (".sh", ".py")]
        else:
            # skills / agents / commands 是子目錄，每個 item 為一個資料夾
            items = [d.name for d in kind_dir.iterdir() if d.is_dir()]
        logger.debug("resolve_items: 'all' resolved to %d items: %s", len(items), items)
        return items

    if isinstance(spec, list):
        # 明確指定的名稱清單
        logger.debug("resolve_items: explicit list=%r", spec)
        return spec

    logger.debug("resolve_items: unknown spec type %r → []", spec)
    return []


def apply_exclude_patterns(items: list, patterns: list) -> list:
    """套用 exclude_symlink.patterns 全域過濾，移除名稱符合任一 regex 的 item。

    **設計意圖**：某些 Expert 在特定環境下不需要某些 skill（例如 LSP tool
    在低資源環境下會關閉），透過全域 regex 一次過濾跨所有 dependency 的 link。

    Args:
        items:    待過濾的 item 名稱 list
        patterns: regex pattern 字串 list（空清單 = 不過濾）

    Returns:
        過濾後的 item 名稱 list（未匹配到任何 pattern 的項目）

    Example:
        patterns = [".*-lsp-.*"]
        items    = ["wifi-bora-lsp-tool", "wifi-bora-memslim-flow"]
        → result = ["wifi-bora-memslim-flow"]  （lsp 被過濾）
    """
    if not patterns:
        return items
    compiled = [re.compile(p) for p in patterns]
    result = []
    for item in items:
        matched = any(pat.search(item) for pat in compiled)
        if matched:
            logger.debug("apply_exclude_patterns: EXCLUDED %r (matched pattern)", item)
        else:
            result.append(item)
    logger.debug("apply_exclude_patterns: %d/%d items passed", len(result), len(items))
    return result


def create_symlink(link_path: Path, target_path: Path) -> str:
    """建立單一 symlink：link_path → target_path。

    **冪等行為**：若相同的 symlink 已存在（目標路徑相同），跳過不動作。
    若存在但目標不同（stale link），先刪除再重建。

    Args:
        link_path:   symlink 路徑（.claude/skills/<name>）
        target_path: symlink 指向的目標路徑（connsys-jarvis/.../skills/<name>/）

    Returns:
        狀態字串："created"（新建）、"exists"（已存在跳過）、或 "error: <msg>"
    """
    logger.debug("create_symlink: %s → %s", link_path, target_path)
    try:
        if link_path.exists() or link_path.is_symlink():
            existing_target = os.readlink(link_path)
            if existing_target == str(target_path):
                logger.debug("create_symlink: already exists, skipping")
                return "exists"
            # 目標不同，刪舊建新（stale or updated）
            logger.debug("create_symlink: stale link (was → %s), recreating", existing_target)
            link_path.unlink()

        link_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(target_path), str(link_path))
        logger.debug("create_symlink: created")
        return "created"
    except Exception as exc:
        logger.error("create_symlink: failed for %s: %s", link_path, exc)
        return f"error: {exc}"


def remove_symlink(link_path: Path) -> None:
    """移除 symlink（若存在）。非 symlink 的一般檔案不會被刪除。

    Args:
        link_path: 要移除的 symlink 路徑
    """
    if link_path.is_symlink():
        logger.debug("remove_symlink: unlinking %s", link_path)
        link_path.unlink()
    else:
        logger.debug("remove_symlink: %s is not a symlink, skipping", link_path)


def build_symlinks_for_expert(
    workspace: Path,
    expert_json_path: Path,
    expert_data: dict,
    exclude_patterns: list = None
) -> dict:
    """計算一個 Expert 應建立的完整 symlink 清單（三步驟核心邏輯）。

    **三步驟建立順序**：
      1. Dependencies：依序處理 expert.json["dependencies"] 中每個依賴 expert
         的 skills/hooks/agents/commands 貢獻，依各自的 spec 規格解析
      2. Internal：處理 expert.json["internal"]，即此 Expert 自身提供的 items
      3. Exclude：套用 expert.json["exclude_symlink"]["patterns"] 全域 regex 過濾

    **重複 item 處理**：同名 item 由後加入者覆蓋（list 中後面的 dependency 優先）。
    這讓 internal 可以覆蓋 dependency 的同名 skill。

    Args:
        workspace:        workspace 根目錄
        expert_json_path: expert.json 的絕對路徑
        expert_data:      已解析的 expert.json 內容 dict
        exclude_patterns: 外部傳入的 exclude patterns；若為 None 則從 expert_data 讀取

    Returns:
        dict，格式：
        {
          "skills":   [{"name": str, "link": Path, "target": Path}, ...],
          "hooks":    [...],
          "agents":   [...],
          "commands": [...]
        }
        link = .claude/<kind>/<name>，target = connsys-jarvis/.../skills/<name>/
    """
    if exclude_patterns is None:
        exclude_patterns = expert_data.get("exclude_symlink", {}).get("patterns", [])
        logger.debug("build_symlinks_for_expert: using expert's own exclude_patterns=%r",
                     exclude_patterns)

    logger.debug("build_symlinks_for_expert: expert=%s, deps=%d, exclude_patterns=%r",
                 expert_data.get("name"), len(expert_data.get("dependencies", [])),
                 exclude_patterns)

    jarvis_dir = get_jarvis_dir(workspace)
    claude_dir = get_claude_dir(workspace)
    # 使用 dict 以 item name 為 key，實現後加入者覆蓋的語義
    # 最終轉為 list 輸出
    symlink_map: dict[str, dict] = {}   # key = (kind, name)，value = {name, link, target}

    def add_items_for_kind(expert_dir: Path, kind: str, spec) -> None:
        """內部 helper：解析並加入某個 kind 的所有 symlink spec。"""
        items = resolve_items(expert_dir, kind, spec)
        items = apply_exclude_patterns(items, exclude_patterns)
        for item_name in items:
            # 根據 kind 決定目標路徑結構
            # hooks 是個別檔案；skills/agents/commands 是子目錄
            if kind == "hooks":
                target = expert_dir / "hooks" / item_name
                link   = claude_dir / "hooks" / item_name
            else:
                target = expert_dir / kind / item_name
                link   = claude_dir / kind / item_name

            if not target.exists():
                logger.warning("build_symlinks: target not found, skipping: %s", target)
                continue

            key = (kind, item_name)
            if key in symlink_map:
                logger.debug("build_symlinks: overriding existing entry for %s/%s", kind, item_name)
            symlink_map[key] = {"name": item_name, "link": link, "target": target}

    # ── Step 1: Dependencies ──
    # 依 dependencies[] 的宣告順序處理，後面的 dep 可以覆蓋前面的同名 item
    logger.debug("build_symlinks_for_expert: Step 1 - processing dependencies")
    for dep in expert_data.get("dependencies", []):
        dep_expert_rel = dep.get("expert", "")
        dep_expert_dir = jarvis_dir / dep_expert_rel
        logger.debug("build_symlinks_for_expert: dep=%s", dep_expert_rel)
        if not dep_expert_dir.exists():
            # 依賴的 expert 目錄不存在，警告並跳過（不中斷安裝）
            logger.warning("build_symlinks_for_expert: dep dir not found: %s", dep_expert_dir)
            print(f"  [WARN] Dependency expert dir not found: {dep_expert_dir}", file=sys.stderr)
            continue
        for kind in ["skills", "hooks", "agents", "commands"]:
            add_items_for_kind(dep_expert_dir, kind, dep.get(kind))

    # ── Step 2: Internal ──
    # 此 expert 自身提供的 skills/hooks 等，通常是最高優先（可覆蓋 dependency）
    logger.debug("build_symlinks_for_expert: Step 2 - processing internal")
    expert_dir = expert_json_path.parent
    internal   = expert_data.get("internal", {})
    for kind in ["skills", "hooks", "agents", "commands"]:
        internal_spec = internal.get(kind, [])
        if internal_spec:
            add_items_for_kind(expert_dir, kind, internal_spec)

    # ── 將 symlink_map 轉回以 kind 分組的輸出格式 ──
    result: dict[str, list] = {"skills": [], "hooks": [], "agents": [], "commands": []}
    for (kind, _), entry in symlink_map.items():
        result[kind].append(entry)

    total = sum(len(v) for v in result.values())
    logger.debug("build_symlinks_for_expert: total %d symlinks planned", total)
    return result


def apply_symlinks(symlinks: dict) -> list:
    """執行 build_symlinks_for_expert 產生的 symlink 清單，實際在 .claude/ 建立連結。

    Args:
        symlinks: build_symlinks_for_expert 的回傳值

    Returns:
        list of (kind: str, name: str, status: str)，status 為 "created"/"exists"/"error:..."
    """
    results = []
    for kind, items in symlinks.items():
        for item in items:
            status = create_symlink(item["link"], item["target"])
            logger.debug("apply_symlinks: %s/%s → %s", kind, item["name"], status)
            results.append((kind, item["name"], status))
    return results


def clear_claude_symlinks(workspace: Path) -> None:
    """清除 .claude/{skills,hooks,agents,commands}/ 中的所有 symlinks。

    **注意**：只刪 symlink，不刪一般檔案（保護使用者自己建立的設定）。

    Args:
        workspace: workspace 根目錄
    """
    claude_dir = get_claude_dir(workspace)
    total_removed = 0
    for kind in ["skills", "hooks", "agents", "commands"]:
        kind_dir = claude_dir / kind
        if not kind_dir.exists():
            continue
        for item in kind_dir.iterdir():
            if item.is_symlink():
                logger.debug("clear_claude_symlinks: removing %s", item)
                item.unlink()
                total_removed += 1
    logger.debug("clear_claude_symlinks: removed %d symlinks", total_removed)


# ─── CLAUDE.md Generation ─────────────────────────────────────────────────────
# CLAUDE.md 是 Claude Code 啟動時自動載入的 context 檔。
# 根據安裝的 Expert 數量，生成不同格式：
#   單一 Expert: 完整的 soul/rules/duties/expert @include
#   多個 Expert: Identity 區段（主 Expert 的身份設定） + Capabilities 區段（所有 expert.md）

def generate_claude_md(workspace: Path, installed: dict) -> str:
    """生成 CLAUDE.md 的文字內容。

    **單一 Expert 格式**（最常見）：
        # Consys Expert: WiFi Bora Memory Slim Expert
        @connsys-jarvis/wifi-bora/experts/.../soul.md
        @connsys-jarvis/wifi-bora/experts/.../rules.md
        @connsys-jarvis/wifi-bora/experts/.../duties.md
        @connsys-jarvis/wifi-bora/experts/.../expert.md
        @CLAUDE.local.md

    **多 Expert 格式**：
        # Consys Experts（N Experts 已安裝）
        ## Expert Identity（以最後安裝的 Expert 為主）
        @connsys-jarvis/.../soul.md   ← identity expert 的身份定義
        @connsys-jarvis/.../rules.md
        @connsys-jarvis/.../duties.md
        ## Expert Capabilities
        @connsys-jarvis/.../expert.md  ← 所有 Expert 的能力描述
        @connsys-jarvis/.../expert.md
        @CLAUDE.local.md

    **@CLAUDE.local.md**：workspace 本地個人化設定，檔案不存在時 Claude Code 會忽略。

    Args:
        workspace: workspace 根目錄（用來讀取 expert.json）
        installed: load_installed_experts 的回傳值

    Returns:
        CLAUDE.md 的完整文字內容（string）
    """
    experts = installed.get("experts", [])
    logger.debug("generate_claude_md: %d experts", len(experts))

    if not experts:
        return "# Connsys Jarvis\n\n（未安裝任何 Expert）\n\n@CLAUDE.local.md\n"

    # 找出 identity expert（最後一個 is_identity=True 的 expert）
    identity_expert = None
    for e in experts:
        if e.get("is_identity", False):
            identity_expert = e
    if identity_expert is None:
        # fallback：取最後一個
        identity_expert = experts[-1]
    logger.debug("generate_claude_md: identity_expert=%s", identity_expert["name"])

    if len(experts) == 1:
        # ── 單一 Expert 格式 ──
        e = experts[0]
        expert_json_path = get_jarvis_dir(workspace) / e["path"]
        expert_data  = load_expert_json(expert_json_path)
        display_name = expert_data.get("display_name", e["name"])
        # ep = expert 資料夾相對 connsys-jarvis 根目錄的路徑（去掉 /expert.json）
        ep = Path(e["path"]).parent

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
        # ── 多 Expert 格式 ──
        n = len(experts)
        lines = [f"# Consys Experts（{n} Experts 已安裝）", ""]

        # Identity 區段：只放主 Expert 的 soul/rules/duties
        ep = Path(identity_expert["path"]).parent
        lines += [
            "## Expert Identity（以最後安裝的 Expert 為主）",
            f"@connsys-jarvis/{ep}/soul.md",
            f"@connsys-jarvis/{ep}/rules.md",
            f"@connsys-jarvis/{ep}/duties.md",
            "",
        ]

        # Capabilities 區段：所有 Expert 的 expert.md
        lines.append("## Expert Capabilities")
        for e in experts:
            ep = Path(e["path"]).parent
            lines.append(f"@connsys-jarvis/{ep}/expert.md")
        lines += ["", "@CLAUDE.local.md", ""]

    content = "\n".join(lines)
    logger.debug("generate_claude_md: generated %d lines", len(lines))
    return content


def write_claude_md(workspace: Path, installed: dict) -> None:
    """生成並寫入 workspace/CLAUDE.md。

    Args:
        workspace: workspace 根目錄
        installed: 安裝狀態 dict
    """
    content = generate_claude_md(workspace, installed)
    claude_md_path = workspace / CLAUDE_MD
    logger.debug("write_claude_md: writing %d chars to %s", len(content), claude_md_path)
    with open(claude_md_path, "w") as f:
        f.write(content)
    print(f"  CLAUDE.md 已更新: {claude_md_path}")


# ─── .env Generation ──────────────────────────────────────────────────────────
# .env 輸出 6 個 CONNSYS_JARVIS_* 環境變數。
# 使用者在安裝後需手動執行 `source .connsys-jarvis/.env` 讓 shell 生效。
# （Python 程式無法直接修改 parent shell 的環境變數）

def write_env_file(workspace: Path, active_expert_name: str) -> None:
    """產生並寫入 .connsys-jarvis/.env（CONNSYS_JARVIS_* 環境變數）。

    **6 個環境變數說明**：
      CONNSYS_JARVIS_PATH             connsys-jarvis repo 根目錄
      CONNSYS_JARVIS_WORKSPACE_ROOT_PATH   workspace 根目錄（.claude/ 所在）
      CONNSYS_JARVIS_CODE_SPACE_PATH  程式碼路徑（agent-first: workspace/codespace/；
                                        legacy: workspace root）
      CONNSYS_JARVIS_MEMORY_PATH      本地 memory 資料夾（.connsys-jarvis/memory/）
      CONNSYS_JARVIS_EMPLOYEE_ID      員工工號（從 git config user.name 取得）
      CONNSYS_JARVIS_ACTIVE_EXPERT    目前啟用的 Expert 名稱

    **前綴統一性**：所有變數均以 CONNSYS_JARVIS_ 開頭，方便在 skill/hook
    中 grep 辨識，避免與其他工具的環境變數衝突。

    Args:
        workspace:          workspace 根目錄
        active_expert_name: 目前安裝（或保留）的 identity expert 名稱
    """
    dot_dir = get_dot_dir(workspace)
    dot_dir.mkdir(parents=True, exist_ok=True)
    env_path = dot_dir / ENV_FILE

    jarvis_path    = get_jarvis_dir(workspace)
    codespace_path = get_codespace_path(workspace)
    memory_path    = dot_dir / "memory"
    # EMPLOYEE_ID 來自 git config user.name，若取不到則 fallback "unknown"
    employee_id    = run_git_config("user.name") or "unknown"

    logger.debug("write_env_file: jarvis_path=%s, codespace=%s, employee=%s, active=%s",
                 jarvis_path, codespace_path, employee_id, active_expert_name)

    # 所有變數統一 CONNSYS_JARVIS_ 前綴
    lines = [
        "# .connsys-jarvis/.env — 由 install.py 自動生成，勿手動編輯",
        f"# 生成時間：{now_iso()}",
        "",
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


# ─── .installed-experts.json Schema ──────────────────────────────────────────

def make_expert_entry(
    workspace: Path,
    expert_json_path: Path,
    expert_data: dict,
    install_order: int,
    is_identity: bool,
    declared_symlinks: dict
) -> dict:
    """建立要寫入 .installed-experts.json 的單一 expert 記錄。

    **declared_symlinks 的用途**：在 --remove 時做 reference counting。
    只有當某個 symlink 的 reference count 降為 0（沒有任何剩餘 expert 聲明它），
    才會真正刪除該 symlink，避免移除共用 symlink。

    Args:
        workspace:         workspace 根目錄
        expert_json_path:  expert.json 的絕對路徑
        expert_data:       已解析的 expert.json 內容
        install_order:     安裝順序（1, 2, 3...），用於 --list 顯示
        is_identity:       是否為目前的 identity expert（CLAUDE.md 主要 Expert）
        declared_symlinks: build_symlinks_for_expert 的回傳值（含 name/link/target）

    Returns:
        single expert entry dict，可直接放入 installed["experts"] 陣列
    """
    jarvis_dir = get_jarvis_dir(workspace)
    rel_path   = os.path.relpath(expert_json_path, jarvis_dir)
    # domain 從路徑的第一層取得（例如 "wifi-bora/experts/..." → "wifi-bora"）
    domain_parts = Path(rel_path).parts
    domain = domain_parts[0] if domain_parts else "unknown"

    entry = {
        "name":          expert_data["name"],
        "domain":        expert_data.get("domain", domain),
        "version":       expert_data.get("version", "1.0.0"),
        "path":          rel_path,
        "installed_at":  now_iso(),
        "install_order": install_order,
        "is_identity":   is_identity,
        # declared_symlinks 只儲存名稱（不需要完整路徑）
        "declared_symlinks": {
            kind: [item["name"] for item in items]
            for kind, items in declared_symlinks.items()
        }
    }
    logger.debug("make_expert_entry: %s (order=%d, identity=%s, symlinks=%s)",
                 entry["name"], install_order, is_identity,
                 {k: len(v) for k, v in entry["declared_symlinks"].items()})
    return entry


# ─── Command Implementations ──────────────────────────────────────────────────
# 每個 cmd_* 函式對應一個 CLI 參數（--init, --add, --remove, --uninstall, --list, --doctor）。
# 設計原則：
#   1. 列印步驟 header，讓使用者知道進度
#   2. 呼叫 helper 函式執行實際工作
#   3. 最後列印完成訊息

def cmd_init(workspace: Path, expert_json_rel: str) -> None:
    """--init：全新安裝，清除現有所有 link 後重建。

    **適用場景**：
      - 首次安裝（workspace 還是乾淨的）
      - 強制重建（安裝狀態混亂時，重新從頭來過）

    **執行步驟**：
      1. 清除 .claude/ 中的所有 symlinks
      2. 清空 .installed-experts.json（重置安裝狀態）
      3. 建立新的 symlinks（dependencies + internal + exclude）
      4. 更新 .installed-experts.json
      5. 生成 CLAUDE.md
      6. 寫入 .connsys-jarvis/.env

    Args:
        workspace:       workspace 根目錄
        expert_json_rel: expert.json 路徑（相對於 workspace 或 connsys-jarvis 目錄）
    """
    print(f"\n=== Connsys Jarvis Init ===")
    print(f"Workspace: {workspace}")
    print(f"Expert: {expert_json_rel}")
    logger.info("cmd_init: workspace=%s, expert=%s", workspace, expert_json_rel)

    # 解析 expert.json 絕對路徑（支援兩種相對路徑基準）
    expert_json_path = workspace / expert_json_rel
    if not expert_json_path.exists():
        # 嘗試相對於 connsys-jarvis 目錄（常見用法）
        expert_json_path = get_jarvis_dir(workspace) / expert_json_rel
    if not expert_json_path.exists():
        logger.error("cmd_init: expert.json not found: %s", expert_json_rel)
        print(f"ERROR: expert.json not found: {expert_json_rel}", file=sys.stderr)
        sys.exit(1)

    logger.debug("cmd_init: resolved expert.json=%s", expert_json_path)
    expert_data = load_expert_json(expert_json_path)

    # 步驟 1：清除舊 symlinks（避免舊 link 殘留影響新安裝）
    print("\n[1] 清除既有 symlinks...")
    logger.info("cmd_init: Step 1 - clearing existing symlinks")
    clear_claude_symlinks(workspace)

    # 步驟 2：清空安裝狀態（--init 是全新開始）
    print("[2] 清除 .installed-experts.json...")
    logger.info("cmd_init: Step 2 - resetting installed-experts.json")
    installed = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now_iso(),
        "experts": []
    }

    # 步驟 3：建立 symlinks
    print("[3] 建立 symlinks...")
    logger.info("cmd_init: Step 3 - building symlinks for %s", expert_data["name"])
    symlinks = build_symlinks_for_expert(workspace, expert_json_path, expert_data)
    results  = apply_symlinks(symlinks)

    # 列印每個 symlink 的建立狀態
    # [+] = 新建，[=] = 已存在（冪等），[!] = 錯誤
    for kind, name, status in results:
        icon = "+" if status == "created" else ("=" if status == "exists" else "!")
        print(f"  [{icon}] {kind}/{name} → {status}")

    # 步驟 4：記錄安裝狀態
    print("[4] 更新 .installed-experts.json...")
    logger.info("cmd_init: Step 4 - saving installed-experts.json")
    entry = make_expert_entry(
        workspace, expert_json_path, expert_data,
        install_order=1,     # --init 只有一個 expert，order 固定為 1
        is_identity=True,    # 唯一的 expert 就是 identity
        declared_symlinks=symlinks
    )
    installed["experts"] = [entry]
    save_installed_experts(workspace, installed)

    # 步驟 5：生成 CLAUDE.md
    print("[5] 生成 CLAUDE.md...")
    logger.info("cmd_init: Step 5 - generating CLAUDE.md")
    write_claude_md(workspace, installed)

    # 步驟 6：寫入環境變數
    print("[6] 寫入 .env...")
    logger.info("cmd_init: Step 6 - writing .env")
    write_env_file(workspace, expert_data["name"])

    logger.info("cmd_init: completed successfully for %s", expert_data["name"])
    print(f"\n完成！Expert '{expert_data['name']}' 已安裝。")


def cmd_add(workspace: Path, expert_json_rel: str) -> None:
    """--add：疊加安裝，在既有 Expert 基礎上加入新的 Expert。

    **與 --init 的差異**：
      - --init：清除一切，重新從頭安裝單一 Expert
      - --add：保留既有 Expert，在上面疊加新 Expert
        （實作上仍會清空再重建所有 symlinks，以確保一致性）

    **冪等性**：若 expert 已安裝，先移除再重新加入（支援 update）。

    **Identity 更新**：每次 --add 後，最後加入的 Expert 成為新的 identity，
    其 soul/rules/duties 會出現在 CLAUDE.md 的 Identity 區段。

    Args:
        workspace:       workspace 根目錄
        expert_json_rel: expert.json 路徑
    """
    print(f"\n=== Connsys Jarvis Add ===")
    print(f"Expert: {expert_json_rel}")
    logger.info("cmd_add: workspace=%s, expert=%s", workspace, expert_json_rel)

    expert_json_path = workspace / expert_json_rel
    if not expert_json_path.exists():
        expert_json_path = get_jarvis_dir(workspace) / expert_json_rel
    if not expert_json_path.exists():
        logger.error("cmd_add: expert.json not found: %s", expert_json_rel)
        print(f"ERROR: expert.json not found: {expert_json_rel}", file=sys.stderr)
        sys.exit(1)

    expert_data = load_expert_json(expert_json_path)
    installed   = load_installed_experts(workspace)

    # 若 expert 已存在，先移除（支援 update）
    existing_names = [e["name"] for e in installed["experts"]]
    if expert_data["name"] in existing_names:
        logger.info("cmd_add: expert %s already installed, updating", expert_data["name"])
        print(f"Expert '{expert_data['name']}' 已安裝，更新...")
        installed["experts"] = [e for e in installed["experts"]
                                 if e["name"] != expert_data["name"]]

    # 清除所有既有 expert 的 identity 標記（最後加入者才是 identity）
    for e in installed["experts"]:
        e["is_identity"] = False
    logger.debug("cmd_add: cleared identity from %d existing experts", len(installed["experts"]))

    # 建立新 expert 的 symlink 規劃
    symlinks = build_symlinks_for_expert(workspace, expert_json_path, expert_data)

    # 清空再重建：確保 symlink 集合完全同步（避免舊殘留）
    logger.info("cmd_add: clearing and rebuilding all symlinks")
    clear_claude_symlinks(workspace)

    # 先重建所有既有 expert 的 symlinks
    for e in installed["experts"]:
        ep = get_jarvis_dir(workspace) / e["path"]
        if ep.exists():
            ed = load_expert_json(ep)
            sl = build_symlinks_for_expert(workspace, ep, ed)
            apply_symlinks(sl)
            logger.debug("cmd_add: rebuilt symlinks for existing expert %s", e["name"])

    # 再建立新 expert 的 symlinks（後加入者可覆蓋同名 symlink）
    results = apply_symlinks(symlinks)
    for kind, name, status in results:
        icon = "+" if status == "created" else ("=" if status == "exists" else "!")
        print(f"  [{icon}] {kind}/{name} → {status}")

    # 計算新的 install_order
    new_order = max((e["install_order"] for e in installed["experts"]), default=0) + 1
    logger.debug("cmd_add: new expert install_order=%d", new_order)

    entry = make_expert_entry(
        workspace, expert_json_path, expert_data,
        install_order=new_order,
        is_identity=True,       # 新加入者成為 identity
        declared_symlinks=symlinks
    )
    installed["experts"].append(entry)
    save_installed_experts(workspace, installed)

    write_claude_md(workspace, installed)
    write_env_file(workspace, expert_data["name"])

    logger.info("cmd_add: completed successfully for %s", expert_data["name"])
    print(f"\n完成！Expert '{expert_data['name']}' 已加入。")


def cmd_remove(workspace: Path, expert_arg: str) -> None:
    """--remove：移除指定 Expert，並用 reference counting 決定哪些 symlink 可以刪除。

    **Reference Counting 邏輯**：
      1. 計算「剩餘 experts（移除後）」各自聲明的 symlink 集合
      2. 被移除的 expert 聲明的每個 symlink：
         - 若剩餘 experts 中仍有人聲明 → 保留（ref count > 0）
         - 若沒有任何人聲明 → 刪除（ref count = 0）
      這樣可以避免刪除共用 symlink（例如 framework-base-expert 的 hooks）。

    **參數格式**：接受兩種輸入：
      - Expert 名稱：framework-base-expert
      - expert.json 路徑：framework/experts/framework-base-expert/expert.json

    Args:
        workspace:  workspace 根目錄
        expert_arg: Expert 名稱或 expert.json 路徑
    """
    print(f"\n=== Connsys Jarvis Remove ===")
    print(f"Expert: {expert_arg}")
    logger.info("cmd_remove: workspace=%s, expert_arg=%s", workspace, expert_arg)

    # 解析 expert 名稱（接受路徑或直接名稱）
    if "/" in expert_arg or expert_arg.endswith(".json"):
        # 路徑格式，讀取 expert.json 取得 name 欄位
        expert_json_path = get_jarvis_dir(workspace) / expert_arg
        if expert_json_path.exists():
            expert_name = load_expert_json(expert_json_path).get("name", "")
            logger.debug("cmd_remove: resolved name from json: %r", expert_name)
        else:
            # 檔案不存在，從路徑推斷（例如 .../experts/{name}/expert.json）
            parts = Path(expert_arg).parts
            expert_name = parts[-2] if len(parts) >= 2 else expert_arg
            logger.debug("cmd_remove: json not found, inferred name from path: %r", expert_name)
    else:
        expert_name = expert_arg
        logger.debug("cmd_remove: using arg as name directly: %r", expert_name)

    installed = load_installed_experts(workspace)
    # 尋找目標 expert（比對 name 或 path）
    target = next(
        (e for e in installed["experts"]
         if e["name"] == expert_name or e["path"] == expert_arg),
        None
    )
    if not target:
        logger.error("cmd_remove: expert '%s' not found in installed list", expert_arg)
        print(f"ERROR: Expert '{expert_arg}' 未安裝", file=sys.stderr)
        sys.exit(1)

    target_name = target["name"]
    logger.info("cmd_remove: removing expert %s", target_name)

    # 計算移除後剩餘的 experts
    remaining = [e for e in installed["experts"] if e["name"] != target_name]
    logger.debug("cmd_remove: %d experts remain after removal", len(remaining))

    # Step 1：建立剩餘 experts 的 symlink reference count
    # key = (kind, name)，value = 聲明此 symlink 的 expert 數量
    symlink_ref_count: dict = {}
    for e in remaining:
        ep = get_jarvis_dir(workspace) / e["path"]
        if ep.exists():
            ed = load_expert_json(ep)
            sl = build_symlinks_for_expert(workspace, ep, ed)
            for kind, items in sl.items():
                for item in items:
                    key = (kind, item["name"])
                    symlink_ref_count[key] = symlink_ref_count.get(key, 0) + 1
    logger.debug("cmd_remove: reference count table has %d entries", len(symlink_ref_count))

    # Step 2：刪除只有被移除的 expert 聲明的 symlinks（ref count = 0）
    claude_dir = get_claude_dir(workspace)
    removed_count = 0
    for kind, sym_names in target.get("declared_symlinks", {}).items():
        if not isinstance(sym_names, list):
            continue
        for name in sym_names:
            key = (kind, name)
            ref = symlink_ref_count.get(key, 0)
            logger.debug("cmd_remove: %s/%s ref_count=%d", kind, name, ref)
            if ref == 0:
                # 沒有其他 expert 需要此 symlink，安全刪除
                link = claude_dir / kind / name
                remove_symlink(link)
                print(f"  [-] 移除 {kind}/{name}")
                removed_count += 1
            else:
                logger.debug("cmd_remove: keeping %s/%s (ref_count=%d)", kind, name, ref)
    logger.info("cmd_remove: removed %d symlinks", removed_count)

    # 若被移除的是 identity，將最後一個剩餘 expert 升為 identity
    if remaining and target.get("is_identity"):
        remaining[-1]["is_identity"] = True
        logger.debug("cmd_remove: promoted %s to identity", remaining[-1]["name"])

    installed["experts"] = remaining
    save_installed_experts(workspace, installed)
    write_claude_md(workspace, installed)

    new_active = remaining[-1]["name"] if remaining else "none"
    write_env_file(workspace, new_active)

    logger.info("cmd_remove: completed for %s", target_name)
    print(f"\n完成！Expert '{target_name}' 已移除。")


def cmd_uninstall(workspace: Path) -> None:
    """--uninstall：完全卸載，清除所有 symlinks 和 CLAUDE.md，但保留 memory/。

    **保留原則**：
      - 保留 .connsys-jarvis/memory/（使用者累積的記憶不應因重裝而消失）
      - 保留 .connsys-jarvis/log/（保留歷史 log 供除錯）
      - 刪除 CLAUDE.md、.claude/ symlinks、.installed-experts.json、.env

    Args:
        workspace: workspace 根目錄
    """
    print(f"\n=== Connsys Jarvis Uninstall ===")
    logger.info("cmd_uninstall: workspace=%s", workspace)

    # 步驟 1：清除所有 symlinks
    print("[1] 清除所有 symlinks...")
    clear_claude_symlinks(workspace)

    # 步驟 2：刪除 CLAUDE.md
    print("[2] 清除 CLAUDE.md...")
    claude_md = workspace / CLAUDE_MD
    if claude_md.exists():
        claude_md.unlink()
        logger.info("cmd_uninstall: deleted CLAUDE.md")
        print(f"  已刪除 {claude_md}")

    # 步驟 3：刪除安裝狀態檔和 .env（但不刪 memory/ 和 log/）
    print("[3] 清除 .installed-experts.json 和 .env...")
    installed_path = get_installed_experts_path(workspace)
    if installed_path.exists():
        installed_path.unlink()
        logger.debug("cmd_uninstall: deleted %s", installed_path)

    dot_dir  = get_dot_dir(workspace)
    env_path = dot_dir / ENV_FILE
    if env_path.exists():
        env_path.unlink()
        logger.debug("cmd_uninstall: deleted .env")

    logger.info("cmd_uninstall: completed, memory/ and log/ preserved")
    print(f"\n完成！保留 {dot_dir}/log/ 和 {dot_dir}/memory/")


def cmd_list(workspace: Path) -> None:
    """--list：列出已安裝的 Experts 和 .claude/ 中的所有 symlinks 及健康狀態。

    Args:
        workspace: workspace 根目錄
    """
    installed  = load_installed_experts(workspace)
    experts    = installed.get("experts", [])
    claude_dir = get_claude_dir(workspace)
    logger.debug("cmd_list: %d experts, claude_dir=%s", len(experts), claude_dir)

    print("\n=== 已安裝的 Experts ===\n")
    if not experts:
        print("（未安裝任何 Expert）")
    else:
        for e in experts:
            ep             = Path(e["path"]).parent
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
            # item.exists() = False 代表 target 不存在（dangling symlink）
            status = "✅" if item.exists() else "❌"
            print(f"  {status} {item.name} → {target}")
        print()


def cmd_doctor(workspace: Path) -> None:
    """--doctor：健康診斷，檢查 symlinks 是否 dangling 及環境工具是否齊全。

    **檢查項目**：
      1. Symlinks：每個 .claude/ 下的 symlink 是否指向有效目標
      2. 環境工具：Python 版本、uv、uvx 是否安裝
      3. 設定檔：.env 和 CLAUDE.md 是否存在

    **dangling symlink**：symlink 存在但目標路徑不存在，通常發生在
    connsys-jarvis repo 被移動或重新 clone 後 symlink 沒有更新。
    修復方式：重新執行 --init 或 --add。

    Args:
        workspace: workspace 根目錄
    """
    installed  = load_installed_experts(workspace)
    experts    = installed.get("experts", [])
    claude_dir = get_claude_dir(workspace)
    logger.debug("cmd_doctor: workspace=%s, %d experts", workspace, len(experts))

    print("\n=== Connsys Jarvis Doctor ===\n")

    # ── 已安裝的 Experts ──
    print("已安裝的 Experts：")
    if not experts:
        print("  （未安裝任何 Expert）")
    else:
        for e in experts:
            print(f"  [{e['install_order']}] {e['name']} ({e['domain']})")

    # ── Symlink 健康狀態 ──
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
                logger.debug("cmd_doctor: OK %s/%s", kind, item.name)
            else:
                print(f"    ❌ {item.name} → {target} DANGLING")
                logger.warning("cmd_doctor: DANGLING %s/%s → %s", kind, item.name, target)
                all_ok = False

    # ── 環境工具檢查 ──
    print("\n環境檢查：")

    # Python 版本（需 >= 3.8，PEP 723 需 >= 3.11）
    pv     = platform.python_version()
    py_ok  = tuple(int(x) for x in pv.split(".")[:2]) >= (3, 8)
    py_icon = "✅" if py_ok else "❌"
    print(f"  Python: {pv} {py_icon}")
    logger.debug("cmd_doctor: Python %s %s", pv, "OK" if py_ok else "FAIL")

    # uv（執行 PEP 723 inline script 的工具）
    uv_path = shutil.which("uv")
    if uv_path:
        print(f"  uv: 找到 ({uv_path}) ✅")
    else:
        print("  uv: 未找到 ⚠️")
        logger.warning("cmd_doctor: uv not found")

    # uvx（執行 pytest 等工具的快捷方式）
    uvx_path = shutil.which("uvx")
    if uvx_path:
        print(f"  uvx: 找到 ({uvx_path}) ✅")
    else:
        print("  uvx: 未找到 ⚠️")
        logger.warning("cmd_doctor: uvx not found")

    # .env 設定檔
    env_path  = get_dot_dir(workspace) / ENV_FILE
    env_icon  = "✅" if env_path.exists() else "❌"
    print(f"  .env: {env_path} {env_icon}")
    logger.debug("cmd_doctor: .env %s", "OK" if env_path.exists() else "MISSING")

    # CLAUDE.md
    claude_md   = workspace / CLAUDE_MD
    claude_icon = "✅" if claude_md.exists() else "❌"
    print(f"  CLAUDE.md: {claude_md} {claude_icon}")
    logger.debug("cmd_doctor: CLAUDE.md %s", "OK" if claude_md.exists() else "MISSING")

    print()
    if all_ok:
        print("總體狀態：✅ 健康")
        logger.info("cmd_doctor: overall status HEALTHY")
    else:
        print("總體狀態：❌ 有 dangling symlinks，請重新執行 --init 或 --add")
        logger.warning("cmd_doctor: overall status UNHEALTHY (dangling symlinks)")


# ─── Usage ────────────────────────────────────────────────────────────────────

def print_usage() -> None:
    """印出使用說明（--help 或不帶參數時呼叫）。"""
    print("""
Connsys Jarvis Install Script

用法（從 workspace 根目錄執行）：
  python connsys-jarvis/scripts/install.py --init   <expert.json>   初始化並安裝 Expert
  python connsys-jarvis/scripts/install.py --add    <expert.json>   新增 Expert
  python connsys-jarvis/scripts/install.py --remove <expert-name>   移除 Expert
  python connsys-jarvis/scripts/install.py --uninstall              卸載所有
  python connsys-jarvis/scripts/install.py --list                   列出已安裝
  python connsys-jarvis/scripts/install.py --doctor                 健康檢查

Debug 選項（可放在任何位置）：
  --debug   顯示 DEBUG 層級日誌（console），同時寫入 .connsys-jarvis/log/install.log

範例：
  python connsys-jarvis/scripts/install.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json
  python connsys-jarvis/scripts/install.py --add  sys-bora/experts/sys-bora-preflight-expert/expert.json
  python connsys-jarvis/scripts/install.py --remove framework-base-expert
  python connsys-jarvis/scripts/install.py --debug --doctor

注意：expert.json 路徑可以是相對於 workspace 或相對於 connsys-jarvis/ 目錄。
""")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI 進入點：解析命令列參數並分派到對應的 cmd_* 函式。

    **參數解析順序**：
      1. 先從所有 args 中擷取 --debug 旗標（可放任意位置）
      2. 剩餘 args 的第一個元素作為 command
      3. 第二個元素（若有）作為 expert.json 路徑參數

    **--debug 旗標設計**：
      允許放在 command 前或後，方便快速加入除錯模式：
        --debug --init ...     ← 放前面
        --init ... --debug     ← 放後面（不影響解析）
    """
    script_path = Path(sys.argv[0])
    # 先取得 workspace 才能設定 log file 路徑
    workspace = find_workspace(script_path)

    # ── 步驟 1：擷取 --debug 旗標 ──
    raw_args = sys.argv[1:]
    debug    = "--debug" in raw_args
    # 移除 --debug 後，剩餘的才是 command 和參數
    args     = [a for a in raw_args if a != "--debug"]

    # ── 步驟 2：設定 logging（需要 workspace 才能確定 log 檔位置）──
    log_file = get_dot_dir(workspace) / "log" / "install.log"
    setup_logging(debug=debug, log_file=log_file)
    logger.info("=== install.py started: args=%r, debug=%s ===", args, debug)

    if not args:
        print_usage()
        sys.exit(0)

    cmd = args[0]
    logger.debug("main: command=%r, remaining_args=%r", cmd, args[1:])

    # ── 步驟 3：分派到對應指令 ──
    if cmd == "--init":
        if len(args) < 2:
            logger.error("--init requires expert.json path")
            print("ERROR: --init 需要指定 expert.json 路徑", file=sys.stderr)
            sys.exit(1)
        cmd_init(workspace, args[1])

    elif cmd == "--add":
        if len(args) < 2:
            logger.error("--add requires expert.json path")
            print("ERROR: --add 需要指定 expert.json 路徑", file=sys.stderr)
            sys.exit(1)
        cmd_add(workspace, args[1])

    elif cmd == "--remove":
        if len(args) < 2:
            logger.error("--remove requires expert name or path")
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
        logger.error("unknown command: %r", cmd)
        print(f"ERROR: 未知指令 '{cmd}'", file=sys.stderr)
        print_usage()
        sys.exit(1)

    logger.info("=== install.py completed ===")


if __name__ == "__main__":
    main()
