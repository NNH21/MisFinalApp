from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import os
import queue
import threading
import time
import re
import sys
import subprocess

from PyQt5.QtCore import QObject, pyqtSignal

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

try:
    from pytube import YouTube
    PYTUBE_AVAILABLE = True
except ImportError:
    PYTUBE_AVAILABLE = False

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

pygame = None
try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
except ImportError:
    pygame = None
except Exception as e:
    print(f"Error initializing pygame: {e}")
    pygame = None

from ..utils import config, logger

class MultimediaService(QObject):
    """
    Service for handling multimedia playback (audio/video/images).
    Provides interfaces for audio playback, playlist management, and media controls.
    """
    # Define Qt signals for UI communication
    playback_started = pyqtSignal(object) 
    playback_stopped = pyqtSignal()
    playback_paused = pyqtSignal(bool) 
    playback_position_changed = pyqtSignal(float, float)  
    playback_finished = pyqtSignal()
    playback_error = pyqtSignal(str)  
    metadata_updated = pyqtSignal(object)  
    
    def __init__(self):
        """Initialize the multimedia service."""
        super().__init__() 
        self.playlist = []
        self.current_track_index = -1
        self.is_playing = False  
        self.is_paused = False
        self.volume = 0.5  
        self.play_time = 0  
        self.track_duration = 0 
        
        global pygame
        if pygame:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.set_volume(self.volume)
                logger.info("Pygame mixer initialized for multimedia service")
            except Exception as e:
                logger.error(f"Failed to initialize pygame mixer: {e}")
        
        self.cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'media_cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.position_timer = None
        self._callbacks = []
        
        # For threaded playback
        self.playback_thread = None
        self.playback_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        logger.info("Multimedia service initialized")
    
    @property
    def current_index(self):
        """Get the current track index in the playlist."""
        return self.current_track_index
    
    @current_index.setter
    def current_index(self, value):
        """Set the current track index in the playlist."""
        self.current_track_index = value
        
    def register_callback(self, callback):
        """Register a callback function for playback events."""
        if callable(callback) and callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """Unregister a callback function."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, event_type, data=None):
        """Notify all registered callbacks of an event."""
        # Call traditional callbacks
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in callback for {event_type}: {e}")
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in multimedia callback: {str(e)}")
        
        # Emit Qt signals based on event type
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
            logger.error(f"Error emitting Qt signal for {event_type}: {str(e)}")
    
    def play(self, media_path=None):
        """
        Play audio from the specified path or current track.
        
        Args:
            media_path (str, optional): Path to the media file to play. If None, plays current track.
            
        Returns:
            bool: True if playback started successfully, False otherwise
        """
        try:
            # Stop any current playback first
            if self.is_playing or self.is_paused:
                self.stop()
            
            # If no media path is provided, use the current track
            if media_path is None:
                if self.is_paused and self.currently_playing:
                    # Resume paused playback
                    if pygame and pygame.mixer.music.get_busy():
                        pygame.mixer.music.unpause()
                        self.is_playing = True
                        self.is_paused = False
                        self._start_position_timer()
                        self._notify_callbacks('playback_resumed', self._get_current_track_info())
                        return True
                    else:
                        # If not paused or no pygame, try to play current track again
                        media_path = self.currently_playing
                elif self.currently_playing:
                    # Play current track from the beginning
                    media_path = self.currently_playing
                elif self.playlist and len(self.playlist) > 0:
                    # Play first track in playlist
                    if self.current_track_index < 0:
                        self.current_track_index = 0
                    media_path = self.playlist[self.current_track_index]
                else:
                    logger.warning("No media to play")
                    return False
            
            # Check if the file exists
            if not os.path.exists(media_path):
                logger.error(f"Media file not found: {media_path}")
                return False
            
            # Update current track
            self.currently_playing = media_path
            
            # Initialize playback based on file type
            file_ext = os.path.splitext(media_path)[1].lower()
            
            if file_ext in ['.mp3', '.wav', '.ogg', '.flac']:
                # Audio file playback
                if pygame:
                    try:
                        pygame.mixer.music.load(media_path)
                        pygame.mixer.music.set_volume(self.volume)
                        pygame.mixer.music.play()
                        
                        self.is_playing = True
                        self.is_paused = False
                        
                        # Get track duration if possible
                        self._update_track_duration()
                        
                        # Start position timer
                        self._start_position_timer()
                        
                        # Notify callbacks
                        self._notify_callbacks('playback_started', self._get_current_track_info())
                        
                        logger.info(f"Started playing: {os.path.basename(media_path)}")
                        return True
                    except Exception as e:
                        logger.error(f"Error playing audio file: {str(e)}")
                        return False
                else:
                    logger.error("Pygame mixer not available for audio playback")
                    return False
            elif file_ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
                # Video file playback (using external player)
                try:
                    # Use a platform-appropriate video player
                    if sys.platform == 'win32':
                        # Windows
                        subprocess.Popen(['start', '', media_path], shell=True)
                    elif sys.platform == 'darwin':
                        # macOS
                        subprocess.Popen(['open', media_path])
                    else:
                        # Linux and others
                        subprocess.Popen(['xdg-open', media_path])
                    
                    logger.info(f"Started external video player for: {os.path.basename(media_path)}")
                    return True
                except Exception as e:
                    logger.error(f"Error starting video player: {str(e)}")
                    return False
            else:
                logger.error(f"Unsupported media file type: {file_ext}")
                return False
                
        except Exception as e:
            logger.error(f"Error in play method: {str(e)}")
            return False
    
    def pause(self):
        """
        Pause the current playback.
        
        Returns:
            bool: True if paused successfully, False otherwise
        """
        try:
            if not self.is_playing or self.is_paused:
                return False
                
            if pygame and pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                self.is_paused = True
                
                # Stop position timer
                self._stop_position_timer()
                
                # Notify callbacks
                self._notify_callbacks('playback_paused', self._get_current_track_info())
                
                logger.info("Paused playback")
                return True
            else:
                logger.warning("No active playback to pause")
                return False
                
        except Exception as e:
            logger.error(f"Error in pause method: {str(e)}")
            return False
    
    def stop(self):
        """
        Stop the current playback.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            if not self.is_playing and not self.is_paused:
                return False
                
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.stop()
            
            self.is_playing = False
            self.is_paused = False
            self.play_time = 0
            
            # Stop position timer
            self._stop_position_timer()
            
            # Notify callbacks
            self._notify_callbacks('playback_stopped', self._get_current_track_info())
            
            logger.info("Stopped playback")
            return True
                
        except Exception as e:
            logger.error(f"Error in stop method: {str(e)}")
            return False
    
    def next_track(self):
        """
        Play the next track in the playlist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.playlist or len(self.playlist) == 0:
                logger.warning("No playlist available")
                return False
                
            # Increment track index
            self.current_track_index += 1
            
            # Loop back to beginning if at the end
            if self.current_track_index >= len(self.playlist):
                self.current_track_index = 0
                
            # Get the next track
            next_track = self.playlist[self.current_track_index]
            
            # Play the track
            return self.play(next_track)
                
        except Exception as e:
            logger.error(f"Error in next_track method: {str(e)}")
            return False
    
    def previous_track(self):
        """
        Play the previous track in the playlist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.playlist or len(self.playlist) == 0:
                logger.warning("No playlist available")
                return False
                
            # If we're in the first few seconds of a track, go to previous track,
            # otherwise restart the current track
            if self.play_time <= 3 and self.current_track_index > 0:
                # Go to previous track
                self.current_track_index -= 1
            elif self.play_time <= 3 and self.current_track_index == 0:
                # Wrap around to the last track
                self.current_track_index = len(self.playlist) - 1
                
            # Get the track
            track = self.playlist[self.current_track_index]
            
            # Play the track
            return self.play(track)
                
        except Exception as e:
            logger.error(f"Error in previous_track method: {str(e)}")
            return False
    
    def set_volume(self, volume):
        """
        Set the playback volume.
        
        Args:
            volume (float): Volume level from 0.0 to 1.0
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure volume is within valid range
            volume = max(0.0, min(1.0, volume))
            
            # Store volume
            self.volume = volume
            
            # Apply volume if playing
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
        """
        Get the current volume level.
        
        Returns:
            float: Volume level from 0.0 to 1.0
        """
        return self.volume
    
    def set_position(self, position_seconds):
        """
        Set the playback position.
        
        Args:
            position_seconds (float): Position in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Lưu vị trí ban đầu được yêu cầu để báo cáo
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
                    # Ước lượng dựa trên kích thước file
                    if os.path.exists(self.currently_playing):
                        size_bytes = os.path.getsize(self.currently_playing)
                        # Khoảng 1MB/phút cho file MP3 128kbps
                        self.track_duration = max(60.0, size_bytes / (128 * 1024 / 8) / 60)
                    else:
                        # Giá trị mặc định 3 phút
                        self.track_duration = 180.0
                        
                    logger.info(f"Estimated track duration: {self.track_duration:.2f}s")
            
            # Ensure position is within valid range
            position_seconds = max(0.0, min(self.track_duration, position_seconds))
            
            # Đảm bảo vị trí hợp lệ (tránh vị trí thập phân quá dài)
            position_seconds = round(position_seconds, 2)
            
            # Store position
            self.play_time = position_seconds
            
            # Theo dõi kết quả
            success = False
            
            # Use the audio_player if available
            if hasattr(self, 'audio_player') and self.audio_player:
                # Delegate to audio player's set_position method
                success = self.audio_player.set_position(position_seconds)
                
                # Notify position change even if handled by audio_player (for UI sync)
                if success:
                    self.playback_position_changed.emit(position_seconds, self.track_duration)
                    logger.info(f"Position set via audio_player to {position_seconds:.2f}s of {self.track_duration:.2f}s (requested: {original_position:.2f}s)")
                    return success
                else:
                    logger.warning("Setting position via audio_player failed, trying direct method")
            
            # Apply position if playing with pygame
            if pygame and pygame.mixer.music.get_busy():
                was_paused = self.is_paused
                currently_playing = self.currently_playing
                
                if currently_playing and os.path.exists(currently_playing):
                    # Thử lặp lại tối đa 2 lần nếu thất bại
                    for attempt in range(2):
                        try:
                            # Pygame doesn't support direct position seeking, so we need to reload and skip
                            pygame.mixer.music.stop()
                            
                            # Thêm nhỏ delay để đảm bảo pygame giải phóng tài nguyên 
                            time.sleep(0.1)
                            
                            pygame.mixer.music.load(currently_playing)
                            pygame.mixer.music.play(0, position_seconds)
                            pygame.mixer.music.set_volume(self.volume)
                            
                            if was_paused:
                                pygame.mixer.music.pause()
                            
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
                            logger.error(f"Error during pygame seeking (attempt {attempt+1}): {str(e)}")
                            if attempt == 0:  # Chỉ thử khởi tạo lại nếu lần đầu thất bại
                                try:
                                    # Khởi tạo lại pygame
                                    pygame.mixer.quit()
                                    time.sleep(0.3)
                                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                                except Exception as reinit_e:
                                    logger.error(f"Error reinitializing pygame: {str(reinit_e)}")
                    
                    # Nếu thành công, báo cáo kết quả
                    if success:
                        # Notify callbacks
                        self._notify_callbacks('position_changed', {'position': position_seconds})
                        
                        # Also emit the signal for UI components
                        self.playback_position_changed.emit(position_seconds, self.track_duration)
                        
                        logger.info(f"Position set to {position_seconds:.2f}s of {self.track_duration:.2f}s (requested: {original_position:.2f}s)")
                        return True
                    else:
                        logger.warning(f"Failed to seek to position {position_seconds:.2f}s after attempts")
                else:
                    logger.warning(f"Cannot seek - file does not exist: {currently_playing}")
                
            # Fallback: Just update the position for UI and timing purposes
            # This ensures that even if actual seeking fails, the UI remains responsive
            self._notify_callbacks('position_changed', {'position': position_seconds})
            self.playback_position_changed.emit(position_seconds, self.track_duration)
            logger.info(f"Position updated to {position_seconds:.2f}s (UI only)")
            return True
                
        except Exception as e:
            logger.error(f"Error in set_position method: {str(e)}")
            return False
    
    def get_position(self):
        """
        Get the current playback position.
        
        Returns:
            float: Position in seconds
        """
        if pygame and pygame.mixer.music.get_busy() and not self.is_paused:
            # Try to get position from pygame if available
            try:
                # Pygame doesn't provide direct position query, so we use our timer
                return self.play_time
            except:
                pass
        
        return self.play_time
    
    def get_track_info(self):
        """
        Get information about the current track.
        
        Returns:
            dict: Track information including title, artist, album, etc.
        """
        return self._get_current_track_info()
    
    def set_playlist(self, file_paths):
        """
        Set the current playlist.
        
        Args:
            file_paths (list): List of file paths to add to the playlist
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate file paths
            valid_paths = []
            for path in file_paths:
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    logger.warning(f"File not found: {path}")
            
            # Set playlist
            self.playlist = valid_paths
            
            # Reset track index
            self.current_track_index = -1
            
            # Notify callbacks
            self._notify_callbacks('playlist_updated', {'playlist': self.playlist})
            
            logger.info(f"Playlist updated with {len(valid_paths)} tracks")
            return True
                
        except Exception as e:
            logger.error(f"Error in set_playlist method: {str(e)}")
            return False
    
    def add_to_playlist(self, file_path):
        """
        Add a file to the current playlist.
        
        Args:
            file_path (str): Path to the file to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate file path
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False
            
            # Add to playlist
            self.playlist.append(file_path)
            
            # Notify callbacks
            self._notify_callbacks('playlist_updated', {'playlist': self.playlist})
            
            logger.info(f"Added to playlist: {os.path.basename(file_path)}")
            return True
                
        except Exception as e:
            logger.error(f"Error in add_to_playlist method: {str(e)}")
            return False
    
    def get_playlist(self):
        """
        Get the current playlist.
        
        Returns:
            list: List of file paths in the playlist
        """
        return self.playlist
    
    def play_file(self, file_path, add_to_playlist=True):
        """
        Play a media file and optionally add it to the playlist.
        
        Args:
            file_path (str): Path to the media file
            add_to_playlist (bool): Whether to add the file to the playlist
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate file path
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False
            
            # Stop any current playback first
            if self.is_playing or self.is_paused:
                self.stop()
            
            # Add to playlist if requested
            if add_to_playlist:
                if file_path not in self.playlist:
                    self.playlist.append(file_path)
                    self.current_track_index = len(self.playlist) - 1
                else:
                    # Find the index of the file in the playlist
                    self.current_track_index = self.playlist.index(file_path)
                
                # Notify callbacks
                self._notify_callbacks('playlist_updated', {'playlist': self.playlist})
            
            # Play the file
            return self.play(file_path)
                
        except Exception as e:
            logger.error(f"Error in play_file method: {str(e)}")
            return False
    
    def is_currently_playing(self):
        """
        Check if media is currently playing.
        
        Returns:
            bool: True if playing, False otherwise
        """
        if pygame and pygame.mixer.music.get_busy() and not self.is_paused:
            return True
        return self.is_playing and not self.is_paused
    
    def play_next(self):
        """
        Play the next track in the playlist (UI friendly method).
        This is a convenience method that calls next_track().
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.next_track()

    def play_previous(self):
        """
        Play the previous track in the playlist (UI friendly method).
        This is a convenience method that calls previous_track().
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.previous_track()

    def resume(self):
        """
        Resume paused playback.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_paused or not self.is_playing:
            return False
            
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.unpause()
            self.is_paused = False
            
            # Resume position timer
            self._start_position_timer()
            
            # Notify callbacks
            self._notify_callbacks('playback_resumed', self._get_current_track_info())
            
            logger.info("Resumed playback")
            return True
        
        return False

    def _start_position_timer(self):
        """Start the timer for tracking playback position."""
        # Stop any existing timer
        self._stop_position_timer()
        
        # Create a new timer
        self.position_timer = threading.Thread(target=self._update_position_thread, daemon=True)
        self.position_timer.start()
    
    def _stop_position_timer(self):
        """Stop the position timer."""
        # Signal the timer to stop
        self.stop_event.set()
        
        # Wait for the timer to stop if it's running
        if self.position_timer and self.position_timer.is_alive():
            try:
                self.position_timer.join(timeout=1.0)
            except:
                pass
            
        # Clear the stop event
        self.stop_event.clear()
        
        # Clear the position timer
        self.position_timer = None
    
    def _update_position_thread(self):
        """Thread function for updating playback position."""
        try:
            last_notification_time = 0
            
            while not self.stop_event.is_set():
                # Check if we're playing
                if self.is_playing and not self.is_paused:
                    # Update play time
                    self.play_time += 0.1
                    
                    # Check for end of track
                    if self.track_duration > 0 and self.play_time >= self.track_duration:
                        # Notify on the main thread
                        self._notify_callbacks('track_finished', self._get_current_track_info())
                        
                        # Try to play the next track
                        if len(self.playlist) > 0:
                            # We do this in a new thread to avoid conflicts
                            threading.Thread(target=self.next_track, daemon=True).start()
                        else:
                            # Just stop
                            threading.Thread(target=self.stop, daemon=True).start()
                            
                        # Exit this loop
                        break
                    
                    # Notify about position updates (but not too frequently)
                    current_time = time.time()
                    if current_time - last_notification_time >= 0.5:  # Every half second
                        self._notify_callbacks('position_updated', {
                            'position': self.play_time,
                            'duration': self.track_duration
                        })
                        last_notification_time = current_time
                
                # Sleep a bit to avoid hogging the CPU
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in position timer thread: {str(e)}")
            # Ensure we stop if there's an error
            self.stop()
    
    def _update_track_duration(self):
        """Update the duration of the current track."""
        try:
            if not self.currently_playing:
                self.track_duration = 0
                return
                
            # Try to get duration from pygame if available
            if pygame and pygame.mixer.get_init():
                try:
                    import mutagen
                    audio = mutagen.File(self.currently_playing)
                    if audio:
                        self.track_duration = audio.info.length
                        return
                except ImportError:
                    logger.warning("Mutagen library not available for track duration")
                except Exception as e:
                    logger.warning(f"Error getting track duration: {str(e)}")
            
            # Fallback to default duration
            self.track_duration = 0
            
        except Exception as e:
            logger.error(f"Error in _update_track_duration: {str(e)}")
            self.track_duration = 0
    
    def _get_current_track_info(self):
        """Get information about the current track."""
        try:
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
                
            # Get basic info from file path
            file_name = os.path.basename(self.currently_playing)
            file_base, file_ext = os.path.splitext(file_name)
            
            # Default info
            info = {
                'title': file_base,
                'artist': 'Unknown Artist',
                'album': 'Unknown Album',
                'duration': self.track_duration,
                'position': self.play_time,
                'file_path': self.currently_playing,
                'is_playing': self.is_playing,
                'is_paused': self.is_paused,
                'cover_url': None
            }
            
            # Try to get metadata from file
            try:
                import mutagen
                audio = mutagen.File(self.currently_playing)
                
                if audio:
                    # Extract metadata based on file type
                    if hasattr(audio, 'tags'):
                        tags = audio.tags
                        
                        # ID3 tags (MP3)
                        if hasattr(tags, 'getall'):
                            # Try to get title
                            title_frames = tags.getall('TIT2')
                            if title_frames:
                                info['title'] = str(title_frames[0])
                                
                            # Try to get artist
                            artist_frames = tags.getall('TPE1')
                            if artist_frames:
                                info['artist'] = str(artist_frames[0])
                                
                            # Try to get album
                            album_frames = tags.getall('TALB')
                            if album_frames:
                                info['album'] = str(album_frames[0])
                                
                            # Try to get cover art
                            apic_frames = tags.getall('APIC')
                            if apic_frames:
                                # Save cover art to cache
                                cover_data = apic_frames[0].data
                                cover_path = os.path.join(self.cache_dir, f"cover_{hash(self.currently_playing)}.jpg")
                                
                                with open(cover_path, 'wb') as f:
                                    f.write(cover_data)
                                    
                                info['cover_url'] = cover_path
                        
                        # FLAC and OGG tags
                        elif hasattr(tags, 'get'):
                            # Try to get title
                            if 'title' in tags:
                                info['title'] = str(tags['title'][0])
                                
                            # Try to get artist
                            if 'artist' in tags:
                                info['artist'] = str(tags['artist'][0])
                                
                            # Try to get album
                            if 'album' in tags:
                                info['album'] = str(tags['album'][0])
                                
                            # Cover art for FLAC
                            if hasattr(audio, 'pictures') and audio.pictures:
                                # Save cover art to cache
                                cover_data = audio.pictures[0].data
                                cover_path = os.path.join(self.cache_dir, f"cover_{hash(self.currently_playing)}.jpg")
                                
                                with open(cover_path, 'wb') as f:
                                    f.write(cover_data)
                                    
                                info['cover_url'] = cover_path
                
            except ImportError:
                logger.warning("Mutagen library not available for track metadata")
            except Exception as e:
                logger.warning(f"Error getting track metadata: {str(e)}")
                
            return info
                
        except Exception as e:
            logger.error(f"Error in _get_current_track_info: {str(e)}")
            
            # Return minimal info
            return {
                'title': os.path.basename(self.currently_playing) if self.currently_playing else 'Unknown',
                'artist': 'Unknown',
                'album': 'Unknown',
                'duration': self.track_duration,
                'position': self.play_time,
                'file_path': self.currently_playing,
                'is_playing': self.is_playing,
                'is_paused': self.is_paused,
                'cover_url': None
            }
    
    def process_media_command(self, command):
        """
        Process a media command from voice input or text.
        
        Args:
            command (str): The command to process (e.g., 'play', 'pause', 'next')
            
        Returns:
            str: A response message
        """
        try:
            command = command.lower().strip()
            
            # Handle play/pause commands
            if "play" in command or "phát" in command or "bắt đầu" in command:
                # If currently paused, resume
                if self.is_playing and self.is_paused:
                    if self.resume():
                        return "Đã tiếp tục phát nhạc"
                # Otherwise try to start playback
                elif self.play():
                    track_info = self._get_current_track_info()
                    return f"Đang phát {track_info['title']} - {track_info['artist']}"
                else:
                    return "Không có bài hát nào để phát"
                    
            elif "pause" in command or "tạm dừng" in command:
                if self.pause():
                    return "Đã tạm dừng phát nhạc"
                else:
                    return "Không có bài hát nào đang phát"
                    
            elif "stop" in command or "dừng" in command or "ngừng" in command:
                if self.stop():
                    return "Đã dừng phát nhạc"
                else:
                    return "Không có bài hát nào đang phát"
                    
            # Handle track navigation
            elif "next" in command or "tiếp theo" in command or "bài tiếp" in command or "bài kế" in command:
                if self.play_next():
                    track_info = self._get_current_track_info()
                    return f"Đang phát bài tiếp theo: {track_info['title']} - {track_info['artist']}"
                else:
                    return "Không có bài tiếp theo trong danh sách phát"
                    
            elif "prev" in command or "previous" in command or "trước" in command or "bài trước" in command:
                if self.play_previous():
                    track_info = self._get_current_track_info()
                    return f"Đang phát bài trước: {track_info['title']} - {track_info['artist']}"
                else:
                    return "Không có bài trước trong danh sách phát"
                    
            # Handle volume commands
            elif "volume" in command or "âm lượng" in command:
                # Extract volume level
                try:
                    # Look for numbers in the command
                    import re
                    volume_matches = re.findall(r'\d+', command)
                    if volume_matches:
                        volume = int(volume_matches[0])
                        # Convert to 0-1 range
                        volume = min(100, max(0, volume)) / 100.0
                        self.set_volume(volume)
                        return f"Đã đặt âm lượng thành {int(volume * 100)}%"
                        
                    # Check for keywords
                    if "up" in command or "increase" in command or "tăng" in command:
                        new_volume = min(1.0, self.volume + 0.1)
                        self.set_volume(new_volume)
                        return f"Đã tăng âm lượng lên {int(new_volume * 100)}%"
                    elif "down" in command or "decrease" in command or "lower" in command or "giảm" in command:
                        new_volume = max(0.0, self.volume - 0.1)
                        self.set_volume(new_volume)
                        return f"Đã giảm âm lượng xuống {int(new_volume * 100)}%"
                    elif "max" in command or "tối đa" in command:
                        self.set_volume(1.0)
                        return "Đã đặt âm lượng tối đa"
                    elif "min" in command or "tối thiểu" in command:
                        self.set_volume(0.1)  # Use 10% instead of 0 to avoid completely muting
                        return "Đã đặt âm lượng tối thiểu"
                    elif "mute" in command or "tắt tiếng" in command:
                        self.set_volume(0.0)
                        return "Đã tắt tiếng"
                    else:
                        return f"Âm lượng hiện tại là {int(self.volume * 100)}%"
                except Exception as e:
                    logger.error(f"Error processing volume command: {str(e)}")
                    return "Không thể thay đổi âm lượng"
                    
            # Information commands
            elif "what" in command or "which" in command or "current" in command or "bài gì" in command or "bài nào" in command:
                if self.is_playing:
                    track_info = self._get_current_track_info()
                    if self.is_paused:
                        return f"Bài hát đang tạm dừng: {track_info['title']} - {track_info['artist']}"
                    else:
                        return f"Đang phát: {track_info['title']} - {track_info['artist']}"
                else:
                    return "Không có bài hát nào đang phát"
                    
            # If command not recognized
            else:
                return "Xin lỗi, tôi không hiểu lệnh âm nhạc đó"
                
        except Exception as e:
            logger.error(f"Error processing media command: {str(e)}")
            return "Đã xảy ra lỗi khi xử lý lệnh âm nhạc"

    def is_media_command(self, command):
        """
        Check if the given command is a media-related command.
        
        Args:
            command (str): The command to check.
            
        Returns:
            bool: True if the command is media-related, False otherwise.
        """
        media_keywords = [
            "play", "pause", "stop", "next", "prev", "previous", "volume",
            "âm lượng", "phát", "bắt đầu", "tạm dừng", "dừng", "ngừng",
            "tiếp theo", "bài tiếp", "bài kế", "trước", "bài trước", "tắt tiếng",
            "tăng", "giảm", "tối đa", "tối thiểu", "mute", "bài gì", "bài nào"
        ]
        command = command.lower().strip()
        return any(keyword in command for keyword in media_keywords)

    # YouTube integration methods
    def search_youtube(self, query, max_results=5):
        """
        Search for videos on YouTube based on a query.
        
        Args:
            query (str): The search query
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of video information dictionaries
        """
        if not YOUTUBE_API_AVAILABLE:
            logger.error("YouTube API client not available. Please install googleapiclient.")
            return []
            
        # Check if API key is configured
        if not config.YOUTUBE_API_KEY:
            logger.error("YouTube API key not configured. Please set it in config.py")
            return []
            
        try:
            # Initialize the YouTube API client
            youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY)
            
            # Execute the search request
            search_response = youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='video',  # Only search for videos
                videoEmbeddable='true'  # Only videos that can be embedded
            ).execute()
            
            # Process the results
            videos = []
            for item in search_response.get('items', []):
                if item['id']['kind'] == 'youtube#video':
                    video_info = {
                        'id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'thumbnail': item['snippet']['thumbnails']['default']['url'],
                        'channel': item['snippet']['channelTitle'],
                        'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                    }
                    videos.append(video_info)
                    
            logger.info(f"Found {len(videos)} YouTube videos for query: {query}")
            return videos
            
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            return []
            
        except Exception as e:
            logger.error(f"Error searching YouTube: {str(e)}")
            return []
    
    def download_youtube_audio(self, video_url, output_dir=None):
        """
        Download audio from a YouTube video.
        
        Args:
            video_url (str): YouTube video URL
            output_dir (str): Directory to save the file (defaults to cache dir)
            
        Returns:
            str: Path to the downloaded audio file, or None if failed
        """
        if not output_dir:
            output_dir = self.cache_dir
            
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the video ID for unique filename
        video_id = video_url.split('v=')[-1].split('&')[0]
        output_file = os.path.join(output_dir, f"{video_id}.mp3")
        
        # Skip download if file already exists
        if os.path.exists(output_file):
            logger.info(f"Using cached YouTube audio at {output_file}")
            return output_file
        
        # Log FFmpeg information for debugging
        if config.FFMPEG_PATH:
            logger.info(f"FFmpeg path is configured as: {config.FFMPEG_PATH}")
            try:
                import platform
                if platform.system() == 'Windows':
                    potential_ffmpeg_paths = [
                        os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg.exe'),
                        os.path.join(config.FFMPEG_PATH, 'ffmpeg.exe'),
                        config.FFMPEG_PATH
                    ]
                else:
                    potential_ffmpeg_paths = [
                        os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg'),
                        os.path.join(config.FFMPEG_PATH, 'ffmpeg'),
                        config.FFMPEG_PATH
                    ]
                
                # Check all potential paths
                ffmpeg_found = False
                for path in potential_ffmpeg_paths:
                    if os.path.exists(path):
                        logger.info(f"FFmpeg executable found at: {path}")
                        ffmpeg_found = True
                        break
                
                if not ffmpeg_found:
                    logger.warning(f"FFmpeg executable not found at any of these locations: {potential_ffmpeg_paths}")
            except Exception as e:
                logger.error(f"Error checking FFmpeg paths: {str(e)}")
        else:
            logger.warning("FFmpeg path is not configured in config")
        
        # Try to download using pytube if available
        if PYTUBE_AVAILABLE:
            try:
                yt = YouTube(video_url)
                # Get the audio stream with highest quality
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                
                if not audio_stream:
                    logger.error(f"No audio stream found for {video_url}")
                    return None
                    
                # Download the audio
                # First, download as .mp4 and then convert to .mp3
                mp4_file = audio_stream.download(output_path=output_dir)
                base, ext = os.path.splitext(mp4_file)
                mp3_file = base + '.mp3'
                
                # Convert to mp3 using ffmpeg if available
                if config.FFMPEG_PATH:
                    try:
                        import platform
                        
                        # Find ffmpeg executable
                        ffmpeg_exe = None
                        if platform.system() == 'Windows':
                            potential_paths = [
                                os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg.exe'),
                                os.path.join(config.FFMPEG_PATH, 'ffmpeg.exe'),
                                config.FFMPEG_PATH if config.FFMPEG_PATH.endswith('.exe') else None
                            ]
                        else:
                            potential_paths = [
                                os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg'),
                                os.path.join(config.FFMPEG_PATH, 'ffmpeg'),
                                config.FFMPEG_PATH
                            ]
                        
                        # Filter out None values
                        potential_paths = [p for p in potential_paths if p]
                        
                        # Try each path
                        for path in potential_paths:
                            if os.path.exists(path):
                                ffmpeg_exe = path
                                logger.info(f"Using FFmpeg at: {ffmpeg_exe}")
                                break
                        
                        if not ffmpeg_exe:
                            logger.warning(f"FFmpeg executable not found at any of these locations: {potential_paths}")
                            # Try to use system ffmpeg
                            import shutil
                            ffmpeg_exe = shutil.which('ffmpeg')
                            if ffmpeg_exe:
                                logger.info(f"Using system FFmpeg at: {ffmpeg_exe}")
                            else:
                                logger.error("FFmpeg not found in system PATH")
                                # Just rename the file and return if no ffmpeg
                                os.rename(mp4_file, mp3_file)
                                logger.info(f"Downloaded YouTube audio to {mp3_file} (without conversion, renamed only)")
                                return mp3_file
                        
                        # Now convert with the found ffmpeg executable
                        logger.info(f"Converting downloaded file from {mp4_file} to {mp3_file} using FFmpeg at {ffmpeg_exe}")
                        
                        command = [
                            ffmpeg_exe,
                            '-i', mp4_file,
                            '-q:a', '0',
                            '-map', 'a',
                            mp3_file
                        ]
                        
                        # Run ffmpeg conversion
                        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                        
                        # Check if the process was successful
                        if process.returncode == 0:
                            # Remove the original mp4 file after successful conversion
                            os.remove(mp4_file)
                            logger.info(f"Successfully converted to MP3 at {mp3_file}")
                            return mp3_file
                        else:
                            # Log the error
                            stderr = process.stderr.decode('utf-8', errors='ignore')
                            logger.error(f"FFmpeg conversion failed: {stderr}")
                            # Just rename the file as fallback
                            os.rename(mp4_file, mp3_file)
                            return mp3_file
                    except Exception as e:
                        logger.error(f"FFmpeg conversion error: {str(e)}")
                        # If conversion fails, just rename the file
                        os.rename(mp4_file, mp3_file)
                        return mp3_file
                else:
                    # No ffmpeg available, just rename the file
                    os.rename(mp4_file, mp3_file)
                    logger.info(f"Downloaded YouTube audio to {mp3_file} (without conversion)")
                    return mp3_file
                
            except Exception as e:
                logger.error(f"Pytube download error: {str(e)}")
                # Fall back to yt-dlp if pytube fails
        
        # Try to download using yt-dlp if available        
        if YT_DLP_AVAILABLE:
            try:
                # Configure yt-dlp options
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': output_file.replace('.mp3', ''),  # yt-dlp adds .mp3 automatically
                    'quiet': True,
                    'no_warnings': True
                }
                
                # Add ffmpeg location if configured
                if config.FFMPEG_PATH:
                    # Find FFmpeg directory
                    import platform
                    import os
                    
                    ffmpeg_dir = None
                    if platform.system() == 'Windows':
                        potential_dirs = [
                            os.path.join(config.FFMPEG_PATH, 'bin'),
                            config.FFMPEG_PATH
                        ]
                    else:
                        potential_dirs = [
                            os.path.join(config.FFMPEG_PATH, 'bin'),
                            config.FFMPEG_PATH
                        ]
                    
                    # Check for directories containing ffmpeg
                    for directory in potential_dirs:
                        if os.path.exists(directory):
                            if platform.system() == 'Windows':
                                if os.path.exists(os.path.join(directory, 'ffmpeg.exe')):
                                    ffmpeg_dir = directory
                                    break
                            else:
                                if os.path.exists(os.path.join(directory, 'ffmpeg')):
                                    ffmpeg_dir = directory
                                    break
                    
                    # If found, add to options
                    if ffmpeg_dir:
                        ydl_opts['ffmpeg_location'] = ffmpeg_dir
                        logger.info(f"Using FFmpeg at {ffmpeg_dir} for yt-dlp")
                    else:
                        logger.warning(f"Could not find FFmpeg in {potential_dirs}, yt-dlp may fail")
                
                # Download the video
                logger.info(f"Attempting to download with yt-dlp, options: {ydl_opts}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                
                # Check if file exists
                if os.path.exists(output_file):
                    logger.info(f"Downloaded YouTube audio to {output_file}")
                    return output_file
                else:
                    # Try to find the file with a different extension
                    for ext in ['.mp3', '.m4a', '.webm']:
                        candidate = os.path.join(output_dir, f"{video_id}{ext}")
                        if os.path.exists(candidate):
                            # If not mp3, try to convert using ffmpeg
                            if ext != '.mp3' and config.FFMPEG_PATH:
                                try:
                                    import platform
                                    # Find ffmpeg executable
                                    ffmpeg_exe = None
                                    if platform.system() == 'Windows':
                                        potential_paths = [
                                            os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg.exe'),
                                            os.path.join(config.FFMPEG_PATH, 'ffmpeg.exe')
                                        ]
                                    else:
                                        potential_paths = [
                                            os.path.join(config.FFMPEG_PATH, 'bin', 'ffmpeg'),
                                            os.path.join(config.FFMPEG_PATH, 'ffmpeg')
                                        ]
                                    
                                    # Try each path
                                    for path in potential_paths:
                                        if os.path.exists(path):
                                            ffmpeg_exe = path
                                            break
                                    
                                    if not ffmpeg_exe:
                                        # Try to use system ffmpeg
                                        import shutil
                                        ffmpeg_exe = shutil.which('ffmpeg')
                                    
                                    if ffmpeg_exe:
                                        mp3_file = os.path.join(output_dir, f"{video_id}.mp3")
                                        
                                        command = [
                                            ffmpeg_exe,
                                            '-i', candidate,
                                            '-q:a', '0',
                                            '-map', 'a',
                                            mp3_file
                                        ]
                                        
                                        # Run ffmpeg conversion
                                        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                                        
                                        # Check if the process was successful
                                        if process.returncode == 0:
                                            # Remove the original file after successful conversion
                                            os.remove(candidate)
                                            logger.info(f"Converted {candidate} to {mp3_file}")
                                            return mp3_file
                                        else:
                                            # Log the error
                                            stderr = process.stderr.decode('utf-8', errors='ignore')
                                            logger.error(f"FFmpeg conversion failed: {stderr}")
                                            # Return the original file if conversion fails
                                            return candidate
                                    else:
                                        logger.warning("FFmpeg not found for conversion, using original file")
                                        return candidate
                                except Exception as e:
                                    logger.error(f"FFmpeg conversion error: {str(e)}")
                                    # Return the original file if conversion fails
                                    return candidate
                            
                            logger.info(f"Downloaded YouTube audio to {candidate}")
                            return candidate
                    
                    logger.error(f"Downloaded file not found at {output_file}")
                    return None
                    
            except Exception as e:
                logger.error(f"YT-DLP download error: {str(e)}")
        
        # Try a direct method with requests as a last resort
        try:
            # This is a very simple direct method that might work for some URLs
            logger.info("Attempting direct download as last resort")
            import requests
            from urllib.parse import parse_qs, urlparse
            
            # Get the video ID
            parsed_url = urlparse(video_url)
            video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            
            if not video_id:
                logger.error("Could not extract video ID for direct download")
                return None
            
            # Get the audio file URL - this method is not reliable and may break
            # It's only used as a last resort
            response = requests.get(f"https://www.youtube.com/get_video_info?video_id={video_id}")
            if response.status_code != 200:
                logger.error(f"Failed to get video info: HTTP {response.status_code}")
                return None
            
            # Parse the response to find audio URLs
            # This is a simplified version and might not work for all videos
            video_info = parse_qs(response.text)
            
            if 'url_encoded_fmt_stream_map' in video_info:
                stream_map = video_info['url_encoded_fmt_stream_map'][0]
                streams = stream_map.split(',')
                
                for stream in streams:
                    stream_data = parse_qs(stream)
                    if 'audio' in stream_data.get('type', [''])[0]:
                        audio_url = stream_data.get('url', [''])[0]
                        
                        if audio_url:
                            # Download the audio file
                            audio_response = requests.get(audio_url, stream=True)
                            if audio_response.status_code == 200:
                                output_file = os.path.join(output_dir, f"{video_id}.mp3")
                                
                                with open(output_file, 'wb') as f:
                                    for chunk in audio_response.iter_content(chunk_size=1024):
                                        if chunk:
                                            f.write(chunk)
                                            
                                logger.info(f"Successfully downloaded audio using direct method to {output_file}")
                                return output_file
            
            logger.error("Failed to find audio stream for direct download")
            return None
        except Exception as e:
            logger.error(f"Direct download error: {str(e)}")
            
        # If we've reached here, all methods failed
        logger.error("Failed to download YouTube audio. No available methods working. Please make sure FFmpeg is properly configured.")
        return None
    
    def process_music_request(self, query):
        """
        Process a natural language request to play music.
        
        Args:
            query (str): The user's query, e.g., "play Despacito", "mở bài hát Phép Màu"
            
        Returns:
            str: A response message
        """
        # Extract the song name from queries like "play X" or "mở bài hát X"
        song_name = self._extract_song_name(query)
        
        if not song_name:
            return "Không thể xác định bài hát bạn muốn nghe. Vui lòng thử lại với cú pháp như 'Mở bài hát [tên bài hát]'."
            
        # Search YouTube for the song
        logger.info(f"Searching YouTube for song: {song_name}")
        search_results = self.search_youtube(song_name, max_results=1)
        
        if not search_results:
            return f"Xin lỗi, không thể tìm thấy bài hát '{song_name}' trên YouTube."
            
        # Get the first result
        video = search_results[0]
        video_url = video['url']
        
        # Download the audio
        logger.info(f"Downloading audio for: {video['title']}")
        audio_file = self.download_youtube_audio(video_url)
        
        if not audio_file:
            return f"Xin lỗi, không thể tải âm thanh từ '{video['title']}'. Vui lòng thử lại sau."
        
        # Update track metadata with YouTube info
        metadata = {
            'title': video['title'],
            'artist': video['channel'],
            'album': 'YouTube',
            'cover_url': video['thumbnail'],
            'source': 'youtube',
            'video_id': video['id'],
            'duration': 0  # Will be updated when playing
        }
        
        # Play the audio file
        if self.play_file(audio_file):
            # Update metadata manually since the file might not have ID3 tags
            self.currently_playing_metadata = metadata
            self._notify_callbacks('metadata_updated', metadata)
            
            return f"Đang phát '{video['title']}' từ YouTube"
        else:
            return f"Xin lỗi, không thể phát '{video['title']}'. Vui lòng thử lại sau."
    
    def _extract_song_name(self, query):
        """
        Extract the song name from a query like "play X" or "mở bài hát X".
        
        Args:
            query (str): The user's query
            
        Returns:
            str: The extracted song name
        """
        query = query.lower().strip()
        
        patterns = [
            # Vietnamese patterns
            r'mở\s+bài\s+(?:hát|)\s+(.*)',  
            r'phát\s+bài\s+(?:hát|)\s+(.*)', 
            r'nghe\s+bài\s+(?:hát|)\s+(.*)',  
            r'(?:bật|mở)\s+nhạc\s+(.*)', 
            
            r'play\s+(.*)', 
            r'listen\s+to\s+(.*)',
            
            r'(?:youtube|yt|video|audio|song|music|bài hát|nhạc|ca khúc)\s+(.*)',
            
            r'(?:mở|phát|bật|play|listen|youtube|yt)\s+(.*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match and match.group(1):
                # Clean up any trailing noise words
                song_name = match.group(1).strip()
                # Remove common stop words at the end
                noise_words = ['nhé', 'nha', 'đi', 'ạ', 'không', 'please', 'for me', 'cho tôi', 'cho mình']
                for word in noise_words:
                    if song_name.endswith(f" {word}"):
                        song_name = song_name[:-(len(word)+1)].strip()
                
                return song_name
        
        return query

    def play_pending_audio(self):
        """
        Play the pending audio file that was stored earlier.
        This should be called after TTS is complete.
        
        Returns:
            bool: True if playback started, False otherwise
        """
        import os
        try:
            if not self.pending_playback_file:
                logger.warning("No pending audio file to play")
                return False
                
            if not os.path.exists(self.pending_playback_file):
                logger.error(f"Pending audio file not found: {self.pending_playback_file}")
                self.pending_playback_file = None
                self.pending_playback_info = None
                return False
                
            logger.info(f"Playing pending audio: {os.path.basename(self.pending_playback_file)}")
            
            # Stop any current playback first
            if self.is_playing or self.is_paused:
                self.stop()
            
            # Add to playlist and play
            result = self.play_file(self.pending_playback_file)
            
            # Reset pending playback
            self.pending_playback_file = None
            self.pending_playback_info = None
            
            return result
        except Exception as e:
            logger.error(f"Error playing pending audio: {str(e)}")
            self.pending_playback_file = None
            self.pending_playback_info = None
            return False