@echo off
REM HILS分類器GUI起動バッチファイル
REM このバッチファイルはHILSモードで分類器GUIを起動します

echo ========================================
echo HILS分類器GUI起動中...
echo ========================================
echo.

REM Pythonで分類器GUIを起動
python app_classifier.py

REM エラーが発生した場合は一時停止
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo エラーが発生しました。エラーコード: %ERRORLEVEL%
    pause
)
