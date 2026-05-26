"""
通用详情窗口组件
用于统一精确匹配、图片相似度、视频相似度的详情页面
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk


class TreeviewTooltip:
    """Treeview单元格Tooltip工具类"""
    
    def __init__(self, tree):
        self.tree = tree
        self.tooltip_window = None
        self.last_item = None
        self.last_column = None
        
        # 绑定鼠标移动事件
        tree.bind('<Motion>', self._on_motion)
        tree.bind('<Leave>', self._on_leave)
    
    def _on_motion(self, event):
        """处理鼠标移动事件"""
        # 获取当前鼠标位置的item和column
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item or not column:
            self._hide_tooltip()
            return
        
        # 如果鼠标移动到不同的单元格，更新tooltip
        if item != self.last_item or column != self.last_column:
            self.last_item = item
            self.last_column = column
            
            # 获取单元格的值
            values = self.tree.item(item, 'values')
            if values:
                # 将column '#4' 转换为索引 3
                col_idx = int(column.replace('#', '')) - 1
                if 0 <= col_idx < len(values):
                    cell_value = str(values[col_idx])
                    # 只显示路径列的tooltip（通常是较长的文本）
                    if len(cell_value) > 30:
                        self._show_tooltip(event, cell_value)
                    else:
                        self._hide_tooltip()
    
    def _show_tooltip(self, event, text):
        """显示tooltip"""
        if self.tooltip_window is None or not self.tooltip_window.winfo_exists():
            # 创建tooltip窗口
            self.tooltip_window = tk.Toplevel(self.tree)
            self.tooltip_window.overrideredirect(True)  # 无边框
            self.tooltip_window.attributes('-topmost', True)
            
            # 创建标签
            label = ttk.Label(
                self.tooltip_window, 
                text=text, 
                background='#ffffe1', 
                relief='solid', 
                borderwidth=1,
                padding=(5, 3),
                wraplength=600  # 自动换行
            )
            label.pack()
            
            # 保存label引用
            self.tooltip_label = label
        
        # 更新文本（以防内容变化）
        self.tooltip_label.config(text=text)
        
        # 计算位置：在鼠标下方显示
        x = self.tree.winfo_rootx() + event.x + 10
        y = self.tree.winfo_rooty() + event.y + 10
        
        self.tooltip_window.geometry(f'+{x}+{y}')
    
    def _hide_tooltip(self):
        """隐藏tooltip"""
        if self.tooltip_window and self.tooltip_window.winfo_exists():
            self.tooltip_window.destroy()
            self.tooltip_window = None
        
        self.last_item = None
        self.last_column = None
    
    def _on_leave(self, event):
        """鼠标离开tree时隐藏tooltip"""
        self._hide_tooltip()


class DetailWindowConfig:
    """详情窗口配置类，定义不同页签的配置"""
    
    # 精确匹配配置
    EXACT_MATCH = {
        'title_prefix': '组',
        'window_size': '900x600',
        'columns': ('size', 'ext', 'path', 'open', 'delete'),
        'headings': {
            '#0': '#',
            'size': '大小',
            'ext': '后缀',
            'path': '完整路径',
            'open': '打开',
            'delete': '删除'
        },
        'column_widths': {
            '#0': 40,
            'size': 80,
            'ext': 60,
            'path': 310,
            'open': 35,
            'delete': 35
        },
        'no_stretch_columns': {'#0', 'size', 'ext', 'open', 'delete'},  # 这些列不拉伸(stretch=False)
        'info_label_key': 'file_size_formatted',
        'info_label_format': '文件大小: {}  |  共 {} 个重复文件',
        'has_preview': False,
        'preview_type': None
    }
    
    # 图片相似度配置
    IMAGE_SIMILARITY = {
        'title_prefix': '相似组',
        'window_size': '1200x600',
        'columns': ('resolution', 'size', 'path', 'open', 'delete'),
        'headings': {
            '#0': '#',
            'resolution': '分辨率',
            'size': '大小',
            'path': '完整路径',
            'open': '打开',
            'delete': '删除'
        },
        'column_widths': {
            '#0': 40,
            'resolution': 100,
            'size': 80,
            'path': 500,
            'open': 35,
            'delete': 35
        },
        'no_stretch_columns': {'#0', 'resolution', 'size', 'open', 'delete'},  # 这些列不拉伸(stretch=False)
        'info_label_key': 'avg_similarity',
        'info_label_format': '平均相似度: {:.1f}%  |  共 {} 个相似图片',
        'has_preview': True,
        'preview_type': 'image',
        'preview_title': '图片预览'
    }
    
    # 视频相似度配置
    VIDEO_SIMILARITY = {
        'title_prefix': '相似视频组',
        'window_size': '1200x600',
        'columns': ('duration', 'resolution', 'fps', 'size', 'path', 'open', 'delete'),
        'headings': {
            '#0': '#',
            'duration': '时长',
            'resolution': '分辨率',
            'fps': '帧率',
            'size': '大小',
            'path': '完整路径',
            'open': '打开',
            'delete': '删除'
        },
        'column_widths': {
            '#0': 40,
            'duration': 80,
            'resolution': 100,
            'fps': 60,
            'size': 80,
            'path': 300,
            'open': 35,
            'delete': 35
        },
        'no_stretch_columns': {'#0', 'duration', 'resolution', 'fps', 'size', 'open', 'delete'},  # 这些列不拉伸(stretch=False)
        'info_label_key': 'avg_similarity',
        'info_label_format': '平均相似度: {:.1f}%  |  共 {} 个相似视频',
        'has_preview': True,
        'preview_type': 'video',
        'preview_title': '视频预览'
    }
    
    # 多版本软件配置
    SOFTWARE_VERSION = {
        'title_prefix': '软件',
        'window_size': '1200x600',
        'columns': ('version', 'size', 'path', 'open', 'delete'),
        'headings': {
            '#0': '#',
            'version': '版本号',
            'size': '大小',
            'path': '完整路径',
            'open': '打开',
            'delete': '删除'
        },
        'column_widths': {
            '#0': 40,
            'version': 100,
            'size': 80,
            'path': 500,
            'open': 35,
            'delete': 35
        },
        'no_stretch_columns': {'#0', 'version', 'size', 'open', 'delete'},  # 这些列不拉伸(stretch=False)
        'info_label_format': '共 {} 个版本  |  总大小: {}',
        'has_preview': False,
        'preview_type': None
    }


class FileDetailWindow:
    """通用文件详情窗口类"""
    
    def __init__(self, parent, group, group_num, config, file_formatter=None, 
                 delete_callback=None, main_window=None):
        """
        初始化详情窗口
        
        Args:
            parent: 父窗口
            group: 文件组数据
            group_num: 组号
            config: 配置字典（从DetailWindowConfig中选择）
            file_formatter: 文件信息格式化函数，返回tuple用于Treeview显示
            delete_callback: 删除回调函数
            main_window: 主窗口引用（用于缓存管理）
        """
        self.parent = parent
        self.group = group
        self.group_num = group_num
        self.config = config
        self.file_formatter = file_formatter
        self.delete_callback = delete_callback
        self.main_window = main_window or parent
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title(f"{config['title_prefix']} #{group_num} 详情")
        self.window.geometry(config['window_size'])
        
        # 初始化缓存
        self.thumbnail_cache = {}
        if config['has_preview'] and config['preview_type'] == 'video':
            if not hasattr(self.main_window, '_video_thumbnail_cache'):
                self.main_window._video_thumbnail_cache = {}
        
        # 构建UI
        self._build_ui()
        self._bind_events()
    
    def _build_ui(self):
        """构建用户界面"""
        # 标题区域
        title_frame = ttk.Frame(self.window)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 根据配置获取信息值
        if 'info_label_key' in self.config:
            info_value = self.group.get(self.config['info_label_key'], 'N/A')
            file_count = len(self.group['files'])
            info_text = self.config['info_label_format'].format(info_value, file_count)
        else:
            # 对于软件版本等没有info_label_key的配置，直接使用info_label_format
            file_count = len(self.group['files'])
            # 如果format字符串中有占位符，使用实际数据替换
            if '{}' in self.config['info_label_format']:
                # 计算总大小用于显示
                total_size = sum(_get_file_size(f['path']) for f in self.group['files'])
                total_size_formatted = _format_total_size(total_size)
                info_text = self.config['info_label_format'].format(file_count, total_size_formatted)
            else:
                info_text = self.config['info_label_format']
        
        ttk.Label(title_frame, text=info_text,
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        
        # 主内容区域
        if self.config['has_preview']:
            content_frame = ttk.Frame(self.window)
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # 左侧：文件列表
            list_frame = ttk.LabelFrame(content_frame, 
                                       text="文件列表（双击路径打开文件夹，点击行查看预览）", 
                                       padding="10")
            list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            # 右侧：预览区域
            self._build_preview_area(content_frame)
        else:
            list_frame = ttk.LabelFrame(self.window, text="文件列表（双击路径打开文件夹）", padding="10")
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Treeview
        self.file_tree = self._create_file_tree(list_frame)
        
        # 插入数据
        self._populate_file_tree()
    
    def _create_file_tree(self, parent):
        """创建文件列表Treeview"""
        tree = ttk.Treeview(
            parent,
            columns=self.config['columns'],
            show='tree headings'
        )
        
        # 设置表头
        for col, text in self.config['headings'].items():
            if col == '#0':
                tree.heading('#0', text=text)
            else:
                # 为可排序的列添加排序命令
                if col in ('size', 'ext', 'path', 'resolution', 'duration', 'fps'):
                    command = lambda c=col: self._sort_file_tree(tree, c)
                    tree.heading(col, text=text, command=command)
                else:
                    tree.heading(col, text=text)
        
        # 设置列宽
        for col, width in self.config['column_widths'].items():
            # 如果列在no_stretch_columns中,则stretch=False,否则stretch=True
            stretch = col not in self.config.get('no_stretch_columns', set())
            anchor = tk.CENTER if col in ('open', 'delete') else tk.W
            tree.column(col, width=width, anchor=anchor, stretch=stretch)
            # 调试输出：验证列宽设置
            if col in ('open', 'delete'):
                print(f"[DEBUG] Column '{col}' set to width={width}, anchor={anchor}, stretch={stretch}")
        
        # 滚动条
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 启用tooltip功能（鼠标悬停显示完整内容）
        TreeviewTooltip(tree)
        
        return tree
    
    def _populate_file_tree(self):
        """填充文件数据到Treeview"""
        for idx, file_info in enumerate(self.group['files'], start=1):
            values = self.file_formatter(file_info, idx) if self.file_formatter else self._default_formatter(file_info, idx)
            self.file_tree.insert('', tk.END, text=str(idx), values=values)
    
    def _default_formatter(self, file_info, idx):
        """默认的文件信息格式化"""
        path = file_info.get('path', '')
        if os.name == 'nt':
            path = path.replace('/', '\\')
        return (path,)
    
    def _build_preview_area(self, parent):
        """构建预览区域"""
        preview_frame = ttk.LabelFrame(parent, text=self.config['preview_title'], padding="10")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))
        preview_frame.config(width=320)
        preview_frame.pack_propagate(False)
        
        if self.config['preview_type'] == 'image':
            # 图片预览：单个预览标签
            self.preview_label = ttk.Label(preview_frame, text="选择文件查看预览", 
                                          anchor='center', foreground='gray')
            self.preview_label.pack(expand=True)
        elif self.config['preview_type'] == 'video':
            # 视频预览：主预览图 + 缩略图列表
            self.main_preview_label = ttk.Label(preview_frame, text="选择视频查看预览", 
                                               font=("微软雅黑", 9), foreground="gray",
                                               anchor='center')
            self.main_preview_label.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
            
            # 缩略图容器
            thumbs_container = ttk.Frame(preview_frame)
            thumbs_container.pack(fill=tk.BOTH, expand=True)
            
            # 缩略图Canvas
            self.thumbs_canvas = tk.Canvas(thumbs_container, height=300, highlightthickness=0)
            thumbs_scrollbar = ttk.Scrollbar(thumbs_container, orient=tk.VERTICAL, command=self.thumbs_canvas.yview)
            self.thumbs_inner_frame = ttk.Frame(self.thumbs_canvas)
            
            self.thumbs_inner_frame.bind(
                "<Configure>",
                lambda e: self.thumbs_canvas.configure(scrollregion=self.thumbs_canvas.bbox("all"))
            )
            
            self.thumbs_canvas.create_window((0, 0), window=self.thumbs_inner_frame, anchor="nw")
            self.thumbs_canvas.configure(yscrollcommand=thumbs_scrollbar.set)
            
            self.thumbs_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            thumbs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _bind_events(self):
        """绑定事件"""
        # 双击行：打开文件夹并选中文件
        def on_double_click(event):
            item = self.file_tree.identify_row(event.y)
            if item:
                values = self.file_tree.item(item, 'values')
                if len(values) >= len(self.config['columns']):
                    # 从Treeview的values中获取路径(path列的位置)
                    # path列在columns中的位置需要动态计算
                    columns = self.config['columns']
                    # 找到'path'列在columns中的索引
                    try:
                        path_col_idx = columns.index('path')
                    except ValueError:
                        # 如果没有path列,使用倒数第三列作为路径
                        path_col_idx = len(columns) - 3
                    
                    file_path = values[path_col_idx]
                    import subprocess
                    import os
                    # 标准化路径
                    file_path = os.path.normpath(file_path)
                    print(f"[DEBUG] Double-click to open: {file_path}")
                    subprocess.Popen(f'explorer /select,"{file_path}"')
        
        self.file_tree.bind('<Double-Button-1>', on_double_click)
        
        # 单击：处理操作列和预览
        def on_tree_click(event):
            column = self.file_tree.identify_column(event.x)
            item = self.file_tree.identify_row(event.y)
            
            if not item:
                return
            
            values = self.file_tree.item(item, 'values')
            if len(values) < len(self.config['columns']):
                return
            
            idx = int(self.file_tree.item(item, 'text')) - 1
            if 0 <= idx < len(self.group['files']):
                file_info = self.group['files'][idx]
                
                # 检查是否点击操作列
                # Treeview列映射规则:
                # - #0 是树形列(序号列)
                # - #1 对应 columns[0], #2 对应 columns[1], 以此类推
                # - 所以 columns[i] 对应 Treeview 的 #{i+1}
                columns = self.config['columns']
                
                # 找到'open'和'delete'在columns中的位置
                try:
                    open_idx = columns.index('open')      # 例如: columns[5] = 'open'
                    delete_idx = columns.index('delete')  # 例如: columns[6] = 'delete'
                except ValueError:
                    # 如果没有这两列，直接返回
                    return
                
                # 转换为Treeview的列标识符
                open_col = f'#{open_idx + 1}'    # columns[5] -> '#6'
                delete_col = f'#{delete_idx + 1}'  # columns[6] -> '#7'
                
                if column == open_col:
                    self._open_file(file_info)
                elif column == delete_col:
                    self._delete_file(file_info, item)
                elif self.config['has_preview']:
                    # 点击其他列，显示预览
                    self._show_preview(file_info, idx)
        
        self.file_tree.bind('<Button-1>', on_tree_click)
    
    def _open_file(self, file_info):
        """打开文件"""
        try:
            import subprocess
            
            if sys.platform == 'win32':
                subprocess.Popen(['start', '', file_info['path']], shell=True)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', file_info['path']])
            else:
                subprocess.Popen(['xdg-open', file_info['path']])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件:\n{str(e)}")
    
    def _delete_file(self, file_info, item):
        """删除文件"""
        if self.delete_callback:
            self.delete_callback(self.file_tree, file_info, item, self.group, self.window)
        else:
            # 默认删除逻辑
            result = messagebox.askyesno("确认删除", 
                                        f"确定要删除以下文件吗？\n\n{file_info['path']}")
            if result:
                try:
                    os.remove(file_info['path'])
                    self.file_tree.delete(item)
                    messagebox.showinfo("成功", "文件已删除")
                except Exception as e:
                    messagebox.showerror("错误", f"删除失败:\n{str(e)}")
    
    def _show_preview(self, file_info, idx):
        """显示预览（由子类重写或传入自定义预览函数）"""
        if not self.config['has_preview']:
            return
        
        if self.config['preview_type'] == 'image':
            self._show_image_preview(file_info)
        elif self.config['preview_type'] == 'video':
            self._show_video_preview(file_info, idx)
    
    def _show_image_preview(self, file_info):
        """显示图片预览"""
        try:
            from PIL import Image, ImageTk
            
            img_path = file_info['path']
            if not os.path.exists(img_path):
                self.preview_label.config(text="文件不存在", foreground='red')
                return
            
            # 加载并缩放图片
            img = Image.open(img_path)
            max_size = (280, 280)
            img.thumbnail(max_size, Image.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.preview_label.config(image=photo, text='')
            self.preview_label.image = photo  # 保持引用防止被垃圾回收
        except Exception as e:
            self.preview_label.config(text=f"预览失败: {str(e)[:50]}", foreground='red')
    
    def _show_video_preview(self, file_info, idx):
        """显示视频预览（多帧）"""
        # 视频预览逻辑较为复杂，由调用方实现
        # 这里提供基本框架
        pass
    
    def _sort_file_tree(self, tree, column):
        """排序文件列表"""
        items = [(tree.set(k, column), k) for k in tree.get_children('')]
        
        # 根据列类型选择排序方式
        if column == 'size':
            try:
                items.sort(key=lambda x: self._parse_size_to_bytes(x[0]))
            except:
                items.sort(key=lambda x: x[0])
        else:
            try:
                items.sort(key=lambda x: float(x[0].replace(',', '').replace(' ', '')))
            except ValueError:
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
    
    def _parse_size_to_bytes(self, size_str):
        """解析文件大小字符串为字节数"""
        size_str = size_str.strip().upper()
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4
        }
        
        for suffix, multiplier in sorted(multipliers.items(), key=lambda x: -len(x[0])):
            if size_str.endswith(suffix):
                try:
                    number = float(size_str[:-len(suffix)].strip())
                    return number * multiplier
                except ValueError:
                    break
        
        try:
            return float(size_str)
        except ValueError:
            return 0
    
    def destroy(self):
        """销毁窗口"""
        self.window.destroy()


def create_exact_match_detail(parent, group, group_num, main_window=None):
    """创建精确匹配详情窗口"""
    def formatter(file_info, idx):
        _, ext = os.path.splitext(file_info['path'])
        size_str = _format_file_size(file_info.get('size', 0))
        return (
            size_str,
            ext.lower() if ext else '(无)',
            file_info['path'],
            '打开',
            '删除'
        )
    
    return FileDetailWindow(
        parent=parent,
        group=group,
        group_num=group_num,
        config=DetailWindowConfig.EXACT_MATCH,
        file_formatter=formatter,
        main_window=main_window
    )


def create_image_similarity_detail(parent, group, group_num, main_window=None):
    """创建图片相似度详情窗口"""
    def formatter(file_info, idx):
        resolution = f"{file_info['width']}x{file_info['height']}"
        size = _format_size(_get_file_size(file_info['path']))
        path = file_info['path']
        if os.name == 'nt':
            path = path.replace('/', '\\')
        return (resolution, size, path, '打开', '删除')
    
    return FileDetailWindow(
        parent=parent,
        group=group,
        group_num=group_num,
        config=DetailWindowConfig.IMAGE_SIMILARITY,
        file_formatter=formatter,
        main_window=main_window
    )


def create_video_similarity_detail(parent, group, group_num, main_window=None):
    """创建视频相似度详情窗口"""
    
    def _format_duration(seconds):
        """格式化时长"""
        if not seconds or seconds == 0:
            return "N/A"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def formatter(file_info, idx):
        # 优先使用duration字段(秒数),如果没有则尝试duration_str
        duration_seconds = file_info.get('duration', 0)
        if duration_seconds:
            duration = _format_duration(duration_seconds)
        else:
            duration = file_info.get('duration_str', 'N/A')
        
        resolution = f"{file_info.get('width', 0)}x{file_info.get('height', 0)}"
        fps = f"{file_info.get('fps', 0):.1f}" if file_info.get('fps', 0) > 0 else "N/A"
        size = _format_size(_get_file_size(file_info['path']))
        path = file_info['path']
        if os.name == 'nt':
            path = path.replace('/', '\\')
        return (duration, resolution, fps, size, path, '打开', '删除')
    
    return FileDetailWindow(
        parent=parent,
        group=group,
        group_num=group_num,
        config=DetailWindowConfig.VIDEO_SIMILARITY,
        file_formatter=formatter,
        main_window=main_window
    )


def create_software_version_detail(parent, group, group_num, main_window=None):
    """创建多版本软件详情窗口"""
    
    def formatter(file_info, idx):
        version = file_info.get('version', 'unknown')
        size = _format_size(_get_file_size(file_info['path']))
        path = file_info['path']
        if os.name == 'nt':
            path = path.replace('/', '\\')
        return (version, size, path, '打开', '删除')
    
    # 计算总大小用于信息标签
    total_size = sum(_get_file_size(f['path']) for f in group['files'])
    total_size_formatted = _format_total_size(total_size)
    
    # 修改info_label_format以使用实际数据
    config = DetailWindowConfig.SOFTWARE_VERSION.copy()
    config['info_label_format'] = f'共 {len(group["files"])} 个版本  |  总大小: {total_size_formatted}'
    
    return FileDetailWindow(
        parent=parent,
        group=group,
        group_num=group_num,
        config=config,
        file_formatter=formatter,
        main_window=main_window
    )


# 辅助函数
def _format_file_size(size_bytes):
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


def _format_size(size_bytes):
    """格式化文件大小（别名）"""
    return _format_file_size(size_bytes)


def _get_file_size(file_path):
    """获取文件大小"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0


def _format_total_size(total_size):
    """格式化总大小"""
    if total_size == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(total_size)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"
