# 公共组件使用指南

## 1. 概述

### 1.1 设计目标
为减少代码重复，提高可维护性，项目将三个页签（精确匹配、图片相似度、视频相似度）的详情窗口代码统一封装为公共组件。

### 1.2 组件位置
```
gui_modules/
└── detail_window.py    # 公共详情窗口组件
```

### 1.3 核心优势
- **代码复用**: 减少约400行重复代码
- **易于维护**: 修改一处，三处生效
- **配置驱动**: 通过配置字典定制不同页签的行为
- **扩展性强**: 新增页签只需添加配置

---

## 2. 架构设计

### 2.1 类图

```
┌─────────────────────────────┐
│   TreeviewTooltip           │  ← Tooltip工具类
│   - __init__(tree)          │
│   - _on_motion(event)       │
│   - _show_tooltip(text)     │
│   - _hide_tooltip()         │
─────────────────────────────┘

┌─────────────────────────────┐
│   DetailWindowConfig        │  ← 配置类
│   EXACT_MATCH = {...}       │
│   IMAGE_SIMILARITY = {...}  │
│   VIDEO_SIMILARITY = {...}  │
└─────────────────────────────┘

┌─────────────────────────────┐
│   FileDetailWindow          │  ← 通用详情窗口
│   - __init__(config)        │
│   - _build_ui()             │
│   - _create_file_tree()     │
│   - _bind_events()          │
│   - _show_preview()         │
└─────────────────────────────┘
         ▲
         │ 继承/使用
┌────────────────┬──────────┐
│        │        │          │
create_  create_  create_
exact_   image_   video_
match_   similar_ similar_
detail   ity_     ity_
         detail   detail
```

### 2.2 工厂函数

```python
# 精确匹配详情窗口
def create_exact_match_detail(parent, group, group_num, main_window=None):
    return FileDetailWindow(
        parent=parent,
        group=group,
        group_num=group_num,
        config=DetailWindowConfig.EXACT_MATCH,
        file_formatter=exact_match_formatter,
        main_window=main_window
    )

# 图片相似度详情窗口
def create_image_similarity_detail(parent, group, group_num, main_window=None):
    return FileDetailWindow(...)

# 视频相似度详情窗口
def create_video_similarity_detail(parent, group, group_num, main_window=None):
    return FileDetailWindow(...)
```

---

## 3. 配置详解

### 3.1 配置项说明

```python
CONFIG_TEMPLATE = {
    # 窗口标题前缀
    'title_prefix': '组',              # 如: "组 #14 详情"
    
    # 窗口尺寸
    'window_size': '900x600',          # 宽x高
    
    # 列定义（Treeview的columns参数）
    'columns': ('size', 'ext', 'path', 'open', 'delete'),
    
    # 列头文本
    'headings': {
        '#0': '#',                     # 序号列
        'size': '大小',                 # 数据列
        'ext': '后缀',
        'path': '完整路径',
        'open': '打开',                 # 操作列
        'delete': '删除'                # 操作列
    },
    
    # 列宽（像素）
    'column_widths': {
        '#0': 40,
        'size': 80,
        'ext': 60,
        'path': 310,
        'open': 35,                     # 固定宽度
        'delete': 35                    # 固定宽度
    },
    
    # 不拉伸的列集合（stretch=False）
    'no_stretch_columns': {'#0', 'size', 'ext', 'open', 'delete'},
    
    # 信息标签格式
    'info_label_key': 'file_size_formatted',  # 从group中取的key
    'info_label_format': '文件大小: {}  |  共 {} 个重复文件',
    
    # 预览配置
    'has_preview': False,               # 是否有预览区域
    'preview_type': None,               # 'image' 或 'video'
    'preview_title': '预览'             # 预览区域标题
}
```

### 3.2 三种页签配置对比

| 配置项 | 精确匹配 | 图片相似度 | 视频相似度 |
|--------|----------|-----------|-----------|
| title_prefix | 组 | 相似组 | 相似视频组 |
| window_size | 900x600 | 1200x600 | 1200x600 |
| columns | (size, ext, path, open, delete) | (resolution, size, path, open, delete) | (duration, resolution, fps, size, path, open, delete) |
| has_preview | False | True | True |
| preview_type | None | image | video |
| info_label_key | file_size_formatted | avg_similarity | avg_similarity |
| info_label_format | 文件大小: {} \| 共 {} 个重复文件 | 平均相似度: {:.1f}% \| 共 {} 个相似图片 | 平均相似度: {:.1f}% \| 共 {} 个相似视频 |

