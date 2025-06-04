import sys
import time
import threading
import os
import json
import re
import base64
import mimetypes
from io import BytesIO
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QLabel, QScrollArea,
                             QFrame, QSizePolicy, QStackedWidget, QListWidget,
                             QListWidgetItem, QSpacerItem, QMenu, QAction, 
                             QGraphicsDropShadowEffect, QApplication, QButtonGroup,
                             QFileDialog, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QMetaObject, Q_ARG, QSize, QRect, QPoint, QByteArray, QBuffer
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QPixmap, QColor, QPainter, QPainterPath, QBrush, QPen, QImage, QLinearGradient

try:
    import pygame
except ImportError:
    pygame = None

# Handle both relative and absolute imports
try:
    from ..utils import config, logger
except ImportError:
    try:
        from utils import config, logger
    except ImportError:
        # Fallback for testing
        class MockConfig:
            CHAT_USER_BUBBLE_COLOR = "#0D6EFD"
            CHAT_ASSISTANT_BUBBLE_COLOR = "#F5F5F5"
            CHAT_USER_TEXT_COLOR = "#000000"
            CHAT_ASSISTANT_TEXT_COLOR = "#212121"
            CHAT_BACKGROUND_COLOR = "#F8F9FA"
        config = MockConfig()
        logger = None

# QueryWorker classes to replace missing workers module
class QueryWorker(QThread):
    """Worker thread for processing text queries to the AI assistant."""
    response_ready = pyqtSignal(str, str)  # sender, response
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, gemini_client, query):
        super().__init__()
        self.gemini_client = gemini_client
        self.query = query
    
    def run(self):
        """Process the query in a separate thread."""
        try:
            if self.gemini_client:
                response = self.gemini_client.generate_response(self.query)
                self.response_ready.emit("MIS Assistant", response)
            else:
                self.error_occurred.emit("AI client not available")
        except Exception as e:
            self.error_occurred.emit(str(e))

class QueryWorkerWithImage(QThread):
    """Worker thread for processing queries with image attachments."""
    response_ready = pyqtSignal(str, str, bytes, str)  # sender, response, image_data, file_name
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, gemini_client, query, image_data, file_name):
        super().__init__()
        self.gemini_client = gemini_client
        self.query = query
        self.image_data = image_data
        self.file_name = file_name
    
    def run(self):
        """Process the query with image in a separate thread."""
        try:
            if self.gemini_client:
                response = self.gemini_client.generate_response_with_image(
                    self.query, self.image_data
                )
                self.response_ready.emit("MIS Assistant", response, self.image_data, self.file_name)
            else:
                self.error_occurred.emit("AI client not available")
        except Exception as e:
            self.error_occurred.emit(str(e))

