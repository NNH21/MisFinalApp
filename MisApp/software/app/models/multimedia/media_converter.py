# File: software/app/models/multimedia/media_converter.py
import os
import platform
import subprocess
import zipfile
import shutil
from ...utils import logger, config

class MediaConverter:
    """
    Component for converting media between formats.
    Handles FFmpeg detection and media conversion operations.
    """
    
    def __init__(self):
        """Initialize the media converter."""
        self.ffmpeg_path = None
        self._extract_ffmpeg_if_needed()
        self._detect_ffmpeg()
        logger.info("Media converter initialized")
    
    def _extract_ffmpeg_if_needed(self):
        """
        Attempt to extract FFmpeg from the bundled zip file if needed.
        """
        # Define paths
        resources_bin_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            'resources', 'bin'
        )
        ffmpeg_dir = os.path.join(resources_bin_dir, 'ffmpeg')
        
        ffmpeg_zip_paths = [
            os.path.join(resources_bin_dir, 'ffmpeg.zip'),
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                'software', 'resources', 'bin', 'ffmpeg.zip'
            ),
            os.path.join(resources_bin_dir, 'temp_ffmpeg.zip')
        ]
        
        if os.path.exists(ffmpeg_dir) and os.listdir(ffmpeg_dir):
            logger.info(f"FFmpeg directory already exists at {ffmpeg_dir}")
            return True
            
        os.makedirs(ffmpeg_dir, exist_ok=True)
        
        for zip_file_path in ffmpeg_zip_paths:
            if os.path.exists(zip_file_path):
                try:
                    if not zipfile.is_zipfile(zip_file_path):
                        logger.warning(f"File exists but is not a valid zip file: {zip_file_path}")
                        continue
                        
                    logger.info(f"Extracting FFmpeg from {zip_file_path}...")
                    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                        zip_ref.extractall(ffmpeg_dir)
                    
                    if os.listdir(ffmpeg_dir):
                        logger.info(f"FFmpeg extracted successfully to {ffmpeg_dir}")
                        return True
                    else:
                        logger.warning(f"Extraction appeared to succeed but directory is empty: {ffmpeg_dir}")
                except zipfile.BadZipFile:
                    logger.warning(f"Invalid zip file format: {zip_file_path}")
                except Exception as e:
                    logger.error(f"Error extracting FFmpeg from {zip_file_path}: {str(e)}")
        
        try:
            system = platform.system()
            if system == 'Windows':
                from subprocess import PIPE, run
                result = run("where ffmpeg", stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                if result.returncode == 0 and result.stdout.strip():
                    ffmpeg_path = os.path.dirname(result.stdout.strip().split('\n')[0])
                    logger.info(f"Using system FFmpeg found at: {ffmpeg_path}")
                    return True
            else:
                # Unix-like systems
                from subprocess import PIPE, run
                result = run("which ffmpeg", stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                if result.returncode == 0 and result.stdout.strip():
                    ffmpeg_path = os.path.dirname(result.stdout.strip())
                    logger.info(f"Using system FFmpeg found at: {ffmpeg_path}")
                    return True
        except Exception as e:
            logger.error(f"Error locating system FFmpeg: {str(e)}")
            
        logger.error("Could not extract FFmpeg from any available zip file")
        return False
    
    def _detect_ffmpeg(self):
        """
        Detect FFmpeg installation.
        Sets self.ffmpeg_path if found.
        """
        # First check config
        if config.FFMPEG_PATH and self._validate_ffmpeg_path(config.FFMPEG_PATH):
            self.ffmpeg_path = config.FFMPEG_PATH
            logger.info(f"Using FFmpeg from config: {self.ffmpeg_path}")
            return
                
        system = platform.system()
        
        paths_to_check = []
        
        # Application bundled ffmpeg
        bundled_ffmpeg_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                'resources', 'bin', 'ffmpeg', 'bin'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                'resources', 'bin', 'ffmpeg')
        ]
        paths_to_check.extend(bundled_ffmpeg_paths)
        
        # System-specific paths
        if system == 'Windows':
            windows_paths = [
                os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'FFmpeg', 'bin'),
                os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'FFmpeg', 'bin'),
                # Check additional common Windows locations
                os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\Users\\' + os.getenv('USERNAME') + '\\AppData\\Local'), 'FFmpeg', 'bin'),
                os.path.join(os.environ.get('APPDATA', 'C:\\Users\\' + os.getenv('USERNAME') + '\\AppData\\Roaming'), 'FFmpeg', 'bin')
            ]
            paths_to_check.extend(windows_paths)
        else:
            # Unix-like systems (Linux/macOS)
            unix_paths = [
                '/usr/bin',
                '/usr/local/bin',
                '/opt/local/bin',
                '/opt/ffmpeg/bin',
                '/usr/local/opt/ffmpeg/bin',  # Common macOS Homebrew location
                os.path.expanduser('~/bin')
            ]
            paths_to_check.extend(unix_paths)
            
        # Check each path
        for path in paths_to_check:
            if self._validate_ffmpeg_path(path):
                self.ffmpeg_path = path
                logger.info(f"Found FFmpeg at: {self.ffmpeg_path}")
                # Update config.FFMPEG_PATH for other components to use
                config.FFMPEG_PATH = self.ffmpeg_path
                return
                
        # Last resort: use which/where command
        try:
            if system == 'Windows':
                where_cmd = 'where ffmpeg'
            else:
                where_cmd = 'which ffmpeg'
                
            result = subprocess.run(where_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                ffmpeg_path = result.stdout.strip()
                if os.path.exists(ffmpeg_path):
                    self.ffmpeg_path = os.path.dirname(ffmpeg_path)
                    logger.info(f"Found system FFmpeg at: {self.ffmpeg_path}")
                    # Update config.FFMPEG_PATH for other components to use
                    config.FFMPEG_PATH = self.ffmpeg_path
                    return
        except Exception as e:
            logger.warning(f"Error looking for FFmpeg in PATH: {str(e)}")
            
        logger.warning("FFmpeg not found, conversion features will be limited")
    
    def _validate_ffmpeg_path(self, path):
        """Check if path contains FFmpeg binaries."""
        if not path or not os.path.exists(path):
            return False
            
        # Check for ffmpeg executable
        system = platform.system()
        if system == 'Windows':
            ffmpeg_exe = os.path.join(path, 'ffmpeg.exe')
        else:
            ffmpeg_exe = os.path.join(path, 'ffmpeg')
            
        if not os.path.exists(ffmpeg_exe):
            # Check if ffmpeg might be in a subdirectory
            for root, dirs, files in os.walk(path):
                for file in files:
                    if system == 'Windows' and file.lower() == 'ffmpeg.exe':
                        self.ffmpeg_path = root
                        return True
                    elif system != 'Windows' and file.lower() == 'ffmpeg':
                        if os.access(os.path.join(root, file), os.X_OK):
                            self.ffmpeg_path = root
                            return True
            return False
            
        # Verify executable permissions on Unix systems
        if system != 'Windows' and not os.access(ffmpeg_exe, os.X_OK):
            logger.warning(f"FFmpeg found at {ffmpeg_exe} but is not executable")
            return False
            
        return True
    
    def get_ffmpeg_path(self):
        """Get the FFmpeg directory path."""
        return self.ffmpeg_path
    
    def get_ffmpeg_executable(self):
        """Get the full path to the FFmpeg executable."""
        if not self.ffmpeg_path:
            return None
            
        system = platform.system()
        if system == 'Windows':
            return os.path.join(self.ffmpeg_path, 'ffmpeg.exe')
        else:
            return os.path.join(self.ffmpeg_path, 'ffmpeg')
    
    def convert_to_mp3(self, input_file, output_file=None):
        """
        Convert audio file to MP3 format.
        
        Args:
            input_file: Path to input file
            output_file: Path to output file (default: same as input with .mp3)
            
        Returns:
            Success status
        """
        try:
            if not self.ffmpeg_path:
                logger.error("FFmpeg not available for conversion")
                return False
                
            # Validate input file
            if not os.path.exists(input_file):
                logger.error(f"Input file not found: {input_file}")
                return False
                
            # Set default output file if not provided
            if not output_file:
                base, _ = os.path.splitext(input_file)
                output_file = f"{base}.mp3"
                
            # Get ffmpeg executable path
            ffmpeg_exe = self.get_ffmpeg_executable()
            if not ffmpeg_exe:
                logger.error("FFmpeg executable not found")
                return False
                
            # Build command
            command = [
                ffmpeg_exe,
                '-i', input_file,
                '-q:a', '0',  # Highest quality
                '-map', 'a',  # Only audio
                '-y',  # Overwrite output file if it exists
                output_file
            ]
            
            # Run conversion
            logger.info(f"Converting {input_file} to {output_file}")
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            
            # Check result
            if process.returncode == 0:
                logger.info(f"Conversion successful: {output_file}")
                return True
            else:
                error_msg = process.stderr.decode('utf-8', errors='replace')
                logger.error(f"FFmpeg error: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error in convert_to_mp3: {str(e)}")
            return False
    
    def extract_audio(self, video_file, output_file=None):
        """
        Extract audio from video file.
        
        Args:
            video_file: Path to video file
            output_file: Path to output audio file
            
        Returns:
            Success status
        """
        try:
            if not self.ffmpeg_path:
                logger.error("FFmpeg not available for extraction")
                return False
                
            # Validate input file
            if not os.path.exists(video_file):
                logger.error(f"Video file not found: {video_file}")
                return False
                
            # Set default output file if not provided
            if not output_file:
                base, _ = os.path.splitext(video_file)
                output_file = f"{base}.mp3"
                
            # Get ffmpeg executable path
            ffmpeg_exe = self.get_ffmpeg_executable()
            if not ffmpeg_exe:
                logger.error("FFmpeg executable not found")
                return False
                
            # Build command
            command = [
                ffmpeg_exe,
                '-i', video_file,
                '-q:a', '0',
                '-map', 'a',
                '-y',  # Overwrite output file if it exists
                output_file
            ]
            
            # Run extraction
            logger.info(f"Extracting audio from {video_file} to {output_file}")
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            
            # Check result
            if process.returncode == 0:
                logger.info(f"Audio extraction successful: {output_file}")
                return True
            else:
                error_msg = process.stderr.decode('utf-8', errors='replace')
                logger.error(f"FFmpeg error: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error in extract_audio: {str(e)}")
            return False