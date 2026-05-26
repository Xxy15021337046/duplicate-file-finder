#!/usr/bin/env python3
"""
多版本软件检测标签页模块
负责扫描和识别同一软件的多个版本
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import subprocess
from datetime import datetime


class SoftwareVersionTab:
    """多版本软件检测标签页"""

    def __init__(self, parent_notebook, main_window):
        self.parent_notebook = parent_notebook
        self.main_window = main_window
        self.frame = ttk.Frame(parent_notebook)

        # 变量
        self.db_path_var = tk.StringVar(value="software_versions.db")
        self.output_path_var = tk.StringVar(value="software_versions.json")

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

        # 第一行：数据库路径
        db_row = ttk.Frame(config_frame)
        db_row.pack(fill=tk.X, pady=2)

        ttk.Label(db_row, text="数据库:", width=12).pack(side=tk.LEFT)
        ttk.Entry(db_row, textvariable=self.db_path_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(db_row, text="浏览...", command=self._browse_db).pack(side=tk.LEFT)

        # 第二行：输出文件路径
        output_row = ttk.Frame(config_frame)
        output_row.pack(fill=tk.X, pady=2)

        ttk.Label(output_row, text="输出文件:", width=12).pack(side=tk.LEFT)
        ttk.Entry(output_row, textvariable=self.output_path_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_row, text="浏览...", command=self._browse_output).pack(side=tk.LEFT)

        # 第三行：扫描方式
        scan_row = ttk.Frame(config_frame)
        scan_row.pack(fill=tk.X, pady=2)

        ttk.Label(scan_row, text="扫描方式:", width=12).pack(side=tk.LEFT)

        self.incremental_var = tk.BooleanVar(value=False)  # 默认全量扫描
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

        # 文件格式过滤区域
        format_frame = ttk.LabelFrame(self.frame, text="文件格式", padding="10")
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        # 第一行：全选 + 常用格式
        format_row1 = ttk.Frame(format_frame)
        format_row1.pack(fill=tk.X, pady=2)

        # 初始化格式变量
        self.format_all = tk.BooleanVar(value=True)
        self.format_exe = tk.BooleanVar(value=True)
        self.format_dll = tk.BooleanVar(value=True)
        self.format_msi = tk.BooleanVar(value=True)
        self.format_jar = tk.BooleanVar(value=True)
        self.format_pyd = tk.BooleanVar(value=True)
        
        # 自定义后缀输入
        self.custom_format_var = tk.StringVar(value="")

        ttk.Checkbutton(format_row1, text="全部", variable=self.format_all,
                       command=self._on_format_all_changed).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(format_row1, text="EXE", variable=self.format_exe,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="DLL", variable=self.format_dll,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="MSI", variable=self.format_msi,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="JAR", variable=self.format_jar,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(format_row1, text="PYD", variable=self.format_pyd,
                       command=self._on_format_item_changed).pack(side=tk.LEFT, padx=2)

        # 第二行：自定义后缀输入
        format_row2 = ttk.Frame(format_frame)
        format_row2.pack(fill=tk.X, pady=5)

        ttk.Label(format_row2, text="自定义后缀:", width=12).pack(side=tk.LEFT)
        custom_entry = ttk.Entry(format_row2, textvariable=self.custom_format_var, width=50)
        custom_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            format_row2, 
            text="(多个用逗号、分号或空格分隔，如: sys,dll.so)",
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

    def _browse_db(self):
        """浏览数据库文件"""
        filename = filedialog.asksaveasfilename(
            title="选择数据库文件",
            defaultextension=".db",
            filetypes=[("数据库文件", "*.db"), ("所有文件", "*.*")]
        )
        if filename:
            self.db_path_var.set(filename)

    def _browse_output(self):
        """浏览输出文件"""
        filename = filedialog.asksaveasfilename(
            title="选择输出文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_path_var.set(filename)

    def _on_format_all_changed(self):
        """全选状态改变"""
        state = self.format_all.get()
        self.format_exe.set(state)
        self.format_dll.set(state)
        self.format_msi.set(state)
        self.format_jar.set(state)
        self.format_pyd.set(state)

    def _on_format_item_changed(self):
        """单个格式项状态改变"""
        # 检查是否所有项都被选中
        all_selected = all([
            self.format_exe.get(),
            self.format_dll.get(),
            self.format_msi.get(),
            self.format_jar.get(),
            self.format_pyd.get()
        ])
        self.format_all.set(all_selected)

    def _get_selected_formats(self) -> set:
        """获取选中的文件格式集合"""
        formats = set()
        
        # 标准格式
        if self.format_exe.get():
            formats.add('.exe')
        if self.format_dll.get():
            formats.add('.dll')
        if self.format_msi.get():
            formats.add('.msi')
        if self.format_jar.get():
            formats.add('.jar')
        if self.format_pyd.get():
            formats.add('.pyd')
        
        # 自定义后缀
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
        
        # 调试日志
        print(f"[DEBUG] Selected formats: {formats}")
        print(f"[DEBUG] Checkboxes state: exe={self.format_exe.get()}, dll={self.format_dll.get()}, msi={self.format_msi.get()}, jar={self.format_jar.get()}, pyd={self.format_pyd.get()}")
        
        return formats

    def start_scan(self):
        """启动多版本软件检测"""
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
        """执行多版本软件检测（后台线程）"""
        try:
            from core.software_version_detector import SoftwareVersionDetector

            # 获取配置
            directories = self.main_window.directories
            db_path = self.db_path_var.get()
            incremental = self.incremental_var.get()
            
            # 获取选中的文件格式
            formats = self._get_selected_formats()
            if not formats:
                messagebox.showwarning("警告", "请至少选择一种文件格式！")
                return

            self._log(f"开始多版本软件检测...")
            self._log(f"目录数: {len(directories)}")
            self._log(f"扫描方式: {'增量' if incremental else '全量'}")
            self._log(f"文件格式: {', '.join(sorted(formats))}")

            # 全量扫描时自动清空数据库
            if not incremental:
                self._log("全量扫描模式：正在清空旧数据...")
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM software_index')
                    cursor.execute('DELETE FROM software_groups')
                    conn.commit()
                    conn.close()
                    self._log("旧数据已清空", "SUCCESS")
                except Exception as e:
                    self._log(f"清空旧数据失败: {e}", "WARNING")

            # 创建检测器
            detector = SoftwareVersionDetector(
                db_path=db_path,
                progress_callback=self._on_progress,
                log_callback=lambda msg, lvl="INFO": self._log(msg, lvl)
            )

            # 构建索引，传入格式过滤
            self._log("正在提取PE信息并构建索引...")
            detector.build_index(directories, incremental=incremental, extensions=formats)

            # 查找多版本软件
            self._log("正在查找多版本软件...")
            groups = detector.find_multiple_versions(min_versions=2)

            self.current_groups = groups
            
            # 导出结果
            if groups:
                output_path = self.output_path_var.get()
                detector.export_results(groups, output_path)
                self._log(f"结果已导出到: {output_path}")

            self._log(f"检测完成！找到 {len(groups)} 个软件有多个版本")

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

    def _stop_scan(self):
        """停止扫描"""
        self.main_window.stop_flag.set()
        self.main_window._log("正在停止检测...")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def _show_results_window(self):
        """显示结果窗口"""
        # 如果当前没有结果，但数据库中有数据，尝试从数据库加载
        if not self.current_groups:
            db_path = self.db_path_var.get()
            if os.path.exists(db_path):
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    cursor = conn.execute("SELECT COUNT(*) FROM software_groups WHERE version_count > 1")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        self._log(f"检测到历史数据 ({count} 个多版本软件)，重新加载...")
                        
                        # 重新执行检测以加载结果
                        thread = threading.Thread(
                            target=self._run_scan,
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
        self.results_window.title("多版本软件检测结果")
        self.results_window.geometry("1100x600")

        # 标题和摘要
        header_frame = ttk.Frame(self.results_window)
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(header_frame, text=f"找到 {len(self.current_groups)} 个软件有多个版本",
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)

        # Treeview
        tree_frame = ttk.Frame(self.results_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.results_tree = ttk.Treeview(tree_frame, 
                                        columns=('name', 'versions', 'size', 'latest', 'action'), 
                                        show='tree headings')
        self.results_tree.heading('#0', text='组别')
        self.results_tree.heading('name', text='软件名称', command=lambda: self._sort_results_tree('name'))
        self.results_tree.heading('versions', text='版本数量', command=lambda: self._sort_results_tree('versions'))
        self.results_tree.heading('size', text='总大小', command=lambda: self._sort_results_tree('size'))
        self.results_tree.heading('latest', text='最新版本', command=lambda: self._sort_results_tree('latest'))
        self.results_tree.heading('action', text='操作')

        self.results_tree.column('#0', width=80)
        self.results_tree.column('name', width=200)
        self.results_tree.column('versions', width=80)
        self.results_tree.column('size', width=100)
        self.results_tree.column('latest', width=100)
        self.results_tree.column('action', width=60)
        
        # 记录排序状态
        self._results_sort_reverse = False
        self._results_last_sort_column = None

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件
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

            group_id = f"软件 #{group['group_id']}"
            name = group['software_name']
            versions = f"{group['version_count']} 个"
            
            # 格式化总大小
            total_size = self._format_size(group['total_size'])
            
            latest = group['latest_version'] or 'N/A'

            self.results_tree.insert('', tk.END, text=group_id, values=(
                name, versions, total_size, latest, "隐藏"
            ), tags=(str(group['group_id']),))

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"

    def _sort_results_tree(self, column):
        """排序结果树"""
        items = [(self.results_tree.set(k, column), k) for k in self.results_tree.get_children('')]
        
        # 根据列类型选择排序方式
        if column == 'versions':
            # 版本数量列：提取数字后排序
            try:
                items.sort(key=lambda x: int(x[0].replace('个', '').strip()))
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
        
        if column == '#5':  # 只有操作列（第5列）才触发
            item = self.results_tree.identify_row(event.y)
            if item:
                item_text = self.results_tree.item(item, 'text')
                try:
                    # 从 "软件 #14" 中提取数字 14
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
                # 从 "软件 #14" 中提取数字 14
                item_group_num = int(item_text.split()[1].replace('#', ''))
                if item_group_num == group_num:
                    self.results_tree.delete(item)
                    break
            except:
                pass
        
        self.main_window._log(f"已隐藏软件组 #{group_num}")

    def _on_double_click_group(self, event):
        """双击组别事件处理"""
        selection = self.results_tree.selection()
        
        if not selection:
            return

        item_text = self.results_tree.item(selection[0], 'text')
        
        try:
            # 从 "软件 #14" 中提取数字 14
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

        # 使用公共组件创建详情窗口
        from gui_modules.detail_window import create_software_version_detail
        
        detail_window_obj = create_software_version_detail(
            parent=self.results_window,
            group=group,
            group_num=group_num,
            main_window=self.main_window
        )
        
        # 绑定删除回调
        detail_window_obj.delete_callback = lambda tree, file_info, item, grp, win: \
            self._delete_single_file(tree, item, grp, win)

    def _delete_single_file(self, tree, item, group, detail_window):
        """删除单个文件"""
        values = tree.item(item, 'values')
        if len(values) < 5:
            return
        
        file_path = values[2]  # path列在第3列（索引2）
        
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
            # 从 "软件 #14" 中提取数字 14
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

    def _open_location(self, file_path):
        """打开文件位置（Windows）"""
        try:
            print(f"[DEBUG] Opening location for: {file_path}")
            
            if os.name == 'nt':  # Windows
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

    def _hide_group(self, item_id):
        """隐藏指定的组"""
        item_text = self.results_tree.item(item_id, 'text')
        try:
            # 从 "软件 #14" 中提取数字 14
            group_num_str = item_text.split()[1].replace('#', '')
            group_num = int(group_num_str)
            self.hidden_groups.add(group_num)
            self.results_tree.delete(item_id)
            self.main_window._log(f"已隐藏软件组 #{group_num}")
        except:
            pass

    def _show_all_groups(self):
        """显示所有隐藏的组"""
        if not self.hidden_groups:
            return

        self.hidden_groups.clear()
        self._display_all_results()
        self.main_window._log("已显示所有隐藏的组")
