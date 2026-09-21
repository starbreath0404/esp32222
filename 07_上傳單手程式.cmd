@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call "01_安裝環境.cmd"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" "micropython\tools\build_deploy.py"
if errorlevel 1 goto failed
set /p PORT=Enter the single glove COM port (example COM5): 
if "%PORT%"=="" goto failed
".venv\Scripts\python.exe" -m mpremote connect "%PORT%" fs cp -r "micropython\dist\single\." :
if errorlevel 1 goto failed
echo Single-glove program uploaded. Press RESET or EN on the board.
pause
exit /b 0
:failed
echo Upload failed. Check the COM port and close other serial programs.
pause
exit /b 1
