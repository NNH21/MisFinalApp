# 1. GIỚI THIỆU DỰ ÁN

## 1.1. BỐI CẢNH VÀ ĐỘNG LỰC

Trong thời đại công nghệ 4.0, trí tuệ nhân tạo (AI) và Internet of Things (IoT) đang trở thành xu hướng phát triển mạnh mẽ. Việc tích hợp AI vào các thiết bị thông minh giúp nâng cao chất lượng cuộc sống và tạo ra những trải nghiệm người dùng tốt hơn.

### Bối cảnh phát triển
- **Nhu cầu thực tế**: Ngày càng có nhiều người dùng mong muốn có một trợ lý thông minh cá nhân có thể tương tác bằng tiếng Việt và điều khiển được phần cứng
- **Xu hướng công nghệ**: Sự phát triển của các API AI như Google Gemini, GPT và các công nghệ nhúng như ESP32
- **Giáo dục và nghiên cứu**: Cần có các dự án thực tế để áp dụng kiến thức về lập trình, điện tử và AI

### Động lực thực hiện
- **Học tập và nghiên cứu**: Áp dụng kiến thức đã học về lập trình Python, điện tử số và trí tuệ nhân tạo
- **Tính thực tiễn**: Tạo ra sản phẩm có thể sử dụng trong đời sống thực tế
- **Đổi mới sáng tạo**: Kết hợp nhiều công nghệ khác nhau tạo ra một hệ thống hoàn chỉnh
- **Phát triển kỹ năng**: Nâng cao khả năng thiết kế hệ thống, lập trình và tích hợp phần cứng

## 1.2. MỤC TIÊU DỰ ÁN

### 1.2.1. Công nghệ và chức năng
**Mục tiêu chính:**
- Xây dựng một trợ lý thông minh sử dụng Google Gemini AI với khả năng hiểu và phản hồi bằng tiếng Việt
- Tích hợp giao diện đồ họa hiện đại sử dụng PyQt5 với nhiều widget chức năng
- Phát triển hệ thống phần cứng ESP32 với các cảm biến và thiết bị hiển thị

**Chức năng cốt lõi:**
- **Xử lý ngôn ngữ tự nhiên**: Hiểu và trả lời các câu hỏi phức tạp bằng tiếng Việt
- **Chuyển đổi văn bản thành giọng nói**: Sử dụng Google Text-to-Speech (gTTS)
- **Hiển thị thông tin thời tiết**: Tích hợp API OpenWeatherMap
- **Quản lý thời gian**: Hiển thị thời gian nhiều múi giờ, báo thức
- **Điều khiển multimedia**: Phát nhạc, video từ nhiều nguồn

### 1.2.2. Hiệu suất và độ tin cậy
**Yêu cầu hiệu suất:**
- Thời gian phản hồi AI dưới 3 giây với kết nối internet ổn định
- Kết nối serial với ESP32 ổn định với cơ chế tự động kết nối lại
- Giao diện người dùng mượt mà, không bị lag khi thao tác

**Độ tin cậy:**
- Hệ thống hoạt động liên tục 24/7 mà không bị crash
- Cơ chế xử lý lỗi và phục hồi tự động khi mất kết nối
- Backup và khôi phục cấu hình người dùng

### 1.2.3. Khả năng mở rộng và tương thích
**Khả năng mở rộng:**
- Kiến trúc modular cho phép thêm các chức năng mới dễ dàng
- Hỗ trợ plugin system cho các tính năng bổ sung
- Có thể tích hợp thêm nhiều loại cảm biến và thiết bị IoT

**Tương thích:**
- Hoạt động trên Windows, macOS và Linux
- Hỗ trợ nhiều thiết bị ESP32 khác nhau
- Tương thích với các API bên thứ ba

### 1.2.4. Giáo dục và nghiên cứu
**Giá trị giáo dục:**
- Minh họa cách tích hợp AI vào ứng dụng thực tế
- Thể hiện kỹ thuật lập trình GUI với PyQt5
- Hướng dẫn chi tiết về việc kết nối và điều khiển phần cứng

**Nghiên cứu:**
- Nghiên cứu hiệu quả của việc kết hợp AI cloud với edge computing
- Đánh giá trải nghiệm người dùng với trợ lý thông minh tiếng Việt
- Phân tích hiệu suất của các API AI khác nhau

### 1.2.5. Tính năng thông minh nâng cao
**Tính năng AI:**
- **Smart Vision**: Nhận dạng hình ảnh và QR code bằng camera
- **Context Awareness**: Hiểu bối cảnh câu hỏi để đưa ra phản hồi phù hợp
- **Learning Capabilities**: Ghi nhớ sở thích người dùng qua thời gian sử dụng

**Tích hợp IoT:**
- Điều khiển thiết bị thông minh qua Bluetooth
- Monitoring trạng thái hệ thống real-time
- Tự động hóa dựa trên thời gian và sự kiện

### 1.2.6. Trải nghiệm người dùng
**Giao diện người dùng:**
- Thiết kế modern, intuitive với dark/light theme
- Responsive layout phù hợp với nhiều kích thước màn hình
- Hiệu ứng visual và animation mượt mà

**Tương tác đa phương thức:**
- Giao diện đồ họa (GUI) với mouse và keyboard
- Điều khiển bằng giọng nói (Voice Control)
- Điều khiển phần cứng qua nút nhấn và cảm biến
- Kết nối và điều khiển qua Bluetooth từ mobile

## 1.3. PHẠM VI DỰ ÁN

### Phạm vi bao gồm:
**Phần mềm:**
- Ứng dụng desktop với PyQt5
- Tích hợp Google Gemini AI API
- Hệ thống multimedia và weather services
- Bluetooth connectivity cho mobile devices

**Phần cứng:**
- Vi điều khiển ESP32 DevKit V1
- Màn hình LCD I2C 16x2 để hiển thị trạng thái
- 3 LED RGB (Đỏ, Vàng, Xanh) + 1 LED trạng thái
- Cảm biến âm thanh KY-038 để kích hoạt voice
- Nút nhấn để điều khiển thủ công
- Breadboard và hệ thống kết nối

**Tính năng:**
- Chat với AI bằng tiếng Việt
- Hiển thị thời tiết real-time
- Quản lý thời gian và báo thức
- Phát multimedia (âm nhạc, video)
- Computer vision với camera
- Kết nối và điều khiển thiết bị IoT

### Phạm vi không bao gồm:
- Ứng dụng mobile native (chỉ điều khiển qua Bluetooth)
- Cloud storage cho dữ liệu người dùng
- Voice recognition offline (chỉ sử dụng online services)
- Tích hợp với social media platforms
- Commercial deployment và maintenance

### Giới hạn kỹ thuật:
- **Phụ thuộc internet**: Cần kết nối mạng cho AI và weather services
- **Ngôn ngữ**: Chủ yếu hỗ trợ tiếng Việt và tiếng Anh
- **Platform**: Tối ưu cho Windows, hỗ trợ hạn chế trên macOS/Linux
- **Hardware**: Thiết kế cho ESP32, cần điều chỉnh để hỗ trợ MCU khác

---

**Tóm tắt:** Dự án MIS Smart Assistant là một hệ thống trợ lý thông minh tích hợp AI, IoT và multimedia, nhằm tạo ra trải nghiệm người dùng hoàn chỉnh với khả năng tương tác đa phương thức và điều khiển phần cứng thông minh.
