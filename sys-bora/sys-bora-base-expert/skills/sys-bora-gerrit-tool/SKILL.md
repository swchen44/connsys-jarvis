---
name: sys-bora-gerrit-tool
description: "Gerrit code review 平台的操作指南，包含 change 查詢、下載、review 操作"
version: "1.0.0"
domain: sys-bora
type: tool
scope: sys-bora-base-expert
tags: [gerrit, code-review, git, sys-bora]
---

# Sys Bora Gerrit Tool

## Gerrit 基本概念

| 術語 | 說明 |
|------|------|
| Change | 一個 Gerrit code review 單元（對應一個 git commit） |
| Patch Set | Change 的修訂版本（每次 push 產生新的 Patch Set） |
| CR | Code Review（Verified/+1/+2） |
| Label | Change 的 review 狀態標籤 |

## 常用操作

### 查詢 Change

```bash
# 使用 Gerrit CLI（若有安裝）
gerrit query --format JSON status:open project:wifi-bora

# 或直接用 git
git fetch gerrit refs/changes/<change-id>/<patch-set>
```

### 下載特定 Change

```bash
# 從 Gerrit 下載 change（patch set 1）
git fetch origin refs/changes/XX/<change-number>/1 && git checkout FETCH_HEAD

# 或使用 repo download（在 Android repo 環境中）
repo download <project> <change-number>/<patch-set>
```

### Push 到 Gerrit Review

```bash
# 推送到 Gerrit 進行 review（不直接合入）
git push origin HEAD:refs/for/<branch>

# 帶 topic
git push origin HEAD:refs/for/<branch>%topic=wifi-memory-slim

# 帶 reviewer
git push origin HEAD:refs/for/<branch>%r=reviewer@email.com
```

### 查看 Change 狀態

```bash
# 使用 Gerrit REST API
curl -s "https://gerrit.example.com/a/changes/<change-id>" \
    --user user:password \
    | python3 -m json.tool
```

## Commit Message 規範

```
[wifi-bora] Short description (< 72 chars)

Detailed explanation of the change.
What problem is being solved?
Why this approach?

Test: <how to verify>
Change-Id: I<40 hex chars>
```

## 注意事項

- 每個 Change 只能包含一個 commit（若需要多個 commit，使用 topic 關聯）
- 不要修改 `Change-Id` 行（由 `commit-msg` hook 自動生成）
- 更新 Patch Set 時，保留同一個 Change-Id：`git commit --amend`
