@echo off
chcp 65001 > nul
REM HILS Full System Launcher
REM Starts Server, HILS GUI, and Classifier App

echo ========================================
echo HILS Full System Starting...
echo ========================================
echo.

REM Check if required Python packages are installed
echo Checking dependencies...

REM Check customtkinter
python -c "import customtkinter" 2>nul
if errorlevel 1 (
    echo [ERROR] customtkinter is not installed
    echo Installing required packages...
    pip install customtkinter
    if errorlevel 1 (
        echo [ERROR] Failed to install customtkinter
        pause
        exit /b 1
    )
)

REM Check websockets
python -c "import websockets" 2>nul
if errorlevel 1 (
    echo [ERROR] websockets is not installed
    echo Installing required packages...
    pip install websockets
    if errorlevel 1 (
        echo [ERROR] Failed to install websockets
        pause
        exit /b 1
    )
)

REM Check numpy
python -c "import numpy" 2>nul
if errorlevel 1 (
    echo [ERROR] numpy is not installed
    echo Installing required packages...
    pip install numpy
    if errorlevel 1 (
        echo [ERROR] Failed to install numpy
        pause
        exit /b 1
    )
)

REM Check scikit-learn
python -c "import sklearn" 2>nul
if errorlevel 1 (
    echo [ERROR] scikit-learn is not installed
    echo Installing required packages...
    pip install scikit-learn
    if errorlevel 1 (
        echo [ERROR] Failed to install scikit-learn
        pause
        exit /b 1
    )
)

REM Check pyserial
python -c "import serial" 2>nul
if errorlevel 1 (
    echo [ERROR] pyserial is not installed
    echo Installing required packages...
    pip install pyserial
    if errorlevel 1 (
        echo [ERROR] Failed to install pyserial
        pause
        exit /b 1
    )
)

echo All dependencies OK
echo.

REM 1. Start HILS Server (separate window)
echo [1/3] Starting HILS Server...
start "HILS Server" cmd /c "chcp 65001 > nul && python run_hils_server.py || pause" 
timeout /t 2 > nul

REM 2. Start HILS GUI (separate window)
echo [2/3] Starting HILS Controller GUI...
start "HILS Controller" cmd /c "chcp 65001 > nul && python run_hils_gui.py || pause"
timeout /t 2 > nul

REM 3. Start Classifier App (current window or separate)
echo [3/3] Starting Classifier App...
echo.
python run_classifier.py
    echo.
    echo [ERROR] Classifier App terminated with error code: %ERRORLEVEL%
    pause
    if errorlevel 1 (
        echo.
        echo [ERROR] Classifier App terminated with error code: %ERRORLEVEL%
        pause
        exit /b %ERRORLEVEL%
    )
)

echo.
echo All systems terminated.
pause
