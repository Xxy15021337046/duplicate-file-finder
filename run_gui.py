#!/usr/bin/env python3
"""
重复文件检测系统 - GUI启动入口
模块化架构 v2.0
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    try:
        # 导入GUI模块
        from gui_modules.main_window import DuplicateFinderGUI
        import tkinter as tk

        # 创建主窗口
        root = tk.Tk()
        app = DuplicateFinderGUI(root)

        # 运行主循环
        root.mainloop()

    except ImportError as e:
        print(f"错误: 无法导入必要的模块 - {e}")
        print("\n请确保已安装所有依赖:")
        print("  pip install Pillow imagehash")
        sys.exit(1)

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
