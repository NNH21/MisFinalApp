# 2. TRIỂN KHAI PHẦN CỨNG

## 2.1. TỔNG QUAN LINH KIỆN PHẦN CỨNG

MIS Smart Assistant sử dụng vi điều khiển ESP32 làm trung tâm xử lý chính, kết hợp với các module cảm biến và thiết bị hiển thị để tạo thành một hệ thống IoT hoàn chỉnh. Hệ thống phần cứng được thiết kế với nguyên tắc:

- **Tính ổn định**: Đảm bảo hoạt động liên tục và ổn định
- **Dễ lắp ráp**: Sử dụng breadboard và jumper wires để dễ dàng thực hiện
- **Chi phí thấp**: Sử dụng các linh kiện phổ biến và giá thành hợp lý
- **Khả năng mở rộng**: Có thể bổ sung thêm cảm biến và thiết bị

### Kiến trúc phần cứng tổng thể

```
┌─────────────────────────────────────────────┐
│                 ESP32 DevKit V1             │
│  ┌─────────────────────────────────────────┐│
│  │        Dual-core 240MHz CPU            ││
│  │        520KB RAM + 4MB Flash           ││
│  │        Wi-Fi + Bluetooth               ││
│  │        32 GPIO pins                    ││
│  └─────────────────────────────────────────┘│
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
        ▼         ▼         ▼
   ┌──────────┐ ┌─────┐ ┌──────────┐
   │ Sensors  │ │LEDs │ │ Display  │
   │          │ │     │ │          │
   │ KY-038   │ │RGB  │ │LCD 16x2  │
   │ Button   │ │LEDs │ │I2C       │
   └──────────┘ └─────┘ └──────────┘
```

## 2.2. BẢNG CHI TIẾT LINH KIỆN

### A. Microcontroller và linh kiện chính

| STT | Tên linh kiện | Mô tả chi tiết | Số lượng | Chức năng |
|-----|---------------|----------------|----------|-----------|
| 1 | **ESP32 DevKit V1** | Vi điều khiển 32-bit dual-core, WiFi + Bluetooth, 32 GPIO pins | 1 | Trung tâm xử lý chính, kết nối Wi-Fi, xử lý tín hiệu |
| 2 | **Breadboard** | Breadboard 830 holes (half-size) | 1 | Nền tảng lắp ráp mạch điện |
| 3 | **Jumper Wires** | Dây jumper Male-to-Male, Female-to-Female | 1 set | Kết nối các linh kiện |
| 4 | **Điện trở 220Ω** | Điện trở carbon 1/4W, tolerance 5% | 4 | Hạn chế dòng điện cho LED |
| 5 | **Cáp USB Type-C** | Cáp USB-A to Type-C, dài 1-2m | 1 | Cấp nguồn và programming |

### B. Thiết bị đầu vào (Input Devices)

| STT | Tên linh kiện | Thông số kỹ thuật | Số lượng | Chức năng |
|-----|---------------|-------------------|----------|-----------|
| 6 | **Cảm biến âm thanh KY-038** | - Điện áp: 3.3V-5V<br>- Độ nhạy: điều chỉnh được<br>- Output: Digital (DO), Analog (AO)<br>- Kích thước: 32 x 17mm | 1 | Phát hiện âm thanh để kích hoạt voice control |
| 7 | **Nút nhấn 4 chân** | - Loại: Tactile Push Button<br>- Điện áp: 3.3V<br>- Kích thước: 6x6x5mm<br>- Life cycle: 100,000 lần nhấn | 1 | Kích hoạt microphone thủ công, điều khiển hệ thống |

**Chi tiết cảm biến KY-038:**
- **Microphone**: Electret condenser microphone
- **LM393 comparator**: So sánh tín hiệu analog với ngưỡng
- **Potentiometer**: Điều chỉnh độ nhạy (sensitivity)
- **LED indicator**: Báo hiệu khi phát hiện âm thanh
- **Chân kết nối**: VCC, GND, DO (Digital Out), AO (Analog Out)

### C. Thiết bị đầu ra (Output Devices)

