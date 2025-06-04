# Simple Hardware Diagram for Report Screenshots

## MIS Smart Assistant - Hardware Connections

```
                    ESP32-WROOM-32 DEVKIT V1
    ┌───────────────────────────────────────────────────────┐
    │                                                       │
    │  [WiFi + Bluetooth]     Dual-Core 240MHz             │
    │  ┌─────┐                                              │
VCC │  │ USB │                                        GPIO2 ├─► Status LED
GND │  └─────┘                                              │
    │                                               GPIO4  ├─► Red LED
    │  Input Pins:                                  GPIO13 ├─► Green LED
    │  ┌────────────────────────┐                  GPIO18 ├─► Yellow LED
    │  │ GPIO33 ◄─ Button       │                          │
    │  │ GPIO34 ◄─ Sound Sensor │                          │
    │  └────────────────────────┘                  GPIO21 ├─► LCD SDA
    │                                               GPIO22 ├─► LCD SCL
    │  Audio Output (I2S):                                 │
    │  ┌────────────────────────┐                  GPIO14 ├─► Audio SCK
    │  │ GPIO14 ─► Bit Clock    │                  GPIO15 ├─► Audio WS
    │  │ GPIO15 ─► Word Select  │                  GPIO25 ├─► Audio Data
    │  │ GPIO25 ─► Data Out     │                          │
    │  └────────────────────────┘                          │
    └───────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │   INPUTS    │  │   DISPLAY   │  │    AUDIO    │
    │             │  │             │  │             │
    │ KY-038      │  │ LCD 16x2    │  │ MAX98357A   │
    │ Sound       │  │ I2C (0x27)  │  │ I2S Amp     │
    │ Sensor      │  │             │  │ + Speaker   │
    │             │  │ LED Status  │  │ 4Ω 3W       │
    │ Push        │  │ R / Y / G   │  │             │
    │ Button      │  │             │  │ Bluetooth   │
    │ (GPIO33)    │  │             │  │ A2DP Audio  │
    └─────────────┘  └─────────────┘  └─────────────┘

KEY CONNECTIONS:
├─ Power: 5V USB → ESP32 VIN → 3.3V Internal
├─ I2C Bus: GPIO21(SDA) + GPIO22(SCL) → LCD Display
├─ Digital Input: GPIO34 → KY-038, GPIO33 → Button
├─ LED Output: GPIO2,4,13,18 → Status LEDs (via 220Ω)
└─ I2S Audio: GPIO14,15,25 → MAX98357A → Speaker

SYSTEM FEATURES:
• Voice activation via sound detection
• Manual control via push button  
• Real-time LCD status display
• Color-coded LED indicators
• High-quality I2S audio output
• Bluetooth A2DP audio streaming
• WiFi connectivity for AI services
```

## Simplified Block Diagram

```
USER INPUT          ESP32 CORE          OUTPUT DEVICES
    │                   │                     │
    ▼                   ▼                     ▼
┌─────────┐        ┌─────────┐          ┌─────────┐
│ Voice   │  ───►  │ GPIO34  │          │ GPIO2   │  ───► Status LED
│ (KY-038)│        │ (Input) │          │ GPIO4   │  ───► Red LED
└─────────┘        └─────────┘          │ GPIO13  │  ───► Green LED
                                        │ GPIO18  │  ───► Yellow LED
┌─────────┐        ┌─────────┐          └─────────┘
│ Button  │  ───►  │ GPIO33  │          
│ Manual  │        │(Pull-up)│          ┌─────────┐
└─────────┘        └─────────┘          │ GPIO21  │  ───► LCD SDA
                                        │ GPIO22  │  ───► LCD SCL
              ┌─────────────────┐       └─────────┘
              │   WiFi Module   │
              │   Bluetooth     │       ┌─────────┐
              │   A2DP Sink     │       │ GPIO14  │  ───► I2S SCK
              └─────────────────┘       │ GPIO15  │  ───► I2S WS
                                        │ GPIO25  │  ───► I2S DATA
                                        └─────────┘
```

## Component List Summary

| Component | Quantity | Function |
|-----------|----------|----------|
| ESP32 DevKit V1 | 1 | Main controller |
| KY-038 Sound Sensor | 1 | Voice detection |
| Push Button 4-pin | 1 | Manual control |
| LCD 16x2 I2C | 1 | Status display |
| LED Red/Yellow/Green | 3 | Status indicators |
| MAX98357A I2S Amp | 1 | Audio amplifier |
| Speaker 4Ω 3W | 1 | Audio output |
| Resistor 220Ω | 3 | LED protection |
| Breadboard + Wires | 1 set | Assembly |

**Power Requirements**: 5V USB (500mA typical)
**Audio Quality**: 44.1kHz/16-bit stereo I2S
**Connectivity**: WiFi 802.11n + Bluetooth 4.2/5.0
