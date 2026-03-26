---
name: sys-bora-repo-tool
description: "Android repo 工具操作指南，包含 init、sync、branch 管理和常見問題排除"
version: "1.0.0"
domain: sys-bora
type: tool
scope: sys-bora-base-expert
tags: [repo, android, manifest, sync, sys-bora]
---

# Sys Bora Repo Tool

## Repo 工具概覽

Android `repo` 是 Google 開發的多 git repo 管理工具，ConnSys 使用它管理跨多個 git repository 的 SoC source code。

## 常用指令

### 初始化

```bash
# 初始化 repo（使用指定 manifest）
repo init -u <manifest-url> -b <branch> -m <manifest.xml>

# 例：
repo init -u https://gerrit.example.com/platform/manifest \
    -b bora-dev \
    -m bora_default.xml
```

### 同步 Source Code

```bash
# 同步所有 project（推薦加 -j）
repo sync -j8 --no-tags

# 只同步特定 project
repo sync wifi/wifi-bora -j4

# 強制覆蓋本地修改（危險！）
repo sync -f --force-sync
```

### 查看 Manifest

```bash
# 查看當前 manifest
repo manifest

# 查看 manifest 中的所有 project
repo list

# 查看特定 project 的遠端 URL
repo list -f wifi/wifi-bora
```

### Branch 管理

```bash
# 列出所有 local branch（跨所有 project）
repo branch

# 在所有 project 建立新 branch
repo start <branch-name> --all

# 在特定 project 建立 branch
repo start <branch-name> wifi/wifi-bora

# 切換 branch
repo checkout <branch-name>
```

### 批次操作

```bash
# 在所有 project 執行 git status
repo status

# 在所有 project 執行 git log（最後 5 筆）
repo forall -c git log --oneline -5

# 在所有 project 執行 git fetch（危險操作前先確認）
repo forall -p -c git fetch origin
```

## Manifest 結構

```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <remote name="origin" fetch="https://gerrit.example.com" />
  <default revision="bora-dev" remote="origin" sync-j="4" />

  <project name="platform/manifest" path="manifest" />
  <project name="wifi/wifi-bora" path="wifi-bora" />
  <project name="sys/bora" path="sys-bora" />
</manifest>
```

## 常見問題

### sync 失敗：`error: RPC failed`

```bash
# 降低並行數
repo sync -j2 --no-tags

# 或設定 git buffer
git config --global http.postBuffer 524288000
```

### Local Changes 未提交導致無法 sync

```bash
# 先確認有哪些未提交的修改
repo status

# 暫存修改
repo forall -c git stash

# sync 後恢復
repo forall -c git stash pop
```

### Manifest 版本不一致

```bash
# 查看當前 manifest hash
cat .repo/manifest.xml | grep revision

# 重新 init 指定版本
repo init -b <specific-branch>
repo sync
```
