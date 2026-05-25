#!/usr/bin/env python3
"""
相似度检测标签页模块
负责图片相似度检测的配置、执行和结果显示
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import subprocess
from datetime import datetime


class SimilarityTab:
    """相似度检测标签页"""

    def __init__(self, parent_notebook, main_window):
        self.parent_notebook = parent_notebook
        self.main_window = main_window
        self.frame = ttk.Frame(parent_notebook)

        # 变量
        self.threshold_var = tk.IntVar(value=12)
        self.mode_var = tk.StringVar(value="precise")
        self.incremental_var = tk.BooleanVar(value=False)
        self.db_path_var = tk.StringVar(value="image_similarity.db")

        # 图片格式过滤
        self.format_all = tk.BooleanVar(value=True)
        self.format_jpg = tk.BooleanVar(value=True)
        self.format_png = tk.BooleanVar(value=True)
        self.format_gif = tk.BooleanVar(value=True)
        self.format_bmp = tk.BooleanVar(value=True)
        self.format_webp = tk.BooleanVar(value=True)

        # 结果相关
        self.current_groups = []
        self.hidden_groups = set()  # 隐藏的组ID
        self.results_window = None  # 结果窗口引用

        self._create_widgets()

    def _create_widgets(self):
        """创建标签页组件"""
        # 配置区域
        config_frame = ttk.LabelFrame(self.frame, text="检测设置", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        # 第一行：相似度阈值
        threshold_row = ttk.Frame(config_frame)
        threshold_row.pack(fill=tk.X, pady=2)

        ttk.Label(threshold_row, text="相似度阈值:", width=12).pack(side=tk.LEFT)

        threshold_scale = ttk.Scale(
            threshold_row,
            from_=5, to=30,
            variable=self.threshold_var,
            orient=tk.HORIZONTAL,
            command=self._update_threshold_label,
            length=200
        )
        threshold_scale.pack(side=tk.LEFT, padx=5)

        self.threshold_label = ttk.Label(threshold_row, text="12 (平衡模式)", width=20)
        self.threshold_label.pack(side=tk.LEFT)

        # 添加Tooltip
        self._add_tooltip(threshold_scale, "汉明距离≤12表示相似，值越小要求越严格\n5=严格, 12=平衡, 20=宽松")

        # 第二行：检测模式
        mode_row = ttk.Frame(config_frame)
        mode_row.pack(fill=tk.X, pady=2)

        ttk.Label(mode_row, text="检测模式:", width=12).pack(side=tk.LEFT)

        ttk.Radiobutton(
            mode_row,
            text="快速模式（仅pHash）",
            variable=self.mode_var,
            value="fast"
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            mode_row,
            text="精确模式（pHash+dHash+直方图）",
            variable=self.mode_var,
            value="precise"
        ).pack(side=tk.LEFT, padx=5)

        # 第三行：扫描方式
        scan_row = ttk.Frame(config_frame)
        scan_row.pack(fill=tk.X, pady=2)

        ttk.Label(scan_row, text="扫描方式:", width=12).pack(side=tk.LEFT)

        ttk.Radiobutton(
            scan_row,
            text="全量扫描",
            variable=self.incremental_var,
            value=False
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            scan_row,
            text="增量扫描（仅新增/修改）",
            variable=self.incremental_var,
            value=True
        ).pack(side=tk.LEFT, padx=5)

        # 第四行：数据库路径
        db_row = ttk.Frame(config_frame)
        db_row.pack(fill=tk.X, pady=2)

        ttk.Label(db_row, text="数据库:", width=12).pack(side=tk.LEFT)
        ttk.Entry(db_row, textvariable=self.db_path_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(db_row, text="浏览...", command=self._browse_db).pack(side=tk.LEFT)

        # 图片格式过滤
        format_frame = ttk.LabelFrame(self.frame, text="图片格式", padding="10")
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Checkbutton(format_frame, text="全部", variable=self.format_all,
                       command=self._on_format_all_changed).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(format_frame, text="JPG", variable=self.format_jpg,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_frame, text="PNG", variable=self.format_png,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_frame, text="GIF", variable=self.format_gif,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_frame, text="BMP", variable=self.format_bmp,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_frame, text="WebP", variable=self.format_webp,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)

        # 控制按钮
        btn_frame = ttk.Frame(self.frame, padding="5")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_btn = ttk.Button(
            btn_frame,
            text="开始检测",
            command=self.start_scan,
            style="Accent.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(
            btn_frame,
            text="停止",
            command=self._stop_scan,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="结果",
            command=self._show_results_window
        ).pack(side=tk.LEFT, padx=5)

        # 进度条
        progress_frame = ttk.Frame(self.frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X)

        self.status_label = ttk.Label(progress_frame, text="", font=("微软雅黑", 8))
        self.status_label.pack()

        # 日志区域
        log_frame = ttk.LabelFrame(self.frame, text="运行日志", padding="10")
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
        style.configure("Accent.TButton", font=("微软雅黑", 9, "bold"))

    def _log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] [{level}] {message}\n")
        self.log_text.see(tk.END)
        self.frame.update_idletasks()

    def update_progress(self, progress: float, message: str):
        """更新进度条"""
        self.progress_var.set(progress)
        self.status_label.config(text=message)
        self.frame.update_idletasks()

    def update_detail(self, message: str):
        """更新详细信息（在相似度标签页中不显示）"""
        pass

    def _add_tooltip(self, widget, text):
        """添加工具提示"""
        def show_tooltip(event):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=text, background="#ffffe0", relief='solid', borderwidth=1)
            label.pack()
            widget._tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(widget, '_tooltip'):
                widget._tooltip.destroy()
                del widget._tooltip

        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)

    def _update_threshold_label(self, value):
        """更新阈值标签"""
        threshold = int(float(value))
        if threshold <= 8:
            mode_text = "严格模式"
        elif threshold <= 15:
            mode_text = "平衡模式"
        else:
            mode_text = "宽松模式"
        self.threshold_label.config(text=f"{threshold} ({mode_text})")

    def _on_format_all_changed(self):
        """当"全部"选项改变时"""
        if self.format_all.get():
            self.format_jpg.set(True)
            self.format_png.set(True)
            self.format_gif.set(True)
            self.format_bmp.set(True)
            self.format_webp.set(True)
        else:
            self.format_jpg.set(False)
            self.format_png.set(False)
            self.format_gif.set(False)
            self.format_bmp.set(False)
            self.format_webp.set(False)

    def _on_format_item_changed(self):
        """当任意格式项改变时"""
        all_checked = all([
            self.format_jpg.get(),
            self.format_png.get(),
            self.format_gif.get(),
            self.format_bmp.get(),
            self.format_webp.get()
        ])
        self.format_all.set(all_checked)

    def _browse_db(self):
        """浏览数据库文件"""
        filename = filedialog.asksaveasfilename(
            title="选择数据库文件",
            defaultextension=".db",
            filetypes=[("数据库文件", "*.db"), ("所有文件", "*.*")]
        )
        if filename:
            self.db_path_var.set(filename)

    def _get_supported_formats(self) -> set:
        """获取支持的图片格式"""
        formats = set()

        if self.format_all.get():
            return {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

        if self.format_jpg.get():
            formats.update(['.jpg', '.jpeg'])
        if self.format_png.get():
            formats.add('.png')
        if self.format_gif.get():
            formats.add('.gif')
        if self.format_bmp.get():
            formats.add('.bmp')
        if self.format_webp.get():
            formats.add('.webp')

        return formats

    def start_scan(self):
        """启动相似度检测"""
        if not self.main_window.directories:
            messagebox.showwarning("警告", "请先添加要扫描的目录！")
            return

        if self.main_window.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中！")
            return

        self.main_window.is_scanning = True
        self.main_window.stop_flag.clear()
        self.hidden_groups.clear()  # 清空隐藏组

        # 更新UI状态
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 清空结果
        self.current_groups = []
        self.results_window = None  # 关闭结果窗口（如果存在）

        # 在新线程中执行
        thread = threading.Thread(
            target=self._run_scan,
            daemon=True
        )
        thread.start()

    def _run_scan(self):
        """执行相似度检测（后台线程）"""
        try:
            from core.visual_similarity import ImageSimilarityFinder

            # 获取配置
            directories = self.main_window.directories
            db_path = self.db_path_var.get()
            threshold = self.threshold_var.get()
            mode = self.mode_var.get()
            incremental = self.incremental_var.get()

            self._log(f"开始相似度检测...")
            self._log(f"目录数: {len(directories)}, 阈值: {threshold}, 模式: {mode}")
            self._log(f"扫描方式: {'增量' if incremental else '全量'}")

            # 创建检测器
            finder = ImageSimilarityFinder(
                db_path=db_path,
                batch_size=1000,
                progress_callback=self._on_progress,
                log_callback=lambda msg, lvl="INFO": self._log(msg, lvl)
            )

            # 构建索引
            self._log("正在构建图片索引...")
            finder.build_index(directories, incremental=incremental)

            # 查找相似组
            self._log("正在查找相似图片组...")
            groups = finder.find_similar_groups(threshold_phash=threshold, mode=mode)

            self.current_groups = groups
            self._log(f"检测完成！找到 {len(groups)} 个相似组")

            # 显示结果
            self._display_results(groups)

        except Exception as e:
            self._log(f"检测失败: {e}", "ERROR")
            messagebox.showerror("错误", f"检测过程中发生错误:\n{e}")

        finally:
            self.main_window.is_scanning = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.update_progress(0, "就绪")

    def _on_progress(self, progress: float, message: str):
        """进度回调"""
        self.update_progress(progress, message)

    def _update_status(self, message: str):
        """更新状态标签（已废弃，使用update_progress）"""
        pass

    def _display_results(self, groups):
        """显示检测结果"""
        # 清空现有数据
        for item in self.tree.get_children(''):
            self.tree.delete(item)

    def _display_results(self, groups):
        """显示检测结果（存储结果，不显示在表格中）"""
        self.current_groups = groups
        
        if not groups:
            self._log("未找到相似图片组")
            return

        self._log(f"已存储 {len(groups)} 个相似组的结果")
        self._log(f"点击「结果」按钮查看详细列表")

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _get_file_size(self, path: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(path)
        except:
            return 0

    def _open_location(self, file_path):
        """打开文件位置（Windows）"""
        try:
            # 调试输出
            print(f"[DEBUG] Opening location for: {file_path}")
            
            if os.name == 'nt':  # Windows
                # 使用列表形式避免shell转义问题，正确处理中文路径和空格
                cmd = ['explorer', '/select,', file_path]
                print(f"[DEBUG] Executing command: {' '.join(cmd)}")
                subprocess.run(cmd, shell=False)
            else:  # Linux/Mac
                folder = os.path.dirname(file_path)
                subprocess.run(['xdg-open', folder])
        except Exception as e:
            print(f"[ERROR] Failed to open location: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"无法打开文件夹: {e}\n\n路径: {file_path}")

    def _stop_scan(self):
        """停止扫描"""
        self.main_window.stop_flag.set()
        self.main_window._log("正在停止检测...")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def _show_results_window(self):
        """显示结果窗口"""
        if not self.current_groups:
            messagebox.showinfo("提示", "还没有检测结果，请先执行检测！")
            return

        # 如果窗口已存在，则聚焦到该窗口
        if self.results_window and self.results_window.winfo_exists():
            self.results_window.lift()
            self.results_window.focus()
            return

        # 创建结果窗口
        self.results_window = tk.Toplevel(self.main_window.root)
        self.results_window.title("相似度检测结果")
        self.results_window.geometry("900x600")

        # 标题和摘要（与精确匹配保持一致）
        header_frame = ttk.Frame(self.results_window)
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(header_frame, text=f"找到 {len(self.current_groups)} 个相似组",
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)

        # 筛选区域（与精确匹配保持一致的布局）
        filter_frame = ttk.Frame(self.results_window)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        # 后缀筛选
        ttk.Label(filter_frame, text="后缀:").pack(side=tk.LEFT, padx=5)
        suffix_var = tk.StringVar()
        suffix_entry = ttk.Entry(filter_frame, textvariable=suffix_var, width=15)
        suffix_entry.pack(side=tk.LEFT, padx=5)

        # 大小范围筛选（单位下拉框在最后）
        ttk.Label(filter_frame, text="最小大小:").pack(side=tk.LEFT, padx=(15, 2))
        min_size_var = tk.StringVar()
        min_size_entry = ttk.Entry(filter_frame, textvariable=min_size_var, width=8)
        min_size_entry.pack(side=tk.LEFT, padx=2)

        ttk.Label(filter_frame, text="~").pack(side=tk.LEFT, padx=2)

        ttk.Label(filter_frame, text="最大大小:").pack(side=tk.LEFT, padx=2)
        max_size_var = tk.StringVar()
        max_size_entry = ttk.Entry(filter_frame, textvariable=max_size_var, width=8)
        max_size_entry.pack(side=tk.LEFT, padx=2)

        unit_var = tk.StringVar(value="KB")
        unit_combo = ttk.Combobox(filter_frame, textvariable=unit_var, values=["B", "KB", "MB", "GB"],
                                  width=5, state="readonly")
        unit_combo.pack(side=tk.LEFT, padx=2)

        ttk.Button(filter_frame, text="应用筛选", command=lambda: self._apply_filters(
            suffix_var.get(), min_size_var.get(), max_size_var.get(), unit_var.get()
        )).pack(side=tk.LEFT, padx=10)

        ttk.Button(filter_frame, text="清除筛选", command=self._clear_filters).pack(side=tk.LEFT, padx=5)

        # Treeview
        tree_frame = ttk.Frame(self.results_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.results_tree = ttk.Treeview(tree_frame, columns=('similarity', 'count', 'size', 'suffix', 'action'), show='tree headings')
        self.results_tree.heading('#0', text='组别')
        self.results_tree.heading('similarity', text='平均相似度')
        self.results_tree.heading('count', text='图片数量')
        self.results_tree.heading('size', text='总大小')
        self.results_tree.heading('suffix', text='后缀')
        self.results_tree.heading('action', text='操作')

        self.results_tree.column('#0', width=80)
        self.results_tree.column('similarity', width=100)
        self.results_tree.column('count', width=80)
        self.results_tree.column('size', width=100)
        self.results_tree.column('suffix', width=150)
        self.results_tree.column('action', width=60)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件（只绑定一次）
        self.results_tree.bind('<Double-Button-1>', self._on_double_click_group)
        self.results_tree.bind('<Button-3>', self._show_context_menu)
        self.results_tree.bind('<ButtonRelease-1>', self._on_click_actions_column)

        # 初始显示所有结果
        self._display_all_results()

    def _display_all_results(self):
        """显示所有结果"""
        # 清空现有数据
        for item in self.results_tree.get_children(''):
            self.results_tree.delete(item)

        # 插入数据
        for group in self.current_groups:
            if group['group_id'] in self.hidden_groups:
                continue

            group_id = f"组 #{group['group_id']}"
            similarity = f"{group['avg_similarity']:.1f}%"
            count = f"{group['file_count']} 张"
            total_size = self._format_size(sum(
                self._get_file_size(f['path']) for f in group['files']
            ))
            
            # 提取后缀
            suffixes = set()
            for f in group['files']:
                ext = os.path.splitext(f['path'])[1].lower()
                if ext:
                    suffixes.add(ext[1:])  # 去掉点
            
            suffix_str = ', '.join(sorted(suffixes)) if suffixes else ''

            self.results_tree.insert('', tk.END, text=group_id, values=(
                similarity, count, total_size, suffix_str, "隐藏"
            ), tags=(str(group['group_id']),))

    def _apply_filters(self, suffix: str, min_size: str, max_size: str, unit: str):
        """应用筛选条件"""
        # 清空现有数据
        for item in self.results_tree.get_children(''):
            self.results_tree.delete(item)

        # 转换大小为字节
        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        multiplier = multipliers.get(unit, 1)
        
        min_bytes = 0
        max_bytes = float('inf')
        
        try:
            if min_size:
                min_bytes = float(min_size) * multiplier
        except ValueError:
            pass
        
        try:
            if max_size:
                max_bytes = float(max_size) * multiplier
        except ValueError:
            pass

        # 插入符合条件的数据
        for group in self.current_groups:
            if group['group_id'] in self.hidden_groups:
                continue

            # 检查后缀
            if suffix:
                has_suffix = False
                for f in group['files']:
                    ext = os.path.splitext(f['path'])[1].lower()
                    if ext and ext[1:] == suffix.lower():
                        has_suffix = True
                        break
                if not has_suffix:
                    continue

            # 检查大小
            total_bytes = sum(self._get_file_size(f['path']) for f in group['files'])
            if total_bytes < min_bytes or total_bytes > max_bytes:
                continue

            group_id = f"组 #{group['group_id']}"
            similarity = f"{group['avg_similarity']:.1f}%"
            count = f"{group['file_count']} 张"
            total_size = self._format_size(total_bytes)
            
            # 提取后缀
            suffixes = set()
            for f in group['files']:
                ext = os.path.splitext(f['path'])[1].lower()
                if ext:
                    suffixes.add(ext[1:])
            
            suffix_str = ', '.join(sorted(suffixes)) if suffixes else ''

            self.results_tree.insert('', tk.END, text=group_id, values=(
                similarity, count, total_size, suffix_str, "隐藏"
            ), tags=(str(group['group_id']),))

    def _clear_filters(self):
        """清除筛选条件"""
        self._display_all_results()

    def _on_click_actions_column(self, event):
        """只在点击操作列时触发隐藏"""
        # 调试输出
        print(f"[DEBUG] Click event: x={event.x}, y={event.y}")
        
        # 检测点击的列
        column = self.results_tree.identify_column(event.x)
        print(f"[DEBUG] Clicked column: {column}")
        
        if column == '#5':  # 只有操作列（第5列，索引从#0开始）才触发
            item = self.results_tree.identify_row(event.y)
            print(f"[DEBUG] Clicked item: {item}")
            if item:
                item_text = self.results_tree.item(item, 'text')
                print(f"[DEBUG] Item text: {item_text}")
                try:
                    # 从 "组 #14" 中提取数字 14
                    group_num_str = item_text.split()[1].replace('#', '')
                    group_num = int(group_num_str)
                    print(f"[DEBUG] Hiding group #{group_num}")
                    self._hide_group_by_num(group_num)
                except Exception as e:
                    print(f"[DEBUG] Error: {e}")
                    import traceback
                    traceback.print_exc()

    def _hide_group_by_num(self, group_num):
        """根据组号隐藏指定的组"""
        self.hidden_groups.add(group_num)
        
        # 从Treeview中删除该行
        for item in self.results_tree.get_children(''):
            item_text = self.results_tree.item(item, 'text')
            try:
                # 从 "组 #14" 中提取数字 14
                item_group_num = int(item_text.split()[1].replace('#', ''))
                if item_group_num == group_num:
                    self.results_tree.delete(item)
                    break
            except:
                pass
        
        self.main_window._log(f"已隐藏组 #{group_num}")

    def _on_double_click_group(self, event):
        """双击组别事件处理"""
        print(f"[DEBUG] Double-click event triggered")
        
        selection = self.results_tree.selection()
        print(f"[DEBUG] Selection: {selection}")
        
        if not selection:
            return

        item_text = self.results_tree.item(selection[0], 'text')
        print(f"[DEBUG] Double-clicked item text: {item_text}")
        
        try:
            # 从 "组 #14" 中提取数字 14
            group_num_str = item_text.split()[1].replace('#', '')
            group_num = int(group_num_str)
            print(f"[DEBUG] Showing details for group #{group_num}")
            self._show_group_details(group_num)
        except Exception as e:
            print(f"[DEBUG] Error in double-click: {e}")
            import traceback
            traceback.print_exc()
        except:
            pass

    def _hide_group(self, item_id):
        """隐藏指定的组（通过item ID）"""
        item_text = self.results_tree.item(item_id, 'text')
        try:
            # 从 "组 #14" 中提取数字 14
            group_num_str = item_text.split()[1].replace('#', '')
            group_num = int(group_num_str)
            self._hide_group_by_num(group_num)
        except:
            pass

    def _show_group_details(self, group_num):
        """显示组详情（与精确匹配保持一致）"""
        if not self.current_groups:
            return

        group = None
        for g in self.current_groups:
            if g['group_id'] == group_num:
                group = g
                break

        if not group:
            return

        # 创建详情窗口（与精确匹配一致的样式）
        detail_window = tk.Toplevel(self.results_window)
        detail_window.title(f"相似组 #{group_num} 详情")
        detail_window.geometry("900x600")

        # 标题区域（与精确匹配一致）
        title_frame = ttk.Frame(detail_window)
        title_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(title_frame, text=f"平均相似度: {group['avg_similarity']:.1f}%",
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        
        ttk.Label(title_frame, text=f"  |  共 {len(group['files'])} 个相似图片",
                 font=("微软雅黑", 10), foreground="gray").pack(side=tk.LEFT)

        # 文件列表（与精确匹配一致）
        list_frame = ttk.LabelFrame(detail_window, text="文件列表（双击路径打开文件夹）", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview for files
        file_tree = ttk.Treeview(
            list_frame,
            columns=('resolution', 'size', 'path'),
            show='tree headings'
        )
        file_tree.heading('#0', text='#')
        file_tree.heading('resolution', text='分辨率', command=lambda: self._sort_file_tree(file_tree, 'resolution'))
        file_tree.heading('size', text='大小', command=lambda: self._sort_file_tree(file_tree, 'size'))
        file_tree.heading('path', text='完整路径', command=lambda: self._sort_file_tree(file_tree, 'path'))

        file_tree.column('#0', width=40)
        file_tree.column('resolution', width=100)
        file_tree.column('size', width=100)
        file_tree.column('path', width=650)  # 增加宽度以显示完整路径

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=file_tree.yview)
        file_tree.configure(yscrollcommand=scrollbar.set)

        file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入文件数据
        for idx, file_info in enumerate(group['files'], start=1):
            resolution = f"{file_info['width']}x{file_info['height']}"
            size = self._format_size(self._get_file_size(file_info['path']))
            path = file_info['path']
            
            file_tree.insert('', tk.END, text=str(idx), values=(resolution, size, path))

        # 绑定双击事件（双击路径打开文件夹）
        file_tree.bind('<Double-Button-1>', lambda e: self._open_file_from_detail(file_tree))

        # 按钮区域
        btn_frame = ttk.Frame(detail_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="打开选中文件的文件夹",
                  command=lambda: self._open_selected_location(file_tree)).pack(side=tk.LEFT, padx=5)

    def _sort_file_tree(self, tree, column):
        """排序文件树（与精确匹配一致）"""
        items = [(tree.set(k, column), k) for k in tree.get_children('')]
        
        # 根据列类型选择排序方式
        if column == 'size':
            # 文件大小列：转换为字节后排序
            try:
                items.sort(key=lambda x: self._parse_size_to_bytes(x[0]))
            except:
                items.sort(key=lambda x: x[0])
        elif column == 'resolution':
            # 分辨率列：按宽度排序
            try:
                items.sort(key=lambda x: int(x[0].split('x')[0]))
            except:
                items.sort(key=lambda x: x[0])
        else:
            # 其他列：字符串排序
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

    def _parse_size_to_bytes(self, size_str: str) -> int:
        """将格式化的大小字符串转换为字节数（与精确匹配一致）"""
        import re
        match = re.match(r'([\d,.]+)\s*([KMGT]?B)', size_str)
        if match:
            number_str, unit = match.groups()
            number = float(number_str.replace(',', ''))
            multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
            return number * multipliers.get(unit, 1)
        return 0

    def _open_file_from_detail(self, tree):
        """从详情窗口打开文件位置"""
        selection = tree.selection()
        if not selection:
            return

        values = tree.item(selection[0], 'values')
        if len(values) >= 3:
            # 从Treeview获取的路径可能包含反斜杠转义问题，需要正确处理
            file_path = values[2].replace('\\', '\\\\')  # 转义反斜杠
            # 但实际路径应该保持原样，所以直接使用原始值
            file_path = values[2]
            
            # 调试输出
            print(f"[DEBUG] Opening file from detail: {file_path}")
            print(f"[DEBUG] File exists: {os.path.exists(file_path)}")
            
            self._open_location(file_path)

    def _open_selected_location(self, tree):
        """打开选中的文件位置"""
        selection = tree.selection()
        if not selection:
            return

        values = tree.item(selection[0], 'values')
        if len(values) >= 3:
            file_path = values[2]
            self._open_location(file_path)

    def _show_context_menu(self, event):
        """显示右键菜单"""
        selection = self.results_tree.identify_row(event.y)
        if not selection:
            return

        self.results_tree.selection_set(selection)

        menu = tk.Menu(self.results_tree, tearoff=0)
        menu.add_command(label="查看详情", command=lambda: self._on_double_click_group(None))
        menu.add_command(label="打开文件夹", command=lambda: self._open_file_from_result_tree(self.results_tree))
        menu.add_separator()
        menu.add_command(label="隐藏此组", command=lambda: self._hide_group(selection))
        menu.add_command(label="显示所有隐藏的组", command=self._show_all_groups)

        menu.post(event.x_root, event.y_root)

    def _open_file_from_result_tree(self, tree):
        """从结果树打开文件位置"""
        selection = tree.selection()
        if not selection:
            return

        item_text = tree.item(selection[0], 'text')
        try:
            # 从 "组 #14" 中提取数字 14
            group_num_str = item_text.split()[1].replace('#', '')
            group_num = int(group_num_str)
            # 找到对应的组
            for group in self.current_groups:
                if group['group_id'] == group_num:
                    if group['files']:
                        # 打开第一个文件
                        self._open_location(group['files'][0]['path'])
                    break
        except:
            pass

    def _hide_group(self, item_id):
        """隐藏指定的组"""
        item_text = self.results_tree.item(item_id, 'text')
        try:
            # 从 "组 #14" 中提取数字 14
            group_num_str = item_text.split()[1].replace('#', '')
            group_num = int(group_num_str)
            self.hidden_groups.add(group_num)
            self.results_tree.delete(item_id)
            self.main_window._log(f"已隐藏组 #{group_num}")
        except:
            pass

    def _show_all_groups(self):
        """显示所有隐藏的组"""
        if not self.hidden_groups:
            return

        self.hidden_groups.clear()
        self._display_all_results()
        self.main_window._log("已显示所有隐藏的组")
