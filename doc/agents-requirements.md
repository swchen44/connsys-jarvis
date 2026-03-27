# Consys Experts — 需求書

**文件版本**：v3.3
**狀態**：Draft
**目標讀者**：架構師、開發者、產品負責人
**改版說明**：
- v2.0：以使用者故事為主軸重寫，記錄設計決策的「為什麼」
- v2.1：明確 Expert 定義、引入 Harness Engineering 概念、repo 更名為 `connsys-jarvis`、補充環境變數定義
- v2.2：expert.json 加入 owner、環境變數統一 CONNSYS_JARVIS_ 前綴、Agent First 流程補充 clone 步驟、skill 名稱更新
- v2.3：新增 Future Work（Security / Memory+Learn）、參考資料
- v2.4：加入三階段演進願景、Expert 交接流程需求、本地三區記憶設計需求
- v2.5：Expert 和 Skill 資料夾統一加入 `test/`、`report/`、`README.md`；`unittest/` 更名為 `test/`
- v2.6：Hook 實作語言改為 Shell 優先，複雜邏輯用 Python，JS 為最後考慮
- v2.7：專案更名 consys → connsys（雙 n），更新所有 repo/env var 名稱
- v2.8：Skill/Hook scripts Shell 優先、Python 採 PEP 723 inline metadata、pytest test_xxx.py
- v2.9：多 Expert 安裝/卸載需求、 setup.py --doctor、Python 版本檢查、Skill 與 Command 邊界釐清、限制補充（Skill 版本相容性、memory GC）、Future Work 補充（registry.json、Skill README 範本）
- v3.0：架構重大重設計——install.sh 改為單一 setup.py（stdlib only）、expert 資料夾移除 CLAUDE.md 和 install.sh、新增 soul.md / rules.md / duties.md / agents/ 資料夾、記憶改用 .connsys-jarvis/memory/、環境變數輸出至 .connsys-jarvis/.env、新增 symlink 靈活性設計原則（因應 agent 生態快速演進）
- v3.1：expert.json dependencies 改為陣列格式（支援 all/正面表列/省略=不繼承）、exclude_symlink 改為全域 regex patterns（3-step 執行順序）、更新 domain 清單（wifi-bora/sys-bora/bt-bora/lrwpan-bora/wifi-gen4m/wifi-logan）、common 改為 base、加入新 expert 清單
- v3.2：setup.py 路徑改為 `scripts/setup.py`；新增 FR-02-17（pytest 單元測試 `scripts/test/test_setup.py`）；更新目錄結構加入 `scripts/` 子節
- v3.3：移除 registry.json；setup.py 改為即時掃描 Expert 目錄；新增 --query 指令、--format json 輸出格式；--remove 改為全清再重建策略（與 --add 一致）；--add 重複安裝 = 重新安裝

> **注意**：文件中所列的 expert、skill 名稱均為**示例**，用於說明命名規則與架構設計。實際規劃以團隊討論為準。

---

## 1. 背景與目標

### 1.1 啟發：Harness Engineering

> 參考來源：[Exploring Gen AI — Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)
> 作者：Birgitta Böckeler（Thoughtworks 傑出工程師），發表於 Martin Fowler 部落格

**Harness Engineering** 是一個新興工程概念：不再只是對 AI 下指令（Prompting），而是建立一套**環繞在 AI 模型周圍的系統、工具與實踐**，用以約束、引導並強化 AI Agent 的能力。

文章提出三大關鍵組件：

| 組件 | 定義 | 對應本系統的設計 |
|------|------|-----------------|
| **上下文工程**（Context Engineering） | 持續維護知識庫，讓 Agent 能存取動態資料 | SKILL.md 技能庫、expert.md、expert.local.md |
| **架構約束**（Architectural Constraints） | 加入確定性工具（Linter、測試），強制執行規範 | Hooks（pre-compact、write-guard）、hand-off 格式規範 |
| **垃圾回收**（Garbage Collection） | 定期執行 Agent 清理過時文件，對抗系統熵增 | session-end 自動整理記憶，push 至 connsys-memory |

**文章關鍵結論**：隨著 AI Agent 的進化，軟體開發的嚴謹性（Rigor）正從「代碼細節」遷移到「系統架構與環境設計」。工程師的工作重點將從「打字寫代碼」轉向**「設計環境、反饋循環與控制系統」**。

本系統正是基於 Harness Engineering 的精神，為 Consys 韌體開發團隊打造的 AI Expert Harness。

---

### 1.2 設計原則：Symlink 為核心的最大彈性

**背景**：外部 Agent 框架（Claude Code、OpenClaw、ADK、gitagent 等）變化極快，無法等待生態穩定才開始設計。

**採用 Symlink 安裝模式的理由**：

| 優點 | 說明 |
|------|------|
| **即換即生效** | 更改 Expert 內容，下次 Claude 啟動即生效，不需重裝 |
| **多版本共存** | 不同 Expert 可共用同一個 common skill，切換只需重新 link |
| **零侵入性** | Workspace 的 `.claude/` 只有 symlink，不污染 expert repo |
| **跨平台** | Linux/macOS 用 symlink；Windows 自動降級為 copy |
| **框架遷移** | 換成 OpenClaw 或其他框架時，setup.py 只需改寫 target 路徑 |

