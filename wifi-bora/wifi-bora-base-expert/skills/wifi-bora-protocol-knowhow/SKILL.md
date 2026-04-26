---
name: wifi-bora-protocol-knowhow
description: "802.11 協議在 WiFi Bora 韌體中的實作細節，涵蓋 MAC、MLME、data path"
version: "1.0.0"
---

# WiFi Bora Protocol Knowhow

## 協議棧架構

WiFi Bora 韌體實作 IEEE 802.11 協議棧，分層如下：

```
┌─────────────────────────────┐
│         MLME Layer          │  管理層：Association, Auth, Scan
├─────────────────────────────┤
│         MAC Layer           │  存取控制：EDCA, TXOP, BA
├─────────────────────────────┤
│       MAC-PHY Interface     │  TXVECTOR, RXVECTOR
├─────────────────────────────┤
│         PHY Layer           │  調變解調（OFDM, DSSS）
└─────────────────────────────┘
```

## 關鍵協議流程

### Station Association 流程

1. **Scan**：主動掃描（Probe Req/Rsp）或被動掃描（Beacon 監聽）
2. **Authentication**：Open System 或 SAE（WPA3）
3. **Association**：能力協商（HT/VHT/HE Capabilities）
4. **4-way Handshake**：PMK → PTK 金鑰協商（WPA2/WPA3）

### Data Path

**TX Path：**
```
Host → SDIO/PCIe → MAC TX Queue → EDCA Scheduler → PHY TX
```

**RX Path：**
```
PHY RX → A-MPDU Reorder Buffer → MAC RX Queue → Host
```

### Block ACK (BA) 機制

- `ADDBA Request/Response`：建立 BA session
- Window Size：典型 64 個 MPDU
- Immediate BA：每個 TXOP 結束後立即回應

## 常見 Debug 場景

### TX 卡住（TX Stall）

1. 檢查 TX Queue 狀態（`dump txq`）
2. 確認 EDCA 參數是否被 AP 修改
3. 檢查 BA session 是否正常（timeout/reset）
4. 查看 PHY TX 狀態（busy/idle）

### RX 遺包（RX Drop）

1. 確認 RSSI 是否足夠（>-70 dBm 為佳）
2. 檢查 Reorder Buffer 是否溢出
3. 確認 MPDU 格式是否正確（FCS check）

## 支援的 802.11 版本

| 版本 | 頻段 | 調變 | 最大速率 |
|------|------|------|---------|
| 802.11b | 2.4 GHz | DSSS/CCK | 11 Mbps |
| 802.11g | 2.4 GHz | OFDM | 54 Mbps |
| 802.11n | 2.4/5 GHz | HT OFDM | 600 Mbps |
| 802.11ac | 5 GHz | VHT OFDM | 6.9 Gbps |
| 802.11ax | 2.4/5/6 GHz | HE OFDM | 9.6 Gbps |
