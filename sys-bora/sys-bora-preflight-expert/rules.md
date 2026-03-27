# Sys Bora Preflight Expert — Rules

## Must Always

- 提交前確認 commit message 符合規範（Change-Id、Test 欄位）
- preflight 觸發後等待結果，不在 CI 仍在跑時提交
- 分析 preflight failure log 前，先確認是否為 flaky test
- 需要 submit 時確認有足夠的 CR+2 label

## Must Never

- 在未通過 preflight 的情況下 submit change
- 使用 `git push --force` 覆蓋他人的 commit
- 在未取得 code review 核准的情況下自行 submit
- 忽略 Verified-1（明確失敗）直接 submit

## Label 規範

| Label | 值 | 意義 |
|-------|-----|------|
| Code-Review | +2 | 可以合入 |
| Code-Review | +1 | 看起來不錯，但需要其他 reviewer +2 |
| Code-Review | -1 | 不應合入（需修改） |
| Verified | +1 | CI 通過 |
| Verified | -1 | CI 失敗 |
