# GUI界面规范文档

## 1. 总体设计原则

### 1.1 设计理念
- **一致性**: 三个页签保持统一的视觉风格和交互模式
- **简洁性**: 避免过度装饰，突出功能核心
- **响应性**: 及时反馈用户操作，显示进度状态
- **容错性**: 提供确认对话框，防止误操作

### 1.2 技术选型
- **框架**: Tkinter (Python内置GUI库)
- **主题**: ttk (Themed Tkinter) 组件
- **字体**: 微软雅黑 (中文), Consolas (日志)
- **布局**: pack() 为主，grid() 为辅

### 1.3 颜色方案

```python
# 标准颜色
COLOR_PRIMARY = '#0078D4'      # 主色调（按钮高亮）
COLOR_SUCCESS = '#107C10'      # 成功/完成
COLOR_WARNING = '#FFB900'      # 警告
COLOR_ERROR = '#D13438'        # 错误
COLOR_GRAY = '#605E5C'         # 禁用/次要文本

# 背景色
COLOR_BG_WINDOW = '#F0F0F0'    # 窗口背景
COLOR_BG_FRAME = '#FFFFFF'     # Frame背景
COLOR_BG_LOG = '#FAFAFA'       # 日志区域背景

# 文本色
COLOR_TEXT_PRIMARY = '#201F1E' # 主要文本
COLOR_TEXT_SECONDARY = '#605E5C'  # 次要文本
COLOR_TEXT_DISABLED = '#A19F9D'   # 禁用文本
```

---

## 2. 主窗口规范

### 2.1 窗口属性

```python
main_window = tk.Tk()
main_window.title("文件重复校验工具 v3.0.0")
main_window.geometry("1000x700")
main_window.minsize(800, 600)
```

### 2.2 布局结构

```
┌─────────────────────────────────────────────────────┐
│  Title Bar: 文件重复校验工具 v3.0.0                  │
├─────────────────────────────────────────────────────┤
│  Directory Panel                                     │
│  ┌─────────────────────────────────────────────────┐ │
│  │ [添加目录] [删除选中]                            │ │
│  │ ┌───────────────────────────────────────────────┐│ │
│  │ │ D:\Photos\2024                                ││ │
│  │ │ D:\Videos\Movies                              ││ │
│  │ └───────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│  Tab Control                                         │
│  ┌─────────────────────────────────────────────────┐ │
│  │ [精确匹配] [图片相似度] [视频相似度]             │ │
│  │                                                 │ │
│  │  <Tab Content Area>                             │ │
│  │                                                 │ │
│  └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│  Log Panel                                           │
│  ┌─────────────────────────────────────────────────┐ │
│  │ [17:23:45] [INFO] 程序启动                       │ │
│  │ [17:23:50] [INFO] 开始扫描...                    │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2.3 目录管理面板

#### 组件定义
```python
# 目录列表Frame
dir_frame = ttk.LabelFrame(main_window, text="扫描目录", padding="10")
dir_frame.pack(fill=tk.X, padx=10, pady=5)

# 按钮行
btn_row = ttk.Frame(dir_frame)
btn_row.pack(fill=tk.X, pady=(0, 5))

ttk.Button(btn_row, text="添加目录", command=add_directory).pack(side=tk.LEFT, padx=5)
ttk.Button(btn_row, text="删除选中", command=remove_selected).pack(side=tk.LEFT, padx=5)

# 目录列表Treeview
dir_tree = ttk.Treeview(dir_frame, columns=('path',), show='tree headings', height=5)
dir_tree.heading('#0', text='#')
dir_tree.heading('path', text='路径')
dir_tree.column('#0', width=40)
dir_tree.column('path', width=400)
dir_tree.pack(fill=tk.X)
```

#### 交互行为
- **添加目录**: 弹出文件夹选择对话框 → 添加到列表
- **删除选中**: 确认对话框 → 从列表移除
- **双击行**: 打开该目录

### 2.4 日志面板

#### 组件定义
```python
log_frame = ttk.LabelFrame(main_window, text="运行日志", padding="10")
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

log_text = scrolledtext.ScrolledText(
    log_frame,
    height=8,
    font=("Consolas", 9),
    wrap=tk.WORD,
    state=tk.DISABLED  # 只读
)
log_text.pack(fill=tk.BOTH, expand=True)
```

#### 日志格式
```
[HH:MM:SS] [LEVEL] Message

