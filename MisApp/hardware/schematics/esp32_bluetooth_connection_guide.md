# Sơ đồ kết nối chi tiết MIS Smart Assistant - ESP32 với Bluetooth A2DP

## Tổng quan về kết nối ESP32 với Audio

Đây là hướng dẫn chi tiết cách kết nối các thiết bị phần cứng của dự án MIS Smart Assistant với **ESP32 DevKit V1** tích hợp tính năng **Bluetooth A2DP Audio**.

### Danh sách thiết bị
- **ESP32 DevKit V1** (Vi điều khiển chính)
- Cảm biến âm thanh KY-038
- Màn hình LCD I2C 16x2
- 3x Đèn LED RGB (Đỏ, Vàng, Xanh)
- 1x Đèn LED trạng thái (đỏ)
- 1x Nút nhấn 4 chân
- **I2S Audio Amplifier (như MAX98357A hoặc tương tự)**
- **Loa hoặc headphone**
- Breadboard
- Dây jumper
- 4x Điện trở 220Ω

### Các chân kết nối ESP32 DevKit V1 (Phiên bản Bluetooth)
Dưới đây là chức năng của các chân được sử dụng trên ESP32:

**I2C và Display:**
- **GPIO21**: SDA của màn hình LCD I2C (I2C default)
- **GPIO16**: SCL của màn hình LCD I2C (moved from 22 to avoid I2S conflict)

**I2S Audio (Bluetooth A2DP) - Updated for ESP_I2S.h:**
- **GPIO14**: I2S SCK (Serial Clock) - kết nối với SCK của amplifier
- **GPIO15**: I2S WS (Word Select/LR Clock) - kết nối với WS của amplifier
- **GPIO22**: I2S SDOUT (Serial Data Output) - kết nối với DIN của amplifier

**LED Control (Updated - FIXED):**
- **GPIO4**: Kết nối với đèn LED Đỏ (qua điện trở 220Ω) - FIXED from GPIO0
- **GPIO2**: Kết nối với đèn LED trạng thái (qua điện trở 220Ω) + LED onboard
- **GPIO18**: Kết nối với đèn LED Vàng (qua điện trở 220Ω) - FIXED from GPIO16
- **GPIO19**: Kết nối với đèn LED Xanh (qua điện trở 220Ω) - FIXED from GPIO17

**Input Devices:**
- **GPIO34**: Kết nối với chân DO (Digital Output) của cảm biến âm thanh KY-038 (Input Only)
- **GPIO35**: Kết nối với nút nhấn (Input Only)

**Power:**
- **3.3V**: Cung cấp điện cho các thiết bị
- **5V**: Cung cấp điện cho I2S Amplifier (nếu cần)
- **GND**: Nối đất cho tất cả các thiết bị

### Sơ đồ kết nối tổng thể

```
                             +----------------------+
                             |      ESP32           |
                             |      DevKit V1       |
                             +----------------------+
                                  |    |    |    |
                                  |    |    |    |
     +---------------+            |    |    |    |           +-------------------+
     |               |            |    |    |    |           |                   |
     | Cảm biến      |------------+    |    +---------------|  LED RGB          |
     | KY-038        |                 |                     |  (Đỏ,Vàng,Xanh)  |
     |               |                 |                     |  + LED trạng thái |
     +---------------+                 |                     +-------------------+
                                       |
                                       |
                              +---------------------+           +-------------------+
                              |                     |           |                   |
                              | Màn hình LCD I2C    |           |   Nút nhấn        |
                              | 16x2                |           |   4 chân          |
                              |                     |           |                   |
                              +---------------------+           +-------------------+
                                       |
                                       |
                              +---------------------+           +-------------------+
                              |                     |           |                   |
                              | I2S Audio Amplifier |-----------|      Loa          |
                              | (MAX98357A)         |           |   hoặc Headphone  |
                              |                     |           |                   |
                              +---------------------+           +-------------------+
```

### Kết nối chi tiết

#### 1. Kết nối màn hình LCD I2C 16x2 với ESP32
- Chân VCC của LCD → 3.3V của ESP32
- Chân GND của LCD → GND của ESP32
- Chân SDA của LCD → GPIO21 của ESP32 (I2C SDA default)
- Chân SCL của LCD → GPIO22 của ESP32 (I2C SCL default)

#### 2. Kết nối cảm biến âm thanh KY-038 với ESP32
- Chân VCC của KY-038 → 3.3V của ESP32
- Chân GND của KY-038 → GND của ESP32
- Chân DO (Digital Output) của KY-038 → GPIO34 của ESP32 (Input Only pin)
- (Tùy chọn) Chân AO (Analog Output) có thể kết nối với GPIO36 (VP) nếu muốn đọc giá trị analog

#### 3. Kết nối I2S Audio Amplifier (MAX98357A) - Updated for ESP_I2S.h
**⚠️ LƯU Ý: Sử dụng GPIO22 cho I2S Data Output - tương thích với ESP_I2S.h**

