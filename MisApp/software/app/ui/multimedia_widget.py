import sys
import os
import time
import math
import threading
import json
import urllib.request
import urllib.parse
import random
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QSlider, QFrame, QSizePolicy, QStackedWidget, QProgressBar,
                           QGraphicsDropShadowEffect, QListWidget, QListWidgetItem,
                           QLineEdit, QComboBox, QScrollArea, QGridLayout, QMessageBox,
                           QMenu, QAction, QApplication)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QRectF, QPoint, QPropertyAnimation, QEasingCurve, QRect, QObject, QThread
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap, QPainter, QPainterPath, QBrush, QPen, QLinearGradient, QRadialGradient, QImage, QTransform, QFontMetrics, QCursor

from ..utils import config, logger
from ..models.multimedia import MultimediaService

class AlbumArtWidget(QWidget):
    """Widget for displaying album artwork with a spinning disc animation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFixedSize(300, 300)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        self.rotation_angle = 0
        self.spinning = False
        self.disc_speed = 0.5  # Degrees per frame
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_rotation)
        
        # Album art image
        self.album_image = None
        self.default_album_image = self._create_default_album_art()
        self.default_vinyl_overlay = self._create_vinyl_overlay()
        
        # Current track metadata
        self.track_metadata = None
        
        # Set up hover effects
        self.setMouseTracking(True)
        self.hover = False
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
    
    def _create_default_album_art(self):
        """Create a default album art image."""
        size = 300
        image = QPixmap(size, size)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        gradient = QRadialGradient(size/2, size/2, size/2)
        gradient.setColorAt(0, QColor("#2D2D2D"))  
        gradient.setColorAt(0.5, QColor("#1A1A1A"))
        gradient.setColorAt(0.9, QColor("#333333")) 
        gradient.setColorAt(1, QColor("#0D0D0D")) 
        
        # Draw circular background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(0, 0, size, size)
        
        painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
        
        # Draw more convincing vinyl grooves at varying distances
        groove_spacing = [5, 8, 12, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 110, 120, 130, 140]
        for i in groove_spacing:
            painter.drawEllipse(size//2 - i, size//2 - i, i*2, i*2)
        
        center_size = 120  
        
        # Create a subtle gradient for the label
        label_gradient = QRadialGradient(size/2, size/2, center_size/2)
        label_gradient.setColorAt(0, QColor("#252525"))  
        label_gradient.setColorAt(0.8, QColor("#1A1A1A"))  
        label_gradient.setColorAt(1, QColor("#151515"))  
        
        painter.setBrush(QBrush(label_gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))  
        
        center_x = int(size//2 - center_size/2)
        center_y = int(size//2 - center_size/2)
        painter.drawEllipse(center_x, center_y, center_size, center_size)
        
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
        painter.setBrush(Qt.NoBrush)
        
        ring_x = int(size//2 - center_size/2 - 3)
        ring_y = int(size//2 - center_size/2 - 3)
        ring_size = int(center_size + 6)
        painter.drawEllipse(ring_x, ring_y, ring_size, ring_size)
        
        # Add improved text styling to the label
        # "MIS" text
        painter.setPen(QPen(QColor(220, 220, 220, 200), 1)) 
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        text_x = int(size/2 - 50)
        text_y = int(size/2 - 30)
        painter.drawText(QRectF(text_x, text_y, 100, 25), Qt.AlignCenter, "MIS")
        
        # "Assistant" text
        painter.setPen(QPen(QColor(180, 180, 180, 180), 1))
        painter.setFont(QFont("Arial", 10))
        # Fix: Use precise integer coordinates for QRectF
        assist_x = int(size/2 - 50)
        assist_y = int(size/2)
        painter.drawText(QRectF(assist_x, assist_y, 100, 20), Qt.AlignCenter, "Assistant")
        
        # Draw center hole
        painter.setBrush(QBrush(QColor("#000000")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(size//2 - 8, size//2 - 8, 16, 16)
        
        painter.end()
        return image
    
    def _create_vinyl_overlay(self):
        """Create a vinyl overlay with realistic lighting effects."""
        size = 300
        overlay = QPixmap(size, size)
        overlay.fill(Qt.transparent)
        
        painter = QPainter(overlay)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        
        gradient = QRadialGradient(size/2, size/2, size/2)
        gradient.setColorAt(0, QColor(255, 255, 255, 20)) 
        gradient.setColorAt(0.6, QColor(255, 255, 255, 10))  
        gradient.setColorAt(1, QColor(255, 255, 255, 0)) 
        
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(0, 0, size, size)
        
        # Add a subtle edge highlight
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1)) 
        painter.drawEllipse(2, 2, size-4, size-4)
        
        painter.end()
        return overlay
    
    def set_track(self, metadata):
        """Set the track metadata and album art."""
        self.track_metadata = metadata
        
        if metadata and 'cover_url' in metadata and metadata['cover_url']:
            # Try to load album art from URL or local file
            try:
                if os.path.isfile(metadata['cover_url']):
                    # Local file
                    self.album_image = QPixmap(metadata['cover_url'])
                else:
                    # URL - download and create QPixmap
                    import urllib.request
                    from io import BytesIO
                    
                    response = urllib.request.urlopen(metadata['cover_url'])
                    data = response.read()
                    image = QPixmap()
                    image.loadFromData(data)
                    self.album_image = image
                
                # Ensure the image is circular with vinyl effects
                self.album_image = self._create_circular_image(self.album_image)
                
            except Exception as e:
                logger.error(f"Error loading album art: {str(e)}")
                self.album_image = self.default_album_image
        else:
            # Use default album art
            self.album_image = self.default_album_image
        
        # Trigger update
        self.update()
    
    def _create_circular_image(self, pixmap):
        """Create a circular version of the album art with vinyl styling."""
        if pixmap.isNull():
            return self.default_album_image
            
        # Create a circular mask
        target_size = self.width()
        
        # Scale the pixmap to target size with proper aspect ratio
        pixmap = pixmap.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Create a circular mask
        result = QPixmap(target_size, target_size)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # First create a clipping path for the entire disc to fix artifacts around edges
        disc_path = QPainterPath()
        disc_path.addEllipse(QRectF(0, 0, target_size, target_size))
        painter.setClipPath(disc_path)
        
        # Draw vinyl disc background first (now with clipping)
        painter.drawPixmap(0, 0, self.default_album_image)
        
        # Create center label area (for album art)
        center_size = 200  # Diameter of the center label
        center_x = int((target_size - center_size) / 2)
        center_y = int((target_size - center_size) / 2)
        
        # Draw the album art in the center label area (add second clipping path)
        path = QPainterPath()
        ellipse_rect = QRectF(center_x, center_y, center_size, center_size)
        path.addEllipse(ellipse_rect)
        painter.setClipPath(path)
        
        # Calculate position to center the album art
        x_pos = int((target_size - pixmap.width()) / 2)
        y_pos = int((target_size - pixmap.height()) / 2)
        
        point = QPoint(x_pos, y_pos)
        painter.drawPixmap(point, pixmap)
        
        painter.setClipPath(disc_path) 
        
        # Draw vinyl overlay effects
        painter.drawPixmap(0, 0, self.default_vinyl_overlay)
        
        # Draw center hole
        painter.setBrush(QBrush(QColor("#000000")))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawEllipse(target_size//2 - 8, target_size//2 - 8, 16, 16)
        
        painter.end()
        return result
    
    def start_spinning(self):
        """Start the spinning animation."""
        if not self.spinning:
            self.spinning = True
            # Use a smoother animation with more frequent updates
            self.animation_timer.start(16)  # ~60 fps
    
    def stop_spinning(self):
        """Stop the spinning animation."""
        if self.spinning:
            self.spinning = False
            self.animation_timer.stop()
    
    def toggle_spinning(self):
        """Toggle the spinning animation."""
        if self.spinning:
            self.stop_spinning()
        else:
            self.start_spinning()
    
    def _update_rotation(self):
        """Update the rotation angle for the spinning animation."""
        self.rotation_angle = (self.rotation_angle + self.disc_speed) % 360
        self.update()
    
    def paintEvent(self, event):
        """Paint the album art with rotation animation."""
        if not self.album_image:
            self.album_image = self.default_album_image
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clear the background first to prevent artifacts
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        
        # Create a clipping path to ensure nothing is drawn outside the circular disc
        circular_path = QPainterPath()
        circular_path.addEllipse(QRectF(0, 0, self.width(), self.height()))
        painter.setClipPath(circular_path)
        
        # Get the center of the widget
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Save current transformation
        painter.save()
        
        # Translate to center, rotate, then translate back
        painter.translate(center_x, center_y)
        painter.rotate(self.rotation_angle)
        painter.translate(-center_x, -center_y)
        
        # Draw the album art
        painter.drawPixmap(0, 0, self.album_image)
        
        # Restore transformation
        painter.restore()
        
        # If hovering and not spinning, draw a play overlay
        if self.hover and not self.spinning:
            # Draw semi-transparent overlay
            painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, self.width(), self.height())
            
            # Draw play icon
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            path = QPainterPath()
            # Convert float coordinates to integers
            int_center_x = int(center_x)
            int_center_y = int(center_y)
            path.moveTo(int_center_x - 15, int_center_y - 20)
            path.lineTo(int_center_x + 25, int_center_y)
            path.lineTo(int_center_x - 15, int_center_y + 20)
            path.closeSubpath()
            painter.drawPath(path)
    
    def enterEvent(self, event):
        """Handle mouse enter event."""
        self.hover = True
        self.update()
    
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        self.hover = False
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.LeftButton:
            self.toggle_spinning()
            
            # Emit play/pause signal if needed
            if hasattr(self.parent(), 'play_pause_clicked'):
                self.parent().play_pause_clicked.emit()

class PlaylistWidget(QWidget):
    """Widget for displaying and managing playlists with modern styling."""
    
    # Define signals
    track_selected = pyqtSignal(int)  # Track index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create playlist title with enhanced styling
        title_label = QLabel("Danh sách phát")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1E3A8A;
            padding: 5px 0;
            border-bottom: 2px solid #3B82F6;
        """)
        
        # Create track info section - display current playing track with details
        self.track_info_container = QWidget()
        track_info_layout = QVBoxLayout(self.track_info_container)
        track_info_layout.setContentsMargins(8, 8, 8, 8)
        track_info_layout.setSpacing(5)
        
        # Playing status
        self.status_label = QLabel("Không có bài hát nào đang phát")
        self.status_label.setStyleSheet("""
            font-size: 13px;
            color: #3B82F6;
            font-weight: bold;
        """)
        
        # Title with ellipsis for long text
        self.title_label = QLabel("--")
        self.title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #111827;
        """)
        self.title_label.setWordWrap(True)
        
        # Artist
        self.artist_label = QLabel("--")
        self.artist_label.setStyleSheet("""
            font-size: 14px;
            color: #4B5563;
        """)
        self.artist_label.setWordWrap(True)
        
        # Album
        self.album_label = QLabel("--")
        self.album_label.setStyleSheet("""
            font-size: 12px;
            color: #6B7280;
            font-style: italic;
        """)
        
        # Add image to the track info area
        self.album_image_label = QLabel()
        self.album_image_label.setAlignment(Qt.AlignCenter)
        self.album_image_label.setMinimumSize(200, 150)  # Set suitable size for the image
        
        # Load the default image
        image_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'images', 'user_medi.jpg'
        )
        
        if os.path.exists(image_path):
            # Load and scale the image
            pixmap = QPixmap(image_path)
            pixmap = pixmap.scaled(900, 850, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Set the pixmap to the label
            self.album_image_label.setPixmap(pixmap)
            
            # Add shadow effect with thicker blur
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)  # Tăng blurRadius để viền bóng dày hơn
            shadow.setXOffset(8)      # Dịch chuyển bóng xa hơn theo trục X
            shadow.setYOffset(8)      # Dịch chuyển bóng xa hơn theo trục Y
            shadow.setColor(QColor(0, 0, 0, 150))  # Màu đen với độ trong suốt vừa phải
            self.album_image_label.setGraphicsEffect(shadow)
            
            logger.info(f"Loaded user media image with thicker shadow from: {image_path}")
        else:
            # Create a placeholder image if the file doesn't exist
            self.album_image_label.setText("Không có ảnh")
            self.album_image_label.setStyleSheet("""
                background-color: #E5E7EB;
                border-radius: 8px;
                color: #6B7280;
                font-style: italic;
            """)
            logger.warning(f"User media image not found at: {image_path}")
        
        # Add to layout
        track_info_layout.addWidget(self.status_label)
        track_info_layout.addWidget(self.title_label)
        track_info_layout.addWidget(self.artist_label)
        track_info_layout.addWidget(self.album_label)
        track_info_layout.addWidget(self.album_image_label)  # Add the image to the layout
        
        # Add a divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("background-color: #E5E7EB; max-height: 1px;")
        
        # Style the track info container
        self.track_info_container.setStyleSheet("""
            background-color: #F3F4F6;
            border-radius: 8px;
            border: 1px solid #E5E7EB;
        """)
        
        # Create playlist list widget with modern styling
        self.playlist = QListWidget()
        self.playlist.setStyleSheet("""
            QListWidget {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                border-bottom: 1px solid #F3F4F6;
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:selected {
                background-color: #EFF6FF;
                color: #1D4ED8;
                border-left: 3px solid #3B82F6;
            }
            QListWidget::item:hover {
                background-color: #F3F4F6;
            }
        """)
        self.playlist.setAlternatingRowColors(True)
        self.playlist.itemClicked.connect(self._on_item_clicked)
        
        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(self.track_info_container)
        layout.addWidget(divider)
        layout.addWidget(self.playlist, 1)  # Give playlist stretch factor
        
        # Set minimum width
        self.setMinimumWidth(250)
    
    def set_track_info(self, metadata):
        """Set track information from metadata."""
        if metadata:
            # Update status
            self.status_label.setText("Đang phát")
            
            # Update title - ensure we're showing the complete title
            title = metadata.get('title', 'Unknown Title')
            self.title_label.setText(title)
            
            # Update artist and album
            self.artist_label.setText(metadata.get('artist', 'Unknown Artist'))
            self.album_label.setText(metadata.get('album', 'Unknown Album'))
            
            # Make sure the title is fully visible with proper word wrapping
            self.title_label.setWordWrap(True)
            self.artist_label.setWordWrap(True)
        else:
            # Reset labels for no track
            self.status_label.setText("Không có bài hát nào đang phát")
            self.title_label.setText("--")
            self.artist_label.setText("--")
            self.album_label.setText("--")
    
    def set_playlist(self, tracks, current_index=-1):
        """Set the playlist items with modern styling."""
        # Clear current items
        self.playlist.clear()
        
        # Add tracks to playlist with improved display
        for i, track in enumerate(tracks):
            title = track.get('title', 'Unknown Title')
            artist = track.get('artist', 'Unknown Artist')
            
            # Create a widget for each item for better styling
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 3, 5, 3)
            item_layout.setSpacing(2)
            
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                font-weight: bold;
                color: #111827;
                font-size: 13px;
            """)
            title_label.setWordWrap(True)
            
            artist_label = QLabel(artist)
            artist_label.setStyleSheet("""
                color: #6B7280;
                font-size: 11px;
            """)
            artist_label.setWordWrap(True)
            
            item_layout.addWidget(title_label)
            item_layout.addWidget(artist_label)
            
            # Create list item
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            
            # Set current track with different style
            if i == current_index:
                title_label.setStyleSheet("""
                    font-weight: bold;
                    color: #1D4ED8;
                    font-size: 13px;
                """)
                artist_label.setStyleSheet("""
                    color: #3B82F6;
                    font-size: 11px;
                """)
                
                # Also update the track info section
                self.set_track_info(track)
            
            self.playlist.addItem(item)
            self.playlist.setItemWidget(item, item_widget)
    
    def set_current_track(self, index):
        """Highlight the current track in the playlist with improved styling."""
        current_track = None
        
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            item_widget = self.playlist.itemWidget(item)
            
            if item_widget:
                title_label = item_widget.findChild(QLabel)
                artist_label = None
                
                # Get the artist label (second label)
                for child in item_widget.children():
                    if isinstance(child, QLabel) and child != title_label:
                        artist_label = child
                        break
                
                if i == index:
                    # Current track styling
                    if title_label:
                        title_label.setStyleSheet("""
                            font-weight: bold;
                            color: #1D4ED8;
                            font-size: 13px;
                        """)
                    if artist_label:
                        artist_label.setStyleSheet("""
                            color: #3B82F6;
                            font-size: 11px;
                        """)
                    item.setSelected(True)
                    
                    # Save current track data to update track info section
                    current_track = {
                        'title': title_label.text() if title_label else 'Unknown Title',
                        'artist': artist_label.text() if artist_label else 'Unknown Artist',
                        'album': ''  # We might not have this info in the item widget
                    }
                else:
                    # Regular track styling
                    if title_label:
                        title_label.setStyleSheet("""
                            font-weight: bold;
                            color: #111827;
                            font-size: 13px;
                        """)
                    if artist_label:
                        artist_label.setStyleSheet("""
                            color: #6B7280;
                            font-size: 11px;
                        """)
                    item.setSelected(False)
        
        # Update track info if we found the current track
        if current_track:
            self.set_track_info(current_track)
        
        # Scroll to the current item
        if 0 <= index < self.playlist.count():
            self.playlist.scrollToItem(self.playlist.item(index))
    
    def _on_item_clicked(self, item):
        """Handle item click event to select a track."""
        index = self.playlist.row(item)
        self.track_selected.emit(index)