示例:
[17:23:45] [INFO] 程序启动
[17:23:50] [INFO] 开始扫描...
[17:24:12] [WARNING] 无法读取文件: xxx.jpg
[17:25:30] [ERROR] 数据库连接失败
[17:26:00] [SUCCESS] 扫描完成，发现23个重复组
```

#### 日志级别颜色
```python
LOG_COLORS = {
    'INFO': 'black',
    'WARNING': '#FF8C00',    # 橙色
    'ERROR': '#D13438',      # 红色
    'SUCCESS': '#107C10',    # 绿色
    'DEBUG': '#605E5C'       # 灰色
}
```

---

## 3. 页签通用规范

### 3.1 页签结构

每个页签包含以下区域：
1. **设置区域**: 配置参数（阈值、扫描方式等）
2. **控制按钮**: 开始、停止、结果
3. **进度条**: 显示扫描进度
4. **状态标签**: 当前操作描述
5. **日志区域**: 页签专属日志（可选）

### 3.2 设置区域样式

```python
# LabelFrame包裹设置项
config_frame = ttk.LabelFrame(tab_frame, text="检测设置", padding="10")
config_frame.pack(fill=tk.X, padx=10, pady=5)

# 每行一个设置项
setting_row = ttk.Frame(config_frame)
setting_row.pack(fill=tk.X, pady=2)

ttk.Label(setting_row, text="标签:", width=12).pack(side=tk.LEFT)
# 控件...
```

### 3.3 按钮样式

```python
# 主要按钮（开始检测）
start_btn = ttk.Button(
    btn_frame,
    text="开始检测",
    command=start_scan,
    style="Accent.TButton"  # 强调样式
)

# 普通按钮
result_btn = ttk.Button(
    btn_frame,
    text="结果",
    command=show_results
)

# 禁用按钮
stop_btn = ttk.Button(
    btn_frame,
    text="停止",
    command=stop_scan,
    state=tk.DISABLED
)
```

#### 自定义样式
```python
style = ttk.Style()
style.configure("Accent.TButton", 
                font=("微软雅黑", 9, "bold"),
                foreground="#0078D4")
```

### 3.4 进度条

```python
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(
    progress_frame,
    variable=progress_var,
    maximum=100,
    mode='determinate'  # 确定模式
)
progress_bar.pack(fill=tk.X)

status_label = ttk.Label(progress_frame, text="", font=("微软雅黑", 8))
status_label.pack()
```

#### 更新逻辑
```python
def update_progress(progress: float, message: str):
    """
    更新进度条
    
    Args:
        progress: 进度百分比 (0-100)
        message: 状态消息
    """
    progress_var.set(progress)
    status_label.config(text=message)
    main_window.update_idletasks()  # 强制刷新UI
```

---

## 4. Treeview规范

### 4.1 列配置模板

```python
# 标准列配置模式
tree = ttk.Treeview(
    parent,
    columns=('col1', 'col2', 'col3', 'open', 'delete'),
    show='tree headings'
)

# 设置表头
tree.heading('#0', text='#')
tree.heading('col1', text='列1名称')
# ...

# 设置列宽（关键！）
tree.column('#0', width=40, anchor=tk.CENTER, stretch=False)
tree.column('col1', width=100, anchor=tk.W, stretch=False)
# ...
tree.column('open', width=35, anchor=tk.CENTER, stretch=False)
tree.column('delete', width=35, anchor=tk.CENTER, stretch=False)

# 不拉伸的列集合（用于动态配置）
no_stretch_columns = {'#0', 'col1', 'open', 'delete'}
```

### 4.2 关键配置说明

#### stretch参数
```python
# ❌ 错误：未设置stretch=False，列会被自动拉伸
tree.column('open', width=35, anchor=tk.CENTER)

# ✅ 正确：固定宽度列必须设置stretch=False
tree.column('open', width=35, anchor=tk.CENTER, stretch=False)
```

#### anchor参数
```python
# 序号、按钮列：居中对齐
tree.column('#0', anchor=tk.CENTER)
tree.column('open', anchor=tk.CENTER)
tree.column('delete', anchor=tk.CENTER)

# 文本列：左对齐
tree.column('path', anchor=tk.W)
tree.column('size', anchor=tk.W)

# 数字列：右对齐（可选）
tree.column('count', anchor=tk.E)
```

### 4.3 滚动条

```python
# 垂直滚动条
scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)

tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
```

### 4.4 事件绑定

#### 双击事件
```python
def on_double_click(event):
    item = tree.identify_row(event.y)
    if item:
        values = tree.item(item, 'values')
        # 处理逻辑...

tree.bind('<Double-Button-1>', on_double_click)
```

#### 单击事件
```python
def on_click(event):
    column = tree.identify_column(event.x)
    item = tree.identify_row(event.y)
    
    if column == '#6':  # 打开列
        open_file(values[4])
    elif column == '#7':  # 删除列
        delete_file(values[4])

