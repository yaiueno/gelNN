@echo off
chcp 65001 > nul
echo ========================================
echo Frequency Analysis Tool (HILS Mode)
echo ========================================
echo.
echo This tool analyzes impedance characteristics
echo across different frequencies to find optimal
echo measurement frequency.
echo.
echo Mode: HILS Simulator
echo.
echo Press any key to start...
pause > nul

python -m src.utils.frequency_analyzer --mode hils
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit.
    pause > nul
)