class PlaybackControlsWidget(QWidget):
    """Widget for playback controls with modern styling."""
    
    # Define signals
    play_pause_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    volume_changed = pyqtSignal(float)
    position_changed = pyqtSignal(int)
    loop_clicked = pyqtSignal()  # New signal for loop button
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Current time and total duration with improved styling
        time_layout = QHBoxLayout()
        time_layout.setSpacing(8)
        
        self.current_time_label = QLabel("0:00.00")
        self.current_time_label.setStyleSheet("""
            color: #4B5563;
            font-size: 12px;
            font-weight: 500;
            min-width: 55px;
        """)
        
        self.total_time_label = QLabel("0:00.00")
        self.total_time_label.setStyleSheet("""
            color: #4B5563;
            font-size: 12px;
            font-weight: 500;
            min-width: 55px;
        """)
        
        # Seek bar with improved styling
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 100)
        self.position_slider.setValue(0)
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #E5E7EB;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3B82F6;
                border: 2px solid #2563EB;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #3B82F6);
                border-radius: 3px;
            }
            QSlider::handle:horizontal:hover {
                background: #1D4ED8;
                border: 2px solid #1E40AF;
            }
        """)
        self.position_slider.sliderReleased.connect(self._on_position_slider_released)
        self.position_slider.sliderMoved.connect(self._on_position_slider_moved)
        self.position_slider.valueChanged.connect(self._on_position_slider_value_changed)
        self.position_slider.sliderPressed.connect(self._on_position_slider_pressed)
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.position_slider, 1)
        time_layout.addWidget(self.total_time_label)
        
        # Buttons layout with better spacing
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        buttons_layout.setContentsMargins(20, 5, 20, 5)
        
        # Create modern control buttons
        self.previous_button = QPushButton()
        self.previous_button.setFixedSize(45, 45)
        self.previous_button.setToolTip("Bài trước")
        self.previous_button.setCursor(Qt.PointingHandCursor)
        self.previous_button.clicked.connect(self.previous_clicked.emit)
        
        self.play_pause_button = QPushButton()
        self.play_pause_button.setFixedSize(60, 60)
        self.play_pause_button.setToolTip("Phát/Tạm dừng")
        self.play_pause_button.setCursor(Qt.PointingHandCursor)
        self.play_pause_button.clicked.connect(self.play_pause_clicked.emit)
        
        self.next_button = QPushButton()
        self.next_button.setFixedSize(45, 45)
        self.next_button.setToolTip("Bài tiếp theo")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(self.next_clicked.emit)
        
        self.stop_button = QPushButton()
        self.stop_button.setFixedSize(45, 45)
        self.stop_button.setToolTip("Dừng phát")
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        
        # Add loop button
        self.loop_button = QPushButton()
        self.loop_button.setFixedSize(45, 45)
        self.loop_button.setToolTip("Phát lại")
        self.loop_button.setCursor(Qt.PointingHandCursor)
        self.loop_button.clicked.connect(self.loop_clicked.emit)
        self.loop_button.setCheckable(True)  # Make it toggleable
        
        # Set button icons with improved styling
        self._setup_button_icons()
        
        # Add buttons to layout with proper arrangement
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.previous_button)
        buttons_layout.addWidget(self.play_pause_button)
        buttons_layout.addWidget(self.next_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.loop_button)  # Add loop button
        buttons_layout.addStretch()
        
        # Volume control with improved styling
        volume_layout = QHBoxLayout()
        volume_layout.setContentsMargins(15, 0, 15, 0)
        volume_layout.setSpacing(10)
        
        # Volume icon
        volume_icon = QLabel()
        volume_pixmap = self._create_volume_icon()
        volume_icon.setPixmap(volume_pixmap)
        volume_icon.setFixedSize(20, 20)
        
        # Volume slider with improved styling
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #E5E7EB;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3B82F6;
                border: 1px solid #2563EB;
                width: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #60A5FA;
                border-radius: 2px;
            }
        """)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        
        # Volume percentage label
        self.volume_label = QLabel("50%")
        self.volume_label.setStyleSheet("""
            color: #4B5563;
            font-size: 12px;
            min-width: 30px;
        """)
        
        volume_layout.addWidget(volume_icon)
        volume_layout.addWidget(self.volume_slider, 1)
        volume_layout.addWidget(self.volume_label)
        
        # Add all layouts to main layout
        layout.addLayout(time_layout)
        layout.addLayout(buttons_layout)
        layout.addLayout(volume_layout)
        
        # Set initial state
        self.set_playing(False)
    
    def _setup_button_icons(self):
        """Set up button icons with modern design."""
        resources_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'icons'
        )
        
        # Check if icon files exist
        previous_icon_path = os.path.join(resources_dir, 'previous.png')
        play_icon_path = os.path.join(resources_dir, 'play.png')
        pause_icon_path = os.path.join(resources_dir, 'pause.png')
        next_icon_path = os.path.join(resources_dir, 'next.png')
        stop_icon_path = os.path.join(resources_dir, 'stop.png')
        loop_icon_path = os.path.join(resources_dir, 'loop.png')  # Add loop icon path
        
        # Create icons directory if it doesn't exist
        os.makedirs(resources_dir, exist_ok=True)
        
        # Previous button
        if os.path.exists(previous_icon_path):
            self.previous_button.setIcon(QIcon(previous_icon_path))
        else:
            prev_icon = self._create_previous_icon()
            self.previous_button.setIcon(QIcon(prev_icon))
        
        # Play/Pause button
        if os.path.exists(play_icon_path):
            self.play_icon = QIcon(play_icon_path)
        else:
            self.play_icon = QIcon(self._create_play_icon())
            
        if os.path.exists(pause_icon_path):
            self.pause_icon = QIcon(pause_icon_path)
        else:
            self.pause_icon = QIcon(self._create_pause_icon())
        
        # Set initial icon
        self.play_pause_button.setIcon(self.play_icon)
        
        # Next button
        if os.path.exists(next_icon_path):
            self.next_button.setIcon(QIcon(next_icon_path))
        else:
            next_icon = self._create_next_icon()
            self.next_button.setIcon(QIcon(next_icon))
        
        # Stop button
        if os.path.exists(stop_icon_path):
            self.stop_button.setIcon(QIcon(stop_icon_path))
        else:
            self.stop_icon = QIcon(self._create_stop_icon())
            self.stop_button.setIcon(QIcon(self.stop_icon))
            
        # Loop button
        if os.path.exists(loop_icon_path):
            self.loop_button.setIcon(QIcon(loop_icon_path))
        else:
            loop_icon = self._create_loop_icon()
            self.loop_button.setIcon(QIcon(loop_icon))
        
        # Set icon sizes
        self.previous_button.setIconSize(QSize(25, 25))
        self.play_pause_button.setIconSize(QSize(35, 35))
        self.next_button.setIconSize(QSize(25, 25))
        self.stop_button.setIconSize(QSize(25, 25))
        self.loop_button.setIconSize(QSize(25, 25))  # Set loop icon size
        
        # Set button styles
        button_style = """
            QPushButton {
                background-color: #feffff;
                border-radius: %dpx;
                border: none;
            }
            QPushButton:hover {
                background-color: #eaeef7;
            }
            QPushButton:pressed {
                background-color: #eaeef7;
            }
            QPushButton:disabled {
                background-color: #d5e9ff;
            }
            QPushButton:checked {
                background-color: #3B82F6;
            }
            QPushButton:checked:hover {
                background-color: #2563EB;
            }
        """
        
        self.previous_button.setStyleSheet(button_style % 22)
        self.play_pause_button.setStyleSheet(button_style % 30)
        self.next_button.setStyleSheet(button_style % 22)
        self.stop_button.setStyleSheet(button_style % 22)
        self.loop_button.setStyleSheet(button_style % 22)  # Set loop button style
    
    def _create_previous_icon(self):
        """Create a previous track icon."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Draw previous icon (two triangles)
        path = QPainterPath()
        path.moveTo(18, 6)
        path.lineTo(18, 18)
        path.lineTo(10, 12)
        path.closeSubpath()
        painter.drawPath(path)
        
        path = QPainterPath()
        path.moveTo(10, 6)
        path.lineTo(10, 18)
        path.lineTo(2, 12)
        path.closeSubpath()
        painter.drawPath(path)
        
        painter.end()
        return pixmap
    
    def _create_play_icon(self):
        """Create a play icon."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Draw play triangle
        path = QPainterPath()
        path.moveTo(10, 6)
        path.lineTo(26, 16)
        path.lineTo(10, 26)
        path.closeSubpath()
        painter.drawPath(path)
        
        painter.end()
        return pixmap
    
    def _create_pause_icon(self):
        """Create a pause icon."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Draw pause bars
        painter.drawRect(10, 6, 5, 20)
        painter.drawRect(18, 6, 5, 20)
        
        painter.end()
        return pixmap
    
    def _create_next_icon(self):
        """Create a next track icon."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Draw next icon (two triangles)
        path = QPainterPath()
        path.moveTo(6, 6)
        path.lineTo(14, 12)
        path.lineTo(6, 18)
        path.closeSubpath()
        painter.drawPath(path)
        
        path = QPainterPath()
        path.moveTo(14, 6)
        path.lineTo(22, 12)
        path.lineTo(14, 18)
        path.closeSubpath()
        painter.drawPath(path)
        
        painter.end()
        return pixmap
    
    def _create_stop_icon(self):
        """Create a stop icon."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Draw stop square
        painter.drawRect(6, 6, 12, 12)
        
        painter.end()
        return pixmap
    
    def _create_volume_icon(self):
        """Create a volume icon."""
        size = 24
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw speaker shape
        painter.setPen(QPen(QColor('#4B5563'), 1.5))
        painter.setBrush(QBrush(QColor('#4B5563')))
        
        # Draw speaker base
        painter.drawRect(4, 8, 5, 8)
        
        # Draw speaker cone
        path = QPainterPath()
        path.moveTo(9, 8)
        path.lineTo(14, 4)
        path.lineTo(14, 20)
        path.lineTo(9, 16)
        path.closeSubpath()
        painter.drawPath(path)
        
        # Draw sound waves
        painter.setPen(QPen(QColor('#4B5563'), 1.5, Qt.SolidLine, Qt.RoundCap))
        # First wave
        painter.drawArc(13, 8, 6, 8, -40 * 16, 80 * 16)
        # Second wave
        painter.drawArc(13, 6, 10, 12, -40 * 16, 80 * 16)
        
        painter.end()
        return pixmap
    
    def set_playing(self, is_playing):
        """Set playing/paused state."""
        if is_playing:
            self.play_pause_button.setIcon(self.pause_icon)
            self.play_pause_button.setToolTip("Tạm dừng")
        else:
            self.play_pause_button.setIcon(self.play_icon)
            self.play_pause_button.setToolTip("Phát")
    
    def update_position(self, position, duration):
        """Update position slider and time labels."""
        # Prevent signal loops
        self.position_slider.blockSignals(True)
        
        # Convert seconds to MM:SS.CC format
        current_time = self._format_time(position)
        total_time = self._format_time(duration)
        
        # Update labels
        self.current_time_label.setText(current_time)
        self.total_time_label.setText(total_time)
        
        # Update slider value (as percentage)
        if duration > 0:
            percentage = int((position / duration) * 100)
            # Chỉ cập nhật slider nếu không đang kéo
            if not self.position_slider.isSliderDown():
                self.position_slider.setValue(percentage)
        else:
            self.position_slider.setValue(0)
        
        self.position_slider.blockSignals(False)
    
    def set_volume(self, volume):
        """Set volume slider value (0-100)."""
        self.volume_slider.blockSignals(True)
        volume_percent = int(volume * 100)
        self.volume_slider.setValue(volume_percent)
        self.volume_label.setText(f"{volume_percent}%")
        self.volume_slider.blockSignals(False)
    
    def _format_time(self, seconds):
        """Format seconds as MM:SS.CC (with hundredths of seconds)."""
        # Round to 2 decimal places for hundredths display
        seconds = round(seconds, 2)
        minutes = int(seconds // 60)
        seconds_part = seconds % 60
        
        # Format with 2 decimal places for hundredths
        if seconds_part < 10:
            return f"{minutes}:0{seconds_part:.2f}"
        else:
            return f"{minutes}:{seconds_part:.2f}"
    
    def _on_volume_changed(self, value):
        """Handle volume slider value change."""
        self.volume_label.setText(f"{value}%")
        self.volume_changed.emit(value / 100.0)  # Convert to 0-1 range
    
    def _on_position_slider_released(self):
        """Handle position slider value change on release."""
        # Lấy giá trị hiện tại của thanh trượt
        value = self.position_slider.value()
        
        # Đánh dấu thời điểm seek để tránh seek liên tục
        self._last_seek_time = time.time()
        self._last_seek_value = value
        
        # Gửi tín hiệu thay đổi vị trí
        self.position_changed.emit(value)
        
        # Khôi phục style gốc cho label
        if hasattr(self, '_original_label_style'):
            self.current_time_label.setStyleSheet(self._original_label_style)
    
    def _on_position_slider_moved(self, value):
        """Handle position slider value change while dragging."""
        # Kiểm tra xem có cần throttle (giới hạn tần suất cập nhật) không
        current_time = time.time()
        if hasattr(self, '_last_slider_update') and (current_time - self._last_slider_update < 0.05):
            # Quá nhanh, bỏ qua để giảm tải
            return
            
        # Cập nhật thời gian cập nhật gần nhất
        self._last_slider_update = current_time
        
        # Update the time label only during dragging, without changing actual playback
        duration = 0
        position = 0
        
        # Get parent widget (MultiMediaWidget) if available
        parent = self.parent()
        if parent and hasattr(parent, "multimedia_service"):
            multimedia_service = parent.multimedia_service
            
            # Tìm duration từ nhiều nguồn khác nhau
            if hasattr(multimedia_service, 'audio_player') and multimedia_service.audio_player:
                if hasattr(multimedia_service.audio_player, 'track_duration'):
                    duration = multimedia_service.audio_player.track_duration
            
            if duration <= 0 and hasattr(multimedia_service, 'track_duration'):
                duration = multimedia_service.track_duration
            
            if duration <= 0 and hasattr(multimedia_service, '_get_current_track_info'):
                # Thử lấy từ metadata
                try:
                    track_info = multimedia_service._get_current_track_info()
                    if track_info and 'duration' in track_info:
                        duration = track_info['duration']
                except:
                    pass
            
            # Sử dụng giá trị mặc định nếu không tìm thấy
            if duration <= 0:
                duration = 100.0
                
            # Calculate position based on percentage
            position = (value / 100.0) * duration
            
            # Làm tròn vị trí để tránh quá nhiều số thập phân
            position = round(position, 2)
                
        # Update time display while dragging
        current_time = self._format_time(position)
        total_time = self._format_time(duration)
        
        # Update both labels để UX nhất quán
        self.current_time_label.setText(current_time)
        
        # Thêm dấu hiệu trực quan để người dùng biết đang kéo
        if not hasattr(self, '_original_label_style'):
            self._original_label_style = self.current_time_label.styleSheet()
        
        self.current_time_label.setStyleSheet("""
            color: #1D4ED8;
            font-size: 12px;
            font-weight: 700;
            min-width: 55px;
        """)
    
    def _on_position_slider_value_changed(self, value):
        """Handle automatic value changes in the position slider."""
        # Only respond to programmatic changes, not user drags
        # (Those are handled by _on_position_slider_moved and _on_position_slider_released)
        if not self.position_slider.isSliderDown():
            # This was a programmatic change, not user interaction
            pass
    
    def _on_position_slider_pressed(self):
        """Handle slider press event to update UI immediately."""
        # Cập nhật thời gian hiển thị ngay khi người dùng bấm vào thanh trượt
        value = self.position_slider.value()
        
        # Tính vị trí thời gian từ phần trăm
        duration = 0
        parent = self.parent()
        if parent and hasattr(parent, "multimedia_service"):
            ms = parent.multimedia_service
            # Thử lấy duration từ nhiều nguồn
            if hasattr(ms, 'track_duration') and ms.track_duration > 0:
                duration = ms.track_duration
            elif hasattr(ms, 'audio_player') and ms.audio_player and hasattr(ms.audio_player, 'track_duration'):
                duration = ms.audio_player.track_duration
            elif hasattr(ms, '_get_current_track_info'):
                try:
                    track_info = ms._get_current_track_info()
                    if track_info and 'duration' in track_info:
                        duration = track_info['duration']
                except:
                    pass
        
        # Sử dụng giá trị mặc định nếu không có
        if duration <= 0:
            duration = 100.0
        
        # Cập nhật hiển thị thời gian
        position = (value / 100.0) * duration
        self.current_time_label.setText(self._format_time(position))
        
        # Thay đổi màu sắc để chỉ ra rằng đang tương tác
        self.current_time_label.setStyleSheet("""
            color: #1D4ED8;
            font-size: 12px;
            font-weight: 700;
            min-width: 55px;
        """)

    def _create_loop_icon(self):
        """Create a loop icon."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.setBrush(Qt.NoBrush)
        
        # Draw loop arrow
        path = QPainterPath()
        # Start from bottom left
        path.moveTo(6, 18)
        # Draw left side curve
        path.cubicTo(6, 12, 6, 6, 12, 6)
        # Draw top curve
        path.cubicTo(18, 6, 18, 12, 18, 12)
        # Draw right side curve
        path.cubicTo(18, 18, 12, 18, 12, 18)
        # Draw arrow head
        path.lineTo(12, 14)
        path.lineTo(8, 18)
        path.lineTo(12, 22)
        path.lineTo(12, 18)
        
        painter.drawPath(path)
        
        painter.end()
        return pixmap


