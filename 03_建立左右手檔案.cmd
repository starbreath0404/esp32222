@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call "01_安裝環境.cmd"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" "micropython\tools\build_deploy.py"
if errorlevel 1 (
    echo 建立失敗。
) else (
    echo 已建立 micropython\dist\left 和 micropython\dist\right。
)
pause
