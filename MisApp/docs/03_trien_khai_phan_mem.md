# 3. TRIỂN KHAI PHẦN MỀM

## 3.1. TỔNG QUAN KIẾN TRÚC PHẦN MỀM

### 3.1.1. Kiến trúc tổng thể

MIS Smart Assistant được xây dựng theo mô hình **Model-View-Controller (MVC)** kết hợp với **Service-Oriented Architecture (SOA)**, đảm bảo tính modular và khả năng mở rộng cao.

```
┌─────────────────────────────────────────────────────────┐
│                    MIS SMART ASSISTANT                  │
│                     ARCHITECTURE                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │    Chat     │ │   Weather   │ │   Time &    │        │
│  │   Widget    │ │   Widget    │ │   Alarm     │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │ Multimedia  │ │Smart Vision │ │ SmartConnect│        │
│  │   Widget    │ │   Widget    │ │   Widget    │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │   Gemini    │ │   Speech    │ │   Weather   │        │
│  │    API      │ │ Processor   │ │   Service   │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │ Multimedia  │ │    Time     │ │  Launcher   │        │
│  │  Service    │ │   Service   │ │   Service   │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                 HARDWARE LAYER                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │  Hardware   │ │ Bluetooth   │ │    LCD      │        │
│  │ Interface   │ │ Interface   │ │   Service   │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                EXTERNAL INTEGRATIONS                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │   Google    │ │ OpenWeather │ │  TimezoneDB │        │
│  │   Gemini    │ │     API     │ │     API     │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │   YouTube   │ │    gTTS     │ │   ESP32     │        │
│  │     API     │ │   Service   │ │  Hardware   │        │
│  └─────────────┘ └─────────────┘ └─────────────┘        │
└─────────────────────────────────────────────────────────┘
```

**Nguyên tắc thiết kế:**
- **Separation of Concerns**: Mỗi component có trách nhiệm riêng biệt
- **Loose Coupling**: Các module ít phụ thuộc lẫn nhau
- **High Cohesion**: Chức năng liên quan được nhóm lại với nhau
- **Dependency Injection**: Tiêm phụ thuộc để dễ test và maintain

### 3.1.2. Cấu trúc thư mục dự án

```
mis_assistant/
│
├── README.md                    # Tài liệu tổng quan dự án
├── requirements.txt             # Dependencies Python
├── test_hardware_connection.py  # Script test kết nối phần cứng
│
├── docs/                        # Tài liệu chi tiết
│   ├── 01_gioi_thieu_du_an.md
│   ├── 02_trien_khai_phan_cung.md
│   └── 03_trien_khai_phan_mem.md
│
├── hardware/                    # Mã nguồn và tài liệu phần cứng
│   ├── arduino_code/
│   │   └── mis_hardware_controller_esp32_bluetooth/
│   │       └── mis_hardware_controller_esp32_bluetooth.ino
│   └── schematics/              # Sơ đồ mạch và hướng dẫn
│       ├── connection_guide.md
│       ├── esp32_connection_guide.md
│       └── setup_guide.md
│
├── software/                    # Ứng dụng phần mềm chính
│   ├── app/                     # Source code ứng dụng
│   │   ├── main.py             # Entry point chính
│   │   ├── models/             # Business logic và services
│   │   │   ├── bluetooth_interface.py
│   │   │   ├── gemini_client.py
│   │   │   ├── hardware_interface.py
│   │   │   ├── launcher_service.py
│   │   │   ├── lcd_service.py
│   │   │   ├── multimedia_service.py
│   │   │   ├── notification_sound_service.py
│   │   │   ├── speech_processor.py
│   │   │   ├── time_service.py
│   │   │   ├── weather_service.py
│   │   │   └── multimedia/      # Multimedia components
│   │   │       ├── metadata_manager.py
│   │   │       ├── playlist_manager.py
│   │   │       └── youtube_downloader.py
│   │   ├── ui/                 # User Interface components
│   │   │   ├── main_window.py  # Main application window
│   │   │   ├── chat_widget.py  # AI Chat interface
│   │   │   ├── weather_widget.py
│   │   │   ├── time_widget.py
│   │   │   ├── multimedia_widget.py
│   │   │   ├── smart_vision_widget.py
│   │   │   ├── smart_connect_widget.py
│   │   │   ├── lcd_widget.py
│   │   │   └── status_widget.py
│   │   └── utils/              # Utilities và configuration
│   │       ├── config.py       # Configuration constants
│   │       └── logger.py       # Logging system
│   │
│   ├── logs/                   # Application logs
│   │   ├── conversation_*.txt  # Chat conversation logs
│   │   └── mis_assistant_*.log # System logs
│   │
│   └── resources/              # Application resources
│       ├── bin/                # Binary executables
│       ├── icons/              # UI icons và images
│       ├── sounds/             # Audio files
│       ├── media_cache/        # Downloaded media cache
│       └── weather_icons/      # Weather condition icons
│
└── resources/                  # Shared resources
    ├── bin/                    # System binaries
    ├── icons/                  # Application icons
    ├── sounds/                 # System sounds
    └── weather_icons/          # Weather icons
```