class AudioWaveformWidget(QWidget):
    """Widget for displaying a responsive audio waveform visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set fixed height but expandable width
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Waveform data
        self.waveform_data = []
        self.max_data_points = 100  # Number of bars to show
        self.is_active = False
        self.audio_intensity = 0.5  # Default intensity factor (0.0 to 1.0)
        self.tempo = 0.5  # Music tempo (0.0=slow to 1.0=fast)
        self.beat_phase = 0.0  # Phase for beat visualization
        
        # Color theme with gradient stops
        self.color_themes = {
            "blue": [
                (0, QColor("#60A5FA")),  # Light blue at top
                (0.5, QColor("#3B82F6")),  # Medium blue at middle
                (1, QColor("#1D4ED8"))   # Dark blue at bottom
            ],
            "purple": [
                (0, QColor("#C084FC")),  # Light purple
                (0.5, QColor("#A855F7")), # Medium purple
                (1, QColor("#7E22CE"))   # Dark purple
            ],
            "teal": [
                (0, QColor("#2DD4BF")),  # Light teal
                (0.5, QColor("#14B8A6")), # Medium teal
                (1, QColor("#0F766E"))   # Dark teal
            ],
            "orange": [
                (0, QColor("#FDBA74")),  # Light orange
                (0.5, QColor("#FB923C")), # Medium orange
                (1, QColor("#EA580C"))   # Dark orange
            ],
            "pink": [
                (0, QColor("#FDA4AF")),  # Light pink
                (0.5, QColor("#FB7185")), # Medium pink
                (1, QColor("#E11D48"))   # Dark pink
            ]
        }
        
        # Default color theme
        self.current_theme = "blue"
        self.transition_progress = 0.0  # For smooth color transitions
        self.target_theme = "blue"
        
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_waveform)
        self.animation_timer.setInterval(50)  # Update every 50ms
        
        # Theme transition timer - changes themes every 10 seconds when active
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self._advance_color_theme)
        self.theme_timer.setInterval(10000)  # Change every 10 seconds
        
        # Beat timer for visual beat effects
        self.beat_timer = QTimer(self)
        self.beat_timer.timeout.connect(self._update_beat)
        self.beat_timer.setInterval(500)  # Default beat interval (will adjust based on tempo)
        
        # Generate initial empty waveform
        self._generate_empty_waveform()
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Set background color
        self.setStyleSheet("background-color: transparent;")
    
    def _generate_empty_waveform(self):
        """Generate an empty waveform with minimal movement for inactive state."""
        self.waveform_data = []
        for i in range(self.max_data_points):
            # Generate very small random values for minimal movement
            value = random.uniform(0.05, 0.08)
            self.waveform_data.append(value)
    
    def _generate_active_waveform(self):
        """Generate a new active waveform frame."""
        # Update existing waveform data
        for i in range(len(self.waveform_data)):
            if self.is_active:
                # Generate more dramatic values when active
                base_height = random.uniform(0.2, 0.8)
                
                # Create a pattern where bars in the middle tend to be taller
                position_factor = 1.0 - abs((i - (self.max_data_points / 2)) / (self.max_data_points / 2))
                height = base_height * (0.5 + position_factor * 0.7)
                
                # Apply audio intensity factor to make waveform respond to volume/intensity
                height = height * self.audio_intensity * 1.3
                
                # Apply beat effect - boost heights rhythmically based on beat phase
                beat_influence = math.sin(self.beat_phase + i * 0.2) * 0.2
                height = height * (1.0 + beat_influence * self.tempo)
                
                # Add some randomness for natural effect
                height += random.uniform(-0.1, 0.1)
                
                # Ensure height stays within bounds
                height = max(0.05, min(0.95, height))
                
                # Smooth transitions by blending with previous value
                if i < len(self.waveform_data):
                    prev_height = self.waveform_data[i]
                    # Faster tempo = more responsive waves (less smoothing)
                    smoothing = max(0.5, 0.8 - self.tempo * 0.3)
                    self.waveform_data[i] = prev_height * smoothing + height * (1.0 - smoothing)
            else:
                # Minimal movement for inactive state
                value = random.uniform(0.02, 0.08)
                self.waveform_data[i] = value
    
    def start_animation(self):
        """Start the waveform animation."""
        self.is_active = True
        if not self.animation_timer.isActive():
            self.animation_timer.start()
        
        # Start theme transitions
        if not self.theme_timer.isActive():
            self.theme_timer.start()
        
        # Start beat animation
        self._update_beat_timer()
        if not self.beat_timer.isActive():
            self.beat_timer.start()
    
    def stop_animation(self):
        """Stop the waveform animation."""
        self.is_active = False
        
        # Don't immediately stop the timer, let it fade out
        # We'll just make the waveform less active
        self._generate_empty_waveform()
        self.update()
        
        # Stop the timers after a short delay
        QTimer.singleShot(1000, self._stop_timers)
    
    def _stop_timers(self):
        """Stop all animation timers completely."""
        if not self.is_active:
            if self.animation_timer.isActive():
                self.animation_timer.stop()
            if self.theme_timer.isActive():
                self.theme_timer.stop()
            if self.beat_timer.isActive():
                self.beat_timer.stop()
    
    def _update_waveform(self):
        """Update the waveform data and trigger a repaint."""
        self._generate_active_waveform()
        
        # Update color transition if in progress
        if self.current_theme != self.target_theme:
            self.transition_progress += 0.05
            if self.transition_progress >= 1.0:
                self.current_theme = self.target_theme
                self.transition_progress = 0.0
        
        self.update()
    
    def _advance_color_theme(self):
        """Advance to the next color theme with smooth transition."""
        if not self.is_active:
            return
            
        # Get available themes excluding current
        available_themes = list(self.color_themes.keys())
        if self.current_theme in available_themes:
            available_themes.remove(self.current_theme)
        
        # Set target theme and reset transition progress
        self.target_theme = random.choice(available_themes)
        self.transition_progress = 0.0
    
    def _update_beat(self):
        """Update the beat phase for visual rhythm effects."""
        self.beat_phase += math.pi / 4
        if self.beat_phase > 2 * math.pi:
            self.beat_phase -= 2 * math.pi
    
    def _update_beat_timer(self):
        """Update the beat timer interval based on tempo."""
        # Adjust beat interval based on tempo (faster tempo = faster beats)
        # tempo 0.0 (slow) = 800ms, tempo 1.0 (fast) = 300ms
        beat_interval = 800 - int(self.tempo * 500)
        if self.beat_timer.interval() != beat_interval:
            self.beat_timer.setInterval(beat_interval)
    
    def _get_blended_color(self, pos):
        """Get a color blended between current and target themes."""
        if self.current_theme == self.target_theme or self.transition_progress <= 0:
            # No transition in progress, just return current theme color
            theme_colors = self.color_themes[self.current_theme]
            return self._get_gradient_color(pos, theme_colors)
        
        # Get colors from both themes at the specified position
        current_color = self._get_gradient_color(pos, self.color_themes[self.current_theme])
        target_color = self._get_gradient_color(pos, self.color_themes[self.target_theme])
        
        # Blend colors based on transition progress
        r = int(current_color.red() * (1 - self.transition_progress) + target_color.red() * self.transition_progress)
        g = int(current_color.green() * (1 - self.transition_progress) + target_color.green() * self.transition_progress)
        b = int(current_color.blue() * (1 - self.transition_progress) + target_color.blue() * self.transition_progress)
        
        return QColor(r, g, b)
    
    def _get_gradient_color(self, pos, theme_colors):
        """Get the color at a specific position in the gradient."""
        # Find the two stops that the position falls between
        lower_stop = None
        upper_stop = None
        
        for i, (stop_pos, color) in enumerate(theme_colors):
            if stop_pos > pos:
                upper_stop = (stop_pos, color)
                if i > 0:
                    lower_stop = theme_colors[i-1]
                break
            elif stop_pos == pos:
                return color
        
        # If we're beyond the last stop or before the first, use the boundary colors
        if upper_stop is None:
            return theme_colors[-1][1]
        if lower_stop is None:
            return theme_colors[0][1]
        
        # Interpolate between the two colors
        lower_pos, lower_color = lower_stop
        upper_pos, upper_color = upper_stop
        
        # Calculate the factor for interpolation
        range_size = upper_pos - lower_pos
        if range_size <= 0:
            return lower_color
            
        factor = (pos - lower_pos) / range_size
        
        # Interpolate RGB values
        r = int(lower_color.red() * (1 - factor) + upper_color.red() * factor)
        g = int(lower_color.green() * (1 - factor) + upper_color.green() * factor)
        b = int(lower_color.blue() * (1 - factor) + upper_color.blue() * factor)
        
        return QColor(r, g, b)
    
    def paintEvent(self, event):
        """Paint the waveform visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        
        # Adjust number of bars based on tempo (faster music = more bars)
        if self.is_active:
            # Scale between 60-120 bars based on tempo
            visible_bars = int(60 + self.tempo * 60)
        else:
            visible_bars = 60  # Default for inactive state
        
        # Calculate bar width and spacing
        bar_count = min(visible_bars, len(self.waveform_data))
        
        # Spacing varies by tempo (faster = tighter spacing)
        base_spacing = 4
        tempo_spacing_adjustment = -2 * self.tempo  # Reduce spacing as tempo increases
        spacing = max(1, base_spacing + tempo_spacing_adjustment)
        
        bar_width = max(2, (width - (bar_count - 1) * spacing) / bar_count)
        
        # Draw each bar
        for i in range(bar_count):
            # Calculate index to use from our data array
            data_index = int(i * (self.max_data_points / bar_count))
            if data_index >= len(self.waveform_data):
                data_index = len(self.waveform_data) - 1
                
            # Get the normalized height value (0.0 to 1.0)
            normalized_height = self.waveform_data[data_index]
            
            # Calculate bar height as percentage of widget height (with padding)
            bar_height = int(normalized_height * (height * 0.8))
            
            # Calculate x position
            x = i * (bar_width + spacing)
            
            # Calculate y position (centered vertically)
            y = (height - bar_height) // 2
            
            # Create gradient for the bar
            if self.is_active:
                gradient = QLinearGradient(x, y, x, y + bar_height)
                
                # Dynamic color gradient based on current theme with smooth transitions
                gradient.setColorAt(0, self._get_blended_color(0))
                gradient.setColorAt(0.5, self._get_blended_color(0.5))
                gradient.setColorAt(1, self._get_blended_color(1))
            else:
                gradient = QLinearGradient(x, y, x, y + bar_height)
                gradient.setColorAt(0, QColor("#9CA3AF"))  # Light gray at top
                gradient.setColorAt(1, QColor("#6B7280"))  # Dark gray at bottom
            
            # Draw rounded bar
            path = QPainterPath()
            radius = min(bar_width / 2, 3)  # Rounded corners radius
            path.addRoundedRect(x, y, bar_width, bar_height, radius, radius)
            
            painter.fillPath(path, gradient)
    
    def set_active(self, active):
        """Set the active state of the waveform."""
        if active != self.is_active:
            self.is_active = active
            if active:
                self.start_animation()
            else:
                self.stop_animation()
    
    def update_intensity(self, position, duration):
        """
        Update the audio intensity based on playback position.
        This simulates response to audio amplitude changes.
        """
        if not self.is_active or duration <= 0:
            return
            
        # Calculate a pseudo-intensity based on position
        # This creates a varying intensity that simulates real audio response
        # In a real implementation, this would use actual audio samples/amplitude
        
        # Create a pattern that varies based on position in the track
        position_ratio = position / duration
        base_intensity = 0.5  # Base intensity
        
        # Add variation based on position
        variation = math.sin(position * 4) * 0.2 + math.cos(position * 2.5) * 0.15
        
        # Add some randomness for more natural effect
        random_factor = random.uniform(-0.1, 0.1)
        
        # Calculate final intensity
        intensity = base_intensity + variation + random_factor
        
        # Ensure intensity stays within bounds
        self.audio_intensity = max(0.3, min(1.0, intensity))
        
        # Also update the tempo (rhythm) based on position
        # This simulates faster/slower sections of music
        tempo_variation = (math.sin(position * 0.5) * 0.3) + (math.cos(position * 0.2) * 0.2)
        self.tempo = 0.5 + tempo_variation
        self.tempo = max(0.2, min(0.9, self.tempo))
        
        # Update beat timer interval based on new tempo
        self._update_beat_timer()