| STT | Tên linh kiện | Thông số kỹ thuật | Số lượng | Chức năng |
|-----|---------------|-------------------|----------|-----------|
| 8 | **Màn hình LCD I2C 16x2** | - Kích thước: 16 ký tự x 2 dòng<br>- Giao tiếp: I2C (SDA, SCL)<br>- Điện áp: 5V<br>- Địa chỉ I2C: 0x27 hoặc 0x3F<br>- Backlight: Blue với ký tự trắng | 1 | Hiển thị trạng thái hệ thống, thông tin thời gian thực |
| 9 | **LED RGB - Đỏ** | - Điện áp: 2.0-2.2V<br>- Dòng điện: 20mA<br>- Wavelength: 620-625nm<br>- Kích thước: 5mm | 1 | Hiển thị trạng thái "Listening" hoặc "Error" |
| 10 | **LED RGB - Vàng** | - Điện áp: 2.0-2.2V<br>- Dòng điện: 20mA<br>- Wavelength: 585-595nm<br>- Kích thước: 5mm | 1 | Hiển thị trạng thái "Processing" hoặc "Waiting" |
| 11 | **LED RGB - Xanh lá** | - Điện áp: 3.0-3.2V<br>- Dòng điện: 20mA<br>- Wavelength: 515-525nm<br>- Kích thước: 5mm | 1 | Hiển thị trạng thái "Connected" hoặc "Success" |
| 12 | **LED trạng thái** | - LED đỏ 3mm<br>- Điện áp: 2.0-2.2V<br>- Dòng điện: 20mA | 1 | Hiển thị trạng thái power và system status |
| 13 | **MAX98357A I2S Audio Amplifier** | - Điện áp: 3.3V-5V<br>- Công suất: 3.2W Class D<br>- Giao tiếp: I2S Digital<br>- Tần số: 8kHz-96kHz<br>- SNR: 100dB | 1 | Khuếch đại âm thanh từ ESP32 Bluetooth A2DP |
| 14 | **Speaker 4Ω 3W** | - Trở kháng: 4Ω<br>- Công suất: 3W<br>- Tần số: 100Hz-20kHz<br>- Kích thước: 40mm | 1 hoặc 2 | Phát âm thanh phản hồi từ AI Assistant |

**Cấu hình I2S Audio System:**
- **I2S Protocol**: Digital audio interface cho chất lượng âm thanh cao
- **Bluetooth A2DP**: Advanced Audio Distribution Profile cho streaming
- **Sample Rate**: 44.1kHz stereo 16-bit (CD quality)
- **Latency**: < 100ms cho real-time interaction
- **Audio Pipeline**: ESP32 → I2S → MAX98357A → Speaker

**Ý nghĩa màu sắc LED:**
- **Đỏ**: Lỗi, mất kết nối, chế độ lắng nghe
- **Vàng**: Đang xử lý, chờ phản hồi từ AI
- **Xanh**: Kết nối thành công, sẵn sàng
- **LED trạng thái**: Nhấp nháy khi có hoạt động

### D. Linh kiện hỗ trợ (Supporting Components)

| STT | Tên linh kiện | Thông số | Số lượng | Mục đích |
|-----|---------------|----------|----------|----------|
| 13 | **Nguồn USB 5V** | Adapter 5V/2A hoặc power bank | 1 | Cấp nguồn ổn định cho hệ thống |
| 14 | **Tụ điện 100µF** | Electrolytic capacitor 16V | 2 | Lọc nhiễu nguồn, ổn định điện áp |
| 15 | **Tụ điện 0.1µF** | Ceramic capacitor | 4 | Bypass capacitor cho IC |
| 16 | **Jumper Wires (Female-Female)** | Dây jumper 20cm, nhiều màu | 1 set | Kết nối ESP32 với I2S amplifier |
| 17 | **Connector 3.5mm Jack** | Audio connector (optional) | 1 | Kết nối tai nghe/loa ngoài |

**Cấu hình Audio Output Options:**
1. **Built-in Speaker**: MAX98357A + 4Ω speaker trực tiếp
2. **External Audio**: 3.5mm jack cho headphones/external speakers  
3. **Bluetooth Speaker**: Kết nối với loa Bluetooth external (alternative)

**Lưu ý về nguồn điện:**
- ESP32 hoạt động ở 3.3V nhưng có thể cấp nguồn qua USB 5V
- LCD I2C cần 5V để hoạt động tối ưu
- Tổng công suất tiêu thụ: khoảng 500mA ở chế độ hoạt động bình thường

## 2.3. SƠ ĐỒ KẾT NỐI PHẦN CỨNG

### 2.3.0. Sơ đồ kết nối nhỏ gọn (Compact Hardware Diagram)