tree.bind('<Button-1>', on_click)
```

#### 排序事件
```python
def sort_by_column(column):
    items = [(tree.set(k, column), k) for k in tree.get_children('')]
    items.sort(key=lambda x: x[0])
    
    for index, (val, k) in enumerate(items):
        tree.move(k, '', index)

tree.heading('size', text='大小', command=lambda: sort_by_column('size'))
```

---

## 5. 详情窗口规范

### 5.1 窗口布局模板

```python
class DetailWindow:
    def __init__(self, parent, group, config):
        self.window = tk.Toplevel(parent)
        self.window.title(f"{config['title_prefix']} #{group_num} 详情")
        self.window.geometry(config['window_size'])
        
        # 标题区域
        self._build_header()
        
        # 内容区域（有预览/无预览）
        if config['has_preview']:
            self._build_content_with_preview()
        else:
            self._build_content_only()
        
        # 绑定事件
        self._bind_events()
```

### 5.2 预览区域布局

#### 图片预览
```python
# 右侧预览Frame
preview_frame = ttk.LabelFrame(content_frame, text="图片预览", padding="10")
preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))
preview_frame.config(width=320)
preview_frame.pack_propagate(False)  # 固定宽度

# 预览标签
preview_label = ttk.Label(
    preview_frame, 
    text="选择文件查看预览",
    anchor='center',
    foreground='gray'
)
preview_label.pack(expand=True)
```

#### 视频预览
```python
# 右侧预览Frame
preview_frame = ttk.LabelFrame(content_frame, text="视频预览", padding="10")
preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))
preview_frame.config(width=320)
preview_frame.pack_propagate(False)

# 主预览图
main_preview_label = ttk.Label(
    preview_frame, 
    text="选择视频查看预览",
    font=("微软雅黑", 9),
    foreground="gray",
    anchor='center'
)
main_preview_label.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

# 缩略图容器
thumbs_container = ttk.Frame(preview_frame)
thumbs_container.pack(fill=tk.BOTH, expand=True)

# Canvas + Scrollbar
thumbs_canvas = tk.Canvas(thumbs_container, height=300, highlightthickness=0)
thumbs_scrollbar = ttk.Scrollbar(thumbs_container, orient=tk.VERTICAL, command=thumbs_canvas.yview)
thumbs_inner_frame = ttk.Frame(thumbs_canvas)

thumbs_canvas.create_window((0, 0), window=thumbs_inner_frame, anchor="nw")
thumbs_canvas.configure(yscrollcommand=thumbs_scrollbar.set)

thumbs_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
thumbs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
```

### 5.3 缩略图横向排列

```python
# 创建横向排列容器
thumbs_row_frame = ttk.Frame(thumbs_inner_frame)
thumbs_row_frame.pack(fill=tk.X, padx=5, pady=5)

# 并排添加缩略图
for frame_data in frames:
    thumb_container = ttk.Frame(thumbs_row_frame)
    thumb_container.pack(side=tk.LEFT, padx=3)
    
    # 缩略图
    thumb_label = ttk.Label(thumb_container, image=frame_data['thumb_photo'])
    thumb_label.pack()
    
    # 时间戳
    time_label = ttk.Label(
        thumb_container,
        text=f"{mins:02d}:{secs:02d}",
        font=("微软雅黑", 7),
        foreground='gray'
    )
    time_label.pack(pady=(2, 0))
