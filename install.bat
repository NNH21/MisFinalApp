@echo off
echo Installing MIS Smart Assistant...
echo.

REM Create application directory
if not exist "%PROGRAMFILES%\MIS Assistant" mkdir "%PROGRAMFILES%\MIS Assistant"

REM Copy files
echo Copying application files...
xcopy /E /I /Y "dist\MIS_Assistant\*" "%PROGRAMFILES%\MIS Assistant\"

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\MIS Assistant.lnk');$s.TargetPath='%PROGRAMFILES%\MIS Assistant\MIS_Assistant.exe';$s.Save()"

REM Create start menu shortcut
echo Creating start menu shortcut...
if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\MIS Assistant" mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\MIS Assistant"
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\MIS Assistant\MIS Assistant.lnk');$s.TargetPath='%PROGRAMFILES%\MIS Assistant\MIS_Assistant.exe';$s.Save()"

echo.
echo Installation completed!
echo You can now run MIS Assistant from your desktop or start menu.
pause
