#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
connsys-jarvis/scripts/setup.py — Connsys Jarvis 安裝管理程式
==============================================================

**用途**：管理 Connsys Expert 在 workspace 中的安裝、更新與移除。
核心工作是在 workspace 的 `.claude/` 目錄建立 symlinks，指向
connsys-jarvis repo 中 Expert 的 skills / hooks / agents / commands，
並生成 CLAUDE.md 和 .connsys-jarvis/.env 等設定檔。

**執行方式（從 workspace 根目錄）**：
    python ./connsys-jarvis/scripts/setup.py --init   <expert.json>
    python ./connsys-jarvis/scripts/setup.py --add    <expert.json>
    python ./connsys-jarvis/scripts/setup.py --add    <expert.json> --with-all-experts
    python ./connsys-jarvis/scripts/setup.py --remove <expert-name>
    python ./connsys-jarvis/scripts/setup.py --uninstall
    python ./connsys-jarvis/scripts/setup.py --list
    python ./connsys-jarvis/scripts/setup.py --list   --format json
    python ./connsys-jarvis/scripts/setup.py --query  <expert-name>
    python ./connsys-jarvis/scripts/setup.py --query  <expert-name> --format json
    python ./connsys-jarvis/scripts/setup.py --doctor
    python ./connsys-jarvis/scripts/setup.py --debug --init <expert.json>

**Expert 探索（不需要 registry.json，每次即時掃描）**：
  --list              列出所有 Expert（已安裝 + 可用）及 symlink 狀態
  --list --format json  回傳 JSON 格式清單（供 LLM / skill 使用）
  --query <name>      查詢指定 Expert 的完整 metadata
  --query <name> --format json  回傳 JSON 格式 metadata（供 LLM 使用）

**CLAUDE.md 多 Expert 模式**：
  - 預設（不加旗標）：CLAUDE.md 只包含最後安裝的 Expert 的
    soul.md / rules.md / duties.md / expert.md（單 Expert 格式）
  - --with-all-experts：在 Identity 區段後加入所有已安裝 Expert 的 expert.md
    （Capabilities 區段），讓 Claude 了解多個 Expert 的能力

**Debug 模式**：加 --debug 旗標後，console 顯示 DEBUG 層級訊息；
同時寫入 .connsys-jarvis/log/setup.log（不論是否加 --debug）。

**設計原則**：
  - Pure Python stdlib（無第三方依賴），相容 PEP 723 inline script metadata
  - workspace = cwd（使用者從 workspace root 執行），不跟隨 symlink
  - 所有安裝狀態持久化於 .connsys-jarvis/.installed-experts.json
  - 不依賴 registry.json；Expert 探索每次從磁碟即時掃描 connsys-jarvis 目錄

**相關文件**：
  - doc/agents-requirements.md  — 功能需求
  - doc/agents-design.md        — 系統設計
  - scripts/README.md           — 開發者指南
  - scripts/test/test_setup.py  — pytest 單元測試
"""

import logging
import os
import sys
import json
import re
import shutil
import platform
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
SETUP_VERSION       = "1.3"                  # setup.py 版本（用於 --doctor 顯示）

# --doctor 環境變數驗證常數
REQUIRED_ENV_VARS = [
    "CONNSYS_JARVIS_PATH",
    "CONNSYS_JARVIS_WORKSPACE_ROOT_PATH",
    "CONNSYS_JARVIS_CODE_SPACE_PATH",
    "CONNSYS_JARVIS_MEMORY_PATH",
    "CONNSYS_JARVIS_EMPLOYEE_ID",
    "CONNSYS_JARVIS_ACTIVE_EXPERT",
]
PATH_ENV_VARS = {   # 需要驗證路徑存在性的 env var
    "CONNSYS_JARVIS_PATH",
    "CONNSYS_JARVIS_WORKSPACE_ROOT_PATH",
    "CONNSYS_JARVIS_CODE_SPACE_PATH",
    "CONNSYS_JARVIS_MEMORY_PATH",
}

# ─── Logger ───────────────────────────────────────────────────────────────────
# 使用 module-level logger，方便 test_setup.py 等 caller 注入 handler。
# 預設不加任何 handler（避免 "No handlers could be found" 警告），
# 由 setup_logging() 在 main() 中統一設定。
logger = logging.getLogger("connsys_jarvis.setup")


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
        python ./connsys-jarvis/scripts/setup.py --init ...

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
            {"expert": "framework/framework-base-expert", "skills": "all", "hooks": "all"}
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


def scan_available_experts(workspace: Path) -> list:
    """即時掃描 connsys-jarvis 目錄下所有可用的 Expert。

    每次都從磁碟即時讀取 expert.json，不依賴 registry.json 或任何快取。
    掃描路徑模式：connsys-jarvis/{domain}/*-expert/expert.json
    識別方式：folder 名字以 -expert 結尾（命名規範），不依賴 expert.json 存在性

    Args:
        workspace: workspace 根目錄

    Returns:
        list of dict：每個元素包含 name, domain, path（相對於 jarvis_dir）,
        description, is_base, version
    """
    jarvis_dir = get_jarvis_dir(workspace)
    experts = []
    for expert_json in sorted(jarvis_dir.glob("*/*-expert/expert.json")):
        try:
            data = load_expert_json(expert_json)
            rel_path = str(expert_json.relative_to(jarvis_dir))
            # domain 取自 expert.json 的 domain 欄位，或從路徑第一段推斷
            domain = data.get("domain") or expert_json.parts[-3] if len(expert_json.parts) >= 3 else ""
            experts.append({
                "name":        data.get("name", expert_json.parent.name),
                "domain":      domain,
                "path":        rel_path,
                "description": data.get("description", ""),
                "is_base":     data.get("is_base", False),
                "version":     data.get("version", ""),
            })
            logger.debug("scan_available_experts: found %s", rel_path)
        except Exception as e:
            logger.warning("scan_available_experts: failed to read %s: %s", expert_json, e)
    logger.debug("scan_available_experts: total %d experts found", len(experts))
    return experts


