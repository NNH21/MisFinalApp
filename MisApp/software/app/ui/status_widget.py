import sys
import platform
import psutil
import datetime
import socket
import subprocess
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QPainter

from ..utils import logger

class StatusWidget(QWidget):
    """Widget for displaying system and hardware status."""
    
    def __init__(self, hardware_interface):
        super().__init__()
        
        # Store reference to hardware interface
        self.hardware_interface = hardware_interface
        
        # Set up the UI
        self._setup_ui()
        
        # Start the timer to update status
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(2000)  # Update every 2 seconds
        
        # Initial update
        self._update_network_info()
        self.update_hardware_status(self.hardware_interface.is_connected(), 
                                    self.hardware_interface.get_esp_ip())
        
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        self.setMaximumHeight(120)  # Limit height
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Network info section
        network_frame = QFrame()
        network_frame.setFrameShape(QFrame.StyledPanel)
        network_layout = QGridLayout(network_frame)
        network_layout.setContentsMargins(10, 5, 10, 5)
        
        # Network info labels
        network_header_layout = QHBoxLayout()
        network_label = QLabel("Thông tin mạng")
        bold_font = QFont()
        bold_font.setBold(True)
        network_label.setFont(bold_font)
        
        # WiFi icon
        self.wifi_icon_label = QLabel()
        self.wifi_icon_label.setFixedSize(24, 24)
        
        network_header_layout.addWidget(network_label)
        network_header_layout.addStretch()
        network_header_layout.addWidget(self.wifi_icon_label)
        
        network_layout.addLayout(network_header_layout, 0, 0, 1, 3)
        
        # WiFi SSID
        ssid_label = QLabel("Tên WiFi:")
        self.ssid_value = QLabel("--")
        network_layout.addWidget(ssid_label, 1, 0)
        network_layout.addWidget(self.ssid_value, 1, 1, 1, 2)
        
        # WiFi Speed
        speed_label = QLabel("Tốc độ:")
        self.speed_value = QLabel("--")
        network_layout.addWidget(speed_label, 2, 0)
        network_layout.addWidget(self.speed_value, 2, 1, 1, 2)
        
        # IP Address
        ip_label = QLabel("Địa chỉ IP:")
        self.network_ip_value = QLabel("--")
        network_layout.addWidget(ip_label, 3, 0)
        network_layout.addWidget(self.network_ip_value, 3, 1, 1, 2)
        
        # Hardware status section
        hardware_frame = QFrame()
        hardware_frame.setFrameShape(QFrame.StyledPanel)
        hardware_layout = QGridLayout(hardware_frame)
        hardware_layout.setContentsMargins(10, 5, 10, 5)
        
        # Hardware status labels
        hardware_label = QLabel("Trạng thái phần cứng")
        hardware_label.setFont(bold_font)
        hardware_layout.addWidget(hardware_label, 0, 0, 1, 2)
          # Connection status
        status_label = QLabel("Kết nối:")
        self.status_value = QLabel("Chưa kết nối")
        hardware_layout.addWidget(status_label, 1, 0)
        hardware_layout.addWidget(self.status_value, 1, 1)
        
        # COM Port
        port_label = QLabel("Cổng COM:")
        self.port_value = QLabel("--")
        hardware_layout.addWidget(port_label, 2, 0)
        hardware_layout.addWidget(self.port_value, 2, 1)
        
        # IP address
        esp_ip_label = QLabel("Địa chỉ IP:")
        self.ip_value = QLabel("--")
        hardware_layout.addWidget(esp_ip_label, 3, 0)
        hardware_layout.addWidget(self.ip_value, 3, 1)
        
        # Add frames to main layout
        main_layout.addWidget(network_frame)
        main_layout.addWidget(hardware_frame)
        
    def _update_status(self):
        """Cập nhật thông tin trạng thái mạng và phần cứng."""
        # Cập nhật thông tin mạng
        self._update_network_info()
        
    def _update_network_info(self):
        """Cập nhật thông tin mạng WiFi."""
        try:
            # Lấy thông tin mạng
            connected, ssid, speed, strength, ip = self._get_network_info()
            
            # Cập nhật biểu tượng WiFi
            wifi_icon = self._create_wifi_icon(connected, strength)
            self.wifi_icon_label.setPixmap(wifi_icon)
            
            # Cập nhật thông tin WiFi
            self.ssid_value.setText(ssid)
            
            if connected:
                self.ssid_value.setStyleSheet("color: green;")
                self.speed_value.setText(speed)
                self.network_ip_value.setText(ip)
            else:
                self.ssid_value.setStyleSheet("color: red;")
                self.speed_value.setText("Không có kết nối")
                self.network_ip_value.setText("--")
            
        except Exception as e:
            logger.error(f"Error updating network info: {str(e)}")            
    def update_hardware_status(self, connected, ip_address=None, port=None):
        """
        Update the hardware connection status display.
        
        Args:
            connected (bool): Whether hardware is connected
            ip_address (str): IP address of the hardware
            port (str): COM port of the hardware
        """
        if connected:
            self.status_value.setText("Đã kết nối")
            self.status_value.setStyleSheet("color: green; font-weight: bold;")
            
            if ip_address and ip_address != "Unknown":
                self.ip_value.setText(ip_address)
                self.ip_value.setStyleSheet("color: green;")
            else:
                self.ip_value.setText("--")
                self.ip_value.setStyleSheet("color: gray;")
                
            if port:
                self.port_value.setText(port)
                self.port_value.setStyleSheet("color: green;")
            else:
                self.port_value.setText("--")
                self.port_value.setStyleSheet("color: gray;")
        else:
            self.status_value.setText("Ngắt kết nối")
            self.status_value.setStyleSheet("color: red; font-weight: bold;")
            self.ip_value.setText("--")
            self.ip_value.setStyleSheet("color: gray;")
            self.port_value.setText("--")
            self.port_value.setStyleSheet("color: gray;")
    
    def _set_progress_color(self, progress_bar, value):
        """Set the progress bar color based on value."""
        palette = QPalette()
        
        if value < 60:
            # Green for low usage
            palette.setColor(QPalette.Highlight, QColor(0, 170, 0))
        elif value < 85:
            # Yellow for medium usage
            palette.setColor(QPalette.Highlight, QColor(255, 170, 0))
        else:
            # Red for high usage
            palette.setColor(QPalette.Highlight, QColor(255, 0, 0))
            
        progress_bar.setPalette(palette)
    
    def _format_bytes(self, bytes):
        """Format bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} PB"
    
    def _create_wifi_icon(self, connected=False, strength=0):
        """
        Tạo biểu tượng WiFi với trạng thái kết nối
        
        Args:
            connected (bool): Trạng thái kết nối
            strength (int): Cường độ tín hiệu (0-4)
        
        Returns:
            QPixmap: Biểu tượng WiFi
        """
        # Tạo ảnh trống
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        
        # Thiết lập đối tượng vẽ
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Màu sắc dựa trên trạng thái kết nối
        if connected:
            if strength == 0:
                color = QColor(255, 0, 0)  # Đỏ cho tín hiệu yếu
            elif strength == 1:
                color = QColor(255, 120, 0)  # Cam cho tín hiệu yếu
            elif strength == 2:
                color = QColor(255, 200, 0)  # Vàng cam cho tín hiệu trung bình
            elif strength == 3:
                color = QColor(200, 255, 0)  # Vàng lục cho tín hiệu khá
            else:
                color = QColor(0, 170, 0)  # Xanh lục cho tín hiệu mạnh
        else:
            color = QColor(128, 128, 128)  # Xám khi không kết nối
            
        painter.setPen(color)
        painter.setBrush(color)
        
        # Vẽ biểu tượng WiFi (4 vòng cung)
        center_x = 12
        center_y = 18
        
        # Điểm trung tâm
        painter.drawEllipse(center_x - 2, center_y - 2, 4, 4)
        
        # Các vòng tín hiệu (4 mức)
        if connected:
            max_arc = strength
        else:
            max_arc = 0  # Không vẽ vòng nào nếu không kết nối
        
        # Vẽ các vòng cung theo cường độ tín hiệu
        for i in range(1, 5):
            pen = painter.pen()
            if i <= max_arc:
                pen.setColor(color)
            else:
                pen.setColor(QColor(220, 220, 220, 100))  # Nhạt cho các vòng không có tín hiệu
            
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            # Vẽ vòng cung
            radius = i * 4
            painter.drawArc(center_x - radius, center_y - radius, radius * 2, radius * 2, 0, -180 * 16)
        
        painter.end()
        return pixmap

    def _get_network_info(self):
        """
        Lấy thông tin mạng WiFi đang kết nối
        
        Returns:
            tuple: (connected, ssid, speed, strength, ip)
        """
        try:
            # Kiểm tra kết nối mạng
            connected = False
            ssid = "Không có kết nối"
            speed = "0 Mbps"
            strength = 0
            ip = "Không có"
            
            # Kiểm tra kết nối internet bằng cách ping Google DNS
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=1)
                connected = True
            except OSError:
                connected = False
                return (connected, ssid, speed, strength, ip)
            
            # Lấy thông tin IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                ip = "Không xác định"
            
            # Lấy thông tin WiFi (Windows)
            if platform.system() == "Windows":
                try:
                    # Chạy lệnh netsh để lấy thông tin WiFi
                    output = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8')
                    
                    # Tìm tên SSID từ kết quả
                    ssid_match = re.search(r"SSID\s+:\s+(.*)", output)
                    if ssid_match:
                        ssid = ssid_match.group(1).strip()
                    
                    # Tìm tốc độ kết nối
                    speed_match = re.search(r"Receive rate \(Mbps\)\s+:\s+(.*)", output)
                    if speed_match:
                        speed = f"{speed_match.group(1).strip()} Mbps"
                    
                    # Tìm cường độ tín hiệu
                    signal_match = re.search(r"Signal\s+:\s+(\d+)%", output)
                    if signal_match:
                        signal_percent = int(signal_match.group(1))
                        # Chuyển đổi phần trăm sang mức từ 0-4
                        if signal_percent < 25:
                            strength = 1
                        elif signal_percent < 50:
                            strength = 2
                        elif signal_percent < 75:
                            strength = 3
                        else:
                            strength = 4
                except:
                    pass
            # Linux và MacOS
            elif platform.system() in ["Linux", "Darwin"]:
                pass
            
            return (connected, ssid, speed, strength, ip)
            
        except Exception as e:
            logger.error(f"Error getting network info: {str(e)}")
            return (False, "Lỗi", "0 Mbps", 0, "Lỗi")