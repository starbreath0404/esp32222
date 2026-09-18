@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call "01_安裝環境.cmd"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" "micropython\tools\build_deploy.py"
if errorlevel 1 goto failed
set /p PORT=請輸入「右手」板子的 COM 編號（例如 COM6）: 
if "%PORT%"=="" goto failed
".venv\Scripts\python.exe" -m mpremote connect "%PORT%" fs cp -r "micropython\dist\right\." :
if errorlevel 1 goto failed
echo 右手程式上傳完成。按一下板子的 RESET 或 EN。
pause
exit /b 0
:failed
echo 上傳失敗。確認 COM 編號正確，而且沒有其他程式占用它。
pause
exit /b 1
