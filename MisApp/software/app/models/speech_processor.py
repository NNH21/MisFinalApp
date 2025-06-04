import os
import sys
import time
import tempfile
import threading
import pygame
import subprocess
import shutil
import hashlib
import queue
import re
from gtts import gTTS
import speech_recognition as sr
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication  # Add this import for QApplication access

# Handle both relative and absolute imports
try:
    from ..utils import config, logger
except ImportError:
    try:
        from utils import config, logger
    except ImportError:
        # Fallback for testing
        class MockConfig:
            ENABLE_TTS_CACHE = True
            SPEECH_PLAYBACK_SPEED = 1.3
            AUDIO_THRESHOLD = 500
            HOTWORD_PHRASE = "ê cu"
            HOTWORD_SENSITIVITY = 0.5
            AUDIO_DEVICE_INDEX = None
            AUDIO_SAMPLE_RATE = 16000
            ENABLE_HOTWORD_DETECTION = True
            DEFAULT_LANGUAGE = 'vi'
        config = MockConfig()
        logger = None

class SpeechProcessor(QObject):
    """
    Handles text-to-speech and speech-to-text processing for MIS Assistant.
    Uses Google Text-to-Speech (gTTS) to convert text to speech.
    Uses SpeechRecognition library for speech-to-text.
    """
    
    speech_ready = pyqtSignal(str) 
    speech_started = pyqtSignal()   
    speech_finished = pyqtSignal() 
    hotword_detected = pyqtSignal() 
    voice_command_received = pyqtSignal(str) 
    
    def __init__(self):
        super().__init__()  # Khởi tạo QObject
        
        try:
            if pygame.mixer.get_init() is None:
                # Initialize with these parameters for better compatibility
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                logger.info("Pygame mixer initialized successfully")
            else:
                logger.info("Pygame mixer was already initialized")
            
            pygame.mixer.set_num_channels(8)  
            self.tts_channel = pygame.mixer.Channel(1)  
            self.tts_channel.set_volume(0.7)  
                
            logger.info("TTS audio channel initialized")
        except Exception as e:
            logger.error(f"Error initializing pygame mixer: {str(e)}")
            # Try to re-initialize with alternative settings
            try:
                pygame.mixer.quit()
                time.sleep(0.5)
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=4096)
                pygame.mixer.set_num_channels(8)
                self.tts_channel = pygame.mixer.Channel(1)
                self.tts_channel.set_volume(0.7)
                logger.info("Pygame mixer initialized with fallback settings")
            except Exception as e2:
                logger.error(f"Failed to initialize pygame mixer even with fallback settings: {str(e2)}")
                self.tts_channel = None
        
        self.is_speaking = False
        self.is_listening = False
        self.hotword_listening = False  # Flag to track hotword detection status
        self.temp_dir = tempfile.gettempdir()
        self.language = config.DEFAULT_LANGUAGE
        self.cache_dir = os.path.join(self.temp_dir, "tts_cache")
        
        # Thiết lập tốc độ phát âm thanh mặc định
        self.playback_speed = getattr(config, 'SPEECH_PLAYBACK_SPEED', 1.2)  # Giảm từ 1.5 xuống 1.2 để nghe rõ hơn
        
        # Mức giới hạn tốc độ để tránh âm thanh biến dạng quá mức
        self.min_speed = 0.8  # Giữ nguyên mức 0.8
        self.max_speed = 1.8  # Giảm từ 2.0 xuống 1.8 để đảm bảo chất lượng
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = config.AUDIO_THRESHOLD  # Adjust sensitivity
        self.recognizer.dynamic_energy_threshold = True        # Add mutex locks for thread safety
        self.speaking_lock = threading.Lock()
        self.listening_lock = threading.Lock()
        self.hotword_lock = threading.Lock()  # Lock for hotword detection state
        
        # Thêm queue xử lý song song âm thanh với văn bản
        self.tts_queue = queue.Queue()
        self.tts_thread = threading.Thread(target=self._process_tts_queue, daemon=True)
        self.tts_thread.start()
        
        # Thêm biến để lưu trữ tệp âm thanh đã tạo sẵn
        self.prepared_audio_file = None
        
        # Thêm biến để lưu trữ trạng thái nhạc trước khi phát TTS
        self.music_was_playing = False
        self.current_sound = None  # Keep track of the current TTS sound
        
        # Start hotword detection if enabled
        if config.ENABLE_HOTWORD_DETECTION:
            self._start_google_hotword_detection()
        
        # Connect signals
        self.hotword_detected.connect(self._on_hotword_detected)
        
        logger.info("Speech processor initialized")
    
    def set_playback_speed(self, speed):
        """
        Đặt tốc độ phát âm thanh
        
        Args:
            speed (float): Tốc độ phát, từ 0.5 đến 2.5
                           1.0 là tốc độ bình thường, 2.0 là nhanh gấp đôi
        """
        if speed < self.min_speed:
            speed = self.min_speed
        elif speed > self.max_speed:
            speed = self.max_speed
            
        self.playback_speed = speed
        logger.info(f"Speech playback speed set to: {speed}x")
    
    def get_playback_speed(self):
        """
        Lấy tốc độ phát âm thanh hiện tại
        
        Returns:
            float: Tốc độ phát hiện tại
        """
        return self.playback_speed
    
    def _adjust_audio_speed(self, input_file, speed=None):
        """
        Điều chỉnh tốc độ của file âm thanh sử dụng FFmpeg.
        
        Args:
            input_file (str): Đường dẫn đến file đầu vào
            speed (float): Tốc độ phát (mặc định: sử dụng self.playback_speed)
            
        Returns:
            str: Đường dẫn đến file đã điều chỉnh tốc độ, hoặc file gốc nếu thất bại
        """
        if speed is None:
            speed = self.playback_speed
            
        # Nếu tốc độ là 1.0, không cần xử lý
        if abs(speed - 1.0) < 0.01:
            return input_file
            
        try:
            # Tạo tên file đầu ra có tốc độ trong tên
            file_dir = os.path.dirname(input_file)
            file_name = os.path.basename(input_file)
            base_name, ext = os.path.splitext(file_name)
            output_file = os.path.join(file_dir, f"{base_name}_speed{speed:.1f}{ext}")
            
            # Kiểm tra xem file đã tồn tại chưa (trường hợp giá trị tốc độ giống nhau)
            if os.path.exists(output_file):
                logger.info(f"Using existing speed-adjusted file: {output_file}")
                return output_file
                
            # Xác định đường dẫn FFmpeg
            ffmpeg_path = getattr(config, 'FFMPEG_PATH', None)
            
            if ffmpeg_path:
                # Sử dụng đường dẫn FFmpeg được cấu hình
                if os.name == 'nt':  # Windows
                    ffmpeg_exe = os.path.join(ffmpeg_path, 'ffmpeg.exe')
                else:  # Linux/Mac
                    ffmpeg_exe = os.path.join(ffmpeg_path, 'ffmpeg')
            else:
                # Sử dụng ffmpeg trên PATH
                ffmpeg_exe = 'ffmpeg'
                
            # Điều chỉnh tốc độ với giữ nguyên pitch (atempo hỗ trợ giá trị từ 0.5 đến 2.0)
            # Đối với giá trị nằm ngoài phạm vi đó, chúng ta sẽ sử dụng nhiều bộ lọc atempo 
            # ghép nối với nhau
            if 0.5 <= speed <= 2.0:
                filter_complex = f"atempo={speed:.3f}"
            elif speed > 2.0:
                # Chia thành nhiều giai đoạn, mỗi giai đoạn <= 2.0
                # Ví dụ: 2.5 = 1.25 * 2.0
                remaining_speed = speed
                filter_parts = []
                
                while remaining_speed > 1.0:
                    if remaining_speed >= 2.0:
                        filter_parts.append("atempo=2.0")
                        remaining_speed /= 2.0
                    else:
                        filter_parts.append(f"atempo={remaining_speed:.3f}")
                        remaining_speed = 1.0
                        
                filter_complex = ','.join(filter_parts)
            else:  # speed < 0.5
                # Ví dụ: 0.3 = 0.6 * 0.5
                remaining_speed = speed
                filter_parts = []
                
                while remaining_speed < 1.0:
                    if remaining_speed <= 0.5:
                        filter_parts.append("atempo=0.5")
                        remaining_speed /= 0.5
                    else:
                        filter_parts.append(f"atempo={remaining_speed:.3f}")
                        remaining_speed = 1.0
                        
                filter_complex = ','.join(filter_parts)
                
            # Thiết lập command để chạy FFmpeg
            command = [
                ffmpeg_exe,
                '-i', input_file,
                '-filter_complex', filter_complex,
                '-y',  # Ghi đè file nếu đã tồn tại
                output_file
            ]
              # Chạy command với tham số ẩn console
            logger.info(f"Adjusting audio speed to {speed}x: {' '.join(command)}")
            
            # Tạo startupinfo để ẩn console trên Windows
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                          startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            
            # Xác minh file đầu ra tồn tại và có kích thước
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"Successfully created speed-adjusted audio: {output_file}")
                return output_file
            else:
                logger.error("Failed to create speed-adjusted audio file (empty or not created)")
                return input_file
                
        except Exception as e:
            logger.error(f"Error adjusting audio speed: {str(e)}")
            # Trả về file gốc nếu có lỗi
            return input_file
    def prepare_speech(self, text, language='vi'):
        """
        Chuẩn bị trước âm thanh từ văn bản - không phát ra.
        Thêm vào hàng đợi để tạo ra song song trong khi hiển thị tin nhắn.
        
        Args:
            text (str): Văn bản cần chuyển đổi
            language (str): Mã ngôn ngữ
            
        Returns:
            bool: True nếu đã thêm vào hàng đợi thành công
        """
        try:
            # Sử dụng văn bản nguyên bản không qua xử lý
            self.tts_queue.put((text, language))
            logger.info(f"Added text to TTS queue: {text[:50]}{'...' if len(text) > 50 else ''}")
            return True
        except Exception as e:
            logger.error(f"Error adding text to TTS queue: {str(e)}")
            return False
    
    def _process_tts_queue(self):
        """
        Xử lý hàng đợi TTS trong một thread riêng biệt.
        Tạo trước các tệp âm thanh để phát nhanh hơn.
        """
        while True:
            try:
                # Lấy mục tiếp theo từ hàng đợi
                text, language = self.tts_queue.get()
                
                # Sử dụng văn bản gốc không qua xử lý
                cleaned_text = text
                
                # Kiểm tra cache trước khi tạo mới
                text_hash = hashlib.md5(cleaned_text.encode('utf-8')).hexdigest()[:10]
                cached_file = os.path.join(self.cache_dir, f"{text_hash}.mp3")
                
                if os.path.exists(cached_file) and config.ENABLE_TTS_CACHE:
                    # Sử dụng file cache nếu có
                    self.prepared_audio_file = cached_file
                    self.speech_ready.emit(text)
                    logger.info(f"Using cached speech: {os.path.basename(cached_file)}")
                else:
                    # Tạo tệp âm thanh mới
                    audio_file = self._generate_speech_file(cleaned_text, language)
                    
                    # Lưu tệp âm thanh đã tạo
                    if audio_file:
                        # Điều chỉnh tốc độ trước khi lưu vào biến prepared_audio_file
                        speed_adjusted_file = self._adjust_audio_speed(audio_file)
                        self.prepared_audio_file = speed_adjusted_file
                        # Phát signal báo hiệu âm thanh đã sẵn sàng
                        self.speech_ready.emit(text)
                        logger.info(f"Speech prepared and ready: {os.path.basename(speed_adjusted_file)}")
                
                # Đánh dấu công việc đã hoàn thành
                self.tts_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in TTS queue processing: {str(e)}")
                try:
                    self.tts_queue.task_done()
                except:
                    pass
            
            # Giảm thời gian sleep để xử lý nhanh hơn
            time.sleep(0.05)  # Giảm từ 0.1 xuống 0.05
    def _generate_speech_file(self, text, language='vi'):
        """
        Tạo tệp âm thanh từ văn bản mà không phát ra.
        
        Args:
            text (str): Văn bản cần chuyển đổi
            language (str): Mã ngôn ngữ
            
        Returns:
            str: Đường dẫn đến tệp âm thanh hoặc None nếu thất bại
        """
        try:
            # Sử dụng văn bản gốc
            cleaned_text = text
            
            # Create a hash of the text for caching
            text_hash = hashlib.md5(cleaned_text.encode('utf-8')).hexdigest()[:10]
            cached_file = os.path.join(self.cache_dir, f"{text_hash}.mp3")
            
            # Return cached file if it exists and caching is enabled
            if os.path.exists(cached_file) and config.ENABLE_TTS_CACHE:
                logger.info(f"Using cached TTS audio: {cached_file}")
                return cached_file
                
            # Generate speech with gTTS
            logger.info(f"Generating speech for text: {cleaned_text[:50]}{'...' if len(cleaned_text) > 50 else ''}")
            
            # Make sure caching directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Generate temp file name (use a unique name to avoid conflicts)
            unique_id = f"{text_hash}_{int(time.time() * 1000) % 10000}"
            temp_file = os.path.join(self.cache_dir, f"temp_{unique_id}.mp3")
            
            # Initialize gTTS with error handling
            try:
                tts = gTTS(text=cleaned_text, lang=language, slow=False)
            except Exception as e:
                logger.error(f"Error initializing gTTS: {str(e)}")
                return None
                
            # Save to temporary file
            try:
                tts.save(temp_file)
            except Exception as e:
                logger.error(f"Error saving TTS audio: {str(e)}")
                # Try to clean up temp file if it exists
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return None
                
            # Verify file was created with content
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 100:  # 100 bytes min
                logger.error(f"TTS generated empty or invalid file: {temp_file}")
                return None
                
            # If caching is enabled, copy (not move) the file to avoid conflicts
            if config.ENABLE_TTS_CACHE and temp_file != cached_file:
                try:
                    # Use copy instead of move to avoid file access conflicts
                    if not os.path.exists(cached_file):
                        shutil.copy2(temp_file, cached_file)
                        logger.info(f"Speech generated and saved to: {cached_file}")
                        # Keep the temp file as backup but return the cached path
                        return cached_file
                except Exception as e:
                    logger.error(f"Error copying temp file to cache: {str(e)}")
                    # Continue with temp file if copy fails
            
            # Log success and return the temp file path
            logger.info(f"Speech generated and saved to: {temp_file}")
            return temp_file
            
        except Exception as e:
            logger.error(f"Error in _generate_speech_file: {str(e)}")
            return None
    def text_to_speech(self, text, language='vi', volume=1.0, play=True):
        """
        Convert text to speech.
        
        Args:
            text (str): Text to convert to speech
            language (str): Language code ('vi' for Vietnamese, 'en' for English, etc.)
            volume (float): Volume adjustment, from 0.0 to 1.0
            play (bool): Whether to play the audio immediately
            
        Returns:
            str: Path to the generated audio file or None if failed
        """
        try:
            # Sử dụng văn bản gốc không qua xử lý
            cleaned_text = text
            
            # Nếu có file âm thanh đã tạo sẵn, sử dụng nó
            if self.prepared_audio_file and play:
                audio_file = self.prepared_audio_file
                self.prepared_audio_file = None  # Reset để không dùng lại
                if os.path.exists(audio_file):
                    return self._play_audio(audio_file)
                else:
                    logger.warning(f"Prepared audio file not found: {audio_file}")
            
            # Create a hash of the text for caching
            text_hash = hashlib.md5(cleaned_text.encode('utf-8')).hexdigest()[:10]
            cached_file = os.path.join(self.cache_dir, f"{text_hash}.mp3")
            
            # Return cached file if it exists and caching is enabled
            if os.path.exists(cached_file) and config.ENABLE_TTS_CACHE:
                logger.info(f"Using cached TTS audio: {cached_file}")
                if play:
                    # Điều chỉnh tốc độ file và phát nó
                    adjusted_file = self._adjust_audio_speed(cached_file)
                    return self._play_audio(adjusted_file)
                return cached_file
                
            # Generate speech with gTTS
            logger.info(f"Generating speech for text: {cleaned_text[:50]}{'...' if len(cleaned_text) > 50 else ''}")
            
            # Make sure caching directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Generate temp file name with unique identifier to avoid conflicts
            unique_id = f"{text_hash}_{int(time.time() * 1000) % 10000}"
            temp_file = os.path.join(self.cache_dir, f"temp_{unique_id}.mp3")
            
            # Initialize gTTS with error handling
            try:
                tts = gTTS(text=cleaned_text, lang=language, slow=False)
            except Exception as e:
                logger.error(f"Error initializing gTTS: {str(e)}")
                return None
                
            # Save to temporary file
            try:
                tts.save(temp_file)
            except Exception as e:
                logger.error(f"Error saving TTS audio: {str(e)}")
                # Try to clean up temp file if it exists
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return None
                
            # Verify file was created with content
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 100:  # 100 bytes min
                logger.error(f"TTS generated empty or invalid file: {temp_file}")
                return None
                
            # If caching is enabled, copy (not move) the file to avoid conflicts
            final_file = temp_file
            if config.ENABLE_TTS_CACHE:
                try:
                    # Use copy instead of move to avoid file access conflicts
                    if not os.path.exists(cached_file):
                        shutil.copy2(temp_file, cached_file)
                        logger.info(f"Speech generated and saved to cache: {cached_file}")
                        final_file = cached_file
                except Exception as e:
                    logger.error(f"Error copying temp file to cache: {str(e)}")
                    # Continue with temp file if copy fails
            
            # Log success
            logger.info(f"Speech generated and saved to: {final_file}")
            
            # Play the audio if requested
            if play:
                # Điều chỉnh tốc độ của file trước khi phát
                adjusted_file = self._adjust_audio_speed(final_file)
                return self._play_audio(adjusted_file)
                
            return final_file
            
        except Exception as e:
            logger.error(f"Error in text_to_speech: {str(e)}")
            return None
    
    def play_prepared_speech(self):
        """
        Phát âm thanh đã được chuẩn bị trước đó.
        
        Returns:
            bool: True nếu phát thành công, False nếu không
        """
        if not self.prepared_audio_file:
            logger.warning("No prepared audio file available")
            return False
        
        # Verify the file actually exists
        if not os.path.exists(self.prepared_audio_file):
            logger.warning(f"Prepared audio file not found: {self.prepared_audio_file}")
            self.prepared_audio_file = None  # Reset since file is invalid
            return False
            
        audio_file = self.prepared_audio_file
        self.prepared_audio_file = None  # Reset để không dùng lại
        
        result = self._play_audio(audio_file)
        return result is not None

    def _play_audio(self, audio_file, volume=1.0):
        """
        Play an audio file using pygame.
        
        Args:
            audio_file (str): Path to the audio file to play
            volume (float): Volume level (0.0 to 1.0)
            
        Returns:
            str: Path to the audio file if successfully played, None if failed
        """
        try:
            # Validate file exists
            if not os.path.exists(audio_file):
                logger.error(f"Audio file not found: {audio_file}")
                return None
                
            # Check if pygame is properly initialized
            if pygame.mixer.get_init() is None:
                logger.error("Pygame mixer is not initialized")
                return None
                
            # Set the speaking flag
            with self.speaking_lock:
                self.is_speaking = True
                
            # Load the sound file with error handling
            try:
                sound = pygame.mixer.Sound(audio_file)
                self.current_sound = sound
            except Exception as e:
                logger.error(f"Failed to load sound file: {str(e)}")
                with self.speaking_lock:
                    self.is_speaking = False
                return None
                
            # Set the volume (clamp between 0 and 1)
            volume = max(0.0, min(1.0, volume))
            sound.set_volume(volume)
            
            # Check if music is playing and pause it
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause()
                    self.music_was_playing = True
                else:
                    self.music_was_playing = False
            except:
                self.music_was_playing = False
                
            # Play the sound on the TTS channel
            try:
                # Play the sound and get the channel it's playing on
                self.tts_channel.play(sound)
                
                # Emit the started signal
                self.speech_started.emit()
                
                # Start a thread to monitor when playback finishes
                monitor_thread = threading.Thread(
                    target=self._monitor_playback_completion,
                    args=(self.tts_channel,),
                    daemon=True
                )
                monitor_thread.start()
                
                return audio_file
                
            except Exception as e:
                logger.error(f"Failed to play sound: {str(e)}")
                with self.speaking_lock:
                    self.is_speaking = False
                return None
                
        except Exception as e:
            logger.error(f"Error in _play_audio: {str(e)}")
            with self.speaking_lock:
                self.is_speaking = False
            return None
            
    def _monitor_playback_completion(self, channel):
        """
        Monitor the playback channel and emit signal when playback finishes.
        
        Args:
            channel (pygame.mixer.Channel): The channel to monitor
        """
        try:
            # Wait until the channel is not busy anymore
            while channel.get_busy():
                time.sleep(0.1)
                
            # At this point, playback has finished
            logger.info("Audio playback completed")
            
            # Resume music if it was playing before
            if self.music_was_playing:
                try:
                    pygame.mixer.music.unpause()
                except:
                    pass
                self.music_was_playing = False
                
            # Reset the current sound
            self.current_sound = None
                
            # Clear the speaking flag
            with self.speaking_lock:
                self.is_speaking = False
                
            # Emit the finished signal
            self.speech_finished.emit()
            
        except Exception as e:
            logger.error(f"Error in playback completion monitor: {str(e)}")
            with self.speaking_lock:
                self.is_speaking = False
                
    def stop_speaking(self):
        """Stop any ongoing TTS playback."""
        try:
            # Stop the TTS channel
            if pygame.mixer.get_init() is not None:
                self.tts_channel.stop()
                
            # Reset flags and resources
            with self.speaking_lock:
                self.is_speaking = False
                
            self.current_sound = None
            
            # Resume music if it was playing
            if self.music_was_playing:
                try:
                    pygame.mixer.music.unpause()
                except:
                    pass
                self.music_was_playing = False
                
            logger.info("TTS playback stopped manually")
            
        except Exception as e:
            logger.error(f"Error stopping TTS playback: {str(e)}")
            
    def is_currently_speaking(self):
        """
        Check if currently speaking with proper state verification.
        
        Returns:
            bool: True if currently speaking, False otherwise
        """
        with self.speaking_lock:
            return self.is_speaking
        
    def is_currently_listening(self):
        """
        Check if currently listening with proper state verification.
        
        Returns:
            bool: True if currently listening, False otherwise
        """
        with self.listening_lock:
            return self.is_listening
            
    def set_listening_status(self, is_listening):
        """
        Set the listening status flag with proper state management.
        
        Args:
            is_listening (bool): The listening status to set
        """
        with self.listening_lock:
            if self.is_listening != is_listening:
                logger.info(f"Changing listening status from {self.is_listening} to {is_listening}")
                self.is_listening = is_listening
                
                # If stopping listening, ensure cleanup
                if not is_listening:
                    try:
                        # Stop any ongoing recognition
                        if hasattr(self, 'recognizer'):
                            self.recognizer.stop()
                    except Exception as e:
                        logger.error(f"Error stopping recognition: {str(e)}")

    def _hotword_detection_loop(self):
        """
        Background thread that listens for hotword detection.
        Continuously monitors for the hotword phrase to activate voice input.
        """
        logger.info("Hotword detection thread started")
        
        # Initialize mic for hotword detection
        microphone = sr.Microphone(device_index=config.AUDIO_DEVICE_INDEX)
        
        # Get the hotword phrase from config
        hotword_phrase = getattr(config, 'HOTWORD_PHRASE', 'ê cu').lower()
        logger.info(f"Listening for hotword: '{hotword_phrase}'")
        
        # Set hotword sensitivity
        hotword_sensitivity = getattr(config, 'HOTWORD_SENSITIVITY', 0.5)
        
        with self.hotword_lock:
            self.hotword_listening = True
        
        try:
            while True:
                # Check if we should stop the thread
                with self.hotword_lock:
                    if not self.hotword_listening:
                        break
                
                # Don't listen for hotword if we're already listening for a command
                # or if we're currently speaking
                if self.is_listening or self.is_speaking:
                    time.sleep(0.5)
                    continue
                
                with microphone as source:
                    try:
                        # Adjust for ambient noise before each detection
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        
                        # Set timeout and phrase_time_limit to make detection more responsive
                        audio = self.recognizer.listen(
                            source, 
                            timeout=1, 
                            phrase_time_limit=3
                        )
                        
                        # Try to recognize the audio
                        text = self.recognizer.recognize_google(audio, language=self.language).lower()
                        
                        # Check if the hotword is in the recognized text
                        if hotword_phrase in text:
                            logger.info(f"Hotword detected: '{text}'")
                            # Emit signal to activate the microphone
                            self.hotword_detected.emit()
                            # Small delay to prevent repeated detection
                            time.sleep(1)
                    
                    except sr.WaitTimeoutError:
                        # Timeout is expected; just continue
                        pass
                    except sr.UnknownValueError:
                        # Speech wasn't understood; just continue
                        pass
                    except Exception as e:
                        # Log other errors but keep the thread running
                        logger.error(f"Error in hotword detection: {str(e)}")
                        time.sleep(1)
                
                # Small sleep to prevent high CPU usage
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Hotword detection thread error: {str(e)}")
        finally:
            with self.hotword_lock:
                self.hotword_listening = False
            logger.info("Hotword detection thread stopped")
            
    def speech_to_text(self, callback_function=None, timeout=5, language=None):
        """
        Convert speech to text using the device microphone.
        
        Args:
            callback_function: Function to call with the recognized text
            timeout (int): Maximum listening time in seconds
            language (str): Language code (None to use default from config)
            
        Returns:
            str: Recognized text, or None if error or nothing recognized
        """
        if language is None:
            language = self.language
            
        # Set listening flag - use a mutex for thread safety
        with self.listening_lock:
            # If already listening, don't start another session
            if self.is_listening:
                logger.warning("Speech recognition already in progress")
                if callback_function:
                    callback_function(None)
                return None
                
            self.is_listening = True
            
        # Get microphone device
        try:
            device_index = config.AUDIO_DEVICE_INDEX  # From config
            microphone = sr.Microphone(device_index=device_index)
        except Exception as e:
            logger.error(f"Error initializing microphone: {str(e)}")
            with self.listening_lock:
                self.is_listening = False
            if callback_function:
                callback_function(None)
            return None
            
        result_text = None
        
        try:
            with microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info(f"Listening for speech (timeout: {timeout}s)")
                
                # Listen for speech
                try:
                    audio = self.recognizer.listen(source, timeout=timeout)
                except sr.WaitTimeoutError:
                    logger.info("Speech recognition timeout - no speech detected")
                    with self.listening_lock:
                        self.is_listening = False
                    if callback_function:
                        callback_function(None)
                    return None
                    
            # Try to recognize the speech
            try:
                logger.info("Processing speech recognition...")
                result_text = self.recognizer.recognize_google(audio, language=language)
                logger.info(f"Speech recognized: '{result_text}'")
            except sr.UnknownValueError:
                logger.info("Speech recognition could not understand audio")
                result_text = None
            except sr.RequestError as e:
                logger.error(f"Could not request results from Google Speech Recognition service: {str(e)}")
                result_text = None
                
        except Exception as e:
            logger.error(f"Error in speech recognition: {str(e)}")
            result_text = None
            
        finally:
            # Clear listening flag
            with self.listening_lock:
                self.is_listening = False
                
            # Call the callback function with the result
            if callback_function:
                callback_function(result_text)
                
            return result_text

    def _on_hotword_detected(self):
        """
        Handle hotword detection by starting voice command recognition.
        """
        try:
            # Don't start if already listening or speaking
            if self.is_listening or self.is_speaking:
                return
                
            logger.info("Hotword detected, starting voice command recognition")
              # Start speech recognition with callback
            self.speech_to_text(
                callback_function=self._on_voice_command,
                timeout=5,
                language=self.language
            )
            
        except Exception as e:
            logger.error(f"Error in hotword detection handler: {str(e)}")
            
    def _on_voice_command(self, text):
        """
        Handle recognized voice command.
        
        Args:
            text (str): The recognized voice command text
        """
        try:
            if text:
                logger.info(f"Voice command received: '{text}'")
                # Emit signal with the recognized text
                self.voice_command_received.emit(text)
            else:
                logger.info("No voice command recognized")
                
        except Exception as e:
            logger.error(f"Error handling voice command: {str(e)}")
    
    def _start_google_hotword_detection(self):
        """Start Google Speech Recognition based hotword detection"""
        self.hotword_thread = threading.Thread(target=self._hotword_detection_loop, daemon=True)
        self.hotword_thread.start()
        logger.info(f"Google Speech Recognition hotword detection started with phrase: '{config.HOTWORD_PHRASE}'")
    
    def stop_hotword_detection(self):
        """Stop hotword detection"""
        # Stop Google Speech Recognition hotword detection
        with self.hotword_lock:
            self.hotword_listening = False
            
        logger.info("Hotword detection stopped")
    
    def restart_hotword_detection(self):
        """Restart hotword detection with current settings"""
        self.stop_hotword_detection()
        time.sleep(0.5)  # Give time for cleanup
        
        if config.ENABLE_HOTWORD_DETECTION:
            self._start_google_hotword_detection()
    
    def get_hotword_status(self) -> dict:
        """Get current hotword detection status"""
        status = {
            "enabled": config.ENABLE_HOTWORD_DETECTION,
            "phrase": config.HOTWORD_PHRASE,
            "google_fallback": True
        }
        
        with self.hotword_lock:
            status["google_listening"] = self.hotword_listening
                
        return status

    # ...existing methods...