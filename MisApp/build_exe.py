
"""
Build script for MIS Smart Assistant
Creates standalone executable using PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def setup_build_environment():
    """Setup the build environment and paths"""
    # Get current directory and project paths
    current_dir = Path(__file__).parent.absolute()
    software_dir = current_dir / "software"
    app_dir = software_dir / "app"
    resources_dir = current_dir / "resources"
    software_resources_dir = software_dir / "resources"
    
    # Ensure all required directories exist
    build_dir = current_dir / "build"
    dist_dir = current_dir / "dist"
      # Clean previous builds
    try:
        if build_dir.exists():
            shutil.rmtree(build_dir)
    except PermissionError:
        print(f"Warning: Could not remove {build_dir}. Some files may be in use.")
        
    try:
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
    except PermissionError:
        print(f"Warning: Could not remove {dist_dir}. Some files may be in use.")
        print("Continuing with build...")
        
    return current_dir, software_dir, app_dir, resources_dir, software_resources_dir

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("PyInstaller is already installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install PyInstaller: {e}")
            return False

def create_spec_file(current_dir, app_dir, resources_dir, software_resources_dir):
    """Create PyInstaller spec file for MIS Assistant"""
    
    # Path to main script
    main_script = app_dir / "main.py"
    
    # Path to icon
    icon_path = software_resources_dir / "icons" / "assistant.png"
    if not icon_path.exists():
        # Fallback to project resources
        icon_path = resources_dir / "icons" / "assistant.png"
    
    # Convert PNG to ICO if needed (PyInstaller prefers ICO on Windows)
    ico_path = current_dir / "assistant.ico"
    
    # Try to convert PNG to ICO
    try:
        from PIL import Image
        img = Image.open(str(icon_path))
        img.save(str(ico_path), format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
        print(f"Converted icon to ICO format: {ico_path}")
        icon_file = str(ico_path)
    except ImportError:
        print("PIL not available, using PNG icon (may not work on all systems)")
        icon_file = str(icon_path)
    except Exception as e:
        print(f"Failed to convert icon: {e}")
        icon_file = str(icon_path) if icon_path.exists() else None
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get paths
current_dir = Path(r"{current_dir}")
app_dir = Path(r"{app_dir}")
resources_dir = Path(r"{resources_dir}")
software_resources_dir = Path(r"{software_resources_dir}")

block_cipher = None

# Define data files to include
datas = [
    # Include all resource directories
    (str(resources_dir / "icons"), "resources/icons"),
    (str(resources_dir / "sounds"), "resources/sounds"),
    (str(resources_dir / "weather_icons"), "resources/weather_icons"),
    (str(software_resources_dir / "icons"), "software/resources/icons"),
    (str(software_resources_dir / "sounds"), "software/resources/sounds"),
    (str(software_resources_dir / "weather_icons"), "software/resources/weather_icons"),
]

# Include bin directory if it exists (for FFmpeg)
bin_dirs = [
    software_resources_dir / "bin",
    resources_dir / "bin"
]

for bin_dir in bin_dirs:
    if bin_dir.exists():
        datas.append((str(bin_dir), str(bin_dir.relative_to(current_dir))))

# Hidden imports for modules that PyInstaller might miss
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtGui', 
    'PyQt5.QtWidgets',
    'PyQt5.QtWebEngineWidgets',
    'pygame',
    'pygame.mixer',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'bleak',
    'bleak.backends',
    'bleak.backends.characteristic',
    'google.generativeai',
    'googleapiclient',
    'googleapiclient.discovery',
    'googleapiclient.errors',
    'pytube',
    'yt_dlp',
    'mutagen',
    'mutagen.id3',
    'gTTS',
    'speech_recognition',
    'pyaudio',
    'pyttsx3',
    'requests',
    'numpy',
    'psutil',
    'pytz',
    'PIL',
    'qrcode',
    'httpx',
    'pydub',
    'pyowm',
    'pathlib',
    'datetime',
    'json',
    'threading',
    'queue',
    'time',
    'os',
    'sys',
    'traceback',
    'subprocess',
    'zipfile',
    'shutil',
    'platform',
    'socket',
    'urllib',
    'html',
    're',
    'math',
    'random',
    'io',
    'base64',
    'hashlib',
    'tempfile',
]

a = Analysis(
    [r"{main_script}"],
    pathex=[
        str(current_dir),
        str(app_dir),
        str(app_dir.parent),
        str(current_dir / "software"),
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MIS_Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r"{icon_file}" if "{icon_file}" != "None" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MIS_Assistant',
)
'''
    
    spec_file = current_dir / "MIS_Assistant.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"Created spec file: {spec_file}")
    return spec_file

def build_executable(spec_file):
    """Build the executable using PyInstaller"""
    try:
        print("Building executable...")
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]
        subprocess.check_call(cmd)
        print("Build completed successfully!")
        
        # Run the libzbar fixer script to ensure QR code scanning works
        try:
            print("\nFixing libzbar.dll issue...")
            fix_script = Path(__file__).parent / "fix_libzbar.py"
            if fix_script.exists():
                subprocess.check_call([sys.executable, str(fix_script)])
                print("libzbar.dll fix applied successfully!")
            else:
                print("Warning: fix_libzbar.py not found, QR code scanning may not work")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to apply libzbar.dll fix: {e}")
            print("QR code scanning may not work properly")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False

def create_installer_script():
    """Create a simple installer script"""
    installer_content = '''@echo off
echo Installing MIS Smart Assistant...
echo.

REM Create application directory
if not exist "%PROGRAMFILES%\\MIS Assistant" mkdir "%PROGRAMFILES%\\MIS Assistant"

REM Copy files
echo Copying application files...
xcopy /E /I /Y "dist\\MIS_Assistant\\*" "%PROGRAMFILES%\\MIS Assistant\\"

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\\Desktop\\MIS Assistant.lnk');$s.TargetPath='%PROGRAMFILES%\\MIS Assistant\\MIS_Assistant.exe';$s.Save()"

REM Create start menu shortcut
echo Creating start menu shortcut...
if not exist "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\MIS Assistant" mkdir "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\MIS Assistant"
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\MIS Assistant\\MIS Assistant.lnk');$s.TargetPath='%PROGRAMFILES%\\MIS Assistant\\MIS_Assistant.exe';$s.Save()"

echo.
echo Installation completed!
echo You can now run MIS Assistant from your desktop or start menu.
pause
'''
    
    installer_file = Path("install.bat")
    with open(installer_file, 'w', encoding='utf-8') as f:
        f.write(installer_content)
    
    print(f"Created installer script: {installer_file}")

def main():
    """Main build function"""
    print("=" * 60)
    print("MIS Smart Assistant - Build Script")
    print("=" * 60)
    
    # Setup build environment
    current_dir, software_dir, app_dir, resources_dir, software_resources_dir = setup_build_environment()
    
    # Check if main script exists
    main_script = app_dir / "main.py"
    if not main_script.exists():
        print(f"Error: Main script not found at {main_script}")
        return False
    
    # Install PyInstaller if needed
    if not install_pyinstaller():
        return False
    
    # Create spec file
    spec_file = create_spec_file(current_dir, app_dir, resources_dir, software_resources_dir)
    
    # Build executable
    if build_executable(spec_file):
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"Executable created in: {current_dir / 'dist' / 'MIS_Assistant'}")
        print(f"Main executable: {current_dir / 'dist' / 'MIS_Assistant' / 'MIS_Assistant.exe'}")
        
        # Create installer script
        create_installer_script()
        
        print("\nTo distribute the application:")
        print("1. Copy the entire 'dist/MIS_Assistant' folder")
        print("2. Run 'install.bat' as administrator on target machine")
        print("3. Or simply run 'MIS_Assistant.exe' directly")
        
        return True
    else:
        print("\n" + "=" * 60)
        print("BUILD FAILED!")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
