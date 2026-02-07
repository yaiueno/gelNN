@echo off
chcp 65001 > nul
echo ========================================
echo HILS Full System Launcher
echo ========================================
echo.
echo This will start:
echo 1. HILS Server (WebSocket backend)
echo 2. HILS Controller (Touch position GUI)
echo 3. Classifier App (Real-time prediction)
echo.
echo Press any key to start...
pause > nul

REM Start HILS Server
echo [1/3] Starting HILS Server...
start "HILS Server" cmd /c "chcp 65001 > nul && python run_hils_server.py || pause"
timeout /t 2 > nul

REM Start HILS GUI
echo [2/3] Starting HILS Controller...
start "HILS Controller" cmd /c "chcp 65001 > nul && python run_hils_gui.py || pause"
timeout /t 2 > nul

REM Start Classifier App
echo [3/3] Starting Classifier App...
python run_classifier.py
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit.
    pause > nul
)