```
                    ESP32-WROOM-32 DevKit V1
        ┌─────────────────────────────────────────────┐
        │                 [WiFi + Bluetooth]          │
        │   ┌─────┐  Core Components & Audio:         │
        │   │ USB │                                   │
        │   └─────┘                                   │
        │                                             │
VCC ────┤ VIN                                   GPIO2 ├──► LED Status (Built-in + External)
GND ────┤ GND                                         │
        │                                    GPIO4  ──┼──► LED Đỏ (Red)
Button ─┤ GPIO33                             GPIO18 ──┼──► LED Vàng (Yellow)  
Sound ──┤ GPIO34                             GPIO13 ──┼──► LED Xanh (Green)
        │                                             │
        │        I2C Bus:                    GPIO21 ──┼──► SDA (LCD)
        │                                    GPIO22 ──┼──► SCL (LCD)
        │                                             │
        │        I2S Audio Output:           GPIO14 ──┼──► I2S SCK (Bit Clock)
        │                                    GPIO15 ──┼──► I2S WS (Word Select)
        │                                    GPIO25 ──┼──► I2S SDOUT (Data Out)
        │                                             │
        └─────────────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
        │  KY-038     │    │ LCD 16x2 I2C │    │ MAX98357A   │
        │ Sound       │    │ (PCF8574)    │    │ I2S Amp +   │
        │ Sensor      │    │ Addr: 0x27   │    │ Speaker     │
        └─────────────┘    └──────────────┘    └─────────────┘

    ┌─────────────────────────────────────────────────────────┐
    │                Status LED Indicators                     │
    │  ┌─────────┐  ┌─────────────┐  ┌──────────────────┐     │
    │  │   Đỏ    │  │    Vàng     │  │      Xanh       │     │
    │  │(Listen) │  │ (Response/  │  │ (Connected/BT)   │     │
    │  │         │  │  Audio)     │  │                  │     │
    │  └─────────┘  └─────────────┘  └──────────────────┘     │
    └─────────────────────────────────────────────────────────┘
```

### 2.3.1. Sơ đồ kết nối tổng thể chi tiết

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                        MIS SMART ASSISTANT - HARDWARE DIAGRAM                  │
└────────────────────────────────────────────────────────────────────────────────┘

                         ╔══════════════════════════════════╗
                         ║          ESP32 DevKit V1         ║
                         ║  ┌─────┬─────┬─────┬─────┬─────┐ ║
                         ║  │3V3  │GND  │D21  │D22  │D34  │ ║
                         ║  │     │     │SDA  │SCL  │ IN  │ ║
                         ║  └──┬──┴──┬──┴──┬──┴──┬──┴──┬──┘ ║
                         ╚═════┼═════┼═════┼═════┼═════┼════╝
                               │     │     │     │     │
                  ┌────────────┼─────┼─────┼─────┼─────┼─────────────┐
                  │            │     │     │     │     │             │
                  │      ┌─────▼─┐   │     │     │     │             │
                  │      │ VCC   │   │     │     │     │             │
                  │ ┌────┤ GND   ├───┼─────┘     │     │             │
                  │ │    │ SDA   ├───┼───────────┘     │             │
                  │ │    │ SCL   ├───┼─────────────────┘             │
                  │ │    └───────┘   │                               │
    ┌─────────────▼─┴──┐              │                               │
    │   LCD I2C 16x2   │              │                               │
    │ ┌─────────────┐  │              │                               │
    │ │MIS Assistant│  │        ┌─────▼─────────────────────────┐     │
    │ │Ready !!!    │  │        │      KY-038 Sound Sensor      │     │
    │ └─────────────┘  │        │  ┌─────┬─────┬─────┬─────┐   │     │
    └──────────────────┘        │  │VCC  │GND  │ AO  │ DO  │   │     │
                                │  └──┬──┴──┬──┴─────┴──┬──┘   │     │
                                └─────┼─────┼───────────┼──────┘     │
                                      │     │           │            │
                                   ┌──▼─┐   │           │            │
                                   │3V3 │   │           │            │
                                   │GND ├───┘           │            │
                                   └────┘               │            │
                                                        │            │
                                              ┌─────────▼──────────┐ │
                                              │     GPIO34         │ │
                                              │   (Input Only)     │ │
                                              └────────────────────┘ │
                                                                     │
        ╔══════════════════════════════════════════════════════════════════════════╗
        ║                           ESP32 GPIO PINS                               ║
        ║  ┌─────┬─────┬─────┬─────────────────────────────────────────────────┐  ║
        ║  │ D2  │ D4  │D18  │ D33                                             │  ║
        ║  │     │     │     │                                                 │  ║
        ║  └──┬──┴──┬──┴──┬──┴──┬──────────────────────────────────────────────┘  ║
        ╚═════┼═════┼═════┼═════┼═══════════════════════════════════════════════════╝
              │     │     │     │
              │     │     │     │
    ┌─────────▼─┐ ┌─▼─┐ ┌─▼─┐   │   ┌─────────────────────────────┐
    │   [220Ω]  │ │220│ │220│   │   │       Push Button           │
    │     ┌─────┘ │Ω  │ │Ω  │   │   │    ┌─────┬─────────────┐    │
    │  ┌──▼───┐   │   │ │   │   │   │    │  1  │      3      │    │
    │  │ 🟢   │   │   │ │   │   │   │    │     │             │    │
    │  │GREEN │   │   │ │   │   │   │    └──┬──┴──────┬──────┘    │
    │  │ LED  │   │   │ │   │   │   │       │         │           │
    │  └──┬───┘   │   │ │   │   │   └───────┼─────────┼───────────┘
    │     │    ┌──▼─┐ │ │   │   │           │         │
    │  ┌──▼──┐ │🔴  │ │ │   │   │        ┌──▼──┐      │
    │  │ GND │ │RED │ │ │   │   │        │GPIO │      │
    │  └─────┘ │LED │ │ │   │   │        │ 33  │      │
    │          └──┬─┘ │ │   │   │        └─────┘      │
    │          ┌──▼─┐ │ │   │   │                     │
    │          │GND │ │ │   │   │                  ┌──▼──┐
    │          └────┘ │ │   │   │                  │ GND │
    │                 │ │   │   │                  └─────┘
    │              ┌──▼─▼─┐ │   │
    │              │ 🟡   │ │   │
    │              │YELLOW│ │   │
    │              │ LED  │ │   │
    │              └──┬───┘ │   │
    │              ┌──▼───┐ │   │
    │              │ GND  │ │   │
    │              └──────┘ │   │
    │                       │   │
    │                    ┌──▼─┐ │
    │                    │🔵  │ │  
    │                    │BLUE│ │  
    │                    │LED │ │  
    │                    └──┬─┘ │  
    │                    ┌──▼─┐ │  
    │                    │GND │ │  
    │                    └────┘ │  
    └───────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LED STATUS INDICATORS                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 🟢 GREEN LED (GPIO2)   → Connected/Ready State                                │
