---
name: wifi-bora-arch-knowhow
description: "WiFi Bora 韌體架構概覽，包含模組劃分、task 架構、IPC 機制與 code 導覽指南"
version: "1.0.0"
domain: wifi-bora
type: knowhow
scope: wifi-bora-base-expert
tags: [wifi, bora, architecture, firmware, task, IPC]
---

# WiFi Bora Architecture Knowhow

## 韌體模組架構

```
wifi-bora/
├── mac/           ← MAC 層核心（EDCA, BA, Frame 處理）
├── mlme/          ← 管理層（Scan, Auth, Assoc, P2P）
├── phy/           ← PHY 抽象層（TX/RX 向量轉換）
├── hal/           ← Hardware Abstraction Layer
├── os/            ← OS 抽象（task, mutex, timer, memory）
├── sys/           ← 系統初始化與 boot 流程
├── util/          ← 共用工具函式（bit ops, list, queue）
└── platform/      ← 平台相關（register map, clock, power）
```

## Task 架構

WiFi Bora 使用 RTOS（FreeRTOS based）多工架構：

| Task | 優先級 | 職責 |
|------|--------|------|
| `wifi_rx_task` | High | RX frame 處理，A-MPDU reorder |
| `wifi_tx_task` | High | TX frame 排程，EDCA dequeue |
| `wifi_mlme_task` | Medium | 管理幀處理，狀態機驅動 |
| `wifi_timer_task` | Medium | 協議 timer 管理（BA timeout, scan timer） |
| `wifi_sys_task` | Low | 系統維護，統計收集 |

## IPC 機制

### Task 間通訊

```c
/* 訊息佇列（最常用） */
wifi_mq_send(mq_handle, &msg, sizeof(msg));
wifi_mq_recv(mq_handle, &msg, WAIT_FOREVER);

/* Event bits（多對一通知） */
wifi_event_set(event_group, EVENT_RX_DONE);
wifi_event_wait(event_group, EVENT_RX_DONE | EVENT_TX_DONE, pdTRUE, WAIT_FOREVER);
```

### Host Interface

- **SDIO**：`sdio_rx_callback()` → `wifi_rx_task`
- **PCIe**：DMA 完成中斷 → `wifi_rx_task`

## 啟動流程

```
boot_rom → loader → firmware_main()
    ├── hw_init()          ← 硬體初始化
    ├── os_init()          ← RTOS 初始化
    ├── wifi_sys_init()    ← WiFi 系統初始化
    ├── task 建立          ← 所有 WiFi task 啟動
    └── wifi_ready_notify() ← 通知 host 韌體就緒
```

## Code 導覽指南

### 找到協議相關程式碼

- Association：`mlme/sta_mgmt.c` → `wifi_mlme_assoc_req()`
- TX scheduling：`mac/edca.c` → `mac_edca_dequeue()`
- RX reorder：`mac/ba_rx.c` → `mac_ba_rx_reorder()`

### 找到 HAL 暫存器存取

```c
/* 所有暫存器操作透過 HAL */
hal_write32(REG_MAC_TX_CTRL, value);
val = hal_read32(REG_MAC_RX_STATUS);
```

暫存器定義在 `platform/<chip>/reg_map.h`。
