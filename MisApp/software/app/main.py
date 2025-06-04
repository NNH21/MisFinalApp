import sys
import os
import time
import traceback
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

# Cải thiện việc xử lý đường dẫn
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = current_dir
software_dir = os.path.dirname(app_dir)
project_dir = os.path.dirname(software_dir)
root_dir = os.path.dirname(project_dir)


paths = [root_dir, project_dir, software_dir, app_dir]
for path in paths:
    if path not in sys.path:
        sys.path.insert(0, path)

# Debug: Print paths for troubleshooting
print(f"Current directory: {os.getcwd()}")
print(f"App directory: {app_dir}")
print(f"Path setup: {sys.path[:5]}")

# Import modules
try:
    from software.app.ui.main_window import MainWindow
    from software.app.utils import config, logger
    # Sử dụng cấu trúc module mới
    from software.app.models.multimedia import MultimediaService
    print("Core modules imported successfully")
except ImportError as e:
    print(f"Failed to import core modules: {e}")
    print(f"sys.path: {sys.path}")
    traceback.print_exc()
    sys.exit(1)

def setup_resources():
    """
    Set up application resources, creates necessary directories and initializes media libraries.
    """
    try:
        import os
        import pygame
        import sys
        import zipfile
        import shutil
        import traceback
        import platform
        from software.app.utils import logger, config
        
        # Initialize paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        resources_dir = os.path.abspath(os.path.join(current_dir, '../../resources'))
        software_resources_dir = os.path.abspath(os.path.join(current_dir, '../resources'))
        bin_dir = os.path.join(resources_dir, 'bin')
        software_bin_dir = os.path.join(software_resources_dir, 'bin')
        
        # Ensure resource directories exist
        os.makedirs(os.path.join(resources_dir, 'icons'), exist_ok=True)
        os.makedirs(os.path.join(resources_dir, 'sounds'), exist_ok=True)
        os.makedirs(os.path.join(resources_dir, 'weather_icons'), exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(software_bin_dir, exist_ok=True)
        
        media_cache_dir = os.path.join(software_resources_dir, 'media_cache')
        os.makedirs(media_cache_dir, exist_ok=True)
        config.MEDIA_CACHE_DIR = media_cache_dir
        
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.set_num_channels(8)  # Allow multiple audio streams
            logger.info("Pygame mixer initialized successfully with optimal settings")
        except pygame.error as e:
            logger.warning(f"Failed to initialize pygame mixer: {e}")
            try:
                pygame.mixer.init()
                logger.info("Pygame mixer initialized with default settings")
            except pygame.error as e:
                logger.error(f"Failed to initialize pygame mixer with default settings: {e}")
                
        ffmpeg_dir = os.path.join(software_bin_dir, 'ffmpeg')
        os.makedirs(ffmpeg_dir, exist_ok=True)
        
        # Kiểm tra xem FFmpeg có cần được giải nén không
        ffmpeg_executable = os.path.join(ffmpeg_dir, 'bin', 'ffmpeg.exe' if platform.system() == 'Windows' else 'ffmpeg')
        if not os.path.exists(ffmpeg_executable):
            logger.info("FFmpeg not found, attempting to extract...")
            
            ffmpeg_zip_paths = [
                os.path.join(software_bin_dir, 'ffmpeg.zip'),
                os.path.join(bin_dir, 'temp_ffmpeg.zip'),
                os.path.join(bin_dir, 'ffmpeg.zip')
            ]
            
            ffmpeg_extracted = False
            
            for zip_path in ffmpeg_zip_paths:
                if os.path.exists(zip_path):
                    try:

                        if not zipfile.is_zipfile(zip_path):
                            logger.warning(f"File exists but is not a valid zip file: {zip_path}")
                            continue
                            
                        logger.info(f"Extracting FFmpeg from {zip_path}...")
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(ffmpeg_dir)
                            
          
                        if os.path.exists(ffmpeg_executable):
                            try:
                                from subprocess import PIPE, run
                                result = run([ffmpeg_executable, '-version'], stdout=PIPE, stderr=PIPE, universal_newlines=True)
                                if result.returncode == 0:
                                    logger.info(f"FFmpeg extracted and verified successfully: {result.stdout.split('\n')[0]}")
                                    ffmpeg_extracted = True
                                    break
                                else:
                                    logger.warning(f"FFmpeg executable test failed: {result.stderr}")
                            except Exception as e:
                                logger.warning(f"Failed to test FFmpeg executable: {str(e)}")
                        else:
                            logger.warning(f"FFmpeg executable not found after extraction at: {ffmpeg_executable}")
                    except zipfile.BadZipFile:
                        logger.warning(f"Invalid zip file format: {zip_path}")
                    except Exception as e:
                        logger.error(f"Error extracting {zip_path}: {str(e)}")
            
            if not ffmpeg_extracted:
                logger.warning("Could not extract FFmpeg. Some multimedia features may not work.")
                try:
                    if platform.system() == 'Windows':
                        from subprocess import PIPE, run
                        result = run("where ffmpeg", stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                        if result.returncode == 0 and result.stdout.strip():
                            ffmpeg_path = os.path.dirname(result.stdout.strip().split('\n')[0])
                            test_result = run([os.path.join(ffmpeg_path, 'ffmpeg.exe'), '-version'], 
                                            stdout=PIPE, stderr=PIPE, universal_newlines=True)
                            if test_result.returncode == 0:
                                config.FFMPEG_PATH = ffmpeg_path
                                logger.info(f"Using system FFmpeg found at: {ffmpeg_path}")
                            else:
                                logger.warning("System FFmpeg found but failed verification test")
                    else:
                        from subprocess import PIPE, run
                        result = run("which ffmpeg", stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                        if result.returncode == 0 and result.stdout.strip():
                            ffmpeg_path = os.path.dirname(result.stdout.strip())
                            test_result = run([os.path.join(ffmpeg_path, 'ffmpeg'), '-version'], 
                                            stdout=PIPE, stderr=PIPE, universal_newlines=True)
                            if test_result.returncode == 0:
                                config.FFMPEG_PATH = ffmpeg_path
                                logger.info(f"Using system FFmpeg found at: {ffmpeg_path}")
                            else:
                                logger.warning("System FFmpeg found but failed verification test")
                except Exception as e:
                    logger.error(f"Error locating system FFmpeg: {str(e)}")
        else:
            try:
                from subprocess import PIPE, run
                result = run([ffmpeg_executable, '-version'], stdout=PIPE, stderr=PIPE, universal_newlines=True)
                if result.returncode == 0:
                    config.FFMPEG_PATH = os.path.dirname(ffmpeg_executable)
                    logger.info(f"Using existing FFmpeg at: {config.FFMPEG_PATH}")
                else:
                    logger.warning("Existing FFmpeg executable failed verification test")
            except Exception as e:
                logger.error(f"Error verifying existing FFmpeg: {str(e)}")
        
        logger.info("Resources setup completed successfully")
        return True

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        logger.error(f"Error during resource setup: {e}")
        traceback.print_exc()
        return False

def exception_hook(exctype, value, tb):
    """
    Custom exception hook to log uncaught exceptions.
    
    Args:
        exctype: Exception type
        value: Exception value
        tb: Traceback object
    """
    try:
        logger.critical(f"Uncaught exception: {exctype.__name__}: {value}")
        logger.critical(''.join(traceback.format_tb(tb)))
        print(f"CRITICAL ERROR: {exctype.__name__}: {value}", file=sys.stderr)
        traceback.print_tb(tb, file=sys.stderr)
        
        if "QObject" in str(value) or "QThread" in str(value):
            try:
                from PyQt5.QtWidgets import QApplication
                
                if QApplication.instance():
                    active_windows = QApplication.instance().topLevelWidgets()
                    logger.critical(f"Active windows: {len(active_windows)}")
                    
                    for i, window in enumerate(active_windows):
                        logger.critical(f"Window {i}: {window.__class__.__name__}, visible: {window.isVisible()}")
                        
                logger.critical("This appears to be a Qt threading issue. Please ensure Qt objects are only accessed from the main thread.")
            except Exception as e:
                logger.critical(f"Failed to collect Qt debug info: {str(e)}")
    except Exception as e:
        
        print(f"ERROR IN EXCEPTION HANDLER: {str(e)}", file=sys.stderr)
    
    sys.__excepthook__(exctype, value, tb)

def main():
    """Main entry point for the MIS Smart Assistant application."""

    setup_resources()
    
    sys.excepthook = exception_hook
    
    logger.info("MIS Smart Assistant starting up")
    
    try:

        app = QApplication(sys.argv)
        app.setApplicationName("MIS Smart Assistant")
        
        app.setApplicationDisplayName("MIS Smart Assistant")
        
        window = MainWindow()
        window.show()
        
        logger.info("MIS Smart Assistant UI initialized")
        
        exit_code = app.exec_()
        
        logger.info(f"MIS Smart Assistant shutting down with exit code {exit_code}")
        
        return exit_code
    except Exception as e:
        logger.critical(f"Fatal error during application initialization: {str(e)}")
        logger.critical(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())