```

---

## 6. Tooltip规范

### 6.1 Treeview单元格Tooltip

```python
class TreeviewTooltip:
    """Treeview单元格鼠标悬停提示"""
    
    def __init__(self, tree):
        self.tree = tree
        self.tooltip_window = None
        self.last_item = None
        self.last_column = None
        
        tree.bind('<Motion>', self._on_motion)
        tree.bind('<Leave>', self._on_leave)
    
    def _on_motion(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item or not column:
            self._hide_tooltip()
            return
        
        if item != self.last_item or column != self.last_column:
            self.last_item = item
            self.last_column = column
            
            values = self.tree.item(item, 'values')
            col_idx = int(column.replace('#', '')) - 1
            
            if 0 <= col_idx < len(values):
                cell_value = str(values[col_idx])
                if len(cell_value) > 30:  # 只显示长文本的tooltip
                    self._show_tooltip(event, cell_value)
    
    def _show_tooltip(self, event, text):
        if self.tooltip_window is None or not self.tooltip_window.winfo_exists():
            self.tooltip_window = tk.Toplevel(self.tree)
            self.tooltip_window.overrideredirect(True)
            self.tooltip_window.attributes('-topmost', True)
            
            label = ttk.Label(
                self.tooltip_window,
                text=text,
                background='#ffffe1',
                relief='solid',
                borderwidth=1,
                padding=(5, 3),
                wraplength=600
            )
            label.pack()
            self.tooltip_label = label
        
        self.tooltip_label.config(text=text)
        
        x = self.tree.winfo_rootx() + event.x + 10
        y = self.tree.winfo_rooty() + event.y + 10
        self.tooltip_window.geometry(f'+{x}+{y}')
```

### 6.2 使用方式

```python
# 为Treeview启用tooltip
TreeviewTooltip(tree)
```

---

## 7. 对话框规范

### 7.1 确认对话框

```python
# 删除确认
result = messagebox.askyesno(
    "确认删除",
    f"确定要删除以下文件吗？\n\n{file_path}\n\n此操作不可恢复！"
)

if result:
    # 执行删除
    pass
```

### 7.2 错误对话框

```python
messagebox.showerror(
    "错误",
    f"无法打开文件:\n{str(e)}"
)
```

### 7.3 信息对话框

```python
messagebox.showinfo(
    "删除完成",
    f"成功删除 {deleted_count} 个文件"
)
```

### 7.4 警告对话框

```python
messagebox.showwarning(
    "警告",
    "请先添加要扫描的目录！"
)
```

---

## 8. 响应式设计

### 8.1 窗口大小调整

```python
# 设置最小窗口尺寸
main_window.minsize(800, 600)

# 某些Frame可随窗口调整
content_frame.pack(fill=tk.BOTH, expand=True)

# 某些Frame固定尺寸
preview_frame.config(width=320)
preview_frame.pack_propagate(False)
```

### 8.2 字体缩放

```python
# 使用相对字体大小
font_small = ("微软雅黑", 8)
font_normal = ("微软雅黑", 9)
font_large = ("微软雅黑", 12, "bold")

# 日志使用等宽字体
font_log = ("Consolas", 9)
```

---

## 9. 性能优化

### 9.1 UI刷新

```python
# 批量更新后刷新UI
def update_ui():
    # ... 更新多个组件 ...
    main_window.update_idletasks()  # 强制刷新
```

### 9.2 异步加载

```python
# 耗时操作在后台线程执行
threading.Thread(
    target=load_thumbnails_async,
    args=(file_path,),
    daemon=True
).start()

# 完成后在主线程更新UI
main_window.after(0, lambda: update_preview(photo))
```

### 9.3 缓存策略

```python
# 缩略图缓存
thumbnail_cache = {}
MAX_CACHE_SIZE = 50

def get_thumbnail(path):
    if path in thumbnail_cache:
        return thumbnail_cache[path]
    
    # 生成缩略图...
    
    # 更新缓存
    if len(thumbnail_cache) >= MAX_CACHE_SIZE:
        thumbnail_cache.pop(next(iter(thumbnail_cache)))
    thumbnail_cache[path] = photo
    
    return photo
```

---

## 10. 常见问题与解决方案

### 10.1 列宽不生效

**问题**: 设置了width但列仍然很宽

**解决**:
```python
# 必须设置stretch=False
tree.column('open', width=35, anchor=tk.CENTER, stretch=False)
```

### 10.2 图片显示变形

**问题**: 图片拉伸失真

**解决**:
```python
# 使用thumbnail保持宽高比
img.thumbnail((280, 280), Image.LANCZOS)
```

### 10.3 点击事件错位

**问题**: 点击"打开"无反应，点击"删除"变成打开

**解决**:
```python
# 动态查找列位置，不要硬编码索引
open_idx = columns.index('open')
open_col = f'#{open_idx + 1}'
```

### 10.4 闭包问题

**问题**: 循环中绑定的事件都引用最后一个变量

**解决**: 使用工厂函数
```python
def make_handler(photo):
    def handler(event=None):
        label.config(image=photo)
    return handler

for photo in photos:
    label.bind('<Button-1>', make_handler(photo))
```

---

## 11. 最佳实践

### 11.1 代码组织
- 将UI构建逻辑封装到方法中（`_build_ui`, `_bind_events`）
- 使用配置字典驱动不同页签的差异
- 公共组件抽取到独立模块（`detail_window.py`）

### 11.2 命名规范
- 私有方法前导下划线（`_on_click`）
- 变量名清晰表达用途（`progress_var`, `status_label`）
- 常量全大写（`MAX_CACHE_SIZE`）

### 11.3 注释规范
- 复杂布局添加注释说明
- 关键参数解释原因
- 已知问题添加TODO标记

---

*文档版本: v3.0.0*  
*最后更新: 2026-05-26*
