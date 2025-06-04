## Sơ đồ kết nối chi tiết MIS Smart Assistant

### Tổng quan về kết nối
Đây là hướng dẫn chi tiết cách kết nối các thiết bị phần cứng của dự án MIS Smart Assistant.

### Danh sách thiết bị
- ESP8266 NodeMCU
- Cảm biến âm thanh KY-038
- Màn hình LCD I2C 16x2
- 3x Đèn LED RGB (Đỏ, Vàng, Xanh)
- 1x Đèn LED trạng thái (đỏ)
- 1x Nút nhấn 4 chân
- Breadboard
- Dây jumper
- 4x Điện trở 220Ω

### Các chân kết nối ESP8266 NodeMCU
Dưới đây là chức năng của các chân được sử dụng trên ESP8266 NodeMCU:

- **D1 (GPIO5)**: SCL của màn hình LCD I2C
- **D2 (GPIO4)**: SDA của màn hình LCD I2C
- **D3 (GPIO0)**: Kết nối với đèn LED Đỏ (qua điện trở 220Ω)
- **D4 (GPIO2)**: Kết nối với đèn LED trạng thái (qua điện trở 220Ω)
- **D5 (GPIO14)**: Kết nối với chân DO (Digital Output) của cảm biến âm thanh KY-038
- **D6 (GPIO12)**: Kết nối với nút nhấn
- **D7 (GPIO13)**: Kết nối với đèn LED Xanh (qua điện trở 220Ω)
- **D8 (GPIO15)**: Kết nối với đèn LED Vàng (qua điện trở 220Ω)
- **3.3V**: Cung cấp điện cho các thiết bị
- **GND**: Nối đất cho tất cả các thiết bị

### Kết nối chi tiết

#### 1. Kết nối màn hình LCD I2C 16x2 với ESP8266
- Chân VCC của LCD → 3.3V của ESP8266
- Chân GND của LCD → GND của ESP8266
- Chân SDA của LCD → D2 (GPIO4) của ESP8266
- Chân SCL của LCD → D1 (GPIO5) của ESP8266

#### 2. Kết nối cảm biến âm thanh KY-038 với ESP8266
- Chân VCC của KY-038 → 3.3V của ESP8266
- Chân GND của KY-038 → GND của ESP8266
- Chân DO (Digital Output) của KY-038 → D5 (GPIO14) của ESP8266
- (Tùy chọn) Chân AO (Analog Output) của KY-038 có thể kết nối với A0 của ESP8266 nếu muốn đọc giá trị analog

#### 3. Kết nối đèn LED trạng thái
- Anot (+) của LED trạng thái → Điện trở 220Ω → D4 (GPIO2) của ESP8266
- Catot (-) của LED trạng thái → GND của ESP8266

#### 4. Kết nối 3 đèn LED RGB
- **Đèn LED Đỏ:**
  - Anot (+) → Điện trở 220Ω → D3 (GPIO0) của ESP8266
  - Catot (-) → GND của ESP8266
- **Đèn LED Vàng:**
  - Anot (+) → Điện trở 220Ω → D8 (GPIO15) của ESP8266
  - Catot (-) → GND của ESP8266
- **Đèn LED Xanh:**
  - Anot (+) → Điện trở 220Ω → D7 (GPIO13) của ESP8266
  - Catot (-) → GND của ESP8266

#### 5. Kết nối nút nhấn
- Chân số 1 của nút nhấn → D6 (GPIO12) của ESP8266
- Chân số 3 của nút nhấn → GND của ESP8266

### Lưu ý
1. Đảm bảo tất cả các kết nối GND đều được nối với nhau
2. Cẩn thận với các kết nối điện áp, ESP8266 hoạt động ở mức 3.3V
3. Sử dụng điện trở 220Ω cho tất cả các LED để bảo vệ chân GPIO
4. Có thể điều chỉnh độ nhạy của cảm biến âm thanh KY-038 bằng biến trở xoay trên module
5. Nút nhấn sử dụng chế độ INPUT_PULLUP, nên trạng thái không nhấn là HIGH, nhấn là LOW

### Kiểm tra kết nối
Sau khi kết nối xong, hãy kiểm tra:
1. Không có kết nối nào bị chạm chập
2. Tất cả các thiết bị đều được kết nối đúng với nguồn điện và GND
3. Các chân tín hiệu được kết nối đúng với chân GPIO tương ứng

### Cấp nguồn
Dự án có thể được cấp nguồn thông qua:
1. Cổng USB của ESP8266 NodeMCU (kết nối với máy tính)
2. Pin ngoài (5-12V) kết nối vào chân Vin của ESP8266