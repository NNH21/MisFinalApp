from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QPushButton, 
                           QSlider, QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QIcon

from ..models.lcd_service import LCDService

class LCDMessageWidget(QWidget):
    """
    Bottom panel widget for LCD message display with professional styling.
    Features: message input, scroll speed control, display/stop buttons.
    """
    
    def __init__(self, hardware_interface=None, parent=None):
        super().__init__(parent)
        self.lcd_service = LCDService(hardware_interface)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the LCD message control UI with compact, professional design."""
        # Main horizontal layout with minimal margins
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)
        
        # Create main frame with subtle shadow effect
        main_frame = QFrame()
        main_frame.setFrameStyle(QFrame.StyledPanel)
        main_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E1E5E9;
                border-radius: 6px;
                padding: 2px;
            }
        """)
        
        # Add compact shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(6)
        shadow.setXOffset(0)
        shadow.setYOffset(1)
        shadow.setColor(Qt.gray)
        main_frame.setGraphicsEffect(shadow)
        
        # Layout for the frame content
        frame_layout = QHBoxLayout(main_frame)
        frame_layout.setContentsMargins(4, 3, 4, 3)
        frame_layout.setSpacing(4)
        
        # LCD icon/label - compact
        lcd_label = QLabel("📟")
        lcd_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #4A90E2;
                font-weight: bold;
                padding: 2px;
            }
        """)
        lcd_label.setFixedSize(20, 20)
        frame_layout.addWidget(lcd_label)
        
        # Message input field - compact
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Nhập thông điệp hiển thị lên LCD...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E8ECF1;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                background-color: #FAFBFC;
                color: #2D3748;
                min-height: 18px;
                margin-top: -8px; /* Move up by reducing top margin */
            }
            QLineEdit:focus {
                border-color: #4A90E2;
                background-color: #FFFFFF;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #CBD5E0;
            }
        """)
        self.message_input.setMaximumHeight(26)
        frame_layout.addWidget(self.message_input, 1)  # Take most space
        
        # Speed control section - compact
        speed_frame = QFrame()
        speed_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        speed_layout = QHBoxLayout(speed_frame)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(3)
        
        speed_icon = QLabel("⚡")
        speed_icon.setStyleSheet("font-size: 12px; color: #718096;")
        speed_icon.setFixedSize(16, 16)
        speed_layout.addWidget(speed_icon)
        
        # Speed slider - compact
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(100)
        self.speed_slider.setMaximum(2000) 
        self.speed_slider.setValue(500)
        self.speed_slider.setFixedWidth(60)
        self.speed_slider.setFixedHeight(20)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #E2E8F0;
                height: 4px;
                background: #F7FAFC;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #4A90E2;
                border: 1px solid #3182CE;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #63B3ED;
            }
            QSlider::handle:horizontal:pressed {
                background: #3182CE;
            }
        """)
        speed_layout.addWidget(self.speed_slider)
        
        frame_layout.addWidget(speed_frame)
        
        # Control buttons - compact
        self.display_button = QPushButton("📤")
        self.display_button.setToolTip("Hiển thị thông điệp")
        self.display_button.setStyleSheet("""
            QPushButton {
                background-color: #48BB78;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                min-width: 24px;
                max-width: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #38A169;
            }
            QPushButton:pressed {
                background-color: #2F855A;
            }
        """)
        self.display_button.setFixedSize(24, 24)
        frame_layout.addWidget(self.display_button)
        
        self.stop_button = QPushButton("⏹️")
        self.stop_button.setToolTip("Dừng và tắt LCD")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #F56565;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                min-width: 24px;
                max-width: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #E53E3E;
            }
            QPushButton:pressed {
                background-color: #C53030;
            }
            QPushButton:disabled {
                background-color: #CBD5E0;
                color: #A0AEC0;
            }
        """)
        self.stop_button.setFixedSize(24, 24)
        self.stop_button.setEnabled(False)
        frame_layout.addWidget(self.stop_button)
        
        # Add the frame to main layout
        main_layout.addWidget(main_frame)
        self.setLayout(main_layout)
        
        # Set overall widget styling - compact height
        self.setStyleSheet("""
            LCDMessageWidget {
                background-color: #F8F9FA;
                border-top: 1px solid #E9ECEF;
            }
        """)
        self.setFixedHeight(40)  # Reduced from 60 to 40
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Button connections
        self.display_button.clicked.connect(self._on_display_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.message_input.returnPressed.connect(self._on_display_clicked)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        
        # LCD service signal connections
        self.lcd_service.scrolling_started.connect(self._on_scrolling_started)
        self.lcd_service.scrolling_stopped.connect(self._on_scrolling_stopped)
        
    @pyqtSlot()
    def _on_display_clicked(self):
        """Handle display button click."""
        message = self.message_input.text().strip()
        if message:
            self.lcd_service.set_display_text(message)
            if len(message) > 16:  # Need scrolling for messages longer than LCD width
                self.lcd_service.start_scroll()
            self.message_input.clear()
    
    @pyqtSlot()
    def _on_stop_clicked(self):
        """Handle stop button click."""
        self.lcd_service.clear_and_reset()
        
    @pyqtSlot(int)
    def _on_speed_changed(self, value):
        """Handle speed slider change."""
        speed = 2100 - value
        self.lcd_service.set_scroll_speed(speed)
        
    @pyqtSlot()
    def _on_scrolling_started(self):
        """Handle scrolling started."""
        self.stop_button.setEnabled(True)
        self.display_button.setToolTip("Đang cuộn...")
        
    @pyqtSlot()
    def _on_scrolling_stopped(self):
        """Handle scrolling stopped."""
        self.stop_button.setEnabled(False)
        self.display_button.setToolTip("Hiển thị thông điệp")
    
    def set_hardware_interface(self, hardware_interface):
        """Set hardware interface for LCD service."""
        self.lcd_service.set_hardware_interface(hardware_interface)
        
    def get_lcd_service(self):
        """Get the LCD service instance."""
        return self.lcd_service
        
    def process_voice_command(self, command):
        """Process voice commands for LCD display."""
        return self.lcd_service.process_voice_command(command)
        
        # LCD icon/label - compact
        lcd_label = QLabel("📟")
        lcd_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #4A90E2;
                font-weight: bold;
                padding: 2px;
            }
        """)
        lcd_label.setFixedSize(20, 20)
        frame_layout.addWidget(lcd_label)
        
        # Message input field - compact
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Nhập thông điệp hiển thị lên LCD...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E8ECF1;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                background-color: #FAFBFC;
                color: #2D3748;
                min-height: 18px;
                margin-top: -8px; /* Move up by reducing top margin */
            }
            QLineEdit:focus {
                border-color: #4A90E2;
                background-color: #FFFFFF;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #CBD5E0;
            }
        """)
        self.message_input.setMaximumHeight(26)
        frame_layout.addWidget(self.message_input, 1)  # Take most space
        
        # Speed control section - compact
        speed_frame = QFrame()
        speed_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        speed_layout = QHBoxLayout(speed_frame)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(3)
        
        speed_icon = QLabel("⚡")
        speed_icon.setStyleSheet("font-size: 12px; color: #718096;")
        speed_icon.setFixedSize(16, 16)
        speed_layout.addWidget(speed_icon)
        
        # Speed slider - compact
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(100)
        self.speed_slider.setMaximum(2000) 
        self.speed_slider.setValue(500)
        self.speed_slider.setFixedWidth(60)
        self.speed_slider.setFixedHeight(20)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #E2E8F0;
                height: 4px;
                background: #F7FAFC;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #4A90E2;
                border: 1px solid #3182CE;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #63B3ED;
            }
            QSlider::handle:horizontal:pressed {
                background: #3182CE;
            }
        """)
        speed_layout.addWidget(self.speed_slider)
        
        frame_layout.addWidget(speed_frame)
        
        # Control buttons - compact
        self.display_button = QPushButton("📤")
        self.display_button.setToolTip("Hiển thị thông điệp")
        self.display_button.setStyleSheet("""
            QPushButton {
                background-color: #48BB78;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                min-width: 24px;
                max-width: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #38A169;
            }
            QPushButton:pressed {
                background-color: #2F855A;
            }
        """)
        self.display_button.setFixedSize(24, 24)
        frame_layout.addWidget(self.display_button)
        
        self.stop_button = QPushButton("⏹️")
        self.stop_button.setToolTip("Dừng và tắt LCD")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #F56565;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                min-width: 24px;
                max-width: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #E53E3E;
            }
            QPushButton:pressed {
                background-color: #C53030;
            }
            QPushButton:disabled {
                background-color: #CBD5E0;
                color: #A0AEC0;
            }
        """)
        self.stop_button.setFixedSize(24, 24)
        self.stop_button.setEnabled(False)
        frame_layout.addWidget(self.stop_button)
        
        # Add the frame to main layout
        main_layout.addWidget(main_frame)
        self.setLayout(main_layout)
        
        # Set overall widget styling - compact height
        self.setStyleSheet("""
            LCDMessageWidget {
                background-color: #F8F9FA;
                border-top: 1px solid #E9ECEF;
            }
        """)
        self.setFixedHeight(40)  # Reduced from 60 to 40
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Button connections
        self.display_button.clicked.connect(self._on_display_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.message_input.returnPressed.connect(self._on_display_clicked)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        
        # LCD service signal connections
        self.lcd_service.scrolling_started.connect(self._on_scrolling_started)
        self.lcd_service.scrolling_stopped.connect(self._on_scrolling_stopped)
        
    @pyqtSlot()
    def _on_display_clicked(self):
        """Handle display button click."""
        message = self.message_input.text().strip()
        if message:
            self.lcd_service.set_display_text(message)
            if len(message) > 16:  # Need scrolling for messages longer than LCD width
                self.lcd_service.start_scroll()
            self.message_input.clear()
    
    @pyqtSlot()
    def _on_stop_clicked(self):
        """Handle stop button click."""
        self.lcd_service.clear_and_reset()
        
    @pyqtSlot(int)
    def _on_speed_changed(self, value):
        """Handle speed slider change."""
        # Invert value: slider left (100) = slow (2000ms), slider right (2000) = fast (100ms)
        speed = 2100 - value
        self.lcd_service.set_scroll_speed(speed)
        
    @pyqtSlot()
    def _on_scrolling_started(self):
        """Handle scrolling started."""
        self.stop_button.setEnabled(True)
        self.display_button.setToolTip("Đang cuộn...")
        
    @pyqtSlot()
    def _on_scrolling_stopped(self):
        """Handle scrolling stopped."""
        self.stop_button.setEnabled(False)
        self.display_button.setToolTip("Hiển thị thông điệp")
    
    def set_hardware_interface(self, hardware_interface):
        """Set hardware interface for LCD service."""
        self.lcd_service.set_hardware_interface(hardware_interface)
        
    def get_lcd_service(self):
        """Get the LCD service instance."""
        return self.lcd_service
        
    def process_voice_command(self, command):
        """Process voice commands for LCD display."""
        return self.lcd_service.process_voice_command(command)
