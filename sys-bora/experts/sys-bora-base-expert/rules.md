# Sys Bora Base Expert — Rules

## Must Always

- 確認 repo manifest 版本和分支正確後再執行 sync
- 執行 `repo forall` 命令前，先說明影響範圍
- Gerrit change 的 commit message 必須符合團隊規範

## Must Never

- 執行 `git push --force` 到 protected branch
- 不確認情況下執行 `repo forall -c git reset --hard`
- 在未設定 CROSS_COMPILE 的情況下執行 build

## Boundaries

- Gerrit commit 和 preflight 的完整流程由 sys-bora-preflight-expert 處理
- 本 Expert 提供基礎的 gerrit 和 repo 工具知識
