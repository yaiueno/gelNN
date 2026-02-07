@echo off
chcp 65001 > nul
echo ========================================
echo Frequency Analysis Tool (Real Hardware)
echo ========================================
echo.
echo This tool analyzes impedance characteristics
echo across different frequencies to find optimal
echo measurement frequency.
echo.
echo Mode: Real Hardware (AD3 + Arduino)
echo.
echo WARNING: Make sure AD3 and Arduino are connected!
echo.
echo Press any key to start...
pause > nul

python -m src.utils.frequency_analyzer --mode real
if %ERRORLEVEL% NEQ 0 (
    echo Error occurred. Press any key to exit.
    pause > nul
)
