@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo 文件重复校验工具 - 发布版打包脚本
echo ========================================
echo.
echo 此脚本用于创建最终发布版本（用户无需Python环境）
echo.
pause

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python 环境！
    echo.
    echo 此脚本需要在有Python环境的电脑上运行
    echo 运行后会生成独立的exe文件，用户无需安装Python
    echo.
    pause
    exit /b 1
)

echo [√] Python 环境检测通过
python --version
echo.

:: 升级pip
echo [提示] 正在升级 pip...
python -m pip install --upgrade pip -q

:: 安装依赖
echo [1/4] 正在安装项目依赖...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败！
    pause
    exit /b 1
)
echo [√] 依赖安装完成
echo.

:: 安装PyInstaller
echo [2/4] 正在安装 PyInstaller...
python -m pip install pyinstaller -q
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败！
    pause
    exit /b 1
)
echo [√] PyInstaller 安装完成
echo.

:: 清理旧的构建文件
echo [3/4] 正在清理旧的构建文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /f /q *.spec
if exist "release" rmdir /s /q release
echo [√] 清理完成
echo.

:: 开始打包
echo [4/4] 正在打包可执行文件（这可能需要几分钟）...
echo ========================================
echo.

python -m PyInstaller ^
    --name="文件重复校验工具-v4.0.0" ^
    --windowed ^
    --onefile ^
    --icon=NONE ^
    --add-data "core;core" ^
    --add-data "gui_modules;gui_modules" ^
    --hidden-import=PIL ^
    --hidden-import=imagehash ^
    --hidden-import=cv2 ^
    --hidden-import=numpy ^
    --hidden-import=pefile ^
    --hidden-import=packaging ^
    --noupx ^
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

:: 创建发布文件夹
mkdir release
copy "dist\文件重复校验工具-v4.0.0.exe" "release\"
copy "README.md" "release\"
if exist "QUICK_START.md" copy "QUICK_START.md" "release\"
mkdir "release\docs"
if exist "docs\*.md" copy "docs\*.md" "release\docs\"

echo 发布文件已准备就绪！
echo.
echo 发布位置: release\
echo.
dir release
echo.
echo ========================================
echo 发布包包含:
echo   - 文件重复校验工具-v4.0.0.exe (主程序)
echo   - README.md (使用说明)
echo   - QUICK_START.md (快速开始指南，如有)
echo   - docs\ (详细文档)
echo ========================================
echo.
echo 您可以将 release 文件夹压缩后分发给用户
echo 用户无需安装Python，双击exe即可使用！
echo.

:: 询问是否打开release目录
set /p open_release="是否打开 release 目录？(Y/N): "
if /i "%open_release%"=="Y" (
    explorer release
)

pause
