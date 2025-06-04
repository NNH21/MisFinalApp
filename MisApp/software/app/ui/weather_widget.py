import sys
import datetime
import os
import time
from datetime import datetime
import urllib.request
from pathlib import Path
import requests
import io
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QGridLayout, QSizePolicy, QComboBox,
                             QLineEdit, QPushButton, QScrollArea, QCompleter)
from PyQt5.QtCore import Qt, QTimer, QSize, QPoint, QRectF, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QColor, QLinearGradient, QPainter, QPainterPath, QBrush, QPen, QIcon

from ..utils import config, logger
from ..models.weather_service import WeatherService

class DailyForecastWidget(QFrame):
    """Widget for displaying a single day's forecast."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(160)
        self.setStyleSheet("""
            DailyForecastWidget {
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.5);
            }
            QLabel {
                color: #333333;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the forecast widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Day of week and date
        self.day_label = QLabel("Thứ Hai")
        self.day_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.day_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.day_label)
        
        self.date_label = QLabel("01/01")
        self.date_label.setFont(QFont("Segoe UI", 10))
        self.date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.date_label)
        
        # Weather icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(60, 60)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label, 0, Qt.AlignHCenter)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.setSpacing(10)
        
        self.high_temp = QLabel("30°C")
        self.high_temp.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.high_temp.setStyleSheet("color: #FF5722;")
        temp_layout.addWidget(self.high_temp, 0, Qt.AlignRight)
        
        temp_layout.addWidget(QLabel("/"))
        
        self.low_temp = QLabel("25°C")
        self.low_temp.setFont(QFont("Segoe UI", 11))
        self.low_temp.setStyleSheet("color: #2196F3;")
        temp_layout.addWidget(self.low_temp, 0, Qt.AlignLeft)
        
        layout.addLayout(temp_layout)
        
        # Weather description
        self.description = QLabel("Trời nắng")
        self.description.setFont(QFont("Segoe UI", 10))
        self.description.setAlignment(Qt.AlignCenter)
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
    
    def update_forecast(self, data, date):
        """Update the forecast with data for a specific date."""
        day_names = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        
        day_of_week = date.weekday()  
        
        self.day_label.setText(day_names[day_of_week])
        self.date_label.setText(date.strftime("%d/%m"))
        
        self.high_temp.setText(f"{data['temp_max']:.1f}°C")
        self.low_temp.setText(f"{data['temp_min']:.1f}°C")
        
        self.description.setText(data['description'].capitalize())
        
        pixmap = data['icon_pixmap']
        self.icon_label.setPixmap(pixmap)

