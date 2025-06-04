# File: software/app/models/multimedia/audio_player.py
from PyQt5.QtCore import QObject, pyqtSignal
import os
import threading
import time
import re
from pathlib import Path
import random

try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    pygame = None
except Exception:
    PYGAME_AVAILABLE = False
    pygame = None

from ...utils import logger, config

class AudioPlayer(QObject):
    """
    Component responsible for audio playback functionality.
    Handles playing, pausing, and controlling audio files.
    """
    # Xác định tín hiệu Qt cho giao tiếp UI
    playback_started = pyqtSignal(object)  
    playback_stopped = pyqtSignal()
    playback_paused = pyqtSignal(bool) 
    playback_position_changed = pyqtSignal(float, float)  
    playback_finished = pyqtSignal()
    playback_error = pyqtSignal(str)  
    metadata_updated = pyqtSignal(object)  
    
    def __init__(self, metadata_manager=None, media_converter=None):
        """Initialize the audio player."""
        super().__init__()
        self.currently_playing = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.5  # 0.0 to 1.0
        self.play_time = 0  
        self.track_duration = 0  
        self.metadata_manager = metadata_manager
        self.media_converter = media_converter
        self.callbacks = []
        
        self.position_timer = None
        self.stop_event = threading.Event()
        
        self._initialize_pygame()
        
        self.browser_player = None
        self.loop_mode = False
        
        import tempfile
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'mis_audio_temp')
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def _initialize_pygame(self):
        """Initialize pygame mixer for audio playback."""
        if not PYGAME_AVAILABLE:
            logger.warning("Pygame not available. Audio playback will be limited.")
            return False
            
        try:
            # First try to quit the mixer if it's already initialized to reset any potential issues
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
                    time.sleep(0.2)  # Give it a moment to release resources
            except Exception as e:
                logger.warning(f"Failed to quit existing pygame mixer: {str(e)}")
                
            # Try different initialization parameters if the default fails
            initialization_options = [
                {"frequency": 44100, "size": -16, "channels": 2, "buffer": 4096},
                {"frequency": 44100, "size": -16, "channels": 1, "buffer": 4096},
                {"frequency": 22050, "size": -16, "channels": 2, "buffer": 2048},
                {"frequency": 44100, "size": 16, "channels": 2, "buffer": 4096},
                {}  # Default parameters as last resort
            ]
            
            for options in initialization_options:
                try:
                    pygame.mixer.init(**options)
                    if pygame.mixer.get_init():
                        logger.info(f"Pygame mixer initialized successfully with options: {options}")
                        pygame.mixer.music.set_volume(self.volume)
                        return True
                except Exception as e:
                    logger.warning(f"Failed to initialize pygame mixer with options {options}: {str(e)}")
                    continue
            
            # If we got here, all initialization attempts failed
            logger.error("All pygame mixer initialization attempts failed")
            return False
                
        except Exception as e:
            logger.error(f"Fatal error initializing pygame mixer: {str(e)}")
            return False
    
    def register_callback(self, callback):
        """Register a callback for player events."""
        if callable(callback) and callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """Unregister a callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def register_metadata_provider(self, metadata_manager):
        """Set the metadata manager for track information."""
        self.metadata_manager = metadata_manager
    
    def _notify_callbacks(self, event_type, data=None):
        """Notify callbacks and emit Qt signals."""
        # Call callbacks
        for callback in self.callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in callback for {event_type}: {str(e)}")
        
        # Emit Qt signals
        try:
            if event_type == 'playback_started':
                self.playback_started.emit(data)
            elif event_type == 'playback_stopped':
                self.playback_stopped.emit()
            elif event_type == 'playback_paused':
                self.playback_paused.emit(True)
            elif event_type == 'playback_resumed':
                self.playback_paused.emit(False)
            elif event_type == 'position_updated':
                if isinstance(data, dict) and 'position' in data and 'duration' in data:
                    self.playback_position_changed.emit(data['position'], data['duration'])
            elif event_type == 'track_finished':
                self.playback_finished.emit()
            elif event_type == 'error':
                if isinstance(data, str):
                    self.playback_error.emit(data)
                else:
                    self.playback_error.emit(str(data))
            elif event_type == 'metadata_updated':
                self.metadata_updated.emit(data)
        except Exception as e:
            logger.error(f"Error emitting signal for {event_type}: {str(e)}")
    
    def play(self, media_path=None):
        """Play audio from the specified path or resume current track."""
        try:
            # Resume if paused
            if self.is_paused and self.currently_playing and not media_path:
                if pygame and pygame.mixer.music.get_busy():
                    pygame.mixer.music.unpause()
                    self.is_playing = True
                    self.is_paused = False
                    self._start_position_timer()
                    self._notify_callbacks('playback_resumed', self._get_basic_track_info())
                    return True
                # If pygame is paused but not busy, restart playback
                elif pygame and self.currently_playing:
                    return self.play(self.currently_playing)
            
            # Use current track if no path provided
            if not media_path:
                if self.currently_playing:
                    media_path = self.currently_playing
                else:
                    logger.warning("No media path provided and no current track")
                    return False
            
            # Validate file exists
            if not os.path.exists(media_path):
                logger.error(f"Media file not found: {media_path}")
                return False
            
            # Kiểm tra tệp có hợp lệ không trước khi phát
            file_ext = Path(media_path).suffix.lower()
            
            # Try pygame first
            if pygame and pygame.mixer.get_init():
                try:
                    # Check if file extension is supported by pygame
                    if file_ext in ['.mp3', '.wav', '.ogg']:
                        # For YouTube downloads, add specific checks
                        if 'media_cache' in media_path and file_ext == '.mp3':
                            logger.info("YouTube downloaded audio detected, using more cautious loading")
                            # Use temporary wav conversion for more reliable playback
                            if self.media_converter and hasattr(self.media_converter, 'convert_to_wav'):
                                try:
                                    temp_wav = self.media_converter.convert_to_wav(media_path)
                                    if temp_wav and os.path.exists(temp_wav):
                                        logger.info(f"Using converted WAV file for playback: {temp_wav}")
                                        pygame.mixer.music.load(temp_wav)
                                    else:
                                        logger.info("Conversion failed, trying direct playback")
                                        pygame.mixer.music.load(media_path)
                                except Exception as conv_e:
                                    logger.warning(f"Error in conversion: {str(conv_e)}")
                                    pygame.mixer.music.load(media_path)
                            else:
                                # No converter available, try direct loading
                                pygame.mixer.music.load(media_path)
                        else:
                            # Normal loading for non-YouTube files
                            pygame.mixer.music.load(media_path)
                        
                        # Set volume and play
                        pygame.mixer.music.set_volume(self.volume)
                        pygame.mixer.music.play()
                        
                        # Store current track
                        self.currently_playing = media_path
                        self.is_playing = True
                        self.is_paused = False
                        
                        # Start position tracking
                        self._start_position_timer()
                        
                        # Get track duration
                        self._update_track_duration()
                        
                        # Notify callbacks
                        self._notify_callbacks('playback_started', self._get_basic_track_info())
                        
                        logger.info(f"Successfully started playing: {os.path.basename(media_path)}")
                        return True
                    else:
                        logger.warning(f"Unsupported file format: {file_ext}")
                        return False
                except pygame.error as e:
                    logger.error(f"Pygame error playing {media_path}: {str(e)}")
                    return False
            else:
                logger.warning("Pygame mixer not initialized")
                return False
                
        except Exception as e:
            logger.error(f"Error in play method: {str(e)}")
            self._notify_callbacks('error', str(e))
            return False
    
    def pause(self):
        """Pause current playback."""
        if not self.is_playing or self.is_paused:
            return False
            
        if pygame and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.is_paused = True
            
            # Stop position timer
            self._stop_position_timer()
            
            # Notify callbacks
            self._notify_callbacks('playback_paused', self._get_basic_track_info())
            
            logger.info("Paused playback")
            return True
        
        return False
    
    def resume(self):
        """Resume paused playback."""
        if not self.is_paused:
            return False
            
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.unpause()
            self.is_paused = False
            
            # Start position timer
            self._start_position_timer()
            
            # Get current track info with current position
            track_info = self._get_basic_track_info()
            
            # Notify callbacks - this is important to maintain UI state
            self._notify_callbacks('playback_resumed', track_info)
            
            # Immediately send a position update to ensure the UI reflects the correct position
            self._notify_callbacks('position_updated', {
                'position': self.play_time,
                'duration': self.track_duration
            })
            
            logger.info(f"Resumed playback at position {self.play_time:.2f}s")
            return True
        
        return False
    
    def stop(self):
        """Stop current playback."""
        if not self.is_playing and not self.is_paused:
            return False
            
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        
        # Close any browser player if it exists
        if self.browser_player and os.path.exists(self.browser_player):
            try:
                # Remove the temporary HTML file
                os.remove(self.browser_player)
                self.browser_player = None
            except Exception as e:
                logger.error(f"Error cleaning up browser player: {str(e)}")
        
        self.is_playing = False
        self.is_paused = False
        self.play_time = 0
        
        # Stop position timer
        self._stop_position_timer()
        
        # Notify callbacks
        self._notify_callbacks('playback_stopped', self._get_basic_track_info())
        
        logger.info("Stopped playback")
        return True
    
    def set_volume(self, volume):
        """Set volume level (0.0 to 1.0)."""
        try:
            # Ensure volume is within valid range
            volume = max(0.0, min(1.0, volume))
            
            # Store volume
            self.volume = volume
            
            # Apply volume if playing with pygame
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.set_volume(volume)
                
            # Notify callbacks
            self._notify_callbacks('volume_changed', {'volume': volume})
            
            logger.info(f"Volume set to {volume:.2f}")
            return True
                
        except Exception as e:
            logger.error(f"Error in set_volume method: {str(e)}")
            return False
    
    def get_volume(self):
        """Get current volume level."""
        return self.volume
    
    def set_position(self, position_seconds):
        """Set playback position in seconds."""
        try:
            # Ghi nhớ vị trí seek ban đầu để kiểm tra kết quả
            original_position = position_seconds
            
            if not self.is_playing and not self.is_paused:
                logger.warning("No active playback to set position")
                return False
                
            # Đảm bảo có track_duration hợp lệ
            if self.track_duration <= 0:
                # Cố gắng cập nhật duration
                self._update_track_duration()
                
                # Nếu vẫn không có duration, sử dụng giá trị mặc định 
                if self.track_duration <= 0:
                    logger.warning("Track duration is unknown, using estimated value")
                    if os.path.exists(self.currently_playing):
                        # Ước lượng dựa trên kích thước file
                        size_bytes = os.path.getsize(self.currently_playing)
                        # Khoảng 1MB/phút cho file MP3 128kbps
                        self.track_duration = max(60.0, size_bytes / (128 * 1024 / 8) / 60)
                    else:
                        # Giá trị mặc định 3 phút
                        self.track_duration = 180.0
                    
                    logger.info(f"Estimated track duration: {self.track_duration:.2f}s")
            
            # Ensure position is within valid range
            position_seconds = max(0.0, min(self.track_duration, position_seconds))
            
            # Store position
            self.play_time = position_seconds
            
            # Biến để theo dõi kết quả
            success = False
            
            # Apply position if playing with pygame
            if pygame and pygame.mixer.get_init():
                # Pygame doesn't support direct position seeking, so reload and skip
                was_paused = self.is_paused
                currently_playing = self.currently_playing
                
                if currently_playing and os.path.exists(currently_playing):
                    # Remember the original volume
                    original_volume = self.volume
                    
                    # Thử lặp lại tối đa 2 lần nếu thất bại
                    for attempt in range(2):
                        try:
                            # Stop existing playback
                            pygame.mixer.music.stop()
                            
                            # Thêm độ trễ nhỏ để đảm bảo pygame giải phóng tài nguyên
                            time.sleep(0.1)
                            
                            # Load the file again
                            pygame.mixer.music.load(currently_playing)
                            
                            # Start from the requested position
                            pygame.mixer.music.play(0, position_seconds)
                            
                            # Restore volume setting
                            pygame.mixer.music.set_volume(original_volume)
                            
                            # If it was paused before, pause it again
                            if was_paused:
                                pygame.mixer.music.pause()
                            else:
                                self.is_playing = True
                                self.is_paused = False
                                
                            # Kiểm tra xem đã phát chưa
                            if not was_paused:
                                time.sleep(0.2)  # Chờ một chút để pygame bắt đầu phát
                                if pygame.mixer.music.get_busy():
                                    success = True
                                    break
                            else:
                                success = True
                                break
                                
                        except Exception as e:
                            logger.error(f"Error during position seeking (attempt {attempt+1}): {str(e)}")
                            if attempt == 0:  # Chỉ thử khởi tạo lại nếu đây là lần thử đầu tiên
                                # Thử khởi tạo lại pygame
                                try:
                                    pygame.mixer.quit()
                                    time.sleep(0.3)
                                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                                except Exception as reinit_error:
                                    logger.error(f"Error reinitializing pygame: {str(reinit_error)}")
                    
                    # Nếu đã thành công, thông báo các callbacks
                    if success:
                        # Notify callbacks with the new position
                        self._notify_callbacks('position_changed', {'position': position_seconds})
                        self._notify_callbacks('position_updated', {
                            'position': position_seconds,
                            'duration': self.track_duration
                        })
                        
                        # Emit Qt signal for UI components
                        self.playback_position_changed.emit(position_seconds, self.track_duration)
                        
                        logger.info(f"Position set to {position_seconds:.2f}s of {self.track_duration:.2f}s (originally requested: {original_position:.2f}s)")
                        return True
                    else:
                        logger.warning(f"Failed to seek to position {position_seconds:.2f}s after multiple attempts")
                else:
                    logger.warning(f"Cannot seek position - file does not exist: {currently_playing}")
            
            # Even if pygame seeking failed, update the position and notify UI
            self._notify_callbacks('position_changed', {'position': position_seconds})
            self._notify_callbacks('position_updated', {
                'position': position_seconds,
                'duration': self.track_duration
            })
            
            # Emit Qt signal for UI components
            self.playback_position_changed.emit(position_seconds, self.track_duration)
            
            logger.info(f"Position updated to {position_seconds:.2f}s (UI only)")
            return True
                
        except Exception as e:
            logger.error(f"Error in set_position method: {str(e)}")
            return False
    
    def get_position(self):
        """Get current playback position in seconds."""
        return self.play_time
    
    def get_track_info(self):
        """Get current track information."""
        if self.metadata_manager and self.currently_playing:
            try:
                return self.metadata_manager.get_track_metadata(self.currently_playing)
            except Exception as e:
                logger.error(f"Error getting metadata: {str(e)}")
                return self._get_basic_track_info()
        else:
            return self._get_basic_track_info()
    
    def is_currently_playing(self):
        """Check if audio is currently playing."""
        if pygame and pygame.mixer.music.get_busy() and not self.is_paused:
            return True
        return self.is_playing and not self.is_paused
    
    def set_loop_mode(self, is_looping):
        """Set the loop mode for the current track.
        
        Args:
            is_looping (bool): True to enable looping, False to disable
            
        Returns:
            bool: Success status
        """
        try:
            self.loop_mode = bool(is_looping)
            logger.info(f"Loop mode {'enabled' if self.loop_mode else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error setting loop mode: {str(e)}")
            return False
    
    def _start_position_timer(self):
        """Start timer for tracking playback position."""
        self._stop_position_timer()
        self.position_timer = threading.Thread(target=self._update_position_thread, daemon=True)
        self.position_timer.start()
    
    def _stop_position_timer(self):
        """Stop the position timer."""
        self.stop_event.set()
        
        if self.position_timer and self.position_timer.is_alive():
            try:
                self.position_timer.join(timeout=1.0)
            except:
                pass
            
        self.stop_event.clear()
        self.position_timer = None
    
    def _update_position_thread(self):
        """Thread function for updating playback position."""
        try:
            # Start at current position if paused
            if not hasattr(self, 'play_time') or self.play_time is None:
                self.play_time = 0.01
            last_notification_time = 0
            
            while not self.stop_event.is_set():
                # Check if we're playing
                if self.is_playing and not self.is_paused:
                    # Update play time (0.1 second increments)
                    self.play_time += 0.1
                    
                    # Check for end of track
                    if pygame and pygame.mixer.get_init():
                        if not pygame.mixer.music.get_busy() and self.play_time > 1.0:
                            # Track has finished - wait a moment to confirm
                            time.sleep(0.2)
                            if not pygame.mixer.music.get_busy():
                                # Check if we should loop the current track
                                if self.loop_mode and self.currently_playing:
                                    logger.info("Loop mode is enabled, replaying current track")
                                    # Restart at the beginning of the track
                                    self.stop()
                                    time.sleep(0.2)  # Give it a moment to release resources
                                    self.play(self.currently_playing)
                                else:
                                    # Notify on the main thread
                                    self._notify_callbacks('track_finished', self._get_basic_track_info())
                                break
                    
                    if self.track_duration > 0 and self.play_time >= self.track_duration:
                        # Check if we should loop the current track
                        if self.loop_mode and self.currently_playing:
                            logger.info("Loop mode is enabled, replaying current track")
                            # Restart at the beginning of the track
                            self.stop()
                            time.sleep(0.2)  # Give it a moment to release resources
                            self.play(self.currently_playing)
                        else:
                            # Notify on the main thread
                            self._notify_callbacks('track_finished', self._get_basic_track_info())
                        break
                    
                    # Notify about position updates (but not too frequently)
                    current_time = time.time()
                    if current_time - last_notification_time >= 0.1:  # Update more frequently (10 times per second)
                        self._notify_callbacks('position_updated', {
                            'position': self.play_time,
                            'duration': self.track_duration
                        })
                        last_notification_time = current_time
                
                # Sleep a bit to avoid hogging the CPU
                time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error in position timer thread: {str(e)}")
            # Stop playback on error
            self.stop()
    
    def _update_track_duration(self, duration=0):
        """Update track duration."""
        if duration > 0:
            self.track_duration = duration
            return
            
        # Get duration from file if possible
        try:
            if not self.currently_playing or not os.path.exists(self.currently_playing):
                self.track_duration = 0
                return
                
            # Try to get duration using mutagen
            try:
                import mutagen
                audio = mutagen.File(self.currently_playing)
                if audio and hasattr(audio.info, 'length'):
                    self.track_duration = audio.info.length
                    return
            except ImportError:
                logger.warning("Mutagen not available for duration detection")
            except Exception as e:
                logger.warning(f"Mutagen error: {str(e)}")
            
            # Fallback: estimate duration based on file size for MP3
            if self.currently_playing.lower().endswith('.mp3'):
                try:
                    # Rough estimate: ~1MB per minute at 128kbps
                    size_bytes = os.path.getsize(self.currently_playing)
                    estimated_duration = size_bytes / (128 * 1024 / 8) / 60
                    self.track_duration = estimated_duration
                    logger.info(f"Estimated duration from file size: {estimated_duration:.2f}s")
                    return
                except Exception as e:
                    logger.warning(f"Error estimating duration: {str(e)}")
            
            # Default to 3 minutes if we can't determine duration
            self.track_duration = 180
            logger.info("Using default duration of 3 minutes")
            
        except Exception as e:
            logger.error(f"Error updating track duration: {str(e)}")
            self.track_duration = 0
    
    def _get_basic_track_info(self):
        """Get basic track info from filename."""
        if not self.currently_playing:
            return {
                'title': 'No track playing',
                'artist': '',
                'album': '',
                'duration': 0,
                'position': 0,
                'file_path': None,
                'is_playing': False,
                'is_paused': False,
                'cover_url': None
            }
            
        # Extract info from filename
        file_name = os.path.basename(self.currently_playing)
        file_base, file_ext = os.path.splitext(file_name)
        
        # Check if this is a YouTube ID (typically 11 characters)
        youtube_id_pattern = re.compile(r'^[a-zA-Z0-9_-]{11}$')
        is_youtube_id = youtube_id_pattern.match(file_base)
        
        title = file_base
        artist = 'Unknown Artist'
        album = 'Unknown Album'
        cover_url = None
        
        # For YouTube IDs, try to get metadata from the JSON file
        if is_youtube_id:
            json_path = os.path.join(os.path.dirname(self.currently_playing), f"{file_base}.json")
            if os.path.exists(json_path):
                try:
                    import json
                    with open(json_path, 'r', encoding='utf-8') as f:
                        yt_metadata = json.load(f)
                    
                    if 'title' in yt_metadata:
                        title = yt_metadata['title']
                    if 'channel' in yt_metadata:
                        artist = yt_metadata['channel']
                    album = 'YouTube'
                    if 'thumbnail' in yt_metadata:
                        cover_url = yt_metadata['thumbnail']
                    
                    logger.info(f"Found YouTube metadata for {file_base}: {title}")
                except Exception as e:
                    logger.warning(f"Error reading YouTube metadata for {file_base}: {str(e)}")
        # Otherwise try to split artist and title if formatted like "Artist - Title"
        elif ' - ' in file_base:
            parts = file_base.split(' - ', 1)
            if len(parts) == 2:
                artist, title = parts
        
        return {
            'title': title,
            'artist': artist,
            'album': album,
            'duration': self.track_duration,
            'position': self.play_time,
            'file_path': self.currently_playing,
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'cover_url': cover_url
        }