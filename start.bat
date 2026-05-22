@echo off
echo ========================================
echo 重复文件检测系统 - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 激活虚拟环境...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 无法激活虚拟环境！
    pause
    exit /b 1
)
echo [成功] 虚拟环境已激活

echo.
echo [2/3] 检查Python版本...
python --version
if errorlevel 1 (
    echo [错误] Python未找到！
    pause
    exit /b 1
)

echo.
echo [3/3] 启动程序...
echo ========================================
echo.

python gui_modules/main_window.py

echo.
echo ========================================
echo 程序已退出
pause