## 3.2. MÔI TRƯỜNG PHÁT TRIỂN VÀ CÔNG CỤ (DEVELOPMENT ENVIRONMENT & TOOLS)

### 3.2.1. Yêu cầu hệ thống

**Hệ điều hành hỗ trợ:**
- **Windows 10/11** (Recommended) - Tối ưu hóa chính
- **macOS 10.14+** - Hỗ trợ cơ bản
- **Ubuntu 18.04+** - Hỗ trợ cơ bản

**Phần cứng tối thiểu:**
- **CPU**: Intel Core i3 hoặc AMD Ryzen 3
- **RAM**: 4GB (Khuyến nghị 8GB)
- **Storage**: 2GB free space
- **USB Port**: Để kết nối ESP32
- **Internet**: Để sử dụng AI services và weather API

**Phần mềm bắt buộc:**
- **Python 3.8+** với pip package manager
- **Arduino IDE 1.8.13+** hoặc **PlatformIO**
- **Git** cho version control
- **Chrome/Firefox** browser (cho web features)

### 3.2.2. Công cụ phát triển chính

**IDE và Editor:**
- **Visual Studio Code** (Recommended)
  - Extensions: Python, Arduino, GitLens
- **PyCharm Community Edition**
- **Arduino IDE** cho ESP32 programming

**Debugging và Testing Tools:**
- **Python Debugger** (pdb, VS Code debugger)
- **Serial Monitor** cho ESP32 communication
- **Postman** để test API endpoints
- **Qt Designer** cho UI design (optional)

**Version Control:**
- **Git** với GitHub integration
- **Branching strategy**: GitFlow

### 3.2.3. Thiết lập môi trường Python

**Bước 1: Cài đặt Python và Virtual Environment**
```bash
# Kiểm tra Python version
python --version  # Cần >= 3.8

# Tạo virtual environment
python -m venv mis_assistant_env

# Kích hoạt virtual environment
# Windows:
mis_assistant_env\Scripts\activate
# macOS/Linux:
source mis_assistant_env/bin/activate
```

**Bước 2: Clone repository và cài đặt dependencies**
```bash
# Clone dự án
git clone https://github.com/YourRepo/mis_assistant.git
cd mis_assistant

# Cài đặt dependencies
pip install -r requirements.txt

# Verify installation
python -c "import PyQt5; print('PyQt5 installed successfully')"
```

**Bước 3: Cấu hình API Keys**
```python
# Chỉnh sửa software/app/utils/config.py
GEMINI_API_KEY = "your-google-gemini-api-key"
WEATHER_API_KEY = "your-openweathermap-api-key"
TIMEZONE_API_KEY = "your-timezonedb-api-key"
YOUTUBE_API_KEY = "your-youtube-api-key"
```

**Bước 4: Test môi trường**
```bash
# Chạy ứng dụng
cd mis_assistant
python -m software.app.main

# Test hardware connection (optional)
python test_hardware_connection.py
```

## 3.3. THƯ VIỆN VÀ DEPENDENCIES (LIBRARIES & DEPENDENCIES)

### 3.3.1. Thư viện GUI - PyQt5

**PyQt5 Framework**
```python
# Core PyQt5 components được sử dụng
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QSlider,
    QProgressBar, QListWidget, QGraphicsView
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, QObject, pyqtSignal,
    QPropertyAnimation, QEasingCurve
)
from PyQt5.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QColor,
    QLinearGradient, QBrush, QPen
)
```

**Tính năng PyQt5 được sử dụng:**
- **Widget System**: Giao diện đa tab với responsive design
- **Signal-Slot Mechanism**: Event handling và inter-component communication
- **Threading**: Background processing để không block UI
- **Graphics**: Custom painting cho weather icons và animations
- **Styling**: CSS-like styling cho modern UI appearance

**Ưu điểm của PyQt5:**
- Cross-platform compatibility
- Rich widget set và customization options
- Mature framework với documentation tốt
- Performance cao cho desktop applications

### 3.3.2. Thư viện AI - Google Generative AI

**Google Generative AI (Gemini)**
```python
import google.generativeai as genai

# Configuration
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Text generation
response = model.generate_content(prompt)
```

