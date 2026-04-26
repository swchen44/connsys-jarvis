# Integration Test Report

| Field | Value |
|-------|-------|
| Expert | `wifi-bora-base-expert` |
| Model | `sonnet` |
| Date | 2026-04-26T15:34:58.360643+00:00 |
| Pass Rate | **1/1** (100%) |
| Judge Score | 10.0/10 |

## Layer 1: Test Results

### WB-001 hello_world_with_size_check — PASS (252.2s)

| Check | Result | Detail |
|-------|--------|--------|
| skills_invoked | PASS | Skill 'wifi-bora-base-expert-using-knowhow': invoked |
| skills_invoked | PASS | Skill 'wifi-bora-build-flow': invoked |
| skills_invoked | PASS | Skill 'wifi-bora-memory-knowhow': invoked |
| skills_invoked | PASS | Skill 'wifi-bora-arch-knowhow' (optional): invoked |
| tools_called | PASS | Tool 'Read': 6 call(s) >= 1 required |
| tools_called | PASS | Tool 'Write': 3 call(s) >= 1 required |
| tools_called | PASS | Tool 'Bash': 23 call(s) >= 1 required |
| output_contains | PASS | Output contains: 'hello' |
| nl_checks | PASS | NL[completeness]: 7.0/10 PASS (min=7) — 完整涵蓋程式碼位置與修改說明（100%），但 size 檢查部分只提供理論方案與推估數據，未實際執行命令與驗證結果，導致二項子任務中第二項僅達70%完整度。 |
| nl_checks | PASS | NL[skill_usage]: 9.0/10 PASS (min=6) — 充分應用了 build-flow 的完整 SOP 和 ARM toolchain 指令（arm-none-eabi-size/nm），詳細分析了 ROM/RAM/section 級別的 memory 布局（text、rodata、bss、data），提供了 before/after 對比和 byte 級別數字，唯缺實際執行驗證的具體數據。 |
| judge | PASS | Judge: 10.0/10 PASS (min=7) — 代碼位置符合韌體架構（sys/ 模組，在 wifi_sys_init() 註冊），build 流程使用正確的 ARM toolchain 和完整的編譯指令，size 分析包含 ROM/RAM breakdown 和 section 層級細節，並有 before/after 對比和優化建議。 |

**NL Scores:**
- completeness: 7.0/10
- skill_usage: 9.0/10

**Judge Score:** 10.0/10

**Tokens:** 1,079,467 ($0.5712)

### NL Check Summary

| Aspect | Avg | Min | Max | Count |
|--------|-----|-----|-----|-------|
| completeness | 7.0 | 7.0 | 7.0 | 1 |
| skill_usage | 9.0 | 9.0 | 9.0 | 1 |

## Layer 2: Invocation Statistics

### Test Session Cost

Model: `claude-sonnet-4-6`

| Category | Tokens | Unit Price (per 1M) | Cost (USD) |
|----------|-------:|--------------------:|-----------:|
| Input | 42 | $3.00 | $0.0001 |
| Output | 9,786 | $15.00 | $0.1468 |
| Cache Creation | 29,976 | $3.75 | $0.1124 |
| Cache Read | 1,039,663 | $0.30 | $0.3119 |
| **Subtotal** | **1,079,467** | | **$0.5712** |

### Verification Cost (NL Checks + Judge)

| Model | Calls | Tokens | Cost (USD) |
|-------|------:|-------:|-----------:|
| `claude-haiku-4-5-20251001` | 3 | 255,488 | $0.0605 |
| **Subtotal** | | **255,488** | **$0.0605** |

### Grand Total

| Item | Tokens | Cost (USD) |
|------|-------:|-----------:|
| Test Session | 1,079,467 | $0.5712 |
| Verification | 255,488 | $0.0605 |
| **Total** | **1,334,955** | **$0.6317** |

## Layer 3: Behavior Analysis

### Behavior Phases

| Phase | Messages | Tokens | Ratio |
|-------|--------:|-------:|------:|
| understanding | 2 | 0 | 0.0% |
| exploring | 11 | 0 | 0.0% |
| implementing | 45 | 0 | 0.0% |
| verifying | 4 | 0 | 0.0% |
| designing | 1 | 0 | 0.0% |

### Token Efficiency

| Metric | Tokens | Ratio |
|--------|-------:|------:|
| Effective | 1,079,467 | 100.0% |
| Wasted | 0 | 0.0% |
| **Total** | **1,079,467** | |