> 參考：[open-gitagent/gitagent](https://github.com/open-gitagent/gitagent)（Expert folder 設計參考）

---

### 1.3 Consys Expert 的定義

**Consys Expert = Agent 能力 + Consys Workflow + Consys Tool + Consys Knowledge**

```
┌─────────────────────────────────────────────────────────────┐
│                      Consys Expert                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Agent 核心能力（平台提供）               │   │
│  │         Think → Plan → Act → Learn（循環）           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↑ 加上                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Workflow   │  │     Tool     │  │    Knowledge     │  │
│  │（工作流程）   │  │  （工具）    │  │    （知識）       │  │
│  │              │  │              │  │                  │  │
│  │ common/      │  │ common/      │  │ common/          │  │
│  │ experts/{n}/ │  │ experts/{n}/ │  │ experts/{n}/     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

每個 Expert 可以：
- 使用 **common** Workflow / Tool / Knowledge（所有 Expert 共用）
- 擁有自己的**私有** Workflow / Tool / Knowledge
- 透過 setup.py 中的 link 或 copy 將上述內容接入 Claude Code（或未來的其他 Agent 平台）

**開發範圍不限於韌體**，包含但不限於：
- Firmware（韌體）
- Driver（驅動程式）
- User Space 應用程式
- 自動化工具（如 FW Parser、Python 工具、CI/CD 腳本）

---

### 1.3 問題陳述

韌體開發團隊的日常工作涉及多個 repo 的下載、編譯、修復、上傳與裝置控制。目前工作流程完全依賴人工判斷，導致以下痛點：

- 每位同仁對工具鏈的熟悉程度不同，重複踩坑
- AI 輔助工具（Claude Code）的使用方式因人而異，效益不一致
- Agent 與 Agent 之間的上下文無法有效傳遞（Context 爆炸問題）
- 無法收集使用資料，難以知道哪些流程需要改善

### 1.4 目標

建立一套以 **Claude Code** 為執行環境、可跨平台遷移的 **Consys Expert Harness**，達成：

1. 同仁可快速安裝對應領域的「專家」(Expert)，取得即用的 Skills（Knowledge）、Hooks（Workflow）與 Commands（Tool）
2. Expert 之間透過結構化 Hand-off 傳遞上下文，避免 Context 爆炸
3. 使用資料自動收集至後臺 Git repo，供反思與大數據分析
4. **未來目標**：Agent 可自行 install、自行運作；簡單任務由 Agent 自動完成，有風險時觸發 **Human in the Loop** 機制，請人類介入確認
5. 架構不綁定特定 AI 平台，未來可平滑遷移至 OpenClaw 或 ADK/SDK

---

### 1.5 三階段演進願景

本系統的設計以「逐步交還控制權給 Agent」為核心願景，共分三個階段演進：

```
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 1：Expert 需要人類輔助（Human-Assisted）                      │
│                                                                     │
│  Agent 協助人類完成任務，高風險操作需人類確認（Human in the Loop）。   │
│  Expert 之間的切換由人工執行（--switch）。                            │
│  這是本系統的 Phase 1 目標（現在）。                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Stage 2：部分 Expert 可獨立完成任務（Semi-Autonomous）               │
│                                                                     │
│  對於風險較低、流程明確的任務（如 build → CI），Expert 可自動執行       │
│  完整流程，包含自動切換到下一個 Expert（根據 transitions 設定）。       │
│  仍對高風險操作觸發 Human in the Loop。                              │
│  需要成熟的記憶系統支撐（Local Memory + connsys-memory）。             │
├─────────────────────────────────────────────────────────────────────┤
│  Stage 3：Expert 之間可互相溝通（Multi-Agent Collaboration）          │
│                                                                     │
│  多個 Expert 可平行運作，透過結構化 Hand-off 與共享記憶互相協調。       │
│  例如 build-expert 發現問題後，主動通知 debug-expert 接手。            │
│  Expert 可透過 framework-memory-tool 讀寫共用記憶區。                │
│  這是本系統的長期目標，對應 ADK/SDK 的 Multi-Agent 架構。             │
└─────────────────────────────────────────────────────────────────────┘
```

**為什麼要定義三個階段**：
- 讓團隊對「現在做什麼」與「未來走向哪裡」有共識
- 記憶設計（本地三區）和交接流程設計，從 Stage 1 開始就要為 Stage 2/3 預留空間
- 每個階段的技術投資都有意義：記憶收集的資料，未來可用於 Stage 3 的 Expert 協調

---

### 1.6 設計決策的理由

| 設計決策 | 理由 |
|---------|------|
| Expert = Agent + Workflow + Tool + Knowledge | 讓 Claude Code 成為真正懂 Consys 流程的專家，而非通用 AI |
| 獨立的 `connsys-jarvis` repo | Expert 工具與 source code 分開管理，兩者生命週期不同；同仁可在任何 workspace 安裝 |
| 以 symlink 為預設安裝方式 | 切換 Expert 時直接重建 link 即可，無需處理檔案複製的一致性問題 |
| CLAUDE.md 採覆蓋（替換）策略 | 切換 Expert 等於「換一個專家來做事」——新專家帶來全新的技能組合 |
| setup.py 不觸碰 settings.json | 平台設定由 `setup-claude.sh` 處理，降低 setup.py 與平台的耦合 |
| 記憶系統用 Markdown + Git | 不需外部資料庫，完全透明可編輯，天然支援跨裝置同步與版本稽核 |
| 工號（git username）作為後臺資料夾名稱 | 無需額外帳號系統，git 帳號即工號，setup.py 可自動取得 |
| `external/` 資料夾 | 避免重造輪子，整合社群優秀工具（如 skill-creator），以工具名稱為資料夾名 |
| Human in the Loop 設計 | 對於有風險的操作（刪除、push、裝置控制），Agent 應先警告並等待人類確認，避免不可逆的錯誤 |

---

## 2. 使用者故事

### US-01：Agent First 場景（從空白 workspace 開始）

**背景**：同仁拿到一台新機器，workspace 是空的，想用 Expert 輔助下載並編譯韌體。

**流程**：
```
0. 初始狀態：~/workspace/ 為空目錄
1. 在 ~/workspace/ 執行：git clone {connsys-jarvis-url}
   → 出現 ~/workspace/connsys-jarvis/
2. 瀏覽 connsys-jarvis/ 資料夾，找到所需 Expert（如 wifi-bora/experts/wifi-bora-memory-slim-expert/）
3. 執行：uv run ./connsys-jarvis/scripts/setup.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json && source .connsys-jarvis/.env
   → 建立 .claude/ symlinks、生成 CLAUDE.md、設定環境變數
4. 開啟 Claude Code → 已具備 wifi-bora-memory-slim-expert 的 Skills/Hooks/Commands
5. 與 Claude 互動，Claude 協助用 repo tool 下載 fw 到 codespace/fw/
6. 需要切換到 wifi-bora-cr-robot-expert 時：
   uv run ./connsys-jarvis/scripts/setup.py --init wifi-bora/experts/wifi-bora-cr-robot-expert/expert.json && source .connsys-jarvis/.env
   確認變更清單後，重新開啟 Claude Code
```

**驗收條件**：
- setup.py 執行後，`.claude/skills/`、`.claude/hooks/`、`.claude/commands/` 均正確建立 symlink
- `CLAUDE.md` 被生成，內容以 `@connsys-jarvis/{domain}/experts/{expert}/` 路徑 @include `expert.md`、`soul.md`、`rules.md`、`duties.md`，末尾附加 `@CLAUDE.local.md`
- 環境變數正確設定（見 FR-03）
- `connsys-memory/` repo 被自動 clone，員工資料夾以 git username 命名

---

### US-02：Legacy 場景（已手動下載 code）

**背景**：同仁已用 `repo` 工具按照傳統流程下載好 fw，現在想引入 Expert 輔助。

**流程**：
```
1. 同仁已有：
   ~/workspace/.repo
   ~/workspace/bora/wifi, bt, mcu, build, coexistence (各為獨立 git repo)
2. 在 ~/workspace/ clone connsys-jarvis
3. 執行 uv run ./connsys-jarvis/scripts/setup.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json && source .connsys-jarvis/.env
4. setup.py 自動偵測到 .repo 存在，判斷為 legacy 場景
5. 建立 .claude/ symlinks，生成 CLAUDE.md
6. 開啟 Claude Code，既有 code 與新安裝的 Expert 技能整合運作
```

**驗收條件**：
- setup.py 能自動偵測場景（legacy vs agent-first）
- Legacy 場景的 `CONNSYS_JARVIS_CODE_SPACE_PATH` 指向 workspace 根目錄
- 不影響已存在的 bora/ 資料夾與 .repo

---

### US-03：切換 Expert（換專家）

**背景**：同仁完成記憶體分析後，想換 cr-robot-expert 來協助 Code Review。

**流程**：
```
1. 執行 uv run ./connsys-jarvis/scripts/setup.py --init wifi-bora/experts/wifi-bora-cr-robot-expert/expert.json && source .connsys-jarvis/.env
2. 系統先觸發 hand-off，儲存當前 session 狀態
3. 移除舊 Expert 的所有 symlinks（common + internal 全部替換）
4. 建立新 Expert 的 symlinks
5. 重新生成 CLAUDE.md 與 expert.md
6. 印出變更清單：
   ✓ 新增: wifi-bora-debug-sop-flow, wifi-bora-risk-report-flow, wifi-bora-coredump-knowhow
   ✗ 移除: wifi-bora-memslim-flow, wifi-bora-lsp-tool, wifi-bora-wut-tool
   ○ 保留: framework-expert-discovery-knowhow, framework-handoff-flow（framework-base）
   ○ 保留: wifi-bora-arch-knowhow, sys-bora-preflight-flow（domain base / preflight）
7. 同仁確認後，開啟 Claude Code 進入新 Expert 環境
```

**為什麼 base skills 也要替換**：切換 Expert 等於「換一個專家」，新專家帶來整套技能組合。即使 base skills 內容相同，link 也應重建以確保一致性，並讓使用者看到完整的切換清單。

---

### US-06：多 Expert 並存場景（--add 追加）

**背景**：同仁已安裝 wifi-bora-base-expert，在同一個 workspace 想額外追加 wifi-bora-coverity-expert 來處理 Coverity 掃描任務，不想重裝整個環境。

**流程**：
```
1. 目前狀態：
   .claude/ 已有 wifi-bora-base-expert 的 symlinks
   CLAUDE.md 已包含 wifi-bora-base-expert 的 @include 內容
2. 執行 --add 追加：
   uv run ./connsys-jarvis/scripts/setup.py --add wifi-bora/experts/wifi-bora-coverity-expert/expert.json && source .connsys-jarvis/.env
3. setup.py 讀取 wifi-bora-coverity-expert 的 dependencies + internal：
   - 補建 wifi-bora-coverity-expert 自己的 internal skills 的 symlink
     (wifi-bora-coverity-flow, wifi-bora-coverity-cr-tool, wifi-bora-risk-report-flow)
   - 跳過已存在的 symlinks（wifi-bora-base-expert 已建好的不重複建立）
4. 重新生成 CLAUDE.md（預設 identity-only 格式，以最後安裝的 Expert 為主）：
   @connsys-jarvis/wifi-bora/experts/wifi-bora-coverity-expert/soul.md
   @connsys-jarvis/wifi-bora/experts/wifi-bora-coverity-expert/rules.md
   @connsys-jarvis/wifi-bora/experts/wifi-bora-coverity-expert/duties.md
   @connsys-jarvis/wifi-bora/experts/wifi-bora-coverity-expert/expert.md
   @CLAUDE.local.md
   （若加 --with-all-experts 參數，則同時加入所有 Expert 的 expert.md）
5. 印出變更清單：
   ✓ 新增: wifi-bora-coverity-flow, wifi-bora-coverity-cr-tool, wifi-bora-risk-report-flow
   ○ 已存在 (跳過): wifi-bora-protocol-knowhow, wifi-bora-build-flow, ... (base 的 skills)
6. 重新開啟 Claude Code，同時具備兩個 Expert 的能力
```

**驗收條件**：
- `--add` 不移除現有 symlinks，只補建新 expert 的 internal skills
- 已存在的 symlink 跳過（idempotent，不報錯）
- CLAUDE.md 預設只包含最後安裝 Expert（identity）的 soul/rules/duties/expert.md
- 加上 `--with-all-experts` 時，CLAUDE.md 以 Identity/Capabilities 雙區段呈現所有已安裝 Expert 的 expert.md
- `.connsys-jarvis/.installed-experts.json`（安裝狀態記錄）更新，新增 wifi-bora-coverity-expert 條目；`include_all_experts` 欄位記錄本次是否使用 `--with-all-experts`

---

### US-07：移除單一 Expert（--remove + --add 重建）

**背景**：同仁目前同時安裝了 wifi-bora-base-expert 和 wifi-bora-coverity-expert，想移除 coverity-expert，但保留 base-expert。由於 CLAUDE.md 是由 setup.py 根據已安裝 Expert 清單動態生成，移除後必須觸發重建。

**流程**：
```
1. 目前狀態：
   .claude/ 同時有兩個 Expert 的 symlinks
   CLAUDE.md 包含兩個 Expert 的 @include
2. 執行 --remove 移除：
   uv run ./connsys-jarvis/scripts/setup.py --remove wifi-bora/experts/wifi-bora-coverity-expert/expert.json
3. setup.py 執行移除邏輯：
   - 找出 wifi-bora-coverity-expert 的 internal skills（coverity-flow, coverity-cr-tool, risk-report-flow）
   - 若這些 skill 的 symlink 沒有被其他已安裝 Expert 引用 → 刪除
   - 若有共用（如 wifi-bora-risk-report-flow 被另一 expert 也引用）→ 保留
   - 更新 .connsys-jarvis/.installed-experts.json，移除 coverity-expert 條目
4. 因 CLAUDE.md 無法部分刪減（它是整體生成的），需要重建：
   setup.py 自動根據 .installed-experts.json 的剩餘清單重新執行 --add 邏輯
   → 等同於 --add wifi-bora-base-expert（只保留 base）
5. 重新生成 CLAUDE.md，只剩 wifi-bora-base-expert 的 @include
6. 印出變更清單：
   ✗ 移除: wifi-bora-coverity-flow, wifi-bora-coverity-cr-tool
   ○ 保留（其他 expert 仍使用）: wifi-bora-risk-report-flow（若有共用）
   ○ 保留: wifi-bora-base-expert 的所有 skills（不受影響）
```

**驗收條件**：
- `--remove` 只刪除「無其他 expert 依賴」的 symlinks，共用 skills 保留
- CLAUDE.md 自動重建，移除後只包含剩餘 Expert 的 @include
- `.connsys-jarvis/.installed-experts.json` 正確更新
- 若移除後 .installed-experts.json 為空，CLAUDE.md 退回最小化內容（僅 framework hooks）

**為什麼需要 --remove + 重建而非單純刪 symlink**：CLAUDE.md 是整體生成的文件，無法只刪除部分 @include 行；需透過 setup.py 根據剩餘 .installed-experts.json 完整重新生成，才能確保 CLAUDE.md 與實際 symlinks 保持一致。

---

### US-04：Agent 自動運作（未來目標）

**背景**：Agent 自行判斷任務，自動完成簡單操作，遇到風險時觸發 Human in the Loop。

**流程**：
```
1. Agent 收到任務：「幫我 build fw 並上傳到 CI」
2. Agent 自動執行：clone code → build → 分析結果
3. 遇到需要 push 到 remote 的步驟：
   ⚠️  警告：即將執行 git push origin main，此操作不可逆
   請確認後繼續 [y/N]：
4. 同仁確認 → Agent 繼續執行
5. Agent 自行 install 下一個需要的 Expert（未來）
```

---

### US-05：後臺資料收集與分析

**背景**：主管想了解同仁使用哪些 Expert 最多、哪些 Hand-off 流程最常卡關。

**流程**：
```
1. session-end hook 在每次對話結束時自動觸發
2. 將 session 摘要寫入 connsys-memory/employees/{username}/sessions/YYYY-MM-DD.md
3. 自動 git push 到 connsys-memory 的 remote
4. 管理者可 clone connsys-memory，查看所有同仁的使用資料
5. 分析：哪些 Expert 最常用、哪些步驟最常需要人工介入
```

**為什麼用 Git**：不需要額外基礎設施，資料天然有版本歷史，可在本地端離線使用。

---

## 3. 系統邊界與目錄結構

### 3.1 `connsys-jarvis` Repo 結構

採用**五層資料夾設計**（Layer 1–5），詳細結構見設計書 §2–3。以下為簡化概覽：

```
connsys-jarvis/ (git)
├── README.md
├── scripts/                         ← 安裝程式與測試
│   ├── setup.py                   ← 唯一安裝程式（設定環境變數、管理 symlink）
│   └── test/
│       └── test_setup.py          ← pytest 單元測試（uv run / uvx pytest）
│
├── framework/                       ← Layer 1：framework domain
│   ├── experts/
│   │   ├── framework-base-expert/ ← 跨所有 domain 共用（is_common: true）
│   │   │   ├── skills/              ← framework-expert-discovery-knowhow, framework-handoff-flow, framework-memory-tool
│   │   │   ├── hooks/               ← session-start.sh, session-end.sh, pre-compact.sh（Shell 優先）
│   │   │   │   └── memory-helper.py ← 複雜記憶操作（Python helper）
│   │   │   └── commands/            ← framework-experts-tool/, framework-handoff-tool/
│   │   ├── framework-skill-create-expert/
│   │   └── framework-learn-expert/
│   └── external-experts/            ← skill-creator/, claude-memory-engine/（git submodule）
│
├── wifi/                            ← Layer 1：wifi domain【示例】
│   ├── experts/
│   │   ├── wifi-bora-base-expert/      ← wifi domain 共用（is_common: true）
│   │   ├── wifi-bora-memory-slim-expert/
│   │   ├── wifi-debug-expert/
│   │   └── wifi-bora-cr-robot-expert/
│   └── external-experts/
│
├── bt/                              ← Layer 1：bt domain【示例】
│   ├── experts/
│   │   ├── bt-bora-base-expert/
│   │   ├── bt-build-expert/
│   │   └── bt-debug-expert/
│   └── external-experts/
│
└── system/                          ← Layer 1：system domain（含跨 domain 共用工具）【示例】
    ├── experts/
    │   ├── sys-bora-base-expert/    ← sys-bora-gerrit-tool, sys-bora-repo-tool 等
    │   ├── system-cicd-expert/
    │   └── system-device-expert/
    └── external-experts/
```

**每個 Expert 資料夾標準結構**（Layer 4）：
```
{domain}-{name}-expert/
├── README.md      ← History、使用說明、人工安裝說明、Design、目的
├── setup.py     ← 唯一安裝程式（Python stdlib）
├── expert.json    ← Expert 設定（dependencies、transitions、human_in_the_loop）
├── CLAUDE.md      ← system prompt 模板
├── skills/        ← 每個 skill 含 SKILL.md / README.md / test/ / report/
├── hooks/         ← 額外 hook（可選，Shell 優先）
├── commands/      ← 額外 command（可選）
├── test/          ← Expert 層級測試腳本
└── report/        ← 執行過程、結果、token 用量
```

---

### 3.2 Agent First 場景：workspace 演進

**Step 0 — 初始狀態（空 workspace）**
```
workspace/
└── （空）
```

**Step 1 — clone connsys-jarvis**
```
workspace/
└── connsys-jarvis/ (git)
```

**Step 2 — `uv run ./connsys-jarvis/scripts/setup.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json`**
```
workspace/                                       ← $CONNSYS_JARVIS_WORKSPACE_ROOT_PATH
├── connsys-jarvis/ (git)
│
├── connsys-memory/ (git)                         ← setup.py 自動 clone
│   └── employees/
│       └── john.doe/                            ← git config user.name
│           ├── sessions/
│           ├── handoffs/
│           └── summary.md
│
├── CLAUDE.md                                    ← setup.py 生成（非 symlink）
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/expert.md
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/soul.md
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/rules.md
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/duties.md
│   # @CLAUDE.local.md
│
├── .connsys-jarvis/                             ← setup.py 建立（.gitignore 排除）
│   ├── .env                                     ← 環境變數（source .connsys-jarvis/.env）
│   ├── .installed-experts.json                       ← 已安裝 Expert 清單
│   ├── log/
│   └── memory/                                  ← 本地三區記憶
│       ├── shared/                              ← Zone 1：跨 Expert 共用知識
│       ├── working/wifi-bora-memory-slim-expert/ ← Zone 2：飛行中狀態
│       └── handoffs/                            ← Zone 3：交接文件（唯讀）
│
└── .claude/
    ├── skills/                                  ← Knowledge symlinks
    │   ├── framework-expert-discovery-knowhow → $CONNSYS_JARVIS_PATH/framework/experts/framework-base-expert/skills/framework-expert-discovery-knowhow/
    │   ├── framework-handoff-flow             → .../framework-base-expert/skills/framework-handoff-flow/
    │   ├── wifi-bora-arch-knowhow             → $CONNSYS_JARVIS_PATH/wifi-bora/experts/wifi-bora-base-expert/skills/wifi-bora-arch-knowhow/
    │   ├── sys-bora-gerrit-commit-flow        → $CONNSYS_JARVIS_PATH/sys-bora/experts/sys-bora-preflight-expert/skills/sys-bora-gerrit-commit-flow/
    │   └── wifi-bora-memslim-flow             → $CONNSYS_JARVIS_PATH/wifi-bora/experts/wifi-bora-memory-slim-expert/skills/wifi-bora-memslim-flow/
    ├── hooks/                                   ← Workflow symlinks（來自 framework-base-expert）
    │   ├── session-start.sh          → $CONNSYS_JARVIS_PATH/framework/experts/framework-base-expert/hooks/session-start.sh
    │   ├── session-end.sh            → .../framework-base-expert/hooks/session-end.sh
    │   ├── pre-compact.sh            → .../framework-base-expert/hooks/pre-compact.sh
    │   ├── mid-session-checkpoint.sh → .../framework-base-expert/hooks/mid-session-checkpoint.sh
    │   └── shared-utils.sh           → .../framework-base-expert/hooks/shared-utils.sh
    └── commands/                                ← Tool symlinks
        ├── framework-experts-tool  → .../framework-base-expert/commands/framework-experts-tool/
        └── framework-handoff-tool  → .../framework-base-expert/commands/framework-handoff-tool/
```

**Step 3 — 開啟 Claude Code，Expert 協助下載 fw**
```
workspace/                                       ← $CONNSYS_JARVIS_WORKSPACE_ROOT_PATH
├── connsys-jarvis/ (git)
├── connsys-memory/ (git)
├── CLAUDE.md
├── .claude/
└── codespace/                                   ← $CONNSYS_JARVIS_CODE_SPACE_PATH
    └── fw/
        ├── .repo (git)
        └── bora/
            ├── bt/ (git)
            ├── build/ (git)
            ├── wifi/ (git)
            └── mcu/ (git)
```

**Step 4 — 下載多套 fw + driver SDK**
```
workspace/
├── connsys-jarvis/ (git)
├── connsys-memory/ (git)
├── CLAUDE.md
├── .claude/
└── codespace/                                   ← $CONNSYS_JARVIS_CODE_SPACE_PATH
    ├── fw/                                      ← 第一套 firmware
    │   ├── .repo (git)
    │   └── bora/
    │       ├── bt/ (git)
    │       ├── build/ (git)
    │       ├── wifi/ (git)
    │       └── mcu/ (git)
    ├── fw2/                                     ← 第二套 firmware
    │   ├── .repo (git)
    │   └── bora/
    │       ├── bt/ (git)
    │       ├── build/ (git)
    │       ├── mcu/ (git)
    │       └── wifi/ (git)
    ├── drv/                                     ← gen4m driver SDK（可能上百個 repo）
    │   ├── .repo (git)
    │   └── gen4m/
    │       ├── wlan_gen4m/ (git)
    │       └── wlan_private/ (git)
    └── drv2/                                    ← logan driver SDK
        ├── .repo (git)
        └── logan/
            ├── wlan_logan/ (git)
            └── wlan_hwifi/ (git)
```

---

### 3.3 Legacy 場景：workspace 演進

**Step 0 — 初始狀態（傳統 repo tool 流程）**
```
workspace/
├── .repo (git)
└── bora/
    ├── wifi/ (git)
    ├── bt/ (git)
    ├── mcu/ (git)
    ├── build/ (git)
    └── coexistence/ (git)
```

**Step 1 — clone connsys-jarvis**
```
workspace/
├── .repo (git)
├── bora/ (同上)
└── connsys-jarvis/ (git)
```

**Step 2 — `uv run ./connsys-jarvis/scripts/setup.py --init wifi-bora/experts/wifi-bora-memory-slim-expert/expert.json`**
（setup.py 偵測到根目錄有 `.repo`，自動判斷 legacy 場景）
```
workspace/                                       ← $CONNSYS_JARVIS_WORKSPACE_ROOT_PATH
│                                                   $CONNSYS_JARVIS_CODE_SPACE_PATH（同一路徑）
├── .repo (git)
├── bora/
│   ├── wifi/ (git)
│   ├── bt/ (git)
│   ├── mcu/ (git)
│   ├── build/ (git)
│   └── coexistence/ (git)
├── connsys-jarvis/ (git)
├── connsys-memory/ (git)
├── CLAUDE.md                                    ← setup.py 生成（非 symlink）
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/expert.md
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/soul.md
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/rules.md
│   # @connsys-jarvis/wifi-bora/experts/wifi-bora-memory-slim-expert/duties.md
│   # @CLAUDE.local.md
│
├── .connsys-jarvis/                             ← setup.py 建立（.gitignore 排除）
│   ├── .env                                     ← 環境變數（source .connsys-jarvis/.env）
│   ├── .installed-experts.json                       ← 已安裝 Expert 清單
│   ├── log/
│   └── memory/                                  ← 本地三區記憶
│       ├── shared/                              ← Zone 1：跨 Expert 共用知識
│       ├── working/wifi-bora-memory-slim-expert/ ← Zone 2：飛行中狀態
│       └── handoffs/                            ← Zone 3：交接文件（唯讀）
│
└── .claude/
    ├── skills/
    │   ├── framework-expert-discovery-knowhow → $CONNSYS_JARVIS_PATH/framework/experts/framework-base-expert/skills/framework-expert-discovery-knowhow/
    │   ├── framework-handoff-flow             → .../framework-base-expert/skills/framework-handoff-flow/
    │   ├── wifi-bora-arch-knowhow             → $CONNSYS_JARVIS_PATH/wifi-bora/experts/wifi-bora-base-expert/skills/wifi-bora-arch-knowhow/
    │   ├── sys-bora-gerrit-commit-flow        → $CONNSYS_JARVIS_PATH/sys-bora/experts/sys-bora-preflight-expert/skills/sys-bora-gerrit-commit-flow/
    │   └── wifi-bora-memslim-flow             → $CONNSYS_JARVIS_PATH/wifi-bora/experts/wifi-bora-memory-slim-expert/skills/wifi-bora-memslim-flow/
    ├── hooks/
    │   ├── session-start.sh          → $CONNSYS_JARVIS_PATH/framework/experts/framework-base-expert/hooks/session-start.sh
    │   ├── session-end.sh            → .../framework-base-expert/hooks/session-end.sh
    │   ├── pre-compact.sh            → .../framework-base-expert/hooks/pre-compact.sh
    │   ├── mid-session-checkpoint.sh → .../framework-base-expert/hooks/mid-session-checkpoint.sh
    │   └── shared-utils.sh           → .../framework-base-expert/hooks/shared-utils.sh
    └── commands/
        ├── framework-experts-tool  → .../framework-base-expert/commands/framework-experts-tool/
        └── framework-handoff-tool  → .../framework-base-expert/commands/framework-handoff-tool/
```

**兩個場景的主要差異**：

| | Agent First | Legacy |
|---|---|---|
| Workspace root | `~/workspace/` | `~/workspace/` |
| Code space | `~/workspace/codespace/` | `~/workspace/`（同 workspace root）|
| `CONNSYS_JARVIS_CODE_SPACE_PATH` | `~/workspace/codespace` | `~/workspace` |
| code 由誰下載 | Claude Expert 互動後用 repo tool 下載 | 同仁已手動下載 |
| 場景自動偵測 | 根目錄無 `.repo` | 根目錄有 `.repo` |

---

## 4. 功能需求

### FR-01：Expert Repo 結構

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-01-1 | repo 命名為 `connsys-jarvis`，Expert 資料夾命名為 `experts/` | Must | 避免與 AI 的「agent」概念混淆，名稱更 general |
| FR-01-2 | 每個 Expert 資料夾含 `expert.json`、`expert.md`、`soul.md`、`rules.md`、`duties.md`、`skills/`、`hooks/`、`agents/`、`commands/`（相容層）、`test/`、`report/`、`README.md`；**不含 `install.sh` 和 `CLAUDE.md`**（由頂層 `setup.py` 統一管理） | Must | 標準化結構，Expert 資料夾只含內容；安裝管理集中在根目錄；新增 agents/ 支援 subagent 功能 |
| FR-01-3 | `expert.json` 含名稱、描述、觸發詞、skills、transitions、dependencies | Must | 資訊越完整，expert-discovery 越有用 |
| FR-01-4 | `framework-base-expert` 存放跨所有 domain 共用的 skills / hooks / commands；各 domain 的 `{domain}-base-expert` 存放該 domain 共用內容 | Must | 三層依賴（framework → domain → internal）對應 Expert 定義的三個組件 |
| FR-01-5 | `external/` 存放社群工具，以工具名稱為資料夾名（git submodule） | Should | 整合優質社群工具，避免重造輪子 |
| FR-01-7 | Expert 資料夾新增 `agents/` 子資料夾，存放 Claude subagent 的 prompt 定義文件（`{agent-name}.md`） | Should | 支援 subagent 功能，可讓主 Expert 呼叫子任務 Agent（如 log 分析、文件查找）；參考 gitagent 設計 |
| FR-01-8 | 開發 SOP：先在各 domain expert 的 internal skills/hooks 中獨立實作；若發現多個 expert 共用，再移至該 domain 的 base expert；初期無法判斷歸屬時，可先當 internal，之後再移入 base | Should | 避免過早抽象化；base expert 是有機成長的 |

#### Expert 清單（初始規劃）

| Expert | Domain | 依賴 | 任務描述 |
|--------|--------|------|---------|
| `framework-base-expert` | framework | — | 管理 connsys expert 生態系；提供 Expert/Skill 建立輔助（`framework-expert-create-flow`、`framework-skill-create-flow`）、手交接、記憶管理 |
| `sys-bora-base-expert` | sys-bora | — | SoC/OS/build system 基礎知識；manifest 下載與 build.py 流程；cpu/os API、ld、firmware config 基礎 |
| `sys-bora-preflight-expert` | sys-bora（跨 domain 共用）| sys-bora-base | gerrit commit/preflight 操作；CI/CD label 定義；preflight 結果分析與自動修復；tmux/agent-browser 操作 |
| `wifi-bora-base-expert` | wifi-bora | — | wifi-bora fw 下載/編譯/build pass-fail；Wi-Fi 標準基礎；ROM patch/linkerscript；memory symbol；fw 架構與 SDS；自動上傳程式碼 |
| `wifi-bora-memory-slim-expert` | wifi-bora | wifi-bora-base, sys-bora-preflight | 縮減 memory 用量；AST/LSP/assembly/ELF 分析；自動變異比較；WUT (googletest)；gerrit 上傳 |
| `wifi-bora-cr-robot-expert` | wifi-bora | wifi-bora-base, sys-bora-preflight | 問題特徵分析；debug SOP；Log/dump/symbol 分析；source compile；自動驗證修復；WUT；gerrit 上傳；risk/bug report |
| `wifi-bora-coverity-expert` | wifi-bora | wifi-bora-base, sys-bora-preflight | coverity 問題解決；CR 資料庫整合；local coverity 執行；WUT；gerrit 上傳；risk/bug report |
| `bt-bora-base-expert` | bt-bora | — | bt-bora fw 下載/編譯/build pass-fail；BT 標準基礎；fw 架構與 SDS；自動上傳程式碼 |
| `bt-bora-security-expert` | bt-bora | bt-bora-base, sys-bora-preflight | security rule 檢查；AST/LSP/assembly/ELF 分析；security insight 報告；gerrit 上傳 |
| `lrwpan-bora-base-expert` | lrwpan-bora | — | lrwpan fw 下載/編譯；LR-WPAN (802.15.4) 標準基礎；fw 架構與 SDS；自動上傳 |
| `wifi-gen4m-base-expert` | wifi-gen4m | — | wifi gen4m driver 下載/編譯；Wi-Fi 標準基礎；driver 架構與 SDS；自動上傳 |
| `wifi-logan-base-expert` | wifi-logan | — | wifi logan driver 下載/編譯；Wi-Fi 標準基礎；driver 架構與 SDS；自動上傳 |

### FR-02：scripts/setup.py（取代 install.sh）

**核心原則**：單一 `connsys-jarvis/scripts/setup.py` 負責所有安裝管理。Expert 資料夾本身不含安裝邏輯。

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-02-1 | `connsys-jarvis/scripts/setup.py` 為**唯一安裝程式**，以 Python stdlib 實作，用 `uv run ./connsys-jarvis/scripts/setup.py` 執行 | Must | 單一入口，避免每個 Expert 各自維護 install.sh；Python stdlib 無需額外依賴 |
| FR-02-2 | 支援 `--init <expert.json>` 參數：**全新安裝**，清除所有既有 link，讀取 expert.json 及其 dependencies，重建所有 symlink，重新生成 CLAUDE.md 和 .env | Must | 初次安裝或強制重建時使用 |
| FR-02-3 | 支援 `--add <expert.json>` 參數：**疊加安裝**，在既有 Expert 基礎上加入新的 Expert；CLAUDE.md 預設只包含最後安裝 Expert 的 identity（soul/rules/duties/expert.md），加上 `--with-all-experts` 旗標則同時輸出所有已安裝 Expert 的 expert.md（Identity + Capabilities 雙區段） | Must | 多 Expert 安裝流程；預設 identity-only 避免 context 過大，`--with-all-experts` 視需要開啟全能力 |
| FR-02-4 | 支援 `--remove <expert.json>` 參數：從已安裝清單移除此 Expert，依剩餘 Expert 重建 symlink 和 CLAUDE.md；**全清再重建策略**：先清除 .claude/ 下所有 symlinks，再依剩餘 Expert（按 install_order）逐一重建，確保 symlink 集合與已安裝清單完全同步 | Must | 全清再重建與 --add 策略一致，邏輯簡單可靠，無需維護 reference count |
| FR-02-5 | 支援 `--uninstall` 參數：清除所有 link 和 CLAUDE.md，但保留 `.connsys-jarvis/log/` 和 `.connsys-jarvis/memory/` | Must | 完全清除安裝，保留記憶 |
| FR-02-6 | 支援 `--list` 參數：即時掃描 connsys-jarvis 目錄，列出**所有** Expert（已安裝 + 可用）及 symlink 狀態；每個 Expert 標注 status（installed/available）、install_order、is_identity | Must | 讓同仁了解目前安裝狀態，並一覽可用但尚未安裝的 Expert |
| FR-02-7 | 支援 `--doctor` 參數：診斷所有 symlink 是否 dangling、列出已安裝 Expert、檢查 Python/uv/uvx 環境 | Must | 快速排查安裝問題 |
| FR-02-8 | setup.py 讀取 `expert.json` 兩類來源：**① `dependencies`**（引用其他 Expert 的 symlinks）和 **② `internal`**（本 Expert 自有的 skills/hooks/commands）。`dependencies` 陣列每個元素可針對四個 key（skills/hooks/agents/commands）各自指定選擇規則：**`"all"`** → 繼承該 Expert 的全部；**`["name1","name2"]`** → 只繼承指定清單；**省略 key** → 不繼承（空集合）。`internal` 下的四個 key 永遠全部建立 | Must | 精確控制每個依賴 expert 貢獻的 link；internal 與 dependencies 分開，避免不必要的 skill 被載入 |
| FR-02-9 | expert.json 支援 `exclude_symlink.patterns`（全域 regex 清單），在所有 link 建立完成後（Step 1+2），於 Step 3 移除名稱符合任一 pattern 的 link | Must | 全域過濾可跨所有 dependency 統一移除不需要的 link，正則表達式提供更彈性的匹配 |
| FR-02-10 | setup.py 執行後將環境變數寫入 `workspace/.connsys-jarvis/.env`；同仁需手動執行 `source .connsys-jarvis/.env` | Must | 環境變數需存入 shell，Python 程式本身無法修改 parent shell 環境 |
| FR-02-11 | setup.py 每次執行結束後自動印出提示訊息：`✅ 安裝完成。請執行：source .connsys-jarvis/.env` | Must | 避免同仁忘記 source，導致環境變數失效 |
| FR-02-12 | setup.py **不**修改 `settings.json` / `settings.local.json`（由 `setup-claude.sh` 處理）| Must | 解耦平台相依 |
| FR-02-13 | setup.py **不**包含 MCP 設定 | Must | MCP 屬不同層次的設定 |
| FR-02-14 | setup.py 安裝前自動檢查：system Python 版本、`uv` 是否安裝、`uvx` 是否可用；版本不符輸出警告（不阻斷）| Should | PEP 723 腳本需要 Python ≥ 3.11 |
| FR-02-15 | Windows 環境下 symlink 不可用時，setup.py 自動降級為 **copy 模式**（功能相同，但更新 expert 內容後需重新執行）| Should | 跨平台支援 |
| FR-02-16 | Hook 實作語言優先順序：**Shell（預設）→ Python（複雜邏輯）→ JS（最後考慮）**；Python 腳本採 PEP 723 | Must | 一致的語言策略，Shell 無需額外 runtime |
| FR-02-17 | `connsys-jarvis/scripts/test/test_setup.py` 提供 **pytest 單元測試**，覆蓋 `setup.py` 所有核心函式；執行方式：`uvx pytest scripts/test/test_setup.py -v` 或 `uv run --with pytest pytest scripts/test/test_setup.py` | Must | 確保安裝邏輯可回歸測試；含環境變數生成、CLAUDE.md 生成、symlink 建立等整合測試 |
| FR-02-18 | 支援 `--query <expert-name>` 參數：即時掃描並讀取指定 Expert 的 expert.json，顯示 metadata（name、domain、description、version、status、dependencies、internal）；支援部分名稱匹配 | Must | 讓工程師和 skill 可快速查詢指定 Expert 的能力與狀態 |
| FR-02-19 | `--list` 和 `--query` 支援 `--format json` 旗標：以 JSON 格式輸出結果，供 framework-expert-discovery-knowhow skill 或 LLM 呼叫；預設輸出 table 格式（人類可讀）| Must | LLM 可直接解析 JSON 取得結構化 Expert 清單，無需解析文字輸出 |
| FR-02-20 | `--add <expert.json>` 對已安裝的 Expert 執行**重新安裝**：先從已安裝清單移除，再依正常 --add 流程重建 symlinks 和 CLAUDE.md（冪等性：重複 --add 結果一致）| Must | 同仁更新 expert.json 後可直接重新 --add 而無需先 --remove；確保安裝狀態正確 |

### FR-03：環境變數

所有環境變數由 setup.py 寫入 `workspace/.connsys-jarvis/.env`，同仁執行 `source .connsys-jarvis/.env` 後即可在 skill、hook、agent 中使用。
**所有變數統一使用 `CONNSYS_JARVIS_` 前綴**。

| 環境變數 | 說明 | Agent First 範例值 | Legacy 範例值 |
|---------|------|-------------------|--------------|
| `CONNSYS_JARVIS_PATH` | `connsys-jarvis` repo 的路徑 | `~/workspace/connsys-jarvis` | `~/workspace/connsys-jarvis` |
| `CONNSYS_JARVIS_WORKSPACE_ROOT_PATH` | 工作根目錄（`.claude/` 所在）| `~/workspace` | `~/workspace` |
| `CONNSYS_JARVIS_CODE_SPACE_PATH` | 程式碼路徑（source code repo 所在）| `~/workspace/codespace` | `~/workspace` |
| `CONNSYS_JARVIS_MEMORY_PATH` | local memory 路徑 | `~/workspace/.connsys-jarvis/memory` | `~/workspace/.connsys-jarvis/memory` |
| `CONNSYS_JARVIS_EMPLOYEE_ID` | 員工工號（自動從 `git config user.name` 取得）| `john.doe` | `john.doe` |

**使用範例**（在 skill 或 hook 中）：
```bash
# 在 skill 中引用 code space 路徑
BUILD_DIR="$CONNSYS_JARVIS_CODE_SPACE_PATH/fw/bora/build"

# 在 hook 中推送記憶
git -C "$CONNSYS_JARVIS_MEMORY_PATH" push origin main
```

### FR-04：Skill 系統（Knowledge）

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-04-1 | 每個 Skill 以獨立資料夾存放，含 `SKILL.md`（YAML frontmatter + 內容） | Must | 結構化格式，未來遷移 OpenClaw 直接相容 |
| FR-04-2 | `expert-discovery` skill 列出所有 Expert 及能力 | Must | 基本的系統可發現性 |
| FR-04-3 | `handoff-protocol` skill 定義交接格式與流程 | Must | 所有 Expert 都需要知道如何交接 |
| FR-04-4 | Expert 可有私有 skills，切換時一併替換 | Must | 不同專家有不同的知識庫 |
| FR-04-5 | External skills 透過 registry 聲明，setup.py 自動建立 link | Should | 整合社群工具 |
| FR-04-6 | 每個 Skill 資料夾除 `SKILL.md` 外，還需含 `README.md`、`test/`、`report/` | Must | 統一 Skill 資料夾標準，支援測試驗證與執行記錄 |
| FR-04-7 | Skill `README.md` 記錄：History、使用說明、人工安裝說明、Design、目的；開發說明亦可寫於此（如何新增 case、測試覆蓋率目標、已知問題）。Skill README 範本與最佳實踐詳見 Future Work FW-03 | Must | 讓維護者了解 skill 的脈絡與演進，開發者不需另開文件 |
| FR-04-8 | Skill `test/` 以 **Shell 腳本（`test-basic.sh`）為主**；需 Python 時使用 pytest，測試檔命名 `test_xxx.py` | Must | Shell 腳本覆蓋基本驗證；pytest 負責結構化 unit test，CI 可自動執行 |
| FR-04-9 | Skill `report/` 記錄執行過程、結果、token 用量 | Should | 追蹤 Skill 品質與 AI 成本 |
| FR-04-10 | Skill 內的 script 語言優先順序：**Shell（預設）→ Python（複雜邏輯）**，與 hook 策略一致 | Must | 一致的語言策略降低維護認知負擔 |
| FR-04-11 | Skill / Hook 內的所有 **Python 腳本須採用 PEP 723 Inline Script Metadata**，在腳本頂端宣告 `requires-python` 與 `dependencies` | Must | 免除 `requirements.txt` 與 venv 管理；每個腳本自帶依賴宣告，可直接用 `uv run` 執行；參考：[PEP 723](https://peps.python.org/pep-0723/) |
| FR-04-12 | pytest `test_xxx.py` 放置於 skill 的 `test/` 資料夾，測試資料用 `test-data.json` 或 `conftest.py` 管理；執行 pytest 時**優先使用 `uvx pytest`**，可與 `uv run` 共用同一 Python 版本，避免環境不一致 | Should | 標準化測試目錄，CI 可直接 `uvx pytest test/` 執行；`uvx` 確保 pytest 與腳本使用相同 Python 版本 |
| FR-04-13 | **Skill 為主要實作單位；`commands/` 資料夾僅保留作 Claude plugin format 相容用**。新開發的 Expert 不須再建立獨立的 command 資料夾；若 Skill 需要像 Command 一樣行為（不自動觸發），在 SKILL.md frontmatter 加入 `disable-model-invocation: true` | Must | 統一以 Skill 開發，降低概念複雜度；Command 資料夾為歷史相容層，未來 Phase 2 遷移時統一處理 |

### FR-05：CLAUDE.md 生成機制

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-05-1 | setup.py 在 workspace 根目錄生成 `CLAUDE.md`（非 symlink） | Must | CLAUDE.md 是動態生成的，不放在 expert 資料夾中 |
| FR-05-2 | 安裝單個 Expert 時，CLAUDE.md 以 `@include` 讀取該 Expert 資料夾的 `expert.md`、`soul.md`、`rules.md`、`duties.md` | Must | 直接引用 expert 資料夾的檔案，更新 expert 後不需重裝即可生效 |
| FR-05-3 | 安裝多個 Expert 時，以**最後安裝的 Expert** 的 `soul.md`、`rules.md`、`duties.md` 為主 identity；所有已安裝 Expert 的 `expert.md` 均 @include | Must | 多 Expert 環境有清楚的 identity 主從關係 |
| FR-05-4 | CLAUDE.md 末尾 `@include CLAUDE.local.md`（若不存在，Claude Code 忽略） | Must | 個人客製化入口 |
| FR-05-5 | `CLAUDE.local.md` 不納入 `connsys-jarvis` repo，以 `.gitignore` 排除 | Must | 個人設定不進 repo |
| FR-05-6 | Expert 資料夾**不含** `CLAUDE.md`（由 setup.py 在 workspace 根目錄生成） | Must | 避免混淆：expert 資料夾只含內容，workspace root 的 CLAUDE.md 才是生效的 |

### FR-06：記憶系統（Workflow + 後臺）

#### FR-06A：四個 Hook 存檔點

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-06-1 | 本地記憶以 Markdown 為格式 | Must | 透明可編輯，無外部依賴 |
| FR-06-2 | `session-end` hook 自動儲存 session 摘要 | Must | 確保記憶不遺失 |
| FR-06-3 | `pre-compact` hook 在 context 壓縮前存快照（最可靠存檔點）| Must | 參考 claude-memory-engine 的三存檔點設計 |
| FR-06-4 | `mid-session-checkpoint` hook 每 20 訊息存一次 | Should | 避免長 session 中途資料遺失 |
| FR-06-5 | `session-start` hook 載入上次摘要 + 偵測待接 hand-off | Must | 新 session 能延續上次工作 |
| FR-06-6 | 記憶資料自動 push 到 `connsys-memory` repo | Must | 後臺收集與跨裝置同步 |

#### FR-06B：本地三區記憶（Local Three-Zone Memory）

本地記憶存放於 `workspace/.connsys-jarvis/memory/`，以 expert 名稱和日期分資料夾。session-stop hook 負責上傳至遠端 `connsys-memory` repo（git push）：

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-06-7 | 建立 `.connsys-jarvis/memory/shared/` 區域（跨 Expert 共用知識） | Must | 儲存 project.md、conventions.md 等跨 Expert 都需要的知識，Expert 切換後仍可讀取 |
| FR-06-8 | 建立 `.connsys-jarvis/memory/{expert-name}/{date}/` 區域（當前 Expert 的飛行中狀態），命名格式：`{HH:MM}-{expert-name}-memory.md` | Must | 以日期和時間戳命名，方便回溯；Expert 切換時歸檔 |
| FR-06-9 | 建立 `.connsys-jarvis/memory/handoffs/{run-id}/` 區域（交接文件，寫入後唯讀）。**`run-id` 應使用 Claude Session ID**（由環境變數或 hook context 取得）；fallback 為 `{timestamp}-{random}` | Must | Session ID 作 run-id，同一人多視窗不衝突；handoff 文件 < 2000 tokens，新 Expert 由 session-start hook 讀取 |
| FR-06-10 | `session-start` hook 自動偵測 `memory/handoffs/` 是否有待接的 hand-off 文件 | Must | 新 Expert 啟動時不需人工操作即可拿到上一個 Expert 的交接內容 |
| FR-06-11 | 週期性記憶整理（Periodic Collection）：每日或每週自動彙整本地記憶至 connsys-memory | Should | 收集長期知識，供未來 framework-learn-expert 分析，但不造成即時系統負擔 |

### FR-07：Hand-off 協議與 Expert 狀態機

| 編號 | 需求 | 優先級 |
|------|------|--------|
| FR-07-1 | Hand-off 發生時機：切換 Expert 時（--switch）、session 結束時 | Must |
| FR-07-2 | Hand-off 文件格式：YAML frontmatter + Markdown 摘要（< 2000 tokens）| Must |
| FR-07-3 | 提供 `/handoff` 指令供同仁手動觸發 | Must |
| FR-07-4 | Hand-off 文件同時存入本地 `memory/handoffs/{run-id}/`（當前 Expert 讀取用）及 `connsys-memory/employees/{id}/handoffs/`（遠端備份） | Must |
| FR-07-5 | `expert.json` 的 `transitions` 欄位定義 Expert 的狀態機轉移（事件 → 下一個 Expert） | Must |
| FR-07-6 | 轉移事件（如 BUILD_SUCCESS / BUILD_FAILED）由 Expert 在工作完成後主動發出，觸發 hand-off 流程 | Must |
| FR-07-7 | 若轉移目標為 `null`（如 BUILD_FAILED），表示需要人工介入，Expert 應提示同仁並等待 | Must |
| FR-07-8 | Stage 2 未來：符合條件的 transitions 可自動觸發 setup.py --init，無需人工操作 | Future |

### FR-08：後臺資料收集

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-08-1 | `connsys-memory` 為單一 repo，以工號（git username）為子資料夾 | Must | 集中管理，不需每人維護自己的 repo |
| FR-08-2 | 收集內容：session 摘要、hand-off 文件、使用的 Expert 名稱 | Must | 管理者可分析哪些 Expert 最常用、哪些流程最常卡關 |
| FR-08-3 | 預設自動 push，可設定為手動 | Must | 減少同仁操作負擔 |

### FR-09：Human in the Loop（未來）

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-09-1 | 對不可逆操作（git push、裝置控制、刪除）先輸出警告，等待人類確認 | Must | 避免 Agent 自動操作造成不可逆損害 |
| FR-09-2 | 警告訊息包含：操作說明、影響範圍、確認提示 | Must | 讓同仁有足夠資訊做判斷 |
| FR-09-3 | Expert 可設定哪些操作需要人類介入（per-expert 設定） | Should | 不同 Expert 的風險等級不同 |
| FR-09-4 | 未來支援 Agent 自行 install 所需 Expert | Could | 實現完全自動化的先決條件 |
| FR-09-5 | **Human in the Loop 的確認行為由 Expert/Skill 的 prompt 內容實作**，透過 SKILL.md 或 expert.md 中的指引告知 Claude Code / OpenClaw 在特定操作前應暫停並詢問同仁；不依賴外部 stdin/API，確保跨平台（Claude Code、OpenClaw）皆可運作 | Must | 以 prompt 驅動確認行為是最可攜帶的方式，不綁定特定平台的 stdin 或 UI 元件 |

---

## 5. 非功能需求

| 類別 | 需求 | 理由 |
|------|------|------|
| **可遷移性** | Skill 格式相容 OpenClaw；Hook 以 Shell/Python 實作（平台無關），未來遷移 OpenClaw 時改為 TypeScript | 不綁定特定平台是核心設計目標 |
| **可擴充性** | 新增 Expert 只需新增資料夾 + expert.json，不修改其他 Expert | 降低同仁貢獻新 Expert 的門檻 |
| **可稽核性** | Hand-off 與 session 記憶均透過 Git 保存，支援 diff 與歷史查詢 | 後臺分析與問題溯源的基礎 |
| **Context 效率** | Hand-off 摘要 < 2000 tokens | 避免新 Expert 開始時就面臨 context 爆炸 |
| **相容性** | 完全運行於 Claude Code CLI，不依賴外部服務或資料庫 | 降低部署複雜度 |
| **透明性** | 所有 hooks 以可讀的 Shell/Python 實作，同仁可自行檢視與修改；韌體工程師無需學習 JS 即可維護 | 參考 Harness Engineering 的精神：no black boxes |

---

## 6. 限制與假設

### 限制

- setup.py 僅處理 symlink/copy，不觸碰 `settings.json`（由 `setup-claude.sh` 處理）
- MCP 設定不在 setup.py 範圍內
- Symlink 在 Windows 環境下：setup.py 自動偵測並降級為 copy 模式（FR-02-15），功能相同，但更新 expert 內容後需重新執行 setup.py
- `connsys-memory` repo 的 push 需要同仁對 remote 有寫入權限
- Human in the Loop 功能為未來規劃，本期以人工切換 Expert 為主
- **Skill 版本向後相容性**：SKILL.md frontmatter 的 `version` 欄位目前僅供顯示，尚未定義 Skill 升版後舊 hand-off 文件的相容性規則；Skill 的 breaking change 需人工審查
- **Local memory GC 尚未設計**：`memory/shared/` 無限增長、`memory/handoffs/` 無保留期限機制，待真實使用 hand-off 功能後再行設計（詳見 Future Work FW-04）

### 假設

- 同仁具備基本終端機操作能力
- 執行環境已安裝 Claude Code CLI、Git、bash
- 同仁的 git config user.name 即其工號（企業環境統一設定）
- `connsys-memory` remote 由管理者預先建立並開放所有同仁寫入

### FR-07：Framework Expert/Skill 建立工具

為降低新建 Expert 和 Skill 的門檻，`framework-base-expert` 提供兩個輔助建立的 flow skill，確保產出符合 connsys-jarvis 規範。

| 編號 | 需求 | 優先級 | 理由 |
|------|------|--------|------|
| FR-07-1 | **`framework-skill-create-flow`**：互動式引導工程師建立符合規範的 Skill。接收使用者對 Skill 用途的描述，輸出完整的 SKILL.md（含 YAML frontmatter、必要章節）、README.md、`test/test-basic.sh` 初版，並放置於正確的五層目錄結構 | Must | 降低建立 Skill 的門檻；確保每個 Skill 包含所有必要章節（觸發條件、How it works、範例、限制），避免遺漏造成 AI 誤用 |
| FR-07-2 | `framework-skill-create-flow` 輸出的 SKILL.md 須包含以下章節：**① YAML frontmatter**（name/description/version/domain/type/scope/tags）、**② Trigger**（觸發詞與條件）、**③ How it works**（步驟說明）、**④ 範例**（至少 1 個）、**⑤ 相依 Skills**（若有）、**⑥ 限制與邊界** | Must | 完整的 SKILL.md 讓 AI 準確理解何時呼叫、如何執行 |
| FR-07-3 | `framework-skill-create-flow` 建立 Skill 後，詢問是否要執行 `test/test-basic.sh` 驗證基本結構完整性 | Should | 即時確認 Skill 結構正確，避免安裝後才發現問題 |
| FR-07-4 | **`framework-expert-create-flow`**：互動式引導工程師建立符合規範的 Expert 資料夾結構。接收使用者對 Expert 角色、職責、適用場景的描述，輸出高品質的 `soul.md`、`rules.md`、`duties.md`、`expert.md`、`expert.json` 初稿，並建立標準資料夾骨架 | Must | 降低建立 Expert 的門檻；確保四個核心文件（soul/rules/duties/expert）結構完整、語意清晰，避免 Expert 定義模糊導致 AI 行為不一致 |
| FR-07-5 | `framework-expert-create-flow` 輸出的四個核心文件須符合：**soul.md**（Identity / Values & Principles / Communication Style / Personality）、**rules.md**（Must Always / Must Never / Boundaries / Conflict Resolution）、**duties.md**（Primary Duties / Segregation of Duties / KPIs）、**expert.md**（Overview / Key Behaviors / Tools Available / Skills 表格 / Hooks 表格） | Must | 四個文件各有明確的結構責任；結構一致才能讓 framework-base-expert 的 hand-off 和 discovery 機制正確運作 |
| FR-07-6 | `framework-expert-create-flow` 產生的 `expert.json` 初稿含正確的 schema 欄位（name/version/description/domain/type/dependencies/internal/exclude_symlink），dependencies 預設包含 `framework-base-expert` | Must | 減少工程師手動填寫 expert.json 的錯誤；新 Expert 預設繼承 framework-base-expert 的 hooks 和 commands |
| FR-07-7 | 兩個 flow skill 均作為 `framework-base-expert` 的 internal skills，透過 `scripts/setup.py --init framework/experts/framework-base-expert/expert.json` 安裝後即可使用 | Must | 建立工具隨 framework 安裝，不需額外操作 |

---

## 7. 遷移路線

```
Phase 1：Claude Code（現在）
  setup.py symlink → .claude/skills（Knowledge）, hooks（Workflow）, commands（Tool）
  CLAUDE.md 生成機制
  connsys-memory Git 後臺收集
  Hooks 以 Shell 實作（複雜邏輯用 Python）
  Human in the Loop：人工切換 Expert

Phase 2：OpenClaw
  setup.py --target openclaw
  SKILL.md 直接相容
  Shell/Python hooks → TypeScript handler.ts（此階段重寫 hooks）
  connsys-memory → workspace/MEMORY.md + LanceDB
  Human in the Loop：Hook 觸發確認機制

Phase 3：ADK/SDK（全自動）
  expert.json → AgentDefinition
  手動 install → Agent 自行 install
  Markdown hand-off → JSON output_format
  Human in the Loop：風險評分自動決定介入等級
```

---

## 8. 名詞定義

| 術語 | 定義 |
|------|------|
| Consys Expert | Agent 能力 + Consys Workflow + Consys Tool + Consys Knowledge 的組合體 |
| Harness Engineering | 為 AI 打造「自動化治理體系」，透過限制行為邊界與豐富上下文，實現大規模自動化（來源：Birgitta Böckeler / Martin Fowler Blog）|
| connsys-jarvis | 團隊共同維護的 Expert 工具 repo |
| connsys-memory | 後臺資料收集 repo，以員工工號（git username）為子資料夾 |
| scripts/setup.py | 安裝腳本，建立 symlinks，生成 CLAUDE.md，設定環境變數 |
| Agent First | 從空白 workspace 開始，由 Expert 引導下載 code 的場景 |
| Legacy | 同仁已手動下載 code，後續引入 Expert 的場景 |
| codespace | Agent First 場景下，Expert 引導下載的 source code 集中目錄 |
| Hand-off | Expert 切換或 session 結束時產生的結構化上下文摘要文件 |
| common/ | 所有 Expert 共用的 skills/hooks/commands |
| external/ | 整合的社群優質工具，以工具名稱為資料夾名 |
| expert.md | 由  setup.py 從 expert.json 生成的可讀 Markdown |
| expert.local.md | 使用者個人客製化檔，不納入 connsys-jarvis repo |
| Human in the Loop | 對高風險操作暫停等待人類確認的機制 |
| `CONNSYS_JARVIS_PATH` | 指向 connsys-jarvis repo 的環境變數 |
| `CONNSYS_JARVIS_WORKSPACE_ROOT_PATH` | 工作根目錄（.claude/ 所在），兩個場景均為 workspace 根目錄 |
| `CONNSYS_JARVIS_CODE_SPACE_PATH` | 程式碼路徑（Agent First: codespace/；Legacy: workspace 根目錄）|
| `CONNSYS_JARVIS_MEMORY_PATH` | 指向 connsys-memory repo 的環境變數 |
| `CONNSYS_JARVIS_EMPLOYEE_ID` | 員工工號，自動從 git config user.name 取得 |

---

## 9. Future Work

### FW-01：Security — Expert 安全審計機制

**背景**：

AI Agent 生態系統的安全威脅已有實際案例：
- 2026 年 1 月，主要 Agent 技能市場中 **12%（341/2,857）為惡意技能**
- CVSS 8.8 的 CVE 暴露了 **17,500+ 個面向網路的實例**
- Moltbook 漏洞跨 770,000 個 Agent 洩露了 **150 萬個 API token**

目前同仁在安裝 external-experts、連接 MCP 伺服器、設定 hooks 時，沒有任何自動化安全審計機制。

**需求**：

| 編號 | 需求 | 優先級 |
|------|------|--------|
| FW-01-1 | 建立 `framework-security-expert`，提供自動化安全審計能力 | Future |
| FW-01-2 | 提供 pre-install hook，在安裝 external-experts 前自動掃描 | Future |
| FW-01-3 | 靜態分析 SKILL.md / COMMAND.md，偵測 prompt injection 與資料外洩指令 | Future |
| FW-01-4 | 掃描 hooks（.sh / .py）是否有可疑網路呼叫或非預期檔案讀寫 | Future |
| FW-01-5 | 產生安全掃描報告，更新至 `report/execution-report.md` | Future |

**參考實作**：[AgentShield](https://github.com/affaan-m/agentshield)

---

### FW-02：Memory + Learn — 自我檢討的 Expert

**背景**：

目前 Expert 的 knowledge（SKILL.md）是靜態的，由人工撰寫與維護。隨著 connsys-memory 累積越來越多的使用記錄，有機會讓 Expert 從記憶中自動學習，持續改善自己的 skills。

**設計方向**：
```
使用記憶（sessions/ + handoffs/）
    → framework-learn-expert 分析
    → 找出 pattern（常見錯誤、成功解法）
    → 自動產生/更新 SKILL.md
    → PR → 人工 review → merge → 所有人受益
```

**需求**：

| 編號 | 需求 | 優先級 |
|------|------|--------|
| FW-02-1 | `framework-learn-expert` 能定期分析 connsys-memory 的 session 記錄 | Future |
| FW-02-2 | 從記憶中萃取重複出現的問題與解法，產生 knowhow skill 草稿 | Future |
| FW-02-3 | 自動建立 PR，由人工 review 後合入 connsys-jarvis repo | Future |
| FW-02-4 | 實現完整的 `Think → Plan → Act → Learn` 循環 | Future |

**參考實作**：[claude-mem](https://github.com/thedotmack/claude-mem)

---

### FW-03：Skill README 開發說明範本

**背景**：

目前 FR-04-7 僅規定 README.md 應包含的大綱，但沒有具體的開發說明格式範本。隨著團隊規模擴大，需要更一致的 Skill 開發文件標準。

**目標**：

提供標準化 Skill README 範本，包含：開發說明章節格式、如何新增 case 的步驟、測試覆蓋率目標、已知問題記錄方式。

**參考資料**：

- [Skill Best Practices（Claude 官方）](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [SKILL.md 範例（Anthropic skills repo）](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)

**需求**：

| 編號 | 需求 | 優先級 |
|------|------|--------|
| FW-03-1 | 提供標準化的 Skill README.md 範本（含開發說明章節）| Future |
| FW-03-2 | 範本包含：如何新增 case、測試覆蓋率目標（Shell + pytest）、已知問題、維護建議 | Future |
| FW-03-3 | 在 `framework-skill-create-expert` 中整合 README 範本生成步驟 | Future |

---

### FW-04：Local Memory GC 機制

**背景**：

目前 `memory/shared/`、`memory/working/`、`memory/handoffs/` 皆無自動清理機制，長期使用後可能無限增長。

**目標**：

設計合理的 GC 策略，在不影響可靠性的前提下控制 memory 資料夾大小。

**需求**：

| 編號 | 需求 | 優先級 |
|------|------|--------|
| FW-04-1 | 定義 `memory/handoffs/` 的保留期限（如保留最近 30 個 run-id）| Future |
| FW-04-2 | 定義 `memory/shared/` 的壓縮策略（如超過一定大小自動摘要）| Future |
| FW-04-3 | 由 session-end hook 或獨立 GC script 負責定期清理 | Future |

> 此功能待真實使用 hand-off 功能、累積足夠資料後再行設計。

---

### FW-05：Expert 推薦機制

**現況**：`registry.json` 已廢棄並移除（v3.3）。`setup.py --list --format json` 和 `--query <name> --format json` 提供即時 Expert 探索能力，`framework-expert-discovery-knowhow` skill 可直接呼叫這兩個指令取得 JSON 資料。

**待規劃**：根據當前任務自動推薦合適 Expert 的機制（根據 task context 比對 Expert 的 description/capabilities）。

| 編號 | 需求 | 優先級 |
|------|------|--------|
| FW-05-1 | 定義 expert-discovery skill 的自動推薦邏輯（根據任務描述比對 Expert description 排序）| Future |

---

## 10. 參考資料

### 核心概念

| 資料 | 說明 |
|------|------|
| [Harness Engineering（Martin Fowler Blog）](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) | 本系統架構核心啟發 |
| [AgentShield](https://github.com/affaan-m/agentshield) | Agent 安全審計參考實作（FW-01）|
| [claude-memory-engine](https://github.com/HelloRuru/claude-memory-engine) | Hooks 設計參考，8-step 學習循環 |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 輕量記憶系統，memory → learn 參考（FW-02）|

### 延伸閱讀（個人知識庫，連結待更新為個人網站）

| 資料 | 說明 |
|------|------|
| [Lessons from Building Claude Code — How We Use Skills](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/AI/2026-03-17-LESSONS-FROM-BUILDING-CLAUDE-CODE-HOW-WE-USE-SKILLS.md) | 實戰經驗：Claude Code 中 Skills 的使用心得 |
| [5 Agent Skill Design Patterns Every ADK Developer Should Know](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/AI/2026-03-18-5-AGENT-SKILL-DESIGN-PATTERNS-EVERY-ADK-DEVELOPER-SHOULD-KNOW.md) | ADK 開發者必知的 5 種 Skill 設計模式 |
| [Claude-mem Code Analysis](https://github.com/swchen44/personal-knowledge-base-from-ai/blob/main/CodeAnalysis/2025-08-31-CLAUDE-MEM-CODE-ANALYSIS.md) | claude-mem 原始碼深度分析 |