# ─── Environment Helpers ──────────────────────────────────────────────────────

def get_login_name() -> str:
    """取得 OS 登入帳號名稱（home 目錄名字）。

    優先順序：
      1. Path.home().name  → home 目錄最後一段（e.g. "swchen.tw"）
      2. os.environ["USER"]
      3. os.environ["LOGNAME"]
      4. "unknown"

    Returns:
        OS 登入帳號字串；全部取不到時回傳 "unknown"
    """
    try:
        name = Path.home().name
        if name:
            logger.debug("get_login_name: from Path.home() → %r", name)
            return name
    except Exception as exc:
        logger.debug("get_login_name: Path.home() failed: %s", exc)
    for var in ("USER", "LOGNAME"):
        name = os.environ.get(var, "")
        if name:
            logger.debug("get_login_name: from env %s → %r", var, name)
            return name
    logger.debug("get_login_name: all methods failed, returning 'unknown'")
    return "unknown"


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
#
# **兩種生成模式**（由 installed["include_all_experts"] 控制）：
#
#   預設（include_all_experts = False）：
#     不論安裝幾個 Expert，CLAUDE.md 都只包含最後安裝（identity）Expert 的
#     soul / rules / duties / expert.md。Claude 以單一角色運作，不感知其他 Expert。
#
#   --with-all-experts（include_all_experts = True）：
#     Identity 區段：identity Expert 的 soul / rules / duties
#     Capabilities 區段：所有已安裝 Expert 的 expert.md
#     適合需要 Claude 同時了解多個 Expert 能力的場景。

