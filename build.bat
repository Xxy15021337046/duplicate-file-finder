@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo 文件重复校验工具 - 自动打包脚本 (Windows)
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python 环境！
    echo.
    echo 请先安装 Python 3.6+：
    echo 1. 访问 https://www.python.org/downloads/
    echo 2. 下载并安装 Python 3.6 或更高版本
    echo 3. 安装时勾选 "Add Python to PATH"
    echo 4. 重新运行此脚本
    echo.
    pause
    exit /b 1
)

echo [√] Python 环境检测通过
python --version
echo.

:: 检查pip是否可用
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [错误] pip 不可用，请重新安装 Python
    pause
    exit /b 1
)

echo [√] pip 检测通过
echo.

:: 升级pip（可选）
echo [提示] 正在升级 pip...
python -m pip install --upgrade pip -q
echo.

:: 安装依赖
echo [1/3] 正在安装项目依赖...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败！
    pause
    exit /b 1
)
echo [√] 依赖安装完成
echo.

:: 安装PyInstaller
echo [2/3] 正在安装 PyInstaller...
python -m pip install pyinstaller -q
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败！
    pause
    exit /b 1
)
echo [√] PyInstaller 安装完成
echo.

:: 清理旧的构建文件
echo [3/3] 正在清理旧的构建文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /f /q *.spec
echo [√] 清理完成
echo.

:: 开始打包
echo ========================================
echo 开始打包可执行文件...
echo ========================================
echo.

python -m PyInstaller ^
    --name="文件重复校验工具" ^
    --windowed ^
    --onefile ^
    --icon=NONE ^
    --add-data "core;core" ^
    --add-data "gui_modules;gui_modules" ^
    --hidden-import=PIL ^
    --hidden-import=imagehash ^
    --hidden-import=cv2 ^
    --hidden-import=numpy ^
    run_gui.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请查看上方错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo [√] 打包成功！
echo ========================================
echo.
echo 可执行文件位置: dist\文件重复校验工具.exe
echo.
echo 您可以将 dist 文件夹中的 exe 文件复制到任意位置使用
echo 注意: 首次运行可能需要几秒钟启动时间
echo.

:: 询问是否打开dist目录
set /p open_dist="是否打开 dist 目录？(Y/N): "
if /i "%open_dist%"=="Y" (
    explorer dist
)

pause
