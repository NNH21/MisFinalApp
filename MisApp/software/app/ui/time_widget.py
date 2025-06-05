import sys
import time
import datetime
import pytz
import os
import math
import random
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QFrame, QGridLayout, QPushButton,
                            QTabWidget, QTimeEdit, QCalendarWidget, QCheckBox,
                            QListWidget, QListWidgetItem, QMessageBox, 
                            QScrollArea, QGroupBox, QDialog, QSlider, QLineEdit,
                            QGraphicsDropShadowEffect, QApplication, QSizePolicy,
                            QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
                            QGraphicsLineItem, QStyleFactory, QToolButton,
                            QCompleter, QSpacerItem, QSpinBox)
from PyQt5.QtCore import (Qt, QTimer, QDateTime, QTime, QDate, QLocale, 
                          pyqtSignal, QRect, QPoint, QPointF, QPropertyAnimation, 
                          QEasingCurve, QSize, QRectF, QObject, QParallelAnimationGroup, 
                          QSequentialAnimationGroup, QThread)
from PyQt5.QtGui import (QFont, QIcon, QColor, QPainter, QPen, QBrush, QLinearGradient,
                         QRadialGradient, QPainterPath, QTransform, QPixmap, QImage,
                         QFontMetrics, QPolygon, QConicalGradient, QPalette)

from ..utils import logger, config
from ..models.time_service import TimeService
from .countdown_timer import CountdownTimer
from .countdown_timer import CountdownTimer

class ToggleSwitch(QSlider):
    """Custom toggle switch widget (On/Off slider)."""
    
    stateChanged = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setMinimum(0)
        self.setMaximum(1)
        self.setValue(1) 
        self.setFixedWidth(60) 
        self.setFixedHeight(30)  
        
        # Remove ticks
        self.setTickPosition(QSlider.NoTicks)
        
        # Set custom stylesheet
        self.setStyleSheet("""
            QSlider {
                background: transparent;
            }
            QSlider::groove:horizontal {
                height: 26px;
                background: #e0e0e0;
                border-radius: 13px;
            }
            QSlider::handle:horizontal {
                width: 26px;
                margin: 0px;
                border-radius: 13px;
                background: white;
                border: 1px solid #ccc;
            }
            QSlider::groove:horizontal:checked {
                background: #192239;
            }
        """)
        
        # Connect value changed signal
        self.valueChanged.connect(self._emit_state_changed)
    
    def _emit_state_changed(self, value):
        self.stateChanged.emit(bool(value))
    
    def isChecked(self):
        return bool(self.value())
    
    def setChecked(self, checked):
        self.setValue(1 if checked else 0)
    
    def paintEvent(self, event):
        # Custom painting for the toggle switch
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw groove
        groove_rect = self.rect().adjusted(2, 2, -2, -2)
        
        # Get colors based on state
        if self.value() == 1:
            groove_color = QColor("#192239")  # Dark blue for ON
        else:
            groove_color = QColor("#e5e7eb")  # Light grey for OFF
            
        # Draw groove with gradient
        gradient = QLinearGradient(groove_rect.topLeft(), groove_rect.bottomRight())
        if self.value() == 1:
            gradient.setColorAt(0, QColor("#192239"))
            gradient.setColorAt(1, QColor("#65356e"))
        else:
            gradient.setColorAt(0, QColor("#e5e7eb"))
            gradient.setColorAt(1, QColor("#d1d5db"))
            
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(groove_rect, 13, 13)
        
        # Calculate handle position with smooth transition
        handle_pos = 4 if self.value() == 0 else self.width() - 32
        
        # Draw handle with shadow
        handle_rect = QRect(handle_pos, 2, 26, 26)
        
        # Draw handle shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Draw handle
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(QColor("#d1d5db"), 1))
        painter.drawEllipse(handle_rect)
        
        # Skip default painting
        event.accept()


