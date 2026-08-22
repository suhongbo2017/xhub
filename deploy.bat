@echo off
chcp 65001 >nul 2>&1
REM ===================================================================
REM X HUB - Windows 一键部署脚本
REM ===================================================================

set APP_NAME=xhub
set PORT=8866
set VENV_NAME=venv

echo.
echo ╔══════════════════════════════════════════╗
echo ║      X HUB Deploy Tool for Windows       ║
echo ╚══════════════════════════════════════════╝
echo.

REM --- 检查 Python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo [OK] Python: %PYVER%

REM --- Cookie 检查 ---
if not exist "xcookies.txt" (
    echo [WARN] xcookies.txt not found!
    echo Please add your Twitter cookie to xcookies.txt
    choice /C YN /M "Continue anyway?"
    if errorlevel 2 exit /b 1
) else (
    echo [OK] Cookie file exists
)

REM --- 虚拟环境 ---
if not exist "%VENV_NAME%" (
    echo [INFO] Creating virtual environment...
    python -m venv %VENV_NAME%
)

REM --- 激活并安装依赖 ---
call %VENV_NAME%\Scripts\activate.bat

echo [INFO] Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt --quiet

echo.
echo ╔══════════════════════════════════════════╗
echo ║  ✅ Ready! Start with command below       ║
echo ╚══════════════════════════════════════════╝
echo.
echo   uvicorn server:app --host 0.0.0.0 --port %PORT%
echo.
echo   Or run:     start.cmd
echo   Visit:      http://localhost:%PORT%
echo.
pause
