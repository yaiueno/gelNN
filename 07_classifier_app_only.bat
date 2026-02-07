@echo off
chcp 65001 > nul
echo ========================================
echo Classifier App (Standalone)
echo ========================================
echo.
echo This app shows real-time classification
echo with probability heatmap and metrics.
echo.
echo Mode: Connect to running HILS Server
echo.
echo NOTE: Make sure HILS Server is already running!
echo       (Run python run_hils_server.py first)
echo.
echo Press any key to start...
pause > nul

python run_classifier.py
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit.
    pause > nul
)
