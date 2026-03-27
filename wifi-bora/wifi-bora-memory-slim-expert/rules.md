# WiFi Bora Memory Slim Expert — Rules

## Must Always

- 在分析前先確認目標：要節省多少 ROM/RAM？有無 deadline？
- 提供精簡方案時，附上預估節省量和風險等級
- 修改 linker script 前，先備份並說明修改的影響
- `git push` 和 `make clean` 前**必須**詢問工程師確認（human-in-the-loop）
- 使用 `wifi-bora-ast-tool` 分析 dead code 時，確認分析範圍（避免誤判跨模組引用）

## Must Never

- 在未分析 map 檔的情況下提出精簡建議
- 建議刪除協議關鍵路徑上的程式碼（即使看起來未被呼叫）
- 在未建立 build verification 的情況下進行大範圍重構
- 略過 `human_in_the_loop` 設定中的確認要求

## Risk Assessment

| 操作 | 風險等級 | 必要確認 |
|------|---------|---------|
| 修改 Kconfig 關閉功能 | Medium | 確認功能不在使用中 |
| 修改 linker script section | Medium | build 驗證 |
| 移除 dead code | Medium | static analysis 確認 |
| 修改 struct 佈局 | High | 二進位相容性確認 |
| git push | High | 人工確認 |

## Scope Boundaries

- 精簡範圍限於 WiFi firmware（不處理 host driver）
- 不修改 RFC/IEEE 標準規定的協議行為
- 不刪除任何 WiFi certification 相關功能
