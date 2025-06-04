# File: software/app/models/multimedia/__init__.py
from .audio_player import AudioPlayer
from .youtube_downloader import YouTubeDownloader
from .playlist_manager import PlaylistManager
from .media_converter import MediaConverter
from .metadata_manager import MetadataManager

# Facade class để giữ tương thích với mã hiện tại
class MultimediaService:
    """
    Facade class tích hợp tất cả các dịch vụ multimedia.
    Duy trì API tương thích với MultimediaService cũ.
    """
    
    def __init__(self):
        """Initialize the multimedia service components."""
        # Initialize các thành phần
        self.media_converter = MediaConverter()
        self.metadata_manager = MetadataManager()
        self.audio_player = AudioPlayer(self.metadata_manager, self.media_converter)
        self.youtube_downloader = YouTubeDownloader(self.media_converter)
        self.playlist_manager = PlaylistManager(self.audio_player)
        
        # Kết nối sự kiện giữa các thành phần
        self.audio_player.register_metadata_provider(self.metadata_manager)
        
        # Forward các signals từ audio_player
        self.playback_started = self.audio_player.playback_started
        self.playback_stopped = self.audio_player.playback_stopped
        self.playback_paused = self.audio_player.playback_paused
        self.playback_position_changed = self.audio_player.playback_position_changed
        self.playback_finished = self.audio_player.playback_finished
        self.playback_error = self.audio_player.playback_error
        self.metadata_updated = self.audio_player.metadata_updated
        
        # For compatibility with original MultimediaService
        self.is_paused = False
        self.track_duration = 0
        
        # Biến lưu trữ cho phát nhạc trì hoãn sau khi TTS hoàn thành
        self.pending_playback_file = None
        self.pending_playback_info = None
        
        # Track loop mode state
        self.loop_mode = False
        
    # --- API tương thích với mã hiện tại ---
    
    # Audio playback methods
    def play(self, media_path=None):
        return self.audio_player.play(media_path)
    
    def pause(self):
        self.is_paused = True
        return self.audio_player.pause()
    
    def resume(self):
        self.is_paused = False
        return self.audio_player.resume()
    
    def stop(self):
        self.is_paused = False
        return self.audio_player.stop()
    
    def set_volume(self, volume):
        return self.audio_player.set_volume(volume)
    
    def get_volume(self):
        return self.audio_player.get_volume()
    
    def set_position(self, position_seconds):
        return self.audio_player.set_position(position_seconds)
    
    def get_position(self):
        return self.audio_player.get_position()
    
    # Add method to check if media is currently playing
    def is_currently_playing(self):
        return self.audio_player.is_currently_playing()
    
    # Playlist methods
    def next_track(self):
        return self.playlist_manager.next_track()
    
    def previous_track(self):
        return self.playlist_manager.previous_track()
    
    def set_playlist(self, file_paths):
        return self.playlist_manager.set_playlist(file_paths)
    
    def add_to_playlist(self, file_path):
        return self.playlist_manager.add_to_playlist(file_path)
    
    def get_playlist(self):
        return self.playlist_manager.get_playlist()
    
    def play_file(self, file_path, add_to_playlist=True):
        if add_to_playlist:
            self.playlist_manager.add_to_playlist(file_path)
        return self.audio_player.play(file_path)
    
    # Set loop mode method
    def set_loop_mode(self, is_looping):
        """Set the loop mode for playback - will repeat current track when enabled."""
        self.loop_mode = is_looping
        # Forward to the audio player if available
        if self.audio_player and hasattr(self.audio_player, 'set_loop_mode'):
            return self.audio_player.set_loop_mode(is_looping)
        return True
    
    # YouTube methods
    def search_youtube(self, query, max_results=5):
        return self.youtube_downloader.search_youtube(query, max_results)
    
    def download_youtube_audio(self, video_url, output_dir=None):
        return self.youtube_downloader.download_audio(video_url, output_dir)
    
    def process_music_request(self, query):
        """
        Process natural language music request.
        
        Args:
            query (str): The user's voice query for music playback
            
        Returns:
            str: Response message about the music request
        """
        from ...utils import logger
        import os
        
        # Extract song name from the query
        song_name = self._extract_song_name(query)
        
        if not song_name:
            return "Không thể xác định bài hát bạn muốn nghe. Vui lòng thử lại với cú pháp như 'Mở bài hát [tên bài hát]'."
            
        # Search and download using YouTubeDownloader
        logger.info(f"Searching for '{song_name}' using YouTube Data API")
        video_info = self.youtube_downloader.search_and_download(song_name)
        
        if not video_info or 'audio_file' not in video_info:
            return f"Xin lỗi, không thể tìm thấy bài hát '{song_name}'."
        
        # Store the audio file for delayed playback after TTS is complete
        audio_file = video_info['audio_file']
        
        # Check if the file exists
        if not os.path.exists(audio_file):
            return f"Xin lỗi, không thể tải xuống âm thanh cho '{video_info.get('title', song_name)}'."
            
        # Set the audio for playback once TTS is complete
        self.set_pending_playback(audio_file, video_info)
        
        # Return response message (will be spoken before music plays)
        return f"Đang phát '{video_info.get('title', song_name)}'"
    
    def _extract_song_name(self, query):
        """Extract song name from voice query."""
        return self.youtube_downloader.extract_song_name(query)
    
    def is_media_command(self, command):
        """Check if command is media-related."""
        media_keywords = [
            "play", "pause", "stop", "next", "prev", "previous", "volume",
            "âm lượng", "phát", "bắt đầu", "tạm dừng", "dừng", "ngừng",
            "tiếp theo", "bài tiếp", "bài kế", "trước", "bài trước", "tắt tiếng",
            "tăng", "giảm", "tối đa", "tối thiểu", "mute", "bài gì", "bài nào"
        ]
        command = command.lower().strip()
        return any(keyword in command for keyword in media_keywords)
    
    def process_media_command(self, command):
        """Process media control command."""
        command = command.lower().strip()
        
        # Handle playback controls
        if any(word in command for word in ["play", "phát", "bắt đầu"]):
            if self.audio_player.is_paused:
                return self.audio_player.resume()
            else:
                return self.audio_player.play()
        
        # Handle pause/stop
        if any(word in command for word in ["pause", "tạm dừng"]):
            return self.audio_player.pause()
            
        if any(word in command for word in ["stop", "dừng", "ngừng"]):
            return self.audio_player.stop()
        
        # Handle track navigation
        if any(word in command for word in ["next", "tiếp theo", "bài tiếp", "bài kế"]):
            return self.playlist_manager.next_track()
            
        if any(word in command for word in ["prev", "previous", "trước", "bài trước"]):
            return self.playlist_manager.previous_track()
        
        # Handle volume
        if any(word in command for word in ["volume", "âm lượng"]):
            # Volume logic here - simplified for brevity
            if "tăng" in command or "up" in command:
                current = self.audio_player.get_volume()
                return self.audio_player.set_volume(min(1.0, current + 0.1))
            elif "giảm" in command or "down" in command:
                current = self.audio_player.get_volume()
                return self.audio_player.set_volume(max(0.0, current - 0.1))
            
        # Information request
        if any(word in command for word in ["what", "which", "current", "bài gì", "bài nào"]):
            # Get current track info
            track_info = self.audio_player.get_track_info()
            if self.audio_player.is_currently_playing():
                return f"Đang phát: {track_info['title']} - {track_info['artist']}"
            else:
                return "Không có bài hát nào đang phát"
                
        return "Không hiểu lệnh âm nhạc"
    
    # Add a new method to get track metadata
    def get_track_metadata(self, file_path):
        """Get metadata for a track from its file path"""
        try:
            if not file_path:
                return None
                
            metadata = self.metadata_manager.get_track_metadata(file_path)
            return metadata
        except Exception as e:
            from ...utils import logger
            logger.error(f"Error getting track metadata: {str(e)}")
            return {
                'title': os.path.basename(file_path) if file_path else 'Unknown Title',
                'artist': 'Unknown Artist',
                'album': 'Unknown Album'
            }
            
    # Property to access current_track_index from playlist_manager
    @property
    def current_index(self):
        """Get the current track index in the playlist."""
        return self.playlist_manager.get_current_track_index()
    
    def set_pending_playback(self, file_path, video_info=None):
        """
        Store audio file for delayed playback after TTS is complete.
        
        Args:
            file_path (str): Path to audio file to play
            video_info (dict): Optional metadata about the video
            
        Returns:
            bool: True if set successfully
        """
        from ...utils import logger
        try:
            self.pending_playback_file = file_path
            self.pending_playback_info = video_info
            logger.info(f"Set pending playback: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            logger.error(f"Error setting pending playback: {str(e)}")
            return False
            
    def play_pending_audio(self):
        """
        Play the pending audio file that was stored earlier.
        This should be called after TTS is complete.
        
        Returns:
            bool: True if playback started, False otherwise
        """
        from ...utils import logger
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