│ 🔴 RED LED (GPIO4)     → Listening/Error State                                │
│ 🟡 YELLOW LED (GPIO18) → Processing/Waiting State                             │
│ 🔵 BLUE LED (Built-in) → System Status/Activity Indicator                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3.2. Sơ đồ kết nối chi tiết từng module

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DETAILED CONNECTION DIAGRAM                           │
└─────────────────────────────────────────────────────────────────────────────────┘

ESP32 DevKit V1 Pinout và Kết nối:

               ┌────────────────────────────────────────┐
               │              ESP32 DevKit V1           │
               │                                        │
    3.3V ◄─────┤ 3V3                              VIN ├─────► 5V Input
     GND ◄─────┤ GND                              GND ├─────► Ground
         ◄─────┤ GPIO13                        GPIO12 ├─────►
         ◄─────┤ GPIO12                        GPIO14 ├─────►
         ◄─────┤ GPIO14                        GPIO27 ├─────►
         ◄─────┤ GPIO27                        GPIO26 ├─────►
         ◄─────┤ GPIO26                        GPIO25 ├─────►
         ◄─────┤ GPIO25                        GPIO33 ├─────► Button Input
         ◄─────┤ GPIO32                        GPIO32 ├─────►
         ◄─────┤ GPIO35                        GPIO35 ├─────►
    KY-038 ◄───┤ GPIO34 (Input Only)           GPIO34 ├─────► 
         ◄─────┤ GPIO39                         VN/39 ├─────►
         ◄─────┤ GPIO36                         VP/36 ├─────►
         ◄─────┤ EN                             GPIO23 ├─────►
         ◄─────┤ GPIO23                         GPIO22 ├─────► LCD SCL
         ◄─────┤ GPIO22                         GPIO21 ├─────► LCD SDA
         ◄─────┤ GPIO1/TX                       GPIO19 ├─────►
         ◄─────┤ GPIO3/RX                       GPIO18 ├─────► Yellow LED
         ◄─────┤ GPIO21                         GPIO5  ├─────►
         ◄─────┤ GPIO19                         GPIO17 ├─────►
         ◄─────┤ GPIO18                         GPIO16 ├─────►
         ◄─────┤ GPIO5                          GPIO4  ├─────► Red LED
         ◄─────┤ GPIO17                         GPIO0  ├─────►
         ◄─────┤ GPIO16                         GPIO2  ├─────► Green LED
         ◄─────┤ GPIO4                          GPIO15 ├─────►
         ◄─────┤ GPIO0                          GPIO8  ├─────►
   Green LED ──┤ GPIO2                          GPIO7  ├─────►
         ◄─────┤ GPIO15                         GPIO6  ├─────►
               │                                        │
               └────────────────────────────────────────┘

Module Connection Details:

┌─────────────────────┬────────────────────┬─────────────────────┬─────────────────┐
│      MODULE         │    ESP32 PIN       │    MODULE PIN       │   DESCRIPTION   │
├─────────────────────┼────────────────────┼─────────────────────┼─────────────────┤
│                     │                    │                     │                 │
│  LCD I2C 16x2       │ 3.3V               │ VCC                 │ Power Supply    │
│                     │ GND                │ GND                 │ Ground          │
│                     │ GPIO21 (SDA)       │ SDA                 │ I2C Data        │
│                     │ GPIO22 (SCL)       │ SCL                 │ I2C Clock       │
│                     │                    │                     │                 │
├─────────────────────┼────────────────────┼─────────────────────┼─────────────────┤
│                     │                    │                     │                 │
│  KY-038 Sound       │ 3.3V               │ VCC                 │ Power Supply    │
│  Sensor             │ GND                │ GND                 │ Ground          │
│                     │ GPIO34 (Input)     │ DO                  │ Digital Output  │
│                     │ Not Connected      │ AO                  │ Analog Output   │
│                     │                    │                     │                 │
├─────────────────────┼────────────────────┼─────────────────────┼─────────────────┤
│                     │                    │                     │                 │
│  Push Button        │ GPIO33 (Pull-up)   │ Pin 1               │ Signal Input    │
│  (4-pin)            │ GND                │ Pin 3               │ Ground          │
│                     │ Not Connected      │ Pin 2               │ Not Used        │
│                     │ Not Connected      │ Pin 4               │ Not Used        │
│                     │                    │                     │                 │
├─────────────────────┼────────────────────┼─────────────────────┼─────────────────┤
│                     │                    │                     │                 │
│  LED System         │ GPIO2 → 220Ω       │ Green LED Anode     │ Ready State     │
│                     │ GPIO4 → 220Ω       │ Red LED Anode       │ Error/Listen    │
│                     │ GPIO18 → 220Ω      │ Yellow LED Anode    │ Processing      │
│                     │ GND                │ All LED Cathodes    │ Common Ground   │
├─────────────────────┼────────────────────┼─────────────────────┼─────────────────┤
│                     │                    │                     │                 │
│  MAX98357A I2S Amp  │ GPIO25 (SDOUT)     │ SDOUT               │ Audio Data Out  │
│                     │ GPIO14 (SCK)       │ SCK                 │ Bit Clock       │
│                     │ GPIO15 (WS)        │ WS                  │ Word Select     │
│                     │ 3.3V               │ VCC                 │ Power Supply    │
│                     │ GND                │ GND                 │ Ground          │
└─────────────────────┴────────────────────┴─────────────────────┴─────────────────┘
```

### 2.3.3. Bảng GPIO Pin Mapping và Chức năng

**Bảng kết nối GPIO ESP32 (Updated from Arduino code):**

| GPIO Pin | Chức năng | Kết nối đến | Type | Pull-up | Ghi chú |
|----------|-----------|-------------|------|---------|---------|
| **GPIO21** | I2C SDA | Chân SDA của LCD I2C | I/O | External | Giao tiếp dữ liệu I2C |
| **GPIO22** | I2C SCL | Chân SCL của LCD I2C | I/O | External | Clock tín hiệu I2C |
| **GPIO34** | Sound Input | Chân DO của KY-038 | Input Only | No | Cảm biến âm thanh (chỉ đầu vào) |
| **GPIO33** | Button Input | Nút nhấn (chân 1) | I/O | Internal | Nút nhấn với pull-up (FIXED pin) |
| **GPIO2** | Status LED | LED Status (Built-in + External) | I/O | Internal | LED trạng thái hệ thống |
| **GPIO4** | Red LED | LED Đỏ (qua R220Ω) | I/O | Internal | Trạng thái Error/Listening |
| **GPIO18** | Yellow LED | LED Vàng (qua R220Ω) | I/O | Internal | Trạng thái Processing |
| **GPIO13** | Green LED | LED Xanh (qua R220Ω) | I/O | Internal | Trạng thái Connected/Ready |
| **GPIO14** | I2S SCK | I2S Bit Clock | I/O | No | Bluetooth A2DP Audio Clock |
| **GPIO15** | I2S WS | I2S Word Select | I/O | No | Audio Left/Right Channel Select |
| **GPIO25** | I2S SDOUT | I2S Audio Data Out | I/O | No | Audio data to speakers/amp |
| **3.3V** | Power | VCC của tất cả module | Power | - | Nguồn 3.3V cho hệ thống |
| **GND** | Ground | GND chung của tất cả | Ground | - | Nối đất chung |

**Chú thích quan trọng:**
- **I2S Audio**: Pins GPIO14, GPIO15, GPIO25 dành cho output audio Bluetooth A2DP
- **Button Pin**: Đã sửa từ GPIO0 thành GPIO33 để tránh xung đột khi boot
- **LED System**: GPIO13 thay vì GPIO18 cho LED Xanh, GPIO18 cho LED Vàng
- **Audio Module**: Sử dụng MAX98357A I2S amplifier để kết nối loa

### 2.3.3.1. I2S Audio Configuration và Bluetooth A2DP Setup

**I2S Interface Connections:**
```
ESP32 Pin    →    MAX98357A Pin    →    Function
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GPIO14       →    BCLK             →    Bit Clock (Audio timing)
GPIO15       →    WSEL (LRC)       →    Word Select (L/R channel)
GPIO25       →    DIN              →    Audio Data Input
3.3V         →    VDD              →    Power Supply
GND          →    GND              →    Ground
             →    GAIN             →    Leave floating (9dB gain)
             →    SD               →    Leave floating (not shutdown)

