# MIS Smart Assistant

Trợ lý thông minh sử dụng Google Gemini API với giao diện PyQt5 và điều khiển phần cứng ESP32.

## Mô tả dự án

MIS Smart Assistant là một dự án kết hợp giữa phần mềm và phần cứng, tạo ra một trợ lý thông minh có khả năng:
- Tương tác qua giao diện đồ họa PyQt5 và qua giọng nói
- Trả lời các câu hỏi và yêu cầu bằng tiếng Việt
- Hiển thị thông tin thời tiết thông qua API
- Hiển thị thời gian từ nhiều múi giờ
- Điều khiển và hiển thị trạng thái thông qua phần cứng ESP32
- Kết nối với thiết bị di động qua Bluetooth

Hệ thống phần cứng bao gồm:
- Vi điều khiển ESP32
- Cảm biến âm thanh KY-038
- Màn hình LCD 16x2 I2C
- 3x Đèn LED RGB (Đỏ, Vàng, Xanh) và 1x đèn LED trạng thái
- Nút nhấn để kích hoạt microphone
- Breadboard và các linh kiện kết nối

## Cấu trúc dự án

```
mis_assistant/
│
├── hardware/              # Mã nguồn và tài liệu phần cứng
│   ├── arduino_code/      # Mã điều khiển ESP32
│   └── schematics/        # Sơ đồ mạch điện
│
├── software/              # Ứng dụng phần mềm
│   ├── app/               # Mã nguồn ứng dụng
│   │   ├── models/        # Các model xử lý dữ liệu
│   │   ├── ui/            # Giao diện người dùng
│   │   └── utils/         # Tiện ích và cấu hình
│   └── resources/         # Tài nguyên (biểu tượng, âm thanh)
│
└── tests/                 # Mã kiểm thử
```

## Hướng dẫn cài đặt

### Yêu cầu
- Python 3.8+ với pip
- Arduino IDE
- ESP32 và các linh kiện phần cứng cần thiết

### Cài đặt phần mềm

1. Clone repository:
   ```
   git clone https://github.com/NNH21/mis_assistant.git
   cd mis_assistant
   ```

2. Cài đặt các thư viện Python:
   ```
   pip install -r requirements.txt
   ```

3. Cấu hình:
   - Chỉnh sửa `software/app/utils/config.py` để thiết lập API keys và cấu hình thiết bị

### Cài đặt phần cứng

1. Mở Arduino IDE và cài đặt thư viện cần thiết:
   - ESP8266WiFi
   - LiquidCrystal_I2C
   - Wire

2. Kết nối các thành phần phần cứng theo sơ đồ mạch trong thư mục `hardware/schematics/`

   **Các kết nối chính:**
   - **LCD I2C**: SDA → D2, SCL → D1
   - **LED RGB**: Đỏ → D3, Vàng → D8, Xanh → D7 (qua điện trở 220Ω)
   - **LED trạng thái**: D4 (qua điện trở 220Ω)
   - **Cảm biến âm thanh**: DO → D5
   - **Nút nhấn**: D6 → GND

3. Tải code lên ESP8266:
   - Mở file `hardware/arduino_code/mis_hardware_controller.ino`
   - Chỉnh sửa thông tin WiFi và các thiết lập khác
   - Tải lên ESP8266

## Sử dụng

1. Khởi động ứng dụng:
   ```
   cd mis_assistant
   python -m software.app.main
   ```

2. Giao diện chính:
   - Tab "Trợ lý": Giao diện chat với trợ lý thông minh
   - Tab "Thời tiết": Hiển thị thông tin thời tiết
   - Tab "Thời gian": Hiển thị thời gian từ nhiều múi giờ

3. Tương tác với phần cứng:
   - LED RGB sẽ hiển thị 8 trạng thái khác nhau theo lệnh thoại
   - LED trạng thái sẽ nhấp nháy khi đang lắng nghe và xử lý yêu cầu
   - Màn hình LCD sẽ hiển thị trạng thái "Listening...", "Processing..." và trạng thái LED
   - Cảm biến âm thanh sẽ kích hoạt chế độ lắng nghe khi phát hiện âm thanh
   - Nút nhấn có thể được sử dụng để kích hoạt microphone thủ công

## Các tính năng chính

1. **Trợ lý thông minh**
   - Sử dụng Google Gemini API để xử lý các câu hỏi và yêu cầu
   - Hỗ trợ tiếng Việt cho cả đầu vào và đầu ra
   - Chuyển đổi văn bản thành giọng nói bằng gTTS

2. **Hiển thị thời tiết**
   - Dữ liệu thời tiết thời gian thực
   - Dự báo thời tiết 5 ngày
   - Tùy chọn thay đổi địa điểm

3. **Hiển thị thời gian**
   - Đồng hồ kỹ thuật số
   - Hiển thị thời gian từ nhiều múi giờ
   - Khả năng thêm/xóa múi giờ

4. **Tích hợp phần cứng**
   - Hiển thị trạng thái trên màn hình LCD 16x2
   - Điều khiển 3 đèn LED RGB với 8 trạng thái khác nhau
   - Đèn LED trạng thái thông báo trạng thái hệ thống
   - Kích hoạt lắng nghe thông qua cảm biến âm thanh
   - Nút nhấn thủ công để kích hoạt microphone

5. **Kết nối Bluetooth**
   - Quét và phát hiện thiết bị Bluetooth gần đó
   - Ghép nối và kết nối với thiết bị di động
   - Điều khiển MIS Assistant thông qua ứng dụng di động
   - Hoạt động không cần internet khi đã kết nối

## Phát triển thêm

Một số ý tưởng phát triển trong tương lai:
- Thêm chức năng nhận dạng giọng nói trực tiếp
- Bổ sung các widget thông tin (tin tức, chứng khoán, tỷ giá)
- Mở rộng khả năng điều khiển thiết bị IoT
- Thêm pin sạc để tạo thiết bị di động

## Thông tin giấy phép

Dự án này được phân phối dưới giấy phép MIT. Xem file LICENSE để biết thêm chi tiết.