#!/usr/bin/env python3
"""
主窗口模块
负责创建和管理主窗口及标签页架构
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import json
from datetime import datetime

# 添加父目录到路径以便导入core模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.duplicate_finder import DuplicateFinder
from core.visual_similarity import ImageSimilarityFinder


class DuplicateFinderGUI:
    """重复文件检测系统图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("重复文件检测系统 v2.0")
        self.root.geometry("1000x750")

        # 共享变量
        self.directories = []
        self.is_scanning = False
        self.stop_flag = threading.Event()

        # 精确匹配相关
        self.db_path = "file_index.db"
        self.output_path = "duplicates.json"
        self.workers = 8
        self.finder = None

        # 相似度检测相关
        self.similarity_db_path = "image_similarity.db"
        self.similarity_threshold = 12
        self.similarity_mode = "precise"  # "fast" or "precise"
        self.incremental_scan = False
        self.similarity_finder = None

        # 创建界面
        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 标题区域
        self._create_header()

        # 目录选择区域
        self._create_directory_section()

        # 标签页容器（包含设置、按钮、进度、日志）
        self._create_notebook()

    def _create_notebook(self):
        """创建标签页容器"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 标签1：精确匹配
        from gui_modules.exact_match_tab import ExactMatchTab
        self.exact_match_tab = ExactMatchTab(self.notebook, self)
        self.notebook.add(self.exact_match_tab.frame, text="精确匹配")

        # 标签2：相似度检测
        from gui_modules.similarity_tab import SimilarityTab
        self.similarity_tab = SimilarityTab(self.notebook, self)
        self.notebook.add(self.similarity_tab.frame, text="图片相似度检测")

        # 标签3：视频相似度检测
        from gui_modules.video_similarity_tab import VideoSimilarityTab
        self.video_similarity_tab = VideoSimilarityTab(self.notebook, self)
        self.notebook.add(self.video_similarity_tab.frame, text="视频相似度检测")

    def _create_header(self):
        """创建标题区域"""
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            title_frame,
            text="重复文件检测系统",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            title_frame,
            text="高性能 TB级数据优化 | SQLite3存储 | 并行处理 | 图片/视频相似度检测",
            font=("微软雅黑", 9),
            foreground="gray"
        )
        subtitle_label.pack()

    def _create_directory_section(self):
        """创建目录选择区域"""
        dir_frame = ttk.LabelFrame(self.root, text="扫描目录", padding="10")
        dir_frame.pack(fill=tk.X, padx=10, pady=5)

        # 目录列表
        list_frame = ttk.Frame(dir_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.dir_listbox = tk.Listbox(list_frame, height=4, font=("Consolas", 9))
        self.dir_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.dir_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dir_listbox.config(yscrollcommand=scrollbar.set)

        # 目录操作按钮
        btn_frame = ttk.Frame(dir_frame)
        btn_frame.pack(fill=tk.Y, padx=(10, 0))

        ttk.Button(btn_frame, text="添加目录", command=self._add_directory).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="移除选中", command=self._remove_directory).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清空全部", command=self._clear_directories).pack(fill=tk.X, pady=2)

    # ==================== 目录操作方法 ====================

    def _add_directory(self):
        """添加扫描目录"""
        directory = filedialog.askdirectory(title="选择要扫描的目录")
        if directory:
            if directory not in self.directories:
                self.directories.append(directory)
                self.dir_listbox.insert(tk.END, directory)
                self._log(f"已添加目录: {directory}")
            else:
                messagebox.showwarning("警告", "该目录已存在！")

    def _remove_directory(self):
        """移除选中的目录"""
        selection = self.dir_listbox.curselection()
        if selection:
            index = selection[0]
            directory = self.directories.pop(index)
            self.dir_listbox.delete(index)
            self._log(f"已移除目录: {directory}")
        else:
            messagebox.showwarning("警告", "请先选择要移除的目录！")

    def _clear_directories(self):
        """清空所有目录"""
        if self.directories:
            if messagebox.askyesno("确认", "确定要清空所有目录吗？"):
                self.directories.clear()
                self.dir_listbox.delete(0, tk.END)
                self._log("已清空所有目录")

    # ==================== 扫描控制方法 ====================

    def _start_scan(self):
        """启动扫描（根据当前标签页决定扫描类型）"""
        if not self.directories:
            messagebox.showwarning("警告", "请先添加要扫描的目录！")
            return

        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # 精确匹配标签页
            self.exact_match_tab.start_scan()
        elif current_tab == 1:  # 相似度检测标签页
            self.similarity_tab.start_scan()
        else:  # 视频相似度检测标签页
            self.video_similarity_tab.start_scan()

    def _stop_scan(self):
        """停止扫描"""
        self.stop_flag.set()

    def _view_results(self):
        """查看结果"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.exact_match_tab.view_results()
        elif current_tab == 1:
            self.similarity_tab.view_results()
        else:
            self.video_similarity_tab.view_results()

    # ==================== 日志和进度方法 ====================

    def _log(self, message, level="INFO"):
        """添加日志（委托给当前标签页）"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.exact_match_tab._log(message, level)
        elif current_tab == 1:
            self.similarity_tab._log(message, level)
        else:
            self.video_similarity_tab._log(message, level)

    def update_progress(self, progress: float, message: str):
        """更新进度条（委托给当前标签页）"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.exact_match_tab.update_progress(progress, message)
        elif current_tab == 1:
            self.similarity_tab.update_progress(progress, message)
        else:
            self.video_similarity_tab.update_progress(progress, message)

    def update_detail(self, message: str):
        """更新详细信息（委托给当前标签页）"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.exact_match_tab.update_detail(message)
        elif current_tab == 1:
            self.similarity_tab.update_detail(message)
        else:
            self.video_similarity_tab.update_detail(message)


def main():
    """主函数"""
    root = tk.Tk()
    app = DuplicateFinderGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
