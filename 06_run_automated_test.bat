@echo off
chcp 65001 > nul
echo ========================================
echo Automated Test Script (HILS Mode)
echo ========================================
echo.
echo This script performs:
echo 1. Random position data collection
echo 2. Model training
echo 3. Inference test with error metrics
echo.
echo Mode: HILS Simulator
echo.
echo Press any key to start...
pause > nul

python scripts\test_auto.py
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit.
    pause > nul
)
