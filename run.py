#!/usr/bin/env python3
"""
重复文件检测系统 - GUI图形界面启动脚本
双击运行或命令行执行: python run.py
"""

import sys
import os

if __name__ == '__main__':
    # 确保可以导入模块
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from gui import main
    main()
