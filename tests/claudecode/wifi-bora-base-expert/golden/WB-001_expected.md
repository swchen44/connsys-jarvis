# WB-001 Expected Output Reference

## 1. Hello World 程式碼

- 在韌體適當的模組位置（如 app/ 或 user/ 目錄）建立 hello world 原始碼
- 使用 printf / log API 輸出 "hello world"
- 修改 Makefile 或 build config 將新檔案加入編譯

## 2. Build 流程

- 使用正確的 ARM toolchain（arm-none-eabi-gcc）
- 執行 make 或相應的 build 指令
- Build 成功產出 binary（.bin / .elf）

## 3. Size 分析

- 使用 arm-none-eabi-size、nm、readelf 等工具分析 binary
- 報告 ROM（.text + .rodata）和 RAM（.data + .bss）使用量
- 與 hello world 加入前的 baseline 比較，指出增量
- 列出主要 symbol 的 size 分佈