**Tính năng AI được tích hợp:**
- **Natural Language Understanding**: Hiểu câu hỏi tiếng Việt phức tạp
- **Context Awareness**: Nhớ ngữ cảnh cuộc hội thoại
- **Multi-modal Input**: Xử lý văn bản và hình ảnh (Gemini Pro Vision)
- **Real-time Response**: Streaming response cho trải nghiệm tốt

**Speech Processing**
```python
# Text-to-Speech với gTTS
from gtts import gTTS
import pygame

# Speech Recognition
import speech_recognition as sr
recognizer = sr.Recognizer()
```

### 3.3.3. Thư viện Hardware Interface

**Serial Communication**
```python
import serial
import serial.tools.list_ports

# ESP32 connection management
class HardwareInterface:
    def __init__(self):
        self.serial_connection = None
        self.baud_rate = 115200
        
    def connect(self):
        # Auto-detect ESP32 port
        ports = serial.tools.list_ports.comports()
        # Connection logic...
```

**Bluetooth Integration**
```python
# Cross-platform Bluetooth với Bleak
import asyncio
from bleak import BleakScanner, BleakClient

# Device discovery và pairing
class BluetoothInterface:
    async def scan_devices(self):
        devices = await BleakScanner.discover()
        return devices
```

### 3.3.4. Thư viện API Integration

**Weather Service**
```python
import requests
import json

# OpenWeatherMap API
class WeatherService:
    def __init__(self):
        self.api_key = config.WEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
    def get_current_weather(self, city):
        url = f"{self.base_url}/weather"
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'vi'
        }
        response = requests.get(url, params=params)
        return response.json()
```

**YouTube Integration**
```python
# YouTube Data API v3
from googleapiclient.discovery import build

# YouTube video download
from pytube import YouTube
import yt_dlp

class YouTubeDownloader:
    def __init__(self):
        self.api_key = config.YOUTUBE_API_KEY
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
```

### 3.3.5. Thư viện Multimedia

**Audio/Video Processing**
```python
# Pygame cho audio playback
import pygame.mixer

# Audio metadata
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC

# Video processing (future enhancement)
import cv2  # OpenCV cho computer vision
```

### 3.3.6. Thư viện Utilities

**Logging và Configuration**
```python
import logging
import configparser
import json
import os
from pathlib import Path

# Advanced logging với file rotation
from logging.handlers import RotatingFileHandler

# System monitoring
import psutil  # CPU, memory, network monitoring
```

**Data Persistence**
```python
# Local data storage
import sqlite3  # Cho conversation history
import pickle   # Cho object serialization
import json     # Cho configuration files
```

### 3.3.7. Dependencies Management

**Core Dependencies (requirements.txt)**
```python
# GUI Framework
PyQt5>=5.15.4

# AI and ML
google-generativeai>=0.3.1
numpy>=1.21.0

# Hardware Communication  
pyserial>=3.5
bleak>=0.14.0

# Speech Processing
gTTS>=2.2.3
SpeechRecognition>=3.8.1
pygame>=2.0.1
pyttsx3>=2.90

# API Clients
requests>=2.25.1
google-api-python-client>=2.0.0

# Multimedia
pytube>=12.1.0
yt-dlp>=2023.3.4
mutagen>=1.45.0

# System Utilities
psutil==5.9.0
pytz>=2021.1
```

**Platform-specific Dependencies**
```python
# Windows-specific
pywin32>=227; platform_system == "Windows"

# macOS-specific  
PyObjC==8.5; platform_system == "Darwin"

# Linux-specific
python3-dev; platform_system == "Linux"
portaudio19-dev; platform_system == "Linux"
```

### 3.3.8. Kiến trúc Module System

**Service Registration Pattern**
```python
class ServiceManager:
    def __init__(self):
        self.services = {}
        
    def register_service(self, name, service):
        self.services[name] = service
        
    def get_service(self, name):
        return self.services.get(name)

# Usage
service_manager = ServiceManager()
service_manager.register_service('gemini', GeminiClient())
service_manager.register_service('weather', WeatherService())
```

**Event-Driven Architecture**
```python
# PyQt Signal-Slot cho inter-component communication
class EventBus(QObject):
    # Define signals
    hardware_connected = pyqtSignal(dict)
    ai_response_ready = pyqtSignal(str)
    weather_updated = pyqtSignal(dict)
    
    def emit_event(self, event_name, data):
        signal = getattr(self, event_name, None)
        if signal:
            signal.emit(data)
```

---

**Tóm tắt:** Kiến trúc phần mềm MIS Smart Assistant được thiết kế theo nguyên tắc modular, sử dụng các thư viện mature và proven để đảm bảo tính ổn định và khả năng mở rộng. Hệ thống tích hợp nhiều công nghệ khác nhau một cách seamless để tạo ra trải nghiệm người dùng hoàn chỉnh.
