@echo off
echo ======================================
echo  Single Terminal Press Detection
echo  (Training + Detection with NN)
echo  AD3 Only - No Arduino Required
echo ======================================
echo.

REM このフォルダをカレントディレクトリにして実行
cd /d "%~dp0"
python run.py
pause