Speaker Out  ←    SPK+             ←    Positive speaker terminal
Speaker Out  ←    SPK-             ←    Negative speaker terminal
```

**Bluetooth A2DP Configuration trong Arduino:**
```cpp
// I2S Audio pins (from actual Arduino code)
const uint8_t I2S_SCK = 14;     // Audio data bit clock
const uint8_t I2S_WS = 15;      // Audio data left and right clock  
const uint8_t I2S_SDOUT = 25;   // ESP32 audio data output

// Initialize I2S with ESP_I2S.h library
i2s.setPins(I2S_SCK, I2S_WS, I2S_SDOUT);
i2s.begin(I2S_MODE_STD, 44100, I2S_DATA_BIT_WIDTH_16BIT, 
          I2S_SLOT_MODE_STEREO, I2S_STD_SLOT_BOTH);

// Bluetooth A2DP Sink setup
BluetoothA2DPSink a2dp_sink(i2s);
a2dp_sink.start("MIS Assistant");
```

**Audio Pipeline Flow:**
```
Bluetooth Device → ESP32 A2DP → I2S Interface → MAX98357A → Speaker
                   (Receive)    (44.1kHz/16bit)  (Amplify)   (Output)
```

### 2.3.4. Sơ đồ mạch điện chi tiết (Electrical Schematic)

```
                 ESP32 DevKit V1 Detailed Schematic

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           POWER DISTRIBUTION                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

    USB 5V ─┬─► ESP32 VIN ──► Internal Regulator ──► 3.3V Rail
            │
            └─► [Optional] External 3.3V Supply for LCD
            
    3.3V Rail ──┬─── LCD VCC
                ├─── KY-038 VCC  
                └─── Pull-up for Button (Internal)
                
    GND Rail ───┬─── LCD GND
                ├─── KY-038 GND
                ├─── Button GND
                └─── LED Cathodes (All)

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            I2C BUS TOPOLOGY                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

    ESP32 GPIO21 (SDA) ──────────────► LCD SDA (Data Line)
                         │
                         └─── [4.7kΩ Pull-up to 3.3V - Internal in LCD Module]
                         
    ESP32 GPIO22 (SCL) ──────────────► LCD SCL (Clock Line)
                         │
                         └─── [4.7kΩ Pull-up to 3.3V - Internal in LCD Module]

┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DIGITAL INPUT CIRCUITS                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    Sound Sensor (KY-038):
    3.3V ──► KY-038 VCC
    GND  ──► KY-038 GND
    ESP32 GPIO34 ◄── KY-038 DO (Digital Output, HIGH when sound detected)
    
    Push Button:
    3.3V ──┬── [10kΩ Internal Pull-up] 
           │
    ESP32 GPIO33 ◄──┬── Button Pin 1
                    │
    GND ────────────┴── Button Pin 3
    
    Logic: Button pressed = LOW, Released = HIGH

┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LED OUTPUT CIRCUITS                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

    Green LED (Ready State):
    ESP32 GPIO2 ──► [220Ω] ──► Green LED Anode
                                      │
    GND ◄────────────────────────────┘ LED Cathode
    
    Red LED (Error/Listen State):
    ESP32 GPIO4 ──► [220Ω] ──► Red LED Anode
                                     │
    GND ◄───────────────────────────┘ LED Cathode
    
    Yellow LED (Processing State):
    ESP32 GPIO18 ──► [220Ω] ──► Yellow LED Anode
                                       │
    GND ◄─────────────────────────────┘ LED Cathode

┌─────────────────────────────────────────────────────────────────────────────────┐
│                      COMPONENT VALUE CALCULATIONS                              │
└─────────────────────────────────────────────────────────────────────────────────┘

    LED Current Limiting Resistors:
    - ESP32 GPIO Output: 3.3V
    - LED Forward Voltage: ~2.0V (Red/Yellow), ~3.0V (Green)
    - Target Current: 15mA (safe for ESP32 GPIO)
    
    For Red/Yellow LEDs: R = (3.3V - 2.0V) / 0.015A = 87Ω → Use 220Ω (safer)
    For Green LED: R = (3.3V - 3.0V) / 0.015A = 20Ω → Use 220Ω (consistent)
    
    Actual Current with 220Ω:
    - Red/Yellow: (3.3V - 2.0V) / 220Ω = 5.9mA
    - Green: (3.3V - 3.0V) / 220Ω = 1.4mA