class MultiMediaWidget(QWidget):
    """
    Widget for multimedia playback with spinning disc, controls, playlist, and search.
    """
    
    def __init__(self, multimedia_service):
        super().__init__()
        
        # Store reference to the multimedia service
        self.multimedia_service = multimedia_service
        
        # Set up the UI components
        self._setup_ui()
        
        # Connect signals from multimedia service
        self._connect_signals()
        
        # Update initial state
        self.update_playlist()
    
    def _setup_ui(self):
        """Set up the UI components with a professional design."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Content container with shadow effect
        content_container = QWidget()
        content_container.setObjectName("contentContainer")
        content_container.setStyleSheet("""
            QWidget#contentContainer {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        content_container.setGraphicsEffect(shadow)
        
        # Content layout
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(20)
        
        # Header with title and modern styling
        header = QLabel("Trình phát Đa phương tiện")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #1E40AF;
            padding-bottom: 5px;
            border-bottom: 2px solid #3B82F6;
        """)
        header.setAlignment(Qt.AlignCenter)
        
        # Player container with three sections: player, playlist, and search
        player_container = QWidget()
        player_layout = QHBoxLayout(player_container)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(15)
        
        # Left side - Album art and controls
        left_side = QWidget()
        left_layout = QVBoxLayout(left_side)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        # Create proper background for the left side
        left_side.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 8px;
        """)
        
        # Album art with spinning disc
        self.album_art = AlbumArtWidget()
        left_layout.addWidget(self.album_art, 0, Qt.AlignCenter)
        
        # Add audio waveform visualization below the album art
        self.waveform = AudioWaveformWidget()
        left_layout.addWidget(self.waveform)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #3B82F6;
            font-weight: bold;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)
        
        # Playback controls
        self.controls = PlaybackControlsWidget()
        left_layout.addWidget(self.controls)
        
        # Middle - Playlist
        middle_side = QWidget()
        middle_layout = QVBoxLayout(middle_side)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        
        self.playlist = PlaylistWidget()
        middle_layout.addWidget(self.playlist)
        
        # Right side - Search widget
        right_side = QWidget()
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_widget = MediaSearchWidget(self.multimedia_service)
        right_layout.addWidget(self.search_widget)
        
        # Add vertical dividers between sections
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.VLine)
        divider1.setFrameShadow(QFrame.Sunken)
        divider1.setStyleSheet("background-color: #E5E7EB; max-width: 1px;")
        
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.VLine)
        divider2.setFrameShadow(QFrame.Sunken)
        divider2.setStyleSheet("background-color: #E5E7EB; max-width: 1px;")
        
        # Add sections to player container
        player_layout.addWidget(left_side, 3)  # 30% width
        player_layout.addWidget(divider1)
        player_layout.addWidget(middle_side, 3)  # 30% width
        player_layout.addWidget(divider2)
        player_layout.addWidget(right_side, 4)  # 40% width
        
        # Add all elements to content layout
        content_layout.addWidget(header)
        content_layout.addWidget(player_container)
        
        # Add content container to main layout
        main_layout.addWidget(content_container)
        
        # Connect control signals
        self._connect_control_signals()
        
        # Connect search widget signals
        self.search_widget.play_media.connect(self._on_search_play_media)
    
    def _connect_signals(self):
        """Connect signals from multimedia service."""
        # Connect playback signals
        self.multimedia_service.playback_started.connect(self._on_playback_started)
        self.multimedia_service.playback_stopped.connect(self._on_playback_stopped)
        self.multimedia_service.playback_paused.connect(self._on_playback_paused)
        self.multimedia_service.playback_position_changed.connect(self._on_position_changed)
        self.multimedia_service.playback_finished.connect(self._on_playback_finished)
        self.multimedia_service.playback_error.connect(self._on_playback_error)
        self.multimedia_service.metadata_updated.connect(self._on_metadata_updated)
    
    def _connect_control_signals(self):
        """Connect signals from control widgets."""
        # Playback controls
        self.controls.play_pause_clicked.connect(self._on_play_pause_clicked)
        self.controls.previous_clicked.connect(self._on_previous_clicked)
        self.controls.next_clicked.connect(self._on_next_clicked)
        self.controls.stop_clicked.connect(self._on_stop_clicked)
        self.controls.volume_changed.connect(self._on_volume_changed)
        self.controls.position_changed.connect(self._on_seek_position)
        self.controls.loop_clicked.connect(self._on_loop_clicked)  # Connect loop signal
        
        # Playlist
        self.playlist.track_selected.connect(self._on_track_selected)
    
    def _on_playback_started(self, metadata):
        """Handle playback started event."""
        # Set status to "Đang phát" but don't show track details on the left side
        self.status_label.setText("Đang phát")
        
        # Update the playlist's track info section
        self.playlist.set_track_info(metadata)
        
        # Update album art and start spinning animation
        self.album_art.set_track(metadata)
        self.album_art.start_spinning()
        
        # Activate waveform animation
        self.waveform.set_active(True)
        
        # Update playlist selection
        try:
            self.playlist.set_current_track(self.multimedia_service.current_index)
        except AttributeError:
            # Handle case when current_index is not available
            self.playlist.set_current_track(0)
            logger.warning("Could not get current_index from multimedia_service")
        
        # Update control state
        self.controls.set_playing(True)
        
        # Set volume
        volume = self.multimedia_service.get_volume()
        self.controls.set_volume(volume)
    
    def _on_playback_stopped(self):
        """Handle playback stopped event."""
        # Clear status
        self.status_label.setText("")
        
        # Stop disc spinning animation
        self.album_art.stop_spinning()
        
        # Deactivate waveform animation
        self.waveform.set_active(False)
        
        # Reset playlist track info
        self.playlist.set_track_info(None)
        
        # Update control state
        self.controls.set_playing(False)
        
        # Reset position
        self.controls.update_position(0, 0)
    
    def _on_playback_paused(self, is_paused):
        """Handle playback paused/resumed event."""
        if is_paused:
            # Show paused status
            self.status_label.setText("Tạm dừng")
            
            # Pause disc spinning animation
            self.album_art.stop_spinning()
            
            # Pause waveform animation
            self.waveform.set_active(False)
            
            # Update control state
            self.controls.set_playing(False)
        else:
            # Show playing status
            self.status_label.setText("Đang phát")
            
            # Resume disc spinning animation
            self.album_art.start_spinning()
            
            # Resume waveform animation
            self.waveform.set_active(True)
            
            # Update control state
            self.controls.set_playing(True)
    
    def _on_playback_finished(self):
        """Handle playback finished event."""
        # Clear status
        self.status_label.setText("")
        
        # Stop disc spinning animation
        self.album_art.stop_spinning()
        
        # Stop waveform animation
        self.waveform.set_active(False)
        
        # Update control state
        self.controls.set_playing(False)
        
        # Reset playlist track info
        self.playlist.set_track_info(None)
    
    def _on_playback_error(self, error_message):
        """Handle playback error event."""
        # Show error status
        self.status_label.setText("Lỗi")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #EF4444;
            font-weight: bold;
        """)
        
        # Stop disc spinning animation
        self.album_art.stop_spinning()
        
        # Update control state
        self.controls.set_playing(False)
        
        # Update playlist with error message
        error_metadata = {
            'title': f"Lỗi: {error_message}",
            'artist': '',
            'album': ''
        }
        self.playlist.set_track_info(error_metadata)
    
    def _on_metadata_updated(self, metadata):
        """Handle metadata updated event."""
        # Update the playlist's track info section
        self.playlist.set_track_info(metadata)
        
        # Update album art (but don't change spinning state)
        was_spinning = self.album_art.spinning
        self.album_art.set_track(metadata)
        if was_spinning:
            self.album_art.start_spinning()
    
    def _on_play_pause_clicked(self):
        """Handle play/pause button click."""
        # Use is_currently_playing method to determine current state
        if self.multimedia_service.is_currently_playing():
            self.multimedia_service.pause()
        elif hasattr(self.multimedia_service, 'is_paused') and self.multimedia_service.is_paused:
            self.multimedia_service.resume()
        else:
            # No current playback, start playing the first track if available
            if hasattr(self.multimedia_service, 'playlist') and self.multimedia_service.playlist:
                self.multimedia_service.play()
    
    def _on_previous_clicked(self):
        """Handle previous button click."""
        # Use previous_track or play_previous based on what's available
        if hasattr(self.multimedia_service, 'play_previous'):
            self.multimedia_service.play_previous()
        else:
            self.multimedia_service.previous_track()
    
    def _on_next_clicked(self):
        """Handle next button click."""
        # Use next_track or play_next based on what's available
        if hasattr(self.multimedia_service, 'play_next'):
            self.multimedia_service.play_next()
        else:
            self.multimedia_service.next_track()
    
    def _on_stop_clicked(self):
        """Handle stop button click.""" 
        self.multimedia_service.stop()
    
    def _on_volume_changed(self, volume):
        """Handle volume slider change."""
        self.multimedia_service.set_volume(volume)
    
    def _on_seek_position(self, percentage):
        """Handle position slider change."""
        # Kiểm tra xem có phải seek liên tục không (để tránh gửi quá nhiều yêu cầu)
        current_time = time.time()
        if hasattr(self, '_last_seek_request') and (current_time - self._last_seek_request < 0.1):
            # Quá nhanh, bỏ qua để tránh seek liên tục
            return
            
        # Cập nhật thời gian seek gần nhất
        self._last_seek_request = current_time
        
        # Convert percentage to position in seconds
        try:
            # Get the current duration from the multimedia service
            duration = 0
            
            # Kiểm tra audio_player theo nhiều cách
            if hasattr(self.multimedia_service, 'audio_player') and self.multimedia_service.audio_player:
                # Lấy từ audio_player
                audio_player = self.multimedia_service.audio_player
                if hasattr(audio_player, 'track_duration') and audio_player.track_duration > 0:
                    duration = audio_player.track_duration
                    logger.info(f"Got duration from audio_player: {duration}s")
            
            # Nếu vẫn chưa có, thử lấy từ track_duration trực tiếp
            if duration <= 0 and hasattr(self.multimedia_service, 'track_duration'):
                duration = self.multimedia_service.track_duration
                logger.info(f"Got duration from multimedia_service: {duration}s")
            
            # Kiểm tra có duration hợp lệ không
            if duration <= 0:
                # Không tìm thấy duration hợp lệ, thử lấy từ metadata bài hát hiện tại
                if hasattr(self.multimedia_service, '_get_current_track_info'):
                    track_info = self.multimedia_service._get_current_track_info()
                    if track_info and 'duration' in track_info and track_info['duration'] > 0:
                        duration = track_info['duration']
                        logger.info(f"Got duration from track metadata: {duration}s")
            
            # Nếu vẫn chưa có duration, cố gắng ước tính từ vị trí hiện tại
            if duration <= 0 and hasattr(self.multimedia_service, 'get_position'):
                current_pos = self.multimedia_service.get_position()
                # Ước tính duration là 100 lần vị trí hiện tại hoặc ít nhất 60 giây
                duration = max(current_pos * 2, 60.0)
                logger.info(f"Estimated duration from current position: {duration}s")
            
            if duration > 0:
                # Calculate the position in seconds based on percentage
                position = (percentage / 100.0) * duration
                
                # Làm tròn vị trí để tránh quá nhiều số thập phân
                position = round(position, 2)
                
                # Set the position in the multimedia service
                if hasattr(self.multimedia_service, 'set_position'):
                    # Store current playing state
                    was_playing = self.multimedia_service.is_currently_playing()
                    
                    # Set the position
                    result = self.multimedia_service.set_position(position)
                    
                    # Immediately update the UI to reflect the requested position
                    self.controls.update_position(position, duration)
                    
                    # Log success or failure
                    if result:
                        logger.info(f"Seek position set to {position:.2f}s ({percentage}%) of {duration:.2f}s")
                    else:
                        logger.warning(f"Failed to set position to {position:.2f}s")
                else:
                    logger.error("Multimedia service does not have set_position method")
            else:
                # Fallback to using percentage directly with a default duration of 100
                duration = 100.0
                position = percentage
                logger.warning(f"Using fallback method for seeking with percentage: {percentage}%")
                
                if hasattr(self.multimedia_service, 'set_position'):
                    self.multimedia_service.set_position(position)
                
                # Update UI with whatever information we have
                self.controls.update_position(position, duration)
                
        except Exception as e:
            logger.error(f"Error seeking position: {str(e)}")
            # Update UI with default values on error
            self.controls.update_position(0, 100)  # Use default values on error
    
    def _on_track_selected(self, index):
        """Handle track selection from playlist."""
        try:
            # Get the playlist from the service
            if hasattr(self.multimedia_service, 'playlist') and 0 <= index < len(self.multimedia_service.playlist):
                # If service has playlist attribute, use it
                track = self.multimedia_service.playlist[index]
                self.multimedia_service.play(track)
            elif hasattr(self.multimedia_service, 'play_track_at_index'):
                # Alternative method if available
                self.multimedia_service.play_track_at_index(index)
        except Exception as e:
            logger.error(f"Error playing selected track: {str(e)}")
    
    def update_playlist(self):
        """Update the playlist widget with current playlist data."""
        try:
            playlist_data = []
            
            # Get playlist based on available methods
            if hasattr(self.multimedia_service, 'get_playlist') and callable(getattr(self.multimedia_service, 'get_playlist')):
                # Convert file paths to metadata objects
                for path in self.multimedia_service.get_playlist():
                    # Always try to get detailed metadata first - especially important for YouTube files
                    if hasattr(self.multimedia_service, 'get_track_metadata'):
                        track_info = self.multimedia_service.get_track_metadata(path)
                        if track_info:
                            playlist_data.append(track_info)
                        else:
                            # Fallback to basic info
                            info = {
                                'title': os.path.basename(path),
                                'artist': 'Unknown Artist',
                                'file_path': path
                            }
                            playlist_data.append(info)
                    else:
                        # Use basic info if metadata getter not available
                        info = {
                            'title': os.path.basename(path),
                            'artist': 'Unknown Artist',
                            'file_path': path
                        }
                        playlist_data.append(info)
            elif hasattr(self.multimedia_service, 'playlist'):
                # Direct access to playlist if available
                playlist_data = self.multimedia_service.playlist
                
            # Get current index safely
            current_index = -1
            if hasattr(self.multimedia_service, 'current_index'):
                current_index = self.multimedia_service.current_index
            elif hasattr(self.multimedia_service, 'get_current_index') and callable(getattr(self.multimedia_service, 'get_current_index')):
                current_index = self.multimedia_service.get_current_index()
                
            self.playlist.set_playlist(playlist_data, current_index)
        except Exception as e:
            logger.error(f"Error updating playlist: {str(e)}")
    
    def is_playing(self):
        """Check if media is currently playing."""
        return self.multimedia_service.is_currently_playing()
    
    def process_media_command(self, query):
        """Process a media command from user input."""
        return self.multimedia_service.process_media_command(query)
    
    def _on_search_play_media(self, media_item):
        """Handle playback request from search widget."""
        # Update the playlist after adding a new item
        QTimer.singleShot(500, self.update_playlist)
    
    def _on_position_changed(self, position, duration):
        """Handle playback position changed event."""
        self.controls.update_position(position, duration)
        
        # Update waveform intensity based on current playback position
        if hasattr(self, 'waveform') and self.waveform.is_active:
            self.waveform.update_intensity(position, duration)

    def _on_loop_clicked(self):
        """Handle loop button click."""
        is_looping = self.controls.loop_button.isChecked()
        if hasattr(self.multimedia_service, 'set_loop_mode'):
            self.multimedia_service.set_loop_mode(is_looping)
            # Update button tooltip
            if is_looping:
                self.controls.loop_button.setToolTip("Tắt phát lại")
            else:
                self.controls.loop_button.setToolTip("Phát lại")


class SearchWorker(QThread):
    """Worker thread for performing media searches without blocking the UI."""
    
    # Signal to emit search results
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, multimedia_service, query, source="youtube"):
        super().__init__()
        self.multimedia_service = multimedia_service
        self.query = query
        self.source = source
        
    def run(self):
        """Perform the search operation in a background thread."""
        try:
            results = []
            
            if self.source == "youtube":
                # Use the multimedia service's YouTube search functionality
                results = self.multimedia_service.search_youtube(self.query, max_results=10)
            elif self.source == "local":
                # Implement local media search if needed
                pass
            # Add more sources as needed: Spotify, SoundCloud, etc.
            
            # Emit results
            self.results_ready.emit(results)
            
        except Exception as e:
            logger.error(f"Error in search worker: {str(e)}")
            self.error_occurred.emit(str(e))


class MediaItemWidget(QWidget):
    """Custom widget for displaying a media item in search results."""
    
    def __init__(self, media_item, parent=None):
        super().__init__(parent)
        self.media_item = media_item
        self.thumbnail_url = media_item.get('thumbnail_url', None)
        self.thumbnail = None
        self.is_loading_thumbnail = False
        
        self._setup_ui()
        
        # Load thumbnail asynchronously
        if self.thumbnail_url:
            self._load_thumbnail_async()
    
    def _setup_ui(self):
        """Set up the UI components for the media item."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Thumbnail area
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 68)  # 16:9 aspect ratio
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            background-color: #E5E7EB;
            border-radius: 6px;
        """)
        
        # Create a default thumbnail
        self._create_default_thumbnail()
        
        # Info area
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Title
        self.title_label = QLabel(self.media_item.get('title', 'Unknown Title'))
        self.title_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #111827;
        """)
        self.title_label.setWordWrap(True)
        
        # Channel/artist
        channel = self.media_item.get('channel', self.media_item.get('artist', 'Unknown Channel'))
        self.channel_label = QLabel(channel)
        self.channel_label.setStyleSheet("""
            color: #4B5563;
            font-size: 12px;
        """)
        
        # Duration
        duration = self.media_item.get('duration', '')
        if duration:
            if isinstance(duration, int):
                # Convert seconds to MM:SS format
                minutes = duration // 60
                seconds = duration % 60
                duration = f"{minutes}:{seconds:02d}"
                
            self.duration_label = QLabel(duration)
            self.duration_label.setStyleSheet("""
                color: #6B7280;
                font-size: 11px;
                font-style: italic;
            """)
            info_layout.addWidget(self.duration_label)
        
        # Views/popularity
        views = self.media_item.get('views', self.media_item.get('plays', ''))
        if views:
            if isinstance(views, int) and views > 1000:
                # Format as K or M for thousands/millions
                if views >= 1000000:
                    views = f"{views/1000000:.1f}M views"
                else:
                    views = f"{views/1000:.1f}K views"
            else:
                views = f"{views} views"
                
            self.views_label = QLabel(views)
            self.views_label.setStyleSheet("""
                color: #6B7280;
                font-size: 11px;
            """)
            info_layout.addWidget(self.views_label)
        
        # Add widgets to layouts
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.channel_label)
        
        layout.addWidget(self.thumbnail_label)
        layout.addLayout(info_layout, 1)
        
        # Add play button
        self.play_button = QPushButton()
        self.play_button.setFixedSize(36, 36)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setToolTip("Phát nội dung này")
        
        # Style the play button
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                border-radius: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)
        
        # Set play icon
        resources_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'icons'
        )
        play_icon_path = os.path.join(resources_dir, 'play.png')
        
        if os.path.exists(play_icon_path):
            self.play_button.setIcon(QIcon(play_icon_path))
        else:
            # Create simple play icon if file doesn't exist
            play_icon = QPixmap(24, 24)
            play_icon.fill(Qt.transparent)
            
            painter = QPainter(play_icon)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            
            # Draw play triangle
            path = QPainterPath()
            path.moveTo(8, 6)
            path.lineTo(18, 12)
            path.lineTo(8, 18)
            path.closeSubpath()
            painter.drawPath(path)
            painter.end()
            
            self.play_button.setIcon(QIcon(play_icon))
        
        self.play_button.setIconSize(QSize(20, 20))
        
        layout.addWidget(self.play_button)
        
        # Set hover effect for the whole widget
        self.setMouseTracking(True)
        self.setStyleSheet("""
            MediaItemWidget {
                background-color: transparent;
                border-radius: 8px;
            }
            MediaItemWidget:hover {
                background-color: #F3F4F6;
            }
        """)
    
    def _create_default_thumbnail(self):
        """Create a default thumbnail with a gradient background."""
        size = (120, 68)
        pixmap = QPixmap(*size)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create a gradient background
        gradient = QLinearGradient(0, 0, size[0], size[1])
        gradient.setColorAt(0, QColor("#6B7280"))
        gradient.setColorAt(1, QColor("#4B5563"))
        
        # Draw rounded rectangle background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, size[0], size[1], 6, 6)
        
        # Draw a play icon placeholder
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Center coordinates
        center_x = size[0] // 2
        center_y = size[1] // 2
        
        # Draw triangle
        path = QPainterPath()
        path.moveTo(center_x - 10, center_y - 15)
        path.lineTo(center_x + 15, center_y)
        path.lineTo(center_x - 10, center_y + 15)
        path.closeSubpath()
        painter.drawPath(path)
        
        painter.end()
        self.thumbnail = pixmap
        self.thumbnail_label.setPixmap(pixmap)
    
    def _load_thumbnail_async(self):
        """Load thumbnail image asynchronously to prevent UI blocking."""
        if self.is_loading_thumbnail:
            return
            
        self.is_loading_thumbnail = True
        
        def load_image():
            try:
                url = self.thumbnail_url
                data = urllib.request.urlopen(url).read()
                image = QPixmap()
                image.loadFromData(data)
                
                # Scale to thumbnail size while preserving aspect ratio
                image = image.scaled(120, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Create a new pixmap with rounded corners
                rounded = QPixmap(120, 68)
                rounded.fill(Qt.transparent)
                
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Create path for rounded rectangle
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, 120, 68), 6, 6)
                
                # Set clip path and draw the image
                painter.setClipPath(path)
                
                # Center the image if aspect ratio is preserved
                x = (120 - image.width()) // 2 if image.width() < 120 else 0
                y = (68 - image.height()) // 2 if image.height() < 68 else 0
                
                painter.drawPixmap(x, y, image)
                painter.end()
                
                self.thumbnail = rounded
                
                # Update UI in the main thread
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self, "_set_thumbnail", 
                                         Qt.QueuedConnection, 
                                         Q_ARG(QPixmap, rounded))
            except Exception as e:
                logger.error(f"Error loading thumbnail: {str(e)}")
            finally:
                self.is_loading_thumbnail = False
        
        # Start loading in background thread
        thread = threading.Thread(target=load_image)
        thread.daemon = True
        thread.start()
    
    def _set_thumbnail(self, pixmap):
        """Set the thumbnail image (called from the main thread)."""
        self.thumbnail_label.setPixmap(pixmap)
    
    def enterEvent(self, event):
        """Handle mouse enter event for hover effect."""
        super().enterEvent(event)
        self.setCursor(Qt.PointingHandCursor)
    
    def leaveEvent(self, event):
        """Handle mouse leave event for hover effect."""
        super().leaveEvent(event)
        self.setCursor(Qt.ArrowCursor)
    
    def mousePressEvent(self, event):
        """Handle mouse press event for selection effect."""
        if event.button() == Qt.LeftButton:
            # Emit play signal if parent has onPlayClicked method
            if hasattr(self.parent(), "onPlayClicked"):
                self.parent().onPlayClicked(self.media_item)
        super().mousePressEvent(event)


