---
name: wifi-bora-build-flow
description: "WiFi Bora firmware build 流程 SOP，包含環境設定、編譯指令、常見錯誤排除"
version: "1.0.0"
---

# WiFi Bora Build Flow

## 環境設定

### 必要工具

```bash
# Toolchain：ARM Cortex-M 裸機編譯器
arm-none-eabi-gcc --version  # 需要 >= 10.x

# Build 工具
make --version               # GNU Make >= 4.x
python3 --version            # Python 3.8+（用於 config 生成腳本）
```

### 環境變數設定

```bash
export CROSS_COMPILE=arm-none-eabi-
export ARCH=arm
export WIFI_BORA_CHIP=bora_a0   # 或 bora_b0
export BUILD_TYPE=release        # 或 debug
```

## Build 流程

### Step 1：選擇 Board Config

```bash
# 列出可用 config
ls configs/

# 套用 config
make BOARD=wifi_bora_evb defconfig
```

### Step 2：（選用）自訂 Kconfig

```bash
make menuconfig
```

重要 Kconfig 選項：

| 選項 | 說明 |
|------|------|
| `CONFIG_WIFI_11AX` | 啟用 802.11ax (Wi-Fi 6) |
| `CONFIG_WIFI_P2P` | 啟用 P2P (Wi-Fi Direct) |
| `CONFIG_WIFI_DEBUG` | 啟用 debug log |
| `CONFIG_OPTIMIZE_SIZE` | 啟用大小優化（-Os） |

### Step 3：編譯

```bash
# 完整 build
make -j$(nproc)

# 只編譯特定模組
make -j$(nproc) mac/

# Verbose mode（看完整指令）
make V=1
```

### Step 4：產出物

```
build/
├── wifi_bora.elf       ← 含 debug 符號的 ELF
├── wifi_bora.bin       ← 下載用 binary
├── wifi_bora.map       ← Linker map 檔
└── wifi_bora.hex       ← Intel HEX 格式
```

## 常見 Build 錯誤

### Linker Error：`section overflow`

```
region `RAM' overflowed by 1234 bytes
```

**原因**：RAM 使用量超出 linker script 定義的大小
**解法**：
1. 分析 `.map` 檔找出最大 section
2. 考慮啟用 `CONFIG_OPTIMIZE_SIZE`
3. 或切換到 `wifi-bora-memory-slim-expert` 進行系統分析

### Linker Error：`undefined reference`

**原因**：缺少必要 object file 或 library
**解法**：確認 Kconfig 選項是否啟用對應模組

### Toolchain 版本不符

```
error: unrecognized command line option '-mfp16-format=ieee'
```

**解法**：升級 arm-none-eabi-gcc 到 10.x 以上

## Clean Build

```bash
# 清除所有 build 產物
make clean

# 只清除特定模組
make clean -C mac/

# 完整重置（包含 .config）
make mrproper
```
