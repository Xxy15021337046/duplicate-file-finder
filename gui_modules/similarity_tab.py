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
            text="查看统计",
            command=self._view_statistics
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

        # 结果展示区域
        results_frame = ttk.LabelFrame(self.frame, text="相似图片组（双击查看详情）", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview
        self.tree = ttk.Treeview(results_frame, columns=('similarity', 'count', 'size'), show='tree headings')
        self.tree.heading('#0', text='组别', command=lambda: self._sort_tree('#0'))
        self.tree.heading('similarity', text='平均相似度', command=lambda: self._sort_tree('similarity'))
        self.tree.heading('count', text='图片数量', command=lambda: self._sort_tree('count'))
        self.tree.heading('size', text='总大小', command=lambda: self._sort_tree('size'))

        self.tree.column('#0', width=80)
        self.tree.column('similarity', width=100)
        self.tree.column('count', width=80)
        self.tree.column('size', width=100)

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件
        self.tree.bind('<Double-Button-1>', self._on_double_click)
        self.tree.bind('<Button-3>', self._show_context_menu)

        # 日志区域
        log_frame = ttk.LabelFrame(self.frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=8,
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
        for item in self.tree.get_children(''):
            self.tree.delete(item)
        self.current_groups = []

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

        if not groups:
            self._log("未找到相似图片组")
            return

        # 插入数据
        for group in groups:
            if group['group_id'] in self.hidden_groups:
                continue

            group_id = f"组 #{group['group_id']}"
            similarity = f"{group['avg_similarity']:.1f}%"
            count = f"{group['file_count']} 张"
            total_size = self._format_size(sum(
                self._get_file_size(f['path']) for f in group['files']
            ))

            self.tree.insert('', tk.END, text=group_id, values=(
                similarity, count, total_size
            ))

        self._log(f"已显示 {len(groups)} 个相似组")

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

    def _sort_tree(self, column):
        """排序Treeview"""
        items = [(self.tree.set(k, column), k) for k in self.tree.get_children('')]

        # 判断是否为数字列
        try:
            float(items[0][0].replace('%', '').replace('张', '').replace('MB', '').replace('KB', ''))
            numeric = True
        except:
            numeric = False

        if numeric:
            items.sort(key=lambda x: float(x[0].replace('%', '').replace('张', '').replace('MB', '').replace('KB', '')))
        else:
            items.sort(key=lambda x: x[0])

        # 反转顺序
        items.reverse()

        for index, (val, k) in enumerate(items):
            self.tree.move(k, '', index)

    def _on_double_click(self, event):
        """双击事件处理"""
        selection = self.tree.selection()
        if not selection:
            return

        item_text = self.tree.item(selection[0], 'text')
        try:
            group_num = int(item_text.split()[1])
            self._show_group_details(group_num)
        except:
            pass

    def _show_group_details(self, group_num):
        """显示组详情"""
        if not self.current_groups:
            return

        group = None
        for g in self.current_groups:
            if g['group_id'] == group_num:
                group = g
                break

        if not group:
            return

        detail_window = tk.Toplevel(self.main_window.root)
        detail_window.title(f"相似组 #{group_num} 详情")
        detail_window.geometry("700x500")

        # 标题
        ttk.Label(detail_window, text=f"组 #{group_num} - 相似度: {group['avg_similarity']:.1f}%",
                 font=("微软雅黑", 12, "bold")).pack(pady=10)

        # 文件列表
        list_frame = ttk.Frame(detail_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tree = ttk.Treeview(list_frame, columns=('resolution', 'size', 'path'), show='headings')
        tree.heading('resolution', text='分辨率')
        tree.heading('size', text='文件大小')
        tree.heading('path', text='文件路径')

        tree.column('resolution', width=100)
        tree.column('size', width=100)
        tree.column('path', width=400)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        for file_info in group['files']:
            resolution = f"{file_info['width']}x{file_info['height']}"
            size = self._format_size(self._get_file_size(file_info['path']))
            tree.insert('', tk.END, values=(resolution, size, file_info['path']))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击跳转
        tree.bind('<Double-Button-1>', lambda e: self._open_file_location(tree))

        # 按钮
        btn_frame = ttk.Frame(detail_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="打开文件夹",
                  command=lambda: self._open_selected_location(tree)).pack(side=tk.LEFT, padx=5)

    def _open_file_location(self, tree):
        """打开文件所在文件夹并选中"""
        selection = tree.selection()
        if not selection:
            return

        values = tree.item(selection[0], 'values')
        if len(values) >= 3:
            file_path = values[2]
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

    def _open_location(self, file_path):
        """打开文件位置（Windows）"""
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(f'explorer /select,"{file_path}"', shell=True)
            else:  # Linux/Mac
                folder = os.path.dirname(file_path)
                subprocess.run(['xdg-open', folder])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")

    def _show_context_menu(self, event):
        """显示右键菜单"""
        selection = self.tree.identify_row(event.y)
        if not selection:
            return

        self.tree.selection_set(selection)

        menu = tk.Menu(self.tree, tearoff=0)
        menu.add_command(label="查看详情", command=lambda: self._on_double_click(None))
        menu.add_command(label="打开文件夹", command=lambda: self._open_file_location(self.tree))
        menu.add_separator()
        menu.add_command(label="隐藏此组", command=lambda: self._hide_group(selection))
        menu.add_command(label="显示所有隐藏的组", command=self._show_all_groups)

        menu.post(event.x_root, event.y_root)

    def _hide_group(self, item_id):
        """隐藏指定的组"""
        item_text = self.tree.item(item_id, 'text')
        try:
            group_num = int(item_text.split()[1])
            self.hidden_groups.add(group_num)
            self.tree.delete(item_id)
            self.main_window._log(f"已隐藏组 #{group_num}")
        except:
            pass

    def _show_all_groups(self):
        """显示所有隐藏的组"""
        if not self.hidden_groups:
            return

        self.hidden_groups.clear()
        self._display_results(self.current_groups)
        self.main_window._log("已显示所有隐藏的组")

    def _stop_scan(self):
        """停止扫描"""
        self.main_window.stop_flag.set()
        self.main_window._log("正在停止检测...")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def _view_statistics(self):
        """查看统计信息"""
        db_path = self.db_path_var.get()
        if not os.path.exists(db_path):
            messagebox.showwarning("警告", "数据库文件不存在！")
            return

        try:
            from core.visual_similarity import ImageSimilarityFinder
            finder = ImageSimilarityFinder(db_path=db_path)
            stats = finder.get_statistics()

            stats_window = tk.Toplevel(self.main_window.root)
            stats_window.title("数据库统计")
            stats_window.geometry("400x300")

            ttk.Label(stats_window, text="图片索引统计", font=("微软雅黑", 12, "bold")).pack(pady=10)

            info_frame = ttk.Frame(stats_window)
            info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

            stats_text = f"""
总图片数: {stats['total_images']:,}
总文件大小: {stats['total_size_formatted']}
不同分辨率数: {stats['unique_resolutions']}
数据库路径: {db_path}
            """.strip()

            ttk.Label(info_frame, text=stats_text, font=("微软雅黑", 10),
                     justify=tk.LEFT).pack(anchor=tk.W)

        except Exception as e:
            messagebox.showerror("错误", f"获取统计信息失败: {e}")