class AlarmListItem(QWidget):
    """Custom widget for displaying an alarm in the list with a professional purple design."""
    
    toggled = pyqtSignal(str, bool)  # Alarm ID, new state
    clicked = pyqtSignal(str)  # Emit alarm ID when clicked for selection
    snooze = pyqtSignal(str)  # Emit alarm ID when snooze is requested
    stop_sound = pyqtSignal(str)  # Emit alarm ID when stop sound is requested
    
    def __init__(self, alarm_id, alarm_data, parent=None):
        super().__init__(parent)
        self.alarm_id = alarm_id
        self.alarm_data = alarm_data
        self.selected = False
        self.is_ringing = False
        
        self._setup_ui()
    
    def setSelected(self, selected):
        """Set the selected state of the alarm item."""
        self.selected = selected
        if selected:
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #e8dcff, stop:1 #f3eeff);
                    border-radius: 15px;
                    border: 2px solid #8b5cf6;
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
                }
            """)
        else:
            self._update_visual_state(self.alarm_data["active"])    
    def _setup_ui(self):
        # Main layout with enhanced spacing and padding for better visibility
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 22, 25, 22)
        layout.setSpacing(20)
        
        # Left side: Time display with improved sizing
        time_container = QFrame()
        time_container.setFixedWidth(200)  # Fixed width for consistent time display
        time_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(139, 92, 246, 0.08), stop:1 rgba(139, 92, 246, 0.12));
                border-radius: 12px;
                border: 2px solid rgba(139, 92, 246, 0.2);
            }
        """)
        time_layout = QVBoxLayout(time_container)
        time_layout.setAlignment(Qt.AlignCenter)
        time_layout.setContentsMargins(10, 15, 10, 15)
        
        # Time display with larger, clearer font
        self.time_label = QLabel(self.alarm_data["time"].toString("HH:mm"))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            font-size: 48px;
            font-weight: 800;
            color: #6b46c1;
            font-family: 'Segoe UI', 'Consolas', 'Arial';
            padding: 5px;
            margin: 0;
            letter-spacing: 2px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 8px;
        """)
        
        time_layout.addWidget(self.time_label)
        
        # Right side: Details container (name and date info)
        details_container = QFrame()
        details_container.setStyleSheet("""
            QFrame {
                background: rgba(139, 92, 246, 0.03);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        details_layout = QVBoxLayout(details_container)
        details_layout.setSpacing(8)
        details_layout.setContentsMargins(15, 12, 15, 12)
        
        # Name with refined styling
        self.name_label = QLabel(self.alarm_data["name"])
        self.name_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #4c1d95;
            padding: 4px 8px;
            margin: 0;
            background: rgba(139, 92, 246, 0.1);
            border-radius: 8px;
        """)
        self.name_label.setWordWrap(True)
        
        # Date info with professional styling
        self.date_label = QLabel()
        self.date_label.setStyleSheet("""
            font-size: 14px;
            color: #6b7280;
            font-weight: 500;
            background: rgba(139, 92, 246, 0.08);
            padding: 6px 10px;
            border-radius: 8px;
            margin-top: 4px;
        """)
        
        details_layout.addWidget(self.name_label)
        details_layout.addWidget(self.date_label)
        details_layout.addStretch()        
        # Middle section: Status indicator only
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(8)
        middle_layout.setAlignment(Qt.AlignCenter)
        
        # Status indicator with elegant design
        self.status_indicator = QLabel("●")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet("""
            font-size: 24px;
            color: #10b981;
            padding: 0;
            margin: 0;
        """)
        
        middle_layout.addWidget(self.status_indicator)
        
        # Right side: Enhanced control panel
        controls_container = QFrame()
        controls_container.setStyleSheet("""
            QFrame {
                background: rgba(139, 92, 246, 0.08);
                border-radius: 12px;
                padding: 8px;
            }
        """)
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setAlignment(Qt.AlignCenter)
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(12, 8, 12, 8)
          # Enhanced toggle switch with purple theme
        self.toggle_switch = ToggleSwitch()
        self.toggle_switch.setChecked(self.alarm_data["active"])
        self.toggle_switch.stateChanged.connect(lambda checked: self.toggled.emit(self.alarm_id, checked))
        
        # Update the toggle switch paintEvent to use purple theme
        original_paint = self.toggle_switch.paintEvent
        def purple_paint_event(event):
            painter = QPainter(self.toggle_switch)
            painter.setRenderHint(QPainter.Antialiasing)
            
            groove_rect = self.toggle_switch.rect().adjusted(2, 4, -2, -4)
            
            if self.toggle_switch.value() == 1:
                groove_color = QColor("#8b5cf6")  # Purple for ON
            else:
                groove_color = QColor("#e5e7eb")  # Grey for OFF
                
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(groove_color))
            painter.drawRoundedRect(groove_rect, 11, 11)
            
            handle_pos = 4 if self.toggle_switch.value() == 0 else self.toggle_switch.width() - 28
            handle_rect = QRect(handle_pos, 4, 22, 22)
            painter.setBrush(QBrush(QColor("white")))
            painter.setPen(QPen(QColor("#d1d5db"), 1))
            painter.drawEllipse(handle_rect)
            
            event.accept()
        
        self.toggle_switch.paintEvent = purple_paint_event
        
        # Button container for better organization
        button_container = QVBoxLayout()
        button_container.setSpacing(6)
        
        # Snooze button with purple gradient
        self.snooze_button = QPushButton("⏰ Báo lại")
        self.snooze_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8b5cf6, stop:1 #a78bfa);
                color: white;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                border: none;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c3aed, stop:1 #9333ea);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6d28d9, stop:1 #7e22ce);
            }
        """)
        self.snooze_button.clicked.connect(lambda: self.snooze.emit(self.alarm_id))
        self.snooze_button.hide()  # Hidden by default
        
        # Stop sound button with distinctive red-purple gradient
        self.stop_sound_button = QPushButton("🔇 Dừng âm thanh")
        self.stop_sound_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
                color: white;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                border: none;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #b91c1c, stop:1 #991b1b);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #991b1b, stop:1 #7f1d1d);
            }
        """)
        self.stop_sound_button.clicked.connect(lambda: self.stop_sound.emit(self.alarm_id))
        self.stop_sound_button.hide()  # Hidden by default
        
        button_container.addWidget(self.snooze_button)
        button_container.addWidget(self.stop_sound_button)
        
        controls_layout.addWidget(self.toggle_switch)
        controls_layout.addLayout(button_container)
          # Add all sections to main layout
        layout.addWidget(time_container, stretch=1)
        layout.addWidget(details_container, stretch=2)
        layout.addLayout(middle_layout, stretch=0)
        layout.addWidget(controls_container, stretch=1)
        
        # Set main widget style with premium purple theme
        self.setFixedHeight(160) # Increased height from 120 to 160
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #faf5ff, stop:1 #f3e8ff);
                border-radius: 15px;
                border: 1px solid #d8b4fe;
            }
            QWidget:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f3e8ff, stop:1 #e9d5ff);
                border: 2px solid #c084fc;
                box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
            }
        """)
        
        # Add subtle drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(139, 92, 246, 50))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Update visual state and date info
        self._update_visual_state(self.alarm_data["active"])
        self._update_date_info()
        
    def _update_visual_state(self, is_active):
        """Update the visual state of the alarm item with enhanced purple styling."""
        if is_active:
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #faf5ff, stop:1 #f3e8ff);
                    border-radius: 15px;
                    border: 1px solid #d8b4fe;
                }
                QWidget:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #f3e8ff, stop:1 #e9d5ff);
                    border: 2px solid #c084fc;
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);                }
            """)
            self.time_label.setStyleSheet("""                font-size: 52px;
                font-weight: 700;
                color: #6b46c1;
                font-family: 'Segoe UI', 'Arial';
                padding: 8px;
                margin: 0;
                letter-spacing: 3px;
                min-width: 180px;
            """)
            self.name_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #4c1d95;
                padding: 4px 8px;
                margin: 0;
                background: rgba(139, 92, 246, 0.1);
                border-radius: 8px;
            """)
            self.status_indicator.setStyleSheet("""
                font-size: 20px;
                color: #10b981;
                padding: 0;
                margin: 0;
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #f9fafb, stop:1 #f3f4f6);
                    border-radius: 15px;
                    border: 1px solid #e5e7eb;
                }
                QWidget:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #f3f4f6, stop:1 #e5e7eb);
                    border: 2px solid #d1d5db;                }
            """)
            self.time_label.setStyleSheet("""
                font-size: 52px;
                font-weight: 700;
                color: #9ca3af;
                font-family: 'Segoe UI', 'Arial';
                padding: 8px;
                margin: 0;
                letter-spacing: 3px;
                min-width: 180px;
            """)
            self.name_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 500;
                color: #6b7280;
                padding: 4px 8px;
                margin: 0;
                background: rgba(139, 92, 246, 0.05);
                border-radius: 8px;
            """)
            self.status_indicator.setStyleSheet("""
                font-size: 20px;
                color: #ef4444;
                padding: 0;
                margin: 0;
            """)
            
    def _update_date_info(self):
        """Update the date/repeat information display with enhanced styling."""
        if self.alarm_data["repeat_days"]:
            day_names = {
                1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"
            }
            
            days_str = ", ".join([day_names[day] for day in self.alarm_data["repeat_days"] if day in day_names])
            date_text = f"Lặp: {days_str}"
        elif self.alarm_data["date"]:
            date_text = f"Ngày: {self.alarm_data['date'].toString('dd/MM/yyyy')}"
        else:
            date_text = "Hôm nay"
            
        self.date_label.setText(date_text)
        
    def set_ringing(self, is_ringing):
        """Set the alarm item to ringing state with animated purple highlights."""
        self.is_ringing = is_ringing
        if is_ringing:
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #fef3c7, stop:1 #fed7aa);
                    border-radius: 15px;
                    border: 2px solid #f59e0b;
                    box-shadow: 0 0 20px rgba(245, 158, 11, 0.5);
                }            """)
            self.status_indicator.setStyleSheet("""
                font-size: 20px;
                color: #f59e0b;
                padding: 0;
                margin: 0;            """)
            self.time_label.setStyleSheet("""
                font-size: 52px;
                font-weight: 700;
                color: #92400e;
                font-family: 'Segoe UI', 'Arial';
                padding: 8px;
                margin: 0;
                letter-spacing: 3px;
                min-width: 180px;
            """)
            self.snooze_button.show()
            self.stop_sound_button.show()
        else:
            self._update_visual_state(self.alarm_data["active"])
            self.snooze_button.hide()
            self.stop_sound_button.hide()
            
    def update_alarm_data(self, alarm_data):
        """Update the displayed alarm data with enhanced visual feedback."""
        self.alarm_data = alarm_data
        
        # Update UI elements
        self.time_label.setText(alarm_data["time"].toString("HH:mm"))
        self.name_label.setText(alarm_data["name"])
        
        # Update active state
        self.toggle_switch.setChecked(alarm_data["active"])
        self._update_visual_state(alarm_data["active"])
        
        # Update date/repeat info
        self._update_date_info()
        
        # Update snooze info if needed
        if hasattr(self, 'snooze_label'):
            if alarm_data.get("snooze_enabled", False):
                snooze_text = f"Báo lại: {alarm_data.get('snooze_time', 5)} phút"
                self.snooze_label.setText(snooze_text)
                self.snooze_label.show()
            else:
                self.snooze_label.hide()
    
    def mousePressEvent(self, event):
        """Handle mouse click on the alarm item."""
        super().mousePressEvent(event)
        self.clicked.emit(self.alarm_id)  # Emit signal with alarm ID


