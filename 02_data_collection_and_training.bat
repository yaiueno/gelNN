@echo off
chcp 65001 > nul
echo ========================================
echo Data Collection and Training App
echo ========================================
echo.
echo This app allows you to:
echo - Collect impedance data at grid positions
echo - Train ML model
echo - Test real-time inference
echo.
echo Mode: Check src\utils\config.py for HILS/Real hardware mode
echo.
echo Press any key to start...
pause > nul

python run_app.py
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit.
    pause > nul
)
