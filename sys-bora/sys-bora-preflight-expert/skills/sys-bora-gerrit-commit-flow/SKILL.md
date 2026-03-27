---
name: sys-bora-gerrit-commit-flow
description: "Gerrit change 提交完整流程 SOP，從 commit 準備到 submit 的每個步驟"
version: "1.0.0"
domain: sys-bora
type: flow
scope: sys-bora-preflight-expert
tags: [sys-bora, gerrit, commit, push, review, submit]
---

# Sys Bora Gerrit Commit Flow

## 流程概覽

```
Step 1: 準備 commit
Step 2: 本地驗證（build/lint）
Step 3: git push 到 Gerrit
Step 4: 設定 reviewer
Step 5: 觸發並等待 preflight
Step 6: 回應 review 意見
Step 7: Submit
```

## Step 1：準備 Commit

### Commit Message 格式

```
[<project>] <short-description>

<body>: 詳細說明修改內容和原因
  - 解決了什麼問題
  - 為何選擇這個方案
  - 有哪些 tradeoff

Test: <how the change was tested>
Bug: <bug-tracker-id>（若有）
Change-Id: I<40 hex chars>（由 commit-msg hook 自動生成）
```

### 安裝 Gerrit commit-msg hook

```bash
# 下載 hook（只需執行一次）
scp -p gerrit.example.com:hooks/commit-msg .git/hooks/

# 確認 hook 可執行
chmod +x .git/hooks/commit-msg
```

### 建立 Commit

```bash
# Stage 修改
git add <modified-files>

# 建立 commit（hook 自動加上 Change-Id）
git commit

# 修改上一個 commit（amend）
git commit --amend
```

## Step 2：本地驗證

```bash
# Build 驗證
make -j$(nproc) && echo "Build OK"

# 程式碼格式檢查（若有 clang-format）
find . -name "*.c" -newer HEAD~1 | xargs clang-format --dry-run -Werror

# 靜態分析（若有）
make check
```

## Step 3：Push 到 Gerrit

**注意：執行前需確認工程師同意（human-in-the-loop）**

```bash
# 推送到 review branch
git push origin HEAD:refs/for/<target-branch>

# 帶 topic（關聯相關 change）
git push origin HEAD:refs/for/<target-branch>%topic=wifi-memory-slim-v2

# 帶 hashtag
git push origin HEAD:refs/for/<target-branch>%t=wifi-memory-slim
```

## Step 4：設定 Reviewer

```bash
# 使用 Gerrit REST API 加入 reviewer
curl -X POST \
    "https://gerrit.example.com/a/changes/<change-id>/reviewers" \
    --user user:http-password \
    -H "Content-Type: application/json" \
    -d '{"reviewer": "teammate@example.com"}'
```

## Step 5：Preflight

參考 `sys-bora-preflight-flow` skill。

## Step 6：回應 Review 意見

```bash
# 修改後更新 Patch Set（保留相同 Change-Id）
git commit --amend
git push origin HEAD:refs/for/<target-branch>
```

## Step 7：Submit

確認以下條件全部滿足後，可以 submit：
- [ ] `Verified: +1`（preflight 通過）
- [ ] `Code-Review: +2`（至少一位 reviewer 核准）
- [ ] 沒有未解決的 comment thread

```bash
# 使用 Gerrit REST API submit
curl -X POST \
    "https://gerrit.example.com/a/changes/<change-id>/submit" \
    --user user:http-password

# 或在 Gerrit UI 點擊 "Submit" 按鈕
```
