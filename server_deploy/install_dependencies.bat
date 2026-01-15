@echo off
title Install Requirements
echo Installing necessary libraries...
pip install opencv-python numpy mysql-connector-python pyyaml onnxruntime
echo.
echo Installation complete! You can now run run_server.bat
pause
