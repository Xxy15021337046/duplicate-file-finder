#!/usr/bin/env python3
"""
重复文件检测系统 - GUI图形界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import json
from datetime import datetime
from duplicate_finder import DuplicateFinder


class DuplicateFinderGUI:
    """重复文件检测系统图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("重复文件检测系统")
        self.root.geometry("900x700")

        # 变量
        self.directories = []
        self.db_path = "file_index.db"
        self.output_path = "duplicates.json"
        self.workers = 8
        self.is_scanning = False
        self.finder = None
        self.stop_flag = threading.Event()  # 停止标志
        self.current_progress = 0

        # 创建界面
        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 标题
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
            text="高性能 TB级数据优化 | SQLite3存储 | 并行处理",
            font=("微软雅黑", 9),
            foreground="gray"
        )
        subtitle_label.pack()

        # 目录选择区域
        dir_frame = ttk.LabelFrame(self.root, text="扫描目录", padding="10")
        dir_frame.pack(fill=tk.X, padx=10, pady=5)

        # 目录列表
        self.dir_listbox = tk.Listbox(dir_frame, height=4, font=("Consolas", 9))
        self.dir_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        scrollbar = ttk.Scrollbar(dir_frame, orient=tk.VERTICAL, command=self.dir_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dir_listbox.config(yscrollcommand=scrollbar.set)

        # 目录操作按钮
        dir_btn_frame = ttk.Frame(dir_frame)
        dir_btn_frame.pack(fill=tk.Y, padx=(10, 0))

        ttk.Button(dir_btn_frame, text="添加目录", command=self._add_directory).pack(fill=tk.X, pady=2)
        ttk.Button(dir_btn_frame, text="移除选中", command=self._remove_directory).pack(fill=tk.X, pady=2)
        ttk.Button(dir_btn_frame, text="清空全部", command=self._clear_directories).pack(fill=tk.X, pady=2)

        # 设置区域
        settings_frame = ttk.LabelFrame(self.root, text="扫描设置", padding="10")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)

        # 数据库路径
        db_row = ttk.Frame(settings_frame)
        db_row.pack(fill=tk.X, pady=2)
        ttk.Label(db_row, text="数据库:", width=10).pack(side=tk.LEFT)
        self.db_var = tk.StringVar(value="file_index.db")
        ttk.Entry(db_row, textvariable=self.db_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(db_row, text="浏览...", command=self._browse_db).pack(side=tk.LEFT)

        # 输出路径
        output_row = ttk.Frame(settings_frame)
        output_row.pack(fill=tk.X, pady=2)
        ttk.Label(output_row, text="输出文件:", width=10).pack(side=tk.LEFT)
        self.output_var = tk.StringVar(value="duplicates.json")
        ttk.Entry(output_row, textvariable=self.output_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_row, text="浏览...", command=self._browse_output).pack(side=tk.LEFT)

        # 线程数
        workers_row = ttk.Frame(settings_frame)
        workers_row.pack(fill=tk.X, pady=2)
        ttk.Label(workers_row, text="并行线程:", width=10).pack(side=tk.LEFT)
        self.workers_var = tk.StringVar(value="8")
        ttk.Spinbox(workers_row, from_=1, to=32, textvariable=self.workers_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(workers_row, text="(建议: HDD用4-8, SSD用8-16, NVMe用16-32)", foreground="gray").pack(side=tk.LEFT)

        # 文件类型过滤
        filter_frame = ttk.Frame(settings_frame)
        filter_frame.pack(fill=tk.X, pady=(5, 2))
        
        ttk.Label(filter_frame, text="文件类型:", width=10).pack(side=tk.LEFT)
        
        # 全部选项（默认选中）
        self.filter_all = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="全部", variable=self.filter_all, 
                       command=self._on_filter_all_changed).pack(side=tk.LEFT, padx=2)
        
        # 预设类型复选框
        self.filter_image = tk.BooleanVar(value=False)
        self.filter_video = tk.BooleanVar(value=False)
        self.filter_audio = tk.BooleanVar(value=False)
        self.filter_text = tk.BooleanVar(value=False)
        self.filter_app = tk.BooleanVar(value=False)
        self.filter_archive = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(filter_frame, text="图片", variable=self.filter_image,
                       command=self._on_filter_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame, text="视频", variable=self.filter_video,
                       command=self._on_filter_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame, text="音频", variable=self.filter_audio,
                       command=self._on_filter_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame, text="文本", variable=self.filter_text,
                       command=self._on_filter_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame, text="应用", variable=self.filter_app,
                       command=self._on_filter_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame, text="压缩", variable=self.filter_archive,
                       command=self._on_filter_item_changed).pack(side=tk.LEFT, padx=2)
        
        # 自定义后缀输入框
        custom_ext_frame = ttk.Frame(settings_frame)
        custom_ext_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(custom_ext_frame, text="自定义后缀:", width=10).pack(side=tk.LEFT)
        self.custom_extensions_var = tk.StringVar()
        ttk.Entry(custom_ext_frame, textvariable=self.custom_extensions_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Label(custom_ext_frame, text="(用逗号分隔，如: .jpg,.png,.txt)", foreground="gray", font=("微软雅黑", 8)).pack(side=tk.LEFT)

        # 控制按钮区域
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(
            control_frame,
            text="开始扫描",
            command=self._start_scan,
            style="Accent.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(
            control_frame,
            text="停止",
            command=self._stop_scan,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="查看结果",
            command=self._view_results
        ).pack(side=tk.LEFT, padx=5)

        # 进度区域
        progress_frame = ttk.LabelFrame(self.root, text="扫描进度", padding="10")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'  # 改为确定性模式（百分比）
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var, font=("微软雅黑", 9))
        status_label.pack()

        self.progress_detail_var = tk.StringVar(value="")
        detail_label = ttk.Label(progress_frame, textvariable=self.progress_detail_var, font=("微软雅黑", 8), foreground="gray")
        detail_label.pack()

        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置样式
        style = ttk.Style()
        style.configure("Accent.TButton", font=("微软雅黑", 10, "bold"))

    def _log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

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

    def _browse_db(self):
        """浏览数据库文件"""
        filename = filedialog.asksaveasfilename(
            title="选择数据库文件",
            defaultextension=".db",
            filetypes=[("数据库文件", "*.db"), ("所有文件", "*.*")]
        )
        if filename:
            self.db_var.set(filename)

    def _browse_output(self):
        """浏览输出文件"""
        filename = filedialog.asksaveasfilename(
            title="选择输出文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_var.set(filename)

    def _on_filter_all_changed(self):
        """当"全部"选项改变时"""
        if self.filter_all.get():
            # 选中全部时，勾选所有子项
            self.filter_image.set(True)
            self.filter_video.set(True)
            self.filter_audio.set(True)
            self.filter_text.set(True)
            self.filter_app.set(True)
            self.filter_archive.set(True)
        else:
            # 取消全部时，取消所有子项
            self.filter_image.set(False)
            self.filter_video.set(False)
            self.filter_audio.set(False)
            self.filter_text.set(False)
            self.filter_app.set(False)
            self.filter_archive.set(False)

    def _on_filter_item_changed(self):
        """当任意子项改变时，更新"全部"状态"""
        all_checked = all([
            self.filter_image.get(),
            self.filter_video.get(),
            self.filter_audio.get(),
            self.filter_text.get(),
            self.filter_app.get(),
            self.filter_archive.get()
        ])
        self.filter_all.set(all_checked)

    def _get_allowed_extensions(self) -> set:
        """获取允许的文件后缀集合"""
        allowed = set()
        
        # 如果选择"全部"，返回None表示不过滤
        if self.filter_all.get():
            return None
        
        # 图片文件
        if self.filter_image.get():
            allowed.update(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
                          '.webp', '.svg', '.ico', '.psd', '.raw', '.cr2', '.nef',
                          '.heic', '.heif', '.avif'])
        
        # 视频文件
        if self.filter_video.get():
            allowed.update(['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', 
                          '.mpeg', '.mpg', '.3gp', '.m4v', '.rmvb', '.rm', '.asf',
                          '.ts', '.mts', '.vob', '.divx', '.xvid'])
        
        # 音频文件
        if self.filter_audio.get():
            allowed.update(['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a',
                          '.ape', '.alac', '.dsd', '.mid', '.midi', '.amr', '.opus'])
        
        # 文本/文档文件
        if self.filter_text.get():
            allowed.update(['.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt', '.md',
                          '.csv', '.xls', '.xlsx', '.ppt', '.pptx', '.epub', '.mobi',
                          '.tex', '.html', '.htm', '.xml', '.json', '.yaml', '.yml'])
        
        # 应用程序文件
        if self.filter_app.get():
            allowed.update(['.exe', '.msi', '.app', '.deb', '.rpm', '.apk', '.dmg',
                          '.jar', '.py', '.java', '.cpp', '.c', '.cs', '.js', '.ts',
                          '.php', '.rb', '.go', '.swift', '.kt', '.sh', '.bat', '.cmd'])
        
        # 压缩/归档文件
        if self.filter_archive.get():
            allowed.update(['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
                          '.iso', '.cab', '.arj', '.lzh', '.ace', '.uue', '.tgz'])
        
        # 自定义后缀
        custom_exts = self.custom_extensions_var.get().strip()
        if custom_exts:
            # 支持逗号、分号、空格分隔
            import re
            ext_list = re.split(r'[,，;；\s]+', custom_exts)
            for ext in ext_list:
                ext = ext.strip().lower()
                if ext and not ext.startswith('.'):
                    ext = '.' + ext
                if ext:
                    allowed.add(ext)
        
        return allowed

    def _start_scan(self):
        """开始扫描"""
        if not self.directories:
            messagebox.showerror("错误", "请先添加至少一个扫描目录！")
            return

        # 验证目录是否存在
        for directory in self.directories:
            if not os.path.exists(directory):
                messagebox.showerror("错误", f"目录不存在: {directory}")
                return

        # 获取设置
        self.db_path = self.db_var.get()
        self.output_path = self.output_var.get()
        try:
            self.workers = int(self.workers_var.get())
            if self.workers < 1 or self.workers > 32:
                raise ValueError()
        except:
            messagebox.showerror("错误", "线程数必须在1-32之间！")
            return

        # 解析文件类型过滤设置
        allowed_extensions = self._get_allowed_extensions()
        if not allowed_extensions:
            messagebox.showwarning("警告", "请至少选择一种文件类型！")
            return

        # 重置停止标志
        self.stop_flag.clear()
        self.current_progress = 0
        self.progress_var.set(0)

        # 禁用按钮
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.is_scanning = True

        # 清空日志
        self.log_text.delete(1.0, tk.END)

        # 在新线程中执行扫描，传递过滤参数
        scan_thread = threading.Thread(target=self._run_scan, args=(allowed_extensions,), daemon=True)
        scan_thread.start()

    def _run_scan(self, allowed_extensions: set):
        """执行扫描任务"""
        try:
            self._log("=" * 60)
            self._log("开始扫描...")
            self._log("=" * 60)
            self._log(f"扫描目录数量: {len(self.directories)} 个")
            
            # 列出所有要扫描的目录
            for i, directory in enumerate(self.directories, 1):
                self._log(f"  [{i}] {directory}")
            
            self._log(f"数据库: {self.db_path}")
            self._log(f"输出文件: {self.output_path}")
            self._log(f"工作线程: {self.workers}")
            
            # 显示文件类型过滤信息
            ext_count = len(allowed_extensions)
            if ext_count <= 10:
                ext_list = '、'.join(sorted(allowed_extensions))
                self._log(f"文件类型过滤: {ext_list} (共{ext_count}种)")
            else:
                self._log(f"文件类型过滤: 已选择 {ext_count} 种文件类型")
            self._log("")

            self.status_var.set("正在扫描目录...")
            self.progress_var.set(0)
            self.progress_detail_var.set("初始化中...")
            self.root.update_idletasks()

            # 创建检测器，传入进度回调、停止标志和日志回调
            # 默认每次扫描前清空数据库，确保只扫描当前选择的目录
            # max_workers=None 时自动检测CPU核心数并设置最优线程数
            self.finder = DuplicateFinder(
                db_path=self.db_path,
                chunk_size=65536,  # 64KB读取块，提升I/O效率
                max_workers=None,  # 自动检测最优线程数
                progress_callback=self._update_progress,
                stop_flag=self.stop_flag.is_set,
                log_callback=self._log_from_finder,
                clear_db=True,  # 清空旧数据
                allowed_extensions=allowed_extensions  # 文件类型过滤
            )

            # 扫描目录
            self.finder.scan_directories(self.directories)

            self.status_var.set("正在查找重复文件...")
            self.progress_detail_var.set("")
            self._log("")

            # 查找重复
            duplicate_groups = self.finder.find_duplicates()

            if duplicate_groups:
                # 导出结果
                self.status_var.set("正在导出结果...")
                self.finder.export_results(duplicate_groups, self.output_path)
                self._log(f"\n结果已保存到: {self.output_path}")

            # 打印摘要
            self.finder.print_summary()

            self.status_var.set("扫描完成！")
            self.progress_var.set(100)
            self._log("\n" + "=" * 60)
            self._log("扫描完成！")
            self._log("=" * 60)

            messagebox.showinfo("完成", f"扫描完成！\n发现 {len(duplicate_groups)} 个重复文件组")

        except InterruptedError:
            self._log("\n扫描已被用户中止")
            self.status_var.set("已停止")
            messagebox.showinfo("已停止", "扫描已被用户中止")

        except Exception as e:
            self._log(f"\n错误: {e}")
            self.status_var.set("扫描失败")
            messagebox.showerror("错误", f"扫描过程中出现错误:\n{e}")

        finally:
            self.is_scanning = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def _update_progress(self, progress: float, detail: str = ""):
        """更新进度条"""
        self.current_progress = progress
        
        # 如果是目录扫描阶段（progress=0），保持indeterminate模式
        if progress == 0 and detail:
            # 目录扫描阶段：显示详情但不设置百分比
            self.progress_detail_var.set(detail)
        else:
            # 哈希计算阶段：显示百分比
            self.progress_var.set(progress)
            if detail:
                self.progress_detail_var.set(f"{detail} ({progress:.1f}%)")
        
        self.root.update_idletasks()

    def _log_from_finder(self, message: str):
        """从DuplicateFinder接收日志消息"""
        # 直接调用_log方法，会自动添加时间戳
        self._log(message)

    def _stop_scan(self):
        """停止扫描"""
        if messagebox.askyesno("确认", "确定要停止扫描吗？"):
            self.stop_flag.set()  # 设置停止标志
            self.status_var.set("正在停止...")
            self._log("用户请求停止扫描...")

    def _sort_tree(self, tree, column, numeric):
        """对Treeview进行排序"""
        # 获取当前排序状态
        reverse = tree._sort_reverse.get(column, False)
        tree._sort_reverse[column] = not reverse
        
        # 获取所有数据项
        data = []
        for item_id in tree.get_children(''):
            if column == '#0':
                # 组别列：按文本排序
                value = tree.item(item_id, 'text')
            elif column == 'size':
                # 文件大小列：使用原始字节数排序
                for gd in tree._group_data:
                    if gd['item_id'] == item_id:
                        value = gd['size_bytes']
                        break
            else:
                # 文件数量列：使用原始数量排序
                for gd in tree._group_data:
                    if gd['item_id'] == item_id:
                        value = gd['count']
                        break
            
            data.append((value, item_id))
        
        # 排序
        data.sort(key=lambda x: x[0], reverse=reverse)
        
        # 重新排列树形视图中的项
        for index, (value, item_id) in enumerate(data):
            tree.move(item_id, '', index)

    def _view_results(self):
        """查看结果"""
        if not os.path.exists(self.output_path):
            messagebox.showwarning("警告", "结果文件不存在！请先执行扫描。")
            return

        try:
            with open(self.output_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            # 创建结果窗口
            result_window = tk.Toplevel(self.root)
            result_window.title("扫描结果")
            result_window.geometry("900x700")

            # 获取摘要数据
            summary = results['scan_summary']

            # 顶部区域：摘要 + 筛选（使用PanedWindow实现可调整比例）
            top_paned = ttk.PanedWindow(result_window, orient=tk.HORIZONTAL)
            top_paned.pack(fill=tk.X, padx=10, pady=5)

            # 左侧：摘要信息（固定宽度300px）
            summary_frame = ttk.LabelFrame(top_paned, text="扫描摘要", padding="10")
            top_paned.add(summary_frame, weight=0)

            summary_text = (
                f"总文件数: {summary['total_files_scanned']:,}\n"
                f"总大小: {summary['total_size_formatted']}\n"
                f"重复文件组: {summary['duplicate_groups']:,}\n"
                f"重复文件数: {summary['duplicate_files']:,}\n"
                f"浪费空间: {summary['wasted_space_formatted']}"
            )

            ttk.Label(summary_frame, text=summary_text, font=("微软雅黑", 10)).pack(anchor=tk.W)

            # 右侧：筛选条件（占据剩余空间）
            filter_frame = ttk.LabelFrame(top_paned, text="快速筛选", padding="10")
            top_paned.add(filter_frame, weight=1)

            # 使用Grid布局优化筛选控件排列
            # 第一行：文件后缀
            ttk.Label(filter_frame, text="文件后缀:", width=8).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
            self.result_ext_filter_var = tk.StringVar()
            ext_entry = ttk.Entry(filter_frame, textvariable=self.result_ext_filter_var, width=25)
            ext_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
            ttk.Label(filter_frame, text="(模糊匹配，如: png)", foreground="gray", font=("微软雅黑", 8)).grid(row=0, column=2, sticky=tk.W, padx=(5, 0))

            # 第二行：文件大小（带单位选择）
            ttk.Label(filter_frame, text="文件大小:", width=8).grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
            
            size_input_frame = ttk.Frame(filter_frame)
            size_input_frame.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=(5, 0))
            
            self.result_size_min_var = tk.StringVar()
            ttk.Entry(size_input_frame, textvariable=self.result_size_min_var, width=8).pack(side=tk.LEFT, padx=(0, 2))
            
            ttk.Label(size_input_frame, text="-").pack(side=tk.LEFT, padx=2)
            
            self.result_size_max_var = tk.StringVar()
            ttk.Entry(size_input_frame, textvariable=self.result_size_max_var, width=8).pack(side=tk.LEFT, padx=2)
            
            # 单位选择下拉框（放在最后）
            self.result_size_unit_var = tk.StringVar(value="KB")
            unit_combo = ttk.Combobox(size_input_frame, textvariable=self.result_size_unit_var, 
                                     values=["B", "KB", "MB", "GB"], width=5, state="readonly")
            unit_combo.pack(side=tk.LEFT, padx=(2, 0))
            
            # 第三行：按钮
            btn_frame = ttk.Frame(filter_frame)
            btn_frame.grid(row=2, column=0, columnspan=3, sticky=tk.E, pady=(8, 0))

            def apply_filter():
                """应用筛选条件"""
                ext_keyword = self.result_ext_filter_var.get().strip().lower()
                size_min_str = self.result_size_min_var.get().strip()
                size_max_str = self.result_size_max_var.get().strip()
                size_unit = self.result_size_unit_var.get()
                
                # 根据单位转换为字节
                unit_multipliers = {
                    'B': 1,
                    'KB': 1024,
                    'MB': 1024 * 1024,
                    'GB': 1024 * 1024 * 1024
                }
                multiplier = unit_multipliers.get(size_unit, 1024)
                
                # 解析大小
                size_min = int(float(size_min_str) * multiplier) if size_min_str else 0
                size_max = int(float(size_max_str) * multiplier) if size_max_str else float('inf')
                
                # 清空当前列表
                for item in tree.get_children(''):
                    tree.delete(item)
                
                # 重新插入符合条件的数据
                filtered_count = 0
                for group in results['duplicate_groups']:
                    # 检查后缀（模糊匹配）
                    ext_match = True
                    if ext_keyword:
                        # 收集该组所有后缀
                        extensions = set()
                        for file_info in group['files']:
                            _, ext = os.path.splitext(file_info['path'])
                            if ext:
                                extensions.add(ext.lower()[1:])  # 去掉点号
                            else:
                                extensions.add('无后缀')
                        ext_display = '、'.join(sorted(extensions))
                        ext_match = ext_keyword in ext_display
                    
                    # 检查大小范围
                    size_bytes = group['file_size']
                    size_match = size_min <= size_bytes <= size_max
                    
                    if ext_match and size_match:
                        group_id = f"第 {group['group_id']} 组"
                        count = group['file_count']
                        
                        # 提取该组中所有不同的文件后缀
                        extensions = set()
                        for file_info in group['files']:
                            _, ext = os.path.splitext(file_info['path'])
                            if ext:
                                extensions.add(ext.lower())
                            else:
                                extensions.add('(无后缀)')
                        
                        ext_display = '、'.join(sorted(extensions)) if extensions else '(未知)'
                        
                        tree.insert('', tk.END, text=group_id, values=(
                            ext_display,
                            group['file_size_formatted'],
                            f"{count} 个文件"
                        ))
                        filtered_count += 1
                
                self._log(f"筛选结果: 显示 {filtered_count} 个组（共{len(results['duplicate_groups'])}个）")

            def clear_filter():
                """清除筛选"""
                self.result_ext_filter_var.set("")
                self.result_size_min_var.set("")
                self.result_size_max_var.set("")
                self.result_size_unit_var.set("KB")
                
                # 重新加载所有数据
                for item in tree.get_children(''):
                    tree.delete(item)
                
                for group in results['duplicate_groups']:
                    group_id = f"第 {group['group_id']} 组"
                    count = group['file_count']
                    
                    extensions = set()
                    for file_info in group['files']:
                        _, ext = os.path.splitext(file_info['path'])
                        if ext:
                            extensions.add(ext.lower())
                        else:
                            extensions.add('(无后缀)')
                    
                    ext_display = '、'.join(sorted(extensions)) if extensions else '(未知)'
                    
                    tree.insert('', tk.END, text=group_id, values=(
                        ext_display,
                        group['file_size_formatted'],
                        f"{count} 个文件"
                    ))
                
                self._log("已清除筛选，显示所有组")

            ttk.Button(btn_frame, text="应用筛选", command=apply_filter, width=12).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="清除筛选", command=clear_filter, width=12).pack(side=tk.LEFT, padx=2)
            
            # 配置列权重，使输入框可以伸缩
            filter_frame.columnconfigure(1, weight=1)

            # 重复组列表
            groups_frame = ttk.LabelFrame(result_window, text="重复文件组（点击列标题排序）", padding="10")
            groups_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            # 创建树形视图，支持排序，添加后缀列
            tree = ttk.Treeview(groups_frame, columns=('ext', 'size', 'count'), show='tree headings')
            tree.heading('#0', text='组别', command=lambda: self._sort_tree(tree, '#0', False))
            tree.heading('ext', text='文件后缀', command=lambda: self._sort_tree(tree, 'ext', False))
            tree.heading('size', text='文件大小', command=lambda: self._sort_tree(tree, 'size', True))
            tree.heading('count', text='文件数量', command=lambda: self._sort_tree(tree, 'count', True))
            
            # 设置列宽
            tree.column('#0', width=80)
            tree.column('ext', width=100)
            tree.column('size', width=120)
            tree.column('count', width=100)

            scrollbar = ttk.Scrollbar(groups_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 插入数据，保存原始数据用于排序
            group_data = []
            for group in results['duplicate_groups']:
                group_id = f"第 {group['group_id']} 组"
                size_bytes = group['file_size']  # 保存原始字节数用于排序
                count = group['file_count']
                
                # 提取该组中所有不同的文件后缀
                extensions = set()
                for file_info in group['files']:
                    _, ext = os.path.splitext(file_info['path'])
                    if ext:
                        extensions.add(ext.lower())
                    else:
                        extensions.add('(无后缀)')
                
                # 用"、"连接所有后缀
                if extensions:
                    ext_display = '、'.join(sorted(extensions))
                else:
                    ext_display = '(未知)'
                
                item_id = tree.insert('', tk.END, text=group_id, values=(
                    ext_display,
                    group['file_size_formatted'],
                    f"{count} 个文件"
                ))
                group_data.append({
                    'item_id': item_id,
                    'group_idx': group['group_id'] - 1,
                    'size_bytes': size_bytes,
                    'count': count,
                    'extension': ext_display.lower()  # 用于排序
                })

            # 绑定排序状态
            tree._sort_reverse = {}
            tree._group_data = group_data
            
            # 隐藏的组ID集合（仅本次会话）
            tree._hidden_groups = set()

            # 添加右键菜单 - 隐藏功能
            context_menu = tk.Menu(tree, tearoff=0)
            
            def hide_group():
                """隐藏选中的组"""
                selection = tree.selection()
                if selection:
                    for item_id in selection:
                        item_text = tree.item(item_id, 'text')
                        # 提取组号
                        try:
                            group_num = int(item_text.split()[1])
                            tree._hidden_groups.add(group_num)
                            tree.delete(item_id)
                            self._log(f"已隐藏 {item_text}")
                        except:
                            pass
            
            def show_all_groups():
                """显示所有隐藏的组"""
                if tree._hidden_groups:
                    hidden_count = len(tree._hidden_groups)
                    tree._hidden_groups.clear()
                    
                    # 重新加载结果
                    result_window.destroy()
                    self._view_results()
                    self._log(f"已显示所有隐藏的组（共{hidden_count}个）")
            
            context_menu.add_command(label="隐藏此组", command=hide_group)
            context_menu.add_separator()
            context_menu.add_command(label="显示所有隐藏的组", command=show_all_groups)
            
            # 绑定右键菜单
            def show_context_menu(event):
                # 获取点击位置的项
                item = tree.identify_row(event.y)
                if item:
                    # 选中该项
                    tree.selection_set(item)
                    # 显示菜单
                    context_menu.post(event.x_root, event.y_root)
            
            tree.bind('<Button-3>', show_context_menu)

            # 双击查看详情
            def on_double_click(event):
                selection = tree.selection()
                if selection:
                    item = tree.item(selection[0])
                    group_idx = int(item['text'].split()[1]) - 1

                    # 显示文件详情
                    detail_window = tk.Toplevel(result_window)
                    detail_window.title(f"重复文件组 {group_idx + 1}")
                    detail_window.geometry("700x500")

                    detail_frame = ttk.Frame(detail_window, padding="10")
                    detail_frame.pack(fill=tk.BOTH, expand=True)

                    group_info = results['duplicate_groups'][group_idx]
                    
                    # 标题信息
                    header_frame = ttk.Frame(detail_frame)
                    header_frame.pack(fill=tk.X, pady=(0, 10))
                    
                    ttk.Label(header_frame, text=f"文件大小: {group_info['file_size_formatted']}", 
                             font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
                    
                    ttk.Label(header_frame, text="💡 提示: 点击文件路径可打开所在文件夹", 
                             font=("微软雅黑", 8), foreground="gray").pack(side=tk.RIGHT)

                    # 文件列表（使用Text控件支持点击）
                    list_frame = ttk.LabelFrame(detail_frame, text="文件列表（点击路径打开文件夹）", padding="5")
                    list_frame.pack(fill=tk.BOTH, expand=True)

                    text_widget = scrolledtext.ScrolledText(
                        list_frame,
                        font=("Consolas", 9),
                        wrap=tk.WORD,
                        cursor="hand2"  # 手型光标
                    )
                    text_widget.pack(fill=tk.BOTH, expand=True)

                    # 插入文件列表
                    for i, file_info in enumerate(group_info['files'], 1):
                        file_path = file_info['path']
                        text_widget.insert(tk.END, f"{i}. ")
                        
                        # 插入可点击的路径
                        path_tag = f"path_{i}"
                        text_widget.insert(tk.END, file_path, (path_tag, "clickable"))
                        text_widget.insert(tk.END, "\n\n")

                    # 配置可点击文本的样式
                    text_widget.tag_configure("clickable", foreground="blue", underline=True)
                    
                    # 绑定点击事件
                    def open_folder(event):
                        # 获取点击位置的文本标签
                        index = text_widget.index(f"@{event.x},{event.y}")
                        tags = text_widget.tag_names(index)
                        
                        # 查找 clickable 标签
                        for tag in tags:
                            if tag.startswith("path_"):
                                # 获取该行的完整路径
                                line_start = text_widget.index(f"{index} linestart")
                                line_end = text_widget.index(f"{index} lineend")
                                line_text = text_widget.get(line_start, line_end)
                                
                                # 提取路径（去掉序号）
                                if '. ' in line_text:
                                    file_path = line_text.split('. ', 1)[1].strip()
                                    
                                    # 打开文件所在文件夹并选中文件
                                    import subprocess
                                    folder_path = os.path.dirname(file_path)
                                    file_name = os.path.basename(file_path)
                                    
                                    try:
                                        # Windows: 使用 explorer /select 命令打开文件夹并选中文件
                                        # 正确格式：explorer /select,"完整文件路径"
                                        subprocess.run(f'explorer /select,"{file_path}"', shell=True, check=True)
                                        self._log(f"已打开文件夹并选中文件: {file_name}")
                                    except Exception as e:
                                        # 如果失败，尝试只打开文件夹
                                        try:
                                            os.startfile(folder_path)
                                            self._log(f"已打开文件夹: {folder_path}")
                                        except Exception as e2:
                                            messagebox.showerror("错误", f"无法打开文件夹:\n{e2}")
                                return
                    
                    text_widget.bind('<Button-1>', open_folder)
                    
                    # 添加悬停效果
                    def on_enter(event):
                        text_widget.config(cursor="hand2")
                    
                    def on_leave(event):
                        text_widget.config(cursor="arrow")
                    
                    text_widget.bind('<Enter>', on_enter)
                    text_widget.bind('<Leave>', on_leave)

            tree.bind('<Double-1>', on_double_click)

        except Exception as e:
            messagebox.showerror("错误", f"读取结果文件失败:\n{e}")


def main():
    root = tk.Tk()
    app = DuplicateFinderGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