```

### 2.3.5. Breadboard Layout và Hướng dẫn lắp ráp

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BREADBOARD LAYOUT DIAGRAM                            │
└─────────────────────────────────────────────────────────────────────────────────┘

     a  b  c  d  e     f  g  h  i  j     a  b  c  d  e     f  g  h  i  j
  1  ○  ○  ○  ○  ○     ○  ○  ○  ○  ○   1 ○  ○  ○  ○  ○     ○  ○  ○  ○  ○  
  2  ○  ○  ○  ○  ○     ○  ○  ○  ○  ○   2 ○  ○  ○  ○  ○     ○  ○  ○  ○  ○  
  3  ○  ○  ○  ○  ○     ○  ○  ○  ○  ○   3 ○  ○  ○  ○  ○     ○  ○  ○  ○  ○  
     ┌─────────────────────────────┐      ┌─────────────────────────────┐
  4  │    LCD I2C 16x2 Module      │   4  │      KY-038 Sound Sensor     │
  5  │  ┌─────────────────────┐    │   5  │  ┌─────────────────────┐    │
  6  │  │  MIS Assistant      │    │   6  │  │   ◎ Sensitivity     │    │
  7  │  │  Ready !!!          │    │   7  │  │   ◎ LED Indicator   │    │
  8  │  └─────────────────────┘    │   8  │  └─────────────────────┘    │
  9  │ VCC GND SDA SCL             │   9  │ VCC GND  AO  DO             │
 10  └──○───○───○───○─────────────┘  10  └──○───○───○───○─────────────┘
 11     │   │   │   │                11     │   │       │              
 12     │   │   │   │                12     │   │       │              
 13  ○──┼───┼───┼───┼────○ ○     ○  13  ○──┼───┼───────┼──○ ○     ○  
 14  ○──┼───┼───┼───┼────○ ○     ○  14  ○──┼───┼───────┼──○ ○     ○  
 15  ○──│   │   │   │────○ ○     ○  15  ○──│   │       │──○ ○     ○  
      ┌─┴─┐ │   │   │                   ┌─┴─┐ │       │              
 16   │3V3│ │   │   │             16    │3V3│ │       │              
      └─┬─┘ │   │   │                   └─┬─┘ │       │              
 17  ○──┼───┼───┼───┼────○ ○     ○  17  ○──┼───┼───────┼──○ ○     ○  
 18  ○──│   │   │   │────○ ○     ○  18  ○──│   │       │──○ ○     ○  
      ┌─┴─┐ │   │   │                   ┌─┴─┐ │       │              
 19   │GND│ │   │   │             19    │GND│ │       │              
      └─┬─┘ │   │   │                   └─┬─┘ │       │              
 20  ○──┼───┼───┼───┼────○ ○     ○  20  ○──┼───┼───────┼──○ ○     ○  
 21  ○  │   │   │   │    ○ ○     ○  21  ○  │   │       │  ○ ○     ○  
      ┌─┴───┼───┼───┼───┐               ┌─┴───┼───────┼─┐
 22   │ESP32 DevKit V1 │          22   │     │       │ │
 23   │                │          23   │ ┌───┴───┐   │ │   ┌─────────┐
 24   │ ┌────────────┐ │          24   │ │GPIO34 │   │ │   │ Button  │
 25   │ │    CPU     │ │          25   │ └───────┘   │ │   │ ┌───┬───┐
 26   │ │   CORE     │ │          26   │             │ │   │ │ 1 │ 3 │
 27   │ └────────────┘ │          27   │             │ │   │ └─┬─┴─┬─┘
 28   │                │          28   │             │ └─────┼───│
 29   └─┬─┬─┬─┬─┬─┬─┬─┬┘          29   └─────────────┘       │   │
 30  ○──┼─┼─┼─┼─┼─┼─┼─┼──○ ○     ○  30  ○ ○ ○ ○ ○ ○         │   │
       │ │ │ │ │ │ │ │                                     │   │
     21│ │ │ │ │2│4│18│                                     │   │
     SDA│ │ │ │  │ │  │                                 ┌───┴─┐ │
 31  ○──┼─┼─┼─┼──┼─┼──┼──○ ○     ○  31  ○ ○ ○ ○ ○ ○     │GPIO │ │
       22│ │ │   │ │   │                                │ 33  │ │
     SCL│ │ │    │ │   │                                └─────┘ │
 32  ○──┼─┼─┼────┼─┼───┼──○ ○     ○  32  ○ ○ ○ ○ ○ ○             │
       GND│ │   [R][R] [R]                                      │
 33  ○────┼─┼───220Ω─220Ω─220Ω ○  33  ○ ○ ○ ○ ○ ○         ┌─────┴─┐
 34  ○    │ │    │  │   │    ○     ○  34  ○ ○ ○ ○ ○ ○       │  GND  │
 35  ○    │ │   🟢 🔴  🟡   ○     ○  35  ○ ○ ○ ○ ○ ○       └───────┘
 36  ○    │ │  LED LED LED  ○     ○  36  ○ ○ ○ ○ ○ ○  
 37  ○────┼─┼────┼──┼───┼────○     ○  37  ○ ○ ○ ○ ○ ○  
 38  ○ ○ ○│ │ ○ ○│ ○│ ○ │○ ○ ○     ○  38  ○ ○ ○ ○ ○ ○  
 39  ○ ○ ○│ │ ○ ○│ ○│ ○ │○ ○ ○     ○  39  ○ ○ ○ ○ ○ ○  
 40  ○ ○ ○└─┴─○ ○└─○┴─○─┘○ ○ ○     ○  40  ○ ○ ○ ○ ○ ○  
       Power Rails (+ -)              Power Rails (+ -)

Legend:
🟢 = Green LED (GPIO2)    🔴 = Red LED (GPIO4)    🟡 = Yellow LED (GPIO18)
[R] = 220Ω Resistor      ○ = Breadboard hole      ◎ = Potentiometer
```

