#!/usr/bin/env python3
"""
Pre-build setup script for MIS Smart Assistant
Checks and installs required dependencies before building executable
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"Error: Python 3.7+ required, got {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_requirements():
    """Install requirements from requirements.txt"""
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("Error: requirements.txt not found")
        return False
    
    print("Installing requirements...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(req_file)
        ])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False

def check_icon_file():
    """Check if icon file exists"""
    icon_paths = [
        Path("software/resources/icons/assistant.png"),
        Path("resources/icons/assistant.png")
    ]
    
    for icon_path in icon_paths:
        if icon_path.exists():
            print(f"✓ Icon found at: {icon_path}")
            return True
    
    print("Warning: assistant.png icon not found in expected locations")
    print("Expected locations:")
    for path in icon_paths:
        print(f"  - {path}")
    return False

def check_main_script():
    """Check if main script exists"""
    main_script = Path("software/app/main.py")
    if main_script.exists():
        print(f"✓ Main script found: {main_script}")
        return True
    else:
        print(f"Error: Main script not found: {main_script}")
        return False

def create_missing_directories():
    """Create missing resource directories"""
    directories = [
        "resources/icons",
        "resources/sounds", 
        "resources/weather_icons",
        "software/resources/icons",
        "software/resources/sounds",
        "software/resources/weather_icons",
        "software/resources/bin"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✓ Resource directories created/verified")

def main():
    """Main setup function"""
    print("=" * 60)
    print("MIS Smart Assistant - Pre-build Setup")
    print("=" * 60)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
    
    # Check main script
    if not check_main_script():
        success = False
    
    # Create missing directories
    create_missing_directories()
    
    # Check icon file
    check_icon_file()  # Warning only, not fatal
    
    # Install requirements
    if not install_requirements():
        success = False
    
    if success:
        print("\n" + "=" * 60)
        print("SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("You can now run the build script:")
        print("  python build_exe.py")
        print("Or use the batch file:")
        print("  build.bat")
    else:
        print("\n" + "=" * 60)
        print("SETUP FAILED!")
        print("=" * 60)
        print("Please fix the errors above before building.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
