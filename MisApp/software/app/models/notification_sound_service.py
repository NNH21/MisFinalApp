"""
MIS Smart Assistant - Notification Sound Service
Module for playing notification sounds for system events like Bluetooth connection/disconnection
"""

import os
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    pygame = None

from ..utils import logger, config


class NotificationSoundService(QObject):
    """Service for playing notification sounds for system events."""
    
    # Qt signals
    sound_played = pyqtSignal(str) 
    sound_error = pyqtSignal(str) 
    
    def __init__(self):
        """Initialize the notification sound service."""
        super().__init__()
        
        self.sounds_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources', 'sounds'
        )
        
        # Available notification sounds
        self.notification_sounds = {
            'bluetooth_connected': os.path.join(self.sounds_dir, 'on_bluetooth.mp3'),
            'bluetooth_disconnected': os.path.join(self.sounds_dir, 'off_bluetooth.mp3'),
            'general_beep': os.path.join(self.sounds_dir, 'beep.mp3'),
            'completion': os.path.join(self.sounds_dir, 'completion.mp3'),
            'alarm': os.path.join(self.sounds_dir, 'alarm.mp3')
        }
        
        # Volume settings
        self.notification_volume = 0.7 
        self.is_enabled = True  
        
        # Threading
        self.playback_lock = threading.Lock()
        
        # Initialize pygame if available
        self._initialize_pygame()
        
        logger.info("Notification Sound Service initialized")
    
    def _initialize_pygame(self):
        """Initialize pygame mixer for notification sounds."""
        if not PYGAME_AVAILABLE:
            logger.warning("Pygame not available. Notification sounds will be disabled.")
            return False
        
        try:
            # Check if pygame mixer is already initialized
            mixer_info = pygame.mixer.get_init()
            if not mixer_info:
                init_configs = [
                    {"frequency": 44100, "size": -16, "channels": 2, "buffer": 1024},
                    {"frequency": 44100, "size": -16, "channels": 2, "buffer": 2048},
                    {"frequency": 22050, "size": -16, "channels": 2, "buffer": 1024},
                    {}  # Default settings
                ]
                
                for config in init_configs:
                    try:
                        pygame.mixer.init(**config)
                        if pygame.mixer.get_init():
                            logger.info(f"Pygame mixer initialized for notifications with config: {config}")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to init pygame with config {config}: {e}")
                        continue
                
                if not pygame.mixer.get_init():
                    logger.error("All pygame mixer initialization attempts failed")
                    return False
            else:
                logger.info(f"Using existing pygame mixer initialization: {mixer_info}")
            
            # Set number of channels to allow multiple notification sounds
            try:
                current_channels = pygame.mixer.get_num_channels()
                if current_channels < 8:
                    pygame.mixer.set_num_channels(8)
                    logger.info(f"Set pygame channels to 8 (was {current_channels})")
            except Exception as e:
                logger.warning(f"Could not set pygame channels: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer for notifications: {e}")
            return False
    
    def set_enabled(self, enabled):
        """Enable or disable notification sounds.
        
        Args:
            enabled (bool): True to enable sounds, False to disable
        """
        self.is_enabled = enabled
        logger.info(f"Notification sounds {'enabled' if enabled else 'disabled'}")
    
    def set_volume(self, volume):
        """Set the volume for notification sounds.
        
        Args:
            volume (float): Volume level (0.0 to 1.0)
        """
        self.notification_volume = max(0.0, min(1.0, volume))
        logger.info(f"Notification volume set to {self.notification_volume:.2f}")
    
    def play_bluetooth_connected(self):
        """Play Bluetooth connection sound."""
        return self._play_notification_sound('bluetooth_connected')
    
    def play_bluetooth_disconnected(self):
        """Play Bluetooth disconnection sound."""
        return self._play_notification_sound('bluetooth_disconnected')
    
    def play_general_beep(self):
        """Play general beep sound."""
        return self._play_notification_sound('general_beep')
    
    def play_completion_sound(self):
        """Play completion sound."""
        return self._play_notification_sound('completion')
    
    def play_alarm_sound(self):
        """Play alarm sound."""
        return self._play_notification_sound('alarm')
    
    def play_custom_sound(self, sound_file_path):
        """Play a custom sound file.
        
        Args:
            sound_file_path (str): Path to the sound file
        """
        if not os.path.exists(sound_file_path):
            logger.warning(f"Custom sound file not found: {sound_file_path}")
            return False
        
        return self._play_sound_file(sound_file_path)
    
    def _play_notification_sound(self, sound_type):
        """Play a predefined notification sound.
        
        Args:
            sound_type (str): Type of notification sound to play
        """
        if not self.is_enabled:
            logger.debug(f"Notification sounds disabled, skipping {sound_type}")
            return False
        
        if sound_type not in self.notification_sounds:
            logger.warning(f"Unknown notification sound type: {sound_type}")
            return False
        
        sound_file = self.notification_sounds[sound_type]
        return self._play_sound_file(sound_file)
    
    def _play_sound_file(self, sound_file_path):
        """Play a sound file using pygame.
        
        Args:
            sound_file_path (str): Path to the sound file to play
            
        Returns:
            bool: True if sound started playing, False otherwise
        """
        if not PYGAME_AVAILABLE:
            logger.warning("Cannot play notification sound: pygame not available")
            return False
        
        if not self.is_enabled:
            return False
        
        try:
            # Check if file exists
            if not os.path.exists(sound_file_path):
                logger.warning(f"Notification sound file not found: {sound_file_path}")
                # Emit error signal
                try:
                    self.sound_error.emit(f"Sound file not found: {os.path.basename(sound_file_path)}")
                except RuntimeError:
                    pass  # Object may have been deleted
                return False
            
            # Play sound in a separate thread to avoid blocking
            threading.Thread(
                target=self._play_sound_thread,
                args=(sound_file_path,),
                daemon=True
            ).start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error playing notification sound {sound_file_path}: {e}")
            try:
                self.sound_error.emit(f"Error playing sound: {str(e)}")
            except RuntimeError:
                pass  # Object may have been deleted
            return False
    
    def _play_sound_thread(self, sound_file_path):
        """Play sound in a separate thread.
        
        Args:
            sound_file_path (str): Path to the sound file to play
        """
        with self.playback_lock:
            try:
                # Ensure pygame mixer is initialized
                if not pygame.mixer.get_init():
                    self._initialize_pygame()
                
                if not pygame.mixer.get_init():
                    logger.error("Cannot play notification sound: pygame mixer not initialized")
                    return
                
                # Load and play the sound with better error handling
                try:
                    sound = pygame.mixer.Sound(sound_file_path)
                    sound.set_volume(self.notification_volume)
                except pygame.error as e:
                    logger.error(f"Pygame cannot load sound file {sound_file_path}: {e}")
                    return
                except Exception as e:
                    logger.error(f"Error loading sound file {sound_file_path}: {e}")
                    return
                
                # Find an available channel to play the sound
                channel = pygame.mixer.find_channel()
                if channel:
                    try:
                        channel.play(sound)
                        
                        # Wait for the sound to finish
                        while channel.get_busy():
                            time.sleep(0.1)
                        
                        # Only emit signal if object still exists (check before emit)
                        try:
                            self.sound_played.emit(sound_file_path)
                        except RuntimeError:
                            # Object was deleted, ignore
                            pass
                        
                        logger.debug(f"Successfully played notification sound: {os.path.basename(sound_file_path)}")
                    except Exception as e:
                        logger.error(f"Error playing sound on channel: {e}")
                else:
                    logger.warning("No available audio channels for notification sound")
                
            except Exception as e:
                logger.error(f"Error in sound playback thread: {e}")
                # Try to emit error signal, but handle if object was deleted
                try:
                    self.sound_error.emit(f"Playback error: {str(e)}")
                except RuntimeError:
                    # Object was deleted, ignore
                    pass
    
    def stop_all_sounds(self):
        """Stop all currently playing notification sounds."""
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            try:
                pygame.mixer.stop()
                logger.info("Stopped all notification sounds")
            except Exception as e:
                logger.error(f"Error stopping notification sounds: {e}")
    
    def get_available_sounds(self):
        """Get list of available notification sounds.
        
        Returns:
            dict: Dictionary of sound types and their file paths
        """
        available = {}
        for sound_type, file_path in self.notification_sounds.items():
            if os.path.exists(file_path):
                available[sound_type] = file_path
        return available
    
    def validate_sound_files(self):
        """Validate that all notification sound files exist.
        
        Returns:
            dict: Dictionary with validation results
        """
        results = {}
        for sound_type, file_path in self.notification_sounds.items():
            results[sound_type] = {
                'file_path': file_path,
                'exists': os.path.exists(file_path),
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
        return results


# Create a global instance
notification_service = NotificationSoundService()