class WeatherWidget(QWidget):
    """Widget for displaying weather information."""
    
    location_changed = pyqtSignal(str)
    
    def __init__(self, weather_service):
        super().__init__()
        
        self.weather_service = weather_service
        
        self.weather_service.register_update_callback(self._on_weather_updated)
        
        # Danh sách các tỉnh thành Việt Nam có mã vùng
        self.vietnam_provinces = [
            "An Giang,VN", "Bà Rịa - Vũng Tàu,VN", "Bắc Giang,VN", "Bắc Kạn,VN", 
            "Bạc Liêu,VN", "Bắc Ninh,VN", "Bến Tre,VN", "Bình Định,VN", 
            "Bình Dương,VN", "Bình Phước,VN", "Bình Thuận,VN", "Cà Mau,VN", 
            "Cần Thơ,VN", "Cao Bằng,VN", "Đà Nẵng,VN", "Đắk Lắk,VN", 
            "Đắk Nông,VN", "Điện Biên,VN", "Đồng Nai,VN", "Đồng Tháp,VN", 
            "Gia Lai,VN", "Hà Giang,VN", "Hà Nam,VN", "Hà Nội,VN", 
            "Hà Tĩnh,VN", "Hải Dương,VN", "Hải Phòng,VN", "Hậu Giang,VN", 
            "Hòa Bình,VN", "Hưng Yên,VN", "Khánh Hòa,VN", "Kiên Giang,VN", 
            "Kon Tum,VN", "Lai Châu,VN", "Lâm Đồng,VN", "Lạng Sơn,VN", 
            "Lào Cai,VN", "Long An,VN", "Nam Định,VN", "Nghệ An,VN", 
            "Ninh Bình,VN", "Ninh Thuận,VN", "Phú Thọ,VN", "Phú Yên,VN", 
            "Quảng Bình,VN", "Quảng Nam,VN", "Quảng Ngãi,VN", "Quảng Ninh,VN", 
            "Quảng Trị,VN", "Sóc Trăng,VN", "Sơn La,VN", "Tây Ninh,VN", 
            "Thái Bình,VN", "Thái Nguyên,VN", "Thanh Hóa,VN", "Thừa Thiên Huế,VN", 
            "Tiền Giang,VN", "TP. Hồ Chí Minh,VN", "Trà Vinh,VN", "Tuyên Quang,VN", 
            "Vĩnh Long,VN", "Vĩnh Phúc,VN", "Yên Bái,VN"
        ]
        
        self.international_cities = [
            "New York,US", "London,GB", "Tokyo,JP", "Beijing,CN", "Sydney,AU",
            "Paris,FR", "Berlin,DE", "Moscow,RU", "Singapore,SG", "Seoul,KR"
        ]
        
        self.current_location = config.WEATHER_LOCATION
        
        self._setup_ui()
        
        self.weather_service.update_weather()
        self._update_display()
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(60000) 
    
    def _setup_ui(self):
        """Set up the weather UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        search_panel = QFrame()
        search_panel.setObjectName("searchPanel")
        search_panel.setStyleSheet("""
            QFrame#searchPanel {
                background-color: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        search_layout = QHBoxLayout(search_panel)
        search_layout.setContentsMargins(15, 10, 15, 10)
        
        self.location_search = QLineEdit()
        self.location_search.setPlaceholderText("Tìm kiếm địa điểm...")
        self.location_search.setMinimumWidth(250)
        self.location_search.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border-radius: 8px;
                border: 1px solid #BDBDBD;
                font-size: 14px;
                background-color: white;
                color: #333333;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)
        
        location_list = [province.split(',')[0] for province in self.vietnam_provinces]
        location_list.extend([city.split(',')[0] for city in self.international_cities])
        completer = QCompleter(location_list)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.location_search.setCompleter(completer)
        
        # Province dropdown
        self.location_combo = QComboBox()
        self.location_combo.addItem("Chọn tỉnh/thành phố...")
        
        # Add Vietnamese provinces to combo box
        for province in self.vietnam_provinces:
            province_name = province.split(',')[0]
            self.location_combo.addItem(province_name)
        
        # Add separator and international cities
        self.location_combo.insertSeparator(self.location_combo.count())
        self.location_combo.addItem("--- Thành phố quốc tế ---")
        
        for city in self.international_cities:
            city_name = city.split(',')[0]
            self.location_combo.addItem(city_name)
        
        self.location_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border-radius: 8px;
                border: 1px solid #BDBDBD;
                font-size: 14px;
                background-color: white;
                color: #333333;
            }
            QComboBox:focus {
                border: 1px solid #2196F3;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #BDBDBD;
                border-left-style: solid;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox::down-arrow {
                image: url(dropdown-arrow.png);
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #2196F3;
                selection-color: white;
                border: 1px solid #BDBDBD;
            }
        """)
        
        # Search button
        self.search_button = QPushButton("Tìm kiếm")
        self.search_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border-radius: 8px;
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        
        search_layout.addWidget(self.location_search)
        search_layout.addWidget(self.location_combo)
        search_layout.addWidget(self.search_button)
        
        # Connect signals
        self.search_button.clicked.connect(self._on_search_clicked)
        self.location_combo.currentIndexChanged.connect(self._on_location_selected)
        self.location_search.returnPressed.connect(self._on_search_clicked)
        
        main_layout.addWidget(search_panel)
        
        # Current weather frame
        self.current_weather_frame = QFrame()
        self.current_weather_frame.setObjectName("currentWeatherFrame")
        self.current_weather_frame.setMinimumHeight(200)
        self.current_weather_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        current_weather_layout = QVBoxLayout(self.current_weather_frame)
        current_weather_layout.setContentsMargins(20, 20, 20, 20)
        
        # Location and time
        location_layout = QHBoxLayout()
        
        self.location_label = QLabel("Đà Nẵng, Việt Nam")
        self.location_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.location_label.setStyleSheet("color: #FFFFFF;")
        location_layout.addWidget(self.location_label)
        
        self.time_label = QLabel(datetime.now().strftime("%H:%M - %d/%m/%Y"))
        self.time_label.setFont(QFont("Segoe UI", 12))
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setStyleSheet("color: #FFFFFF;")
        location_layout.addWidget(self.time_label)
        
        current_weather_layout.addLayout(location_layout)
        
        # Current conditions
        conditions_layout = QHBoxLayout()
        
        # Weather icon and temperature
        icon_temp_layout = QVBoxLayout()
        
        self.weather_icon = QLabel()
        self.weather_icon.setFixedSize(120, 120)
        icon_temp_layout.addWidget(self.weather_icon, 0, Qt.AlignHCenter)
        
        self.temperature_label = QLabel("25°C")
        self.temperature_label.setFont(QFont("Segoe UI", 36, QFont.Bold))
        self.temperature_label.setStyleSheet("color: #FFFFFF;")
        icon_temp_layout.addWidget(self.temperature_label, 0, Qt.AlignHCenter)
        
        conditions_layout.addLayout(icon_temp_layout)
        
        # Vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(1)
        separator.setMidLineWidth(1)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2);")
        conditions_layout.addWidget(separator)
        
        # Weather details
        details_layout = QGridLayout()
        details_layout.setVerticalSpacing(10)
        details_layout.setHorizontalSpacing(20)
        
        # Description
        self.description_label = QLabel("Đang cập nhật...")
        self.description_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.description_label.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.description_label, 0, 0, 1, 2)
        
        # Feels like
        feels_like_label = QLabel("Cảm giác như:")
        feels_like_label.setFont(QFont("Segoe UI", 10))
        feels_like_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        details_layout.addWidget(feels_like_label, 1, 0)
        
        self.feels_like_value = QLabel("--°C")
        self.feels_like_value.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.feels_like_value.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.feels_like_value, 1, 1)
        
        # Humidity
        humidity_label = QLabel("Độ ẩm:")
        humidity_label.setFont(QFont("Segoe UI", 10))
        humidity_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        details_layout.addWidget(humidity_label, 2, 0)
        
        self.humidity_value = QLabel("--%")
        self.humidity_value.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.humidity_value.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.humidity_value, 2, 1)
        
        # Wind
        wind_label = QLabel("Gió:")
        wind_label.setFont(QFont("Segoe UI", 10))
        wind_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        details_layout.addWidget(wind_label, 3, 0)
        
        self.wind_value = QLabel("-- m/s")
        self.wind_value.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.wind_value.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.wind_value, 3, 1)
        
        # Add a column gap
        details_layout.setColumnMinimumWidth(2, 40)
        
        # Pressure
        pressure_label = QLabel("Áp suất:")
        pressure_label.setFont(QFont("Segoe UI", 10))
        pressure_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        details_layout.addWidget(pressure_label, 1, 3)
        
        self.pressure_value = QLabel("-- hPa")
        self.pressure_value.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.pressure_value.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.pressure_value, 1, 4)
        
        # Visibility
        visibility_label = QLabel("Tầm nhìn:")
        visibility_label.setFont(QFont("Segoe UI", 10))
        visibility_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        details_layout.addWidget(visibility_label, 2, 3)
        
        self.visibility_value = QLabel("-- km")
        self.visibility_value.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.visibility_value.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.visibility_value, 2, 4)
        
        # UV Index
        uv_label = QLabel("Chỉ số UV:")
        uv_label.setFont(QFont("Segoe UI", 10))
        uv_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        details_layout.addWidget(uv_label, 3, 3)
        
        self.uv_value = QLabel("--")
        self.uv_value.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.uv_value.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.uv_value, 3, 4)
        
        conditions_layout.addLayout(details_layout)
        conditions_layout.setStretch(0, 1)
        conditions_layout.setStretch(2, 2)
        
        current_weather_layout.addLayout(conditions_layout)
        
        # Add current weather frame to main layout
        main_layout.addWidget(self.current_weather_frame)
        
        # Forecast title (now 10 days)
        forecast_title_frame = QFrame()
        forecast_title_frame.setObjectName("forecastTitleFrame")
        forecast_title_frame.setStyleSheet("""
            QFrame#forecastTitleFrame {
                background-color: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        forecast_title_layout = QHBoxLayout(forecast_title_frame)
        forecast_title_layout.setContentsMargins(15, 10, 15, 10)
        
        forecast_title = QLabel("Dự báo 10 ngày tới")
        forecast_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        forecast_title.setStyleSheet("color: #333333;")
        forecast_title_layout.addWidget(forecast_title)
        
        main_layout.addWidget(forecast_title_frame)
        
        # Forecast scrollable area
        forecast_scroll = QScrollArea()
        forecast_scroll.setObjectName("forecastScroll")
        forecast_scroll.setWidgetResizable(True)
        forecast_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        forecast_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        forecast_scroll.setMinimumHeight(190)
        forecast_scroll.setMaximumHeight(190)
        forecast_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:horizontal {
                border: none;
                background: rgba(255, 255, 255, 0.2);
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 0.8);
                min-width: 30px;
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # Forecast container
        forecast_container = QWidget()
        forecast_container.setStyleSheet("background: transparent;")
        forecast_scroll.setWidget(forecast_container)
        
        # Forecast layout
        self.forecast_layout = QHBoxLayout(forecast_container)
        self.forecast_layout.setContentsMargins(0, 0, 0, 0)
        self.forecast_layout.setSpacing(15)
        
        # Initialize daily forecast widgets
        self.forecast_widgets = []
        for i in range(10):
            daily_widget = DailyForecastWidget()
            self.forecast_layout.addWidget(daily_widget)
            self.forecast_widgets.append(daily_widget)
            
        # Add forecast scroll area to main layout
        main_layout.addWidget(forecast_scroll)
        
        # Add a stretcher to push everything up
        main_layout.addStretch()
        
        # Set custom styling for frames
        self._setup_styling()
    
    def _setup_styling(self):
        """Set up custom styling for weather widget components."""
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            
            QFrame#currentWeatherFrame {
                border-radius: 15px;
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                 stop:0 #2196F3, stop:1 #1976D2);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        
        # Apply drop shadow effects to frames for better depth
        try:
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect
            from PyQt5.QtCore import QPoint
            
            # Add shadow to current weather frame
            shadow1 = QGraphicsDropShadowEffect()
            shadow1.setBlurRadius(20)
            shadow1.setColor(QColor(0, 0, 0, 60))
            shadow1.setOffset(QPoint(0, 5))
            self.current_weather_frame.setGraphicsEffect(shadow1)
            
        except ImportError:
            logger.warning("QGraphicsDropShadowEffect not available, skipping shadow effects")
    
    def _update_display(self):
        """Update the weather display with current data."""
        # Update time
        self.time_label.setText(datetime.now().strftime("%H:%M - %d/%m/%Y"))
        
        # Get weather data
        weather_data = self.weather_service.get_current_weather()
        forecast_data = self.weather_service.get_forecast()
        
        if not weather_data:
            # Display error message if no data available
            self.description_label.setText("Không thể lấy dữ liệu thời tiết")
            return
        
        try:
            # Update location
            city = weather_data.get('name', 'Không xác định')
            country = weather_data.get('sys', {}).get('country', '')
            country_name = "Việt Nam" if country == "VN" else country
            self.location_label.setText(f"{city}, {country_name}")
            
            # Update current conditions
            temp = weather_data.get('main', {}).get('temp', 0)
            self.temperature_label.setText(f"{temp:.1f}°C")
            
            feels_like = weather_data.get('main', {}).get('feels_like', 0)
            self.feels_like_value.setText(f"{feels_like:.1f}°C")
            
            humidity = weather_data.get('main', {}).get('humidity', 0)
            self.humidity_value.setText(f"{humidity}%")
            
            wind_speed = weather_data.get('wind', {}).get('speed', 0)
            self.wind_value.setText(f"{wind_speed} m/s")
            
            pressure = weather_data.get('main', {}).get('pressure', 0)
            self.pressure_value.setText(f"{pressure} hPa")
            
            visibility = weather_data.get('visibility', 0) / 1000  # Convert from m to km
            self.visibility_value.setText(f"{visibility:.1f} km")
            
            # Set UV Index (estimated)
            clouds = weather_data.get('clouds', {}).get('all', 0)
            current_hour = datetime.now().hour
            uv_index = self._estimate_uv_index(clouds, current_hour)
            self.uv_value.setText(f"{uv_index} ({self._get_uv_description(uv_index)})")
            
            # Set description
            description = weather_data.get('weather', [{}])[0].get('description', 'Không xác định')
            self.description_label.setText(description.capitalize())
            
            # Set weather icon
            icon_code = weather_data.get('weather', [{}])[0].get('icon', '01d')
            self._set_weather_icon(icon_code)
            
            # Update forecast if available
            if forecast_data and 'list' in forecast_data:
                self._update_forecast(forecast_data)
            
        except Exception as e:
            logger.error(f"Error updating weather display: {str(e)}")
            self.description_label.setText("Lỗi khi hiển thị dữ liệu")
    
    def _update_forecast(self, forecast_data):
        """Update the forecast display with forecast data."""
        # Check if there's forecast data
        if not forecast_data or 'list' not in forecast_data:
            return
            
        try:
            # Get the list of forecasts
            forecasts = forecast_data['list']
            
            # Organize forecasts by day
            daily_forecasts = {}
            
            for forecast in forecasts:
                # Get date from timestamp
                dt = datetime.fromtimestamp(forecast['dt'])
                date = dt.date()
                
                # Store each forecast by date
                if date not in daily_forecasts:
                    daily_forecasts[date] = {
                        'temp_max': -100,
                        'temp_min': 100,
                        'icon_code': '',
                        'description': '',
                        'forecasts': []
                    }
                
                # Add this forecast to the date's list
                daily_forecasts[date]['forecasts'].append(forecast)
                
                # Update min/max temperatures
                temp = forecast['main']['temp']
                if temp > daily_forecasts[date]['temp_max']:
                    daily_forecasts[date]['temp_max'] = temp
                if temp < daily_forecasts[date]['temp_min']:
                    daily_forecasts[date]['temp_min'] = temp
                
                # Use noon forecast for the icon and description if available
                if dt.hour == 12 or (dt.hour == 15 and not daily_forecasts[date]['icon_code']):
                    daily_forecasts[date]['icon_code'] = forecast['weather'][0]['icon']
                    daily_forecasts[date]['description'] = forecast['weather'][0]['description']
            
            # If we don't have an icon/description, use the first forecast of the day
            for date, day_data in daily_forecasts.items():
                if not day_data['icon_code'] and day_data['forecasts']:
                    day_data['icon_code'] = day_data['forecasts'][0]['weather'][0]['icon']
                    day_data['description'] = day_data['forecasts'][0]['weather'][0]['description']
            
            # Sort dates
            dates = sorted(daily_forecasts.keys())
            
            # Update forecast widgets (up to 10 days)
            for i, date in enumerate(dates[:10]):
                day_data = daily_forecasts[date]
                
                # Add icon pixmap to data
                icon_pixmap = self._get_weather_icon_pixmap(day_data['icon_code'], size=60)
                day_data['icon_pixmap'] = icon_pixmap
                
                # Update the widget
                self.forecast_widgets[i].update_forecast(day_data, date)
        
        except Exception as e:
            logger.error(f"Error updating forecast display: {str(e)}")
    
    def _on_search_clicked(self):
        """Handle search button click."""
        location = self.location_search.text().strip()
        if location:
            self._search_location(location)
    
    def _on_location_selected(self, index):
        """Handle location selection from dropdown."""
        # Skip headers and separators
        if index <= 0 or self.location_combo.currentText().startswith("---"):
            return
            
        location = self.location_combo.currentText()
        self._search_location(location)
    
    def _search_location(self, location_name):
        """Search for a location and update weather."""
        # Find the location in our list to get the country code
        location_query = location_name
        
        # Search in Vietnamese provinces
        for province in self.vietnam_provinces:
            if province.split(',')[0].lower() == location_name.lower():
                location_query = province
                break
                
        # Search in international cities if not found
        if location_query == location_name:
            for city in self.international_cities:
                if city.split(',')[0].lower() == location_name.lower():
                    location_query = city
                    break
        
        # Update location and request weather update
        self.current_location = location_query
        self.weather_service.set_location(location_query)
        
        # Update location search field
        self.location_search.setText(location_name)
        
        # Emit location changed signal
        self.location_changed.emit(location_query)
    
    def _set_weather_icon(self, icon_code):
        """Set the weather icon based on the icon code."""
        pixmap = self._get_weather_icon_pixmap(icon_code, size=120)
        self.weather_icon.setPixmap(pixmap)
    
    def _get_weather_icon_pixmap(self, icon_code, size=100):
        """Get the weather icon pixmap from icon code."""
        # Try to load icon from resources
        current_dir = os.path.dirname(os.path.abspath(__file__))
        resources_dir = os.path.abspath(os.path.join(current_dir, '../../../resources/weather_icons'))
        icon_path = os.path.join(resources_dir, f"{icon_code}.png")
        
        # Create a pixmap with the specified size
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        if os.path.exists(icon_path):
            # Load icon from file
            pixmap = QPixmap(icon_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            # If icon file doesn't exist, try to download it from OpenWeatherMap
            icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
            try:
                response = requests.get(icon_url, stream=True)
                response.raise_for_status()
                
                # Create pixmap from the downloaded image
                img_data = response.content
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Create the directory if it doesn't exist
                os.makedirs(resources_dir, exist_ok=True)
                
                # Save for future use
                pixmap.save(icon_path, "PNG")
                
            except Exception as e:
                logger.error(f"Error downloading weather icon: {str(e)}")
                
                # Create a fallback icon
                if 'n' in icon_code:  # Night icon
                    self._draw_night_icon(pixmap, size)
                elif 'd' in icon_code:  # Day icon
                    self._draw_day_icon(pixmap, icon_code, size)
                else:
                    # Generic icon
                    self._draw_day_icon(pixmap, "01d", size)
        
        return pixmap
    
    def _draw_day_icon(self, pixmap, icon_code, size):
        """Draw a day weather icon on the pixmap."""
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create rect
        rect = pixmap.rect()
        
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(255, 200, 0)))
        
        # Convert QRect to QRectF
        rectF = QRectF(rect)
        
        # Draw icon based on weather code
        if '01' in icon_code:  # Clear sky
            # Draw sun
            painter.drawEllipse(rectF.adjusted(size/4, size/4, -size/4, -size/4))
        elif '02' in icon_code:  # Few clouds
            # Draw sun
            painter.drawEllipse(rectF.adjusted(size*0.15, size*0.15, -size*0.45, -size*0.45))
            
            # Draw cloud
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(rectF.adjusted(size*0.3, size*0.4, -size*0.1, -size*0.2))
        elif '03' in icon_code or '04' in icon_code:  # Clouds
            # Draw clouds
            painter.setBrush(QBrush(QColor(200, 200, 200)))
            painter.drawEllipse(rectF.adjusted(size*0.15, size*0.3, -size*0.55, -size*0.4))
            
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(rectF.adjusted(size*0.35, size*0.25, -size*0.15, -size*0.35))
        elif '09' in icon_code or '10' in icon_code:  # Rain
            # Draw cloud
            painter.setBrush(QBrush(QColor(200, 200, 200)))
            painter.drawEllipse(rectF.adjusted(size*0.2, size*0.2, -size*0.2, -size*0.5))
            
            # Draw rain drops
            painter.setPen(QPen(QColor(30, 144, 255), 2))
            painter.drawLine(int(rect.left() + size*0.3), int(rect.top() + size*0.6), 
                            int(rect.left() + size*0.2), int(rect.top() + size*0.8))
            painter.drawLine(int(rect.left() + size*0.5), int(rect.top() + size*0.55), 
                            int(rect.left() + size*0.4), int(rect.top() + size*0.75))
            painter.drawLine(int(rect.left() + size*0.7), int(rect.top() + size*0.6), 
                            int(rect.left() + size*0.6), int(rect.top() + size*0.8))
        elif '11' in icon_code:  # Thunderstorm
            # Draw cloud
            painter.setBrush(QBrush(QColor(100, 100, 100)))
            painter.drawEllipse(rectF.adjusted(size*0.2, size*0.2, -size*0.2, -size*0.5))
            
            # Draw lightning
            painter.setPen(QPen(QColor(255, 255, 0), 3))
            painter.drawLine(int(rect.left() + size*0.5), int(rect.top() + size*0.4), 
                            int(rect.left() + size*0.4), int(rect.top() + size*0.65))
            painter.drawLine(int(rect.left() + size*0.4), int(rect.top() + size*0.65), 
                            int(rect.left() + size*0.55), int(rect.top() + size*0.65))
            painter.drawLine(int(rect.left() + size*0.55), int(rect.top() + size*0.65), 
                            int(rect.left() + size*0.45), int(rect.top() + size*0.9))
        elif '13' in icon_code:  # Snow
            # Draw cloud
            painter.setBrush(QBrush(QColor(200, 200, 200)))
            painter.drawEllipse(rectF.adjusted(size*0.2, size*0.2, -size*0.2, -size*0.5))
            
            # Draw snowflakes
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawEllipse(int(rect.left() + size*0.3), int(rect.top() + size*0.6), int(size*0.1), int(size*0.1))
            painter.drawEllipse(int(rect.left() + size*0.5), int(rect.top() + size*0.7), int(size*0.1), int(size*0.1))
            painter.drawEllipse(int(rect.left() + size*0.7), int(rect.top() + size*0.6), int(size*0.1), int(size*0.1))
        elif '50' in icon_code:  # Mist
            # Draw fog lines
            painter.setPen(QPen(QColor(200, 200, 200), 3))
            painter.drawLine(int(rect.left() + size*0.2), int(rect.top() + size*0.3), 
                           int(rect.left() + size*0.8), int(rect.top() + size*0.3))
            painter.drawLine(int(rect.left() + size*0.3), int(rect.top() + size*0.45), 
                           int(rect.left() + size*0.7), int(rect.top() + size*0.45))
            painter.drawLine(int(rect.left() + size*0.2), int(rect.top() + size*0.6), 
                           int(rect.left() + size*0.8), int(rect.top() + size*0.6))
            painter.drawLine(int(rect.left() + size*0.3), int(rect.top() + size*0.75), 
                           int(rect.left() + size*0.7), int(rect.top() + size*0.75))
        
        painter.end()
    
    def _draw_night_icon(self, pixmap, size):
        """Draw a night weather icon on the pixmap."""
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create rect
        rect = pixmap.rect()
        rectF = QRectF(rect)
        
        # Draw moon
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(200, 200, 255)))
        
        # Draw moon
        path = QPainterPath()
        path.addEllipse(rectF.adjusted(size*0.25, size*0.25, -size*0.25, -size*0.25))
        
        # Add crescent by subtracting an offset ellipse
        subtract_path = QPainterPath()
        subtract_path.addEllipse(rectF.adjusted(size*0.15, size*0.25, -size*0.35, -size*0.25))
        path = path.subtracted(subtract_path)
        
        painter.drawPath(path)
        painter.end()
    
    def _estimate_uv_index(self, cloud_cover, current_hour):
        """Estimate UV index based on time of day and cloud cover."""
        if current_hour >= 19 or current_hour <= 5:
            return 0  # Night time
            
        max_uv = 11  # Maximum possible UV index on a clear day
        cloud_factor = 1 - (cloud_cover / 100)  # Reduction factor due to clouds
        time_factor = 1.0
            
        # Time of day affects UV intensity
        if current_hour < 10:
            time_factor = 0.5 + (current_hour - 5) * 0.1  # Morning ramp up
        elif current_hour > 16:
            time_factor = 0.5 - (current_hour - 16) * 0.1  # Afternoon ramp down
            
        uv_index = round(max_uv * cloud_factor * time_factor)
        return min(11, max(0, uv_index))
    
    def _get_uv_description(self, index):
        """Get a description of the UV index level."""
        if index <= 2:
            return "thấp"
        elif index <= 5:
            return "trung bình"
        elif index <= 7:
            return "cao"
        elif index <= 10:
            return "rất cao"
        else:
            return "cực kỳ cao"
    
    def _on_weather_updated(self, data):
        """Callback function when weather data is updated."""
        self._update_display()
    
    def paintEvent(self, event):
        """Custom paint event for better-looking background."""
        super().paintEvent(event)
        
        # Get gradient colors based on time of day
        current_hour = datetime.now().hour
        
        if 6 <= current_hour < 10:  # Morning
            top_color = QColor(135, 206, 250)  # Light sky blue
            bottom_color = QColor(240, 248, 255)  # Alice blue
        elif 10 <= current_hour < 16:  # Day
            top_color = QColor(100, 181, 246)  # Light blue
            bottom_color = QColor(187, 222, 251)  # Lighter blue
        elif 16 <= current_hour < 19:  # Evening
            top_color = QColor(255, 183, 77)  # Light orange
            bottom_color = QColor(255, 236, 179)  # Light yellow
        else:  # Night
            top_color = QColor(63, 81, 181)  # Indigo
            bottom_color = QColor(121, 134, 203)  # Light indigo
        
        # Create and draw the gradient
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, top_color)
        gradient.setColorAt(1, bottom_color)
        
        painter.fillRect(self.rect(), gradient)