---

## 4. 使用示例

### 4.1 精确匹配页签

```python
from gui_modules.detail_window import create_exact_match_detail

def _show_group_details(self, group_num):
    """显示精确匹配组详情"""
    # 获取组数据
    group = self.current_groups[group_num - 1]
    
    # 创建详情窗口
    detail_window_obj = create_exact_match_detail(
        parent=self.results_window,
        group=group,
        group_num=group_num,
        main_window=self.main_window
    )
    
    # 绑定删除回调
    detail_window_obj.delete_callback = lambda tree, file_info, item, grp, win: \
        self._delete_single_file(tree, item, grp, win)
```

### 4.2 图片相似度页签

```python
from gui_modules.detail_window import create_image_similarity_detail

def _show_group_details(self, group_num):
    """显示图片相似度组详情"""
    group = self.current_groups[group_num - 1]
    
    detail_window_obj = create_image_similarity_detail(
        parent=self.results_window,
        group=group,
        group_num=group_num,
        main_window=self.main_window
    )
    
    # 绑定删除回调
    detail_window_obj.delete_callback = self._delete_single_file
```

### 4.3 视频相似度页签

```python
from gui_modules.detail_window import create_video_similarity_detail

def _show_group_details(self, group_num):
    """显示视频相似度组详情"""
    group = self.current_groups[group_num - 1]
    
    detail_window_obj = create_video_similarity_detail(
        parent=self.results_window,
        group=group,
        group_num=group_num,
        main_window=self.main_window
    )
    
    # 绑定删除回调
    detail_window_obj.delete_callback = lambda tree, file_info, item, grp, win: \
        self._delete_single_file(tree, item, grp, win)
    
    # 重写视频预览方法（增强版多帧预览）
    original_show_video_preview = detail_window_obj._show_video_preview
    
    def enhanced_video_preview(file_info, idx):
        # 自定义视频预览逻辑...
        pass
    
    detail_window_obj._show_video_preview = enhanced_video_preview
```

---

## 5. 格式化函数

### 5.1 作用
格式化函数负责将文件信息转换为Treeview显示的values元组。

### 5.2 精确匹配格式化

```python
def exact_match_formatter(file_info, idx):
    """
    精确匹配文件信息格式化
    
    Args:
        file_info: 文件信息字典 {'path': ..., 'size': ...}
        idx: 序号
    
    Returns:
        tuple: (size_str, ext, path, '打开', '删除')
    """
    _, ext = os.path.splitext(file_info['path'])
    size_str = format_file_size(file_info.get('size', 0))
    
    return (
        size_str,
        ext.lower() if ext else '(无)',
        file_info['path'],
        '打开',
        '删除'
    )
```

### 5.3 图片相似度格式化

```python
def image_similarity_formatter(file_info, idx):
    """
    图片相似度文件信息格式化
    
    Returns:
        tuple: (resolution, size, path, '打开', '删除')
    """
    resolution = f"{file_info['width']}x{file_info['height']}"
    size = format_size(get_file_size(file_info['path']))
    path = file_info['path']
    
    # Windows路径标准化
    if os.name == 'nt':
        path = path.replace('/', '\\')
    
    return (resolution, size, path, '打开', '删除')
```

### 5.4 视频相似度格式化

```python
def video_similarity_formatter(file_info, idx):
    """
    视频相似度文件信息格式化
    
    Returns:
        tuple: (duration, resolution, fps, size, path, '打开', '删除')
    """
    # 格式化时长
    duration_seconds = file_info.get('duration', 0)
    if duration_seconds:
        duration = format_duration(duration_seconds)
    else:
        duration = file_info.get('duration_str', 'N/A')
    
    resolution = f"{file_info.get('width', 0)}x{file_info.get('height', 0)}"
    fps = f"{file_info.get('fps', 0):.1f}" if file_info.get('fps', 0) > 0 else "N/A"
    size = format_size(get_file_size(file_info['path']))
    path = file_info['path']
    
    if os.name == 'nt':
        path = path.replace('/', '\\')
    
    return (duration, resolution, fps, size, path, '打开', '删除')
```

---

## 6. 事件处理

### 6.1 双击事件（打开文件夹）

