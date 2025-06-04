import sys
import time
import datetime
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QGridLayout, QApplication,
                            QSpinBox, QDateTimeEdit, QGroupBox, QGraphicsDropShadowEffect,
                            QSizePolicy, QSpacerItem, QScrollArea, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QTime, QDate, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QUrl
from PyQt5.QtGui import QFont, QColor, QLinearGradient, QPalette, QPainter, QBrush, QPen, QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from ..utils import logger, config

class CountdownTimer(QWidget):
    """Widget for displaying and managing a countdown timer."""
    timer_finished = pyqtSignal()  # Signal emitted when countdown reaches zero
    
    def __init__(self, hardware_interface=None, parent=None):
        super().__init__(parent)
        self.hardware_interface = hardware_interface
        
        # Countdown state
        self.target_datetime = None
        self.is_running = False
        
        # Sound notification setup
        self.sound_enabled = True
        self.media_player = QMediaPlayer()
        self.media_player.setVolume(80)
        self._setup_sound()
        
        # Setup UI
        self._setup_ui()
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_countdown)
        self.update_timer.start(1000)  # Update every second
          # Initial display update
        self._update_current_time()
        
    def _setup_ui(self):
        """Set up the UI components with modern, professional design."""
        # Main layout with margins and spacing
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
          # Set main widget background with purple gradient
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2d1b69, stop:0.5 #512da8, stop:1 #673ab7);
                border-radius: 20px;
            }
        """)
        
        # Create scroll area for better mobile compatibility
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(25)
        
        # === CURRENT TIME SECTION ===
        current_time_frame = self._create_modern_frame()
        current_time_layout = QVBoxLayout(current_time_frame)
        current_time_layout.setSpacing(15)
          # Title with icon
        time_title = QLabel("🕐 THỜI GIAN HIỆN TẠI")
        time_title.setAlignment(Qt.AlignCenter)
        time_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ce93d8;
                background: transparent;
                padding: 10px;
                border-bottom: 2px solid #ce93d8;
                margin-bottom: 10px;
            }
        """)
        
        self.current_time_label = QLabel()
        self.current_time_label.setAlignment(Qt.AlignCenter)
        self.current_time_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: #ffffff;
                background: transparent;
                padding: 20px;
                border-radius: 15px;                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(142, 36, 170, 0.3), stop:1 rgba(156, 39, 176, 0.3));
            }
        """)
        
        self.current_date_label = QLabel()
        self.current_date_label.setAlignment(Qt.AlignCenter)
        self.current_date_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 500;
                color: #b0bec5;
                background: transparent;
                padding: 8px;
            }
        """)
        
        current_time_layout.addWidget(time_title)
        current_time_layout.addWidget(self.current_time_label)
        current_time_layout.addWidget(self.current_date_label)
        
        # Add shadow effect
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(25)
        shadow_effect.setXOffset(0)
        shadow_effect.setYOffset(5)
        shadow_effect.setColor(QColor(0, 0, 0, 100))
        current_time_frame.setGraphicsEffect(shadow_effect)
        
        scroll_layout.addWidget(current_time_frame)
        
        # === TARGET TIME SETTING SECTION ===
        target_frame = self._create_modern_frame()
        target_layout = QVBoxLayout(target_frame)
        target_layout.setSpacing(20)
          # Title
        target_title = QLabel("⏰ ĐẶT THỜI GIAN ĐẾM NGƯỢC")
        target_title.setAlignment(Qt.AlignCenter)
        target_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ab47bc;
                background: transparent;
                padding: 10px;
                border-bottom: 2px solid #ab47bc;
                margin-bottom: 10px;
            }
        """)
        
        # DateTime picker with modern style
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDisplayFormat("dd/MM/yyyy HH:mm:ss")
        self.datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setStyleSheet("""            QDateTimeEdit {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid #9c27b0;
                border-radius: 12px;
                padding: 15px;
                font-size: 16px;
                font-weight: 500;
                color: #ffffff;
            }
            QDateTimeEdit:focus {
                border: 2px solid #ab47bc;
                background: rgba(255, 255, 255, 0.15);
            }
            QDateTimeEdit::drop-down {
                border: none;
                background: #9c27b0;
                border-radius: 8px;
                width: 30px;
            }
            QDateTimeEdit::down-arrow {
                image: none;
                border: none;
                width: 12px;
                height: 12px;
                background: white;
                border-radius: 6px;
            }
        """)
        
        # Quick time presets
        preset_layout = QHBoxLayout()
        preset_buttons = [
            ("5 phút", 300),
            ("15 phút", 900),
            ("30 phút", 1800),
            ("1 giờ", 3600),
            ("2 giờ", 7200)
        ]
        
        for text, seconds in preset_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4fc3f7, stop:1 #29b6f6);
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 12px;
                    font-weight: 500;
                    color: white;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #29b6f6, stop:1 #1e88e5);
                    transform: translateY(-2px);
                }
                QPushButton:pressed {
                    background: #1565c0;
                }
            """)
            btn.clicked.connect(lambda checked, s=seconds: self._set_preset_time(s))
            preset_layout.addWidget(btn)
        
        # Control buttons with modern design
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.start_button = QPushButton("🚀 BẮT ĐẦU")
        self.start_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4caf50, stop:1 #43a047);
                border: none;
                border-radius: 15px;
                padding: 15px 25px;
                font-size: 16px;
                font-weight: bold;
                color: white;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #66bb6a, stop:1 #4caf50);
                transform: translateY(-3px);
            }
            QPushButton:pressed {
                background: #388e3c;
            }
            QPushButton:disabled {
                background: #424242;
                color: #757575;
            }
        """)
        self.start_button.clicked.connect(self._start_countdown)
        
        self.stop_button = QPushButton("⏹️ DỪNG")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f44336, stop:1 #d32f2f);
                border: none;
                border-radius: 15px;
                padding: 15px 25px;
                font-size: 16px;
                font-weight: bold;
                color: white;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef5350, stop:1 #f44336);
                transform: translateY(-3px);
            }
            QPushButton:pressed {
                background: #c62828;
            }
            QPushButton:disabled {
                background: #424242;
                color: #757575;
            }        """)
        self.stop_button.clicked.connect(self._reset_countdown)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        
        target_layout.addWidget(target_title)
        target_layout.addWidget(self.datetime_edit)
        target_layout.addLayout(preset_layout)
        
        # === SOUND NOTIFICATION SECTION ===
        sound_frame = QFrame()
        sound_frame.setStyleSheet("""
            QFrame {
                background: rgba(156, 39, 176, 0.1);
                border: 1px solid rgba(156, 39, 176, 0.3);
                border-radius: 12px;
                padding: 15px;
            }
        """)
        sound_layout = QHBoxLayout(sound_frame)
        sound_layout.setSpacing(15)
        
        # Sound icon and title
        sound_icon = QLabel("🔊")
        sound_icon.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #ce93d8;
                background: transparent;
            }
        """)
        
        sound_title = QLabel("Âm thanh thông báo:")
        sound_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 500;
                color: #ce93d8;
                background: transparent;
            }
        """)
        
        # Sound checkbox
        self.sound_checkbox = QCheckBox("Bật âm thanh")
        self.sound_checkbox.setChecked(True)
        self.sound_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #9c27b0;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator:checked {
                background: #9c27b0;
                border: 2px solid #ab47bc;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
                font-weight: bold;
            }
        """)
        self.sound_checkbox.toggled.connect(self._toggle_sound)
        
        # Stop sound button (initially hidden)
        self.stop_sound_button = QPushButton("🔇 Dừng âm thanh")
        self.stop_sound_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff5722, stop:1 #d84315);
                border: none;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: 500;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff7043, stop:1 #ff5722);
            }
            QPushButton:pressed {
                background: #bf360c;
            }
        """)
        self.stop_sound_button.clicked.connect(self._stop_sound)
        self.stop_sound_button.hide()
        
        sound_layout.addWidget(sound_icon)
        sound_layout.addWidget(sound_title)
        sound_layout.addWidget(self.sound_checkbox)
        sound_layout.addStretch()
        sound_layout.addWidget(self.stop_sound_button)
        
        target_layout.addWidget(sound_frame)
        target_layout.addLayout(button_layout)
        
        scroll_layout.addWidget(target_frame)
        
        # === COUNTDOWN DISPLAY SECTION ===
        countdown_frame = self._create_modern_frame()
        countdown_layout = QVBoxLayout(countdown_frame)
        countdown_layout.setSpacing(20)
        
        # Title
        countdown_title = QLabel("⏱️ THỜI GIAN CÒN LẠI")
        countdown_title.setAlignment(Qt.AlignCenter)
        countdown_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffa726;
                background: transparent;
                padding: 10px;
                border-bottom: 2px solid #ffa726;
                margin-bottom: 10px;
            }
        """)
        
        # Main countdown display
        self.countdown_display = QLabel("--:--:--")
        self.countdown_display.setAlignment(Qt.AlignCenter)
        self.countdown_display.setStyleSheet("""
            QLabel {
                font-size: 72px;
                font-weight: bold;
                color: #ffffff;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 167, 38, 0.3), stop:1 rgba(255, 193, 7, 0.3));
                padding: 30px;
                border-radius: 20px;
                border: 3px solid #ffa726;
            }
        """)
        
        # Days display
        self.days_display = QLabel()
        self.days_display.setAlignment(Qt.AlignCenter)
        self.days_display.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: #81c784;
                background: transparent;
                padding: 10px;
            }
        """)
        self.days_display.hide()
        
        # Progress indicator for visual feedback
        self.progress_frame = QFrame()
        self.progress_frame.setFixedHeight(8)
        self.progress_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        self.progress_frame.hide()
        
        countdown_layout.addWidget(countdown_title)
        countdown_layout.addWidget(self.days_display)
        countdown_layout.addWidget(self.countdown_display)
        countdown_layout.addWidget(self.progress_frame)
        
        scroll_layout.addWidget(countdown_frame)
        
        # Add shadow effects to all frames
        for frame in [target_frame, countdown_frame]:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(25)
            shadow.setXOffset(0)
            shadow.setYOffset(5)
            shadow.setColor(QColor(0, 0, 0, 100))
            frame.setGraphicsEffect(shadow)
        
        # Setup scroll area
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #4fc3f7;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #29b6f6;
            }
        """)
        
        main_layout.addWidget(scroll_area)
        
        # Setup timers
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self._update_current_time)
        self.time_timer.start(1000)
        
    def _create_modern_frame(self):
        """Create a modern styled frame."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 20px;
            }
        """)
        return frame
    def _set_preset_time(self, seconds):
        """Set a preset countdown time."""
        target_time = QDateTime.currentDateTime().addSecs(seconds)
        self.datetime_edit.setDateTime(target_time)
        
        
    def _update_current_time(self):
        """Update the current time display."""
        now = QDateTime.currentDateTime()
        
        # Format time
        self.current_time_label.setText(now.toString("HH:mm:ss"))
        
        # Format date with Vietnamese day name
        day_names = {
            1: "⚡Thứ Hai",
            2: "✨Thứ Ba",
            3: "🌟Thứ Tư",
            4: "💫Thứ Năm",
            5: "💥Thứ Sáu", 
            6: "☀️Thứ Bảy",
            7: "💫Chủ Nhật"
        }
        day_name = day_names.get(now.date().dayOfWeek(), "")
        formatted_date = f"{day_name}, {now.toString('dd/MM/yyyy')}"
        self.current_date_label.setText(formatted_date)
        
        # Update minimum datetime to ensure future dates
        self.datetime_edit.setMinimumDateTime(now)
        
    def _start_countdown(self):
        """Start the countdown timer."""
        # Get the target datetime
        self.target_datetime = self.datetime_edit.dateTime()
        
        # Ensure target time is in the future
        now = QDateTime.currentDateTime()
        if self.target_datetime <= now:
            self.target_datetime = now.addSecs(10)  # Default to 10 seconds if not in future
            self.datetime_edit.setDateTime(self.target_datetime)
        
        # Update display immediately
        self._update_countdown()
        
        # Update UI state
        self.is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.datetime_edit.setEnabled(False)
        
        logger.info(f"Countdown started to {self.target_datetime.toString()}")
        
    def _reset_countdown(self):
        """Reset the countdown timer."""
        # Stop the countdown
        self.is_running = False
        
        # Reset UI state
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.datetime_edit.setEnabled(True)
        
        # Reset displays
        self.countdown_display.setText("--:--:--")
        self.days_display.hide()
        
        # Reset target datetime
        self.target_datetime = None
        
        # Set datetime edit to 1 hour from now
        self.datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        logger.info("Countdown reset")
        
    def _update_countdown(self):
        """Update the countdown display with visual effects."""
        if not self.is_running or not self.target_datetime:
            return
            
        # Get current time
        now = QDateTime.currentDateTime()
        
        # Calculate time difference
        seconds_to_target = now.secsTo(self.target_datetime)
        
        # Check if countdown has finished
        if seconds_to_target <= 0:
            self._finish_countdown()
            return
            
        # Calculate days, hours, minutes, seconds
        days = seconds_to_target // (24 * 3600)
        seconds_to_target %= (24 * 3600)
        hours = seconds_to_target // 3600
        seconds_to_target %= 3600
        minutes = seconds_to_target // 60
        seconds = seconds_to_target % 60
        
        # Update days display if needed
        if days > 0:
            self.days_display.setText(f"📅 {days} ngày")
            self.days_display.show()
        else:
            self.days_display.hide()
            
        # Format time as HH:MM:SS
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.countdown_display.setText(time_str)
        
        # Change color based on remaining time
        total_seconds = now.secsTo(self.target_datetime)
        if total_seconds <= 60:  # Last minute - red
            self.countdown_display.setStyleSheet("""
                QLabel {
                    font-size: 72px;
                    font-weight: bold;
                    color: #ffffff;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(244, 67, 54, 0.4), stop:1 rgba(229, 57, 53, 0.4));
                    padding: 30px;
                    border-radius: 20px;
                    border: 3px solid #f44336;
                }
            """)
        elif total_seconds <= 300:  # Last 5 minutes - orange
            self.countdown_display.setStyleSheet("""
                QLabel {
                    font-size: 72px;
                    font-weight: bold;
                    color: #ffffff;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(255, 152, 0, 0.4), stop:1 rgba(251, 140, 0, 0.4));
                    padding: 30px;
                    border-radius: 20px;
                    border: 3px solid #ff9800;
                }
            """)
        else:  # Normal - green/blue
            self.countdown_display.setStyleSheet("""
                QLabel {
                    font-size: 72px;
                    font-weight: bold;
                    color: #ffffff;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(76, 175, 80, 0.4), stop:1 rgba(67, 160, 71, 0.4));
                    padding: 30px;
                    border-radius: 20px;
                    border: 3px solid #4caf50;                }
            """)
            
    def _finish_countdown(self):
        """Handle countdown completion with celebration effect."""
        self.countdown_display.setText("🎉 00:00:00")
        self.countdown_display.setStyleSheet("""
            QLabel {
                font-size: 72px;
                font-weight: bold;
                color: #ffffff;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(156, 39, 176, 0.6), stop:1 rgba(233, 30, 99, 0.6));
                padding: 30px;
                border-radius: 20px;
                border: 3px solid #e91e63;
                animation: pulse 1s infinite;
            }
        """)
        
        self.days_display.setText("🎊 ĐẾM NGƯỢC ĐÃ KẾT THÚC! 🎊")
        self.days_display.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #e91e63;
                background: rgba(233, 30, 99, 0.1);
                padding: 15px;
                border-radius: 15px;
                border: 2px solid #e91e63;
            }
        """)
        self.days_display.show()
        
        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.datetime_edit.setEnabled(True)
        
        # Play notification sound
        self._play_notification_sound()
          # Emit signal for countdown finished
        self.timer_finished.emit()
        
        logger.info("Countdown finished!")
        
    def set_hardware_interface(self, hardware_interface):
        """Set the hardware interface reference."""
        self.hardware_interface = hardware_interface
        
    def closeEvent(self, event):
        """Handle widget close event."""
        # Call parent class closeEvent
        super().closeEvent(event)
        
    def _setup_sound(self):
        """Setup sound notification system."""
        # Try to load notification sound
        sound_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'sounds', 'thong_bao.mp3')
        if os.path.exists(sound_path):
            sound_url = QUrl.fromLocalFile(os.path.abspath(sound_path))
            self.media_player.setMedia(QMediaContent(sound_url))
            logger.info(f"Sound file loaded: {sound_path}")
        else:
            logger.warning(f"Sound file not found: {sound_path}")
            # Fallback to wav file if mp3 doesn't exist
            fallback_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'resources', 'sounds', 'notification.wav')
            if os.path.exists(fallback_path):
                sound_url = QUrl.fromLocalFile(os.path.abspath(fallback_path))
                self.media_player.setMedia(QMediaContent(sound_url))
                logger.info(f"Fallback sound file loaded: {fallback_path}")
    
    def _toggle_sound(self, enabled):
        """Toggle sound notification on/off."""
        self.sound_enabled = enabled
        if not enabled and self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.stop()
            self.stop_sound_button.hide()
        logger.info(f"Sound notification {'enabled' if enabled else 'disabled'}")
    
    def _play_notification_sound(self):
        """Play notification sound continuously."""
        if self.sound_enabled and self.sound_checkbox.isChecked():
            self.media_player.setPosition(0)
            # Set to loop the sound
            self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
            self.media_player.play()
            self.stop_sound_button.show()
            logger.info("Playing notification sound")
    
    def _on_media_status_changed(self, status):
        """Handle media status changes to loop the sound."""
        if status == QMediaPlayer.EndOfMedia and self.sound_enabled:
            self.media_player.setPosition(0)
            self.media_player.play()
    
    def _stop_sound(self):
        """Stop the notification sound."""
        self.media_player.stop()
        self.stop_sound_button.hide()
        logger.info("Notification sound stopped")