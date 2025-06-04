# MIS Assistant - IoT Final Project

## Giới thiệu
MIS Assistant là một trợ lý thông minh được phát triển như một dự án cuối kỳ IoT. Ứng dụng tích hợp nhiều tính năng như:

- 🗣️ Nhận diện giọng nói và phản hồi bằng giọng nói
- 🤖 Trò chuyện thông minh với AI (Google Gemini)
- ⏰ Quản lý báo thức và hẹn giờ
- 🌤️ Thông tin thời tiết
- 📰 Tin tức cập nhật
- 🎵 Phát nhạc và multimedia
- 📱 Giao diện LCD và điều khiển phần cứng
- 🔊 Thông báo âm thanh

## Cấu trúc dự án

```
FinalReportIoT/
├── MisApp/                    # Ứng dụng chính
│   ├── software/             # Mã nguồn phần mềm
│   │   ├── app/             # Core application
│   │   │   ├── models/      # Business logic
│   │   │   ├── ui/          # User interface
│   │   │   └── utils/       # Utilities
│   │   └── logs/            # Log files
│   ├── hardware/            # Phần cứng và sơ đồ
│   │   ├── arduino_code/    # Code Arduino/ESP32
│   │   └── schematics/      # Sơ đồ mạch
│   ├── resources/           # Tài nguyên (âm thanh, hình ảnh)
│   └── docs/               # Tài liệu dự án
└── build/                   # Build artifacts
```

## Yêu cầu hệ thống

### Phần mềm
- Python 3.11+
- PyQt5
- Libraries: xem `requirements.txt`

### Phần cứng
- ESP32/Arduino
- LCD Display (I2C)
- Speaker/Buzzer
- Microphone (USB/3.5mm)

## Cài đặt

1. Clone repository:
```bash
git clone https://github.com/[username]/FinalReportIoT.git
cd FinalReportIoT/MisApp
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

3. Chạy ứng dụng:
```bash
python software/app/main.py
```

## Cấu hình

1. **API Keys**: Cần thiết lập API keys cho:
   - Google Gemini AI
   - OpenWeatherMap
   - News API

2. **Hardware**: Kết nối phần cứng theo sơ đồ trong `hardware/schematics/`

## Tính năng chính

### 🎤 Voice Assistant
- Nhận diện giọng nói tiếng Việt
- Xử lý lệnh tự nhiên
- Phản hồi bằng giọng nói

### 🤖 AI Chat
- Tích hợp Google Gemini
- Trò chuyện thông minh
- Hỗ trợ đa ngữ

### ⏰ Time Management
- Đặt báo thức
- Hẹn giờ đếm ngược
- Hiển thị đồng hồ trên LCD

### 🌤️ Weather & News
- Thông tin thời tiết theo vị trí
- Tin tức cập nhật
- Hiển thị trực quan

### 🎵 Multimedia
- Phát nhạc MP3
- Điều khiển âm lượng
- Danh sách phát

## Tác giả
Dự án IoT - Final Report

## License
MIT License

## Liên hệ
- Email: [your-email]
- GitHub: [your-github]
