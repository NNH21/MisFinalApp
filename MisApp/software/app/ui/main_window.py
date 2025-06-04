import os
import sys
import platform
import time
from PyQt5.QtWidgets import (QMainWindow, QStackedWidget, QWidget,
                              QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QStatusBar, QAction, QMenu,
                              QTabWidget, QSplitter, QFrame, QToolBar,
                              QGraphicsDropShadowEffect, QSizePolicy)
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QColor, QFont

# Import UI widgets
from .time_widget import TimeWidget
from .weather_widget import WeatherWidget
from .chat_widget import ChatWidget
from .multimedia_widget import MultiMediaWidget
from .status_widget import StatusWidget
from .smart_vision_widget import SmartVisionWidget
from .lcd_widget import LCDWidget

# Import services
from ..utils import config, logger
from ..models.gemini_client import GeminiClient
from ..models.speech_processor import SpeechProcessor
from ..models.hardware_interface import HardwareInterface
from ..models.time_service import TimeService
from ..models.weather_service import WeatherService
from ..models.news_service import NewsService
from ..models.lcd_service import LCDService
from ..models.multimedia import MultimediaService
from ..models.launcher_service import LauncherService
from ..models.notification_sound_service import notification_service

class MainWindow(QMainWindow):
    """Main window of the MIS Smart Assistant application."""
    
    def __init__(self):
        super().__init__()
        # Initialize models
        self.hardware_interface = HardwareInterface()
        self.speech_processor = SpeechProcessor()
        self.weather_service = WeatherService()
        self.news_service = NewsService()
        self.time_service = TimeService(hardware_interface=self.hardware_interface)
        self.launcher_service = LauncherService()
        self.multimedia_service = MultimediaService()
        self.lcd_service = LCDService(hardware_interface=self.hardware_interface)
          # Initialize notification sound service
        self.notification_service = notification_service
        
        # Connect launcher service with multimedia service for music playback
        self.launcher_service.set_multimedia_service(self.multimedia_service)
        
        # Initialize Gemini client with services
        self.gemini_client = GeminiClient(
            time_service=self.time_service,
            weather_service=self.weather_service,
            news_service=self.news_service,
            launcher_service=self.launcher_service,
            multimedia_service=self.multimedia_service,
            hardware_interface=self.hardware_interface,
            lcd_service=self.lcd_service
        )
        
        # Set up the window
        self.setWindowTitle("MIS Smart Assistant")
        self.setMinimumSize(config.UI_WIDTH, config.UI_HEIGHT)
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               "resources", "icons", "assistant1.png")
        self.setWindowIcon(QIcon(icon_path))
        
        # Set up the theme
        self._setup_theme()
        
        # Create the central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create status widget (hardware status, connection info)
        self.status_widget = StatusWidget(self.hardware_interface)
        self.layout.addWidget(self.status_widget)
        
        # Create tab widget for various features
        self.tabs = QTabWidget()
        
        # Create and add chat widget
        self.chat_widget = ChatWidget(
            self.gemini_client, 
            self.speech_processor, 
            self.hardware_interface,
            self.time_service,
            self.weather_service
        )
        self.tabs.addTab(self.chat_widget, "Trợ lý")
        
        # Create and add weather widget
        self.weather_widget = WeatherWidget(self.weather_service)
        self.tabs.addTab(self.weather_widget, "Thời tiết")
        
        # Create and add time widget
        self.time_widget = TimeWidget(self.time_service, self.lcd_service)
        self.tabs.addTab(self.time_widget, "Thời gian")
        
        # Create and add smart vision widget
        self.smart_vision_widget = SmartVisionWidget(
            gemini_client=self.gemini_client,
            speech_processor=self.speech_processor
        )
        self.tabs.addTab(self.smart_vision_widget, "Smart Vision")
        
        # Create and add multimedia widget
        self.multimedia_widget = MultiMediaWidget(self.multimedia_service)
        self.tabs.addTab(self.multimedia_widget, "Media")
        
        # Create and add LCD widget
        self.lcd_widget = LCDWidget(hardware_interface=self.hardware_interface)
        self.tabs.addTab(self.lcd_widget, "LCD")
        
        # Add the tabs to the layout
        self.layout.addWidget(self.tabs)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("MIS Smart Assistant đã sẵn sàng")
        
        # Connect signals
        self._connect_signals()
        
        # Add menu animations and effects
        self._add_menu_animations()
        
        logger.info("Main window initialized")
        
    def _setup_theme(self):
        """Set up the UI theme."""
        self.setStyleSheet("""
            QMainWindow, QTabWidget, QWidget {
                background-color: #F5F5F7;
                color: #222222;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QTabWidget::pane {
                border: none;
                border-top: 1px solid #DDDDDD;
                background-color: #FFFFFF;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #F0F0F5;
                color: #666666;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #DDDDDD;
                border-bottom: none;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #007AFF;
                border-bottom: 2px solid #007AFF;
            }
            QTabBar::tab:hover:!selected {
                background-color: #E8E8ED;
            }
            QPushButton {
                background-color: #007AFF;
                color: #FFFFFF;
                border: none;
                padding: 8px 16px;
                margin: 2px;
                border-radius: 6px;
                font-weight: 500;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #0069D9;
            }
            QPushButton:pressed {
                background-color: #0052CC;
            }
            QLineEdit {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #DDDDDD;
                padding: 8px 12px;
                border-radius: 6px;
                selection-background-color: #007AFF;
                min-height: 30px;
            }
            QLineEdit:focus {
                border: 1px solid #007AFF;
            }
            QTextEdit {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #DDDDDD;
                padding: 8px;
                border-radius: 6px;
                selection-background-color: #007AFF;
            }
            QTextEdit:focus {
                border: 1px solid #007AFF;
            }
            QStatusBar {
                background-color: #6a7581;
                color: #FFFFFF;
                padding: 4px;
                font-weight: 500;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F5;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C8;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A0A0A8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QLabel {
                color: #333333;
                font-size: 14px;
            }
        """)
        
        # Set font size
        font = QFont("Segoe UI", config.UI_FONT_SIZE)
        font.setStyleHint(QFont.SansSerif)
        self.setFont(font)
    
    def _create_menu_bar(self):
        """Create the application menu bar with modern, professional styling."""
        menu_bar = self.menuBar()
        
        # Apply custom styling to menu bar
        menu_bar.setStyleSheet("""
            QMenuBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #06030e, stop: 0.5 #392c5b, stop: 1 #853aab);
                color: #E8ECEF;
                border: none;
                border-bottom: 2px solid #FFD700;
                padding: 6px;
                font-weight: 600;
                font-size: 14px;
                min-height: 30px;
            }
            QMenuBar::item {
                padding: 10px 20px;
                background: transparent;
                border-radius: 8px;
                margin: 2px 4px;
                color: #E8ECEF;
                font-weight: 500;
            }
            QMenuBar::item:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #FFD700, stop: 1 #32b9af);
                color: #1A3C4A;
                border: 1px solid rgba(255, 215, 0, 0.5);
                border-radius: 8px;
            }
            QMenuBar::item:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #32b9af, stop: 1 #B8972E);
                color: #1A3C4A;
                border: 1px solid rgba(255, 215, 0, 0.7);
            }
            QMenu {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #FFFFFF, stop: 1 #E8ECEF);
                color: #1A3C4A;
                border: 2px solid #FFD700;
                border-radius: 8px;
                padding: 6px;
                font-weight: 500;
            }
            QMenu::item {
                padding: 10px 20px;
                border-radius: 6px;
                margin: 1px;
                background: transparent;
                color: #1A3C4A;
                min-width: 150px;
            }
            QMenu::item:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #FFD700, stop: 1 #32b9af);
                color: #1A3C4A;
                border: 1px solid rgba(255, 215, 0, 0.5);
            }
            QMenu::item:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #32b9af, stop: 1 #B8972E);
                color: #1A3C4A;
            }
            QMenu::separator {
                height: 2px;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 transparent, stop: 0.5 #FFD700, stop: 1 transparent);
                margin: 5px 10px;
            }
        """)
        
        # File menu
        file_menu = menu_bar.addMenu("📁 &Tệp")
        
        # Exit action
        exit_action = QAction("🚪 &Thoát", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Thoát khỏi ứng dụng")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menu_bar.addMenu("⚙️ &Cài đặt")
        
        # Toggle voice response
        voice_action = QAction("🔊 &Phản hồi bằng giọng nói", self)
        voice_action.setCheckable(True)
        voice_action.setChecked(config.ENABLE_VOICE_RESPONSE)
        voice_action.setStatusTip("Bật/tắt phản hồi bằng giọng nói")
        voice_action.triggered.connect(self._toggle_voice_response)
        settings_menu.addAction(voice_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("❓ &Trợ giúp")
        
        # Connection status action
        connection_action = QAction("🔌 &Trạng thái kết nối", self)
        connection_action.setStatusTip("Hiển thị thông tin chi tiết về kết nối phần cứng")
        connection_action.triggered.connect(self._show_connection_status)
        help_menu.addAction(connection_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction("ℹ️ &Thông tin", self)
        about_action.setStatusTip("Hiển thị thông tin về ứng dụng")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """Connect signals between components."""
        self.hardware_interface.register_callback('CONNECTED', self._on_hardware_connected)
        self.hardware_interface.register_callback('DISCONNECTED', self._on_hardware_disconnected)
        self.hardware_interface.register_callback('LISTENING', self._on_hardware_listening)
        self.hardware_interface.register_callback('ACTIVATE_MICROPHONE', self.chat_widget._on_hardware_button_pressed)
        self.lcd_service.display_updated.connect(self._on_lcd_display_updated)
        self.lcd_service.scrolling_started.connect(self._on_lcd_scrolling_started)
        self.lcd_service.scrolling_stopped.connect(self._on_lcd_scrolling_stopped)
    
    def _on_hardware_connected(self, data):
        """Handle hardware connected event.""" 
        ip = data.get('ip', 'Unknown')
        port = data.get('port', self.hardware_interface.serial_port)
        message = f"Đã kết nối với phần cứng trên {port} (IP: {ip})" if ip != 'Unknown' else f"Đã kết nối với phần cứng trên {port}"
        self.statusBar.showMessage(message)
        self.status_widget.update_hardware_status(True, ip, port)
        logger.info(f"Hardware connected: {message}")
    
    def _on_hardware_disconnected(self, data):
        """Handle hardware disconnected event.""" 
        port = self.hardware_interface.serial_port
        message = f"Mất kết nối với phần cứng ({port})"
        if self.hardware_interface.auto_reconnect:
            message += " - Đang thử kết nối lại..."
        self.statusBar.showMessage(message)
        self.status_widget.update_hardware_status(False, None, port)
        logger.warning(f"Hardware disconnected: {message}")
    
    def _on_hardware_listening(self, data):
        """Handle hardware listening event.""" 
        self.statusBar.showMessage("Bạn cần nhấn nút microphone để bắt đầu nói...")
    
    def _on_lcd_display_updated(self, text):
        """Handle LCD display updated event."""
        if text.strip():
            self.statusBar.showMessage(f"LCD hiển thị: {text[:30]}...")
    
    def _on_lcd_scrolling_started(self):
        """Handle LCD scrolling started event."""
        self.statusBar.showMessage("LCD đang cuộn tin nhắn...")
    
    def _on_lcd_scrolling_stopped(self):
        """Handle LCD scrolling stopped event."""
        self.statusBar.showMessage("LCD đã dừng cuộn")
    
    def _toggle_voice_response(self, state):
        """Toggle voice response on/off.""" 
        config.ENABLE_VOICE_RESPONSE = state
        self.statusBar.showMessage(f"Phản hồi bằng giọng nói: {'Bật' if state else 'Tắt'}")
    
    def _show_about(self):
        """Show about dialog.""" 
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self, "Thông tin MIS Smart Assistant", 
            "MIS Smart Assistant v1.0\n\n"
            "Dự án trí tuệ nhân tạo kết hợp phần cứng ESP32.\n"
            "Liên hệ nhà phát triển HoangDev21 để biết thêm chi tiết.\n\n"
            "© 2025 MIS Team")
    
    def closeEvent(self, event):
        """Handle window close event.""" 
        try:
            if self.lcd_service:
                self.lcd_service.stop_scrolling()
            if self.hardware_interface:
                self.hardware_interface.disconnect()
            if self.speech_processor:
                self.speech_processor.stop_speaking()
            logger.info("Application shutting down")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
        event.accept()
    
    def _show_connection_status(self):
        """Show detailed connection status dialog."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle("Trạng thái kết nối phần cứng")
        dialog.setFixedSize(500, 400)
        layout = QVBoxLayout(dialog)
        conn_info = self.hardware_interface.get_connection_info()
        title = QLabel("Thông tin chi tiết về kết nối phần cứng:")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details = f"""
Trạng thái kết nối: {"✅ Đã kết nối" if conn_info['connected'] else "❌ Ngắt kết nối"}
Cổng hiện tại: {conn_info['port'] or "Không xác định"}
Cổng thành công cuối: {conn_info['last_successful_port'] or "Chưa có"}
Địa chỉ IP ESP32: {conn_info['esp_ip'] or "Chưa có"}
Tự động kết nối lại: {"✅ Bật" if conn_info['auto_reconnect'] else "❌ Tắt"}

Các cổng COM có sẵn:
"""
        for port in conn_info['available_ports']:
            details += f"  • {port}\n"
        if not conn_info['available_ports']:
            details += "  (Không tìm thấy cổng COM nào)\n"
        details += f"""
Cấu hình kết nối:
  • Tốc độ Baud: {self.hardware_interface.baud_rate}
  • Thời gian kiểm tra: {self.hardware_interface.connection_check_interval}s
  • Thời gian thử lại: {self.hardware_interface.reconnect_interval}s
"""
        details_text.setPlainText(details)
        layout.addWidget(details_text)
        button_layout = QHBoxLayout()
        reconnect_btn = QPushButton("🔄 Kết nối lại")
        reconnect_btn.clicked.connect(lambda: self._force_reconnect_and_update(details_text))
        button_layout.addWidget(reconnect_btn)
        auto_reconnect_btn = QPushButton("⚙️ Bật/Tắt tự động kết nối")
        auto_reconnect_btn.clicked.connect(lambda: self._toggle_auto_reconnect_and_update(details_text))
        button_layout.addWidget(auto_reconnect_btn)
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(dialog.close)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        dialog.exec_()
        
    def _force_reconnect_and_update(self, details_text):
        """Force reconnection and update the status dialog."""
        from PyQt5.QtWidgets import QMessageBox
        try:
            if self.hardware_interface.force_reconnect():
                QMessageBox.information(self, "Thành công", "Đã kết nối lại thành công!")
            else:
                QMessageBox.warning(self, "Thất bại", "Không thể kết nối lại. Kiểm tra ESP32 và cáp USB.")
            self._update_connection_details(details_text)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi kết nối lại: {str(e)}")
            
    def _toggle_auto_reconnect_and_update(self, details_text):
        """Toggle auto-reconnect and update the status dialog."""
        current_state = self.hardware_interface.auto_reconnect
        self.hardware_interface.set_auto_reconnect(not current_state)
        self._update_connection_details(details_text)
        
    def _update_connection_details(self, details_text):
        """Update the connection details in the dialog."""
        conn_info = self.hardware_interface.get_connection_info()
        details = f"""
Trạng thái kết nối: {"✅ Đã kết nối" if conn_info['connected'] else "❌ Ngắt kết nối"}
Cổng hiện tại: {conn_info['port'] or "Không xác định"}
Cổng thành công cuối: {conn_info['last_successful_port'] or "Chưa có"}
Địa chỉ IP ESP32: {conn_info['esp_ip'] or "Chưa có"}
Tự động kết nối lại: {"✅ Bật" if conn_info['auto_reconnect'] else "❌ Tắt"}

Các cổng COM có sẵn:
"""
        for port in conn_info['available_ports']:
            details += f"  • {port}\n"
        if not conn_info['available_ports']:
            details += "  (Không tìm thấy cổng COM nào)\n"
        details += f"""
Cấu hình kết nối:
  • Tốc độ Baud: {self.hardware_interface.baud_rate}
  • Thời gian kiểm tra: {self.hardware_interface.connection_check_interval}s
  • Thời gian thử lại: {self.hardware_interface.reconnect_interval}s
"""
        details_text.setPlainText(details)
    
    def _add_menu_animations(self):
        """Add smooth animations and effects to menu bar."""
        try:
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect
            
            # Add shadow effect to menu bar
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setBlurRadius(20)
            shadow_effect.setOffset(0, 4)
            shadow_effect.setColor(QColor(0, 0, 0, 100))
            self.menuBar().setGraphicsEffect(shadow_effect)
            
            # Animation for shadow blur radius on hover
            shadow_anim = QPropertyAnimation(shadow_effect, b"blurRadius")
            shadow_anim.setDuration(300)
            shadow_anim.setStartValue(20)
            shadow_anim.setEndValue(30)
            shadow_anim.setEasingCurve(QEasingCurve.InOutQuad)
            
            # Animation for menu bar opacity
            opacity_anim = QPropertyAnimation(self.menuBar(), b"windowOpacity")
            opacity_anim.setDuration(200)
            opacity_anim.setStartValue(0.95)
            opacity_anim.setEndValue(1.0)
            opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
            
            # Start animations on mouse enter
            def on_enter():
                shadow_anim.setDirection(QPropertyAnimation.Forward)
                shadow_anim.start()
                opacity_anim.setDirection(QPropertyAnimation.Forward)
                opacity_anim.start()
            
            # Reverse animations on mouse leave
            def on_leave():
                shadow_anim.setDirection(QPropertyAnimation.Backward)
                shadow_anim.start()
                opacity_anim.setDirection(QPropertyAnimation.Backward)
                opacity_anim.start()
            
            # Connect hover events
            self.menuBar().installEventFilter(self)
            self._menu_animations = {'enter': on_enter, 'leave': on_leave}
            
        except ImportError as e:
            logger.warning(f"Animation effects not available: {str(e)}")
    
    def eventFilter(self, obj, event):
        """Handle events for menu bar animations."""
        if obj == self.menuBar():
            if event.type() == event.Enter and self._menu_animations.get('enter'):
                self._menu_animations['enter']()
            elif event.type() == event.Leave and self._menu_animations.get('leave'):
                self._menu_animations['leave']()
        return super().eventFilter(obj, event)