# Test: Memory Slim Flow

請分析目前 Wi-Fi Bora 的 ROM/RAM footprint。

我需要了解：
1. 目前 ROM 和 RAM 的整體用量分佈
2. 各 section（.text, .rodata, .data, .bss）的大小
3. 佔用空間最大的前 10 個 function/symbol
4. 有哪些可以優化精簡的建議

請使用 memslim 分析流程來完成這個任務。
