# WB-001 Judge Rubric

評分標準（滿分 10 分）：

## 程式碼位置 (3 分)
- 3: hello world 放在韌體合理位置，有 task/thread 註冊或 init 函式呼叫
- 2: 放在合理位置但缺少 init 註冊
- 1: 放在不合理的位置（如直接修改 main）
- 0: 沒有寫程式碼

## Build 流程 (3 分)
- 3: 使用正確的 ARM toolchain，修改了 Makefile/build config，build 成功
- 2: 使用正確的 toolchain 但缺少 Makefile 修改
- 1: 有嘗試 build 但指令有誤
- 0: 沒有 build 步驟

## Size 分析 (2 分)
- 2: 分析包含 ROM 和 RAM，有 section 或 symbol 層級的細節
- 1: 只有總 size 數字，缺少 section 分析
- 0: 沒有 size 分析

## 分析深度 (2 分)
- 2: 比較 baseline 前後差異，有具體的優化建議
- 1: 有數字但沒有前後比較
- 0: 沒有深入分析
