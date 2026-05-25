#!/bin/bash

# 文件重复校验工具 - 自动打包脚本 (Linux/macOS)

echo "========================================"
echo "文件重复校验工具 - 自动打包脚本"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 错误处理函数
error_exit() {
    echo -e "${RED}[错误] $1${NC}"
    exit 1
}

success_msg() {
    echo -e "${GREEN}[√] $1${NC}"
}

info_msg() {
    echo -e "${YELLOW}[提示] $1${NC}"
}

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    error_exit "未检测到 Python3 环境！\n\n请先安装 Python 3.6+：\n- Ubuntu/Debian: sudo apt install python3 python3-pip\n- CentOS/RHEL: sudo yum install python3 python3-pip\n- macOS: brew install python3"
fi

success_msg "Python 环境检测通过"
python3 --version
echo ""

# 检查pip是否可用
if ! python3 -m pip --version &> /dev/null; then
    error_exit "pip 不可用，请重新安装 Python"
fi

success_msg "pip 检测通过"
echo ""

# 升级pip（可选）
info_msg "正在升级 pip..."
python3 -m pip install --upgrade pip -q || true
echo ""

# 安装依赖
echo "[1/3] 正在安装项目依赖..."
python3 -m pip install -r requirements.txt -q || error_exit "依赖安装失败！"
success_msg "依赖安装完成"
echo ""

# 安装PyInstaller
echo "[2/3] 正在安装 PyInstaller..."
python3 -m pip install pyinstaller -q || error_exit "PyInstaller 安装失败！"
success_msg "PyInstaller 安装完成"
echo ""

# 清理旧的构建文件
echo "[3/3] 正在清理旧的构建文件..."
rm -rf dist build *.spec
success_msg "清理完成"
echo ""

# 开始打包
echo "========================================"
echo "开始打包可执行文件..."
echo "========================================"
echo ""

python3 -m PyInstaller \
    --name="文件重复校验工具" \
    --windowed \
    --onefile \
    --add-data "core:core" \
    --add-data "gui_modules:gui_modules" \
    --hidden-import=PIL \
    --hidden-import=imagehash \
    --hidden-import=cv2 \
    --hidden-import=numpy \
    run_gui.py

if [ $? -ne 0 ]; then
    echo ""
    error_exit "打包失败！请查看上方错误信息"
fi

echo ""
echo "========================================"
success_msg "打包成功！"
echo "========================================"
echo ""
echo "可执行文件位置: dist/文件重复校验工具"
echo ""
echo "您可以将 dist 文件夹中的可执行文件复制到任意位置使用"
echo "注意: 首次运行可能需要几秒钟启动时间"
echo ""

# 询问是否打开dist目录
read -p "是否打开 dist 目录？(y/n): " open_dist
if [[ "$open_dist" =~ ^[Yy]$ ]]; then
    if [[ "$(uname)" == "Darwin" ]]; then
        open dist
    elif [[ "$(uname)" == "Linux" ]]; then
        xdg-open dist 2>/dev/null || nautilus dist 2>/dev/null || dolphin dist 2>/dev/null || true
    fi
fi
