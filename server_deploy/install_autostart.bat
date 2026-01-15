@echo off
set "SCRIPT_DIR=%~dp0"
set "TARGET_BATCH=%SCRIPT_DIR%run_server.bat"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\FluxServer.lnk"

echo ========================================================
echo   SETTING UP AUTOSTART FOR FLUX SERVER
echo ========================================================
echo.
echo Target Batch File: %TARGET_BATCH%
echo Startup Folder: %SHORTCUT_PATH%
echo.

powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='%TARGET_BATCH%';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] Shortcut created successfully.
    echo The Flux Server will now start automatically when this user logs in.
) else (
    echo [ERROR] Failed to create shortcut.
)

echo.
pause
