#!/usr/bin/env python3
"""
精确匹配标签页模块
负责精确文件匹配的配置和结果显示
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import json
from datetime import datetime

# 导入公共详情窗口组件
from gui_modules.detail_window import create_exact_match_detail


class ExactMatchTab:
    """精确匹配标签页"""

    def __init__(self, parent_notebook, main_window):
        self.parent_notebook = parent_notebook
        self.main_window = main_window
        self.frame = ttk.Frame(parent_notebook)

        # 变量
        self.db_var = tk.StringVar(value="file_index.db")
        self.output_var = tk.StringVar(value="duplicates.json")
        self.workers_var = tk.StringVar(value="8")

        # 文件类型过滤
        self.filter_all = tk.BooleanVar(value=True)
        self.filter_image = tk.BooleanVar(value=False)
        self.filter_video = tk.BooleanVar(value=False)
        self.filter_audio = tk.BooleanVar(value=False)
        self.filter_text = tk.BooleanVar(value=False)
        self.filter_app = tk.BooleanVar(value=False)
        self.filter_archive = tk.BooleanVar(value=False)
        self.custom_extensions_var = tk.StringVar()

        self._create_widgets()

    def _create_widgets(self):
        """创建标签页组件"""
        # 设置区域
        settings_frame = ttk.LabelFrame(self.frame, text="扫描设置", padding="10")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)

        # 数据库路径
        db_row = ttk.Frame(settings_frame)
        db_row.pack(fill=tk.X, pady=2)
        ttk.Label(db_row, text="数据库:", width=10).pack(side=tk.LEFT)
        ttk.Entry(db_row, textvariable=self.db_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(db_row, text="浏览...", command=self._browse_db).pack(side=tk.LEFT)

        # 输出路径
        output_row = ttk.Frame(settings_frame)
        output_row.pack(fill=tk.X, pady=2)
        ttk.Label(output_row, text="输出文件:", width=10).pack(side=tk.LEFT)
        ttk.Entry(output_row, textvariable=self.output_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_row, text="浏览...", command=self._browse_output).pack(side=tk.LEFT)

        # 线程数
        workers_row = ttk.Frame(settings_frame)
        workers_row.pack(fill=tk.X, pady=2)
        ttk.Label(workers_row, text="并行线程:", width=10).pack(side=tk.LEFT)
        ttk.Spinbox(workers_row, from_=1, to=32, textvariable=self.workers_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(workers_row, text="(建议: HDD用4-8, SSD用8-16)", foreground="gray").pack(side=tk.LEFT)

        # 文件类型过滤
        self._create_filter_section(settings_frame)

    def _create_filter_section(self, parent):
        """创建文件类型过滤区域"""
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(5, 2))

        ttk.Label(filter_frame, text="文件类型:", width=10).pack(side=tk.LEFT)

        # 全部选项
        ttk.Checkbutton(filter_frame, text="全部", variable=self.filter_all,
                       command=self._on_filter_all_changed).pack(side=tk.LEFT, padx=2)

        # 预设类型
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

        # 自定义后缀（放在parent即settings_frame内）
        custom_ext_row = ttk.Frame(parent)
        custom_ext_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(custom_ext_row, text="自定义后缀:", width=10).pack(side=tk.LEFT)
        ttk.Entry(custom_ext_row, textvariable=self.custom_extensions_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Label(custom_ext_row, text="(用逗号分隔，如: .jpg,.png)", foreground="gray", font=("微软雅黑", 8)).pack(side=tk.LEFT)

        # 控制按钮区域
        self._create_control_buttons()

        # 进度区域
        self._create_progress_section()

        # 日志区域
        self._create_log_section()

    def _create_control_buttons(self):
        """创建控制按钮区域"""
        control_frame = ttk.Frame(self.frame, padding="10")
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
            command=self.view_results
        ).pack(side=tk.LEFT, padx=5)

        # 配置样式
        style = ttk.Style()
        style.configure("Accent.TButton", font=("微软雅黑", 10, "bold"))

    def _create_progress_section(self):
        """创建进度区域"""
        progress_frame = ttk.LabelFrame(self.frame, text="扫描进度", padding="10")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var, font=("微软雅黑", 9))
        status_label.pack()

        self.progress_detail_var = tk.StringVar(value="")
        detail_label = ttk.Label(progress_frame, textvariable=self.progress_detail_var, font=("微软雅黑", 8), foreground="gray")
        detail_label.pack()

    def _create_log_section(self):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(self.frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] [{level}] {message}\n")
        self.log_text.see(tk.END)
        self.frame.update_idletasks()

    def update_progress(self, progress: float, message: str):
        """更新进度条"""
        self.progress_var.set(progress)
        self.status_var.set(message)
        self.frame.update_idletasks()

    def update_detail(self, message: str):
        """更新详细信息"""
        self.progress_detail_var.set(message)
        self.frame.update_idletasks()

    def _on_filter_all_changed(self):
        """当"全部"选项改变时"""
        if self.filter_all.get():
            self.filter_image.set(True)
            self.filter_video.set(True)
            self.filter_audio.set(True)
            self.filter_text.set(True)
            self.filter_app.set(True)
            self.filter_archive.set(True)
        else:
            self.filter_image.set(False)
            self.filter_video.set(False)
            self.filter_audio.set(False)
            self.filter_text.set(False)
            self.filter_app.set(False)
            self.filter_archive.set(False)

    def _on_filter_item_changed(self):
        """当任意子项改变时"""
        all_checked = all([
            self.filter_image.get(),
            self.filter_video.get(),
            self.filter_audio.get(),
            self.filter_text.get(),
            self.filter_app.get(),
            self.filter_archive.get()
        ])
        self.filter_all.set(all_checked)

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

    def _get_allowed_extensions(self) -> set:
        """获取允许的文件后缀集合"""
        allowed = set()

        if self.filter_all.get():
            return None

        if self.filter_image.get():
            allowed.update(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
                          '.webp', '.svg', '.ico', '.psd', '.raw', '.cr2', '.nef'])

        if self.filter_video.get():
            allowed.update(['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
                          '.mpeg', '.mpg', '.3gp', '.m4v', '.rmvb', '.rm'])

        if self.filter_audio.get():
            allowed.update(['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a',
                          '.ape', '.alac', '.mid', '.midi', '.amr'])

        if self.filter_text.get():
            allowed.update(['.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt', '.md',
                          '.csv', '.xls', '.xlsx', '.ppt', '.pptx', '.html', '.xml', '.json'])

        if self.filter_app.get():
            allowed.update(['.exe', '.msi', '.app', '.deb', '.rpm', '.apk', '.dmg',
                          '.jar', '.py', '.java', '.cpp', '.c', '.js', '.ts', '.php'])

        if self.filter_archive.get():
            allowed.update(['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
                          '.iso', '.cab', '.arj', '.lzh'])

        # 自定义后缀
        custom_exts = self.custom_extensions_var.get().strip()
        if custom_exts:
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
        """启动精确匹配扫描"""
        if self.main_window.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中！")
            return

        self.main_window.is_scanning = True
        self.main_window.stop_flag.clear()

        # 更新UI状态（使用标签页自己的按钮）
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 在新线程中执行
        thread = threading.Thread(
            target=self._run_scan,
            daemon=True
        )
        thread.start()

    def _stop_scan(self):
        """停止扫描"""
        self.main_window.stop_flag.set()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._log("正在停止扫描...")

    def _run_scan(self):
        """执行扫描（后台线程）"""
        try:
            from core.duplicate_finder import DuplicateFinder

            # 获取配置
            directories = self.main_window.directories
            db_path = self.db_var.get()
            output_path = self.output_var.get()
            workers = int(self.workers_var.get())
            allowed_extensions = self._get_allowed_extensions()

            self._log(f"开始精确匹配扫描...")
            self._log(f"目录数: {len(directories)}, 线程数: {workers}")

            if allowed_extensions:
                self._log(f"文件类型过滤: {len(allowed_extensions)} 种后缀")
            else:
                self._log("文件类型: 全部")

            # 创建检测器
            finder = DuplicateFinder(
                db_path=db_path,
                max_workers=workers,
                clear_db=True,
                allowed_extensions=allowed_extensions,
                progress_callback=self._on_progress,
                stop_flag=self.main_window.stop_flag,
                log_callback=lambda msg, lvl="INFO": self._log(msg, lvl)
            )

            # 执行扫描
            finder.scan_directories(directories)
            
            # 查找重复文件
            duplicate_groups = finder.find_duplicates()
            
            # 导出结果
            if duplicate_groups:
                finder.export_results(duplicate_groups, output_path)
                
                self._log(f"扫描完成！结果已保存到: {output_path}")
                self._log(f"重复组数: {finder.stats['duplicate_groups']}")
                self._log(f"重复文件数: {finder.stats['duplicate_files']}")
                self._log(f"浪费空间: {finder._format_size(finder.stats['wasted_space'])}")
            else:
                self._log("未发现重复文件")

        except InterruptedError:
            self._log("扫描已停止", "INFO")

        except Exception as e:
            self._log(f"扫描失败: {e}", "ERROR")
            messagebox.showerror("错误", f"扫描过程中发生错误:\n{e}")

        finally:
            self.main_window.is_scanning = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.update_progress(0, "就绪")

    def _on_progress(self, progress: float, message: str):
        """进度回调"""
        self.update_progress(progress, message)

    def view_results(self):
        """查看结果"""
        output_path = self.output_var.get()
        if not os.path.exists(output_path):
            messagebox.showwarning("警告", "结果文件不存在！请先执行扫描。")
            return

        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            self._show_results_window(results)

        except Exception as e:
            messagebox.showerror("错误", f"读取结果文件失败: {e}")

    def _show_results_window(self, results):
        """显示结果窗口"""
        result_window = tk.Toplevel(self.main_window.root)
        result_window.title("扫描结果 - 精确匹配")
        result_window.geometry("1200x800")

        summary = results['scan_summary']

        # 顶部区域：摘要 + 筛选（横向布局）
        top_frame = ttk.Frame(result_window)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # 左侧：摘要信息
        summary_frame = ttk.LabelFrame(top_frame, text="扫描摘要", padding="10")
        summary_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        summary_text = (
            f"总文件数: {summary['total_files_scanned']:,}\n"
            f"总大小: {summary['total_size_formatted']}\n"
            f"重复文件组: {summary['duplicate_groups']:,}\n"
            f"重复文件数: {summary['duplicate_files']:,}\n"
            f"浪费空间: {summary['wasted_space_formatted']}"
        )

        ttk.Label(summary_frame, text=summary_text, font=("微软雅黑", 10)).pack(anchor=tk.W)

        # 右侧：筛选区域
        filter_frame = ttk.LabelFrame(top_frame, text="筛选条件", padding="10")
        filter_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 后缀模糊筛选
        ext_row = ttk.Frame(filter_frame)
        ext_row.pack(fill=tk.X, pady=2)
        ttk.Label(ext_row, text="后缀:", width=8).pack(side=tk.LEFT)
        filter_ext_var = tk.StringVar()
        ttk.Entry(ext_row, textvariable=filter_ext_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(ext_row, text="(模糊匹配)", foreground="gray", font=("微软雅黑", 8)).pack(side=tk.LEFT)

        # 文件大小范围筛选
        size_row = ttk.Frame(filter_frame)
        size_row.pack(fill=tk.X, pady=2)
        ttk.Label(size_row, text="大小范围:", width=8).pack(side=tk.LEFT)
        
        min_size_var = tk.StringVar()
        ttk.Entry(size_row, textvariable=min_size_var, width=10).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(size_row, text="~").pack(side=tk.LEFT, padx=2)
        
        max_size_var = tk.StringVar()
        ttk.Entry(size_row, textvariable=max_size_var, width=10).pack(side=tk.LEFT, padx=2)
        
        size_unit_var = tk.StringVar(value="KB")
        size_unit_combo = ttk.Combobox(size_row, textvariable=size_unit_var, values=["B", "KB", "MB", "GB"], width=6, state="readonly")
        size_unit_combo.pack(side=tk.LEFT, padx=2)

        # 筛选按钮
        btn_row = ttk.Frame(filter_frame)
        btn_row.pack(fill=tk.X, pady=(5, 2))
        
        ttk.Button(
            btn_row,
            text="应用筛选",
            command=lambda: self._apply_advanced_filter(tree, results, filter_ext_var.get(), min_size_var.get(), max_size_var.get(), size_unit_var.get())
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_row,
            text="清除筛选",
            command=lambda: self._clear_filter(tree, results)
        ).pack(side=tk.LEFT, padx=2)

        # 结果列表
        groups_frame = ttk.LabelFrame(result_window, text="重复文件组（双击打开文件夹）", padding="10")
        groups_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview with more columns
        tree = ttk.Treeview(
            groups_frame,
            columns=('size', 'count', 'extension', 'actions'),
            show='tree headings'
        )
        tree.heading('#0', text='组别')  # 移除排序命令，#0列不支持排序
        tree.heading('size', text='文件大小', command=lambda: self._sort_tree_by_column(tree, 'size'))
        tree.heading('count', text='文件数量', command=lambda: self._sort_tree_by_column(tree, 'count'))
        tree.heading('extension', text='主要后缀', command=lambda: self._sort_tree_by_column(tree, 'extension'))
        tree.heading('actions', text='操作')  # 移除排序命令

        tree.column('#0', width=100)
        tree.column('size', width=100)
        tree.column('count', width=100)
        tree.column('extension', width=120)
        tree.column('actions', width=80)

        scrollbar = ttk.Scrollbar(groups_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # 存储隐藏状态
        hidden_groups = set()

        def toggle_visibility(group_id):
            """切换组的显示/隐藏状态"""
            if group_id in hidden_groups:
                hidden_groups.remove(group_id)
            else:
                hidden_groups.add(group_id)
            self._refresh_tree_display(tree, results, hidden_groups)

        # 插入数据
        for group in results['duplicate_groups']:
            group_id = f"第 {group['group_id']} 组"
            
            # 获取主要后缀
            first_file = group['files'][0]['path'] if group['files'] else ''
            _, ext = os.path.splitext(first_file)
            extension = ext.lower() if ext else '(无)'

            tree.insert('', tk.END, text=group_id, values=(
                group['file_size_formatted'],
                f"{group['file_count']} 个文件",
                extension,
                "隐藏"
            ), tags=(group['group_id'],))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件
        tree.bind('<Double-Button-1>', lambda e: self._on_double_click_group(tree, results))
        # 只在点击"操作"列时才触发隐藏
        tree.bind('<ButtonRelease-1>', lambda e: self._on_click_actions_column(tree, e, hidden_groups, toggle_visibility))

    def _on_click_actions_column(self, tree, event, hidden_groups, toggle_func):
        """只在点击操作列时触发隐藏"""
        # 获取点击的列
        region = tree.identify_region(event.x, event.y)
        column = tree.identify_column(event.x)
        
        # 只有在操作列（最后一列）点击时才触发
        if column == '#4':  # actions 是第4列（从#0开始）
            item = tree.identify_row(event.y)
            if item:
                item_text = tree.item(item, 'text')
                try:
                    group_num = int(item_text.split()[1])
                    toggle_func(group_num)
                except:
                    pass

    def _refresh_tree_display(self, tree, results, hidden_groups):
        """刷新Treeview显示"""
        # 清空现有数据
        for item in tree.get_children(''):
            tree.delete(item)

        # 重新插入未隐藏的组
        for group in results['duplicate_groups']:
            if group['group_id'] in hidden_groups:
                continue

            group_id = f"第 {group['group_id']} 组"
            first_file = group['files'][0]['path'] if group['files'] else ''
            _, ext = os.path.splitext(first_file)
            extension = ext.lower() if ext else '(无)'

            tree.insert('', tk.END, text=group_id, values=(
                group['file_size_formatted'],
                f"{group['file_count']} 个文件",
                extension,
                "隐藏"
            ), tags=(group['group_id'],))

    def _apply_advanced_filter(self, tree, results, filter_ext, min_size, max_size, size_unit):
        """应用高级筛选（后缀+大小）"""
        # 转换大小单位为字节
        unit_multipliers = {'B': 1, 'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024}
        multiplier = unit_multipliers.get(size_unit, 1)
        
        min_bytes = float(min_size.strip()) * multiplier if min_size.strip() else 0
        max_bytes = float(max_size.strip()) * multiplier if max_size.strip() else float('inf')

        # 过滤匹配的组
        filtered_groups = []
        for group in results['duplicate_groups']:
            file_size = group['file_size']
            
            # 检查大小范围
            if not (min_bytes <= file_size <= max_bytes):
                continue
            
            # 检查后缀（模糊匹配）
            if filter_ext.strip():
                filter_lower = filter_ext.strip().lower()
                if not filter_lower.startswith('.'):
                    filter_lower = '.' + filter_lower
                
                has_match = False
                for file_info in group['files']:
                    _, ext = os.path.splitext(file_info['path'])
                    if filter_lower in ext.lower():
                        has_match = True
                        break
                
                if not has_match:
                    continue
            
            filtered_groups.append(group)

        # 更新结果显示
        for item in tree.get_children(''):
            tree.delete(item)

        for group in filtered_groups:
            group_id = f"第 {group['group_id']} 组"
            first_file = group['files'][0]['path'] if group['files'] else ''
            _, ext = os.path.splitext(first_file)
            extension = ext.lower() if ext else '(无)'

            tree.insert('', tk.END, text=group_id, values=(
                group['file_size_formatted'],
                f"{group['file_count']} 个文件",
                extension,
                "隐藏"
            ))

    def _apply_filter(self, tree, results, filter_ext):
        """应用后缀筛选（保留旧方法兼容）"""
        self._apply_advanced_filter(tree, results, filter_ext, '', '', 'KB')

    def _clear_filter(self, tree, results):
        """清除筛选"""
        for item in tree.get_children(''):
            tree.delete(item)

        for group in results['duplicate_groups']:
            group_id = f"第 {group['group_id']} 组"
            first_file = group['files'][0]['path'] if group['files'] else ''
            _, ext = os.path.splitext(first_file)
            extension = ext.lower() if ext else '(无)'

            tree.insert('', tk.END, text=group_id, values=(
                group['file_size_formatted'],
                f"{group['file_count']} 个文件",
                extension,
                "隐藏"
            ))

    def _parse_size_to_bytes(self, size_str):
        """将格式化的大小字符串转换为字节数"""
        if not size_str:
            return 0
        
        size_str = size_str.strip()
        
        # 定义单位映射
        unit_multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024
        }
        
        # 尝试匹配数字和单位
        import re
        match = re.match(r'([\d,.]+)\s*([KMGT]?B)', size_str)
        if match:
            number_str, unit = match.groups()
            number = float(number_str.replace(',', ''))
            multiplier = unit_multipliers.get(unit, 1)
            return number * multiplier
        
        # 如果无法解析，返回0
        return 0

    def _sort_tree_by_column(self, tree, column):
        """按列排序Treeview"""
        items = [(tree.set(k, column), k) for k in tree.get_children('')]
        
        # 根据列类型选择排序方式
        if column == 'size':
            # 文件大小列：转换为字节后排序
            try:
                items.sort(key=lambda x: self._parse_size_to_bytes(x[0]))
            except:
                items.sort(key=lambda x: x[0])
        else:
            # 其他列：尝试数值排序
            try:
                items.sort(key=lambda x: float(x[0].replace(',', '').replace(' ', '')))
            except ValueError:
                # 字符串排序
                items.sort(key=lambda x: x[0])

        # 反转顺序（如果已经是升序则改为降序）
        if hasattr(tree, '_sort_reverse') and tree._sort_reverse:
            items.reverse()
            tree._sort_reverse = False
        else:
            tree._sort_reverse = True

        # 重新排列
        for index, (val, k) in enumerate(items):
            tree.move(k, '', index)

    def _on_double_click_group(self, tree, results):
        """双击组时显示详情窗口"""
        selection = tree.selection()
        if not selection:
            return

        item_text = tree.item(selection[0], 'text')
        try:
            group_num = int(item_text.split()[1])
            group = results['duplicate_groups'][group_num - 1]

            # 使用公共组件创建详情窗口
            detail_window_obj = create_exact_match_detail(
                parent=tree,
                group=group,
                group_num=group_num,
                main_window=self.main_window
            )
            
            # 绑定删除回调
            detail_window_obj.delete_callback = self._delete_single_file

        except Exception as e:
            messagebox.showerror("错误", f"显示详情失败: {e}")

    def _sort_file_tree(self, tree, column):
        """排序文件列表"""
        items = [(tree.set(k, column), k) for k in tree.get_children('')]
        
        # 根据列类型选择排序方式
        if column == 'size':
            # 文件大小列：转换为字节后排序
            try:
                items.sort(key=lambda x: self._parse_size_to_bytes(x[0]))
            except:
                items.sort(key=lambda x: x[0])
        else:
            # 其他列：尝试数值排序
            try:
                items.sort(key=lambda x: float(x[0].replace(',', '').replace(' ', '')))
            except ValueError:
                # 字符串排序
                items.sort(key=lambda x: x[0])

        # 反转顺序
        if hasattr(tree, '_sort_reverse') and tree._sort_reverse:
            items.reverse()
            tree._sort_reverse = False
        else:
            tree._sort_reverse = True

        # 重新排列
        for index, (val, k) in enumerate(items):
            tree.move(k, '', index)

    def _open_file_location(self, tree, group):
        """打开选中文件的位置"""
        selection = tree.selection()
        if not selection:
            return

        idx = int(tree.item(selection[0], 'text')) - 1
        if 0 <= idx < len(group['files']):
            file_path = group['files'][idx]['path']
            folder = os.path.dirname(file_path)
            
            if os.path.exists(folder):
                import subprocess
                subprocess.Popen(f'explorer /select,"{file_path}"')
            else:
                messagebox.showerror("错误", f"文件不存在: {file_path}")

    def _show_group_details(self, tree, results):
        """显示组详情（保留原有方法）"""
        selection = tree.selection()
        if not selection:
            return

        item_text = tree.item(selection[0], 'text')
        try:
            group_num = int(item_text.split()[1])
            group = results['duplicate_groups'][group_num - 1]

            # 使用公共组件创建详情窗口
            detail_window_obj = create_exact_match_detail(
                parent=self.main_window.root,
                group=group,
                group_num=group_num,
                main_window=self.main_window
            )
            
            # 绑定删除回调
            detail_window_obj.delete_callback = self._delete_single_file

        except Exception as e:
            messagebox.showerror("错误", f"显示详情失败: {e}")

    def _on_click_action_column(self, tree, group, detail_window):
        """处理操作列点击"""
        # 获取点击位置
        x = tree.winfo_pointerx() - tree.winfo_rootx()
        y = tree.winfo_pointery() - tree.winfo_rooty()
        
        # 检查是否点击在单元格上
        region = tree.identify("region", x, y)
        if region != "cell":
            return
        
        # 检查是否是操作列（第4列）
        column = tree.identify_column(x)
        if column != '#4':
            return
        
        # 获取点击的行
        item = tree.identify_row(y)
        if not item:
            return
        
        # 获取文件信息
        idx = int(tree.item(item, 'text')) - 1
        if 0 <= idx < len(group['files']):
            file_info = group['files'][idx]
            self._delete_single_file(tree, file_info, item, group, detail_window)

    def _delete_single_file(self, tree, file_info, item, group, detail_window):
        """删除单个文件（使用批处理延迟删除）"""
        if not messagebox.askyesno("确认删除", f"确定要删除以下文件吗？\n\n{file_info['path']}\n\n此操作不可恢复！"):
            return
        
        import subprocess
        import os
        
        try:
            # 创建批处理文件，延迟1秒后删除
            bat_file = os.path.join(os.environ['TEMP'], 'force_delete.bat')
            with open(bat_file, 'w', encoding='gbk') as f:
                f.write('@echo off\n')
                f.write('timeout /t 1 /nobreak >nul\n')
                f.write(f'del /f /q "{file_info["path"]}"\n')
                f.write('del "%~f0"\n')  # 删除自身
            
            # 异步执行批处理（隐藏窗口）
            subprocess.Popen([bat_file], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 立即从UI中移除
            tree.delete(item)
            group['files'] = [f for f in group['files'] if f['path'] != file_info['path']]
            
            # 如果所有文件都被删除，关闭详情窗口
            if len(tree.get_children('')) == 0:
                detail_window.destroy()
            
        except Exception as e:
            messagebox.showerror("删除失败", f"无法创建删除任务:\n{str(e)}\n\n请手动删除文件: {file_info['path']}")

    def _delete_selected_files(self, tree, group, detail_window):
        """删除选中的文件"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的文件")
            return
        
        # 获取选中的文件路径
        files_to_delete = []
        for item in selection:
            idx = int(tree.item(item, 'text')) - 1
            if 0 <= idx < len(group['files']):
                files_to_delete.append(group['files'][idx])
        
        if not files_to_delete:
            return
        
        # 确认删除
        file_list = "\n".join([f['path'] for f in files_to_delete[:3]])
        if len(files_to_delete) > 3:
            file_list += f"\n...等共{len(files_to_delete)}个文件"
        
        if not messagebox.askyesno("确认删除", f"确定要删除以下{len(files_to_delete)}个文件吗？\n\n{file_list}\n\n此操作不可恢复！"):
            return
        
        # 执行删除
        deleted_count = 0
        failed_files = []
        
        for file_info in files_to_delete:
            try:
                os.remove(file_info['path'])
                deleted_count += 1
                # 从Treeview中移除
                for item in tree.get_children(''):
                    if tree.item(item, 'values')[2] == file_info['path']:
                        tree.delete(item)
                        break
            except Exception as e:
                failed_files.append((file_info['path'], str(e)))
        
        # 显示结果
        if deleted_count > 0:
            messagebox.showinfo("删除完成", f"成功删除 {deleted_count} 个文件")
            
            # 如果所有文件都被删除，关闭详情窗口
            if deleted_count == len(files_to_delete) and len(tree.get_children('')) == 0:
                detail_window.destroy()
        
        if failed_files:
            error_msg = f"以下 {len(failed_files)} 个文件删除失败:\n\n"
            for path, error in failed_files[:5]:
                error_msg += f"{os.path.basename(path)}: {error}\n"
            if len(failed_files) > 5:
                error_msg += f"...等共{len(failed_files)}个文件"
            messagebox.showerror("删除失败", error_msg)

    def _open_file_location(self, tree, group):
        """打开选中文件的位置"""
        selection = tree.selection()
        if not selection:
            return

        idx = int(tree.item(selection[0], 'text')) - 1
        if 0 <= idx < len(group['files']):
            file_path = group['files'][idx]['path']
            folder = os.path.dirname(file_path)
            
            if os.path.exists(folder):
                import subprocess
                subprocess.Popen(f'explorer /select,"{file_path}"')
            else:
                messagebox.showerror("错误", f"文件不存在: {file_path}")

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