class ChatBubbleWidget(QWidget):
    """Custom widget for displaying chat bubbles in a Messenger-like interface."""
    
    def __init__(self, text, sender, bubble_color, text_color, avatar_path=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.sender = sender
        self.bubble_color = QColor(bubble_color)
        self.text_color = QColor(text_color)
        self.avatar_path = avatar_path
        self.is_user = sender == "User"
        self.avatar_size = 40
        self.bubble_radius = 18
        self.bubble_padding = 12
        self.avatar_margin = 10
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        self._create_layout()
        
    def _create_layout(self):
        """Create the layout for the chat bubble."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 8)
        main_layout.setSpacing(12)
        
        # Create avatar label
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(self.avatar_size, self.avatar_size)
        
        # Load avatar image or create default
        self._load_avatar()
        
        # Create bubble container for text
        self.bubble_container = QFrame()
        self.bubble_container.setObjectName("bubbleContainer")
        self.bubble_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # Set style for the bubble container - different colors for user and assistant
        if self.is_user:
            # User bubble with enhanced visibility using config colors
            self.bubble_container.setStyleSheet(f"""
                QFrame#bubbleContainer {{
                    background-color: {config.CHAT_USER_BUBBLE_COLOR};
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: {self.bubble_radius}px;
                    padding: {self.bubble_padding}px;
                }}
                QLabel {{
                    background-color: transparent;
                    color: white;
                }}
            """)
        else:
            # Assistant bubble - flat lighter color
            self.bubble_container.setStyleSheet(f"""
                QFrame#bubbleContainer {{
                    background-color: {config.CHAT_ASSISTANT_BUBBLE_COLOR};
                    border: 1px solid #E4E6EB;
                    border-radius: {self.bubble_radius}px;
                    padding: {self.bubble_padding}px;
                }}
            """)
        
        bubble_layout = QVBoxLayout(self.bubble_container)
        bubble_layout.setContentsMargins(self.bubble_padding, self.bubble_padding, 
                                       self.bubble_padding, self.bubble_padding)
        bubble_layout.setSpacing(6)
        
        # Create sender name label with timestamp
        timestamp = time.strftime("%H:%M")
        if self.is_user:
            sender_text = f"Bạn, {timestamp}"
        else:
            sender_text = f"{self.sender}, {timestamp}"
            
        self.sender_label = QLabel(sender_text)
        
        # Different color for sender names based on bubble type
        if self.is_user:
            self.sender_label.setStyleSheet(f"color: rgba(255, 255, 255, 1.0); font-size: 12px; font-weight: bold; background-color: transparent;")
        else:
            self.sender_label.setStyleSheet(f"color: #3d3d3d; font-size: 12px; font-weight: bold;")
        
        # Create text label with proper contrast and format text properly
        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # Format message text (handle HTML or escape special characters)
        self._format_message()
        
        # Different text color for better contrast
        if self.is_user:
            self.text_label.setStyleSheet("color: white; font-size: 15px; line-height: 145%; font-weight: 600; background-color: transparent;")
        else:
            self.text_label.setStyleSheet("color: #050505; font-size: 14px; line-height: 140%;")
        
        # Add text to bubble
        bubble_layout.addWidget(self.sender_label)
        bubble_layout.addWidget(self.text_label)
        
        # Arrange elements based on sender (user or assistant)
        if self.is_user:
            main_layout.addStretch()
            main_layout.addWidget(self.bubble_container)
            main_layout.addWidget(self.avatar_label)
            # Right align sender name
            self.sender_label.setAlignment(Qt.AlignRight)
        else:
            # For assistant, we place the bubble on the left
            main_layout.addWidget(self.avatar_label)
            main_layout.addWidget(self.bubble_container)
            main_layout.addStretch()
            # Left align sender name
            self.sender_label.setAlignment(Qt.AlignLeft)
            
    def _format_message(self):
        """Format message text to handle HTML or escape special characters."""
        import re
        import html
        
        try:
            # Sử dụng TextFormatter nếu khả dụng, nếu không dùng xử lý trực tiếp
            try:
                from ..models.text_formatter import TextFormatter
                formatted_text, text_format = TextFormatter.format_message_text(self.text)
                
                # Kiểm tra chuỗi có chứa thơ hoặc trích dẫn không
                if '>' in self.text and '\n' in self.text:
                    # Tìm kiếm đoạn trích dẫn dạng ">"
                    quote_pattern = r'(\n|^)\s*>.*(\n\s*>.*)*'
                    matches = re.findall(quote_pattern, self.text)
                    if matches:
                        # Nếu tìm thấy đoạn trích dẫn nhiều dòng, áp dụng định dạng đặc biệt hơn
                        formatted_text = TextFormatter.format_poem_text(self.text)
                
                if text_format == "html":
                    self.text_label.setTextFormat(Qt.RichText)
                    self.text_label.setText(formatted_text)
                    self.text_label.setOpenExternalLinks(True)
                elif text_format == "rich":
                    self.text_label.setTextFormat(Qt.RichText)
                    self.text_label.setText(formatted_text)
                    self.text_label.setOpenExternalLinks(True)
                else:
                    self.text_label.setTextFormat(Qt.PlainText)
                    self.text_label.setText(self.text)
                    
            except ImportError:
                # Fallback - Xử lý trực tiếp nếu không import được TextFormatter
                # Kiểm tra xem có phải là văn bản HTML không
                if self.text.startswith('<') and '>' in self.text:
                    # Nếu là HTML, hiển thị trực tiếp
                    self.text_label.setTextFormat(Qt.RichText)
                    self.text_label.setText(self.text)
                else:
                    # Tìm và chuyển URLs thành link có thể nhấp
                    url_pattern = r'(https?://[^\s]+)'
                    html_result = re.sub(url_pattern, r'<a href="\1">\1</a>', self.text)
                    
                    # Nếu có URLs, hiển thị dưới dạng HTML
                    if html_result != self.text:
                        self.text_label.setTextFormat(Qt.RichText)
                        self.text_label.setText(html_result)
                        self.text_label.setOpenExternalLinks(True)
                    else:
                        # Đảm bảo ký tự đặc biệt được hiển thị đúng
                        escaped_text = html.escape(self.text)
                        # Thay thế xuống dòng bằng thẻ <br>
                        formatted_text = escaped_text.replace('\n', '<br>')
                        self.text_label.setTextFormat(Qt.RichText)
                        self.text_label.setText(formatted_text)
        
        except Exception as e:
            # Nếu có lỗi, hiển thị dưới dạng văn bản thuần túy
            self.text_label.setTextFormat(Qt.PlainText)
            self.text_label.setText(self.text)
    
    def _load_avatar(self):
        """Load or create avatar image."""
        pixmap = QPixmap(self.avatar_size, self.avatar_size)
        pixmap.fill(Qt.transparent)
        
        if self.avatar_path and os.path.exists(self.avatar_path):
            # Load from file if exists
            avatar_img = QImage(self.avatar_path)
            avatar_pixmap = QPixmap.fromImage(avatar_img)
            
            # Create a rounded avatar
            rounded_pixmap = QPixmap(self.avatar_size, self.avatar_size)
            rounded_pixmap.fill(Qt.transparent)
            
            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Create circular path
            path = QPainterPath()
            path.addEllipse(0, 0, self.avatar_size, self.avatar_size)
            painter.setClipPath(path)
            
            # Draw the avatar
            painter.drawPixmap(0, 0, self.avatar_size, self.avatar_size, avatar_pixmap)
            painter.end()
            
            self.avatar_label.setPixmap(rounded_pixmap)
        else:
            # Create a default avatar with gradient
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw circle background with gradient
            if self.is_user:
                # Blue gradient for user
                gradient = QLinearGradient(0, 0, self.avatar_size, self.avatar_size)
                gradient.setColorAt(0, QColor("#4285F4"))
                gradient.setColorAt(1, QColor("#1A73E8"))
            else:
                # Purple/blue gradient for assistant
                gradient = QLinearGradient(0, 0, self.avatar_size, self.avatar_size)
                gradient.setColorAt(0, QColor("#9575CD"))
                gradient.setColorAt(1, QColor("#7986CB"))
                
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, self.avatar_size, self.avatar_size)
            
            # Add a subtle highlight for 3D effect
            highlight = QPainterPath()
            highlight.addEllipse(5, 5, self.avatar_size - 10, self.avatar_size/3)
            painter.fillPath(highlight, QColor(255, 255, 255, 60))
            
            # Draw initial letter
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 16, QFont.Bold))
            
            initial = self.sender[0].upper() if self.sender else "?"
            if self.is_user:
                initial = "B"  # "Bạn" in Vietnamese
            
            painter.drawText(pixmap.rect(), Qt.AlignCenter, initial)
            painter.end()
            
            self.avatar_label.setPixmap(pixmap)
            
    def sizeHint(self):
        """Provide size hint for layout management"""
        width = self.bubble_container.sizeHint().width() + self.avatar_size + 20
        height = max(self.bubble_container.sizeHint().height(), self.avatar_size) + 16
        return QSize(width, height)


class ChatBubbleWidgetWithImage(ChatBubbleWidget):
    """Extended chat bubble that can display an image attachment."""
    
    def __init__(self, text, sender, bubble_color, text_color, image_data=None, file_path=None, 
                 file_name=None, avatar_path=None, parent=None):
        super().__init__(text, sender, bubble_color, text_color, avatar_path, parent)
        self.image_data = image_data
        self.file_path = file_path
        self.file_name = file_name
        
        # Add image or file attachment if provided
        if image_data or file_path:
            self._add_attachment()
    
    def _create_layout(self):
        """Override to create a layout that can include an image."""
        super()._create_layout()
        
        # Create container for potential attachments
        self.attachment_container = QWidget()
        self.attachment_layout = QVBoxLayout(self.attachment_container)
        self.attachment_layout.setContentsMargins(0, 8, 0, 0)
        self.attachment_layout.setSpacing(5)
        
        # Insert attachment container after text
        bubble_layout = self.bubble_container.layout()
        bubble_layout.addWidget(self.attachment_container)
    
    def _add_attachment(self):
        """Add image or file attachment to the bubble."""
        if self.image_data:
            # Create image from image data
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray.fromBase64(self.image_data))
            
            # Scale image to reasonable size if needed (max 300px wide)
            if pixmap.width() > 300:
                pixmap = pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            
            # Create image label
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignLeft)
            
            # Add rounded corners to image
            image_label.setStyleSheet("""
                border: 1px solid #DDDDDD;
                border-radius: 8px;
                padding: 2px;
            """)
            
            # Add image to bubble
            self.attachment_layout.addWidget(image_label)
            
            # Add file name if available
            if self.file_name:
                file_name_label = QLabel(f"Hình ảnh: {self.file_name}")
                file_name_label.setStyleSheet("""
                    color: #555555;
                    font-size: 12px;
                    font-style: italic;
                """)
                self.attachment_layout.addWidget(file_name_label)
                
        elif self.file_path:
            # Create file attachment representation
            file_widget = QWidget()
            file_layout = QHBoxLayout(file_widget)
            file_layout.setContentsMargins(5, 5, 5, 5)
            
            # File icon
            file_icon_label = QLabel()
            file_icon = QPixmap(24, 24)
            file_icon.fill(Qt.transparent)
            
            # Draw a simple document icon
            painter = QPainter(file_icon)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor("#6c757d"), 1))
            painter.setBrush(QBrush(QColor("#f8f9fa")))
            painter.drawRect(4, 2, 16, 20)
            painter.drawLines([QPoint(8, 8), QPoint(16, 8), 
                              QPoint(8, 12), QPoint(16, 12), 
                              QPoint(8, 16), QPoint(16, 16)])
            painter.end()
            
            file_icon_label.setPixmap(file_icon)
            
            # File name and info
            file_name = self.file_name if self.file_name else os.path.basename(self.file_path)
            file_info_label = QLabel(f"Tệp đính kèm: {file_name}")
            file_info_label.setStyleSheet("""
                color: #0d6efd;
                font-size: 13px;
                text-decoration: underline;
            """)
            
            file_layout.addWidget(file_icon_label)
            file_layout.addWidget(file_info_label, 1)
            
            # Style the file widget
            file_widget.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 6px;
            """)
            
            self.attachment_layout.addWidget(file_widget)
    
    def sizeHint(self):
        """Override size hint to account for attachment."""
        # Start with the base size
        base_size = super().sizeHint()
        
        # Add space for attachment if present
        if hasattr(self, 'attachment_container') and not self.attachment_container.isHidden():
            attachment_height = self.attachment_container.sizeHint().height()
            return QSize(base_size.width(), base_size.height() + attachment_height)
            
        return base_size