```python
def on_double_click(event):
    """双击行：打开文件所在文件夹并选中文件"""
    item = self.file_tree.identify_row(event.y)
    if item:
        values = self.file_tree.item(item, 'values')
        
        # 从Treeview的values中获取已格式化的路径
        columns = self.config['columns']
        path_col_idx = columns.index('path')
        file_path = values[path_col_idx]
        
        # 标准化路径
        file_path = os.path.normpath(file_path)
        
        # 打开文件夹
        subprocess.Popen(f'explorer /select,"{file_path}"')

self.file_tree.bind('<Double-Button-1>', on_double_click)
```

### 6.2 单击事件（操作列+预览）

```python
def on_tree_click(event):
    """单击：处理操作列和预览"""
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
        
        # 动态查找操作列位置
        columns = self.config['columns']
        try:
            open_idx = columns.index('open')
            delete_idx = columns.index('delete')
        except ValueError:
            return
        
        open_col = f'#{open_idx + 1}'
        delete_col = f'#{delete_idx + 1}'
        
        if column == open_col:
            self._open_file(file_info)
        elif column == delete_col:
            self._delete_file(file_info, item)
        elif self.config['has_preview']:
            self._show_preview(file_info, idx)

self.file_tree.bind('<Button-1>', on_tree_click)
```

### 6.3 排序事件

```python
def _sort_file_tree(self, tree, column):
    """排序文件列表"""
    items = [(tree.set(k, column), k) for k in tree.get_children('')]
    
    # 根据列类型选择排序方式
    if column == 'size':
        items.sort(key=lambda x: parse_size_to_bytes(x[0]))
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
```

---

## 7. 预览功能

### 7.1 图片预览

```python
def _show_image_preview(self, file_info):
    """显示图片预览"""
    try:
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
        self.preview_label.image = photo  # 保持引用防止垃圾回收
        
    except Exception as e:
        self.preview_label.config(text=f"预览失败: {str(e)[:50]}", foreground='red')
```

### 7.2 视频预览（基础版）

```python
def _show_video_preview(self, file_info, idx):
    """显示视频预览（由调用方重写）"""
    # 基础实现为空，由video_similarity_tab.py重写
    pass
```

### 7.3 视频预览（增强版）

在`video_similarity_tab.py`中重写：

```python
def enhanced_video_preview(file_info, idx):
    """增强版视频预览，支持多帧显示"""
    # 1. 提取关键帧
    frames_data = extract_keyframes(video_path)
    
    # 2. 生成主图和缩略图
    for i, frame in enumerate(frames_data):
        if i == 0:
            # 主图：300x200
            main_photo = resize_frame(frame, (300, 200))
        # 缩略图：80x60
        thumb_photo = resize_frame(frame, (80, 60))
    
    # 3. 显示主图
    main_preview_label.config(image=main_photo)
    
    # 4. 横向排列缩略图
    thumbs_row_frame = ttk.Frame(thumbs_inner_frame)
    thumbs_row_frame.pack(fill=tk.X, padx=5, pady=5)
    
    for frame_data in frames_data:
        thumb_container = ttk.Frame(thumbs_row_frame)
        thumb_container.pack(side=tk.LEFT, padx=3)
        
        thumb_label = ttk.Label(thumb_container, image=frame_data['thumb_photo'])
        thumb_label.pack()
        
        time_label = ttk.Label(thumb_container, text="MM:SS")
        time_label.pack()
        
        # 点击切换主图
        click_handler = make_click_handler(frame_data['main_photo'])
        thumb_label.bind('<Button-1>', click_handler)
```

---

## 8. 工具类

### 8.1 TreeviewTooltip

#### 功能
为Treeview单元格提供鼠标悬停提示，当单元格文本过长时自动显示tooltip。

#### 使用方式
```python
# 创建Treeview后，直接启用tooltip
tree = ttk.Treeview(...)
TreeviewTooltip(tree)  # 一行搞定！
```

#### 触发条件
- 鼠标移动到单元格上
- 单元格文本长度 > 30字符

#### 样式
- 背景色: #ffffe1（淡黄色）
- 边框: 1px solid
- 内边距: (5, 3)
- 最大宽度: 600px（自动换行）

### 8.2 DetailWindowConfig

#### 功能
预定义三种页签的配置常量。

#### 使用方式
```python
from gui_modules.detail_window import DetailWindowConfig

# 直接使用预定义配置
config = DetailWindowConfig.EXACT_MATCH
config = DetailWindowConfig.IMAGE_SIMILARITY
config = DetailWindowConfig.VIDEO_SIMILARITY
```

---

## 9. 辅助函数

### 9.1 文件大小格式化

```python
def format_file_size(size_bytes):
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小(字节)
    
    Returns:
        str: 格式化的大小字符串 (如 "12.5 MB")
    """
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
```

