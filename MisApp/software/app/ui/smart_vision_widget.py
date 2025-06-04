from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QFrame, QComboBox, QGridLayout, QMessageBox, 
                            QTabWidget, QCheckBox, QSlider, QGraphicsDropShadowEffect, 
                            QApplication, QFileDialog, QSplitter, QProgressBar, QTextBrowser)
from PyQt5.QtCore import (Qt, QSize, pyqtSignal, QTimer, QThread, QMutex, QRect, 
                         QMetaObject, Q_ARG, QUrl)
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap, QPainter, QImage, QDesktopServices

from ..utils import config, logger
from ..models.gemini_client import GeminiClient

# Import for launcher service
from ..models.launcher_service import LauncherService
# Import speech processor for TTS functionality
from ..models.speech_processor import SpeechProcessor

# Import OpenCV with error handling for exe environment
try:
    import cv2
    CV2_AVAILABLE = True
    # Test basic OpenCV functionality
    test_cap = cv2.VideoCapture()
    test_cap.release()
except ImportError as e:
    CV2_AVAILABLE = False
    logger.error(f"OpenCV not available: {e}")
except Exception as e:
    CV2_AVAILABLE = False
    logger.error(f"OpenCV initialization error: {e}")

import numpy as np
import time
import os
import threading
import io
import base64
from datetime import datetime

# Import để tạo QR code và xử lý mã QR
try:
    import qrcode
    from PIL import Image as PILImage
    from PIL import ImageEnhance, ImageFilter
    from PIL.ImageQt import ImageQt
    QR_CODE_AVAILABLE = True
except ImportError:
    QR_CODE_AVAILABLE = False
    logger.warning("QR code generation is not available. Install qrcode and pillow packages.")

# Thử import ZBar cho việc quét mã QR/barcode
try:
    from pyzbar.pyzbar import decode as zbar_decode
    # Check if ZBar actually works by testing a minimal decode
    test_img = np.zeros((10, 10), dtype=np.uint8)
    zbar_decode(test_img)  # Test if it can actually be used
    ZBAR_AVAILABLE = True
except ImportError:
    ZBAR_AVAILABLE = False
    logger.warning("ZBar not available. Install pyzbar package for QR code scanning.")
except Exception as e:
    ZBAR_AVAILABLE = False
    logger.warning(f"ZBar is installed but not functioning properly: {e}")
    logger.warning("This may be due to missing libzbar.dll - run fix_libzbar.py to fix")

class CameraThread(QThread):
    """Thread cho việc đọc camera để không block UI thread."""
    frame_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)  # Signal for error reporting
    
    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.running = False
        self.mutex = QMutex()
        self.capture = None
        self.mirror = True
        self.frame_processor = None
        self.current_frame = None  # Store the current frame
    
    def run(self):
        """Chạy thread camera."""
        if not CV2_AVAILABLE:
            self.error_occurred.emit("OpenCV không khả dụng. Vui lòng cài đặt opencv-python.")
            return
            
        self.mutex.lock()
        
        # Try to release any existing capture first
        if self.capture is not None:
            try:
                self.capture.release()
            except Exception:
                pass
                
        try:
            # Initialize camera with different backends for better compatibility
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            self.capture = None
            
            for backend in backends:
                try:
                    self.capture = cv2.VideoCapture(self.camera_id, backend)
                    if self.capture.isOpened():
                        logger.info(f"Camera opened successfully with backend: {backend}")
                        break
                    else:
                        self.capture.release()
                        self.capture = None
                except Exception as e:
                    logger.warning(f"Failed to open camera with backend {backend}: {e}")
                    continue
            
            # Check if any backend worked
            if self.capture is None or not self.capture.isOpened():
                self.error_occurred.emit(f"Không thể mở camera với ID {self.camera_id}")
                self.mutex.unlock()
                return
                
            # Set camera properties to improve performance
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.capture.set(cv2.CAP_PROP_FPS, 30)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize lag
            
            self.running = True
        except Exception as e:
            logger.error(f"Error initializing camera: {str(e)}")
            self.error_occurred.emit(f"Lỗi khởi tạo camera: {str(e)}")
            self.running = False
            
        self.mutex.unlock()
        
        # Camera reading loop
        while self.running:
            try:
                ret, frame = self.capture.read()
                if ret:
                    # Xử lý frame
                    if self.mirror:
                        frame = cv2.flip(frame, 1)  # Lật ngang để hiển thị mirror mode
                    
                    # Store the current frame
                    self.current_frame = frame.copy()
                    
                    # Áp dụng xử lý frame nếu được cung cấp
                    processed_frame = frame
                    if self.frame_processor is not None:
                        processed_frame = self.frame_processor(frame)
                    
                    self.frame_ready.emit(processed_frame)
                else:
                    # If frame reading fails, wait and try again
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.5)
                    
                    # Try to reconnect if camera disconnected
                    if not self.capture.isOpened():
                        logger.info("Attempting to reconnect to camera...")
                        self.capture.release()
                        self.capture = cv2.VideoCapture(self.camera_id)
                        
                time.sleep(0.03)  # ~30fps
            except Exception as e:
                logger.error(f"Lỗi khi đọc frame từ camera: {str(e)}")
                time.sleep(0.5)  # Tạm dừng trong trường hợp lỗi
    
    def stop(self):
        """Dừng thread camera."""
        self.mutex.lock()
        self.running = False
        if self.capture:
            self.capture.release()
            self.capture = None
        self.mutex.unlock()
        self.wait()
    
    def set_mirror(self, mirror):
        """Đặt chế độ gương."""
        self.mirror = mirror
    
    def set_processor(self, processor_func):
        """Đặt hàm xử lý frame."""
        self.frame_processor = processor_func