class ChatWidget(QWidget):
    """Widget for interacting with the AI assistant through chat with a modern Messenger-like interface."""
    
    # Add signals for thread-safe operations
    speech_finished_signal = pyqtSignal()
    speech_result_signal = pyqtSignal(str)
    ui_update_signal = pyqtSignal(str, str)  # sender, message
    ui_update_with_image_signal = pyqtSignal(str, str, object, str)  # sender, message, image_data, filename
    status_update_signal = pyqtSignal(str)
    button_style_signal = pyqtSignal(str)
    
    def __init__(self, gemini_client, speech_processor, hardware_interface, time_service=None, weather_service=None):
        super().__init__()
        
        # Store references to the models
        self.gemini_client = gemini_client
        self.speech_processor = speech_processor
        self.hardware_interface = hardware_interface
        
        # Pass service references to GeminiClient if not already done
        if time_service and not self.gemini_client.time_service:
            self.gemini_client.time_service = time_service
            
        if weather_service and not self.gemini_client.weather_service:
            self.gemini_client.weather_service = weather_service
        
        # Initialize pygame for beep sound
        if pygame and not pygame.mixer.get_init():
            pygame.mixer.init()
        
        # Get path to beep sound and avatar images
        current_dir = os.path.dirname(os.path.abspath(__file__))
        resources_dir = os.path.abspath(os.path.join(current_dir, '../../resources'))
        sounds_dir = os.path.join(resources_dir, 'sounds')
        self.beep_sound_path = os.path.join(sounds_dir, 'beep.mp3')
        self.completion_sound_path = os.path.join(sounds_dir, 'completion.mp3')
        
        # Setup avatar paths with correct path resolution
        self.icons_dir = os.path.join(resources_dir, 'icons')
        self.user_avatar_path = os.path.join(self.icons_dir, 'user.png')
        self.assistant_avatar_path = os.path.join(self.icons_dir, 'assistant.png')
        
        # Make sure the avatar files exist, log if not
        if not os.path.exists(self.user_avatar_path):
            logger.error(f"User avatar not found at: {self.user_avatar_path}")
        else:
            logger.info(f"User avatar found successfully at: {self.user_avatar_path}")
            
        if not os.path.exists(self.assistant_avatar_path):
            logger.error(f"Assistant avatar not found at: {self.assistant_avatar_path}")
        else:
            logger.info(f"Assistant avatar found successfully at: {self.assistant_avatar_path}")
        
        # Biến lưu trữ thông tin hình ảnh đã chọn
        self.selected_image = {
            'path': None,
            'name': None,
            'image_data': None
        }
          # Connect signals to slots for thread-safe operations
        self.speech_finished_signal.connect(self._on_speech_finished)
        self.speech_result_signal.connect(self._on_speech_result)
        self.ui_update_signal.connect(self._add_message_to_chat)
        self.ui_update_with_image_signal.connect(self._add_message_to_chat_with_image)
        self.status_update_signal.connect(self._update_status_label)
        self.button_style_signal.connect(self._update_voice_button_style)
        
        if self.speech_processor:
            self.speech_processor.speech_started.connect(self._on_speech_processor_started)
            self.speech_processor.speech_finished.connect(self._on_speech_processor_finished)
            logger.info("Speech processor signals connected for hardware status updates")
        
        # Connect hotword detection signal to microphone activation
        if config.ENABLE_HOTWORD_DETECTION and hasattr(self.speech_processor, 'hotword_detected'):
            self.speech_processor.hotword_detected.connect(self._on_hotword_detected)
            logger.info(f"Hotword detection enabled with phrase: '{config.HOTWORD_PHRASE}'")
        
        # Register hardware button callback
        if self.hardware_interface:
            self.hardware_interface.register_callback('ACTIVATE_MICROPHONE', self._on_hardware_button_pressed)
        
        # Set up the UI
        self._setup_ui()
        
        self.is_processing = False
        
        # Create worker thread for queries
        self.query_thread = None
        
    def _setup_ui(self):
        """Set up the Messenger-like chat UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15) 
        layout.setSpacing(15)  
        
        # Header area with title and controls
        header_container = QWidget()
        header_container.setObjectName("headerContainer")
        header_container.setStyleSheet("""
            QWidget#headerContainer {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # Logo/Icon for the assistant
        logo_label = QLabel()
        logo_pixmap = QPixmap(32, 32)
        if os.path.exists(self.assistant_avatar_path):
            # Load from file if exists
            avatar_img = QImage(self.assistant_avatar_path)
            logo_pixmap = QPixmap.fromImage(avatar_img).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            # Create a default icon with gradient
            logo_pixmap.fill(Qt.transparent)
            painter = QPainter(logo_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            gradient = QLinearGradient(0, 0, 32, 32)
            gradient.setColorAt(0, QColor("#9575CD"))
            gradient.setColorAt(1, QColor("#7986CB"))
            
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 32, 32)
            painter.end()
        
        # Create a circular mask for the logo
        rounded_pixmap = QPixmap(32, 32)
        rounded_pixmap.fill(Qt.transparent)
        
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addEllipse(0, 0, 32, 32)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, logo_pixmap)
        painter.end()
        
        logo_label.setPixmap(rounded_pixmap)
        
        # Title label
        title_label = QLabel("MIS Assistant")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #212529;
        """)
        
        # Add speech speed control
        speed_control_container = QWidget()
        speed_control_layout = QHBoxLayout(speed_control_container)
        speed_control_layout.setContentsMargins(0, 0, 0, 0)
        speed_control_layout.setSpacing(5)
        
        speed_label = QLabel("Tốc độ:")
        speed_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        # Create speed selector buttons
        speed_options = {"1.0x": 1.0, "1.3x": 1.3, "1.5x": 1.5, "1.8x": 1.8, "2.0x": 2.0}
        
        # Get current speed from speech processor if available
        current_speed = 1.3  # Default
        if self.speech_processor:
            current_speed = self.speech_processor.get_playback_speed()
            
        # Create a button group for the speed controls
        self.speed_button_group = QButtonGroup(self)
        self.speed_button_group.setExclusive(True)  # Only one button can be checked at a time
        
        for label, value in speed_options.items():
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(abs(value - current_speed) < 0.05)  # Select current speed
            button.setProperty("speed_value", value)
            button.setFixedHeight(28)
            button.setFixedWidth(45)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    border: 1px solid #ced4da;
                    border-radius: 14px;
                    color: #495057;
                    font-size: 11px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
                QPushButton:checked {
                    background-color: #0d6efd;
                    color: white;
                    border: 1px solid #0d6efd;
                }
            """)
            # Connect button to change speed when clicked
            button.clicked.connect(self._change_speech_speed)
            
            # Add to button group
            self.speed_button_group.addButton(button)
            
            speed_control_layout.addWidget(button)
            
        speed_control_layout.addWidget(speed_label)
        
        # Layout elements
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(speed_control_container)
        
        # Add header to main layout
        layout.addWidget(header_container)
        
        # Chat messages container with shadow effect
        self.messages_container = QWidget()
        self.messages_container.setObjectName("messagesContainer")
        self.messages_container.setStyleSheet("""
            QWidget#messagesContainer {
                background-color: #F8F9FA;
                border: none;
            }
        """)
        
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(15, 20, 15, 20)  # Increased padding inside the chat area
        self.messages_layout.setSpacing(20)  # Increased spacing between messages for better readability
        self.messages_layout.setAlignment(Qt.AlignTop)
        
        # Add a spacer at the bottom to keep messages at the top
        self.messages_layout.addStretch()
        
        # Create a container for the scroll area with shadow
        scroll_container = QWidget()
        scroll_container.setObjectName("scrollContainer")
        scroll_container.setStyleSheet("""
            QWidget#scrollContainer {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)
        
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(1, 1, 1, 1)  # Very small margins to not interfere with the border radius
        
        # Scroll area for chat messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.messages_container)
        self.scroll_area.setFrameShape(QFrame.NoFrame)  # Remove the frame
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #F8F9FA;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #CED4DA;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #ADB5BD;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
                height: 0px;
            }
        """)
        
        scroll_layout.addWidget(self.scroll_area)
        
        # Add shadow effect to scroll container
        shadow = self.create_shadow_effect()
        scroll_container.setGraphicsEffect(shadow)
        
        layout.addWidget(scroll_container, 1)  # Add with stretch factor
        
        # Input area with modern styling and shadow effect
        input_container = QWidget()
        input_container.setObjectName("inputContainer")
        input_container.setStyleSheet("""
            QWidget#inputContainer {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 24px;
                padding: 2px;
            }
        """)
        
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(16, 8, 8, 8)
        input_layout.setSpacing(10)
        
        # Text input with modern styling
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Nhập câu hỏi hoặc yêu cầu của bạn...")
        self.input_field.setMinimumHeight(46)  # Slightly taller for better visibility
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                font-size: 14px;
                color: #212529;
                padding: 0 12px;
            }
            QLineEdit:focus {
                outline: none;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        # Attachment button for sending files/images
        self.attachment_button = QPushButton()
        self.attachment_button.setFixedSize(46, 46)
        self.attachment_button.setToolTip("Đính kèm file/ảnh")
        self.attachment_button.setStyleSheet("""
            QPushButton {
                background-color: #fafeff;
                color: white;
                border-radius: 23px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eceeef;
            }
            QPushButton:pressed {
                background-color: #eceeef;
            }
        """)
        
        # Tạo biểu tượng đính kèm
        attachment_icon = QPixmap(24, 24)
        attachment_icon.fill(Qt.transparent)
        
        # Kiểm tra xem có biểu tượng đính kèm có sẵn không
        attachment_icon_path = os.path.join(self.icons_dir, 'attachment.png')
        
        if os.path.exists(attachment_icon_path):
            # Sử dụng biểu tượng từ file nếu tồn tại
            attachment_icon = QPixmap(attachment_icon_path).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logger.info(f"Sử dụng biểu tượng đính kèm từ file: {attachment_icon_path}")
        else:
            # Vẽ biểu tượng đính kèm đẹp hơn
            logger.warning(f"Không tìm thấy file biểu tượng đính kèm tại: {attachment_icon_path}. Tạo biểu tượng mặc định.")
            
            painter = QPainter(attachment_icon)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Tạo gradient cho biểu tượng
            gradient = QLinearGradient(0, 0, 24, 24)
            gradient.setColorAt(0, QColor("#5d87ff"))
            gradient.setColorAt(1, QColor("#367bf0"))
            
            # Vẽ nền tròn
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(2, 2, 20, 20)
            
            # Vẽ biểu tượng kẹp giấy
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            
            # Vẽ biểu tượng đính kèm đơn giản (paper clip)
            path = QPainterPath()
            path.moveTo(9, 13)
            path.arcTo(9, 7, 4, 4, 180, -90)
            path.lineTo(15, 7)
            path.arcTo(13, 7, 4, 4, 90, -90)
            path.lineTo(17, 14)
            path.arcTo(13, 14, 4, 4, 0, -90)
            path.lineTo(10, 18)
            path.arcTo(9, 14, 4, 4, 270, -90)
            
            painter.drawPath(path)
            painter.end()
        
        self.attachment_button.setIcon(QIcon(attachment_icon))
        self.attachment_button.setIconSize(QSize(22, 22))
        self.attachment_button.clicked.connect(self.show_attachment_dialog)
        
        # Voice input button with circular design
        self.voice_button = QPushButton()
        self.voice_button.setFixedSize(46, 46)  # Slightly larger buttons
        self.voice_button.setToolTip("Nhấn để nói")
        self.voice_button.setStyleSheet("""
            QPushButton {
                background-color: #fafeff;
                color: white;
                border-radius: 23px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eceeef;
            }
            QPushButton:pressed {
                background-color: #eceeef;
            }
        """)
        
        # Thay thế biểu tượng mic được vẽ bằng QPainter bằng file ảnh
        mic_icon_path = os.path.join(self.icons_dir, 'mic.png')
        if os.path.exists(mic_icon_path):
            # Sử dụng biểu tượng mic từ file
            self.voice_button.setIcon(QIcon(mic_icon_path))
            logger.info(f"Sử dụng biểu tượng mic từ file: {mic_icon_path}") 
        else:
            # Fallback - vẽ biểu tượng mic nếu file không tồn tại
            logger.warning(f"Không tìm thấy file biểu tượng mic tại: {mic_icon_path}")
            mic_icon = QPixmap(24, 24)
            mic_icon.fill(Qt.transparent)
            
            painter = QPainter(mic_icon)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.white)
            painter.setBrush(Qt.white)
            
            # Draw a simple microphone
            painter.drawRoundedRect(9, 5, 6, 10, 2, 2)  # Mic top
            painter.drawRect(11, 15, 2, 4)  # Mic stand
            painter.drawRoundedRect(7, 18, 10, 2, 1, 1)  # Mic base
            painter.end()
            
            self.voice_button.setIcon(QIcon(mic_icon))
        
        self.voice_button.setIconSize(QSize(22, 22))
        self.voice_button.clicked.connect(self.toggle_listening)
        
        # Send button with circular design
        self.send_button = QPushButton()
        self.send_button.setFixedSize(46, 46)  # Slightly larger buttons
        self.send_button.setToolTip("Gửi tin nhắn")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #fafeff;
                color: white;
                border-radius: 23px;
            }
            QPushButton:hover {
                background-color: #eceeef;
            }
            QPushButton:pressed {
                background-color: #eceeef;
            }
        """)
        
        # Thay thế biểu tượng send được vẽ bằng QPainter bằng file ảnh
        send_icon_path = os.path.join(self.icons_dir, 'send.png')
        if os.path.exists(send_icon_path):
            # Sử dụng biểu tượng send từ file
            self.send_button.setIcon(QIcon(send_icon_path))
            logger.info(f"Sử dụng biểu tượng send từ file: {send_icon_path}")
        else:
            # Fallback - vẽ biểu tượng send nếu file không tồn tại
            logger.warning(f"Không tìm thấy file biểu tượng send tại: {send_icon_path}")
            send_icon = QPixmap(24, 24)
            send_icon.fill(Qt.transparent)
            
            painter = QPainter(send_icon)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.white)
            painter.setBrush(Qt.white)
            
            # Draw a paper airplane
            points = [QPoint(4, 12), QPoint(20, 4), QPoint(12, 12), QPoint(20, 20)]
            painter.drawPolygon(points)
            painter.end()
            
            self.send_button.setIcon(QIcon(send_icon))
        
        self.send_button.setIconSize(QSize(22, 22))
        self.send_button.clicked.connect(self.send_message)
        
        # Assemble input area
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.attachment_button)
        input_layout.addWidget(self.voice_button)
        input_layout.addWidget(self.send_button)
        
        # Add shadow effect to input container
        input_shadow = self.create_shadow_effect(blur_radius=8, offset=1)
        input_container.setGraphicsEffect(input_shadow)
        
        layout.addWidget(input_container)
        
        # Status and control bar with modern styling
        self.status_container = QWidget()
        self.status_container.setObjectName("statusContainer")
        self.status_container.setStyleSheet("""
            QWidget#statusContainer {
                background-color: transparent;
            }
        """)
        
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(10, 10, 10, 5)
        status_layout.setSpacing(15)
        
        # Status indicator dot
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(8, 8)
        self.status_indicator.setStyleSheet("""
            background-color: #28A745;
            border-radius: 4px;
        """)
        
        # Status label with modern styling
        self.status_label = QLabel("Sẵn sàng hỗ trợ bạn")
        self.status_label.setStyleSheet("""
            color: #6C757D;
            font-size: 13px;
            font-weight: 500;
        """)
        
        # Create a container for the status elements
        status_elements = QWidget()
        status_elements_layout = QHBoxLayout(status_elements)
        status_elements_layout.setContentsMargins(0, 0, 0, 0)
        status_elements_layout.setSpacing(8)
        status_elements_layout.addWidget(self.status_indicator)
        status_elements_layout.addWidget(self.status_label)
        
        # Clear chat button with modern styling
        self.clear_button = QPushButton("Làm mới")
        self.clear_button.setFixedSize(100, 36)
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #26b9c2;
                color: white;
                border: 1px solid #CED4DA;
                border-radius: 18px;
                padding: 6px 15px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d858c;
                color: white;
            }
            QPushButton:pressed {
                background-color: #23858c;
            }
        """)
        self.clear_button.clicked.connect(self.clear_chat)
        
        # Add Stop button for stopping voice response
        self.stop_button = QPushButton("Dừng")
        self.stop_button.setFixedSize(100, 36)
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: 1px solid #C82333;
                border-radius: 18px;
                padding: 6px 15px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #C82333;
                color: white;
            }
            QPushButton:pressed {
                background-color: #BD2130;
            }
        """)
        self.stop_button.clicked.connect(self.stop_speech)
        
        status_layout.addWidget(status_elements)
        status_layout.addStretch()
        status_layout.addWidget(self.stop_button)
        status_layout.addWidget(self.clear_button)
        
        layout.addWidget(self.status_container)
        
        # Add default welcome message
        self._add_message_to_chat("MIS Assistant", "Xin chào! Tôi là MIS Assistant. Bạn có thể hỏi tôi thông tin về thời tiết, thời gian, hoặc bất kỳ điều gì bạn muốn biết.\n\nNhấn vào nút microphone để kích hoạt chế độ nhận diện giọng nói.")
    
    def create_shadow_effect(self, color=QColor(0, 0, 0, 35), blur_radius=15, offset=0):
        """Create a shadow effect for widgets."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setColor(color)
        shadow.setOffset(offset)
        return shadow

    def _change_speech_speed(self):
        """Change the speech playback speed based on the selected button."""
        selected_button = self.speed_button_group.checkedButton()
        if selected_button:
            speed_value = selected_button.property("speed_value")
            if self.speech_processor:
                self.speech_processor.set_playback_speed(speed_value)
                logger.info(f"Speech playback speed changed to {speed_value}x")

    def send_message(self):
        """Send the user's message to the AI assistant."""
        # Get the text from the input field
        query = self.input_field.text().strip()
        
        # Kiểm tra nếu không có văn bản và không có hình ảnh
        if not query and not self.selected_image['path']:
            return
        
        # Xử lý trường hợp có hình ảnh đính kèm
        has_image = self.selected_image['path'] is not None
        
        # Nếu người dùng không nhập gì và chỉ gửi ảnh, sử dụng tin nhắn mặc định
        if not query and has_image:
            query = "Hãy phân tích hình ảnh này giúp tôi."
            
        # Clear the input field
        self.input_field.clear()
          # Disable input while processing
        self._set_processing_state(True)
        
        if self.hardware_interface.is_connected():
            try:
                self.hardware_interface.display_message("Processing...")
            except Exception as e:
                logger.error(f"Error setting hardware processing state: {str(e)}")
        
        # Xử lý khác nhau cho trường hợp có hình ảnh và không có hình ảnh
        if has_image:
            # Lấy thông tin hình ảnh đã chọn
            image_data = self.selected_image['image_data']
            file_name = self.selected_image['name']
            
            # Hiển thị tin nhắn với hình ảnh trong chatbox
            message = f"[Hình ảnh: {file_name}] {query}"
            self._add_message_to_chat_with_image("User", message, image_data, file_name)
              # Gửi hình ảnh và tin nhắn đến AI trong luồng riêng
            self.query_thread = QueryWorkerWithImage(
                self.gemini_client,
                query,
                image_data,
                file_name
            )
            self.query_thread.response_ready.connect(self._handle_response_with_image)
            self.query_thread.error_occurred.connect(self._handle_error)
            self.query_thread.start()
            
            # Reset selected image
            self.selected_image = {'path': None, 'name': None, 'image_data': None}
            
            # Khôi phục placeholder mặc định
            self.input_field.setPlaceholderText("Nhập câu hỏi hoặc yêu cầu của bạn...")
            
            # Reset style của nút đính kèm
            self.attachment_button.setStyleSheet("""
                QPushButton {
                    background-color: #fafeff;
                    color: white;
                    border-radius: 23px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #eceeef;
                }
                QPushButton:pressed {
                    background-color: #eceeef;
                }
            """)
        else:
            # Xử lý tin nhắn văn bản thông thường
            # Add the query to the chat history
            self._add_message_to_chat("User", query)
              # Process in a separate thread to keep UI responsive
            self.query_thread = QueryWorker(self.gemini_client, query)
            self.query_thread.response_ready.connect(self._handle_text_response)
            self.query_thread.error_occurred.connect(self._handle_error)
            self.query_thread.start()
    
    def _handle_text_response(self, sender, response):
        """Handle the AI assistant's text-only response."""
        self._handle_response_common(sender, response)
    
    def _handle_response_with_image(self, sender, response, image_data, file_name):
        """Handle the AI assistant's response to a query with image."""
        self._handle_response_common(sender, response)
    
    def _handle_response_common(self, sender, response):
        """Common handling for AI assistant responses."""
        # Clear any previous prepared speech to avoid playing the wrong audio
        if self.speech_processor:
            self.speech_processor.prepared_audio_file = None
            
        # Chuẩn bị âm thanh trước khi hiển thị văn bản để quá trình chạy song song
        if config.ENABLE_VOICE_RESPONSE:
            self.speech_processor.prepare_speech(response)
        
        # Thiết lập flag để theo dõi khi nào tin nhắn được hiển thị đầy đủ
        self.message_displayed = False
          # Add the response to the chat history
        self._add_message_to_chat(sender, response)
        
        # Notify hardware that we're responding and display the response text
        if self.hardware_interface.is_connected():
            try:
                # Display first part of response on LCD
                display_text = response[:40] + "..." if len(response) > 40 else response
                self.hardware_interface.display_message(display_text)
                self.hardware_interface.set_responding_mode()
            except Exception as e:
                logger.error(f"Error updating hardware with response: {str(e)}")
        
        # Force the UI to update immediately and process all pending events
        QApplication.processEvents()
        
        # Force scroll to the most recent message immediately
        self._scroll_to_bottom()
        QApplication.processEvents()
        
        # Đánh dấu tin nhắn đã được hiển thị
        self.message_displayed = True
        
        # Start speech processing in a separate thread to avoid blocking the UI
        if config.ENABLE_VOICE_RESPONSE:
            speech_thread = threading.Thread(
                target=self._process_speech_response,
                args=(response,),
                daemon=True
            )
            speech_thread.start()
        else:
            # Mark as finished immediately if speech is disabled
            if self.hardware_interface.is_connected():
                self.hardware_interface.set_finished_mode()
        
        # Enable input after response is displayed - don't wait for speech
        self._set_processing_state(False)
    
    def _process_speech_response(self, response):
        """Process the speech response in a separate thread."""
        try:
            # Đợi tin nhắn hiển thị hoàn tất trước khi bắt đầu phát âm thanh
            start_time = time.time()
            max_wait = 1  # Giảm từ 2 xuống 1 giây
            
            while not hasattr(self, 'message_displayed') or not self.message_displayed:
                # Đợi tin nhắn được hiển thị đầy đủ
                time.sleep(0.02)  # Giảm từ 0.05 xuống 0.02
                if time.time() - start_time > max_wait:
                    logger.warning("Timed out waiting for message display")
                    break
            
            # Phát âm thanh đã được chuẩn bị trước
            logger.info("Tin nhắn đã hiển thị, bắt đầu phát âm thanh")
            if self.speech_processor.prepared_audio_file:
                # Có file âm thanh được chuẩn bị sẵn, phát nó
                self.speech_processor.play_prepared_speech()
            else:
                # Không có file được chuẩn bị (hiếm khi xảy ra), tạo mới
                logger.warning("No prepared audio found, generating new one")
                self.speech_processor.text_to_speech(response)
            
            # Wait for speech to finish
            self._wait_for_speech_completion()
        except Exception as e:
            logger.error(f"Error processing speech response: {str(e)}")
            # Ensure hardware is in finished mode even if there's an error
            if self.hardware_interface.is_connected():
                self.hardware_interface.set_finished_mode()
    
    def _wait_for_speech_completion(self):
        """Wait for speech to complete and emit signal when done. Runs in a thread."""
        try:
            logger.info("Waiting for speech to complete...")

            start_time = time.time()
            speaking_confirmed = False
            max_confirm_time = 1  # Giảm từ 3 xuống 1 giây

            while time.time() - start_time < max_confirm_time:
                if self.speech_processor.is_currently_speaking():
                    speaking_confirmed = True
                    logger.info("Speech confirmed to have started")
                    break
                time.sleep(0.1)  # Giảm từ 0.2 xuống 0.1

            if not speaking_confirmed:
                logger.warning("Speech may not have started properly, continuing anyway")

            # Wait until speech is fully complete with periodic checks and better error handling
            max_wait = time.time() + 120  # Giảm từ 180 xuống 120 giây
            while time.time() < max_wait:
                if not self.speech_processor.is_currently_speaking():
                    logger.info("Speech processor reports speaking complete")
                    break
                time.sleep(0.2)  # Giảm từ 0.5 xuống 0.2

            # Ensure we're truly done and pygame is idle
            if pygame and pygame.mixer.get_init():
                while pygame.mixer.music.get_busy():
                    logger.info("Waiting for pygame to finish playing...")
                    time.sleep(0.2)  # Giảm từ 0.5 xuống 0.2

            # Important: small delay before updating hardware state to ensure stability
            time.sleep(0.2)

            # Update hardware state - with error protection
            try:
                if self.hardware_interface.is_connected():
                    self.hardware_interface.set_finished_mode()
                    logger.info("Hardware finished mode set successfully")
            except Exception as e:
                logger.error(f"Error setting hardware finished mode: {str(e)}")

            # Important: small delay before emitting signal to prevent race conditions
            time.sleep(0.2)
            
            # Emit completion signal in a safer way
            logger.info("Emitting speech completion signal")
            self.speech_finished_signal.emit()

        except Exception as e:
            logger.error(f"Error in speech completion thread: {str(e)}")
            # Emit signal even on error so the UI doesn't get stuck
            try:
                self.speech_finished_signal.emit()
            except Exception:
                logger.error("Could not emit speech finished signal after error")
    
    def _add_message_to_chat(self, sender, message):
        """Add a message to the chat history with the messenger-like UI."""
        # Get appropriate colors for the sender
        if sender == "User":
            bubble_color = config.CHAT_USER_BUBBLE_COLOR
            text_color = config.CHAT_USER_TEXT_COLOR
            avatar_path = self.user_avatar_path
        elif sender == "MIS Assistant":
            bubble_color = config.CHAT_ASSISTANT_BUBBLE_COLOR
            text_color = config.CHAT_ASSISTANT_TEXT_COLOR
            avatar_path = self.assistant_avatar_path
        else:
            # System messages use a light gray
            bubble_color = "#F1F1F1"
            text_color = "#666666"
            avatar_path = None
        
        # Create a chat bubble for the message
        chat_bubble = ChatBubbleWidget(message, sender, bubble_color, text_color, avatar_path)
        
        # Remove the stretch from the bottom
        self.messages_layout.removeItem(self.messages_layout.itemAt(self.messages_layout.count() - 1))
        
        # Add new bubble
        self.messages_layout.addWidget(chat_bubble)
        
        # Add stretch back to push messages to the top
        self.messages_layout.addStretch()
        
        # Scroll to the bottom to show the latest message
        QTimer.singleShot(100, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        """Scroll the chat to the bottom to show the latest messages."""
        # Using a more reliable approach to ensure scrolling works consistently
        try:
            vertical_scrollbar = self.scroll_area.verticalScrollBar()
            # Force layout update to ensure correct scroll maximum
            self.messages_container.layout().update()
            QApplication.processEvents()
            # Set to maximum value to scroll to bottom
            vertical_scrollbar.setValue(vertical_scrollbar.maximum())
            # For additional reliability, schedule another scroll after a short delay
            QTimer.singleShot(50, lambda: vertical_scrollbar.setValue(vertical_scrollbar.maximum()))
        except Exception as e:
            logger.error(f"Error scrolling to bottom: {str(e)}")
    
    def _set_processing_state(self, is_processing):
        """Update UI elements based on processing state."""
        self.is_processing = is_processing
        self.input_field.setEnabled(not is_processing)
        self.send_button.setEnabled(not is_processing)
        self.voice_button.setEnabled(not is_processing)
        self.attachment_button.setEnabled(not is_processing)
        
        if is_processing:
            # Change to processing state (orange indicator)
            self.status_label.setText("Đang xử lý...")
            self.status_label.setStyleSheet("color: #FFA500; font-size: 13px; font-weight: 500;")
            self.status_indicator.setStyleSheet("background-color: #FFA500; border-radius: 4px;")
        else:
            # Change to ready state (green indicator)
            self.status_label.setText("Sẵn sàng hỗ trợ bạn")
            self.status_label.setStyleSheet("color: #6C757D; font-size: 13px; font-weight: 500;")
            self.status_indicator.setStyleSheet("background-color: #28A745; border-radius: 4px;")
    
    def toggle_listening(self):
        """Toggle voice input listening mode."""
        # If we're speaking or already in a processing state, don't allow activation
        if self.is_processing or self.speech_processor.is_currently_speaking():
            logger.info("Ignoring microphone activation - already processing or speaking")
            return

        # If speech processor reports listening but UI isn't reflecting it,
        # the state might be stuck - force reset it
        if self.speech_processor.is_currently_listening():
            logger.info("Detected potentially stuck listening state - forcing reset")
            self.speech_processor.set_listening_status(False)
            
        # Immediate UI feedback
        self.status_label.setText("Đang lắng nghe...")
        self.status_label.setStyleSheet("color: #DC3545; font-size: 13px; font-weight: 500;")
        self.status_indicator.setStyleSheet("background-color: #DC3545; border-radius: 4px;")
        
        # Update button style
        self.voice_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border-radius: 23px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
            QPushButton:pressed {
                background-color: #BD2130;
            }
        """)
        
        # Force immediate UI update
        QApplication.processEvents()
        
        # Play beep sound asynchronously
        self._play_beep_sound()
        
        # Disable input while listening
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
          # Notify hardware that we're listening
        if self.hardware_interface.is_connected():
            try:
                self.hardware_interface.set_listening_mode()
            except Exception as e:
                logger.error(f"Error setting hardware listening mode: {str(e)}")
        
        # Start speech recognition in a separate thread
        recognition_thread = threading.Thread(
            target=self._run_speech_recognition,
            daemon=True
        )
        recognition_thread.start()
    
    def _run_speech_recognition(self):
        """Run speech recognition in a separate thread."""
        try:
            logger.info("Starting speech recognition")

            # Define a callback function that properly handles thread-safe UI updates
            def handle_result(text):
                logger.info(f"Speech recognition result: {text if text else 'No text detected'}")
                
                # Only emit signals from the background thread - don't directly manipulate UI
                if not text:
                    self.ui_update_signal.emit("System", "Không nhận được giọng nói hoặc không thể nhận dạng. Vui lòng thử lại.")
                else:
                    # Send recognized text to main thread for processing
                    self.speech_result_signal.emit(text)
                
                # Update status in thread-safe way
                self.status_update_signal.emit("Sẵn sàng hỗ trợ bạn")
                self.button_style_signal.emit("")  # Reset mic button style

            # Start speech recognition with our callback
            self.speech_processor.speech_to_text(callback_function=handle_result, timeout=5)
            
        except Exception as e:
            logger.error(f"Error in speech recognition thread: {str(e)}")
            # Update UI in thread-safe way
            self.ui_update_signal.emit("System", f"Lỗi khi nhận dạng giọng nói: {str(e)}")
            self.status_update_signal.emit("Sẵn sàng hỗ trợ bạn")
    
    def clear_chat(self):
        """Clear the chat history and stop any ongoing response."""
        # Stop ongoing query
        if self.is_processing and self.query_thread and hasattr(self.query_thread, 'gemini_client'):
            self.query_thread.gemini_client.stop_response_generation()
            if config.ENABLE_VOICE_RESPONSE and self.speech_processor:
                self.speech_processor.stop_speaking()
            self._set_processing_state(False)
            if self.hardware_interface.is_connected():
                self.hardware_interface.set_finished_mode()
        
        # Clear messages
        for i in reversed(range(self.messages_layout.count())):
            item = self.messages_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Add stretch back
        self.messages_layout.addStretch()
        
        # Xóa ảnh đính kèm đang chờ nếu có
        if self.selected_image['path']:
            self.selected_image = {'path': None, 'name': None, 'image_data': None}
            # Khôi phục placeholder mặc định
            self.input_field.setPlaceholderText("Nhập câu hỏi hoặc yêu cầu của bạn...")
            # Khôi phục trạng thái nút đính kèm
            self.attachment_button.setStyleSheet("""
                QPushButton {
                    background-color: #fafeff;
                    color: white;
                    border-radius: 23px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #eceeef;
                }
                QPushButton:pressed {
                    background-color: #eceeef;
                }
            """)
        
        # Reset status to ready state
        self.status_label.setText("Sẵn sàng hỗ trợ bạn")
        self.status_label.setStyleSheet("color: #6C757D; font-size: 13px; font-weight: 500;")
        self.status_indicator.setStyleSheet("background-color: #28A745; border-radius: 4px;")
        
        # Reset voice button style
        self.voice_button.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border-radius: 23px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1E7E34;
            }
        """)
        
        # Enable input controls
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.voice_button.setEnabled(True)
        
        # Reset conversation
        if self.gemini_client:
            reset_message = self.gemini_client.reset_conversation()
            self._add_message_to_chat(
                "MIS Assistant", 
                "Cuộc trò chuyện đã được làm mới.\n\nTôi là MIS Assistant. Bạn có thể hỏi tôi bất kỳ điều gì."
            )
    
    def stop_speech(self):
        """Stop the assistant's voice response."""
        if config.ENABLE_VOICE_RESPONSE and self.speech_processor:
            logger.info("Stopping speech playback manually")
            self.speech_processor.stop_speaking()
            
            # Update UI state
            self.status_label.setText("Sẵn sàng hỗ trợ bạn")
            self.status_label.setStyleSheet("color: #6C757D; font-size: 13px; font-weight: 500;")
            self.status_indicator.setStyleSheet("background-color: #28A745; border-radius: 4px;")
            
            # Update hardware state
            if self.hardware_interface.is_connected():
                self.hardware_interface.set_finished_mode()
                
            # Log the action
            logger.info("Speech playback stopped by user")
    
    def _play_beep_sound(self):
        """Play a beep sound."""
        if pygame and os.path.exists(self.beep_sound_path):
            try:
                pygame.mixer.music.load(self.beep_sound_path)
                pygame.mixer.music.play()
            except Exception as e:
                logger.error(f"Error playing beep sound: {str(e)}")
    
    def _play_completion_sound(self):
        """Play a completion sound to signal the end of the assistant's response."""
        if pygame and os.path.exists(self.completion_sound_path):
            try:
                pygame.mixer.music.load(self.completion_sound_path)
                pygame.mixer.music.play()
                logger.info("Playing completion sound to signal end of response")
            except Exception as e:
                logger.error(f"Error playing completion sound: {str(e)}")
        else:
            logger.warning(f"Completion sound file not found at: {self.completion_sound_path}")
    
    def _on_speech_finished(self):
        """Slot for speech finished signal. Called when speech playback is complete."""
        logger.info("Speech playback finished completely")
        
        # Double-check speech state before updating hardware state
        is_speaking = self.speech_processor.is_currently_speaking()
        is_playing = pygame and pygame.mixer.music.get_busy()
        
        if is_speaking or is_playing:
            logger.warning(f"Speech not fully complete (is_speaking={is_speaking}, is_playing={is_playing}), scheduling recheck")
            QTimer.singleShot(500, self._check_speech_completed)
            return
        
        # Play completion sound to signal the end of the assistant's response
        self._play_completion_sound()
        
        # Check if there's pending music to play after speech is done
        if hasattr(self.gemini_client, 'multimedia_service') and self.gemini_client.multimedia_service:
            multimedia_service = self.gemini_client.multimedia_service
            if hasattr(multimedia_service, 'pending_playback_file') and multimedia_service.pending_playback_file:
                logger.info("Playing pending audio after speech completed")
                # Give a small delay to avoid audio overlap
                QTimer.singleShot(300, multimedia_service.play_pending_audio)
        
        # Update hardware state
        if self.hardware_interface.is_connected():
            self.hardware_interface.set_finished_mode()
    
    def _check_speech_completed(self):
        """Kiểm tra xem speech đã thực sự kết thúc chưa (chạy trong main thread)"""
        # Không bật mic nếu vẫn đang xử lý
        if self.is_processing:
            logger.warning("Still in processing state, not updating hardware state")
            return
            
        # Kiểm tra trạng thái speaking và pygame
        still_speaking = self.speech_processor.is_currently_speaking()
        still_playing = False
        try:
            if pygame and pygame.mixer.get_init():
                still_playing = pygame.mixer.music.get_busy()
        except Exception as e:
            logger.error(f"Error checking pygame status: {str(e)}")
            
        # Log trạng thái hiện tại
        logger.info(f"Speech status check: is_speaking={still_speaking}, is_playing={still_playing}")
        
        if not still_speaking and not still_playing:
            # Speech đã kết thúc hoàn toàn, cập nhật trạng thái hardware
            if self.hardware_interface.is_connected():
                self.hardware_interface.set_finished_mode()
            logger.info("All checks passed - speech completed")
            
            # Play completion sound to signal the end of the assistant's response
            self._play_completion_sound()
        else:
            # Vẫn đang nói, lên lịch kiểm tra lại sau 500ms
            logger.info("Speech still in progress, checking again in 500ms")
            QTimer.singleShot(500, self._check_speech_completed)
    
    def _on_speech_result(self, text):
        """Slot for speech result signal. Called when speech recognition completes."""
        if text:
            # Set the recognized text in the input field
            self.input_field.setText(text)
            
            # Re-enable controls before sending message
            self.input_field.setEnabled(True)
            self.send_button.setEnabled(True)
            
            # Send the message with a slight delay to ensure UI is ready
            QTimer.singleShot(100, self.send_message)
            
            # Update UI state
            self.status_label.setText("Sẵn sàng hỗ trợ bạn")
            self.status_indicator.setStyleSheet("background-color: #28A745; border-radius: 4px;")
    
    def _handle_error(self, error_message):
        """Handle errors from query worker threads."""
        logger.error(f"Error in query processing: {error_message}")
        
        # Add error message to chat
        self._add_message_to_chat("System", f"Xin lỗi, đã xảy ra lỗi: {error_message}")
        
        # Reset UI state
        self._set_processing_state(False)
        
        # Update hardware state if connected
        if self.hardware_interface.is_connected():
            self.hardware_interface.set_finished_mode()
            
        # Reset status
        self.status_label.setText("Sẵn sàng hỗ trợ bạn")
        self.status_label.setStyleSheet("color: #6C757D; font-size: 13px; font-weight: 500;")
        self.status_indicator.setStyleSheet("background-color: #28A745; border-radius: 4px;")
    
    def _update_status_label(self, status):
        """Slot for updating the status label in a thread-safe way."""
        self.status_label.setText(status)
        if "lắng nghe" in status.lower():
            self.status_label.setStyleSheet("color: #DC3545; font-size: 13px; font-weight: 500;")
            self.status_indicator.setStyleSheet("background-color: #DC3545; border-radius: 4px;")
        elif "xử lý" in status.lower():
            self.status_label.setStyleSheet("color: #FFA500; font-size: 13px; font-weight: 500;")
            self.status_indicator.setStyleSheet("background-color: #FFA500; border-radius: 4px;")
        else:
            self.status_label.setStyleSheet("color: #6C757D; font-size: 13px; font-weight: 500;")
            self.status_indicator.setStyleSheet("background-color: #28A745; border-radius: 4px;")
    
    def _update_voice_button_style(self, style):
        """Slot for updating the voice button style in a thread-safe way."""
        if style:
            self.voice_button.setStyleSheet(style)
        else:
            self.voice_button.setStyleSheet("""
                QPushButton {
                    background-color: #28A745;
                    color: white;
                    border-radius: 23px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1E7E34;
                }
            """)
    
    def _on_hardware_button_pressed(self, data=None):
        """Callback for hardware button press to activate microphone."""
        logger.info("Hardware button pressed - activating microphone")
        
        # Additional protection: check if we just processed a button event recently
        current_time = time.time()
        if not hasattr(self, '_last_hardware_activation_time'):
            self._last_hardware_activation_time = 0
            
        time_since_last_activation = current_time - self._last_hardware_activation_time
        
        # Ignore if we just processed a hardware activation within 1 second
        if time_since_last_activation < 1.0:
            logger.info(f"Ignoring duplicate hardware activation (time since last: {time_since_last_activation:.3f}s)")
            return
            
        # Update last activation time
        self._last_hardware_activation_time = current_time
        
        # Use QMetaObject to invoke toggle_listening in the main thread
        # This is more reliable than direct calls between threads
        QMetaObject.invokeMethod(self, "_activate_hardware_microphone",
                                Qt.QueuedConnection)
    
    @pyqtSlot()
    def _activate_hardware_microphone(self):
        """Thread-safe implementation of microphone activation from hardware button."""
        try:
            logger.info("Hardware button press received - checking state")
            
            # Check if we're already processing
            if self.is_processing:
                logger.info("Ignoring button press - already processing")
                return
                
            # Check if we're currently speaking
            if self.speech_processor.is_currently_speaking():
                logger.info("Ignoring button press - currently speaking")
                return
            
            # If we're already listening, stop current session
            if self.speech_processor.is_currently_listening():
                logger.info("Already listening - stopping current session")
                self.speech_processor.set_listening_status(False)
                # Wait for clean state
                time.sleep(0.3)
            
            # Update UI immediately
            self.status_label.setText("Đang lắng nghe...")
            self.status_label.setStyleSheet("color: #DC3545; font-size: 13px; font-weight: 500;")
            
            # Give UI time to update
            QApplication.processEvents()
            
            # Small delay to ensure clean state
            time.sleep(0.2)
                
            # Activate microphone with a slight delay to ensure UI is updated
            logger.info("Trực tiếp kích hoạt microphone từ nút nhấn phần cứng")
            
            # Use a single-shot timer to ensure UI updates are processed
            QTimer.singleShot(100, lambda: self._safe_toggle_listening())
            
        except Exception as e:
            logger.error(f"Lỗi khi kích hoạt microphone: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _safe_toggle_listening(self):
        """Safely toggle listening state with additional checks."""
        try:
            # Double check state before toggling
            if not self.is_processing and not self.speech_processor.is_currently_speaking():
                self.toggle_listening()
        except Exception as e:
            logger.error(f"Error in safe toggle listening: {str(e)}")
    
    def _on_hotword_detected(self):
        """Callback for hotword detection to activate microphone."""
        logger.info("Hotword detected - activating microphone")
        self.toggle_listening()
        
    def _on_speech_processor_started(self):
        """Callback when speech processor starts speaking - update hardware to responding mode."""
        try:
            if self.hardware_interface:
                self.hardware_interface.set_responding_mode()
                logger.info("Hardware updated to responding mode - speech started")
        except Exception as e:
            logger.error(f"Error updating hardware to responding mode: {str(e)}")
    
    def _on_speech_processor_finished(self):
        """Callback when speech processor finishes speaking - update hardware to finished mode."""
        try:
            if self.hardware_interface:
                self.hardware_interface.set_finished_mode()
                logger.info("Hardware updated to finished mode - speech finished")
        except Exception as e:
            logger.error(f"Error updating hardware to finished mode: {str(e)}")
        
    def show_attachment_dialog(self):
        """Show dialog to select file or image attachment."""
        # Kiểm tra xem có đang trong quá trình xử lý không
        if self.is_processing:
            logger.info("Ignoring attachment request - already processing")
            return
            
        # Kiểm tra nếu đã có ảnh được chọn 
        if self.selected_image['path']:
            # Hiển thị tùy chọn xóa ảnh đã chọn
            self._show_attachment_options_menu()
            return
            
        # Tạo hộp thoại chọn tệp
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Chọn tệp đính kèm")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Tất cả tệp (*.*);;Hình ảnh (*.png *.jpg *.jpeg *.gif *.bmp)")
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self.handle_file_attachment(file_path)
                
    def _show_attachment_options_menu(self):
        """Hiển thị menu tùy chọn cho ảnh đính kèm."""
        options_menu = QMenu(self)
        remove_action = QAction(f"Xóa ảnh: {self.selected_image['name']}", self)
        remove_action.triggered.connect(self._remove_attached_image)
        options_menu.addAction(remove_action)
        
        # Hiển thị menu tại vị trí nút đính kèm
        options_menu.exec_(self.attachment_button.mapToGlobal(self.attachment_button.rect().bottomLeft()))
        
    def _remove_attached_image(self):
        """Xóa ảnh đã đính kèm."""
        file_name = self.selected_image['name']
        self.selected_image = {'path': None, 'name': None, 'image_data': None}
        
        # Khôi phục placeholder mặc định
        self.input_field.setPlaceholderText("Nhập câu hỏi hoặc yêu cầu của bạn...")
        
        # Khôi phục trạng thái nút đính kèm
        self.attachment_button.setStyleSheet("""
            QPushButton {
                background-color: #fafeff;
                color: white;
                border-radius: 23px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eceeef;
            }
            QPushButton:pressed {
                background-color: #eceeef;
            }
        """)
        
        # Cập nhật trạng thái
        self.status_label.setText(f"Đã hủy đính kèm ảnh: {file_name}")
        self.status_label.setStyleSheet("color: #6C757D; font-size: 13px; font-weight: 500;")
        
        # Chuyển sang trạng thái sẵn sàng sau 2 giây
        QTimer.singleShot(2000, lambda: self._update_status_label("Sẵn sàng hỗ trợ bạn"))
    
    def handle_file_attachment(self, file_path):
        """Process the attached file based on its type."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return
            
        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Kiểm tra loại tệp
        if mime_type and mime_type.startswith('image/'):
            # Xử lý tệp hình ảnh - chỉ lưu trữ thông tin, không gửi ngay
            self._prepare_image_attachment(file_path, file_name)
            # Thông báo cho người dùng biết đã chọn hình ảnh
            self.status_label.setText(f"Đã chọn ảnh: {file_name}")
            self.status_label.setStyleSheet("color: #0d6efd; font-size: 13px; font-weight: 500;")
            # Tập trung vào ô input để người dùng nhập tin nhắn
            self.input_field.setFocus()
        else:
            # Hiển thị thông báo cho người dùng về tệp không phải hình ảnh
            self._add_message_to_chat("System", f"Hiện tại chỉ hỗ trợ đính kèm hình ảnh. Tệp '{file_name}' không phải là hình ảnh.")
            logger.info(f"Unsupported file type: {mime_type} for file {file_path}")
            
    def _prepare_image_attachment(self, image_path, file_name):
        """Xử lý và lưu trữ thông tin hình ảnh để gửi sau."""
        try:
            # Đọc dữ liệu hình ảnh
            image = QImage(image_path)
            if image.isNull():
                logger.error(f"Failed to load image: {image_path}")
                self._add_message_to_chat("System", f"Không thể tải hình ảnh '{file_name}'.")
                return
                
            # Tạo bản sao chất lượng phù hợp của hình ảnh
            max_dimension = 800  # Giới hạn kích thước hình ảnh
            if image.width() > max_dimension or image.height() > max_dimension:
                image = image.scaled(max_dimension, max_dimension, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Chuyển đổi hình ảnh sang base64
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.WriteOnly)
            
            # Lưu với định dạng phù hợp và chất lượng tốt
            image.save(buffer, "JPEG", 85)
            image_base64 = byte_array.toBase64().data()
            
            # Lưu thông tin hình ảnh để sử dụng sau
            self.selected_image = {
                'path': image_path,
                'name': file_name,
                'image_data': image_base64
            }
            
            # Cập nhật placeholder cho input field
            self.input_field.setPlaceholderText(f"Nhập tin nhắn kèm ảnh '{file_name}'...")
            
            # Thêm biểu tượng vào nút gửi để thông báo có hình ảnh đính kèm
            self.attachment_button.setStyleSheet("""
                QPushButton {
                    background-color: #0d6efd;
                    color: white;
                    border-radius: 23px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0b5ed7;
                }
                QPushButton:pressed {
                    background-color: #0a58ca;
                }
            """)
            
            logger.info(f"Image prepared for sending: {file_name}")
            
        except Exception as e:
            logger.error(f"Error preparing image attachment: {str(e)}")
            self._add_message_to_chat("System", f"Lỗi khi xử lý hình ảnh: {str(e)}")
            self.selected_image = {'path': None, 'name': None, 'image_data': None}
            
    def handle_image_attachment(self, image_path, file_name):
        """Phương thức tương thích ngược với mã cũ."""
        self._prepare_image_attachment(image_path, file_name)

    def _add_message_to_chat_with_image(self, sender, message, image_data, file_name=None):
        """Add a message with image attachment to the chat history."""
        # Get appropriate colors for the sender
        if sender == "User":
            bubble_color = config.CHAT_USER_BUBBLE_COLOR
            text_color = config.CHAT_USER_TEXT_COLOR
            avatar_path = self.user_avatar_path
        elif sender == "MIS Assistant":
            bubble_color = config.CHAT_ASSISTANT_BUBBLE_COLOR
            text_color = config.CHAT_ASSISTANT_TEXT_COLOR
            avatar_path = self.assistant_avatar_path
        else:
            # System messages use a light gray
            bubble_color = "#F1F1F1"
            text_color = "#666666"
            avatar_path = None
        
        # Create a chat bubble with image for the message
        chat_bubble = ChatBubbleWidgetWithImage(
            message, sender, bubble_color, text_color, 
            image_data=image_data, file_name=file_name,
            avatar_path=avatar_path
        )
        
        # Remove the stretch from the bottom
        self.messages_layout.removeItem(self.messages_layout.itemAt(self.messages_layout.count() - 1))
          # Add new bubble
        self.messages_layout.addWidget(chat_bubble)
        
        # Add stretch back to push messages to the top
        self.messages_layout.addStretch()
        
        # Scroll to the bottom to show the latest message
        QTimer.singleShot(100, self._scroll_to_bottom)

    def get_hotword_detection_status(self):
        """Get detailed hotword detection status for UI display"""
        if not self.speech_processor:
            return "Hotword detection not available"
            
        status = self.speech_processor.get_hotword_status()
        status_text = "🎤 Hotword Detection: "
        
        if not status["enabled"]:
            status_text += "Disabled"
        elif status.get("google_fallback") and status.get("google_listening"):
            status_text += f"Active (Google SR) - '{status['phrase']}'"
        else:
            status_text += "Initializing..."
            
        return status_text

    def show_hotword_status_dialog(self):
        """Show a dialog with detailed hotword detection status"""
        from PyQt5.QtWidgets import QMessageBox
        
        if not self.speech_processor:
            QMessageBox.information(self, "Hotword Status", "Speech processor not available")
            return
            
        status = self.speech_processor.get_hotword_status()
        dialog_text = "🎤 Hotword Detection Status\n\n"
        dialog_text += f"Enabled: {'Yes' if status['enabled'] else 'No'}\n"
        dialog_text += f"Phrase: '{status['phrase']}'\n"
        dialog_text += f"Google SR Fallback: {'Yes' if status.get('google_fallback') else 'No'}\n"
        if status.get('google_fallback'):
            dialog_text += f"Google SR Listening: {'Yes' if status.get('google_listening') else 'No'}\n"
        
        dialog_text += "\n💡 Tips:\n"
        dialog_text += "• Speak clearly and loudly for better recognition\n"
        dialog_text += "• Use the hotword 'ê cu' to activate voice commands\n"
        dialog_text += "• Make sure your microphone is working properly\n"
        
        QMessageBox.information(self, "Hotword Detection Status", dialog_text)