### 2.3.6. Hướng dẫn lắp ráp từng bước

**Bước 1: Chuẩn bị breadboard và nguồn điện**
1. Đặt ESP32 DevKit V1 vào giữa breadboard (hàng 22-29)
2. Kết nối power rails: 3.3V và GND từ ESP32 ra các rail nguồn

**Bước 2: Lắp đặt LCD I2C**
1. Đặt LCD I2C module ở vị trí hàng 4-10, cột a-e
2. Kết nối dây jumper:
   - VCC (LCD) → 3.3V rail
   - GND (LCD) → GND rail  
   - SDA (LCD) → GPIO21 (ESP32)
   - SCL (LCD) → GPIO22 (ESP32)

**Bước 3: Lắp đặt cảm biến KY-038**
1. Đặt KY-038 ở vị trí hàng 4-10, cột f-j
2. Kết nối dây jumper:
   - VCC (KY-038) → 3.3V rail
   - GND (KY-038) → GND rail
   - DO (KY-038) → GPIO34 (ESP32)
   - AO (KY-038) → Không kết nối

**Bước 4: Lắp đặt hệ thống LED**
1. Đặt 3 điện trở 220Ω ở hàng 33
2. Kết nối LEDs:
   - LED Xanh: GPIO2 → 220Ω → LED Anode, LED Cathode → GND
   - LED Đỏ: GPIO4 → 220Ω → LED Anode, LED Cathode → GND  
   - LED Vàng: GPIO18 → 220Ω → LED Anode, LED Cathode → GND

**Bước 5: Lắp đặt I2S Audio Module (MAX98357A)**
1. Đặt MAX98357A module ở vị trí riêng biệt trên breadboard
2. Kết nối I2S pins:
   - VDD (MAX98357A) → 3.3V rail
   - GND (MAX98357A) → GND rail
   - BCLK (MAX98357A) → GPIO14 (ESP32)
   - WSEL/LRC (MAX98357A) → GPIO15 (ESP32)
   - DIN (MAX98357A) → GPIO25 (ESP32)
   - GAIN (MAX98357A) → Leave floating (9dB gain)
   - SD (MAX98357A) → Leave floating (enable)
3. Kết nối speaker:
   - SPK+ (MAX98357A) → Speaker positive terminal
   - SPK- (MAX98357A) → Speaker negative terminal

**Bước 6: Lắp đặt nút nhấn**
1. Đặt nút nhấn 4 chân ở vị trí hàng 23-26
2. Kết nối:
   - Pin 1 (nút) → GPIO33 (ESP32)
   - Pin 3 (nút) → GND rail
   - Enable internal pull-up trong code cho GPIO33

**Bước 7: Kiểm tra kết nối**
1. Kiểm tra tất cả kết nối nguồn (3.3V, GND)
2. Đảm bảo không có short circuit
3. Kiểm tra polarity của LEDs (chân dài = anode, chân ngắn = cathode)
4. Verify I2S connections với đồng hồ vạn năng
5. Test continuity cho tất cả GPIO pins

**Bước 8: Upload code và test**
1. Kết nối ESP32 với máy tính qua USB
2. Upload Arduino code từ `hardware/arduino_code/`
3. Mở Serial Monitor để kiểm tra hoạt động
4. Test từng chức năng: LCD, LEDs, Button, Sound Sensor, I2S Audio
5. Test Bluetooth A2DP bằng cách pair với smartphone và phát nhạc

**Audio Testing Procedure:**
1. Enable Bluetooth trên smartphone
2. Tìm kiếm "MIS Assistant" trong danh sách Bluetooth devices
3. Pair và connect với ESP32
4. Phát nhạc từ smartphone - âm thanh sẽ ra từ speaker
5. Check Serial Monitor để xem Bluetooth connection status
6. Test audio quality và volume levels