def generate_claude_md(workspace: Path, installed: dict) -> str:
    """生成 CLAUDE.md 的文字內容。

    **預設格式**（不論 1 或 N 個 Expert，只呈現最後安裝的 Expert）：
        # Consys Expert: WiFi Bora Memory Slim Expert
        @connsys-jarvis/wifi-bora/.../soul.md
        @connsys-jarvis/wifi-bora/.../rules.md
        @connsys-jarvis/wifi-bora/.../duties.md
        @connsys-jarvis/wifi-bora/.../expert.md
        @CLAUDE.local.md

    **--with-all-experts 格式**（多 Expert 時才有意義）：
        # Consys Experts（N Experts 已安裝）
        ## Expert Identity（以最後安裝的 Expert 為主）
        @connsys-jarvis/.../soul.md   ← identity expert 的身份定義
        @connsys-jarvis/.../rules.md
        @connsys-jarvis/.../duties.md
        ## Expert Capabilities
        @connsys-jarvis/.../expert.md  ← 所有 Expert 的能力描述
        @connsys-jarvis/.../expert.md
        @CLAUDE.local.md

    **設計考量**：
      預設不加入其他 Expert 的 expert.md，避免 context 膨脹造成
      Claude 注意力稀釋。只有明確需要跨 Expert 能力感知時才用 --with-all-experts。

    **@CLAUDE.local.md**：workspace 本地個人化設定，不存在時 Claude Code 會忽略。

    Args:
        workspace: workspace 根目錄（用來讀取 expert.json 取得 display_name）
        installed: load_installed_experts 的回傳值；
                   installed["include_all_experts"] 決定輸出格式

    Returns:
        CLAUDE.md 的完整文字內容（string）
    """
    experts      = installed.get("experts", [])
    include_all  = installed.get("include_all_experts", False)
    logger.debug("generate_claude_md: %d experts, include_all=%s", len(experts), include_all)

    if not experts:
        return "# Connsys Jarvis\n\n（未安裝任何 Expert）\n\n@CLAUDE.local.md\n"

    # 找出 identity expert（最後一個 is_identity=True 的 expert）
    # 若無明確標記，fallback 為清單中最後一個
    identity_expert = None
    for e in experts:
        if e.get("is_identity", False):
            identity_expert = e
    if identity_expert is None:
        identity_expert = experts[-1]
    logger.debug("generate_claude_md: identity_expert=%s", identity_expert["name"])

    # identity expert 的資料夾路徑（相對於 connsys-jarvis 根目錄）
    ep = Path(identity_expert["path"]).parent

    # 嘗試讀取 display_name；expert.json 不可讀時 fallback 為 name
    try:
        id_data      = load_expert_json(get_jarvis_dir(workspace) / identity_expert["path"])
        display_name = id_data.get("display_name", identity_expert["name"])
    except Exception:
        display_name = identity_expert["name"]

    if not include_all or len(experts) == 1:
        # ── 預設格式：只有 identity expert 的四份文件 ──
        # len(experts) == 1 時強制使用此格式（--with-all-experts 在單 expert 無意義）
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
        # ── --with-all-experts 格式：Identity + 所有 Expert 的 expert.md ──
        n = len(experts)
        lines = [f"# Consys Experts（{n} Experts 已安裝）", ""]

        # Identity 區段：identity Expert 的 soul/rules/duties（角色、規範、職責）
        lines += [
            "## Expert Identity（以最後安裝的 Expert 為主）",
            f"@connsys-jarvis/{ep}/soul.md",
            f"@connsys-jarvis/{ep}/rules.md",
            f"@connsys-jarvis/{ep}/duties.md",
            "",
        ]

        # Capabilities 區段：所有已安裝 Expert 的 expert.md（能力概覽）
        # 讓 Claude 了解系統中有哪些 Expert 可以被呼叫或切換
        lines.append("## Expert Capabilities")
        for e in experts:
            ep_e = Path(e["path"]).parent
            lines.append(f"@connsys-jarvis/{ep_e}/expert.md")
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
      CONNSYS_JARVIS_EMPLOYEE_ID      員工工號（OS 登入帳號，即 home 目錄名稱）
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
    # EMPLOYEE_ID 來自 OS 登入帳號（home 目錄名稱），若取不到則 fallback "unknown"
    employee_id    = get_login_name()

    logger.debug("write_env_file: jarvis_path=%s, codespace=%s, employee=%s, active=%s",
                 jarvis_path, codespace_path, employee_id, active_expert_name)

    # 所有變數統一 CONNSYS_JARVIS_ 前綴
    lines = [
        "# .connsys-jarvis/.env — 由 setup.py 自動生成，勿手動編輯",
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
    # domain 從路徑的第一層取得（例如 "wifi-bora/..." → "wifi-bora"）
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


def cmd_add(workspace: Path, expert_json_rel: str, include_all: bool = False) -> None:
    """--add：疊加安裝，在既有 Expert 基礎上加入新的 Expert。

    **與 --init 的差異**：
      - --init：清除一切，重新從頭安裝單一 Expert
      - --add：保留既有 Expert，在上面疊加新 Expert
        （實作上仍會清空再重建所有 symlinks，以確保一致性）

    **冪等性**：若 expert 已安裝，先移除再重新加入（支援 update）。

    **Identity 更新**：每次 --add 後，最後加入的 Expert 成為新的 identity，
    其 soul/rules/duties 會出現在 CLAUDE.md 的 Identity 區段。

    **CLAUDE.md 生成模式**（由 include_all 決定）：
      - include_all=False（預設）：CLAUDE.md 只包含 identity Expert 的四份文件
      - include_all=True（--with-all-experts）：加入所有 Expert 的 expert.md

    Args:
        workspace:       workspace 根目錄
        expert_json_rel: expert.json 路徑（相對於 workspace 或 connsys-jarvis 目錄）
        include_all:     True = 啟用 --with-all-experts 模式，CLAUDE.md 包含所有 expert.md
    """
    print(f"\n=== Connsys Jarvis Add ===")
    print(f"Expert: {expert_json_rel}")
    if include_all:
        print("模式: --with-all-experts（CLAUDE.md 將包含所有 Expert 的 expert.md）")
    logger.info("cmd_add: workspace=%s, expert=%s, include_all=%s",
                workspace, expert_json_rel, include_all)

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
    # 儲存 include_all_experts 旗標，讓後續 write_claude_md 使用相同模式
    # 這也讓 --remove 後重建 CLAUDE.md 時維持一致的格式
    installed["include_all_experts"] = include_all
    save_installed_experts(workspace, installed)

    write_claude_md(workspace, installed)
    write_env_file(workspace, expert_data["name"])

    logger.info("cmd_add: completed successfully for %s (include_all=%s)",
                expert_data["name"], include_all)
    print(f"\n完成！Expert '{expert_data['name']}' 已加入。")


def cmd_remove(workspace: Path, expert_arg: str) -> None:
    """--remove：移除指定 Expert，清除所有 symlinks 後依剩餘 Expert 重建。

    **全清再重建策略**（與 --add 一致）：
      1. 清除 .claude/ 下所有既有 symlinks
      2. 依剩餘 Expert（按 install_order）逐一重建 symlinks
      這確保 symlink 集合始終與已安裝 Expert 清單完全同步，
      邏輯比 reference counting 更簡單可靠。

    **參數格式**：接受兩種輸入：
      - Expert 名稱：framework-base-expert
      - expert.json 路徑：framework/framework-base-expert/expert.json

    Args:
        workspace:  workspace 根目錄
        expert_arg: Expert 名稱或 expert.json 路徑
    """
    print(f"\n=== Connsys Jarvis Remove ===")
    print(f"Expert: {expert_arg}")
    logger.info("cmd_remove: workspace=%s, expert_arg=%s", workspace, expert_arg)

    # 解析 expert 名稱（接受路徑或直接名稱）
    if "/" in expert_arg or expert_arg.endswith(".json"):
        expert_json_path = get_jarvis_dir(workspace) / expert_arg
        if expert_json_path.exists():
            expert_name = load_expert_json(expert_json_path).get("name", "")
            logger.debug("cmd_remove: resolved name from json: %r", expert_name)
        else:
            parts = Path(expert_arg).parts
            expert_name = parts[-2] if len(parts) >= 2 else expert_arg
            logger.debug("cmd_remove: json not found, inferred name from path: %r", expert_name)
    else:
        expert_name = expert_arg
        logger.debug("cmd_remove: using arg as name directly: %r", expert_name)

    installed = load_installed_experts(workspace)
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

    remaining = [e for e in installed["experts"] if e["name"] != target_name]
    logger.debug("cmd_remove: %d experts remain after removal", len(remaining))

    # 全清再重建：清除所有既有 symlinks，依剩餘 expert 重新建立
    logger.info("cmd_remove: clearing all symlinks and rebuilding from %d remaining experts",
                len(remaining))
    clear_claude_symlinks(workspace)
    print(f"  [-] 已清除所有 symlinks")

    for e in remaining:
        ep = get_jarvis_dir(workspace) / e["path"]
        if ep.exists():
            ed = load_expert_json(ep)
            sl = build_symlinks_for_expert(workspace, ep, ed)
            results = apply_symlinks(sl)
            logger.debug("cmd_remove: rebuilt symlinks for %s", e["name"])
            for kind, name, status in results:
                icon = "+" if status == "created" else ("=" if status == "exists" else "!")
                print(f"  [{icon}] {kind}/{name} → {status}")

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


def cmd_list(workspace: Path, output_format: str = "table") -> None:
    """--list：列出所有 Expert（已安裝 + 可用），支援 table 和 json 格式。

    每次都即時掃描 connsys-jarvis 目錄，不依賴 registry.json。
    output_format="json" 時輸出機器可讀的 JSON，供
    framework-expert-discovery skill 或 LLM 使用。

    Args:
        workspace:     workspace 根目錄
        output_format: "table"（預設，人類可讀）或 "json"（LLM 可讀）
    """
    installed     = load_installed_experts(workspace)
    installed_map = {e["name"]: e for e in installed.get("experts", [])}
    available     = scan_available_experts(workspace)
    claude_dir    = get_claude_dir(workspace)
    logger.debug("cmd_list: %d installed, %d available (format=%s)",
                 len(installed_map), len(available), output_format)

    # 合併：標注每個 expert 的 status
    result = []
    for exp in available:
        name = exp["name"]
        inst = installed_map.get(name)
        result.append({
            "name":          name,
            "domain":        exp["domain"],
            "path":          exp["path"],
            "description":   exp["description"],
            "version":       exp["version"],
            "is_base":       exp["is_base"],
            "status":        "installed" if inst else "available",
            "is_identity":   inst.get("is_identity", False) if inst else False,
            "install_order": inst.get("install_order") if inst else None,
        })

    if output_format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # ── Table 格式 ──
    print("\n=== Connsys Jarvis — Expert 清單 ===\n")
    for r in result:
        status_icon   = "✅" if r["status"] == "installed" else "○ "
        order_mark    = f" [{r['install_order']}]" if r["install_order"] is not None else ""
        identity_mark = " ← identity" if r["is_identity"] else ""
        print(f"{status_icon} {r['name']} ({r['domain']}){order_mark}{identity_mark}")
        if r["description"]:
            print(f"      {r['description']}")

    installed_count = sum(1 for r in result if r["status"] == "installed")
    print(f"\n已安裝：{installed_count}  可用：{len(result)}")

    # ── Symlink 清單 ──
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
            status_icon = "✅" if item.exists() else "❌"
            print(f"  {status_icon} {item.name} → {target}")
        print()


def cmd_query(workspace: Path, expert_name: str, output_format: str = "table") -> None:
    """--query：查詢指定 Expert 的完整 metadata。

    每次都即時掃描並讀取 expert.json，不依賴 registry.json。
    output_format="json" 時輸出機器可讀的 JSON，供 skill 或 LLM 使用。

    Args:
        workspace:     workspace 根目錄
        expert_name:   Expert 名稱（完整名稱或部分匹配）
        output_format: "table" 或 "json"
    """
    available     = scan_available_experts(workspace)
    installed     = load_installed_experts(workspace)
    installed_map = {e["name"]: e for e in installed.get("experts", [])}
    logger.debug("cmd_query: looking for %r in %d available experts", expert_name, len(available))

    # 精確匹配
    target = next((e for e in available if e["name"] == expert_name), None)
    if not target:
        # 部分匹配（case-insensitive）
        matches = [e for e in available if expert_name.lower() in e["name"].lower()]
        if len(matches) == 1:
            target = matches[0]
        elif len(matches) > 1:
            names = [m["name"] for m in matches]
            logger.warning("cmd_query: ambiguous name %r, matches: %s", expert_name, names)
            print(f"多個匹配，請指定完整名稱：{names}", file=sys.stderr)
            sys.exit(1)
        else:
            logger.error("cmd_query: expert '%s' not found", expert_name)
            print(f"ERROR: Expert '{expert_name}' 不存在", file=sys.stderr)
            sys.exit(1)

    # 讀取完整 expert.json
    jarvis_dir       = get_jarvis_dir(workspace)
    expert_json_path = jarvis_dir / target["path"]
    full_data        = load_expert_json(expert_json_path)

    inst = installed_map.get(target["name"])
    result = {
        "name":          target["name"],
        "domain":        target["domain"],
        "path":          target["path"],
        "description":   target.get("description", ""),
        "version":       target.get("version", ""),
        "is_base":       target.get("is_base", False),
        "status":        "installed" if inst else "available",
        "is_identity":   inst.get("is_identity", False) if inst else False,
        "install_order": inst.get("install_order") if inst else None,
        "dependencies":  full_data.get("dependencies", []),
        "internal":      full_data.get("internal", {}),
    }
    logger.debug("cmd_query: result for %s: status=%s", target["name"], result["status"])

    if output_format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # ── Table 格式 ──
    if result["is_identity"]:
        inst_mark = " ← identity"
    elif result["status"] == "installed":
        inst_mark = f" [已安裝 #{result['install_order']}]"
    else:
        inst_mark = ""
    print(f"\n=== Expert: {result['name']} ===")
    print(f"Domain      : {result['domain']}")
    print(f"Status      : {result['status']}{inst_mark}")
    print(f"Version     : {result['version']}")
    print(f"Description : {result['description']}")
    print(f"Path        : {result['path']}")
    deps = result["dependencies"]
    if deps:
        print("Dependencies:")
        for dep in deps:
            dep_name = dep.get("expert", str(dep)) if isinstance(dep, dict) else str(dep)
            print(f"  - {dep_name}")
    internal = result["internal"]
    if internal:
        print("Internal    :")
        for k, v in internal.items():
            print(f"  {k}: {v}")


def parse_env_file(env_path: Path) -> dict:
    """解析 .connsys-jarvis/.env，回傳 {key: value} dict。

    處理兩種格式：
      export CONNSYS_JARVIS_PATH="/path"   ← setup.py 產生的格式
      CONNSYS_JARVIS_PATH=/path            ← 無 export 的純 key=value 格式

    Returns:
        dict，key 為變數名稱，value 為去除引號後的字串；
        若檔案無法讀取則回傳空 dict。
    """
    result = {}
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:].strip()
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            result[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return result


def collect_skill_references(jarvis_dir: Path) -> tuple:
    """收集 connsys-jarvis repo 中所有 expert.json 對 skill 的引用。

    用於 --doctor 的 F4 orphan skill 檢查。

    Returns:
        (named_skills, all_skills_experts)
        named_skills:      set of str — 所有被明確點名的 skill 名稱
        all_skills_experts: set of str — 被某 dep 以 "skills":"all" 引用的 expert 相對路徑
                            (相對於 jarvis_dir，例如 "framework/framework-base-expert")
    """
    named_skills: set = set()
    all_skills_experts: set = set()

    for expert_json in sorted(jarvis_dir.glob("*/*-expert/expert.json")):
        try:
            data = json.loads(expert_json.read_text())
        except Exception:
            continue

        # internal skills
        internal = data.get("internal", {})
        for s in internal.get("skills", []):
            if isinstance(s, str):
                named_skills.add(s)

        # dependency skills
        for dep in data.get("dependencies", []):
            dep_path    = dep.get("expert", "")
            skills_spec = dep.get("skills", None)
            if skills_spec is None:
                continue
            if skills_spec == "all" or (isinstance(skills_spec, list) and "all" in skills_spec):
                all_skills_experts.add(dep_path)
            elif isinstance(skills_spec, list):
                for s in skills_spec:
                    if isinstance(s, str):
                        named_skills.add(s)

    return named_skills, all_skills_experts


def cmd_doctor(workspace: Path) -> None:
    """--doctor：健康診斷（僅顯示問題與修正建議，不自動修復）。

    **6 個診斷區段**：
      A. 系統資訊     — OS、Python 版本、connsys-jarvis 版本
      B. 環境變數     — 6 個 CONNSYS_JARVIS_* 變數存在性與路徑合法性
      C. Symlink 完整性 — expected（依已安裝 Expert 宣告）vs actual（.claude/ 現況）
                          missing / orphan / dangling；已建 skill link 的 SKILL.md
      D. CLAUDE.md    — @include 行與已安裝 Expert 的預期內容比對 + target 存在性
      E. 環境工具     — uv、uvx 是否安裝
      F. Expert 結構  — 掃描 connsys-jarvis repo 中所有 expert folder：
                        必要檔案、expert.json 必要欄位、skill SKILL.md、orphan skill

    Args:
        workspace: workspace 根目錄
    """
    installed  = load_installed_experts(workspace)
    experts    = installed.get("experts", [])
    claude_dir = get_claude_dir(workspace)
    env_path   = get_dot_dir(workspace) / ENV_FILE
    claude_md  = workspace / CLAUDE_MD
    jarvis_dir = get_jarvis_dir(workspace)
    logger.debug("cmd_doctor: workspace=%s, %d experts", workspace, len(experts))

    all_ok = True
    print("\n=== Connsys Jarvis Doctor ===\n")

    # ── A. 系統資訊 ──
    print("A. 系統資訊：")
    os_info = f"{platform.system()} {platform.release()}"
    print(f"  OS:             {os_info}")
    py_ver = platform.python_version()
    py_ok  = tuple(int(x) for x in py_ver.split(".")[:2]) >= (3, 8)
    py_icon = "✅" if py_ok else "❌"
    print(f"  Python:         {py_ver} {py_icon}")
    if not py_ok:
        print("     → 需要 Python 3.8+")
        all_ok = False
    print(f"  connsys-jarvis: v{SETUP_VERSION}")
    logger.debug("cmd_doctor: OS=%s, Python=%s", os_info, py_ver)

    # ── 已安裝的 Experts ──
    print("\n已安裝的 Experts：")
    if not experts:
        print("  （未安裝任何 Expert）")
    else:
        for e in experts:
            print(f"  [{e['install_order']}] {e['name']} ({e['domain']})")

    # ── B. 環境變數（CONNSYS_JARVIS_*）──
    print("\nB. 環境變數（CONNSYS_JARVIS_*）：")
    if not env_path.exists():
        print(f"  ❌ .env 不存在：{env_path}")
        print(f"     → 修正：重新執行 --init <expert.json>")
        all_ok = False
        logger.debug("cmd_doctor: .env missing at %s", env_path)
    else:
        env_vars = parse_env_file(env_path)
        for var in REQUIRED_ENV_VARS:
            val = env_vars.get(var)
            if val is None:
                print(f"  ❌ {var}：未定義")
                print(f"     → 修正：重新執行 --init <expert.json>")
                all_ok = False
                logger.debug("cmd_doctor: missing env var %s", var)
            elif var in PATH_ENV_VARS and not Path(val).exists():
                print(f"  ❌ {var} = {val}（路徑不存在）")
                print(f"     → 修正：確認路徑存在，或重新執行 --init <expert.json>")
                all_ok = False
                logger.debug("cmd_doctor: env path not found %s=%s", var, val)
            else:
                print(f"  ✅ {var} = {val}")
                logger.debug("cmd_doctor: env OK %s", var)

    # ── C. Symlink 完整性（expected vs actual，僅 Linux/macOS）──
    print("\nC. Symlink 完整性：")
    if platform.system() == "Windows":
        print("  ⚠️  Windows 環境：symlink 完整性檢查略過")
    else:
        # expected：從 declared_symlinks 聚合所有已安裝 Expert 宣告的 symlink
        expected_by_kind: dict = {}
        for e in experts:
            for kind, names in e.get("declared_symlinks", {}).items():
                expected_by_kind.setdefault(kind, set()).update(names)

        for kind in ["skills", "agents", "commands", "hooks"]:
            kind_dir = claude_dir / kind
            expected = expected_by_kind.get(kind, set())

            actual: dict = {}
            if kind_dir.exists():
                for item in sorted(kind_dir.iterdir()):
                    if item.is_symlink():
                        actual[item.name] = item

            if not expected and not actual:
                continue

            print(f"  {kind.capitalize()}（預期 {len(expected)}，實際 {len(actual)}）：")

            for name in sorted(expected):
                if name not in actual:
                    print(f"    ❌ [缺少] {name}")
                    print(f"       → 修正：python setup.py --init <expert.json>")
                    all_ok = False
                    logger.debug("cmd_doctor: missing symlink %s/%s", kind, name)
                else:
                    item   = actual[name]
                    target = Path(os.readlink(item))
                    if item.exists():
                        print(f"    ✅ {name} → {target}")
                        logger.debug("cmd_doctor: OK %s/%s", kind, name)
                    else:
                        print(f"    ❌ {name} → {target} DANGLING")
                        print(f"       → 修正：重新執行 --init 或 --add")
                        all_ok = False
                        logger.debug("cmd_doctor: DANGLING %s/%s → %s", kind, name, target)

            for name in sorted(actual):
                if name not in expected:
                    item         = actual[name]
                    target       = Path(os.readlink(item))
                    dangling_note = "（DANGLING）" if not item.exists() else ""
                    print(f"    ⚠️  [多餘] {name} → {target}{dangling_note}")
                    print(f"       → 修正：python setup.py --remove <expert-name> 全清再重建")
                    all_ok = False
                    logger.debug("cmd_doctor: orphan symlink %s/%s", kind, name)

        # 已建 skill links 的 SKILL.md 驗證
        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            skill_links = sorted(
                item for item in skills_dir.iterdir() if item.is_symlink() and item.exists()
            )
            if skill_links:
                print(f"  Skills SKILL.md：")
                for item in skill_links:
                    skill_md = item / "SKILL.md"
                    if skill_md.exists():
                        print(f"    ✅ {item.name}/SKILL.md")
                        logger.debug("cmd_doctor: SKILL.md OK %s", item.name)
                    else:
                        print(f"    ⚠️  {item.name}/SKILL.md 不存在")
                        print(f"       → 修正：在 skill folder 補充 SKILL.md")
                        all_ok = False
                        logger.debug("cmd_doctor: SKILL.md missing for skill link %s", item.name)

    # ── D. CLAUDE.md 內容驗證 ──
    print("\nD. CLAUDE.md 驗證：")
    if not claude_md.exists():
        print(f"  ❌ CLAUDE.md 不存在：{claude_md}")
        print(f"     → 修正：重新執行 --init <expert.json>")
        all_ok = False
        logger.debug("cmd_doctor: CLAUDE.md missing")
    else:
        actual_includes: set = set()
        for line in claude_md.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith('@') and stripped != '@CLAUDE.local.md':
                actual_includes.add(stripped)

        expected_content  = generate_claude_md(workspace, installed)
        expected_includes: set = set()
        for line in expected_content.splitlines():
            stripped = line.strip()
            if stripped.startswith('@') and stripped != '@CLAUDE.local.md':
                expected_includes.add(stripped)

        mode = "with-all-experts" if installed.get("include_all_experts") else "identity-only"

        if actual_includes == expected_includes:
            print(f"  ✅ 內容符合預期（{mode}，{len(expected_includes)} 個 @include）")
            logger.debug("cmd_doctor: CLAUDE.md OK, %d includes", len(expected_includes))
        else:
            missing_inc = expected_includes - actual_includes
            extra_inc   = actual_includes   - expected_includes
            for inc in sorted(missing_inc):
                print(f"  ❌ [缺少 @include] {inc}")
                all_ok = False
                logger.debug("cmd_doctor: CLAUDE.md missing include: %s", inc)
            for inc in sorted(extra_inc):
                print(f"  ⚠️  [多餘 @include] {inc}")
                all_ok = False
                logger.debug("cmd_doctor: CLAUDE.md extra include: %s", inc)
            if missing_inc or extra_inc:
                print(f"     → 修正：重新執行 --init 或 --add <expert.json>")

        # 驗證 CLAUDE.md 中每個 @include 目標檔案存在
        # 只檢查實際存在於 CLAUDE.md 的 @-行（actual_includes），排除 @CLAUDE.local.md
        if actual_includes:
            print(f"  @include 目標存在性（{len(actual_includes)} 個）：")
            for inc in sorted(actual_includes):
                rel    = inc.lstrip('@')
                target = workspace / rel
                if target.exists():
                    print(f"    ✅ {rel}")
                    logger.debug("cmd_doctor: @include target OK: %s", rel)
                else:
                    print(f"    ❌ {rel}（檔案不存在）")
                    print(f"       → 修正：確認 connsys-jarvis repo 路徑正確，或重新執行 --init")
                    all_ok = False
                    logger.debug("cmd_doctor: @include target missing: %s", rel)

    # ── E. 環境工具 ──
    print("\nE. 環境工具：")
    uv_path = shutil.which("uv")
    if uv_path:
        print(f"  uv:  找到 ({uv_path}) ✅")
    else:
        print("  uv:  未找到 ⚠️")
        logger.warning("cmd_doctor: uv not found")

    uvx_path = shutil.which("uvx")
    if uvx_path:
        print(f"  uvx: 找到 ({uvx_path}) ✅")
    else:
        print("  uvx: 未找到 ⚠️")
        logger.warning("cmd_doctor: uvx not found")

    # ── F. Expert 結構完整性（掃描 connsys-jarvis repo）──
    print("\nF. Expert 結構完整性（掃描 connsys-jarvis repo）：")

    expert_dirs = sorted(d for d in jarvis_dir.glob("*/*-expert") if d.is_dir())

    if not expert_dirs:
        print("  （未找到任何 expert folder）")
    else:
        # F1: 必要檔案
        REQUIRED_EXPERT_FILES = ["expert.json", "expert.md", "rules.md", "duties.md", "soul.md"]
        print(f"  F1 必要檔案（{', '.join(REQUIRED_EXPERT_FILES)}）：")
        for exp_dir in expert_dirs:
            rel = str(exp_dir.relative_to(jarvis_dir))
            missing_files = [f for f in REQUIRED_EXPERT_FILES if not (exp_dir / f).exists()]
            if missing_files:
                print(f"    ❌ {rel} 缺少：{', '.join(missing_files)}")
                print(f"       → 修正：補充上列缺少的檔案")
                all_ok = False
                logger.debug("cmd_doctor: expert missing files %s: %s", rel, missing_files)
            else:
                print(f"    ✅ {rel}")

        # F2: expert.json 必要欄位
        REQUIRED_JSON_FIELDS = ["name", "domain", "owner"]
        print(f"\n  F2 expert.json 欄位（{', '.join(REQUIRED_JSON_FIELDS)}, internal.skills）：")
        for exp_dir in expert_dirs:
            rel          = str(exp_dir.relative_to(jarvis_dir))
            expert_json  = exp_dir / "expert.json"
            if not expert_json.exists():
                continue    # 已由 F1 報告
            try:
                data = json.loads(expert_json.read_text())
            except Exception as e:
                print(f"    ❌ {rel}/expert.json 無法解析：{e}")
                all_ok = False
                continue

            missing_fields = [f for f in REQUIRED_JSON_FIELDS if not data.get(f)]
            # internal.skills 必須是 list（可為空）
            internal      = data.get("internal")
            has_int_skills = (
                isinstance(internal, dict) and "skills" in internal
                and isinstance(internal["skills"], list)
            )
            if missing_fields or not has_int_skills:
                issues_desc = []
                if missing_fields:
                    issues_desc.append(f"缺少欄位：{', '.join(missing_fields)}")
                if not has_int_skills:
                    issues_desc.append("internal.skills 不存在或格式錯誤")
                print(f"    ❌ {rel}/expert.json — {'; '.join(issues_desc)}")
                print(f"       → 修正：補充上列缺少的欄位")
                all_ok = False
                logger.debug("cmd_doctor: expert.json issues %s: %s", rel, issues_desc)
            else:
                print(f"    ✅ {rel}/expert.json")

        # F3: skill SKILL.md 完整性
        print(f"\n  F3 Skill SKILL.md：")
        skill_dirs_all = sorted(d for d in jarvis_dir.glob("*/*-expert/skills/*") if d.is_dir())
        if not skill_dirs_all:
            print("    （未找到任何 skill folder）")
        else:
            f3_ok = True
            for skill_dir in skill_dirs_all:
                rel = str(skill_dir.relative_to(jarvis_dir))
                if not (skill_dir / "SKILL.md").exists():
                    print(f"    ⚠️  {rel} 缺少 SKILL.md")
                    print(f"       → 修正：在此 skill folder 補充 SKILL.md")
                    all_ok = False
                    f3_ok  = False
                    logger.debug("cmd_doctor: skill missing SKILL.md: %s", rel)
            if f3_ok:
                print(f"    ✅ 所有 {len(skill_dirs_all)} 個 skill folder 均有 SKILL.md")

        # F4: orphan skill（skill folder 未被任何 expert.json 引用）
        print(f"\n  F4 Orphan Skill（未被任何 expert.json 引用）：")
        named_skills, all_skills_experts = collect_skill_references(jarvis_dir)
        f4_ok = True
        for skill_dir in skill_dirs_all:
            skill_name = skill_dir.name
            # parent expert 相對於 jarvis_dir：domain/expert-name
            parts = skill_dir.relative_to(jarvis_dir).parts
            parent_expert_rel = str(Path(*parts[:2]))   # e.g. "wifi-bora/wifi-bora-base-expert"
            if skill_name not in named_skills and parent_expert_rel not in all_skills_experts:
                rel = str(skill_dir.relative_to(jarvis_dir))
                print(f"    ⚠️  {rel}（未被任何 expert.json 引用）")
                print(f"       → 修正：加入某個 expert.json 的 internal.skills，或刪除此資料夾")
                all_ok = False
                f4_ok  = False
                logger.debug("cmd_doctor: orphan skill: %s", rel)
        if f4_ok and skill_dirs_all:
            print(f"    ✅ 所有 skill 均有被引用")

    # ── 總體狀態 ──
    print()
    if all_ok:
        print("總體狀態：✅ 健康")
        logger.info("cmd_doctor: overall status HEALTHY")
    else:
        print("總體狀態：❌ 有問題需修正（詳見上方各項 ❌ / ⚠️ 說明）")
        logger.debug("cmd_doctor: overall status UNHEALTHY")


# ─── Usage ────────────────────────────────────────────────────────────────────

def print_usage() -> None:
    """印出使用說明（--help 或不帶參數時呼叫）。"""
    print("""
Connsys Jarvis Setup Script

用法（從 workspace 根目錄執行）：
  python connsys-jarvis/scripts/setup.py --init   <expert.json>   初始化並安裝 Expert
  python connsys-jarvis/scripts/setup.py --add    <expert.json>   新增 Expert（重複執行 = 重新安裝）
  python connsys-jarvis/scripts/setup.py --remove <expert-name>   移除 Expert
  python connsys-jarvis/scripts/setup.py --uninstall              卸載所有
  python connsys-jarvis/scripts/setup.py --list                   列出所有 Expert（已安裝 + 可用）
  python connsys-jarvis/scripts/setup.py --list --format json     以 JSON 格式輸出（供 LLM 使用）
  python connsys-jarvis/scripts/setup.py --query <expert-name>    查詢指定 Expert 的 metadata
  python connsys-jarvis/scripts/setup.py --query <expert-name> --format json
  python connsys-jarvis/scripts/setup.py --doctor                 健康檢查

CLAUDE.md 模式選項（搭配 --add 使用）：
  --with-all-experts  在 CLAUDE.md 中加入所有已安裝 Expert 的 expert.md
                      （預設只包含最後安裝的 Expert 的四份文件）

輸出格式選項：
  --format table      人類可讀格式（預設）
  --format json       JSON 格式（供 framework-expert-discovery skill / LLM 使用）

Debug 選項（可放在任何位置）：
  --debug   顯示 DEBUG 層級日誌（console），同時寫入 .connsys-jarvis/log/setup.log

範例：
  python connsys-jarvis/scripts/setup.py --init wifi-bora/wifi-bora-memory-slim-expert/expert.json
  python connsys-jarvis/scripts/setup.py --add  sys-bora/sys-bora-preflight-expert/expert.json
  python connsys-jarvis/scripts/setup.py --add  sys-bora/sys-bora-preflight-expert/expert.json --with-all-experts
  python connsys-jarvis/scripts/setup.py --remove framework-base-expert
  python connsys-jarvis/scripts/setup.py --list --format json
  python connsys-jarvis/scripts/setup.py --query wifi-bora-memory-slim-expert
  python connsys-jarvis/scripts/setup.py --debug --doctor

注意：
  - expert.json 路徑可以是相對於 workspace 或相對於 connsys-jarvis/ 目錄
  - 不依賴 registry.json；Expert 清單每次即時掃描 connsys-jarvis 目錄取得
  - --add 若 Expert 已安裝，則執行重新安裝（先移除再重建 symlinks）
""")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI 進入點：解析命令列參數並分派到對應的 cmd_* 函式。

    **參數解析順序**：
      1. 先從所有 args 中擷取 --debug 旗標（可放任意位置）
      2. 剩餘 args 的第一個元素作為 command
      3. 第二個元素（若有）作為 expert.json 路徑參數

    **全域旗標設計**：
      所有旗標允許放在任何位置，方便靈活組合：
        --debug --init ...                ← debug 放前面
        --add expert.json --with-all-experts --debug  ← 旗標放後面
    """
    script_path = Path(sys.argv[0])
    # 先取得 workspace 才能設定 log file 路徑
    workspace = find_workspace(script_path)

    # ── 步驟 1：擷取全域旗標（可放任意位置）──
    raw_args     = sys.argv[1:]
    debug        = "--debug" in raw_args
    include_all  = "--with-all-experts" in raw_args
    # --format json / --format table（預設 table）
    fmt_idx      = next((i for i, a in enumerate(raw_args) if a == "--format"), None)
    output_format = raw_args[fmt_idx + 1] if fmt_idx is not None and fmt_idx + 1 < len(raw_args) else "table"
    if output_format not in ("json", "table"):
        output_format = "table"
    # 移除旗標後，剩餘的才是 command 和其參數
    GLOBAL_FLAGS = {"--debug", "--with-all-experts", "--format",
                    "json", "table"}          # 移除 --format 及其值
    # 更精確地移除 --format 及緊接的值
    args_clean: list = []
    skip_next = False
    for a in raw_args:
        if skip_next:
            skip_next = False
            continue
        if a == "--format":
            skip_next = True
            continue
        if a in {"--debug", "--with-all-experts"}:
            continue
        args_clean.append(a)
    args = args_clean

    # ── 步驟 2：設定 logging（需要 workspace 才能確定 log 檔位置）──
    log_file = get_dot_dir(workspace) / "log" / "setup.log"
    setup_logging(debug=debug, log_file=log_file)
    logger.info("=== setup.py started: args=%r, debug=%s ===", args, debug)

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
        cmd_add(workspace, args[1], include_all=include_all)

    elif cmd == "--remove":
        if len(args) < 2:
            logger.error("--remove requires expert name or path")
            print("ERROR: --remove 需要指定 expert name", file=sys.stderr)
            sys.exit(1)
        cmd_remove(workspace, args[1])

    elif cmd == "--uninstall":
        cmd_uninstall(workspace)

    elif cmd == "--list":
        cmd_list(workspace, output_format=output_format)

    elif cmd == "--query":
        if len(args) < 2:
            logger.error("--query requires expert name")
            print("ERROR: --query 需要指定 Expert 名稱", file=sys.stderr)
            sys.exit(1)
        cmd_query(workspace, args[1], output_format=output_format)

    elif cmd == "--doctor":
        cmd_doctor(workspace)

    elif cmd in ("-h", "--help"):
        print_usage()

    else:
        logger.error("unknown command: %r", cmd)
        print(f"ERROR: 未知指令 '{cmd}'", file=sys.stderr)
        print_usage()
        sys.exit(1)

    logger.info("=== setup.py completed ===")


if __name__ == "__main__":
    main()
