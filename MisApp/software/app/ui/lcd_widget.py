from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QSlider, QFrame, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont, QPalette, QColor

from ..models.lcd_service import LCDService

class LCDWidget(QWidget):
    """Professional LCD display control widget with modern dark theme and premium styling"""
    
    def __init__(self, hardware_interface=None, parent=None):
        super().__init__(parent)
        self.lcd_service = LCDService(hardware_interface)
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize the premium user interface with modern dark theme"""
        
        # Set main widget background with sophisticated gradient
        self.setStyleSheet("""
            LCDWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0f1419, stop:0.3 #1a1f29, stop:0.7 #232937, stop:1 #2d3748);
                color: #f7fafc;
                border-radius: 16px;
            }
            QWidget {
                background: transparent;
                color: #f7fafc;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(32, 32, 32, 32)
        
        # Premium title with gradient text effect and glass morphism
        title_label = QLabel("🖥️ LCD Display Controller")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: 800;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
                -webkit-background-clip: text;
                color: transparent;
                background-clip: text;
                color: #667eea;
                margin-bottom: 20px;
                padding: 20px 24px;
                background: qradialgradient(cx:0.5, cy:0.5, radius:1, 
                    stop:0 rgba(102, 126, 234, 0.15), 
                    stop:0.5 rgba(118, 75, 162, 0.1), 
                    stop:1 rgba(240, 147, 251, 0.05));
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 16px;
                backdrop-filter: blur(10px);
                text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
            }
        """)
        main_layout.addWidget(title_label)
        
        # LCD Display simulation with ultra-modern design
        display_group = QGroupBox("💎 LCD Display")
        display_group.setStyleSheet("""
            QGroupBox {
                font-weight: 700;
                font-size: 18px;
                color: #667eea;
                border: 2px solid rgba(102, 126, 234, 0.4);
                border-radius: 20px;
                margin-top: 1ex;
                padding-top: 20px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(15, 20, 25, 0.9), 
                    stop:0.5 rgba(26, 31, 41, 0.8), 
                    stop:1 rgba(35, 41, 55, 0.7));
                backdrop-filter: blur(15px);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 8px 16px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(102, 126, 234, 0.2), stop:1 rgba(118, 75, 162, 0.2));
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 12px;
                backdrop-filter: blur(10px);
            }
        """)
        
        display_layout = QVBoxLayout()
        display_layout.setContentsMargins(20, 25, 20, 20)
        
        # Premium LCD display with holographic effect
        self.display_label = QLabel("🤖 MIS Assistant\n⚡ Ready for Action")
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #000000, 
                    stop:0.1 #0a0a0f, 
                    stop:0.5 #050510, 
                    stop:0.9 #0a0a0f, 
                    stop:1 #000000);
                color: #00f5ff;
                border: 3px solid #1e3a5f;
                border-radius: 18px;
                padding: 28px;
                font-family: 'Consolas', 'SF Mono', 'Monaco', 'Inconsolata', monospace;
                font-size: 18px;
                font-weight: 800;
                letter-spacing: 3px;
                text-shadow: 
                    0 0 5px rgba(0, 245, 255, 0.8),
                    0 0 10px rgba(0, 245, 255, 0.6),
                    0 0 15px rgba(0, 245, 255, 0.4),
                    0 0 20px rgba(0, 245, 255, 0.2);
                box-shadow: 
                    inset 0 0 30px rgba(0, 245, 255, 0.1),
                    0 0 20px rgba(0, 245, 255, 0.2),
                    0 8px 32px rgba(0, 0, 0, 0.5);
            }
        """)
        self.display_label.setMinimumHeight(120)
        self.display_label.setMaximumWidth(500)
        display_layout.addWidget(self.display_label)
        display_group.setLayout(display_layout)
        main_layout.addWidget(display_group)
        
        # Control panel with glass morphism and premium styling
        control_group = QGroupBox("🎛️ Advanced Controls")
        control_group.setStyleSheet("""
            QGroupBox {
                font-weight: 700;
                font-size: 18px;
                color: #f093fb;
                border: 2px solid rgba(240, 147, 251, 0.4);
                border-radius: 20px;
                margin-top: 1ex;
                padding-top: 20px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(15, 20, 25, 0.9), 
                    stop:0.5 rgba(26, 31, 41, 0.8), 
                    stop:1 rgba(35, 41, 55, 0.7));
                backdrop-filter: blur(15px);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 8px 16px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(240, 147, 251, 0.2), stop:1 rgba(118, 75, 162, 0.2));
                border: 1px solid rgba(240, 147, 251, 0.3);
                border-radius: 12px;
                backdrop-filter: blur(10px);
            }
        """)
        
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(20, 25, 20, 20)
        
        # Premium input controls with modern glass effect
        input_layout = QHBoxLayout()
        input_layout.setSpacing(16)
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("💬 Nhập thông tin muốn hiển thị lên LCD...")
        self.text_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 14px;
                padding: 16px 20px;
                font-size: 16px;
                font-weight: 500;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(45, 55, 72, 0.8), 
                    stop:1 rgba(26, 32, 44, 0.9));
                color: #f7fafc;
                selection-background-color: #667eea;
                selection-color: #ffffff;
                backdrop-filter: blur(10px);
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(45, 55, 72, 0.9), 
                    stop:1 rgba(26, 32, 44, 0.95));
                box-shadow: 
                    0 0 20px rgba(102, 126, 234, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            QLineEdit::placeholder {
                color: rgba(160, 174, 192, 0.7);
                font-style: italic;
            }
        """)
        input_layout.addWidget(self.text_input)
        
        # Premium gradient buttons with hover animations
        self.send_button = QPushButton("🚀 Display")
        self.send_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
                color: #ffffff;
                border: none;
                padding: 16px 28px;
                border-radius: 14px;
                font-weight: 700;
                font-size: 16px;
                min-width: 120px;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
                box-shadow: 
                    0 4px 15px rgba(102, 126, 234, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #7c88f0, stop:0.5 #8b5fb8, stop:1 #f5a9ff);
                transform: translateY(-2px);
                box-shadow: 
                    0 6px 20px rgba(102, 126, 234, 0.5),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                transform: translateY(-1px);
                box-shadow: 
                    0 2px 10px rgba(102, 126, 234, 0.6),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
        """)
        input_layout.addWidget(self.send_button)
        
        self.stop_button = QPushButton("⏹️ Stop")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #ff6b6b, stop:0.5 #ee5a52, stop:1 #ff8a80);
                color: #ffffff;
                border: none;
                padding: 16px 28px;
                border-radius: 14px;
                font-weight: 700;
                font-size: 16px;
                min-width: 120px;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
                box-shadow: 
                    0 4px 15px rgba(255, 107, 107, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #ff8a80, stop:0.5 #ff6b6b, stop:1 #ff9999);
                transform: translateY(-2px);
                box-shadow: 
                    0 6px 20px rgba(255, 107, 107, 0.5),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                transform: translateY(-1px);
                box-shadow: 
                    0 2px 10px rgba(255, 107, 107, 0.6),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(74, 85, 104, 0.6), stop:1 rgba(45, 55, 72, 0.6));
                color: rgba(160, 174, 192, 0.5);
                box-shadow: none;
            }
        """)
        self.stop_button.setEnabled(False)
        input_layout.addWidget(self.stop_button)
        
        control_layout.addLayout(input_layout)
        
        # Premium scroll speed control with modern design
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(16)
        
        speed_label = QLabel("⚡ Scroll Speed Control:")
        speed_label.setStyleSheet("""
            font-weight: 700; 
            color: #f7fafc; 
            margin-top: 20px;
            font-size: 17px;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        """)
        speed_layout.addWidget(speed_label)
        
        speed_control_layout = QHBoxLayout()
        speed_control_layout.setSpacing(20)
        
        slow_label = QLabel("🐌 Slow")
        slow_label.setStyleSheet("""
            color: #4ade80; 
            font-size: 14px; 
            font-weight: 600;
            padding: 8px 12px;
            background: rgba(74, 222, 128, 0.1);
            border-radius: 8px;
            border: 1px solid rgba(74, 222, 128, 0.3);
        """)
        speed_control_layout.addWidget(slow_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(100)
        self.speed_slider.setMaximum(2000)
        self.speed_slider.setValue(500)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(74, 85, 104, 0.8), 
                    stop:0.5 rgba(102, 126, 234, 0.3),
                    stop:1 rgba(240, 147, 251, 0.8));
                margin: 2px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border: 3px solid #ffffff;
                width: 24px;
                margin: -6px 0;
                border-radius: 12px;
                box-shadow: 
                    0 4px 12px rgba(102, 126, 234, 0.5),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #7c88f0, stop:1 #8b5fb8);
                box-shadow: 
                    0 6px 16px rgba(102, 126, 234, 0.6),
                    inset 0 1px 0 rgba(255, 255, 255, 0.4);
                transform: scale(1.1);
            }
            QSlider::handle:horizontal:pressed {
                box-shadow: 
                    0 2px 8px rgba(102, 126, 234, 0.8),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
            }
        """)
        speed_control_layout.addWidget(self.speed_slider)
        
        fast_label = QLabel("🚀 Fast")
        fast_label.setStyleSheet("""
            color: #f093fb; 
            font-size: 14px; 
            font-weight: 600;
            padding: 8px 12px;
            background: rgba(240, 147, 251, 0.1);
            border-radius: 8px;
            border: 1px solid rgba(240, 147, 251, 0.3);
        """)
        speed_control_layout.addWidget(fast_label)
        
        self.speed_value_label = QLabel("500ms")
        self.speed_value_label.setStyleSheet("""
            color: #667eea; 
            font-weight: 700; 
            font-size: 16px;
            margin-left: 20px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 rgba(102, 126, 234, 0.2), stop:1 rgba(118, 75, 162, 0.2));
            padding: 12px 20px;
            border-radius: 12px;
            border: 1px solid rgba(102, 126, 234, 0.3);
            min-width: 70px;
            text-align: center;
            backdrop-filter: blur(5px);
        """)
        speed_control_layout.addWidget(self.speed_value_label)
        
        speed_layout.addLayout(speed_control_layout)
        control_layout.addLayout(speed_layout)
        
        # Premium clear button with sophisticated styling
        clear_layout = QHBoxLayout()
        clear_layout.addStretch()
        
        self.clear_button = QPushButton("🗑️ Clear Display")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(107, 114, 128, 0.8), 
                    stop:0.5 rgba(75, 85, 99, 0.9), 
                    stop:1 rgba(55, 65, 81, 0.8));
                color: #f3f4f6;
                border: 1px solid rgba(156, 163, 175, 0.3);
                padding: 14px 24px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 15px;
                margin-top: 16px;
                backdrop-filter: blur(10px);
                box-shadow: 
                    0 2px 8px rgba(0, 0, 0, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(134, 142, 150, 0.9), 
                    stop:0.5 rgba(107, 114, 128, 0.95), 
                    stop:1 rgba(75, 85, 99, 0.9));
                transform: translateY(-1px);
                box-shadow: 
                    0 4px 12px rgba(0, 0, 0, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed {
                transform: translateY(0px);
                box-shadow: 
                    0 1px 4px rgba(0, 0, 0, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
        """)
        clear_layout.addWidget(self.clear_button)
        clear_layout.addStretch()
        
        control_layout.addLayout(clear_layout)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Premium status indicator with dynamic styling
        self.status_label = QLabel("✅ Hệ thống sẵn sàng")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #50f88d;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 22px;
                border-left: 4px solid #402658;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #5c476f, 
                    stop:0.5 #764983, 
                    stop:1 #ad6ebf);
                border-radius: 12px;
                border: 1px solid rgba(109, 76, 139, 0.3);
                margin-top: 18px;
                box-shadow: 
                    0 2px 8px rgba(109, 76, 139, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }
        """)
        main_layout.addWidget(self.status_label)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
        
    def _connect_signals(self):
        """Connect signals and slots"""
        self.send_button.clicked.connect(self._on_send_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.text_input.returnPressed.connect(self._on_send_clicked)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        
        # Connect LCD service signals
        self.lcd_service.display_updated.connect(self._on_display_updated)
        self.lcd_service.scroll_position_changed.connect(self._on_scroll_position_changed)
        self.lcd_service.scrolling_started.connect(self._on_scrolling_started)
        self.lcd_service.scrolling_stopped.connect(self._on_scrolling_stopped)
        
    @pyqtSlot(str)
    def _on_display_updated(self, text: str):
        """Handle display text updates with enhanced formatting"""
        if len(text) <= 16:
            display_text = text.center(16)
            if len(display_text) <= 16:
                self.display_label.setText(f"🤖 {display_text}\n⚡ Active Mode")
            else:
                self.display_label.setText(display_text[:16] + "\n" + display_text[16:32].ljust(16))
        else:
            # Show first 16 characters on first line, indicate scrolling
            self.display_label.setText(f"📱 {text[:14]}\n🔄 Scrolling...")
        
    @pyqtSlot(int)
    def _on_scroll_position_changed(self, position: int):
        """Handle scroll position changes"""
        self.stop_button.setEnabled(True)
        
    @pyqtSlot()
    def _on_scrolling_started(self):
        """Handle scrolling started with premium styling"""
        self.status_label.setText("🔄 Đang cuộn tin nhắn...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #667eea;
                font-weight: 700;
                font-size: 16px;
                padding: 16px 20px;
                border-left: 4px solid #4f46e5;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(102, 126, 234, 0.15), 
                    stop:0.5 rgba(79, 70, 229, 0.1), 
                    stop:1 rgba(99, 102, 241, 0.05));
                border-radius: 12px;
                border: 1px solid rgba(102, 126, 234, 0.3);
                margin-top: 16px;
                backdrop-filter: blur(10px);
                box-shadow: 
                    0 2px 8px rgba(102, 126, 234, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }
        """)
        self.stop_button.setEnabled(True)
        
    @pyqtSlot()
    def _on_scrolling_stopped(self):
        """Handle scrolling stopped with premium styling"""
        self.status_label.setText("⏸️ Scrolling Stopped")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #fbbf24;
                font-weight: 700;
                font-size: 16px;
                padding: 16px 20px;
                border-left: 4px solid #f59e0b;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(251, 191, 36, 0.15), 
                    stop:0.5 rgba(245, 158, 11, 0.1), 
                    stop:1 rgba(217, 119, 6, 0.05));
                border-radius: 12px;
                border: 1px solid rgba(251, 191, 36, 0.3);
                margin-top: 16px;
                backdrop-filter: blur(10px);
                box-shadow: 
                    0 2px 8px rgba(251, 191, 36, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }
        """)
        self.stop_button.setEnabled(False)
        
    def _on_send_clicked(self):
        """Handle send button click with enhanced feedback"""
        text = self.text_input.text().strip()
        if text:
            self.lcd_service.set_display_text(text)
            if len(text) > 16:  # Need scrolling for text longer than LCD width
                self.lcd_service.start_scroll()
            else:
                self.status_label.setText("✨ Hiển thị thông tin thành công")
                self.status_label.setStyleSheet("""
            QLabel {
                color: #50f88d;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 22px;
                border-left: 4px solid #402658;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #5c476f, 
                    stop:0.5 #764983, 
                    stop:1 #ad6ebf);
                border-radius: 12px;
                border: 1px solid rgba(109, 76, 139, 0.3);
                margin-top: 18px;
                box-shadow: 
                    0 2px 8px rgba(109, 76, 139, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }
        """)
            
            self.text_input.clear()
            
    def _on_stop_clicked(self):
        """Handle stop button click with premium feedback"""
        self.lcd_service.clear_and_reset()
        self.display_label.setText("🤖 MIS Assistant\n⚡ Ready for Action")
        self.status_label.setText("🛑 Hiển thị đã dừng & Xóa")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-weight: 700;
                font-size: 16px;
                padding: 16px 20px;
                border-left: 4px solid #ef4444;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(239, 68, 68, 0.15), 
                    stop:0.5 rgba(248, 113, 113, 0.1), 
                    stop:1 rgba(252, 165, 165, 0.05));
                border-radius: 12px;
                border: 1px solid rgba(239, 68, 68, 0.3);
                margin-top: 16px;
                backdrop-filter: blur(10px);
                box-shadow: 
                    0 2px 8px rgba(239, 68, 68, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }
        """)
        self.stop_button.setEnabled(False)
        
    def _on_clear_clicked(self):
        """Handle clear button click with elegant feedback"""
        self.lcd_service.clear_display()
        self.display_label.setText("🤖 MIS Assistant\n Ready for Action")
        self.status_label.setText("🧹 Hiển thị đã xóa thành công")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #50f88d;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 22px;
                border-left: 4px solid #402658;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #5c476f, 
                    stop:0.5 #764983, 
                    stop:1 #ad6ebf);
                border-radius: 12px;
                border: 1px solid rgba(109, 76, 139, 0.3);
                margin-top: 18px;
                box-shadow: 
                    0 2px 8px rgba(109, 76, 139, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }
        """)
        
    def _on_speed_changed(self, value):
        """Handle speed slider change with visual feedback"""
        # Invert the value so left (low values) = slow, right (high values) = fast
        speed = 2100 - value  # Convert to milliseconds (100ms = fast, 2000ms = slow)
        self.lcd_service.set_scroll_speed(speed)
        self.speed_value_label.setText(f"{speed}ms")
        
        # Dynamic color based on speed
        if speed < 500:
            color = "#f093fb"  # Fast - Pink
        elif speed < 1000:
            color = "#667eea"  # Medium - Blue
        else:
            color = "#4ade80"  # Slow - Green
            
        self.speed_value_label.setStyleSheet(f"""
            color: {color}; 
            font-weight: 700; 
            font-size: 16px;
            margin-left: 20px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2), 
                stop:1 rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1));
            padding: 12px 20px;
            border-radius: 12px;
            border: 1px solid rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3);
            min-width: 70px;
            text-align: center;
            backdrop-filter: blur(5px);
            box-shadow: 0 2px 8px rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2);
        """)
        
    def set_hardware_interface(self, hardware_interface):
        """Set hardware interface for LCD service"""
        self.lcd_service.set_hardware_interface(hardware_interface)        
    
    def process_voice_command(self, command: str) -> bool:
        """Process voice commands for LCD display with enhanced feedback
        
        Args:
            command: Voice command text
            
        Returns:
            bool: True if command was handled, False otherwise
        """
        result = self.lcd_service.process_voice_command(command)
        if result:
            self.status_label.setText("🎤 Voice Command Processed Successfully")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #06d6a0;
                    font-weight: 700;
                    font-size: 16px;
                    padding: 16px 20px;
                    border-left: 4px solid #059669;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 rgba(5, 150, 105, 0.15), 
                        stop:0.5 rgba(6, 214, 160, 0.1), 
                        stop:1 rgba(52, 211, 153, 0.05));
                    border-radius: 12px;
                    border: 1px solid rgba(5, 150, 105, 0.3);
                    margin-top: 16px;
                    backdrop-filter: blur(10px);
                    box-shadow: 
                        0 2px 8px rgba(5, 150, 105, 0.2),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
                }
            """)
        return result
    
    def get_lcd_service(self):
        """Get the LCD service instance"""
        return self.lcd_service