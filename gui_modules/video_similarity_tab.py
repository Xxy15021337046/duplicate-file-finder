#!/usr/bin/env python3
"""
视频相似度检测标签页模块
负责视频相似度检测的配置、执行和结果显示
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import subprocess
from datetime import datetime


class VideoSimilarityTab:
    """视频相似度检测标签页"""

    def __init__(self, parent_notebook, main_window):
        self.parent_notebook = parent_notebook
        self.main_window = main_window
        self.frame = ttk.Frame(parent_notebook)

        # 变量
        self.threshold_var = tk.IntVar(value=12)
        self.db_path_var = tk.StringVar(value="video_similarity.db")

        # 视频格式过滤
        self.format_all = tk.BooleanVar(value=True)
        self.format_mp4 = tk.BooleanVar(value=True)
        self.format_avi = tk.BooleanVar(value=True)
        self.format_mkv = tk.BooleanVar(value=True)
        self.format_mov = tk.BooleanVar(value=True)
        self.format_wmv = tk.BooleanVar(value=True)
        self.format_flv = tk.BooleanVar(value=True)
        self.format_webm = tk.BooleanVar(value=True)
        
        # 自定义格式输入
        self.custom_format_var = tk.StringVar(value="")

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

        # 第二行：扫描方式
        scan_row = ttk.Frame(config_frame)
        scan_row.pack(fill=tk.X, pady=2)

        ttk.Label(scan_row, text="扫描方式:", width=12).pack(side=tk.LEFT)

        self.incremental_var = tk.BooleanVar(value=False)
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

        # 第三行：数据库路径
        db_row = ttk.Frame(config_frame)
        db_row.pack(fill=tk.X, pady=2)

        ttk.Label(db_row, text="数据库:", width=12).pack(side=tk.LEFT)
        ttk.Entry(db_row, textvariable=self.db_path_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(db_row, text="浏览...", command=self._browse_db).pack(side=tk.LEFT)

        # 视频格式过滤
        format_frame = ttk.LabelFrame(self.frame, text="视频格式", padding="10")
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        # 第一行：全选 + 常用格式
        format_row1 = ttk.Frame(format_frame)
        format_row1.pack(fill=tk.X, pady=2)

        ttk.Checkbutton(format_row1, text="全部", variable=self.format_all,
                       command=self._on_format_all_changed).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(format_row1, text="MP4", variable=self.format_mp4,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="AVI", variable=self.format_avi,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="MKV", variable=self.format_mkv,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="MOV", variable=self.format_mov,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="WMV", variable=self.format_wmv,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="FLV", variable=self.format_flv,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="WebM", variable=self.format_webm,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)

        # 第二行：自定义后缀输入
        format_row2 = ttk.Frame(format_frame)
        format_row2.pack(fill=tk.X, pady=5)

        ttk.Label(format_row2, text="自定义后缀:", width=12).pack(side=tk.LEFT)
        custom_entry = ttk.Entry(format_row2, textvariable=self.custom_format_var, width=50)
        custom_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            format_row2, 
            text="(多个用逗号、分号或空格分隔，如: mp4,avi,mkv)",
            foreground="gray",
            font=("微软雅黑", 8)
        ).pack(side=tk.LEFT)

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
        """全选复选框变化时的处理"""
        if self.format_all.get():
            # 选中所有格式
            self.format_mp4.set(True)
            self.format_avi.set(True)
            self.format_mkv.set(True)
            self.format_mov.set(True)
            self.format_wmv.set(True)
            self.format_flv.set(True)
            self.format_webm.set(True)
            self.custom_format_var.set("")  # 清空自定义输入

    def _on_format_item_changed(self):
        """单个格式复选框变化时的处理"""
        # 检查是否所有格式都被选中
        all_checked = all([
            self.format_mp4.get(),
            self.format_avi.get(),
            self.format_mkv.get(),
            self.format_mov.get(),
            self.format_wmv.get(),
            self.format_flv.get(),
            self.format_webm.get()
        ])
        
        # 更新"全部"复选框状态
        self.format_all.set(all_checked)
        
        # 如果手动取消某个格式，清空自定义输入
        if not all_checked:
            self.custom_format_var.set("")

    def _get_supported_formats(self) -> set:
        """获取支持的视频格式"""
        formats = set()

        # 如果选择"全部"，返回所有支持的格式
        if self.format_all.get():
            return {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
                    '.mpeg', '.mpg', '.3gp', '.m4v', '.rmvb', '.rm', '.ts', '.mts'}

        # 根据选中的复选框添加格式
        if self.format_mp4.get():
            formats.add('.mp4')
        if self.format_avi.get():
            formats.add('.avi')
        if self.format_mkv.get():
            formats.add('.mkv')
        if self.format_mov.get():
            formats.add('.mov')
        if self.format_wmv.get():
            formats.add('.wmv')
        if self.format_flv.get():
            formats.add('.flv')
        if self.format_webm.get():
            formats.add('.webm')

        # 处理自定义后缀输入
        custom_input = self.custom_format_var.get().strip()
        if custom_input:
            # 支持逗号、分号、空格分隔
            import re
            custom_list = re.split(r'[,;\s]+', custom_input)
            for ext in custom_list:
                ext = ext.strip().lower()
                if ext and not ext.startswith('.'):
                    ext = '.' + ext
                if ext:
                    formats.add(ext)

        return formats

    def _browse_db(self):
        """浏览数据库文件"""
        filename = filedialog.asksaveasfilename(
            title="选择数据库文件",
            defaultextension=".db",
            filetypes=[("数据库文件", "*.db"), ("所有文件", "*.*")]
        )
        if filename:
            self.db_path_var.set(filename)

    def start_scan(self):
        """启动视频相似度检测"""
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
        """执行视频相似度检测（后台线程）"""
        try:
            from core.video_similarity import VideoSimilarityFinder

            # 获取配置
            directories = self.main_window.directories
            db_path = self.db_path_var.get()
            threshold = self.threshold_var.get()
            incremental = self.incremental_var.get()
            
            # 获取支持的视频格式
            supported_formats = self._get_supported_formats()

            self._log(f"开始视频相似度检测...")
            self._log(f"目录数: {len(directories)}, 阈值: {threshold}")
            self._log(f"扫描方式: {'增量' if incremental else '全量'}")
            self._log(f"视频格式: {', '.join(sorted(supported_formats))}")

            # 创建检测器
            finder = VideoSimilarityFinder(
                db_path=db_path,
                batch_size=100,
                progress_callback=self._on_progress,
                log_callback=lambda msg, lvl="INFO": self._log(msg, lvl)
            )
            
            # 设置自定义格式
            finder.SUPPORTED_FORMATS = supported_formats

            # 构建索引
            self._log("正在提取视频关键帧...")
            finder.build_index(directories, incremental=incremental)

            # 查找相似组
            self._log("正在查找相似视频组...")
            groups = finder.find_similar_groups(threshold_phash=threshold)

            self.current_groups = groups
            self._log(f"检测完成！找到 {len(groups)} 个相似组")

            # 显示结果
            self._display_results(groups)

        except Exception as e:
            self._log(f"检测失败: {e}", "ERROR")
            import traceback
            print(traceback.format_exc())
            messagebox.showerror("错误", f"检测过程中发生错误:\n{e}")

        finally:
            self.main_window.is_scanning = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.update_progress(0, "就绪")

    def _on_progress(self, progress: float, message: str):
        """进度回调"""
        self.update_progress(progress, message)

    def _display_results(self, groups):
        """显示检测结果（存储结果，不显示在表格中）"""
        self.current_groups = groups
        
        if not groups:
            self._log("未找到相似视频组")
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

    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds == 0:
            return "未知"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _on_video_select_multiframe(self, tree, main_preview_label, thumbs_frame, 
                                    thumbnail_cache, max_cached_videos, max_frames):
        """当用户选中Treeview中的某一行时，显示视频预览（支持多帧）"""
        selection = tree.selection()
        if not selection:
            return
        
        values = tree.item(selection[0], 'values')
        if len(values) >= 5:
            file_path = values[4]
            
            # 检查缓存
            if file_path in thumbnail_cache:
                self._display_multiframe_preview(
                    file_path, main_preview_label, thumbs_frame, thumbnail_cache[file_path]
                )
                return
            
            # 异步加载多帧缩略图
            threading.Thread(
                target=self._load_multiframe_thumbnails_async,
                args=(file_path, main_preview_label, thumbs_frame, 
                      thumbnail_cache, max_cached_videos, max_frames),
                daemon=True
            ).start()

    def _display_multiframe_preview(self, file_path, main_preview_label, thumbs_frame, cache_data):
        """显示多帧预览（从缓存）"""
        frames = cache_data['frames']  # 现在是原始numpy数组
        thumbnails = cache_data['thumbnails']  # 缩略图PhotoImage
        timestamps = cache_data['timestamps']
        
        # 清空当前缩略图
        for widget in thumbs_frame.winfo_children():
            widget.destroy()
        
        # 显示主预览（第一帧，实时缩放到正确尺寸）
        self._set_main_preview_image(main_preview_label, frames[0])
        
        # 如果有多个帧，创建缩略图列表
        if len(thumbnails) > 1:
            label = ttk.Label(thumbs_frame, text=f"共{len(thumbnails)}帧预览:", 
                            font=("微软雅黑", 8), foreground="gray")
            label.pack(anchor='w', pady=(5, 2))
            
            # 创建缩略图网格
            thumb_frame = ttk.Frame(thumbs_frame)
            thumb_frame.pack(fill=tk.X)
            
            for i, (thumb, ts) in enumerate(zip(thumbnails[1:], timestamps[1:]), start=1):
                # 创建可点击的缩略图按钮
                btn = ttk.Button(
                    thumb_frame, 
                    image=thumb,
                    command=lambda f=frames[i]: self._set_main_preview_image(main_preview_label, f)
                )
                btn.grid(row=0, column=i-1, padx=2, pady=2)
                
                # 添加时间标签
                time_label = ttk.Label(
                    thumb_frame, 
                    text=self._format_duration(ts),
                    font=("微软雅黑", 7),
                    foreground="gray"
                )
                time_label.grid(row=1, column=i-1, padx=2)

    def _set_main_preview_image(self, label, frame_array):
        """设置主预览图（将numpy数组缩放到正确尺寸并显示）"""
        try:
            import cv2
            from PIL import Image, ImageTk
            
            # 转换为PIL Image
            rgb_frame = cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            
            # 固定宽度310px，高度自适应
            target_width = 310
            aspect_ratio = pil_img.width / pil_img.height
            target_height = int(target_width / aspect_ratio)
            
            # 限制最大高度
            if target_height > 400:
                target_height = 400
                target_width = int(target_height * aspect_ratio)
            
            pil_img = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)
            
            # 更新标签
            label.config(image=photo, text="")
            label.image = photo  # 保持引用防止垃圾回收
            
        except Exception as e:
            print(f"[ERROR] Failed to set main preview: {e}")
            label.config(text="显示失败", foreground="red")

    def _load_multiframe_thumbnails_async(self, file_path, main_preview_label, thumbs_frame,
                                         thumbnail_cache, max_cached_videos, max_frames):
        """异步加载视频多帧缩略图（不生成实际文件）"""
        try:
            import cv2
            from PIL import Image, ImageTk
            
            # 打开视频文件
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                self.main_window.root.after(0, lambda: main_preview_label.config(
                    text="无法打开视频", foreground="red"
                ))
                return
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            # 根据视频时长决定提取多少帧
            if duration <= 60:
                # 短视频：只提取1帧（开头）
                num_frames = 1
                frame_indices = [0]
            elif duration <= 300:
                # 中等长度视频：提取3帧（开头、中间、结尾前）
                num_frames = min(3, max_frames)
                frame_indices = [
                    0,
                    total_frames // 2,
                    int(total_frames * 0.9)
                ]
            else:
                # 长视频：提取5帧（均匀分布）
                num_frames = min(5, max_frames)
                step = total_frames // (num_frames - 1) if num_frames > 1 else 1
                frame_indices = [i * step for i in range(num_frames)]
                # 确保最后一帧不是真正的最后一帧（可能是片尾字幕）
                frame_indices[-1] = int(total_frames * 0.95)
            
            # 提取指定帧（保存原始numpy数组用于主预览，同时生成缩略图）
            frames_data = []  # 原始帧数组（numpy）
            thumbnails = []   # 缩略图（PhotoImage）
            timestamps = []
            
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                # 保存原始帧（用于主预览）
                frames_data.append(frame.copy())
                
                # 计算时间戳
                timestamp = idx / fps if fps > 0 else 0
                timestamps.append(timestamp)
                
                # 生成缩略图（仅用于列表显示）
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                max_size = (80, 60)
                pil_img.thumbnail(max_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(pil_img)
                thumbnails.append(photo)
            
            cap.release()
            
            if not frames_data:
                self.main_window.root.after(0, lambda: main_preview_label.config(
                    text="无法读取视频帧", foreground="red"
                ))
                return
            
            # 更新缓存（LRU策略）
            if len(thumbnail_cache) >= max_cached_videos:
                # 删除最旧的项
                thumbnail_cache.pop(next(iter(thumbnail_cache)))
            
            thumbnail_cache[file_path] = {
                'frames': frames_data,      # 原始帧数组（numpy ndarray）
                'thumbnails': thumbnails,   # 缩略图（PhotoImage）
                'timestamps': timestamps    # 时间戳列表
            }
            
            # 更新UI（在主线程中执行）
            self.main_window.root.after(0, lambda: self._display_multiframe_preview(
                file_path, main_preview_label, thumbs_frame, thumbnail_cache[file_path]
            ))
            
        except Exception as e:
            print(f"[ERROR] Failed to load video thumbnails: {e}")
            import traceback
            traceback.print_exc()
            self.main_window.root.after(0, lambda: main_preview_label.config(
                text=f"加载失败: {str(e)[:30]}", foreground="red"
            ))

    def _get_file_size(self, path: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(path)
        except:
            return 0

    def _open_location(self, file_path):
        """打开文件位置（Windows）"""
        try:
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
        # 如果当前没有结果，但数据库中有数据，尝试从数据库加载并重新检测
        if not self.current_groups:
            db_path = self.db_path_var.get()
            if os.path.exists(db_path):
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    cursor = conn.execute("SELECT COUNT(*) FROM video_index")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        # 数据库中有视频数据，从路径中提取目录并重新检测
                        cursor = conn.execute("SELECT DISTINCT path FROM video_index")
                        paths = [row[0] for row in cursor.fetchall()]
                        conn.close()
                        
                        # 从路径中提取唯一的根目录（取每个路径的父目录）
                        directories = set()
                        for path in paths:
                            # 向上查找直到找到存在的目录
                            parent = os.path.dirname(path)
                            while parent and not os.path.exists(parent):
                                parent = os.path.dirname(parent)
                            if parent and os.path.exists(parent):
                                directories.add(parent)
                        
                        if directories:
                            # 临时设置目录列表
                            temp_directories = list(directories)
                            self._log(f"检测到历史数据 ({count} 个视频)，从 {len(temp_directories)} 个目录重新检测...")
                            
                            # 直接执行检测，不经过start_scan的检查
                            thread = threading.Thread(
                                target=self._run_scan_with_directories,
                                args=(temp_directories,),
                                daemon=True
                            )
                            thread.start()
                            return
                    
                    conn.close()
                except Exception as e:
                    import traceback
                    print(f"[ERROR] 加载历史数据失败: {e}")
                    print(traceback.format_exc())
                    pass  # 静默失败，继续显示空结果窗口

        # 如果窗口已存在，则聚焦到该窗口
        if self.results_window and self.results_window.winfo_exists():
            self.results_window.lift()
            self.results_window.focus()
            return

        # 创建结果窗口
        self.results_window = tk.Toplevel(self.main_window.root)
        self.results_window.title("视频相似度检测结果")
        self.results_window.geometry("1000x600")

        # 标题和摘要
        header_frame = ttk.Frame(self.results_window)
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(header_frame, text=f"找到 {len(self.current_groups)} 个相似组",
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)

        # Treeview
        tree_frame = ttk.Frame(self.results_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.results_tree = ttk.Treeview(tree_frame, columns=('similarity', 'count', 'duration', 'size', 'action'), show='tree headings')
        self.results_tree.heading('#0', text='组别')
        self.results_tree.heading('similarity', text='平均相似度', command=lambda: self._sort_results_tree('similarity'))
        self.results_tree.heading('count', text='视频数量', command=lambda: self._sort_results_tree('count'))
        self.results_tree.heading('duration', text='总时长', command=lambda: self._sort_results_tree('duration'))
        self.results_tree.heading('size', text='总大小', command=lambda: self._sort_results_tree('size'))
        self.results_tree.heading('action', text='操作')

        self.results_tree.column('#0', width=80)
        self.results_tree.column('similarity', width=100)
        self.results_tree.column('count', width=80)
        self.results_tree.column('duration', width=120)
        self.results_tree.column('size', width=100)
        self.results_tree.column('action', width=60)
        
        # 记录排序状态
        self._results_sort_reverse = False
        self._results_last_sort_column = None

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

    def _run_scan_with_directories(self, directories):
        """使用指定的目录列表执行扫描（不检查main_window.directories）"""
        try:
            from core.video_similarity import VideoSimilarityFinder

            # 获取配置
            db_path = self.db_path_var.get()
            threshold = self.threshold_var.get()

            self._log(f"开始视频相似度检测...")
            self._log(f"目录数: {len(directories)}, 阈值: {threshold}")

            # 更新UI状态
            self.main_window.root.after(0, lambda: self.start_btn.config(state=tk.DISABLED))
            self.main_window.root.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
            self.main_window.is_scanning = True
            self.main_window.stop_flag.clear()

            # 创建检测器
            finder = VideoSimilarityFinder(
                db_path=db_path,
                batch_size=100,
                progress_callback=self._on_progress,
                log_callback=lambda msg, lvl="INFO": self._log(msg, lvl)
            )

            # 构建索引（增量模式，保留已有数据）
            self._log("正在加载视频索引...")
            finder.build_index(directories, incremental=True)

            # 查找相似组
            self._log("正在查找相似视频组...")
            groups = finder.find_similar_groups(threshold_phash=threshold)

            self.current_groups = groups
            self._log(f"检测完成！找到 {len(groups)} 个相似组")

            # 显示结果
            self._display_results(groups)

        except Exception as e:
            self._log(f"检测失败: {e}", "ERROR")
            import traceback
            print(traceback.format_exc())

        finally:
            self.main_window.is_scanning = False
            self.main_window.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.main_window.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self.update_progress(0, "就绪")

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
            count = f"{group['file_count']} 个"
            
            # 计算总时长
            total_duration = sum(f['duration'] for f in group['files'])
            duration_str = self._format_duration(total_duration)
            
            total_size = self._format_size(sum(
                self._get_file_size(f['path']) for f in group['files']
            ))

            self.results_tree.insert('', tk.END, text=group_id, values=(
                similarity, count, duration_str, total_size, "隐藏"
            ), tags=(str(group['group_id']),))

    def _sort_results_tree(self, column):
        """排序结果树"""
        items = [(self.results_tree.set(k, column), k) for k in self.results_tree.get_children('')]
        
        # 根据列类型选择排序方式
        if column == 'similarity':
            # 相似度列：转换为浮点数后排序（去掉%符号）
            try:
                items.sort(key=lambda x: float(x[0].replace('%', '')))
            except:
                items.sort(key=lambda x: x[0])
        elif column == 'count':
            # 数量列：提取数字后排序（去掉"个"字）
            try:
                items.sort(key=lambda x: int(x[0].replace('个', '').strip()))
            except:
                items.sort(key=lambda x: x[0])
        elif column == 'duration':
            # 时长列：转换为秒后排序
            try:
                items.sort(key=lambda x: self._parse_duration_to_seconds(x[0]))
            except:
                items.sort(key=lambda x: x[0])
        elif column == 'size':
            # 大小列：转换为字节后排序
            try:
                items.sort(key=lambda x: self._parse_size_to_bytes(x[0]))
            except:
                items.sort(key=lambda x: x[0])
        else:
            # 其他列：字符串排序
            items.sort(key=lambda x: x[0])

        # 反转顺序（如果已经是升序则改为降序）
        if self._results_last_sort_column == column:
            self._results_sort_reverse = not self._results_sort_reverse
        else:
            self._results_sort_reverse = False
            self._results_last_sort_column = column
        
        if self._results_sort_reverse:
            items.reverse()

        # 重新排列
        for index, (val, k) in enumerate(items):
            self.results_tree.move(k, '', index)

    def _parse_duration_to_seconds(self, duration_str: str) -> float:
        """将格式化的时长字符串转换为秒数"""
        if duration_str == "未知":
            return 0
        
        total_seconds = 0
        parts = duration_str.split()
        
        for part in parts:
            if 'h' in part:
                total_seconds += int(part.replace('h', '')) * 3600
            elif 'm' in part:
                total_seconds += int(part.replace('m', '')) * 60
            elif 's' in part:
                total_seconds += int(part.replace('s', ''))
        
        return total_seconds

    def _parse_size_to_bytes(self, size_str: str) -> int:
        """将格式化的大小字符串转换为字节数"""
        import re
        match = re.match(r'([\d,.]+)\s*([KMGT]?B)', size_str)
        if match:
            number_str, unit = match.groups()
            number = float(number_str.replace(',', ''))
            multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
            return number * multipliers.get(unit, 1)
        return 0

    def _on_click_actions_column(self, event):
        """只在点击操作列时触发隐藏"""
        # 检测点击的列
        column = self.results_tree.identify_column(event.x)
        
        if column == '#5':  # 只有操作列（第5列，索引从#0开始）才触发
            item = self.results_tree.identify_row(event.y)
            if item:
                item_text = self.results_tree.item(item, 'text')
                try:
                    # 从 "组 #14" 中提取数字 14
                    group_num_str = item_text.split()[1].replace('#', '')
                    group_num = int(group_num_str)
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
        selection = self.results_tree.selection()
        
        if not selection:
            return

        item_text = self.results_tree.item(selection[0], 'text')
        
        try:
            # 从 "组 #14" 中提取数字 14
            group_num_str = item_text.split()[1].replace('#', '')
            group_num = int(group_num_str)
            self._show_group_details(group_num)
        except Exception as e:
            print(f"[DEBUG] Error in double-click: {e}")
            import traceback
            traceback.print_exc()

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

        # 创建详情窗口
        detail_window = tk.Toplevel(self.results_window)
        detail_window.title(f"相似视频组 #{group_num} 详情")
        detail_window.geometry("1200x600")  # 增加宽度以容纳预览区域

        # 标题区域
        title_frame = ttk.Frame(detail_window)
        title_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(title_frame, text=f"平均相似度: {group['avg_similarity']:.1f}%",
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        
        ttk.Label(title_frame, text=f"  |  共 {len(group['files'])} 个相似视频",
                 font=("微软雅黑", 10), foreground="gray").pack(side=tk.LEFT)

        # 主内容区域：左侧列表 + 右侧预览
        content_frame = ttk.Frame(detail_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：文件列表
        list_frame = ttk.LabelFrame(content_frame, text="视频列表（双击路径打开文件夹，点击行查看预览）", padding="10")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Treeview for files
        file_tree = ttk.Treeview(
            list_frame,
            columns=('duration', 'resolution', 'fps', 'size', 'path', 'open', 'delete'),
            show='tree headings'
        )
        file_tree.heading('#0', text='#')
        file_tree.heading('duration', text='时长')
        file_tree.heading('resolution', text='分辨率')
        file_tree.heading('fps', text='帧率')
        file_tree.heading('size', text='大小')
        file_tree.heading('path', text='完整路径')
        file_tree.heading('open', text='打开', anchor=tk.CENTER)
        file_tree.heading('delete', text='删除', anchor=tk.CENTER)

        file_tree.column('#0', width=40)
        file_tree.column('duration', width=80)
        file_tree.column('resolution', width=100)
        file_tree.column('fps', width=60)
        file_tree.column('size', width=80)
        file_tree.column('path', width=300)
        file_tree.column('open', width=45, anchor=tk.CENTER)  # 固定3字符宽度，居中
        file_tree.column('delete', width=45, anchor=tk.CENTER)  # 固定3字符宽度，居中

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=file_tree.yview)
        file_tree.configure(yscrollcommand=scrollbar.set)

        file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 右侧：视频预览（支持多帧）
        preview_frame = ttk.LabelFrame(content_frame, text="视频预览", padding="10")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))
        preview_frame.config(width=320)  # 固定预览区域宽度
        preview_frame.pack_propagate(False)  # 防止子组件改变框架大小

        # 主预览图
        main_preview_label = ttk.Label(preview_frame, text="选择视频查看预览", 
                                      font=("微软雅黑", 9), foreground="gray",
                                      anchor='center')
        main_preview_label.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # 缩略图列表容器（用于长视频多帧预览）
        thumbs_container = ttk.Frame(preview_frame)
        thumbs_container.pack(fill=tk.BOTH, expand=True)

        # 缩略图Canvas（可滚动）
        thumbs_canvas = tk.Canvas(thumbs_container, height=300, highlightthickness=0)
        thumbs_scrollbar = ttk.Scrollbar(thumbs_container, orient=tk.VERTICAL, command=thumbs_canvas.yview)
        thumbs_inner_frame = ttk.Frame(thumbs_canvas)

        thumbs_inner_frame.bind(
            "<Configure>",
            lambda e: thumbs_canvas.configure(scrollregion=thumbs_canvas.bbox("all"))
        )

        thumbs_canvas.create_window((0, 0), window=thumbs_inner_frame, anchor="nw")
        thumbs_canvas.configure(yscrollcommand=thumbs_scrollbar.set)

        thumbs_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        thumbs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 缓存结构：{file_path: {'frames': [photo1, photo2, ...], 'timestamps': [t1, t2, ...]}}
        # 使用main_window的属性来存储缓存，以便删除时可以清除
        if not hasattr(self.main_window, '_video_thumbnail_cache'):
            self.main_window._video_thumbnail_cache = {}
        
        thumbnail_cache = self.main_window._video_thumbnail_cache
        max_cached_videos = 10  # 最多缓存10个视频的完整预览
        max_frames_per_video = 5  # 每个视频最多5帧

        # 插入文件数据
        for idx, file_info in enumerate(group['files'], start=1):
            duration = self._format_duration(file_info['duration'])
            resolution = f"{file_info['width']}x{file_info['height']}"
            fps = f"{file_info['fps']:.1f}" if file_info['fps'] > 0 else "未知"
            size = self._format_size(self._get_file_size(file_info['path']))
            path = file_info['path']
            
            # 确保路径使用Windows标准格式（统一使用反斜杠）
            if os.name == 'nt':
                path = path.replace('/', '\\')
            
            file_tree.insert('', tk.END, text=str(idx), values=(duration, resolution, fps, size, path, '打开', '删除'))

        # 绑定事件
        # 双击行：使用Windows资源管理器打开文件夹并选中文件
        def on_double_click(event):
            item = file_tree.identify_row(event.y)
            if item:
                values = file_tree.item(item, 'values')
                if len(values) >= 7:
                    file_path = values[4]  # 从Treeview获取路径（已经格式化）
                    import subprocess
                    import os as os_module
                    # 标准化路径
                    file_path = os_module.path.normpath(file_path)
                    subprocess.Popen(f'explorer /select,"{file_path}"')
        
        file_tree.bind('<Double-Button-1>', on_double_click)
        
        # 点击行显示预览（支持多帧）
        file_tree.bind('<ButtonRelease-1>', 
                      lambda e: self._on_video_select_multiframe(
                          file_tree, main_preview_label, thumbs_inner_frame, 
                          thumbnail_cache, max_cached_videos, max_frames_per_video
                      ))
        
        # 绑定操作列点击（使用更精确的检测方式）
        def on_tree_click(event):
            # 获取点击的列
            column = file_tree.identify_column(event.x)
            item = file_tree.identify_row(event.y)
            
            if not item:
                return
            
            values = file_tree.item(item, 'values')
            if len(values) < 7:
                return
            
            # 获取文件信息
            file_path = values[4]
            for file_info in group['files']:
                import os as os_module
                if os_module.path.normpath(file_info['path']) == os_module.path.normpath(file_path):
                    if column == '#6':  # 打开列 - 直接运行文件
                        try:
                            import subprocess
                            import sys
                            
                            if sys.platform == 'win32':
                                subprocess.Popen(['start', '', file_info['path']], shell=True)
                            elif sys.platform == 'darwin':
                                subprocess.Popen(['open', file_info['path']])
                            else:
                                subprocess.Popen(['xdg-open', file_info['path']])
                        except Exception as e:
                            messagebox.showerror("错误", f"无法打开文件:\n{str(e)}")
                    elif column == '#7':  # 删除列
                        self._delete_single_file(file_tree, item, group, detail_window)
                    break
        
        file_tree.bind('<Button-1>', on_tree_click)

    def _on_click_action_column(self, tree, group, detail_window):
        """处理操作列点击事件"""
        # 获取点击位置
        x = tree.winfo_pointerx() - tree.winfo_rootx()
        y = tree.winfo_pointery() - tree.winfo_rooty()
        
        # 检查是否点击在单元格上
        region = tree.identify("region", x, y)
        if region != "cell":
            return
        
        # 检查是否是操作列（第6列）
        column = tree.identify_column(x)
        if column != '#6':
            return
        
        # 获取点击的行
        item = tree.identify_row(y)
        if not item:
            return
        
        # 获取values并检查是否有"删除"文本
        values = tree.item(item, 'values')
        if len(values) >= 6 and values[5] == '删除':
            self._delete_single_file(tree, item, group, detail_window)

    def _delete_single_file(self, tree, item, group, detail_window):
        """删除单个文件（使用批处理延迟删除）"""
        values = tree.item(item, 'values')
        if len(values) < 6:
            return
        
        file_path = values[4]
        
        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除以下文件吗？\n\n{file_path}\n\n此操作不可恢复！"):
            return
        
        import subprocess
        import os
        
        try:
            # 创建批处理文件，延迟1秒后删除
            bat_file = os.path.join(os.environ['TEMP'], 'force_delete.bat')
            with open(bat_file, 'w', encoding='gbk') as f:
                f.write('@echo off\n')
                f.write('timeout /t 1 /nobreak >nul\n')
                f.write(f'del /f /q "{file_path}"\n')
                f.write('del "%~f0"\n')  # 删除自身
            
            # 异步执行批处理（隐藏窗口）
            subprocess.Popen([bat_file], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 立即从UI中移除
            tree.delete(item)
            group['files'] = [f for f in group['files'] if f['path'] != file_path]
            
            # 如果所有文件都被删除，关闭详情窗口
            if len(tree.get_children('')) == 0:
                detail_window.destroy()
            
        except Exception as e:
            messagebox.showerror("删除失败", f"无法创建删除任务:\n{str(e)}\n\n请手动删除文件: {file_path}")

    def _delete_selected_files(self, tree, group, detail_window):
        """删除选中的文件"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的文件")
            return
        
        # 获取选中的文件路径
        files_to_delete = []
        for item in selection:
            values = tree.item(item, 'values')
            if len(values) >= 5:
                file_path = values[4]
                # 查找对应的文件信息
                for file_info in group['files']:
                    if file_info['path'] == file_path:
                        files_to_delete.append(file_info)
                        break
        
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
                    if tree.item(item, 'values')[4] == file_info['path']:
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

    def _open_file_from_detail(self, tree):
        """从详情窗口打开文件位置"""
        selection = tree.selection()
        if not selection:
            return

        values = tree.item(selection[0], 'values')
        if len(values) >= 5:
            file_path = values[4]
            
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
        if len(values) >= 5:
            file_path = values[4]
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