**Cấu hình mới (ESP_I2S.h compatible):**
- **ESP32 GPIO14** → **SCK** của MAX98357A (I2S Serial Clock)
- **ESP32 GPIO15** → **WS/LRC** của MAX98357A (Word Select)
- **ESP32 GPIO22** → **SD/DIN** của MAX98357A (Serial Data Output) - **REVERTED**
- **3.3V hoặc 5V** → **VCC** của MAX98357A
- **GND** → **GND** của MAX98357A

#### 4. Kết nối đèn LED trạng thái
- Anot (+) của LED trạng thái → Điện trở 220Ω → GPIO2 của ESP32
- Catot (-) của LED trạng thái → GND của ESP32

#### 5. Kết nối 3 đèn LED RGB (UPDATED - FIXED)
- **Đèn LED Đỏ:**
  - Anot (+) → Điện trở 220Ω → GPIO4 của ESP32 (FIXED from GPIO0)
  - Catot (-) → GND của ESP32
- **Đèn LED Vàng:**
  - Anot (+) → Điện trở 220Ω → GPIO18 của ESP32 (FIXED from GPIO16)
  - Catot (-) → GND của ESP32
- **Đèn LED Xanh:**
  - Anot (+) → Điện trở 220Ω → GPIO19 của ESP32 (FIXED from GPIO17)
  - Catot (-) → GND của ESP32

#### 6. Kết nối nút nhấn
- Chân số 1 của nút nhấn → GPIO35 của ESP32 (Input Only pin)
- Chân số 3 của nút nhấn → GND của ESP32

#### 7. Kết nối loa/headphone
- Loa trái (+) → OUT+ của MAX98357A
- Loa trái (-) → OUT- của MAX98357A
- Loa phải → Nối song song hoặc sử dụng 2 amplifier riêng biệt

### Lưu ý quan trọng cho ESP32 Bluetooth

1. **Điện áp**: ESP32 hoạt động ở mức 3.3V, MAX98357A có thể dùng 3.3V hoặc 5V
2. **I2C mặc định**: ESP32 có chân I2C mặc định là GPIO21 (SDA) và GPIO22 (SCL)
3. **GPIO2**: Kết nối với LED onboard, sẽ nhấp nháy khi có hoạt động
4. **Input Only Pins**: GPIO34, GPIO35, GPIO36, GPIO39 chỉ dùng làm input
5. **I2S Audio**: Sử dụng GPIO14, GPIO15, GPIO25 cho I2S
6. **Bluetooth**: Tự động hoạt động, không cần kết nối thêm
7. **Điện trở**: Vẫn sử dụng điện trở 220Ω cho tất cả các LED để bảo vệ chân GPIO
8. **Nút nhấn**: Vẫn sử dụng chế độ INPUT_PULLUP, trạng thái không nhấn là HIGH, nhấn là LOW

### So sánh pin mapping ESP32 thường vs ESP32 Bluetooth

| Chức năng | ESP32 Thường | ESP32 + Bluetooth | Ghi chú |
|-----------|--------------|-------------------|---------|
| LCD SDA | GPIO21 | GPIO21 | Không đổi |
| LCD SCL | GPIO22 | GPIO22 | Không đổi |
| I2S SCK | - | GPIO14 | Mới thêm |
| I2S WS | - | GPIO15 | Mới thêm |
| I2S SD | - | GPIO25 | Mới thêm |
| LED Đỏ | GPIO0 | GPIO4 | Đổi để tránh boot conflict |
| LED Status | GPIO2 | GPIO2 | Giữ nguyên |
| LED Vàng | GPIO15 | GPIO16 | Đổi vì GPIO15 dùng cho I2S |
| LED Xanh | GPIO13 | GPIO17 | Đổi để nhóm pin |
| KY-038 DO | GPIO14 | GPIO34 | Đổi vì GPIO14 dùng cho I2S |
| Button | GPIO12 | GPIO35 | Đổi để dùng Input Only pin |

### Kiểm tra kết nối Audio
Sau khi kết nối xong, hãy kiểm tra:
1. **I2S Amplifier**: LED power sáng, không có tiếng ồn
2. **Loa**: Kết nối chắc chắn, phân cực đúng
3. **Bluetooth**: ESP32 xuất hiện với tên "MIS Assistant" trong danh sách Bluetooth
4. **Audio Test**: Phát nhạc từ điện thoại để test âm thanh

### Cấp nguồn cho hệ thống Audio
ESP32 + Audio có thể được cấp nguồn:
1. **Cổng USB của ESP32 DevKit V1** (kết nối với máy tính) - Khuyến nghị cho test
2. **Pin ngoài 5V** kết nối vào chân Vin của ESP32 - Khuyến nghị cho loa lớn
3. **Pin 3.3V** trực tiếp (chỉ cho I2S amplifier điện áp thấp)

### Lợi ích của pin mapping mới
1. **Audio chất lượng cao**: I2S digital audio, không bị nhiễu analog
2. **Bluetooth A2DP**: Hỗ trợ codec SBC, aptX cho âm thanh stereo
3. **Tương thích**: Vẫn giữ nguyên LCD và chức năng cơ bản
4. **Mở rộng**: Có thể thêm microphone I2S, equalizer
5. **Input Only pins**: Sử dụng hiệu quả các chân input only cho sensor
6. **Hiệu năng**: ESP32 dual-core xử lý đồng thời WiFi và Bluetooth
