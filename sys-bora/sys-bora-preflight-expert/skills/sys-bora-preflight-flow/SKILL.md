---
name: sys-bora-preflight-flow
description: "ConnSys CI/CD preflight 觸發、監控和結果分析的完整 SOP"
version: "1.0.0"
---

# Sys Bora Preflight Flow

## Preflight 概覽

ConnSys 的 preflight 系統在 Gerrit change 提交後自動觸發 CI/CD 驗證，確保修改不影響現有功能。

## 觸發 Preflight

### 自動觸發

Push 到 Gerrit 後，若 change 通過基本格式檢查，系統自動觸發 preflight：

```
Gerrit → webhook → Jenkins → preflight pipeline
```

### 手動觸發（重新觸發）

當 preflight 因環境問題失敗，需要重新觸發時：

```bash
# 使用 Gerrit REST API 觸發 review
curl -X POST \
    "https://gerrit.example.com/a/changes/<change-id>/revisions/current/review" \
    --user user:http-password \
    -H "Content-Type: application/json" \
    -d '{"message": "Retrigger preflight", "labels": {}}'

# 或在 Gerrit UI 留言 "retrigger" 觸發 bot
```

## 監控 Preflight 狀態

### 查看 Jenkins Job

```bash
# 使用 Jenkins CLI（若有安裝）
java -jar jenkins-cli.jar -s <jenkins-url> \
    build "wifi-bora-preflight" \
    -p CHANGE_ID=<gerrit-change-id>

# 或查看 Jenkins URL
open "https://jenkins.example.com/job/wifi-bora-preflight/<build-number>/console"
```

### Gerrit Label 狀態

| Label | 意義 |
|-------|------|
| `Verified: 0` | preflight 尚未完成 |
| `Verified: +1` | preflight 通過 |
| `Verified: -1` | preflight 失敗 |

## 分析 Preflight 失敗

### Step 1：確認失敗類型

1. **Build Failure**：編譯錯誤，修改引入語法或 API 問題
2. **Test Failure**：功能測試失敗，需分析 test log
3. **Flaky Test**：偶發性失敗，與修改無關（可重試）
4. **Infra Failure**：CI 環境問題（機器、網路），重試即可

### Step 2：獲取 Log

```bash
# 從 Jenkins 取得 console log
curl -s "https://jenkins.example.com/job/wifi-bora-preflight/<build>/consoleText" \
    --user user:password \
    > preflight-log.txt

# 快速找到 FAIL 關鍵字
grep -E "FAIL|ERROR|error:" preflight-log.txt | head -30
```

### Step 3：決定處理方式

```
Build Failure   → 修改程式碼 → 重新 push → 自動重觸發
Test Failure    → 分析失敗原因 → 修改 or 更新 test
Flaky Test      → 留言說明，重新觸發，等待 +1
Infra Failure   → 聯繫 CI 維護人員 or 重新觸發
```

## Preflight 通過後

1. 確認 `Verified: +1` 出現在 Gerrit change 上
2. 等待 Code-Review: +2
3. 由 reviewer 或自己 submit（依團隊政策）
