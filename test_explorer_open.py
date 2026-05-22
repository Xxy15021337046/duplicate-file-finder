#!/usr/bin/env python3
"""
测试Windows资源管理器打开文件功能
"""

import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox


def test_explorer_select():
    """测试explorer /select命令"""
    # 使用一个实际存在的测试文件路径
    test_files = [
        r"D:\文档\2025D132 智能老人陪伴系统\老人\home\src\assets\images\slider\4.png",
        r"D:\文档\2025D132 智能老人陪伴系统\老人\admin\src\assets\images\slider\4.png"
    ]

    print("测试Windows资源管理器打开功能...")
    for file_path in test_files:
        print(f"\n测试文件: {file_path}")
        print(f"文件是否存在: {os.path.exists(file_path)}")

        if os.path.exists(file_path):
            # 模拟Tkinter中的打开操作
            try:
                cmd = f'explorer /select,"{file_path}"'
                print(f"执行命令: {cmd}")
                result = subprocess.run(cmd, shell=True)
                print(f"返回码: {result.returncode}")
            except Exception as e:
                print(f"错误: {e}")


if __name__ == "__main__":
    test_explorer_select()
