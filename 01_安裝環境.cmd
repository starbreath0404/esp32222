@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo 手語翻譯手套 - Windows 環境安裝
echo ========================================

where py >nul 2>nul && goto use_py
where python >nul 2>nul && goto use_python
goto no_python

:use_py
set "PYTHON=py -3"
goto python_ready

:use_python
set "PYTHON=python"

:python_ready

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 建立專案自己的 Python 環境...
    %PYTHON% -m venv ".venv"
    if errorlevel 1 goto failed
) else (
    echo [1/3] 已找到 .venv，保留現有環境。
)

echo [2/3] 更新 pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed

echo [3/3] 安裝錄製、燒錄及上傳工具...
".venv\Scripts\python.exe" -m pip install -r "micropython\desktop\requirements.txt"
if errorlevel 1 goto failed

echo.
echo 安裝完成。現在可以雙擊 02_啟動錄製工具.cmd。
pause
exit /b 0

:no_python
echo.
echo 找不到 Python。
echo 請到 https://www.python.org/downloads/windows/ 安裝 Python 3.11 或 3.12。
echo 安裝畫面務必勾選 Add python.exe to PATH，之後重新執行本檔。
pause
exit /b 1

:failed
echo.
echo 安裝失敗。請保留這個視窗並拍下最後面的錯誤文字。
pause
exit /b 1
