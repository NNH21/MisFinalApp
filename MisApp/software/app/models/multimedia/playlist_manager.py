# File: software/app/models/multimedia/playlist_manager.py
from typing import List, Optional
import os
from ...utils import logger

class PlaylistManager:
    """
    Component for managing audio playlists.
    """
    
    def __init__(self, audio_player=None):
        """Initialize the playlist manager."""
        self.audio_player = audio_player
        self.playlist = []
        self.current_track_index = -1
        logger.info("Playlist manager initialized")
    
    def set_audio_player(self, audio_player):
        """Set the audio player reference."""
        self.audio_player = audio_player
    
    def get_playlist(self) -> List[str]:
        """Get the current playlist."""
        return self.playlist
    
    def set_playlist(self, file_paths: List[str]) -> bool:
        """
        Set the current playlist.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Success status
        """
        try:
            # Validate paths
            valid_paths = []
            for path in file_paths:
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    logger.warning(f"File not found: {path}")
            
            # Update playlist
            self.playlist = valid_paths
            self.current_track_index = -1
            
            logger.info(f"Playlist updated with {len(valid_paths)} tracks")
            return True
                
        except Exception as e:
            logger.error(f"Error in set_playlist: {str(e)}")
            return False
    
    def add_to_playlist(self, file_path: str) -> bool:
        """
        Add a file to the playlist.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Success status
        """
        try:
            # Validate path
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False
            
            if file_path not in self.playlist:
                self.playlist.append(file_path)
                logger.info(f"Added to playlist: {os.path.basename(file_path)}")
                
                if self.current_track_index == -1 and len(self.playlist) == 1:
                    self.current_track_index = 0
            else:
                self.current_track_index = self.playlist.index(file_path)
                logger.info(f"Track already in playlist, set as current: {os.path.basename(file_path)}")
            
            return True
                
        except Exception as e:
            logger.error(f"Error in add_to_playlist: {str(e)}")
            return False
    
    def clear_playlist(self) -> bool:
        """Clear the current playlist."""
        try:
            self.playlist = []
            self.current_track_index = -1
            logger.info("Playlist cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing playlist: {str(e)}")
            return False
    
    def next_track(self) -> bool:
        """
        Play the next track in the playlist.
        
        Returns:
            Success status
        """
        if not self.audio_player:
            logger.error("No audio player set")
            return False
            
        if not self.playlist or len(self.playlist) == 0:
            logger.warning("Playlist is empty")
            return False
            
        try:
            # Increment index
            self.current_track_index += 1
            
            # Loop back if at end
            if self.current_track_index >= len(self.playlist):
                self.current_track_index = 0
                
            # Get track and play
            next_track = self.playlist[self.current_track_index]
            
            return self.audio_player.play(next_track)
                
        except Exception as e:
            logger.error(f"Error in next_track: {str(e)}")
            return False
    
    def previous_track(self) -> bool:
        """
        Play the previous track.
        
        Returns:
            Success status
        """
        if not self.audio_player:
            logger.error("No audio player set")
            return False
            
        if not self.playlist or len(self.playlist) == 0:
            logger.warning("Playlist is empty")
            return False
            
        try:
            # Get current position
            current_position = self.audio_player.get_position()
            
            if current_position <= 3 and self.current_track_index > 0:
                self.current_track_index -= 1
            elif current_position <= 3 and self.current_track_index == 0:
                # Wrap to end of playlist
                self.current_track_index = len(self.playlist) - 1
                
            # Get track and play
            track = self.playlist[self.current_track_index]
            
            return self.audio_player.play(track)
                
        except Exception as e:
            logger.error(f"Error in previous_track: {str(e)}")
            return False
    
    def jump_to_track(self, index: int) -> bool:
        """
        Jump to a specific track by index.
        
        Args:
            index: Track index
            
        Returns:
            Success status
        """
        if not self.audio_player:
            logger.error("No audio player set")
            return False
            
        if not self.playlist or len(self.playlist) == 0:
            logger.warning("Playlist is empty")
            return False
            
        try:
            # Validate index
            if index < 0 or index >= len(self.playlist):
                logger.error(f"Invalid track index: {index}")
                return False
                
            # Set index and play
            self.current_track_index = index
            track = self.playlist[index]
            
            return self.audio_player.play(track)
                
        except Exception as e:
            logger.error(f"Error in jump_to_track: {str(e)}")
            return False
    
    def get_current_track_index(self) -> int:
        """Get the current track index."""
        return self.current_track_index
    
    def shuffle_playlist(self) -> bool:
        """
        Shuffle the playlist.
        
        Returns:
            Success status
        """
        try:
            import random
            
            if not self.playlist or len(self.playlist) <= 1:
                return False
                
            # Get current track
            current_track = self.playlist[self.current_track_index] if self.current_track_index >= 0 else None
            
            # Shuffle
            random.shuffle(self.playlist)
            
            # Update index if we have a current track
            if current_track:
                try:
                    self.current_track_index = self.playlist.index(current_track)
                except ValueError:
                    self.current_track_index = 0
            
            logger.info("Playlist shuffled")
            return True
                
        except Exception as e:
            logger.error(f"Error shuffling playlist: {str(e)}")
            return False