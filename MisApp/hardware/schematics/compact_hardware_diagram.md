# MIS Smart Assistant - Compact Hardware Diagram

## Sơ đồ phần cứng nhỏ gọn cho báo cáo

### 1. Sơ đồ tổng thể (Report-Ready Format)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MIS SMART ASSISTANT - HARDWARE OVERVIEW                 │
└─────────────────────────────────────────────────────────────────────────────┘

                         ESP32-WROOM-32 DevKit V1
        ┌───────────────────────────────────────────────────────────┐
        │              [WiFi + Bluetooth A2DP]                     │
        │   ┌─────┐                                                │
        │   │ USB │   Dual-core 240MHz, 520KB RAM, 4MB Flash      │
        │   └─────┘                                                │
        │                                                          │
        │  GPIO Connections:                                       │
        │  ┌─────────────────────────────────────────────────────┐ │
VCC ────┤  │ Power & I/O Pins                          GPIO2   │ ├──► Status LED
GND ────┤  │                                                   │ │
        │  │ Input Devices:                            GPIO4   │ ├──► Red LED
Button──┤  │ • Button (GPIO33)                         GPIO13  │ ├──► Green LED  
Sound───┤  │ • KY-038 Sound (GPIO34)                   GPIO18  │ ├──► Yellow LED
        │  │                                                   │ │
        │  │ I2C Bus:                                  GPIO21  │ ├──► LCD SDA
        │  │ • LCD Display (0x27)                      GPIO22  │ ├──► LCD SCL
        │  │                                                   │ │
        │  │ I2S Audio:                                GPIO14  │ ├──► Audio SCK
        │  │ • Bluetooth A2DP Output                   GPIO15  │ ├──► Audio WS
        │  │ • 44.1kHz/16-bit Stereo                   GPIO25  │ ├──► Audio DATA
        │  └─────────────────────────────────────────────────────┘ │
        └───────────────────────────────────────────────────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
        ┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐
        │   Input Layer   │ │ Display Layer │ │  Audio Layer    │
        │                 │ │               │ │                 │
        │ ┌─────────────┐ │ │ ┌───────────┐ │ │ ┌─────────────┐ │
        │ │ KY-038      │ │ │ │ LCD 16x2  │ │ │ │ MAX98357A   │ │
        │ │ Sound       │ │ │ │ I2C       │ │ │ │ I2S Amp     │ │
        │ │ Sensor      │ │ │ │ 0x27      │ │ │ │ Class D     │ │
        │ └─────────────┘ │ │ └───────────┘ │ │ └─────────────┘ │
        │                 │ │               │ │        │        │
        │ ┌─────────────┐ │ │ ┌───────────┐ │ │        ▼        │
        │ │ Push Button │ │ │ │ LED Array │ │ │ ┌─────────────┐ │
        │ │ GPIO33      │ │ │ │ R/Y/G     │ │ │ │ Speaker     │ │
        │ │ Pull-up     │ │ │ │ Status    │ │ │ │ 4Ω 3W       │ │
        │ └─────────────┘ │ │ └───────────┘ │ │ └─────────────┘ │
        └─────────────────┘ └───────────────┘ └─────────────────┘

        ┌─────────────────────────────────────────────────────────────────────┐
        │                        SYSTEM FEATURES                             │
        ├─────────────────────────────────────────────────────────────────────┤
        │ • Voice Activation via Sound Sensor                                │
        │ • Manual Control via Push Button                                   │
        │ • Real-time Status Display on LCD                                  │
        │ • LED Status Indicators (Red/Yellow/Green)                         │
        │ • Bluetooth A2DP Audio Output                                      │
        │ • WiFi Connectivity for AI Services                                │
        │ • I2S Digital Audio (High Quality)                                 │
        └─────────────────────────────────────────────────────────────────────┘
```

### 2. Bảng kết nối pin (Pin Mapping Table)

| Component | ESP32 Pin | Function | Type | Description |
|-----------|-----------|----------|------|-------------|
| **Power** | VIN/3.3V | Power Supply | Power | 5V USB input → 3.3V system |
| **Ground** | GND | Common Ground | Ground | All components ground |
| **Sound Sensor** | GPIO34 | Digital Input | Input Only | KY-038 sound detection |
| **Push Button** | GPIO33 | Digital Input | I/O + Pull-up | Manual control trigger |
| **Status LED** | GPIO2 | Digital Output | I/O | Built-in + external LED |
| **Red LED** | GPIO4 | Digital Output | I/O | Error/Listening indicator |
| **Yellow LED** | GPIO18 | Digital Output | I/O | Processing indicator |
| **Green LED** | GPIO13 | Digital Output | I/O | Ready/Connected indicator |
| **LCD Display** | GPIO21 (SDA) | I2C Data | I/O | Display communication |
| **LCD Display** | GPIO22 (SCL) | I2C Clock | I/O | Display communication |
| **Audio Clock** | GPIO14 | I2S SCK | I/O | Audio bit clock |
| **Audio Select** | GPIO15 | I2S WS | I/O | Audio word select |
| **Audio Data** | GPIO25 | I2S SDOUT | I/O | Audio data output |

### 3. Component List (Bill of Materials)

| Category | Component | Quantity | Description |
|----------|-----------|----------|-------------|
| **Core** | ESP32 DevKit V1 | 1 | Main microcontroller |
| **Input** | KY-038 Sound Sensor | 1 | Sound detection |
| **Input** | 4-pin Push Button | 1 | Manual trigger |
| **Display** | LCD 16x2 I2C | 1 | Status display |
| **Display** | LED Red 5mm | 1 | Error indicator |
| **Display** | LED Yellow 5mm | 1 | Processing indicator |
| **Display** | LED Green 5mm | 1 | Ready indicator |
| **Audio** | MAX98357A I2S Amp | 1 | Audio amplifier |
| **Audio** | Speaker 4Ω 3W | 1 | Audio output |
| **Support** | Resistor 220Ω | 3 | LED current limiting |
| **Support** | Breadboard | 1 | Assembly platform |
| **Support** | Jumper Wires | 1 set | Connections |

### 4. Software Libraries Required

```cpp
// Arduino Libraries for ESP32
#include <WiFi.h>              // WiFi connectivity
#include <Wire.h>              // I2C communication
#include "ESP_I2S.h"           // I2S audio interface
#include "BluetoothA2DPSink.h" // Bluetooth A2DP audio
```

### 5. Key Technical Specifications

- **Microcontroller**: ESP32-WROOM-32 (240MHz dual-core)
- **Memory**: 520KB SRAM, 4MB Flash
- **Connectivity**: WiFi 802.11b/g/n, Bluetooth 4.2/5.0
- **Audio**: I2S 44.1kHz/16-bit stereo, Bluetooth A2DP
- **Display**: 16x2 LCD with I2C backpack (0x27)
- **Input**: Sound sensor + manual button
- **Power**: 5V USB input, 3.3V system operation
- **Current**: ~500mA typical operation

### 6. System Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Physical  │    │   Hardware  │    │  Software   │
│   Layer     │ ←→ │   Layer     │ ←→ │   Layer     │
│             │    │             │    │             │
│ • User      │    │ • ESP32     │    │ • Arduino   │
│ • Voice     │    │ • Sensors   │    │ • Python    │
│ • Sound     │    │ • Display   │    │ • AI APIs   │
│ • Visual    │    │ • Audio     │    │ • Bluetooth │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

**Note**: This compact diagram is optimized for inclusion in reports and presentations. It shows all essential connections and components while maintaining readability in smaller formats.