class MediaSearchWidget(QWidget):
    """Widget for searching and displaying media results from various sources."""
    
    # Define signals
    play_media = pyqtSignal(dict)  # Emitted when media is selected for playback
    
    def __init__(self, multimedia_service, parent=None):
        super().__init__(parent)
        self.multimedia_service = multimedia_service
        self.current_search_worker = None
        self.search_results = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components for the media search widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title section
        title_layout = QHBoxLayout()
        
        title_label = QLabel("Tìm kiếm nội dung")
        title_label.setStyleSheet("""
            background-color: #3cbfa3;
            font-size: 18px;
            font-weight: bold;
            color: #1E3A8A;
            padding-bottom: 5px;
            border-bottom: 2px solid #46d2b6;
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Source selector for different platforms
        self.source_combo = QComboBox()
        self.source_combo.addItem("YouTube", "youtube")
        # Add more sources as they are implemented
        # self.source_combo.addItem("Spotify", "spotify")
        # self.source_combo.addItem("SoundCloud", "soundcloud")
        
        self.source_combo.setStyleSheet("""
            QComboBox {
                background-color: #F3F4F6;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 5px 10px;
                min-width: 120px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: none;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                selection-background-color: #EFF6FF;
                selection-color: #1D4ED8;
            }
        """)
        
        title_layout.addWidget(self.source_combo)
        
        # Search section
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nhập tên bài hát, nghệ sĩ, hoặc video...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #F9FAFB;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #60A5FA;
                background-color: #FFFFFF;
            }
        """)
        self.search_input.returnPressed.connect(self.perform_search)
        
        self.search_button = QPushButton("Tìm kiếm")
        self.search_button.setCursor(Qt.PointingHandCursor)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)
        self.search_button.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.search_input, 1)  # 1 = stretch factor
        search_layout.addWidget(self.search_button)
        
        # Results section
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.NoFrame)
        self.results_scroll.setStyleSheet("""
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
                background: #D1D5DB;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9CA3AF;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
                height: 0px;
            }
        """)
        
        # Container widget for results
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(10)
        self.results_layout.setAlignment(Qt.AlignTop)
        
        # Add empty state label
        self.empty_label = QLabel("Nhập từ khóa và nhấn Tìm kiếm để tìm kiếm nội dung.")
        self.empty_label.setStyleSheet("""
            color: #6B7280;
            font-size: 14px;
            font-style: italic;
            padding: 20px;
        """)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.results_layout.addWidget(self.empty_label)
        
        # Add loading indicator
        self.loading_label = QLabel("Đang tìm kiếm...")
        self.loading_label.setStyleSheet("""
            color: #3B82F6;
            font-size: 14px;
            font-weight: bold;
            padding: 20px;
        """)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.hide()
        self.results_layout.addWidget(self.loading_label)
        
        self.results_scroll.setWidget(self.results_container)
        
        # Add all sections to main layout
        main_layout.addLayout(title_layout)
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.results_scroll, 1)  # 1 = stretch factor
        
        # Apply shadow effect to the widget
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        # Style the widget
        self.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E5E7EB;
        """)
    
    def perform_search(self):
        """Perform a search based on the search input."""
        # Get search query
        query = self.search_input.text().strip()
        if not query:
            return
            
        # Get selected source
        source = self.source_combo.currentData()
        
        # Show loading state
        self._set_loading_state(True)
        
        # Cancel any existing search
        if self.current_search_worker and self.current_search_worker.isRunning():
            self.current_search_worker.terminate()
            self.current_search_worker.wait()
        
        # Start new search
        self.current_search_worker = SearchWorker(self.multimedia_service, query, source)
        self.current_search_worker.results_ready.connect(self._handle_search_results)
        self.current_search_worker.error_occurred.connect(self._handle_search_error)
        self.current_search_worker.start()
    
    def _set_loading_state(self, is_loading):
        """Set the loading state of the search widget."""
        self.search_button.setEnabled(not is_loading)
        self.search_input.setEnabled(not is_loading)
        self.source_combo.setEnabled(not is_loading)
        
        if is_loading:
            self.empty_label.hide()
            self.loading_label.show()
        else:
            self.loading_label.hide()
    
    def _handle_search_results(self, results):
        """Handle the search results."""
        # Store results
        self.search_results = results
        
        # Clear loading state
        self._set_loading_state(False)
        
        # Clear previous results
        self._clear_results()
        
        if not results:
            # Show no results message
            self.empty_label.setText("Không tìm thấy kết quả nào. Vui lòng thử từ khóa khác.")
            self.empty_label.show()
            return
            
        # Hide empty label
        self.empty_label.hide()
        
        # Add results to the container
        for result in results:
            item_widget = MediaItemWidget(result)
            # Connect play button clicked
            item_widget.play_button.clicked.connect(lambda checked=False, r=result: self.onPlayClicked(r))
            
            # Add to layout with a divider after each item (except the last one)
            self.results_layout.addWidget(item_widget)
            
            if result != results[-1]:
                divider = QFrame()
                divider.setFrameShape(QFrame.HLine)
                divider.setFrameShadow(QFrame.Sunken)
                divider.setStyleSheet("background-color: #E5E7EB; max-height: 1px;")
                self.results_layout.addWidget(divider)
    
    def _handle_search_error(self, error_message):
        """Handle search error."""
        # Clear loading state
        self._set_loading_state(False)
        
        # Show error message
        self._clear_results()
        self.empty_label.setText(f"Lỗi tìm kiếm: {error_message}")
        self.empty_label.setStyleSheet("""
            color: #DC2626;
            font-size: 14px;
            font-style: italic;
            padding: 20px;
        """)
        self.empty_label.show()
        
        # Log error
        logger.error(f"Search error: {error_message}")
    
    def _clear_results(self):
        """Clear the search results."""
        # Remove all widgets except the empty and loading labels
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            widget = item.widget()
            
            if widget and widget not in [self.empty_label, self.loading_label]:
                widget.deleteLater()
    
    def onPlayClicked(self, media_item):
        """Handle play button click on a media item."""
        if not media_item:
            return
            
        source = self.source_combo.currentData()
        
        try:
            if source == "youtube":
                # Show progress dialog
                progress_dialog = QMessageBox()
                progress_dialog.setWindowTitle("Đang tải xuống")
                progress_dialog.setText(f"Đang chuẩn bị phát '{media_item['title']}'...\nQuá trình này có thể mất vài giây.")
                progress_dialog.setStandardButtons(QMessageBox.NoButton)
                progress_dialog.setIcon(QMessageBox.Information)
                
                # Show dialog asynchronously
                progress_dialog.show()
                QApplication.processEvents()
                
                # Download and play the YouTube video
                video_id = media_item.get('id', media_item.get('video_id', ''))
                
                if video_id:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    # Use the YouTube downloader to get the audio
                    result = self.multimedia_service.download_youtube_audio(video_url)
                    
                    # Close progress dialog
                    progress_dialog.close()
                    
                    if result and 'audio_file' in result:
                        # Play the downloaded audio
                        self.multimedia_service.play_file(result['audio_file'])
                        
                        # Emit signal for external handling
                        self.play_media.emit(media_item)
                        
                        # Return success message
                        return f"Đang phát '{media_item['title']}'"
                    else:
                        QMessageBox.warning(self, "Lỗi tải xuống", 
                                           f"Không thể tải xuống '{media_item['title']}'.\nVui lòng thử lại sau.")
                        return f"Lỗi tải xuống '{media_item['title']}'"
                else:
                    # Close progress dialog
                    progress_dialog.close()
                    QMessageBox.warning(self, "Lỗi phát", "Không thể xác định ID video. Vui lòng thử lại.")
            
            # Implement handling for other sources as needed
            
        except Exception as e:
            logger.error(f"Error playing media: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi khi phát nội dung: {str(e)}")