class SmartVisionWidget(QWidget):
    """Widget for smart vision analysis using webcam."""
    # Signal for analysis completion
    analysis_completed = pyqtSignal(str)  # Signal to update analysis result
    
    def __init__(self, gemini_client=None, speech_processor=None):
        super().__init__()
        
        # Kiểm tra OpenCV availability ngay khi khởi tạo
        if not CV2_AVAILABLE:
            logger.error("OpenCV not available - Smart Vision will be disabled")
        
        # Lưu tham chiếu đến Gemini client và SpeechProcessor
        self.gemini_client = gemini_client
        self.speech_processor = speech_processor
        
        # Create launcher service for handling links
        self.launcher_service = LauncherService()
        
        # Thiết lập trạng thái
        self.is_camera_running = False
        self.is_mirror_mode = True  # Chế độ gương mặc định
        self.is_capturing = False   # Đang trong quá trình chụp
        self.current_mode = "normal"  # Các chế độ: normal, text, document, qr
        self.captured_frame = None  # Frame đã chụp
        self.analysis_result = None # Kết quả phân tích
        self.contrast_level = 1.0   # Mức độ tương phản
        self.brightness_level = 1.0 # Mức độ sáng
        self.sharpness_level = 1.0  # Mức độ sắc nét
        self.qr_codes = []          # Danh sách mã QR được phát hiện
        self.qr_links = []          # Danh sách các link từ QR codes
        
        # Connect signal to slot
        self.analysis_completed.connect(self._update_analysis_result)
        
        # Thread camera
        self.camera_thread = None
        self.camera_id = 0
        
        # Khởi tạo UI
        self._setup_ui()
        
        # Tự động khởi động camera chỉ khi OpenCV khả dụng
        if CV2_AVAILABLE:
            self._start_camera()
        else:
            self._show_opencv_error()

    def _setup_ui(self):
        """Thiết lập giao diện người dùng."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Tiêu đề
        header_layout = QHBoxLayout()
        title_label = QLabel("Smart Vision Analyzer")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Combobox chọn chế độ
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Chế độ thường", "Tối ưu văn bản", "Quét tài liệu", "Quét mã QR"])
        self.mode_combo.setFixedSize(160, 40)
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header_layout.addWidget(self.mode_combo)
        
        layout.addLayout(header_layout)
        
        # Splitter chia đôi màn hình: camera ở bên trái, kết quả ở bên phải
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel camera (bên trái)
        camera_panel = QFrame()
        camera_panel.setFrameShape(QFrame.StyledPanel)
        camera_panel.setStyleSheet("""
            QFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #010000, 
                          stop:0.5 #4c2352, 
                          stop:1 #010000);
            border-radius: 10px;
            }
        """)
        camera_layout = QVBoxLayout(camera_panel)
        
        # Hiển thị camera
        self.camera_view = QLabel("Camera đang khởi động...")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumSize(480, 360)
        self.camera_view.setStyleSheet("""
            QLabel {
                color: white; 
                font-size: 16px;
                border: 3px solid rgba(255, 255, 255, 0.4);
                border-radius: 25px;
                background-color: rgba(0, 0, 0, 0.2);
                padding: 10px;
            }
        """)
        camera_layout.addWidget(self.camera_view)
        
        # Controls cho camera
        camera_controls = QHBoxLayout()
        
        # Chụp ảnh
        self.capture_btn = QPushButton("Chụp ảnh")
        self.capture_btn.setFixedSize(120, 40)
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #010000, 
                          stop:0.5 #4c2352, 
                          stop:1 #010000);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #230909, 
                          stop:0.5 #482d4f, 
                          stop:1 #230909);
            }
        """)
        self.capture_btn.clicked.connect(self._capture_image)
        camera_controls.addWidget(self.capture_btn)
        
        # Thêm nút mở link QR
        self.open_qr_btn = QPushButton("Mở mã QR")
        self.open_qr_btn.setFixedSize(120, 40)
        self.open_qr_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #454038, 
                          stop:0.5 #7a756e, 
                          stop:1 #454038);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7a756e;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.open_qr_btn.clicked.connect(self._open_detected_qr)
        self.open_qr_btn.setEnabled(False)  # Mặc định không có QR code
        camera_controls.addWidget(self.open_qr_btn)
        
        # Mirror mode
        self.mirror_btn = QPushButton("Tắt gương")
        self.mirror_btn.setFixedSize(120, 40)
        self.mirror_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #1f4449, 
                          stop:0.5 #397d86, 
                          stop:1 #1f4449);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #1f4449, 
                          stop:0.5 #27666f, 
                          stop:1 #1f4449);
            }
        """)
        self.mirror_btn.clicked.connect(self._toggle_mirror)
        camera_controls.addWidget(self.mirror_btn)
        
        # Nút cải thiện hình ảnh
        self.enhance_btn = QPushButton("Chất lượng")
        self.enhance_btn.setFixedSize(150, 40)
        self.enhance_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #2f401f, 
                          stop:0.5 #65b11d, 
                          stop:1 #2f401f);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #2f401f, 
                          stop:0.5 #3b6711, 
                          stop:1 #2f401f);
            }
        """)
        self.enhance_btn.clicked.connect(self._show_enhancement_dialog)
        camera_controls.addWidget(self.enhance_btn)
        
        camera_layout.addLayout(camera_controls)
        
        # Thêm một statusbar
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setStyleSheet("color: #BBBBBB; padding: 5px;")
        camera_layout.addWidget(self.status_label)
        
        # Panel kết quả (bên phải)
        result_panel = QFrame()
        result_panel.setFrameShape(QFrame.StyledPanel)
        result_panel.setStyleSheet("background-color: white; border-radius: 10px;")
        result_layout = QVBoxLayout(result_panel)
        
        # Label hiển thị ảnh đã chụp
        self.captured_image_label = QLabel("Chưa có ảnh nào được chụp")
        self.captured_image_label.setAlignment(Qt.AlignCenter)
        self.captured_image_label.setMinimumSize(480, 240)
        self.captured_image_label.setStyleSheet("border: 1px dashed #cccccc; border-radius: 5px;")
        result_layout.addWidget(self.captured_image_label)
          # Kết quả phân tích
        result_layout.addWidget(QLabel("Kết quả phân tích:"))
        self.result_label = QTextBrowser()
        self.result_label.setOpenExternalLinks(True)
        self.result_label.setPlaceholderText("Chưa có kết quả. Chụp ảnh và nhấn 'Phân tích' để bắt đầu.")
        self.result_label.setMinimumHeight(200)
        self.result_label.setStyleSheet("""
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
        """)
        self.result_label.anchorClicked.connect(self._handle_link_click)
        result_layout.addWidget(self.result_label)
        
        # Nút phân tích
        analyze_btn = QPushButton("Phân tích hình ảnh")
        analyze_btn.setFixedHeight(40)
        analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #4e381a, 
                          stop:0.5 #c06432, 
                          stop:1 #4e381a);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #4e381a, 
                          stop:0.5 #8c421a, 
                          stop:1 #4e381a);
            }
        """)
        analyze_btn.clicked.connect(self._analyze_image)
        result_layout.addWidget(analyze_btn)
        
        # Nút lưu kết quả
        save_btn = QPushButton("Lưu kết quả")
        save_btn.setFixedHeight(40)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #050607, 
                          stop:0.5 #4e5863, 
                          stop:1 #050607);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #050607, 
                          stop:0.5 #333f4b, 
                          stop:1 #050607);
            }
        """)
        save_btn.clicked.connect(self._save_results)
        result_layout.addWidget(save_btn)
        
        # Nút dừng âm thanh
        self.stop_audio_btn = QPushButton("⏹ Dừng âm thanh")
        self.stop_audio_btn.setFixedHeight(40)
        self.stop_audio_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #8B0000, 
                          stop:0.5 #DC143C, 
                          stop:1 #8B0000);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #A0000A, 
                          stop:0.5 #FF1C47, 
                          stop:1 #A0000A);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                          stop:0 #666666, 
                          stop:0.5 #888888, 
                          stop:1 #666666);
                color: #CCCCCC;
            }
        """)
        self.stop_audio_btn.clicked.connect(self._stop_audio)
        self.stop_audio_btn.setEnabled(False)  # Mặc định tắt khi chưa có âm thanh
        result_layout.addWidget(self.stop_audio_btn)
        
        # Thêm panels vào splitter
        splitter.addWidget(camera_panel)
        splitter.addWidget(result_panel)
        
        # Thiết lập kích thước ban đầu cho splitter
        splitter.setSizes([500, 500])
        
        # Thêm splitter vào layout chính
        layout.addWidget(splitter)
        
        # Status bar dưới cùng
        status_bar = QHBoxLayout()
        status_bar.addWidget(QLabel("Trạng thái camera:"))
        
        self.camera_status = QLabel("Chưa khởi động")
        self.camera_status.setStyleSheet("font-weight: bold; color: #F44336;")
        status_bar.addWidget(self.camera_status)
        
        status_bar.addStretch()
        
        # Thêm thông tin QR code (nếu có)
        if ZBAR_AVAILABLE:
            status_bar.addWidget(QLabel("Quét mã QR:"))
            self.qr_status = QLabel("Sẵn sàng")
            self.qr_status.setStyleSheet("font-style: italic;")
            status_bar.addWidget(self.qr_status)
        else:
            qr_install_btn = QPushButton("Cài đặt pyzbar để quét mã QR")
            qr_install_btn.clicked.connect(self._show_qr_installation)
            status_bar.addWidget(qr_install_btn)
        
        layout.addLayout(status_bar)

    def _toggle_mirror(self):
        """Bật/tắt chế độ gương."""
        self.is_mirror_mode = not self.is_mirror_mode
        if self.camera_thread:
            self.camera_thread.set_mirror(self.is_mirror_mode)
        
        # Cập nhật nút
        if self.is_mirror_mode:
            self.mirror_btn.setText("Tắt gương")
        else:
            self.mirror_btn.setText("Bật gương")
        
        self.status_label.setText(f"Chế độ gương: {'Bật' if self.is_mirror_mode else 'Tắt'}")
    def _on_mode_changed(self, index):
        """Xử lý khi chế độ thay đổi."""
        modes = ["normal", "text", "document", "qr"]
        self.current_mode = modes[index]
        
        # Cập nhật processor cho camera thread
        if self.camera_thread:
            if self.current_mode == "text":
                self.camera_thread.set_processor(self._enhance_text_frame)
            elif self.current_mode == "document":
                self.camera_thread.set_processor(self._enhance_document_frame)
            else:
                self.camera_thread.set_processor(None)  # Sử dụng frame gốc
                
        # Cập nhật trạng thái
        mode_names = {
            "normal": "thường",
            "text": "tối ưu văn bản",
            "document": "quét tài liệu",
            "qr": "quét mã QR"
        }
        
        mode_message = f"Đã chuyển sang chế độ {mode_names.get(self.current_mode, '')}"
        
        # Thêm thông báo đặc biệt cho chế độ QR
        if self.current_mode == "qr":
            mode_message += " - Chỉ trong chế độ này các liên kết mới có thể được mở trực tiếp"
        
        self.status_label.setText(mode_message)
          # Nếu chuyển sang chế độ QR, xóa kết quả cũ
        if self.current_mode == "qr":
            self.result_label.setText("Chụp ảnh hoặc quét QR để hiển thị kết quả")
        # Cập nhật nút mở QR
        self.open_qr_btn.setEnabled(self.current_mode == "qr" and len(self.qr_links) > 0)
    
    def _enhance_text_frame(self, frame):
        """Tăng cường frame để hiển thị văn bản tốt hơn."""
        if not CV2_AVAILABLE:
            return frame
            
        try:
            # Chuyển thành grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Áp dụng adaptive threshold để làm rõ văn bản
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Chuyển lại thành BGR để hiển thị
            enhanced = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
            
            # Áp dụng các mức điều chỉnh tùy chỉnh
            if self.contrast_level != 1.0 or self.brightness_level != 1.0:
                # Chuyển về định dạng float32 để tính toán
                enhanced_float = enhanced.astype(np.float32) / 255.0
                
                # Áp dụng độ tương phản
                enhanced_float = enhanced_float * self.contrast_level
                
                # Áp dụng độ sáng
                enhanced_float = enhanced_float + (self.brightness_level - 1.0)
                
                # Giới hạn giá trị từ 0 đến 1
                enhanced_float = np.clip(enhanced_float, 0, 1)
                  # Chuyển lại về uint8
                enhanced = (enhanced_float * 255).astype(np.uint8)
            
            return enhanced
        except Exception as e:
            logger.error(f"Error enhancing text frame: {str(e)}")
            return frame
    
    def _enhance_document_frame(self, frame):
        """Tăng cường frame để quét tài liệu tốt hơn."""
        if not CV2_AVAILABLE:
            return frame
            
        try:
            # Tạo bản sao để vẽ lên
            enhanced = frame.copy()
            
            # Nâng cao độ tương phản cho tài liệu
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Áp dụng Canny edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Tìm contours
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sắp xếp theo diện tích giảm dần và lấy 5 contour lớn nhất
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
            
            # Tìm contour có 4 cạnh (có thể là tài liệu)
            doc_contour = None
            for contour in contours:
                perimeter = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
                
                # Nếu contour có 4 điểm, có thể là tài liệu
                if len(approx) == 4:
                    doc_contour = approx
                    break
              # Vẽ contour tài liệu nếu tìm thấy
            if doc_contour is not None:
                cv2.drawContours(enhanced, [doc_contour], -1, (0, 255, 0), 2)
                # Đánh dấu các góc
                for point in doc_contour:
                    x, y = point[0]
                    cv2.circle(enhanced, (x, y), 5, (0, 0, 255), -1)
            
            return enhanced
        except Exception as e:
            logger.error(f"Error enhancing document frame: {str(e)}")
            return frame
    
    def _start_camera(self):
        """Khởi động camera."""
        if not CV2_AVAILABLE:
            self._show_opencv_error()
            return
            
        if self.is_camera_running:
            return
            
        try:
            # Dừng camera thread hiện tại nếu có
            if self.camera_thread and self.camera_thread.isRunning():
                self.camera_thread.stop()
                self.camera_thread.wait()
                
            # Check for available cameras
            available_cameras = []
            for i in range(5):  # Check the first 5 camera indices
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        available_cameras.append(i)
                        cap.release()
                except Exception as e:
                    logger.warning(f"Error checking camera {i}: {e}")
                    continue
            
            if not available_cameras:
                raise Exception("Không tìm thấy camera nào được kết nối")
                
            # Use the first available camera (usually the default webcam)
            self.camera_id = available_cameras[0]
            logger.info(f"Using camera with index {self.camera_id}")
                
            # Khởi tạo camera thread mới
            self.camera_thread = CameraThread(self.camera_id)
            self.camera_thread.frame_ready.connect(self._process_frame)
            self.camera_thread.error_occurred.connect(self._handle_camera_error)  # Connect error signal
            self.camera_thread.set_mirror(self.is_mirror_mode)
            
            # Set the appropriate processor based on current mode
            if self.current_mode == "text":
                self.camera_thread.set_processor(self._enhance_text_frame)
            elif self.current_mode == "document":
                self.camera_thread.set_processor(self._enhance_document_frame)
            
            # Start the camera thread
            self.camera_thread.start()
            
            # Set a timer to verify camera is working after 2 seconds
            QTimer.singleShot(2000, self._verify_camera_running)
            
            self.is_camera_running = True
            self.camera_status.setText("Đã kết nối")
            self.camera_status.setStyleSheet("font-weight: bold; color: #4CAF50;")
            self.status_label.setText("Camera đã khởi động")
            
            logger.info("Camera started successfully")
        except Exception as e:
            self.camera_status.setText("Lỗi: " + str(e))
            self.camera_status.setStyleSheet("font-weight: bold; color: #F44336;")
            self.status_label.setText("Không thể khởi động camera")
            logger.error(f"Error starting camera: {str(e)}")
            QMessageBox.critical(self, "Lỗi Camera", 
                               f"Không thể khởi động camera: {str(e)}\n\n"
                               "Vui lòng kiểm tra xem camera có được kết nối và không bị ứng dụng khác sử dụng.")
    
    def _handle_camera_error(self, error_message):
        """Handle camera errors from thread."""
        self.camera_status.setText("Lỗi camera")
        self.camera_status.setStyleSheet("font-weight: bold; color: #F44336;")
        self.status_label.setText(error_message)
        self.is_camera_running = False
        
        # Show error in camera view
        self.camera_view.setText(f"❌ Lỗi Camera\n\n{error_message}")
        self.camera_view.setStyleSheet("color: #F44336; font-size: 14px; background-color: #ffebee; border: 2px solid #F44336;")
        
        logger.error(f"Camera error: {error_message}")
                               
    def _verify_camera_running(self):
        """Verify that the camera is actually running and receiving frames."""
        if self.camera_thread and not hasattr(self.camera_thread, "current_frame"):
            logger.warning("Camera not providing frames after initialization")
            self.status_label.setText("Camera không phản hồi, thử khởi động lại")
            
            # Try restarting the camera
            self.is_camera_running = False
            self._start_camera()
    
    def _process_frame(self, frame):
        """Xử lý frame từ camera."""
        if self.is_capturing:
            return
            
        try:            # Tạo bản sao để tránh sửa đổi frame gốc
            display_frame = frame.copy()
            
            # Thực hiện quét mã QR nếu đang ở chế độ QR
            if self.current_mode == "qr":
                # Kiểm tra nếu ZBar có sẵn
                if ZBAR_AVAILABLE:
                    try:
                        # Chuyển đổi sang grayscale cho việc quét QR tốt hơn
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        
                        # Quét mã QR
                        self.qr_codes = zbar_decode(gray)
                        
                        # Vẽ khung xung quanh mã QR
                        for code in self.qr_codes:
                            # Lấy tọa độ của mã QR
                            points = code.polygon
                            if len(points) > 4:
                                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                                points = hull
                            else:
                                points = np.array([point for point in points], dtype=np.int32)
                            
                            # Vẽ đa giác
                            cv2.polylines(display_frame, [points], True, (0, 255, 0), 3)
                            
                            # Vẽ điểm trung tâm
                            x, y, w, h = code.rect
                            cv2.circle(display_frame, (x + w//2, y + h//2), 5, (0, 0, 255), -1)
                            
                            # Thêm hiệu ứng highlight cho vùng QR code
                            overlay = display_frame.copy()
                            cv2.fillPoly(overlay, [points], (0, 255, 0, 64))
                            cv2.addWeighted(overlay, 0.3, display_frame, 0.7, 0, display_frame)
                            
                            # Hiển thị dữ liệu QR
                            qr_data = code.data.decode('utf-8')
                            if len(qr_data) > 30:
                                qr_data = qr_data[:27] + "..."
                                
                            # Tạo nền cho văn bản
                            text_size = cv2.getTextSize(qr_data, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                            text_x = x
                            text_y = y - 10
                            cv2.rectangle(display_frame, 
                                         (text_x - 2, text_y - text_size[1] - 2),
                                         (text_x + text_size[0] + 2, text_y + 2), 
                                         (0, 0, 0), -1)
                                
                            cv2.putText(display_frame, qr_data, (text_x, text_y),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            # Lưu link nếu là URL
                            if qr_data.startswith("http://") or qr_data.startswith("https://"):
                                self.qr_links.append(qr_data)
                    except Exception as e:
                        logger.error(f"Error processing QR code: {str(e)}")
                        self.qr_codes = []
                else:
                    # Hiển thị thông báo khi ZBar không có sẵn
                    cv2.putText(display_frame, "ZBar không khả dụng - Chức năng quét QR bị vô hiệu", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(display_frame, "Chạy fix_libzbar_proper.py để sửa lỗi", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    # Đặt QR codes rỗng
                    self.qr_codes = []                # Cập nhật trạng thái QR
                if hasattr(self, 'qr_status'):
                    if not ZBAR_AVAILABLE:
                        self.qr_status.setText("ZBar không khả dụng - Không thể quét QR")
                        self.qr_status.setStyleSheet("font-weight: bold; color: #FF5252;")
                        self.open_qr_btn.setEnabled(False)
                        
                        # Hiển thị hướng dẫn cài đặt ZBar
                        html_content = "<h3>Chức năng quét QR code bị vô hiệu</h3>"
                        html_content += "<p>Để kích hoạt tính năng quét mã QR, hãy cài đặt ZBar:</p>"
                        html_content += "<ol>"
                        html_content += "<li>Chạy fix_libzbar_proper.py hoặc ultimate_fix.py</li>"
                        html_content += "<li>Tải và cài đặt ZBar từ: <a href='https://sourceforge.net/projects/zbar/files/zbar/0.10/zbar-0.10-setup.exe/download'>sourceforge.net</a></li>"
                        html_content += "</ol>"
                        
                        if hasattr(self, 'result_label'):
                            self.result_label.setHtml(html_content)
                    elif self.qr_codes:
                        self.qr_status.setText(f"Đã tìm thấy {len(self.qr_codes)} mã")
                        self.qr_status.setStyleSheet("font-weight: bold; color: #4CAF50;")
                        
                        # Cập nhật kết quả QR code trong thời gian thực
                        if self.current_mode == "qr" and not self.is_capturing:
                            qr_data = []
                            self.qr_links = []
                            
                            for i, code in enumerate(self.qr_codes):
                                decoded_data = code.data.decode('utf-8')
                                self.qr_links.append(decoded_data)
                                # Tạo dòng hiển thị với link có thể nhấp
                                link_display = self._format_qr_link(i, decoded_data)
                                qr_data.append(link_display)
                            # Hiển thị dữ liệu QR với định dạng HTML để có link có thể nhấp
                            html_content = "<h3>Mã QR đã phát hiện:</h3>"
                            for item in qr_data:
                                html_content += f"<p>{item}</p>"
                                
                            html_content += "<p><i>Trong chế độ QR, bạn có thể nhấp trực tiếp vào link để mở.</i></p>"
                            self.result_label.setHtml(html_content)                            # Enable nút mở QR
                            self.open_qr_btn.setEnabled(len(self.qr_links) > 0)
                    else:
                        self.qr_status.setText("Không tìm thấy mã QR")
                        self.qr_status.setStyleSheet("font-style: italic; color: #757575;")
                        
                        # Disable nút mở QR khi không phát hiện mã QR
                        self.open_qr_btn.setEnabled(False)
            
            # Vẽ khung hướng dẫn cho việc chụp tài liệu
            if self.current_mode == "document":
                h, w = display_frame.shape[:2]
                margin = 50  # Căn lề
                # Vẽ khung hướng dẫn
                cv2.rectangle(display_frame, (margin, margin), (w - margin, h - margin), (0, 255, 0), 2)
                
                # Vẽ văn bản hướng dẫn
                cv2.putText(display_frame, "Dat tai lieu vao khung: ", (margin, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Chuyển đổi frame sang định dạng QImage để hiển thị trên QLabel
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Hiển thị frame trên QLabel
            pixmap = QPixmap.fromImage(qt_image)
            self.camera_view.setPixmap(pixmap.scaled(
                self.camera_view.width(), 
                self.camera_view.height(), 
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation            ))
            
        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            self.status_label.setText(f"Lỗi xử lý frame: {str(e)}")
    
    def _capture_image(self):
        """Chụp ảnh từ camera."""
        if not CV2_AVAILABLE:
            QMessageBox.warning(self, "OpenCV không khả dụng", 
                              "OpenCV không khả dụng. Vui lòng cài đặt opencv-python.")
            return
            
        if not self.is_camera_running:
            QMessageBox.warning(self, "Camera không hoạt động", 
                              "Camera không hoạt động. Vui lòng khởi động camera trước.")
            return
            
        try:
            self.is_capturing = True
            self.status_label.setText("Đang chụp ảnh...")
            
            # Reset các dữ liệu cũ
            self.qr_links = []
            
            # Đếm ngược 2 giây
            for i in range(2, 0, -1):
                self.status_label.setText(f"Chuẩn bị chụp trong {i}...")
                QApplication.processEvents()  # Đảm bảo UI được cập nhật
                time.sleep(1)
                
            # Chụp frame hiện tại
            if self.camera_thread and self.camera_thread.isRunning():
                # Chờ frame tiếp theo
                self.status_label.setText("Đang chụp...")
                QApplication.processEvents()
                time.sleep(0.5)  # Đảm bảo có frame mới
                
                # Get the latest frame from the camera thread
                if hasattr(self.camera_thread, 'current_frame') and self.camera_thread.current_frame is not None:
                    frame = self.camera_thread.current_frame.copy()
                    ret = True
                else:
                    # Fallback to direct capture if no frame is available
                    try:
                        capture = cv2.VideoCapture(self.camera_id)
                        ret, frame = capture.read()
                        capture.release()  # Immediately release the capture object
                    except Exception as e:
                        logger.error(f"Error in fallback capture: {str(e)}")
                        ret = False
                
                if ret:
                    # Lưu trữ frame đã chụp
                    self.captured_frame = frame.copy()
                    
                    # Tăng cường chất lượng nếu cần
                    if self.current_mode == "text":
                        enhanced_frame = self._enhance_text_frame(frame)
                    elif self.current_mode == "document":
                        enhanced_frame = self._enhance_document_frame(frame)
                    else:
                        enhanced_frame = frame.copy()
                    
                    # Chuyển đổi sang RGB để hiển thị
                    rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    
                    # Hiển thị hình ảnh đã chụp
                    pixmap = QPixmap.fromImage(qt_image)
                    self.captured_image_label.setPixmap(pixmap.scaled(
                        self.captured_image_label.width(),
                        self.captured_image_label.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation                    ))
                    
                    # Cập nhật trạng thái
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.status_label.setText(f"Đã chụp ảnh lúc {timestamp}")
                    
                    # Nếu đang trong chế độ QR và có mã QR
                    if self.current_mode == "qr" and self.qr_codes:
                        qr_data = []
                        self.qr_links = []
                        
                        for i, code in enumerate(self.qr_codes):
                            decoded_data = code.data.decode('utf-8')
                            self.qr_links.append(decoded_data)
                            
                            # Tạo dòng hiển thị với link có thể nhấp
                            link_display = self._format_qr_link(i, decoded_data)
                            qr_data.append(link_display)
                        
                        # Hiển thị dữ liệu QR với định dạng HTML để có link có thể nhấp
                        html_content = "<h3>Mã QR đã quét:</h3>"
                        for item in qr_data:
                            html_content += f"<p>{item}</p>"
                            
                        html_content += "<p><i>Trong chế độ QR, bạn có thể nhấp vào link để mở trực tiếp.</i></p>"
                        self.result_label.setHtml(html_content)
                          # Hiển thị một thông báo nếu phát hiện nhiều mã QR
                        if len(self.qr_codes) > 1:
                            self.status_label.setText(f"Đã quét được {len(self.qr_codes)} mã QR. Nhấp vào link để mở trực tiếp.")
                        else:
                            self.status_label.setText("Đã quét được 1 mã QR. Nhấp vào link để mở trực tiếp.")
                else:
                    self.status_label.setText("Không thể chụp ảnh. Vui lòng thử lại.")
                    QMessageBox.warning(self, "Lỗi Chụp ảnh", "Không thể chụp ảnh. Vui lòng thử lại.")
            else:
                self.status_label.setText("Camera không hoạt động")
                QMessageBox.warning(self, "Lỗi Camera", "Camera không hoạt động.")
        except Exception as e:
            logger.error(f"Error capturing image: {str(e)}")
            self.status_label.setText(f"Lỗi: {str(e)}")
            QMessageBox.critical(self, "Lỗi Chụp ảnh", f"Lỗi khi chụp ảnh: {str(e)}")
        finally:
            self.is_capturing = False
    
    def _analyze_image(self):
        """Phân tích hình ảnh bằng Gemini."""
        if not CV2_AVAILABLE:
            QMessageBox.warning(self, "OpenCV không khả dụng", 
                              "OpenCV không khả dụng. Không thể phân tích hình ảnh.")
            return
            
        if self.captured_frame is None:
            QMessageBox.warning(self, "Không có ảnh", 
                              "Vui lòng chụp ảnh trước khi phân tích.")
            return
            
        if not self.gemini_client:
            QMessageBox.warning(self, "Gemini không khả dụng", 
                              "Dịch vụ Gemini không khả dụng. Vui lòng kiểm tra kết nối.")
            return
            
        try:
            # Hiển thị trạng thái phân tích
            self.status_label.setText("Đang phân tích hình ảnh...")
            self.result_label.setText("Mis Assistant đang phân tích hình ảnh, vui lòng đợi...")
            QApplication.processEvents()
            
            # Chuẩn bị hình ảnh để gửi đến Gemini
            # Chuyển đổi frame sang RGB
            rgb_frame = cv2.cvtColor(self.captured_frame, cv2.COLOR_BGR2RGB)
            
            # Chuyển thành định dạng base64
            _, buffer = cv2.imencode('.jpg', rgb_frame)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
              # Chuẩn bị prompt dựa vào chế độ
            prompt = "Hãy mô tả chi tiết những gì bạn thấy trong hình ảnh này."
            
            if self.current_mode == "text":
                prompt = "Hãy đọc và tóm tắt văn bản trong hình ảnh này. Nếu có văn bản không rõ ràng, hãy cho biết."
            elif self.current_mode == "document":
                prompt = "Đây là một tài liệu. Hãy trích xuất thông tin quan trọng từ tài liệu này và tóm tắt nội dung chính."
            elif self.current_mode == "qr":
                prompt = "Hãy mô tả hình ảnh này và nếu có bất kỳ mã QR hoặc mã vạch nào, hãy cho biết."
            
            # Tạo thread để phân tích (tránh block UI)
            threading.Thread(target=self._run_gemini_analysis, 
                            args=(image_base64, prompt), 
                            daemon=True).start()
        except Exception as e:
            logger.error(f"Error preparing image analysis: {str(e)}")
            self.status_label.setText(f"Lỗi chuẩn bị phân tích: {str(e)}")
            self.result_label.setText(f"Lỗi: {str(e)}")
    
    def _run_gemini_analysis(self, image_base64, prompt):
        """Chạy phân tích Gemini trong thread riêng."""
        try:
            # Gọi API Gemini
            response = self.gemini_client.analyze_image(image_base64, prompt)
            
            # Lưu kết quả phân tích
            self.analysis_result = response
            
            # Cập nhật UI trong thread chính
            try:
                # Sử dụng signal thay vì invokeMethod để tránh lỗi
                self.analysis_completed.emit(response)
            except Exception as invoke_error:
                logger.error(f"Failed to emit analysis_completed signal: {str(invoke_error)}")
                # Fallback to direct update (not thread safe but as a last resort)
                QApplication.processEvents()
                self._update_analysis_result(response)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in Gemini analysis: {error_msg}")
            # Cập nhật UI với lỗi sử dụng signal
            self.analysis_completed.emit(f"Lỗi phân tích: {error_msg}")
    
    def _update_analysis_result(self, result):
        """Cập nhật kết quả phân tích trên UI (được gọi từ thread chính)."""
        # Kiểm tra xem có phải là văn bản thường hay dạng HTML
        if isinstance(result, str) and result.startswith('<') and '>' in result:
            # Nếu là HTML, hiển thị trực tiếp
            self.result_label.setHtml(result)
        else:
            # Kiểm tra chế độ hiện tại
            if self.current_mode == "qr":
                # Nếu đang ở chế độ QR, hiển thị văn bản đơn giản
                self.result_label.setText(result)
            else:
                # Đối với chế độ khác, tìm và chuyển URLs thành link có thể nhấp
                import re
                url_pattern = r'(https?://[^\s]+)'
                html_result = re.sub(url_pattern, r'<a href="\1">\1</a>', result)
                  # Chỉ chuyển sang HTML nếu thực sự tìm thấy link
                if html_result != result:
                    # Thêm thông báo về chế độ QR ở đầu kết quả
                    notice = """<div style="background-color: #f8f9fa; padding: 8px; margin-bottom: 10px; border-left: 4px solid #ffc107; border-radius: 4px;">
                    <b>Lưu ý:</b> Đã phát hiện liên kết trong kết quả. Trong chế độ thường, bạn chỉ có thể sao chép liên kết, không thể mở trực tiếp.
                    Để mở liên kết trực tiếp, vui lòng chuyển sang <b>chế độ quét mã QR</b>.
                    </div>"""
                    
                    html_result = notice + html_result
                    self.result_label.setHtml(html_result)
                    self.status_label.setText("Phân tích hoàn tất - Nhấp vào liên kết để sao chép")
                else:
                    self.result_label.setText(result)
        
        # Automatic TTS for all modes when analysis is completed (NON-BLOCKING)
        if self.speech_processor and result:
            try:
                # Clean the text for TTS (remove HTML tags if any)
                import re
                clean_text = re.sub(r'<[^>]+>', '', result)
                clean_text = clean_text.strip()
                
                if clean_text:
                    # Clear any prepared audio from previous chat interactions
                    # to ensure Smart Vision generates new TTS for the analysis result
                    self.speech_processor.prepared_audio_file = None
                    
                    # Kích hoạt nút dừng khi bắt đầu TTS
                    self.stop_audio_btn.setEnabled(True)
                    
                    # Use NON-BLOCKING TTS in a separate thread to avoid UI freeze
                    def async_tts():
                        try:
                            self.speech_processor.text_to_speech(clean_text)
                            # Tự động tắt nút dừng khi TTS hoàn tất
                            QTimer.singleShot(100, lambda: self.stop_audio_btn.setEnabled(False))
                        except Exception as e:
                            logger.error(f"Error in async TTS: {str(e)}")
                            # Tắt nút dừng nếu có lỗi
                            QTimer.singleShot(100, lambda: self.stop_audio_btn.setEnabled(False))
                    
                    # Start TTS in background thread
                    threading.Thread(target=async_tts, daemon=True).start()
                    self.status_label.setText("Phân tích hoàn tất - Đang phát âm thanh")
                else:
                    self.status_label.setText("Phân tích hoàn tất")
            except Exception as e:
                logger.error(f"Error in automatic TTS setup: {str(e)}")
                self.status_label.setText("Phân tích hoàn tất - Lỗi TTS tự động")
                self.stop_audio_btn.setEnabled(False)
        else:
            self.status_label.setText("Phân tích hoàn tất")
    
    def _save_results(self):
        """Lưu kết quả phân tích và hình ảnh."""
        if not CV2_AVAILABLE:
            QMessageBox.warning(self, "OpenCV không khả dụng", 
                              "OpenCV không khả dụng. Không thể lưu hình ảnh.")
            return
            
        if self.captured_frame is None:
            QMessageBox.warning(self, "Không có dữ liệu", 
                              "Không có hình ảnh hoặc kết quả để lưu.")
            return
            
        try:
            # Tạo thư mục lưu nếu chưa tồn tại
            save_dir = os.path.join(os.path.expanduser("~"), "MIS_Assistant_Results")
            os.makedirs(save_dir, exist_ok=True)
            
            # Tạo tên file dựa vào thời gian
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = os.path.join(save_dir, f"vision_analysis_{timestamp}")
            
            # Lưu hình ảnh
            image_path = f"{base_filename}.jpg"
            cv2.imwrite(image_path, self.captured_frame)
            
            # Lưu kết quả văn bản nếu có
            if self.analysis_result:
                text_path = f"{base_filename}.txt"
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(self.analysis_result)
            
            # Lưu các link QR nếu có
            if self.qr_links:
                links_path = f"{base_filename}_links.txt"
                with open(links_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(self.qr_links))
            
            QMessageBox.information(self, "Lưu thành công", 
                                  f"Đã lưu hình ảnh và kết quả tại:\n{save_dir}")
            
            self.status_label.setText(f"Đã lưu kết quả tại: {save_dir}")
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            QMessageBox.critical(self, "Lỗi Lưu", f"Không thể lưu kết quả: {str(e)}")
    
    def _show_qr_installation(self):
        """Hiển thị thông tin về cách cài đặt pyzbar."""
        QMessageBox.information(self, "Cài đặt pyzbar", 
                              "Để sử dụng chức năng quét mã QR, vui lòng cài đặt pyzbar:\n\n"
                              "pip install pyzbar\n\n"
                              "Trên Windows, bạn có thể cần cài đặt thêm các thư viện Visual C++.\n"
                              "Trên Linux, bạn có thể cần cài đặt libzbar0:\n"
                              "sudo apt install libzbar0")
                              
    def _show_enhancement_dialog(self):
        """Hiển thị dialog điều chỉnh tăng cường hình ảnh."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Tùy chỉnh hình ảnh")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Điều chỉnh độ tương phản
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Độ tương phản:"))
        
        contrast_slider = QSlider(Qt.Horizontal)
        contrast_slider.setMinimum(50)
        contrast_slider.setMaximum(150)
        contrast_slider.setValue(int(self.contrast_level * 100))
        contrast_value = QLabel(f"{self.contrast_level:.1f}")
        
        contrast_slider.valueChanged.connect(
            lambda v: self._update_enhancement_value('contrast', v/100, contrast_value))
        
        contrast_layout.addWidget(contrast_slider)
        contrast_layout.addWidget(contrast_value)
        layout.addLayout(contrast_layout)
        
        # Điều chỉnh độ sáng
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Độ sáng:"))
        
        brightness_slider = QSlider(Qt.Horizontal)
        brightness_slider.setMinimum(50)
        brightness_slider.setMaximum(150)
        brightness_slider.setValue(int(self.brightness_level * 100))
        brightness_value = QLabel(f"{self.brightness_level:.1f}")
        
        brightness_slider.valueChanged.connect(
            lambda v: self._update_enhancement_value('brightness', v/100, brightness_value))
        
        brightness_layout.addWidget(brightness_slider)
        brightness_layout.addWidget(brightness_value)
        layout.addLayout(brightness_layout)
        
        # Điều chỉnh độ sắc nét
        sharpness_layout = QHBoxLayout()
        sharpness_layout.addWidget(QLabel("Độ sắc nét:"))
        
        sharpness_slider = QSlider(Qt.Horizontal)
        sharpness_slider.setMinimum(50)
        sharpness_slider.setMaximum(200)
        sharpness_slider.setValue(int(self.sharpness_level * 100))
        sharpness_value = QLabel(f"{self.sharpness_level:.1f}")
        
        sharpness_slider.valueChanged.connect(
            lambda v: self._update_enhancement_value('sharpness', v/100, sharpness_value))
        
        sharpness_layout.addWidget(sharpness_slider)
        sharpness_layout.addWidget(sharpness_value)
        layout.addLayout(sharpness_layout)
        
        # Nút reset
        reset_btn = QPushButton("Reset về mặc định")
        reset_btn.clicked.connect(lambda: self._reset_enhancement_values(
            contrast_slider, brightness_slider, sharpness_slider,
            contrast_value, brightness_value, sharpness_value
        ))
        layout.addWidget(reset_btn)
        
        # Nút đóng
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()
    
    def _update_enhancement_value(self, param, value, label):
        """Cập nhật giá trị tăng cường hình ảnh."""
        if param == 'contrast':
            self.contrast_level = value
        elif param == 'brightness':
            self.brightness_level = value
        elif param == 'sharpness':
            self.sharpness_level = value
            
        label.setText(f"{value:.1f}")
    
    def _reset_enhancement_values(self, c_slider, b_slider, s_slider, c_label, b_label, s_label):
        """Reset các giá trị tăng cường về mặc định."""
        self.contrast_level = 1.0
        self.brightness_level = 1.0
        self.sharpness_level = 1.0
        
        c_slider.setValue(100)
        b_slider.setValue(100)
        s_slider.setValue(100)
        
        c_label.setText("1.0")
        b_label.setText("1.0")
        s_label.setText("1.0")
    
    def _format_qr_link(self, index, link_text):
        """Format a QR code link for display with clickable functionality."""
        # Check if text is a valid URL, email, or other recognizable format
        is_url = link_text.startswith(('http://', 'https://', 'www.', 'ftp://'))
        is_email = '@' in link_text and '.' in link_text.split('@')[1]
        is_phone = link_text.startswith(('tel:', '+'))
        
        # Create a readable display version (shortened if needed)
        display_text = link_text
        if len(display_text) > 50:
            display_text = display_text[:47] + "..."
        
        # Format appropriate HTML based on content type
        if is_url:
            # For URLs, create a proper HTML link
            if not link_text.startswith(('http://', 'https://')):
                actual_link = 'https://' + link_text.lstrip('www.')
            else:
                actual_link = link_text
                
            return f"<b>Link {index+1}:</b> <a href='{actual_link}'>{display_text}</a>"
        
        elif is_email:
            # For emails, create a mailto link
            if not link_text.startswith('mailto:'):
                actual_link = 'mailto:' + link_text
            else:
                actual_link = link_text
                
            return f"<b>Email {index+1}:</b> <a href='{actual_link}'>{display_text}</a>"
        
        elif is_phone:
            # For phone numbers, create a tel link
            if not link_text.startswith('tel:'):
                actual_link = 'tel:' + link_text.lstrip('+')
            else:
                actual_link = link_text
                
            return f"<b>Số điện thoại {index+1}:</b> <a href='{actual_link}'>{display_text}</a>"
        else:
            # For other content, make it a custom protocol that we'll handle
            return f"<b>Nội dung {index+1}:</b> <a href='qrtext://{index}'>{display_text}</a>"
    
    def _handle_link_click(self, url):
        """Handle clicks on links in the result browser."""
        url_str = url.toString()
        
        # Prevent the default navigation
        self.result_label.setSource(QUrl())
        
        try:
            # Handle our custom protocol for text content
            if url_str.startswith('qrtext://'):
                index = int(url_str.split('://')[1])
                if 0 <= index < len(self.qr_links):
                    # Copy to clipboard
                    clipboard = QApplication.clipboard()
                    clipboard.setText(self.qr_links[index])
                    self.status_label.setText("Đã sao chép nội dung vào clipboard")
                return
            
            # For standard URLs, try to open them with the launcher service first
            if url_str.startswith(('http://', 'https://')):
                # Only allow opening URLs in QR mode, otherwise show a message
                if self.current_mode == "qr":
                    # Check if it's a command or app URL
                    handled = self.launcher_service.process_request(url_str)
                    
                    # If not handled as a command, open in browser
                    if not handled:
                        QDesktopServices.openUrl(url)
                    
                    self.status_label.setText(f"Đã mở link: {url_str}")
                else:
                    # If not in QR mode, just copy the URL to clipboard
                    clipboard = QApplication.clipboard()
                    clipboard.setText(url_str)
                    QMessageBox.information(self, "Đã sao chép liên kết", 
                                         "Liên kết đã được sao chép vào clipboard.\n\n"
                                         "Chỉ có thể mở liên kết trực tiếp khi ở chế độ quét mã QR. "
                                         "Vui lòng chuyển sang chế độ QR để sử dụng chức năng này.")
                    self.status_label.setText("Đã sao chép liên kết vào clipboard. Chuyển sang chế độ QR để mở trực tiếp.")
            else:
                # For other protocols (mailto, tel, etc.)
                if self.current_mode == "qr":
                    QDesktopServices.openUrl(url)
                    self.status_label.setText(f"Đã mở: {url_str}")
                else:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(url_str)
                    self.status_label.setText("Đã sao chép vào clipboard. Chuyển sang chế độ QR để mở trực tiếp.")
                
        except Exception as e:
            logger.error(f"Error handling link click: {str(e)}")
            self.status_label.setText(f"Lỗi khi mở link: {str(e)}")
            QMessageBox.warning(self, "Lỗi Mở Link", 
                               f"Không thể mở link này: {str(e)}")
    def _open_detected_qr(self):
        """Open the first detected QR code link."""
        if self.qr_links:
            try:
                # Only allow opening URLs in QR mode
                if self.current_mode != "qr":
                    QMessageBox.information(self, "Chế độ QR không hoạt động", 
                                         "Chức năng mở liên kết chỉ hoạt động trong chế độ quét mã QR.\n\n"
                                         "Vui lòng chuyển sang chế độ QR để sử dụng chức năng này.")
                    return
                
                # Try to handle with launcher service first
                handled = self.launcher_service.process_request(self.qr_links[0])
                  # If not handled as a command, open in browser
                if not handled:
                    QDesktopServices.openUrl(QUrl(self.qr_links[0]))
                
                self.status_label.setText(f"Đã mở mã QR: {self.qr_links[0]}")
            except Exception as e:
                logger.error(f"Error opening QR code link: {str(e)}")
                self.status_label.setText(f"Lỗi khi mở mã QR: {str(e)}")
                QMessageBox.warning(self, "Lỗi Mở Mã QR", 
                                                                      f"Không thể mở mã QR này: {str(e)}")
        else:
            self.status_label.setText("Không có mã QR để mở")
    
    def closeEvent(self, event):
        """Xử lý khi đóng widget."""
        # Dừng camera thread nếu đang chạy
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
            self.camera_thread.wait()
        
        event.accept()
    
    def _show_opencv_error(self):
        """Hiển thị lỗi khi OpenCV không khả dụng."""
        error_html = """
        <div style="text-align: center; padding: 20px;">
            <h2 style="color: #F44336;">❌ Smart Vision không khả dụng</h2>
            <p><strong>Nguyên nhân:</strong> OpenCV (cv2) không được cài đặt hoặc không hoạt động đúng.</p>
            <br>
            <h3>🔧 Cách khắc phục:</h3>
            <ol style="text-align: left; display: inline-block;">
                <li>Cài đặt OpenCV bằng lệnh: <code>pip install opencv-python</code></li>
                <li>Nếu vẫn lỗi, thử: <code>pip install opencv-python-headless</code></li>
                <li>Khởi động lại ứng dụng sau khi cài đặt</li>
                <li>Nếu sử dụng exe, vui lòng build lại với opencv-python trong requirements</li>
            </ol>
            <br>
            <p style="color: #757575; font-style: italic;">
                Smart Vision cần OpenCV để hoạt động. Các chức năng khác của MIS Assistant vẫn hoạt động bình thường.
            </p>
        </div>
        """
        
        self.camera_view.setText("")
        self.camera_view.setStyleSheet("background-color: #f5f5f5; border: 2px dashed #cccccc;")
        
        self.result_label.setHtml(error_html)
        self.camera_status.setText("OpenCV không khả dụng")
        self.camera_status.setStyleSheet("font-weight: bold; color: #F44336;")
        self.status_label.setText("Smart Vision đã bị vô hiệu hóa - OpenCV không khả dụng")
        
        # Disable camera-related buttons
        self.capture_btn.setEnabled(False)
        self.mirror_btn.setEnabled(False)
        self.enhance_btn.setEnabled(False)
        self.stop_audio_btn.setEnabled(False)
    
    def _stop_audio(self):
        """Dừng âm thanh TTS đang phát."""
        try:
            if self.speech_processor:
                # Dừng TTS - use the correct method name
                if hasattr(self.speech_processor, 'stop_audio'):
                    self.speech_processor.stop_audio()
                elif hasattr(self.speech_processor, 'stop_speech'):
                    self.speech_processor.stop_speech()
                elif hasattr(self.speech_processor, 'stop'):
                    self.speech_processor.stop()
                elif hasattr(self.speech_processor, 'stop_playback'):
                    self.speech_processor.stop_playback()
                else:
                    # Fallback: try to stop pygame mixer directly if available
                    try:
                        import pygame
                        if pygame.mixer.get_init():
                            pygame.mixer.stop()
                        logger.info("Stopped audio using pygame mixer fallback")
                    except (ImportError, pygame.error):
                        logger.warning("No suitable stop method found in SpeechProcessor")
                        self.status_label.setText("Không thể dừng âm thanh - phương thức không hỗ trợ")
                        return
                
                # Cập nhật trạng thái UI
                self.stop_audio_btn.setEnabled(False)
                self.status_label.setText("Đã dừng âm thanh")
                
                logger.info("Audio stopped by user in Smart Vision")
            else:
                self.status_label.setText("Không có dịch vụ âm thanh")
        except Exception as e:
            logger.error(f"Error stopping audio in Smart Vision: {str(e)}")
            self.status_label.setText(f"Lỗi khi dừng âm thanh: {str(e)}")
            # Disable the button even if there's an error
            self.stop_audio_btn.setEnabled(False)