class AlarmSettingDialog(QDialog):
    """Dialog for setting a new alarm."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đặt báo thức mới")
        self.setMinimumWidth(500)
        self.setMinimumHeight(900)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #faf5ff, stop:1 #f8fafc);
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #c084fc;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: rgba(139, 92, 246, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #6b46c1;
                font-size: 14px;
            }
            QTimeEdit, QLineEdit, QComboBox {
                padding: 12px;
                border: 2px solid #e9d5ff;
                border-radius: 8px;
                background-color: white;
                font-size: 16px;
            }
            QTimeEdit:focus, QLineEdit:focus, QComboBox:focus {
                border-color: #8b5cf6;
                background-color: #faf5ff;
            }
            QPushButton {
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton#saveButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8b5cf6, stop:1 #a78bfa);
                color: white;
                border: none;
            }
            QPushButton#saveButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c3aed, stop:1 #9333ea);
            }
            QPushButton#cancelButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white;
                border: none;
            }
            QPushButton#cancelButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
            }
            QCheckBox {
                color: #4c1d95;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #c084fc;
            }
            QCheckBox::indicator:checked {
                background-color: #8b5cf6;
                border-color: #8b5cf6;
            }
            QSpinBox {
                padding: 8px;
                border: 2px solid #e9d5ff;
                border-radius: 6px;
                background-color: white;
            }
            QSpinBox:focus {
                border-color: #8b5cf6;
                background-color: #faf5ff;
            }
        """)
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Time selection
        time_group = QGroupBox("Thời gian báo thức")
        time_layout = QVBoxLayout(time_group)
        
        time_input_layout = QHBoxLayout()
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.currentTime().addSecs(60*60))  # Default to 1 hour from now
        self.time_edit.setStyleSheet("font-size: 24px;")
        
        time_input_layout.addWidget(self.time_edit)
        time_input_layout.addStretch()
        
        time_layout.addLayout(time_input_layout)
        layout.addWidget(time_group)
        
        # Alarm name and type
        name_group = QGroupBox("Tên và loại báo thức")
        name_layout = QVBoxLayout(name_group)
        
        # Alarm name
        name_label = QLabel("Tên báo thức:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nhập tên báo thức...")
        
        # Alarm type
        type_label = QLabel("Loại báo thức:")
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Báo thức thông thường",
            "Báo thức dần dần",
            "Báo thức rung",
            "Báo thức nhạc"
        ])
        
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        name_layout.addWidget(type_label)
        name_layout.addWidget(self.type_combo)
        
        layout.addWidget(name_group)
        
        # Calendar for date selection
        date_group = QGroupBox("Ngày báo thức")
        date_layout = QVBoxLayout(date_group)
        
        self.calendar = QCalendarWidget()
        self.calendar.setMinimumDate(QDate.currentDate())
        
        # Set Vietnamese locale for the calendar
        locale = QLocale(QLocale.Vietnamese, QLocale.Vietnam)
        self.calendar.setLocale(locale)
        
        # Set the first day of week to Monday
        self.calendar.setFirstDayOfWeek(Qt.Monday)
        
        date_layout.addWidget(self.calendar)
        
        layout.addWidget(date_group)
        
        # Repeat options
        repeat_group = QGroupBox("Lặp lại")
        repeat_layout = QGridLayout(repeat_group)
        
        self.repeat_checkboxes = {}
        days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        
        for i, day in enumerate(days):
            checkbox = QCheckBox(day)
            checkbox.setStyleSheet("""
                QCheckBox {
                    padding: 8px;
                    border-radius: 4px;
                }
                QCheckBox:hover {
                    background-color: #e9ecef;
                }
            """)
            repeat_layout.addWidget(checkbox, i // 4, i % 4)
            self.repeat_checkboxes[i+1] = checkbox  # 1-7 (Monday=1)
            
        # Quick repeat options
        quick_repeat_layout = QHBoxLayout()
        
        repeat_buttons = [
            ("Hàng ngày", lambda: self._set_repeat_days([1,2,3,4,5,6,7])),
            ("Ngày làm việc", lambda: self._set_repeat_days([1,2,3,4,5])),
            ("Cuối tuần", lambda: self._set_repeat_days([6,7])),
            ("Không lặp lại", lambda: self._set_repeat_days([]))
        ]
        
        for text, callback in repeat_buttons:
            button = QPushButton(text)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
            button.clicked.connect(callback)
            quick_repeat_layout.addWidget(button)
            
        repeat_layout.addLayout(quick_repeat_layout, 2, 0, 1, 4)
        
        layout.addWidget(repeat_group)
        
        # Snooze options
        snooze_group = QGroupBox("Tùy chọn báo lại")
        snooze_layout = QVBoxLayout(snooze_group)
        
        snooze_enabled = QCheckBox("Cho phép báo lại")
        snooze_enabled.setChecked(True)
        
        snooze_time_layout = QHBoxLayout()
        snooze_time_label = QLabel("Thời gian báo lại:")
        self.snooze_time = QSpinBox()
        self.snooze_time.setRange(1, 60)
        self.snooze_time.setValue(5)
        self.snooze_time.setSuffix(" phút")
        
        snooze_time_layout.addWidget(snooze_time_label)
        snooze_time_layout.addWidget(self.snooze_time)
        snooze_time_layout.addStretch()
        
        snooze_layout.addWidget(snooze_enabled)
        snooze_layout.addLayout(snooze_time_layout)
        
        layout.addWidget(snooze_group)
          # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Lưu")
        save_button.setObjectName("saveButton")
        save_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Hủy")
        cancel_button.setObjectName("cancelButton")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def _set_repeat_days(self, days):
        """Set the repeat days checkboxes."""
        for day_num, checkbox in self.repeat_checkboxes.items():
            checkbox.setChecked(day_num in days)
            
    def get_alarm_data(self):
        """Get the alarm data from dialog inputs."""
        alarm_time = self.time_edit.time()
        alarm_date = self.calendar.selectedDate()
        
        # Get selected days for repeating
        repeat_days = []
        for day_num, checkbox in self.repeat_checkboxes.items():
            if checkbox.isChecked():
                repeat_days.append(day_num)
                
        # If repeat days selected, we don't use the calendar date
        use_specific_date = len(repeat_days) == 0
        
        return {
            "time": alarm_time,
            "date": alarm_date if use_specific_date else None,
            "repeat_days": repeat_days,
            "name": self.name_edit.text() or "Báo thức",
            "type": self.type_combo.currentText(),
            "snooze_enabled": True,  # TODO: Add snooze_enabled checkbox
            "snooze_time": self.snooze_time.value(),
            "active": True
        }


class TimeWidget(QWidget):
    """Widget for displaying time information and alarms."""
    
    def __init__(self, time_service=None, lcd_service=None):
        super().__init__()
        
        # Set up the time service
        self.time_service = time_service if time_service else TimeService()
        
        # Set up the LCD service
        self.lcd_service = lcd_service
        
        # Connect LCD service to TimeService if available
        if self.lcd_service and hasattr(self.time_service, 'set_hardware_interface'):            # Create a mock hardware interface that provides LCD service access
            class LCDAccessor:
                def __init__(self, lcd_service):
                    self.lcd_service = lcd_service
                    
                def get_lcd_service(self):
                    return self.lcd_service
                
                def is_connected(self):
                    # Toujours retourner True pour permettre l'affichage des messages sur LCD
                    return True
                
                def display_message(self, message):
                    """Display message using the LCD service."""
                    if self.lcd_service:
                        self.lcd_service.set_display_text(message)
                        return True
                    return False
            
            self.time_service.set_hardware_interface(LCDAccessor(self.lcd_service))
        
        # Set up timezone data
        self.timezones = {
            "Việt Nam": "Asia/Ho_Chi_Minh",
            "New York": "America/New_York",
            "London": "Europe/London",
            "Tokyo": "Asia/Tokyo",
            "Sydney": "Australia/Sydney",
            "Paris": "Europe/Paris",
            "Berlin": "Europe/Berlin",
            "Moscow": "Europe/Moscow",
            "Dubai": "Asia/Dubai",
            "Los Angeles": "America/Los_Angeles",
            "Bangkok": "Asia/Bangkok",
            "Singapore": "Asia/Singapore",
            "Beijing": "Asia/Shanghai",
            "Cairo": "Africa/Cairo",
            "Rio de Janeiro": "America/Sao_Paulo",
            "Mexico City": "America/Mexico_City",
            "Johannesburg": "Africa/Johannesburg",
            "Rome": "Europe/Rome",
            "Seoul": "Asia/Seoul",
            "Jakarta": "Asia/Jakarta",
            "Amsterdam": "Europe/Amsterdam",
            "Istanbul": "Europe/Istanbul",
            "New Delhi": "Asia/Kolkata",
            "Toronto": "America/Toronto",
            "Manila": "Asia/Manila"
        }
        
        self.default_timezone = "Asia/Ho_Chi_Minh"
        self.selected_timezones = ["Asia/Ho_Chi_Minh", "America/New_York", "Europe/London"]
        
        # Dictionary to store alarm list items
        self.alarm_items = {}
        
        # Countdown timer instance
        self.countdown_timer = None
        
        # Set up the UI
        self._setup_ui()
        
        # Start the timer to update time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)  # Update every second
        
        # Initial time update
        self._update_time()
        
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
          # Enhanced Tab Widget styling
        self.tab_widget = QTabWidget()        
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(102, 126, 234, 0.1), stop:1 rgba(118, 75, 162, 0.1));
                padding: 0px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.8), stop:1 rgba(240, 240, 250, 0.9));
                color: #2d3748;
                padding: 12px 24px;
                margin-right: 4px;
                margin-bottom: 4px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                border: 2px solid rgba(102, 126, 234, 0.3);
                min-width: 120px;
                text-shadow: none;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border-bottom: none;
                margin-bottom: 0px;
                border: 2px solid #667eea;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(240, 240, 250, 1.0));
                border-color: rgba(102, 126, 234, 0.6);
                color: #1a202c;
                transform: translateY(-1px);
            }
        """)
        
        # Add tab widget animation
        self.tab_animation = QPropertyAnimation(self.tab_widget, b"geometry")
        self.tab_animation.setDuration(300)
        self.tab_animation.setEasingCurve(QEasingCurve.OutCubic)
          # ======= Time Tab =======
        time_tab = QWidget()
        time_tab.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
            }
        """)
        time_layout = QVBoxLayout(time_tab)
        time_layout.setSpacing(15) # Reduced spacing from 25 to 15
        time_layout.setContentsMargins(20, 20, 20, 20) # Reduced margins from 25 to 20
        
        # Enhanced title with modern glass morphism effect
        title_container = QFrame()
        title_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                backdrop-filter: blur(10px);
            }
        """)
        
        # Add glass morphism shadow effect
        title_shadow = QGraphicsDropShadowEffect()
        title_shadow.setBlurRadius(25)
        title_shadow.setColor(QColor(0, 0, 0, 30))
        title_shadow.setOffset(0, 8)
        title_container.setGraphicsEffect(title_shadow)
        
        title_layout_inner = QVBoxLayout(title_container)
        title_layout_inner.setContentsMargins(30, 20, 30, 20)
        
        title_label = QLabel("🌍 Thời Gian Thế Giới")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI", 22, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            color: white;
            font-size: 28px;
            font-weight: 700;
            text-shadow: 4px 4px 12px rgba(0, 0, 0, 0.4);
            letter-spacing: 1px;
        """)
        
        subtitle_label = QLabel("Theo dõi thời gian các múi giờ trên toàn thế giới")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: 500;
            margin-top: 5px;
        """)
        
        title_layout_inner.addWidget(title_label)
        title_layout_inner.addWidget(subtitle_label)
        time_layout.addWidget(title_container)
          # Ultra-modern clock display with 3D effects
        clock_container = QFrame()
        clock_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:0.3 #16213e, stop:0.7 #0f3460, stop:1 #e94560);
                border-radius: 25px;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """)
        
        # Enhanced shadow effect for depth
        clock_shadow = QGraphicsDropShadowEffect()
        clock_shadow.setBlurRadius(30)
        clock_shadow.setColor(QColor(0, 0, 0, 60))
        clock_shadow.setOffset(0, 10)
        clock_container.setGraphicsEffect(clock_shadow)
        
        clock_layout = QVBoxLayout(clock_container)
        clock_layout.setContentsMargins(40, 30, 40, 30)
        clock_layout.setSpacing(15)
        
        # Digital clock with neon effect
        self.digital_clock = QLabel()
        self.digital_clock.setAlignment(Qt.AlignCenter)
        clock_font = QFont("JetBrains Mono", 48, QFont.Bold)
        self.digital_clock.setFont(clock_font)
        self.digital_clock.setStyleSheet("""
            QLabel {
                color: #00ff88;
                font-size: 40px; /* Reduced font size from 54px to 40px */
                font-weight: 800;
                background: rgba(0, 255, 136, 0.1);
                border-radius: 15px;
                padding: 10px 20px;
                border: 2px solid rgba(0, 255, 136, 0.3);
                text-shadow: 0 0 20px #00ff88, 0 0 40px #00ff88;
                letter-spacing: 3px;
            }
        """)
        
        # Date display with elegant styling
        self.date_display = QLabel()
        self.date_display.setAlignment(Qt.AlignCenter)
        date_font = QFont("Segoe UI", 16, QFont.Medium)
        self.date_display.setFont(date_font)
        self.date_display.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 18px;
                font-weight: 600;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 8px 16px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                letter-spacing: 1px;
            }
        """)
        
        clock_layout.addWidget(self.digital_clock)
        clock_layout.addWidget(self.date_display)
        clock_layout.addStretch()
        
        time_layout.addWidget(clock_container)
          # Enhanced search panel with glass morphism
        search_panel = QFrame()
        search_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                backdrop-filter: blur(15px);
            }
        """)
        
        # Add search panel shadow
        search_shadow = QGraphicsDropShadowEffect()
        search_shadow.setBlurRadius(20)
        search_shadow.setColor(QColor(0, 0, 0, 30))
        search_shadow.setOffset(0, 5)
        search_panel.setGraphicsEffect(search_shadow)
        
        search_layout = QHBoxLayout(search_panel)
        search_layout.setContentsMargins(25, 15, 25, 15)
        search_layout.setSpacing(15)
        
        search_label = QLabel("🔍 Tìm kiếm:")
        search_label.setStyleSheet("""
            color: white;
            font-weight: 600;
            font-size: 16px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        """)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nhập tên thành phố hoặc quốc gia...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
                color: #333;
            }
            QLineEdit:focus {
                border-color: #00ff88;
                background: white;
                box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
            }
            QLineEdit::placeholder {
                color: #999;
                font-style: italic;
            }
        """)
        
        self.search_button = QPushButton("🚀 Tìm")
        self.search_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 12px 24px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                border: none;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5a67d8, stop:1 #667eea);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4c51bf, stop:1 #5a67d8);
                transform: translateY(0px);
            }
        """)
        self.search_button.clicked.connect(self._search_timezone)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_button)
        
        time_layout.addWidget(search_panel)
          # Enhanced world clock title with dynamic styling
        world_clock_header = QHBoxLayout()
        self.world_clock_title = QLabel("🌐 Các múi giờ đã thêm (0)")
        title_font_world = QFont("Segoe UI", 18, QFont.Bold)
        self.world_clock_title.setFont(title_font_world)
        self.world_clock_title.setStyleSheet("""
            color: white;
            font-size: 20px;
            font-weight: 700;
            text-shadow: 2px 2px 6px rgba(0, 0, 0, 0.4);
            padding: 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        """)
        world_clock_header.addWidget(self.world_clock_title)
        world_clock_header.addStretch()
        
        time_layout.addLayout(world_clock_header)
          # Enhanced timezone selection panel with premium styling
        tz_panel = QFrame()
        tz_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.25);
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                backdrop-filter: blur(15px);
            }
        """)
        
        # Add timezone panel shadow
        tz_shadow = QGraphicsDropShadowEffect()
        tz_shadow.setBlurRadius(20)
        tz_shadow.setColor(QColor(0, 0, 0, 30))
        tz_shadow.setOffset(0, 5)
        tz_panel.setGraphicsEffect(tz_shadow)
        
        tz_layout = QHBoxLayout(tz_panel)
        tz_layout.setContentsMargins(25, 15, 25, 15)
        tz_layout.setSpacing(15)
        
        tz_label = QLabel("➕ Thêm múi giờ:")
        tz_label.setStyleSheet("""
            color: white;
            font-weight: 600;
            font-size: 16px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        """)
        
        self.tz_combo = QComboBox()
        self.tz_combo.addItems(sorted(self.timezones.keys()))
        self.tz_combo.setStyleSheet("""
            QComboBox {
                padding: 12px 16px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
                color: #333;
                min-width: 200px;
            }
            QComboBox:focus {
                border-color: #667eea;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 8px;
                background: white;
                selection-background-color: #667eea;
                selection-color: white;
            }
        """)
        
        add_button = QPushButton("✨ Thêm")
        add_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 12px 24px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                border: none;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5a67d8, stop:1 #667eea);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4c51bf, stop:1 #5a67d8);
                transform: translateY(0px);
            }
        """)
        add_button.clicked.connect(self._add_timezone)
        
        tz_layout.addWidget(tz_label)
        tz_layout.addWidget(self.tz_combo)
        tz_layout.addWidget(add_button)
        
        time_layout.addWidget(tz_panel)
          # Premium LCD Clock Display Panel
        lcd_clock_panel = QFrame()
        lcd_clock_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                backdrop-filter: blur(15px);
            }
        """)
        
        # Add LCD panel shadow
        lcd_shadow = QGraphicsDropShadowEffect()
        lcd_shadow.setBlurRadius(20)
        lcd_shadow.setColor(QColor(0, 0, 0, 30))
        lcd_shadow.setOffset(0, 5)
        lcd_clock_panel.setGraphicsEffect(lcd_shadow)
        
        lcd_clock_layout = QHBoxLayout(lcd_clock_panel)
        lcd_clock_layout.setContentsMargins(25, 15, 25, 15)
        lcd_clock_layout.setSpacing(15)
        
        lcd_clock_label = QLabel("📺 Hiển thị thời gian trên LCD:")
        lcd_clock_label.setStyleSheet("""
            color: white;
            font-weight: 600;
            font-size: 16px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        """)
        
        self.show_clock_button = QPushButton("🎯 Hiển thị thời gian")
        self.show_clock_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #28a745, stop:1 #20c997);
                color: white;
                padding: 12px 20px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                border: none;
                min-width: 150px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #218838, stop:1 #1e7e34);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
                transform: translateY(0px);
            }
        """)
        self.show_clock_button.clicked.connect(self._show_clock_on_lcd)
        
        self.stop_clock_button = QPushButton("⏹️ Dừng hiển thị")
        self.stop_clock_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                padding: 12px 20px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                border: none;
                min-width: 130px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #a71e2a, stop:1 #8b1a1a);
                transform: translateY(0px);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6c757d, stop:1 #495057);
                color: rgba(255, 255, 255, 0.6);
            }
        """)
        self.stop_clock_button.clicked.connect(self._stop_clock_on_lcd)
        self.stop_clock_button.setEnabled(False)  # Initially disabled
        
        lcd_clock_layout.addWidget(lcd_clock_label)
        lcd_clock_layout.addStretch()
        lcd_clock_layout.addWidget(self.show_clock_button)
        lcd_clock_layout.addWidget(self.stop_clock_button)
        
        time_layout.addWidget(lcd_clock_panel)
          # Enhanced world clock grid with premium styling
        world_clock_scroll = QScrollArea()
        world_clock_scroll.setWidgetResizable(True)
        world_clock_scroll.setFrameShape(QFrame.NoFrame)
        world_clock_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.1);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a67d8, stop:1 #667eea);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        world_clock_container = QWidget()
        world_clock_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        
        # Add container shadow
        container_shadow = QGraphicsDropShadowEffect()
        container_shadow.setBlurRadius(25)
        container_shadow.setColor(QColor(0, 0, 0, 40))
        container_shadow.setOffset(0, 8)
        world_clock_container.setGraphicsEffect(container_shadow)
        
        self.world_clock_layout = QGridLayout(world_clock_container)
        self.world_clock_layout.setContentsMargins(25, 25, 25, 25)
        self.world_clock_layout.setSpacing(15)
        
        # Enhanced headers with premium styling
        header_font = QFont("Segoe UI", 12, QFont.Bold)
        
        header_location = QLabel("🌍 Địa điểm")
        header_location.setFont(header_font)
        header_location.setStyleSheet("""
            color: white;
            font-size: 13px; /* Reduced font size from 14px to 13px */
            font-weight: 700;
            background: rgba(255, 255, 255, 0.1);
            padding: 6px 10px; /* Reduced padding from 8px 12px */
            border-radius: 8px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        """)
        
        header_time = QLabel("⏰ Thời gian")
        header_time.setFont(header_font)
        header_time.setStyleSheet("""
            color: white;
            font-size: 13px; /* Reduced font size from 14px to 13px */
            font-weight: 700;
            background: rgba(255, 255, 255, 0.1);
            padding: 6px 10px; /* Reduced padding from 8px 12px */
            border-radius: 8px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        """)
        
        header_date = QLabel("📅 Ngày")
        header_date.setFont(header_font)
        header_date.setStyleSheet("""
            color: white;
            font-size: 13px; /* Reduced font size from 14px to 13px */
            font-weight: 700;
            background: rgba(255, 255, 255, 0.1);
            padding: 6px 10px; /* Reduced padding from 8px 12px */
            border-radius: 8px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        """)
        
        header_action = QLabel("⚙️ Thao tác")
        header_action.setFont(header_font)
        header_action.setStyleSheet("""
            color: white;
            font-size: 13px; /* Reduced font size from 14px to 13px */
            font-weight: 700;
            background: rgba(255, 255, 255, 0.1);
            padding: 6px 10px; /* Reduced padding from 8px 12px */
            border-radius: 8px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
        """)
        
        self.world_clock_layout.addWidget(header_location, 0, 0)
        self.world_clock_layout.addWidget(header_time, 0, 1)
        self.world_clock_layout.addWidget(header_date, 0, 2)
        self.world_clock_layout.addWidget(header_action, 0, 3)
        
        world_clock_scroll.setWidget(world_clock_container)
        time_layout.addWidget(world_clock_scroll, 1) # Added stretch factor of 1
        
        # Initialize the world clocks
        self.world_clocks = {}
        for i, tz in enumerate(self.selected_timezones):
            self._add_clock_to_grid(tz, i + 1)
            
        # Add time tab to tab widget
        self.tab_widget.addTab(time_tab, "Thời gian")
          # ======= Alarm Tab =======
        alarm_tab = QWidget()
        alarm_tab.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #faf5ff, stop:1 #f8fafc);
                
            }
        """)
        alarm_layout = QVBoxLayout(alarm_tab)
        alarm_layout.setSpacing(25)
        alarm_layout.setContentsMargins(20, 20, 20, 20)
        
        # Enhanced title with purple gradient
        alarm_title_container = QFrame()
        alarm_title_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #192239, stop:1 #65356e);
                border-radius: 15px;
                padding: 15px;
            }
        """)
        alarm_title_layout = QVBoxLayout(alarm_title_container)
        
        alarm_title = QLabel("⏰ Quản lý Báo Thức")
        alarm_title.setAlignment(Qt.AlignCenter)
        alarm_title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        alarm_title.setStyleSheet("""
            color: white;
            font-size: 40px;
            font-weight: 700;
            letter-spacing: 1px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        """)
        
        alarm_subtitle = QLabel("Tạo, chỉnh sửa và quản lý các báo thức của bạn")
        alarm_subtitle.setAlignment(Qt.AlignCenter)
        alarm_subtitle.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: 500;
            margin-top: 5px;
        """)
        
        alarm_title_layout.addWidget(alarm_title)
        alarm_title_layout.addWidget(alarm_subtitle)
        
        alarm_layout.addWidget(alarm_title_container)
        
        # Enhanced control panel with purple theme
        controls_panel = QFrame()
        controls_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #f8fafc);
                border-radius: 18px;
                border: 2px solid #e9d5ff;
                padding: 10px;
            }
        """)
        
        # Add subtle drop shadow to controls panel
        controls_shadow = QGraphicsDropShadowEffect()
        controls_shadow.setBlurRadius(12)
        controls_shadow.setColor(QColor(139, 92, 246, 80))
        controls_shadow.setOffset(0, 4)
        controls_panel.setGraphicsEffect(controls_shadow)
        
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(25, 20, 25, 20)
        controls_layout.setSpacing(15)
        
        # Enhanced buttons with purple gradient theme
        self.add_alarm_button = QPushButton("➕ Thêm báo thức")
        self.add_alarm_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8b5cf6, stop:1 #a78bfa);
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 15px;
                border: none;
                min-width: 150px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c3aed, stop:1 #9333ea);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6d28d9, stop:1 #7e22ce);
            }
        """)
        self.add_alarm_button.clicked.connect(self._add_alarm)
        
        self.edit_alarm_button = QPushButton("✏️ Chỉnh sửa")
        self.edit_alarm_button.setEnabled(False)
        self.edit_alarm_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #06b6d4, stop:1 #0891b2);
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 15px;
                border: none;
                min-width: 130px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0891b2, stop:1 #0e7490);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0e7490, stop:1 #155e75);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d1d5db, stop:1 #9ca3af);
                color: #6b7280;
            }
        """)
        self.edit_alarm_button.clicked.connect(self._edit_alarm)
        
        self.delete_alarm_button = QPushButton("🗑️ Xóa")
        self.delete_alarm_button.setEnabled(False)
        self.delete_alarm_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 15px;
                border: none;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #b91c1c, stop:1 #991b1b);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d1d5db, stop:1 #9ca3af);
                color: #6b7280;
            }
        """)
        self.delete_alarm_button.clicked.connect(self._delete_alarm)
        
        # Enhanced stop sound button with distinctive styling
        self.stop_alarm_button = QPushButton("🔇 Dừng âm thanh")
        self.stop_alarm_button.setVisible(False)
        self.stop_alarm_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f59e0b, stop:1 #d97706);
                color: white;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 15px;
                border: none;
                min-width: 150px;
                animation: pulse 2s infinite;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d97706, stop:1 #b45309);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #b45309, stop:1 #92400e);
            }
        """)
        self.stop_alarm_button.clicked.connect(self._stop_alarm_sound)
        
        controls_layout.addWidget(self.add_alarm_button)
        controls_layout.addWidget(self.edit_alarm_button)
        controls_layout.addWidget(self.delete_alarm_button)
        controls_layout.addWidget(self.stop_alarm_button)
        controls_layout.addStretch()
        
        alarm_layout.addWidget(controls_panel)
        
        # Enhanced alarm list container with purple theme
        alarm_list_container = QFrame()
        alarm_list_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #fefbff);
                border-radius: 18px;
                border: 2px solid #e9d5ff;
            }
        """)
        
        # Add subtle drop shadow to list container
        list_shadow = QGraphicsDropShadowEffect()
        list_shadow.setBlurRadius(15)
        list_shadow.setColor(QColor(139, 92, 246, 60))
        list_shadow.setOffset(0, 6)
        alarm_list_container.setGraphicsEffect(list_shadow)        
        # Enhanced scroll area with purple styling
        alarm_scroll = QScrollArea()
        alarm_scroll.setWidgetResizable(True)
        alarm_scroll.setFrameShape(QFrame.NoFrame)
        alarm_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f3e8ff, stop:1 #e9d5ff);
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #a78bfa, stop:1 #8b5cf6);
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #7c3aed);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Enhanced container widget for alarm list
        alarm_list_widget = QWidget()
        self.alarm_list_layout = QVBoxLayout(alarm_list_widget)
        self.alarm_list_layout.setContentsMargins(25, 25, 25, 25)
        self.alarm_list_layout.setSpacing(20)
        
        # Enhanced empty state with purple theme
        self.empty_alarms_label = QLabel("🕐 Chưa có báo thức nào")
        self.empty_alarms_label.setAlignment(Qt.AlignCenter)
        self.empty_alarms_label.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-size: 22px;
                font-weight: 600;
                padding: 60px 40px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #faf5ff, stop:1 #f3e8ff);
                border-radius: 15px;
                border: 3px dashed #c084fc;
            }
        """)
        self.alarm_list_layout.addWidget(self.empty_alarms_label)
        self.alarm_list_layout.addStretch()
        
        alarm_scroll.setWidget(alarm_list_widget)
        
        alarm_list_layout = QVBoxLayout(alarm_list_container)
        alarm_list_layout.setContentsMargins(0, 0, 0, 0)
        alarm_list_layout.addWidget(alarm_scroll)
        
        alarm_layout.addWidget(alarm_list_container)
        
        # Add alarm tab to tab widget
        self.tab_widget.addTab(alarm_tab, "Báo thức")
        
        # ======= Countdown Tab =======
        countdown_tab = QWidget()
        countdown_tab.setStyleSheet("background-color: #f8f9fa;")
        countdown_layout = QVBoxLayout(countdown_tab)
        countdown_layout.setSpacing(20)
        
        # Title
        countdown_title = QLabel("Đếm ngược")
        countdown_title.setAlignment(Qt.AlignCenter)
        countdown_title.setFont(title_font)
        countdown_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        countdown_layout.addWidget(countdown_title)
        
        # Create countdown timer instance
        self.countdown_timer = CountdownTimer()
        countdown_layout.addWidget(self.countdown_timer)
        
        # Add countdown tab to tab widget
        self.tab_widget.addTab(countdown_tab, "Đếm ngược")
        
        # Add the tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Check if sound file exists
        self.alarm_sound_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'sounds', 'alarm.mp3'
        )
        if not os.path.exists(self.alarm_sound_path):
            logger.warning(f"Alarm sound file not found at: {self.alarm_sound_path}")
        
    def _update_time(self):
        """Update all time displays and check alarms."""
        try:
            # Update Vietnam time
            now = datetime.datetime.now(pytz.timezone(self.default_timezone))
            
            # Update digital clock with modern format
            self.digital_clock.setText(now.strftime("%H:%M:%S"))
            
            # Update date display with Vietnamese format
            day_names = {
                0: "Thứ Hai",
                1: "Thứ Ba",
                2: "Thứ Tư",
                3: "Thứ Năm",
                4: "Thứ Sáu", 
                5: "Thứ Bảy",
                6: "Chủ Nhật"
            }
            day_name = day_names.get(now.weekday(), "")
            formatted_date = f"{day_name}, {now.day} Tháng {now.month} Năm {now.year}"
            self.date_display.setText(formatted_date)
            
            # Update world clocks
            for tz in self.world_clocks:
                if tz in self.world_clocks:
                    time_label = self.world_clocks[tz]["time"]
                    date_label = self.world_clocks[tz]["date"]
                    
                    tz_time = datetime.datetime.now(pytz.timezone(tz))
                    time_label.setText(tz_time.strftime("%H:%M:%S"))
                    date_label.setText(tz_time.strftime("%d/%m/%Y"))
              # Check alarms
            if hasattr(self.time_service, 'check_alarms'):
                self.time_service.check_alarms()
            
            # Update LCD clock display if it's showing
            if hasattr(self.time_service, 'is_clock_displaying') and self.time_service.is_clock_displaying():
                self._update_lcd_clock_from_timer()
                
        except Exception as e:
            logger.error(f"Error updating time display: {str(e)}")
    
    def _update_lcd_clock_from_timer(self):
        """Update LCD clock display from the main timer (called every second)."""
        try:
            # Get LCD service through hardware interface if available
            if (hasattr(self.time_service, 'hardware_interface') and 
                self.time_service.hardware_interface and 
                hasattr(self.time_service.hardware_interface, 'get_lcd_service')):
                lcd_service = self.time_service.hardware_interface.get_lcd_service()
                if lcd_service:
                    self._update_lcd_clock_display(lcd_service)
        except Exception as e:
            logger.error(f"Error updating LCD clock from timer: {str(e)}")
    
    def _add_timezone(self):
        """Add a new timezone to the world clock display."""
        city_name = self.tz_combo.currentText()
        timezone = self.timezones[city_name]
        
        # Check if already added
        if timezone in self.world_clocks:
            return
              # Add to selected timezones
        self.selected_timezones.append(timezone)
        
        # Add to grid
        row = len(self.world_clocks) + 1
        self._add_clock_to_grid(timezone, row)
        
        # Update world clock title
        self._update_world_clock_title()
    
    def _add_clock_to_grid(self, timezone, row):
        """Add a clock for the specified timezone to the grid with premium styling."""
        try:
            # Find the matching city name
            city_name = next((name for name, tz in self.timezones.items() if tz == timezone), timezone)
            
            # Create enhanced city label with flag emoji
            city_label = QLabel(f"🏙️ {city_name}")
            city_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 13px; /* Reduced font size from 14px to 13px */
                    font-weight: 600;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 6px 10px; /* Reduced padding from 8px 12px */
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
            """)
            
            # Create enhanced time label with digital font and neon effect
            time_label = QLabel()
            time_label.setStyleSheet("""
                QLabel {
                    font-family: 'JetBrains Mono', 'Consolas', monospace;
                    font-weight: 700;
                    font-size: 15px; /* Reduced font size from 16px to 15px */
                    color: #00ff88;
                    background: rgba(0, 255, 136, 0.1);
                    padding: 6px 10px; /* Reduced padding from 8px 12px */
                    border-radius: 8px;
                    border: 1px solid rgba(0, 255, 136, 0.3);
                    text-shadow: 0 0 10px #00ff88;
                    letter-spacing: 1px;
                }
            """)
            
            # Create enhanced date label
            date_label = QLabel()
            date_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 12px; /* Reduced font size from 13px to 12px */
                    font-weight: 500;
                    background: rgba(255, 255, 255, 0.08);
                    padding: 6px 10px; /* Reduced padding from 8px 12px */
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
            """)
            
            # Create enhanced remove button with modern styling
            remove_button = QPushButton("🗑️ Xóa")
            remove_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ff6b6b, stop:1 #ee5a52);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 10px; /* Reduced padding from 8px 12px */
                    font-size: 11px; /* Reduced font size from 12px to 11px */
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ff5252, stop:1 #f44336);
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #e53935, stop:1 #d32f2f);
                    transform: translateY(0px);
                }
            """)
            remove_button.clicked.connect(lambda: self._remove_timezone(timezone))
            
            # Add hover effects to all items in the row
            for widget in [city_label, time_label, date_label]:
                widget.enterEvent = lambda e, w=widget: self._on_clock_row_hover(w, True)
                widget.leaveEvent = lambda e, w=widget: self._on_clock_row_hover(w, False)
            
            # Add to grid with proper spacing
            self.world_clock_layout.addWidget(city_label, row, 0)
            self.world_clock_layout.addWidget(time_label, row, 1)
            self.world_clock_layout.addWidget(date_label, row, 2)
            self.world_clock_layout.addWidget(remove_button, row, 3)
            
            # Store references
            self.world_clocks[timezone] = {
                "city": city_label,
                "time": time_label,
                "date": date_label,
                "button": remove_button,
                "row": row
            }
            
            # Update world clock title count
            self._update_world_clock_title()
            
        except Exception as e:
            logger.error(f"Error adding timezone: {str(e)}")
    
    def _on_clock_row_hover(self, widget, is_hover):
        """Handle hover effects for clock row items."""
        try:
            # Find all widgets in the same row
            timezone = None
            for tz, data in self.world_clocks.items():
                if widget in [data["city"], data["time"], data["date"]]:
                    timezone = tz
                    break
            
            if timezone:
                row_widgets = [
                    self.world_clocks[timezone]["city"],
                    self.world_clocks[timezone]["time"], 
                    self.world_clocks[timezone]["date"]
                ]
                
                if is_hover:
                    # Enhanced hover styling
                    for w in row_widgets:
                        if w == self.world_clocks[timezone]["time"]:
                            # Special hover for time label
                            w.setStyleSheet("""
                                QLabel {
                                    font-family: 'JetBrains Mono', 'Consolas', monospace;
                                    font-weight: 700;
                                    font-size: 16px;
                                    color: #00ff88;
                                    background: rgba(0, 255, 136, 0.2);
                                    padding: 8px 12px;
                                    border-radius: 8px;
                                    border: 2px solid rgba(0, 255, 136, 0.5);
                                    text-shadow: 0 0 15px #00ff88;
                                    letter-spacing: 1px;
                                }
                            """)
                        else:
                            # Standard hover for other labels
                            w.setStyleSheet(w.styleSheet().replace(
                                "rgba(255, 255, 255, 0.1)",
                                "rgba(255, 255, 255, 0.2)"
                            ).replace(
                                "rgba(255, 255, 255, 0.08)",
                                "rgba(255, 255, 255, 0.15)"
                            ))
                else:
                    # Reset to normal styling
                    self._reset_clock_row_styling(timezone)
                    
        except Exception as e:
            logger.debug(f"Error in hover effect: {str(e)}")
    
    def _reset_clock_row_styling(self, timezone):
        """Reset clock row styling to normal state."""
        if timezone in self.world_clocks:
            # Reset city label
            self.world_clocks[timezone]["city"].setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 13px; /* Reduced font size from 14px to 13px */
                    font-weight: 600;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 6px 10px; /* Reduced padding from 8px 12px */
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
            """)
            
            # Reset time label
            self.world_clocks[timezone]["time"].setStyleSheet("""
                QLabel {
                    font-family: 'JetBrains Mono', 'Consolas', monospace;
                    font-weight: 700;
                    font-size: 15px; /* Reduced font size from 16px to 15px */
                    color: #00ff88;
                    background: rgba(0, 255, 136, 0.1);
                    padding: 6px 10px; /* Reduced padding from 8px 12px */
                    border-radius: 8px;
                    border: 1px solid rgba(0, 255, 136, 0.3);
                    text-shadow: 0 0 10px #00ff88;
                    letter-spacing: 1px;
                }
            """)
            
            # Reset date label
            self.world_clocks[timezone]["date"].setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 12px; /* Reduced font size from 13px to 12px */
                    font-weight: 500;
                    background: rgba(255, 255, 255, 0.08);
                    padding: 6px 10px; /* Reduced padding from 8px 12px */
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
            """)
    
    def _remove_timezone(self, timezone):
        """Remove a timezone from the world clock display."""
        if timezone not in self.world_clocks:
            return
            
        # Get the clock data
        clock_data = self.world_clocks[timezone]
        
        # Remove from grid
        self.world_clock_layout.removeWidget(clock_data["city"])
        self.world_clock_layout.removeWidget(clock_data["time"])
        self.world_clock_layout.removeWidget(clock_data["date"])
        self.world_clock_layout.removeWidget(clock_data["button"])
        
        # Delete widgets
        clock_data["city"].deleteLater()
        clock_data["time"].deleteLater()
        clock_data["date"].deleteLater()
        clock_data["button"].deleteLater()
        
        # Remove from selected timezones
        if timezone in self.selected_timezones:
            self.selected_timezones.remove(timezone)
            
        # Remove from dictionary
        del self.world_clocks[timezone]
        
        # Reindex rows
        self._reindex_grid()
    
    def _reindex_grid(self):
        """Reindex the grid rows after removing a timezone."""
        row = 1
        for tz, data in self.world_clocks.items():
            # Update the stored row
            data["row"] = row
            
            # Move widgets to new row
            self.world_clock_layout.addWidget(data["city"], row, 0)
            self.world_clock_layout.addWidget(data["time"], row, 1)
            self.world_clock_layout.addWidget(data["date"], row, 2)
            self.world_clock_layout.addWidget(data["button"], row, 3)
            
            row += 1
    
    def _add_alarm(self):
        """Open dialog to add a new alarm."""
        dialog = AlarmSettingDialog(self)
        if dialog.exec_():
            # Get alarm data from dialog
            alarm_data = dialog.get_alarm_data()
            
            # Add to time service
            alarm_id = self.time_service.add_alarm(
                alarm_data["time"],
                alarm_data["date"],
                alarm_data["repeat_days"],
                alarm_data["name"]
            )
            
            if alarm_id:
                # Add to alarm list
                self._add_alarm_to_list(alarm_id, alarm_data)
                
                # Show success toast notification
                toast = ToastNotification("Đã thêm báo thức thành công", self)
                toast.show()
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể thêm báo thức.")
    
    def _add_alarm_to_list(self, alarm_id, alarm_data):
        """Add an alarm to the alarm list with enhanced purple styling."""
        # Hide empty state label if visible
        if self.empty_alarms_label.isVisible():
            self.empty_alarms_label.hide()
            
        # Create enhanced alarm item widget
        alarm_item = AlarmListItem(alarm_id, alarm_data)
        alarm_item.toggled.connect(self._on_alarm_toggled)
        alarm_item.clicked.connect(self._on_alarm_clicked)
        alarm_item.snooze.connect(self._on_alarm_snooze)
        alarm_item.stop_sound.connect(self._on_alarm_stop_sound)
        
        # Add to layout with enhanced spacing
        self.alarm_list_layout.addWidget(alarm_item)
        
        # Store reference to the item
        self.alarm_items[alarm_id] = alarm_item
        
        # Add elegant separator line with purple theme
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e9d5ff, stop:1 #c084fc);
                height: 2px;
                border: none;
                margin: 10px 0;
            }
        """)
        self.alarm_list_layout.addWidget(separator)
    
    def _on_alarm_toggled(self, alarm_id, is_active):
        """Handle toggling of an alarm's active state."""
        if alarm_id in self.alarm_items:
            # Get current alarm data
            alarm_data = self.time_service.get_alarm(alarm_id)
            
            if alarm_data:
                # If alarm is ringing, stop the sound
                if self.alarm_items[alarm_id].is_ringing:
                    if hasattr(self.time_service, 'stop_alarm_sound'):
                        self.time_service.stop_alarm_sound(alarm_id)
                        self.alarm_items[alarm_id].set_ringing(False)
                        self._check_and_hide_stop_button()
                
                # Update alarm in time service
                self.time_service.update_alarm(
                    alarm_id,
                    alarm_data["time"],
                    alarm_data["date"],
                    alarm_data["repeat_days"],
                    alarm_data["name"],
                    is_active
                )
                
                logger.info(f"Alarm {alarm_id} active state changed to {is_active}")
    
    def _on_alarm_snooze(self, alarm_id):
        """Handle snooze request for an alarm."""
        if hasattr(self.time_service, 'snooze_alarm'):
            success = self.time_service.snooze_alarm(alarm_id)
            if success:
                logger.info(f"Alarm {alarm_id} snoozed")
                # Update UI to show snooze state
                if alarm_id in self.alarm_items:
                    self.alarm_items[alarm_id].set_ringing(False)
        else:
            logger.warning("Snooze functionality not available in time service")
    
    def _on_alarm_stop_sound(self, alarm_id):
        """Handle stop sound request for an alarm."""
        if hasattr(self.time_service, 'stop_alarm_sound'):
            success = self.time_service.stop_alarm_sound(alarm_id)
            if success:
                logger.info(f"Alarm {alarm_id} sound stopped")
                # Update UI
                if alarm_id in self.alarm_items:
                    self.alarm_items[alarm_id].set_ringing(False)
                # Hide the main stop button if no alarms are ringing
                self._check_and_hide_stop_button()
        else:
            # Fallback to general stop alarm method
            self._stop_alarm_sound()
    
    def _check_and_hide_stop_button(self):
        """Check if any alarms are ringing and hide stop button if none."""
        any_ringing = any(item.is_ringing for item in self.alarm_items.values())
        if not any_ringing:
            self.stop_alarm_button.setVisible(False)
    
    def set_alarm_ringing(self, alarm_id, is_ringing=True):
        """Set an alarm to ringing state and show stop button."""
        if alarm_id in self.alarm_items:
            self.alarm_items[alarm_id].set_ringing(is_ringing)
            if is_ringing:
                self.stop_alarm_button.setVisible(True)
            else:
                self._check_and_hide_stop_button()
    
    def _on_alarm_clicked(self, alarm_id):
        """Handle clicking on an alarm item to select it."""
        # Deselect all alarms
        for item_id, item in self.alarm_items.items():
            item.setSelected(item_id == alarm_id)
        
        # Enable edit and delete buttons when an alarm is selected
        self.edit_alarm_button.setEnabled(True)
        self.delete_alarm_button.setEnabled(True)
        
        # Store currently selected alarm ID
        self.selected_alarm_id = alarm_id
    
    def _edit_alarm(self):
        """Edit the selected alarm."""
        # Check if we have a selected alarm ID
        if not hasattr(self, 'selected_alarm_id') or not self.selected_alarm_id:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn một báo thức để chỉnh sửa.")
            return
            
        # Get alarm data
        alarm_data = self.time_service.get_alarm(self.selected_alarm_id)
        
        if not alarm_data:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy báo thức.")
            return
            
        # Open dialog with existing data
        dialog = AlarmSettingDialog(self)
          # Set dialog fields from alarm data
        dialog.time_edit.setTime(alarm_data["time"])
        if alarm_data["date"]:
            dialog.calendar.setSelectedDate(alarm_data["date"])
            
        for day in alarm_data["repeat_days"]:
            if day in dialog.repeat_checkboxes:
                dialog.repeat_checkboxes[day].setChecked(True)
                
        dialog.name_edit.setText(alarm_data["name"])
        
        # Show dialog
        if dialog.exec_():
            # Get updated data
            updated_data = dialog.get_alarm_data()
            
            # Keep active state from existing alarm
            updated_data["active"] = alarm_data["active"]
            
            # Update alarm
            success = self.time_service.update_alarm(
                self.selected_alarm_id,
                updated_data["time"],
                updated_data["date"],
                updated_data["repeat_days"],
                updated_data["name"],
                updated_data["active"]
            )
            
            if success:
                # Update UI
                self.alarm_items[self.selected_alarm_id].update_alarm_data(updated_data)
                QMessageBox.information(self, "Báo thức", "Đã cập nhật báo thức thành công.")
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể cập nhật báo thức.")
    
    def _delete_alarm(self):
        """Delete the selected alarm."""
        # Check if we have a selected alarm ID
        if not hasattr(self, 'selected_alarm_id') or not self.selected_alarm_id:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn một báo thức để xóa.")
            return
            
        # Ask for confirmation
        confirm = QMessageBox.question(
            self, "Xác nhận xóa", 
            "Bạn có chắc chắn muốn xóa báo thức này không?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Delete from time service
            if self.time_service.delete_alarm(self.selected_alarm_id):
                # Remove from UI
                if self.selected_alarm_id in self.alarm_items:
                    # Get the widget
                    item = self.alarm_items[self.selected_alarm_id]
                    
                    # Also get the separator that follows the alarm item
                    item_index = self.alarm_list_layout.indexOf(item)
                    separator = None
                    if item_index + 1 < self.alarm_list_layout.count():
                        separator = self.alarm_list_layout.itemAt(item_index + 1).widget()
                    
                    # Remove widget from layout
                    self.alarm_list_layout.removeWidget(item)
                    item.deleteLater()
                    
                    # Remove separator if it exists
                    if separator:
                        self.alarm_list_layout.removeWidget(separator)
                        separator.deleteLater()
                    
                    # Remove from dictionary
                    del self.alarm_items[self.selected_alarm_id]
                    
                    # Clear selected alarm ID
                    self.selected_alarm_id = None
                    
                    # Disable edit and delete buttons
                    self.edit_alarm_button.setEnabled(False)
                    self.delete_alarm_button.setEnabled(False)
                    
                    # Show empty state if no alarms left
                    if not self.alarm_items:
                        self.empty_alarms_label.show()
                        
                    # Show success message
                    QMessageBox.information(self, "Báo thức", "Đã xóa báo thức thành công.")
            else:                QMessageBox.warning(self, "Lỗi", "Không thể xóa báo thức.")
    
    def _stop_alarm_sound(self):
        """Stop the currently ringing alarm with enhanced UI feedback."""
        try:
            if hasattr(self.time_service, 'stop_alarm'):
                success = self.time_service.stop_alarm()
                if success:
                    # Update all alarm items to stop ringing state
                    for alarm_item in self.alarm_items.values():
                        if alarm_item.is_ringing:
                            alarm_item.set_ringing(False)
                    
                    # Hide the stop button
                    self.stop_alarm_button.setVisible(False)
                    
                    # Show success message with purple styling
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Báo thức")
                    msg.setText("Đã tắt âm thanh báo thức.")
                    msg.setIcon(QMessageBox.Information)
                    msg.setStyleSheet("""
                        QMessageBox {
                            background-color: #faf5ff;
                        }
                        QMessageBox QPushButton {
                            background-color: #8b5cf6;
                            color: white;
                            padding: 8px 16px;
                            border-radius: 6px;
                            font-weight: 600;
                        }
                        QMessageBox QPushButton:hover {
                            background-color: #7c3aed;
                        }
                    """)
                    msg.exec_()
                    
                    logger.info("All alarm sounds stopped via main stop button")
                else:
                    self._show_error_message("Không thể tắt âm thanh báo thức.")
            else:
                self._show_error_message("Chức năng tắt báo thức không khả dụng.")
        except Exception as e:
            logger.error(f"Error stopping alarm sound: {str(e)}")
            self._show_error_message("Có lỗi xảy ra khi tắt âm thanh báo thức.")
    
    def _show_error_message(self, message):
        """Show error message with consistent purple styling."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Lỗi")
        msg.setText(message)
        msg.setIcon(QMessageBox.Warning)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #fef2f2;
            }
            QMessageBox QPushButton {
                background-color: #ef4444;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QMessageBox QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        msg.exec_()
    
    def _refresh_alarm_list(self):
        """Refresh the alarm list from the time service data."""
        # Clear existing alarm items
        for alarm_id, item in list(self.alarm_items.items()):
            if item and item.parent():
                self.alarm_list_layout.removeWidget(item)
                item.deleteLater()
        
        # Clear separator lines
        for i in reversed(range(self.alarm_list_layout.count())):
            widget = self.alarm_list_layout.itemAt(i).widget()
            if widget and widget != self.empty_alarms_label:  # Don't remove the empty state label
                self.alarm_list_layout.removeWidget(widget)
                widget.deleteLater()
        
        # Clear alarm items dictionary
        self.alarm_items.clear()
        
        # Get alarms from time service
        alarms = self.time_service.get_all_alarms()
        
        # Show/hide empty state label
        if not alarms:
            self.empty_alarms_label.show()
        else:
            self.empty_alarms_label.hide()
            
            # Add alarms to list
            for alarm_id, alarm_data in alarms.items():
                self._add_alarm_to_list(alarm_id, alarm_data)
    
    def showEvent(self, event):
        """Handle widget show event."""
        super().showEvent(event)
        
        # Refresh alarm list when widget becomes visible
        if hasattr(self.time_service, 'get_all_alarms'):
            self._refresh_alarm_list()
            
    def _search_timezone(self):
        """Search for a timezone based on user input."""
        search_text = self.search_input.text().strip().lower()
        if not search_text:
            return
            
        # Search through timezone names (both display names and IANA identifiers)
        matches = []
        for city_name, timezone_id in self.timezones.items():
            if search_text in city_name.lower() or search_text in timezone_id.lower():
                matches.append((city_name, timezone_id))
        
        if not matches:
            QMessageBox.information(
                self,
                "Tìm kiếm múi giờ",
                f"Không tìm thấy múi giờ phù hợp với '{search_text}'."
            )
            return
            
        # If only one match, add it directly
        if len(matches) == 1:
            city_name, timezone_id = matches[0]
            
            # Check if already added
            if timezone_id in self.world_clocks:
                QMessageBox.information(
                    self,
                    "Múi giờ đã tồn tại",
                    f"Múi giờ {city_name} đã được thêm vào danh sách."
                )
                return
                
            # Add to selected timezones
            self.selected_timezones.append(timezone_id)
            
            # Add to grid
            row = len(self.world_clocks) + 1
            self._add_clock_to_grid(timezone_id, row)
            
            # Update title
            self._update_world_clock_title()
            
            # Clear search input
            self.search_input.clear()
            
            return
            
        # If multiple matches, show a selection dialog
        selection_dialog = QDialog(self)
        selection_dialog.setWindowTitle("Chọn múi giờ")
        selection_dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(selection_dialog)
        layout.addWidget(QLabel(f"Tìm thấy {len(matches)} múi giờ phù hợp với '{search_text}':"))
        
        # Create list widget for selection
        list_widget = QListWidget()
        for city_name, timezone_id in matches:
            item = QListWidgetItem(f"{city_name} ({timezone_id})")
            item.setData(Qt.UserRole, timezone_id)
            list_widget.addItem(item)
            
        layout.addWidget(list_widget)
        
        # Add buttons
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Hủy")
        cancel_button.clicked.connect(selection_dialog.reject)
        
        add_button = QPushButton("Thêm")
        add_button.setDefault(True)
        add_button.clicked.connect(selection_dialog.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(add_button)
        layout.addLayout(button_layout)
        
        # Show dialog and process result
        if selection_dialog.exec_() == QDialog.Accepted:
            selected_items = list_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
                timezone_id = item.data(Qt.UserRole)
                
                # Check if already added
                if timezone_id in self.world_clocks:
                    QMessageBox.information(
                        self,
                        "Múi giờ đã tồn tại",
                        f"Múi giờ đã được thêm vào danh sách."
                    )
                    return
                    
                # Add to selected timezones
                self.selected_timezones.append(timezone_id)
                
                # Add to grid
                row = len(self.world_clocks) + 1
                self._add_clock_to_grid(timezone_id, row)
                
                # Update title
                self._update_world_clock_title()
                
                # Clear search input
                self.search_input.clear()
    
    def _show_clock_on_lcd(self):
        """Display current time on LCD screen."""
        try:
            # Start clock display in TimeService
            if hasattr(self.time_service, 'start_clock_display'):
                self.time_service.start_clock_display()
            else:
                # If method doesn't exist, create it
                self._start_clock_display_fallback()
                
            # Update button states
            self.show_clock_button.setEnabled(False)
            self.stop_clock_button.setEnabled(True)
            
            logger.info("Clock display started on LCD")
            
        except Exception as e:
            logger.error(f"Error starting clock display: {str(e)}")
    
    def _stop_clock_on_lcd(self):
        """Stop displaying time on LCD screen."""
        try:
            # Stop clock display in TimeService
            if hasattr(self.time_service, 'stop_clock_display'):
                self.time_service.stop_clock_display()
            else:
                # If method doesn't exist, create it
                self._stop_clock_display_fallback()
                
            # Update button states
            self.show_clock_button.setEnabled(True)
            self.stop_clock_button.setEnabled(False)
            
            logger.info("Clock display stopped on LCD")
            
        except Exception as e:
            logger.error(f"Error stopping clock display: {str(e)}")
            
    def _start_clock_display_fallback(self):
        """Fallback method to start clock display if TimeService method doesn't exist."""
        # Try to access LCD service through time_service hardware interface
        try:
            if (hasattr(self.time_service, 'hardware_interface') and 
                self.time_service.hardware_interface and 
                hasattr(self.time_service.hardware_interface, 'get_lcd_service')):
                lcd_service = self.time_service.hardware_interface.get_lcd_service()
                if lcd_service:
                    # Start displaying time immediately
                    self._update_lcd_clock_display(lcd_service)
        except Exception as e:
            logger.warning(f"Could not access LCD service for clock display: {str(e)}")
    
    def _stop_clock_display_fallback(self):
        """Fallback method to stop clock display if TimeService method doesn't exist."""
        try:
            if (hasattr(self.time_service, 'hardware_interface') and 
                self.time_service.hardware_interface and 
                hasattr(self.time_service.hardware_interface, 'get_lcd_service')):
                lcd_service = self.time_service.hardware_interface.get_lcd_service()
                if lcd_service:
                    lcd_service.clear_and_reset()
        except Exception as e:
            logger.warning(f"Could not access LCD service to stop clock display: {str(e)}")
    
    def _update_lcd_clock_display(self, lcd_service):
        """Update LCD with current time information."""
        try:
            # Get current Vietnam time
            now = datetime.datetime.now(pytz.timezone(self.default_timezone))
            
            # Format as requested: Date: DD/MM/YYYY \n Time: HH:MM:SS
            date_str = now.strftime("%d/%m/%Y")
            time_str = now.strftime("%H:%M:%S")
            display_text = f"Time: {time_str}\nDate: {date_str}"
            
            # Send to LCD
            lcd_service.set_display_text(display_text)
            
        except Exception as e:
            logger.error(f"Error updating LCD clock display: {str(e)}")
    
    def _update_world_clock_title(self):
        """Update the world clock title with the count of timezones."""
        count = len(self.world_clocks)
        self.world_clock_title.setText(f"Các múi giờ đã thêm ({count})")


class ToastNotification(QWidget):
    """Custom toast notification widget that slides in from the right."""
    
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create container
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8b5cf6, stop:1 #a78bfa);
                border-radius: 10px;
                border: 1px solid #c084fc;
            }
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(139, 92, 246, 80))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)
        
        # Create message label
        message_label = QLabel(message)
        message_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: 600;
            padding: 10px;
        """)
        
        # Add to layout
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(message_label)
        layout.addWidget(container)
        
        # Set up animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Set up timer for auto-close
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self._start_close_animation)
        self.close_timer.setSingleShot(True)
        
        # Flag to track animation state
        self.is_closing = False
        
    def showEvent(self, event):
        """Handle show event to start animation."""
        super().showEvent(event)
        
        # Get parent geometry
        parent = self.parent()
        if parent:
            parent_geo = parent.geometry()
            
            # Calculate start and end positions
            start_x = parent_geo.right()
            end_x = parent_geo.right() - self.width() - 20
            
            # Set animation geometry
            self.animation.setStartValue(QRect(start_x, parent_geo.bottom() - self.height() - 20, 
                                             self.width(), self.height()))
            self.animation.setEndValue(QRect(end_x, parent_geo.bottom() - self.height() - 20,
                                           self.width(), self.height()))
            
            # Start animation
            self.animation.start()
            
            # Start close timer
            self.close_timer.start(3000)  # Close after 3 seconds
            
    def _start_close_animation(self):
        """Start the closing animation."""
        if not self.is_closing:
            self.is_closing = True
            self.animation.setDirection(QPropertyAnimation.Backward)
            self.animation.finished.connect(self.close)
            self.animation.start()
            
    def closeEvent(self, event):
        """Handle close event."""
        if self.animation.state() == QPropertyAnimation.Running:
            event.ignore()
            return
        super().closeEvent(event)