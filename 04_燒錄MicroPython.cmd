@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call "01_安裝環境.cmd"
if not exist ".venv\Scripts\python.exe" exit /b 1
if not exist "firmware\ESP32S3_MICROPYTHON.bin" goto no_firmware

set /p PORT=請輸入板子的 COM 編號（例如 COM5）: 
if "%PORT%"=="" goto bad_port
echo 即將清除 %PORT% 並燒錄 MicroPython。
pause
".venv\Scripts\python.exe" -m esptool --chip esp32s3 --port "%PORT%" erase-flash
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m esptool --chip esp32s3 --port "%PORT%" --baud 460800 write-flash 0 "firmware\ESP32S3_MICROPYTHON.bin"
if errorlevel 1 goto failed
echo 燒錄完成。按一下板子的 RESET 或 EN。
pause
exit /b 0

:no_firmware
echo 找不到 firmware\ESP32S3_MICROPYTHON.bin。
echo 請依照 MicroPython_燒入教學_零基礎版.md 第 2 步下載韌體。
pause
exit /b 1
:bad_port
echo 沒有輸入 COM 編號。
pause
exit /b 1
:failed
echo 燒錄失敗。若畫面一直顯示 Connecting，請照教學操作 BOOT 和 RESET。
pause
exit /b 1
