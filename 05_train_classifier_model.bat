@echo off
chcp 65001 > nul
echo ========================================
echo Train Classifier Model (Batch Mode)
echo ========================================
echo.
echo This script collects training data and
echo trains a 9-point grid classifier.
echo.
echo Default: 3x3 grid, 30 samples per point
echo.
echo Press any key to start...
pause > nul

python scripts\train.py
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit.
    pause > nul
)
