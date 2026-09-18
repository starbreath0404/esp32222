@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call "01_安裝環境.cmd"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" "micropython\desktop\app.py"
if errorlevel 1 (
    echo.
    echo 程式異常結束，請拍下上方錯誤文字。
    pause
)