### 9.2 视频时长格式化

```python
def format_duration(seconds):
    """
    格式化视频时长
    
    Args:
        seconds: 时长(秒)
    
    Returns:
        str: 格式化的时长 (如 "15m 23s")
    """
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
```

### 9.3 文件大小解析

```python
def parse_size_to_bytes(size_str):
    """
    解析文件大小字符串为字节数
    
    Args:
        size_str: 格式化的大小字符串 (如 "12.5 MB")
    
    Returns:
        int: 字节数
    """
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
```

---

## 10. 常见问题排查

### 10.1 列宽设置不生效

**问题**: 设置了width但列仍然很宽

**原因**: 没有设置`stretch=False`

**解决**:
```python
# 在配置中确保包含这些列
'no_stretch_columns': {'#0', 'size', 'ext', 'open', 'delete'}

# 或在_create_file_tree中检查
for col, width in self.config['column_widths'].items():
    stretch = col not in self.config.get('no_stretch_columns', set())
    tree.column(col, width=width, anchor=anchor, stretch=stretch)
```

### 10.2 操作列点击错位

**问题**: 点击"打开"无反应，点击"删除"变成打开

**原因**: 列索引计算错误

**解决**:
```python
# 不要硬编码索引
# open_col = '#6'  # ❌ 错误

# 动态查找列位置
columns = self.config['columns']
open_idx = columns.index('open')
open_col = f'#{open_idx + 1}'  # ✅ 正确
```

### 10.3 双击跳转路径错误

**问题**: 双击行跳转到桌面而非文件位置

**原因**: 直接使用原始路径，未标准化

**解决**:
```python
# 从Treeview的values中获取已格式化的路径
values = self.file_tree.item(item, 'values')
path_col_idx = columns.index('path')
file_path = values[path_col_idx]

# 标准化路径
file_path = os.path.normpath(file_path)

subprocess.Popen(f'explorer /select,"{file_path}"')
```

### 10.4 视频预览点击无效

**问题**: 点击缩略图无法切换主图

**原因**: 循环中的闭包问题

**解决**: 使用工厂函数
```python
def make_click_handler(photo):
    def handler(event=None):
        main_preview_label.config(image=photo, text='')
        main_preview_label.image = photo
    return handler

# 使用时
click_handler = make_click_handler(frame_data['main_photo'])
thumb_label.bind('<Button-1>', click_handler)
```

---

## 11. 扩展新页签

### 11.1 步骤

1. **定义配置**
```python
# 在DetailWindowConfig中添加新配置
NEW_FEATURE_CONFIG = {
    'title_prefix': '新特征组',
    'window_size': '1200x600',
    'columns': ('col1', 'col2', 'path', 'open', 'delete'),
    'headings': {...},
    'column_widths': {...},
    'no_stretch_columns': {...},
    'info_label_format': '...',
    'has_preview': True/False,
    'preview_type': 'image'/'video'/None
}
```

2. **创建格式化函数**
```python
def new_feature_formatter(file_info, idx):
    return (value1, value2, path, '打开', '删除')
```

3. **创建工厂函数**
```python
def create_new_feature_detail(parent, group, group_num, main_window=None):
    return FileDetailWindow(
        parent=parent,
        group=group,
        group_num=group_num,
        config=DetailWindowConfig.NEW_FEATURE_CONFIG,
        file_formatter=new_feature_formatter,
        main_window=main_window
    )
```

4. **在页签中使用**
```python
from gui_modules.detail_window import create_new_feature_detail

detail_window_obj = create_new_feature_detail(...)
detail_window_obj.delete_callback = self._delete_single_file
```

### 11.2 注意事项
- 确保`columns`中包含`'path'`, `'open'`, `'delete'`
- `no_stretch_columns`必须包含`'open'`和`'delete'`
- 如果有预览，需要实现对应的`_show_xxx_preview`方法

---

## 12. 最佳实践

### 12.1 代码组织
- 将公共组件放在独立模块（`detail_window.py`）
- 使用配置驱动不同页签的差异
- 格式化函数尽量简洁，只负责数据转换

### 12.2 性能优化
- 缩略图使用缓存（LRU策略）
- 大图片先缩小再显示
- 异步加载耗时操作

### 12.3 可维护性
- 添加详细注释说明配置项含义
- 使用有意义的变量名
- 遵循统一的命名规范

---

*文档版本: v3.0.0*  
*最后更新: 2026-05-26*
