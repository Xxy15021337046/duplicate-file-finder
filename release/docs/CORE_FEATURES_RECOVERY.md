# 核心功能恢复指南

> **用途**: 本文档用于在后续开发导致原有功能出现bug时，快速定位问题并还原三个主要功能（精确匹配、图片相似度、视频相似度）的核心逻辑。
> 
> **最后更新**: 2026-05-25  
> **适用版本**: v2.2.0+

---

## 目录

1. [功能概览](#1-功能概览)
2. [精确匹配功能](#2-精确匹配功能)
3. [图片相似度功能](#3-图片相似度功能)
4. [视频相似度功能](#4-视频相似度功能)
5. [通用交互行为](#5-通用交互行为)
6. [关键代码模式](#6-关键代码模式)
7. [常见问题快速修复](#7-常见问题快速修复)

---

## 1. 功能概览

### 1.1 三个核心功能对比

| 功能 | 文件位置 | 核心算法 | 数据库 | 主要用途 |
|------|---------|---------|--------|---------|
| **精确匹配** | `gui_modules/exact_match_tab.py` | MD5三级哈希 | `file_index.db` | 检测完全相同的文件 |
| **图片相似度** | `gui_modules/similarity_tab.py` | pHash+dHash+直方图 | `image_similarity.db` | 检测相似图片 |
| **视频相似度** | `gui_modules/video_similarity_tab.py` | 关键帧序列匹配 | `video_similarity.db` | 检测相似视频 |

### 1.2 共同特性

所有三个功能都具备以下共同特性：
- ✅ 结果详情窗口展示
- ✅ 双击行打开Windows资源管理器并选中文件
- ✅ 点击"打开"按钮直接运行文件
- ✅ 点击"删除"按钮删除单个文件
- ✅ 列标题点击排序
- ✅ 右键菜单隐藏功能

---

## 2. 精确匹配功能

### 2.1 核心文件

| 文件 | 说明 | 关键类/函数 |
|------|------|------------|
| `core/duplicate_finder.py` | 精确匹配引擎 | `DuplicateFinder` |
| `gui_modules/exact_match_tab.py` | GUI标签页 | `ExactMatchTab`, `_on_double_click_group()`, `_show_group_details()` |

### 2.2 核心算法：三级哈希策略

```python
# 第1级：按文件大小分组
size_groups = defaultdict(list)
for file_info in files:
    size_groups[file_info['size']].append(file_info)

# 第2级：部分哈希（前1MB）
partial_hash = self._calculate_partial_hash(file_path, chunk_size=1048576)

# 第3级：完整哈希（全文件MD5）
full_hash = self._calculate_md5(file_path)
```

### 2.3 关键数据结构

```python
# 重复组结构
{
    'group_id': 1,
    'hash': 'abc123...',           # MD5哈希值
    'size': 1048576,                # 文件大小（字节）
    'count': 3,                     # 文件数量
    'files': [                      # 文件列表
        {
            'path': 'C:\\path\\to\\file1.txt',
            'size': 1048576,
            'modified_time': 1234567890.0
        },
        ...
    ]
}
```

### 2.4 详情窗口实现要点

**方法**: `_on_double_click_group(group)` （实际调用的方法）

**关键代码**:
```python
def _on_double_click_group(self, group):
    """双击结果组显示详情"""
    detail_window = tk.Toplevel(self.frame)
    detail_window.title(f"重复组 - {len(group['files'])}个文件")
    
    # 创建Treeview（4列：序号、路径、打开、删除）
    columns = ('index', 'path', 'open', 'delete')
    file_tree = ttk.Treeview(detail_window, columns=columns, show='tree headings')
    
    file_tree.heading('#0', text='序号', anchor=tk.W)
    file_tree.heading('path', text='文件路径', anchor=tk.W)
    file_tree.heading('open', text='打开', anchor=tk.CENTER)
    file_tree.heading('delete', text='删除', anchor=tk.CENTER)
    
    # 设置列宽
    file_tree.column('#0', width=50, minwidth=40)
    file_tree.column('path', width=310, minwidth=200)
    file_tree.column('open', width=40, minwidth=30)  # 缩小到40px
    file_tree.column('delete', width=40, minwidth=30)  # 缩小到40px
    
    # 插入文件数据
    for idx, file_info in enumerate(group['files'], start=1):
        path = file_info['path']
        if os.name == 'nt':
            path = path.replace('/', '\\')
        file_tree.insert('', tk.END, text=str(idx), values=(path, '打开', '删除'))
    
    # === 关键绑定：双击行打开文件夹 ===
    def on_double_click(event):
        item = file_tree.identify_row(event.y)
        if item:
            idx = int(file_tree.item(item, 'text')) - 1
            if 0 <= idx < len(group['files']):
                file_path = group['files'][idx]['path']
                import subprocess
                subprocess.Popen(f'explorer /select,"{file_path}"')
    
    file_tree.bind('<Double-Button-1>', on_double_click)
    
    # === 关键绑定：点击操作列 ===
    def on_tree_click(event):
        column = file_tree.identify_column(event.x)
        item = file_tree.identify_row(event.y)
        
        if not item:
            return
        
        values = file_tree.item(item, 'values')
        if len(values) < 5:
            return
        
        idx = int(file_tree.item(item, 'text')) - 1
        if 0 <= idx < len(group['files']):
            file_info = group['files'][idx]
            
            if column == '#4':  # 打开列 - 直接运行文件
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
            elif column == '#5':  # 删除列
                self._delete_single_file(file_tree, file_info, item, group, detail_window)
    
    file_tree.bind('<Button-1>', on_tree_click)
```

---

## 3. 图片相似度功能

### 3.1 核心文件

| 文件 | 说明 | 关键类/函数 |
|------|------|------------|
| `core/visual_similarity.py` | 相似度检测引擎 | `ImageSimilarityFinder`, `_compute_image_fingerprint()` |
| `gui_modules/similarity_tab.py` | GUI标签页和结果展示 | `SimilarityTab`, `_show_group_details()` |

### 3.2 核心算法：三级过滤策略

```python
# 第1级：pHash快速筛选（汉明距离≤阈值）
phash_dist = self._hamming_distance(img1[5], img2[5])
if phash_dist > threshold_phash:
    continue

# 第2级：dHash二次验证（仅精确模式）
if mode == "precise":
    dhash_dist = self._hamming_distance(img1[6], img2[6])
    if dhash_dist > threshold_phash:
        continue
    
    # 第3级：颜色直方图精确比对（余弦相似度≥75%）
    if img1[7] and img2[7]:
        hist_sim = self._histogram_similarity(img1[7], img2[7])
        if hist_sim < 0.75:
            continue
    
    # 综合评分：pHash×0.5 + dHash×0.3 + 直方图×0.2
    score = self._compute_similarity_score(phash_dist, dhash_dist, hist_sim)
```

### 3.3 关键数据结构

```python
# 相似组结构
{
    'group_id': 1,
    'avg_similarity': 95.5,        # 平均相似度（百分比）
    'similarity_range': (90.0, 100.0),  # 相似度范围
    'count': 4,                     # 图片数量
    'total_size': 4194304,          # 总大小（字节）
    'files': [                      # 文件列表
        {
            'path': 'C:\\path\\to\\image1.jpg',
            'width': 1920,
            'height': 1080,
            'size': 1048576,
            'phash': 'a1b2c3d4e5f6...',
            'dhash': 'f6e5d4c3b2a1...',
            'histogram': b'...'
        },
        ...
    ]
}
```

### 3.4 详情窗口实现要点

**方法**: `_show_group_details(group)`

**关键代码**:
```python
def _show_group_details(self, group):
    """显示相似组详情和图片预览"""
    detail_window = tk.Toplevel(self.results_window)
    detail_window.title(f"相似组 - {len(group['files'])}张图片")
    
    # 创建Treeview（5列：分辨率、大小、路径、打开、删除）
    columns = ('resolution', 'size', 'path', 'open', 'delete')
    file_tree = ttk.Treeview(detail_window, columns=columns, show='tree headings')
    
    file_tree.heading('#0', text='序号', anchor=tk.W)
    file_tree.heading('resolution', text='分辨率', anchor=tk.CENTER)
    file_tree.heading('size', text='大小', anchor=tk.CENTER)
    file_tree.heading('path', text='文件路径', anchor=tk.W)
    file_tree.heading('open', text='打开', anchor=tk.CENTER)
    file_tree.heading('delete', text='删除', anchor=tk.CENTER)
    
    # 设置列宽
    file_tree.column('#0', width=50, minwidth=40)
    file_tree.column('resolution', width=100, minwidth=80)
    file_tree.column('size', width=80, minwidth=60)
    file_tree.column('path', width=300, minwidth=200)
    file_tree.column('open', width=40, minwidth=30)  # 缩小到40px
    file_tree.column('delete', width=40, minwidth=30)  # 缩小到40px
    
    # 插入文件数据
    for idx, file_info in enumerate(group['files'], start=1):
        resolution = f"{file_info['width']}x{file_info['height']}"
        size = self._format_size(self._get_file_size(file_info['path']))
        path = file_info['path']
        
        # 确保路径使用Windows标准格式（统一使用反斜杠）
        if os.name == 'nt':
            path = path.replace('/', '\\')
        
        file_tree.insert('', tk.END, text=str(idx), values=(resolution, size, path, '打开', '删除'))
    
    # === 关键绑定：双击行打开文件夹 ===
    def on_double_click(event):
        item = file_tree.identify_row(event.y)
        if item:
            values = file_tree.item(item, 'values')
            if len(values) >= 5:
                file_path = values[2]  # 从Treeview获取路径（已经格式化）
                import subprocess
                import os as os_module
                # 标准化路径
                file_path = os_module.path.normpath(file_path)
                subprocess.Popen(f'explorer /select,"{file_path}"')
    
    file_tree.bind('<Double-Button-1>', on_double_click)
    
    # === 关键绑定：点击操作列 ===
    def on_tree_click(event):
        column = file_tree.identify_column(event.x)
        item = file_tree.identify_row(event.y)
        
        if not item:
            return
        
        values = file_tree.item(item, 'values')
        if len(values) < 5:
            return
        
        # 获取文件信息
        file_path = values[2]
        for file_info in group['files']:
            import os as os_module
            if os_module.path.normpath(file_info['path']) == os_module.path.normpath(file_path):
                if column == '#4':  # 打开列 - 直接运行文件
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
                elif column == '#5':  # 删除列
                    self._delete_single_file(file_tree, file_info, item, group, detail_window)
                break
    
    file_tree.bind('<Button-1>', on_tree_click)
```

### 3.5 图片预览功能

**懒加载机制**:
```python
# 绑定选中事件（点击行显示预览）
file_tree.bind('<<TreeviewSelect>>', 
              lambda e: self._on_file_select(file_tree, preview_label, thumbnail_cache))

def _on_file_select(self, tree, preview_label, thumbnail_cache):
    """当用户选中Treeview中的某一行时，显示图片预览"""
    selection = tree.selection()
    if not selection:
        return
    
    values = tree.item(selection[0], 'values')
    if len(values) >= 3:
        file_path = values[2]
        
        # 检查缓存中是否已有缩略图
        if file_path in thumbnail_cache:
            preview_label.config(image=thumbnail_cache[file_path])
            return
        
        # 异步加载缩略图（避免界面卡顿）
        threading.Thread(
            target=self._load_thumbnail_async,
            args=(file_path, preview_label, thumbnail_cache),
            daemon=True
        ).start()
```

---

## 4. 视频相似度功能

### 4.1 核心文件

| 文件 | 说明 | 关键类/函数 |
|------|------|------------|
| `core/video_similarity.py` | 视频相似度引擎 | `VideoSimilarityFinder`, `_compute_video_fingerprint()` |
| `gui_modules/video_similarity_tab.py` | GUI标签页和结果展示 | `VideoSimilarityTab`, `_show_group_details()` |

### 4.2 核心算法：关键帧序列匹配

```python
# 动态采样策略：根据视频时长确定关键帧数量
def calculate_sample_frames(duration_seconds: float) -> int:
    if duration_seconds < 10:
        return 5          # 短视频：5帧
    elif duration_seconds < 60:
        return 10         # 中短视频：10帧
    elif duration_seconds < 300:
        return 20         # 中长视频：20帧
    else:
        return min(50, int(duration_seconds / 60))  # 长视频：最多50帧

# 滑动窗口匹配
window_size = 5
for i in range(len(hashes_a) - window_size + 1):
    window_a = hashes_a[i:i + window_size]
    for j in range(len(hashes_b) - window_size + 1):
        window_b = hashes_b[j:j + window_size]
        # 计算窗口内帧的相似度
        match_count = sum(1 for ha, hb in zip(window_a, window_b) 
                         if imagehash.hex_to_hash(ha) - imagehash.hex_to_hash(hb) <= 10)
        if match_count >= 3:
            return True
```

### 4.3 关键数据结构

```python
# 相似视频组结构
{
    'group_id': 1,
    'avg_similarity': 85.5,        # 平均相似度（百分比）
    'similarity_range': (80.0, 90.0),  # 相似度范围
    'count': 2,                     # 视频数量
    'total_size': 104857600,        # 总大小（字节）
    'files': [                      # 文件列表
        {
            'path': 'C:\\path\\to\\video1.mp4',
            'duration': 120.5,      # 时长（秒）
            'width': 1920,
            'height': 1080,
            'fps': 30.0,
            'size': 52428800,
            'frame_hashes': ['a1b2...', 'c3d4...', ...]  # 关键帧哈希列表
        },
        ...
    ]
}
```

### 4.4 详情窗口实现要点

**方法**: `_show_group_details(group)`

**关键代码**:
```python
def _show_group_details(self, group):
    """显示相似视频组详情和多帧预览"""
    detail_window = tk.Toplevel(self.results_window)
    detail_window.title(f"相似视频组 - {len(group['files'])}个视频")
    
    # 创建Treeview（7列：时长、分辨率、FPS、大小、路径、打开、删除）
    columns = ('duration', 'resolution', 'fps', 'size', 'path', 'open', 'delete')
    file_tree = ttk.Treeview(detail_window, columns=columns, show='tree headings')
    
    file_tree.heading('#0', text='序号', anchor=tk.W)
    file_tree.heading('duration', text='时长', anchor=tk.CENTER)
    file_tree.heading('resolution', text='分辨率', anchor=tk.CENTER)
    file_tree.heading('fps', text='FPS', anchor=tk.CENTER)
    file_tree.heading('size', text='大小', anchor=tk.CENTER)
    file_tree.heading('path', text='文件路径', anchor=tk.W)
    file_tree.heading('open', text='打开', anchor=tk.CENTER)
    file_tree.heading('delete', text='删除', anchor=tk.CENTER)
    
    # 设置列宽
    file_tree.column('#0', width=50, minwidth=40)
    file_tree.column('duration', width=80, minwidth=60)
    file_tree.column('resolution', width=100, minwidth=80)
    file_tree.column('fps', width=60, minwidth=50)
    file_tree.column('size', width=80, minwidth=60)
    file_tree.column('path', width=250, minwidth=200)
    file_tree.column('open', width=40, minwidth=30)  # 缩小到40px
    file_tree.column('delete', width=40, minwidth=30)  # 缩小到40px
    
    # 插入文件数据
    for idx, file_info in enumerate(group['files'], start=1):
        duration = self._format_duration(file_info['duration'])
        resolution = f"{file_info['width']}x{file_info['height']}"
        fps = f"{file_info['fps']:.1f}"
        size = self._format_size(file_info['size'])
        path = file_info['path']
        
        # 确保路径使用Windows标准格式
        if os.name == 'nt':
            path = path.replace('/', '\\')
        
        file_tree.insert('', tk.END, text=str(idx), 
                        values=(duration, resolution, fps, size, path, '打开', '删除'))
    
    # === 关键绑定：双击行打开文件夹 ===
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
    
    # 点击行显示多帧预览
    file_tree.bind('<ButtonRelease-1>', 
                  lambda e: self._on_video_select_multiframe(
                      file_tree, main_preview_label, thumbs_inner_frame, 
                      thumbnail_cache, max_cached_videos, max_frames_per_video
                  ))
    
    # === 关键绑定：点击操作列 ===
    def on_tree_click(event):
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
```

### 4.5 多帧预览功能

**懒加载+缓存机制**:
```python
def _on_video_select_multiframe(self, file_tree, main_preview_label, thumbs_frame, 
                                 thumbnail_cache, max_cached_videos, max_frames_per_video):
    """点击视频行显示多帧预览（最多5帧）"""
    selection = file_tree.selection()
    if not selection:
        return
    
    values = file_tree.item(selection[0], 'values')
    file_path = values[4]
    
    # 检查缓存
    if file_path in thumbnail_cache:
        # 显示缓存的缩略图
        self._display_thumbnails(thumbs_frame, thumbnail_cache[file_path])
        return
    
    # 异步提取关键帧
    threading.Thread(
        target=self._extract_video_frames_async,
        args=(file_path, thumbs_frame, thumbnail_cache, max_frames_per_video),
        daemon=True
    ).start()
```

---

## 5. 通用交互行为

### 5.1 双击行行为（所有三个页签）

**行为**: 使用Windows资源管理器打开文件所在文件夹，并选中该文件

**实现**:
```python
def on_double_click(event):
    item = file_tree.identify_row(event.y)
    if item:
        # 从Treeview的values中获取路径（确保与显示的路径一致）
        values = file_tree.item(item, 'values')
        if len(values) >= N:  # N取决于列数
            file_path = values[COLUMN_INDEX]  # 根据具体页签调整索引
            import subprocess
            import os as os_module
            # 标准化路径（处理各种路径格式）
            file_path = os_module.path.normpath(file_path)
            subprocess.Popen(f'explorer /select,"{file_path}"')

file_tree.bind('<Double-Button-1>', on_double_click)
```

**关键点**:
1. ✅ 从Treeview的values数组获取路径，而不是从group字典
2. ✅ 使用`os.path.normpath()`标准化路径
3. ✅ 使用`explorer /select,"路径"`命令
4. ✅ 验证values数组长度，避免索引越界

### 5.2 点击"打开"按钮行为（所有三个页签）

**行为**: 直接运行/打开文件（使用系统默认程序）

**实现**:
```python
if column == '#OPEN_COLUMN':  # 打开列
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
```

**关键点**:
1. ✅ 跨平台支持（Windows/macOS/Linux）
2. ✅ 使用`start "" "路径"`命令（Windows）
3. ✅ 异常处理，显示友好错误提示

### 5.3 点击"删除"按钮行为（所有三个页签）

**行为**: 弹出确认对话框，确认后1秒后自动删除文件

**实现**:
```python
elif column == '#DELETE_COLUMN':  # 删除列
    self._delete_single_file(file_tree, file_info, item, group, detail_window)

def _delete_single_file(self, file_tree, file_info, item, group, parent_window):
    """删除单个文件（批处理延迟删除）"""
    import os
    import subprocess
    import tempfile
    from tkinter import messagebox
    
    file_path = file_info['path']
    
    # 确认删除
    if not messagebox.askyesno("确认删除", f"确定要删除此文件吗？\n\n{file_path}"):
        return
    
    try:
        # 使用批处理延迟删除（解决OpenCV占用问题）
        temp_dir = tempfile.gettempdir()
        bat_path = os.path.join(temp_dir, f"delete_{os.path.basename(file_path)}.bat")
        
        with open(bat_path, 'w', encoding='gbk') as bat_file:
            bat_file.write(f"@echo off\n")
            bat_file.write(f"timeout /t 1 /nobreak >nul\n")
            bat_file.write(f'del /f /q "{file_path}"\n')
            bat_file.write(f'del "%~f0"\n')  # 自删除
        
        # 异步执行批处理（不阻塞主程序）
        subprocess.Popen(bat_path, shell=True)
        
        # 从Treeview中移除
        file_tree.delete(item)
        
        # 清除缓存（如果有）
        if hasattr(self.main_window, '_video_thumbnail_cache'):
            cache = self.main_window._video_thumbnail_cache
            if file_path in cache:
                del cache[file_path]
        
    except Exception as e:
        messagebox.showerror("错误", f"删除失败:\n{str(e)}")
```

**关键点**:
1. ✅ 使用批处理延迟删除（解决文件占用问题）
2. ✅ 异步执行，不阻塞主程序
3. ✅ 批处理文件自删除
4. ✅ 清除相关缓存
5. ✅ 从Treeview中立即移除条目

---

## 6. 关键代码模式

### 6.1 路径处理规范

**问题**: Windows路径可能包含正斜杠或反斜杠，导致匹配失败

**解决方案**:
```python
import os

# 统一转换为反斜杠（Windows）
if os.name == 'nt':
    path = path.replace('/', '\\')

# 标准化路径（处理相对路径、多余斜杠等）
normalized_path = os.path.normpath(path)

# 比较时使用标准化路径
if os_module.path.normpath(file_info['path']) == os_module.path.normpath(file_path):
    # 路径匹配
```

### 6.2 Treeview多列定义

**标准模式**:
```python
# 定义列
columns = ('col1', 'col2', 'col3', 'action_open', 'action_delete')
file_tree = ttk.Treeview(parent, columns=columns, show='tree headings')

# 设置表头
file_tree.heading('#0', text='序号', anchor=tk.W)
file_tree.heading('col1', text='列1', anchor=tk.CENTER)
file_tree.heading('action_open', text='打开', anchor=tk.CENTER)
file_tree.heading('action_delete', text='删除', anchor=tk.CENTER)

# 设置列宽（操作列缩小到40px）
file_tree.column('#0', width=50, minwidth=40)
file_tree.column('col1', width=XXX, minwidth=YYY)
file_tree.column('action_open', width=40, minwidth=30)
file_tree.column('action_delete', width=40, minwidth=30)
```

### 6.3 事件绑定优先级

**重要**: 不同事件的绑定顺序和冲突处理

```python
# 1. 双击事件（最高优先级）
file_tree.bind('<Double-Button-1>', on_double_click)

# 2. 选中事件（次优先级，用于预览）
file_tree.bind('<<TreeviewSelect>>', on_select)

# 3. 单击释放事件（用于视频预览）
file_tree.bind('<ButtonRelease-1>', on_release)

# 4. 单击事件（最低优先级，用于操作列）
file_tree.bind('<Button-1>', on_tree_click)
```

**注意**: 
- `<Button-1>` 和 `<ButtonRelease-1>` 可能冲突，选择一个使用
- 双击事件中不要处理操作列点击，避免冲突

### 6.4 懒加载+缓存模式

**标准模式**:
```python
# 缓存字典
thumbnail_cache = {}

def load_data_async(key, preview_widget, cache):
    """异步加载数据（懒加载）"""
    # 检查缓存
    if key in cache:
        preview_widget.config(image=cache[key])
        return
    
    # 异步加载
    threading.Thread(
        target=_do_load,
        args=(key, preview_widget, cache),
        daemon=True
    ).start()

def _do_load(key, preview_widget, cache):
    """实际加载逻辑"""
    try:
        # 加载数据...
        result = load_from_disk(key)
        
        # 存入缓存
        cache[key] = result
        
        # 更新UI（需要在主线程）
        preview_widget.after(0, lambda: preview_widget.config(image=result))
    except Exception as e:
        print(f"加载失败: {e}")
```

### 6.5 跨平台文件打开

**标准模式**:
```python
import subprocess
import sys

def open_file(file_path):
    """跨平台打开文件"""
    try:
        if sys.platform == 'win32':
            # Windows: 使用start命令
            subprocess.Popen(['start', '', file_path], shell=True)
        elif sys.platform == 'darwin':
            # macOS: 使用open命令
            subprocess.Popen(['open', file_path])
        else:
            # Linux: 使用xdg-open
            subprocess.Popen(['xdg-open', file_path])
    except Exception as e:
        raise Exception(f"无法打开文件: {str(e)}")
```

---

## 7. 常见问题快速修复

### 7.1 双击行无法打开文件夹

**症状**: 双击结果行，没有反应或打开错误的文件夹

**排查步骤**:
1. 检查路径格式
   ```python
   print(f"[DEBUG] File path: {file_path}")
   print(f"[DEBUG] Path exists: {os.path.exists(file_path)}")
   ```

2. 检查事件绑定
   ```python
   # 确认已绑定双击事件
   print(f"[DEBUG] Bindings: {file_tree.bind()}")
   ```

3. 检查values数组长度
   ```python
   values = file_tree.item(item, 'values')
   print(f"[DEBUG] Values length: {len(values)}")
   print(f"[DEBUG] Values: {values}")
   ```

**解决方案**:
- ✅ 从Treeview的values数组获取路径，而不是group字典
- ✅ 使用`os.path.normpath()`标准化路径
- ✅ 验证values数组长度
- ✅ 确保使用`explorer /select,"路径"`格式

### 7.2 点击"打开"无反应

**症状**: 点击"打开"文本，文件没有打开

**排查步骤**:
1. 检查列号是否正确
   ```python
   print(f"[DEBUG] Clicked column: {column}")
   ```

2. 检查文件路径
   ```python
   print(f"[DEBUG] File path: {file_info['path']}")
   print(f"[DEBUG] File exists: {os.path.exists(file_info['path'])}")
   ```

**解决方案**:
- ✅ 确认列号正确（图片=#4，视频=#6，精确匹配=#4）
- ✅ 使用跨平台的文件打开方式
- ✅ 添加异常处理，显示错误提示

### 7.3 点击"删除"无效

**症状**: 点击"删除"文本，文件没有被删除

**排查步骤**:
1. 检查路径匹配
   ```python
   for file_info in group['files']:
       normalized_tree_path = os.path.normpath(file_path)
       normalized_group_path = os.path.normpath(file_info['path'])
       print(f"[DEBUG] Tree path: {normalized_tree_path}")
       print(f"[DEBUG] Group path: {normalized_group_path}")
       print(f"[DEBUG] Match: {normalized_tree_path == normalized_group_path}")
   ```

2. 检查文件占用
   ```python
   try:
       os.remove(file_path)
   except PermissionError as e:
       print(f"[ERROR] File is locked: {e}")
   ```

**解决方案**:
- ✅ 使用`os.path.normpath()`标准化路径后再比较
- ✅ 使用批处理延迟删除（解决文件占用问题）
- ✅ 异步执行批处理，不阻塞主程序

### 7.4 图片/视频预览不显示

**症状**: 点击行，预览区域无变化

**排查步骤**:
1. 检查事件绑定
   ```python
   print(f"[DEBUG] TreeviewSelect binding: {'<<TreeviewSelect>>' in file_tree.bind()}")
   ```

2. 检查缓存
   ```python
   print(f"[DEBUG] Cache keys: {list(thumbnail_cache.keys())}")
   print(f"[DEBUG] File in cache: {file_path in thumbnail_cache}")
   ```

3. 检查异步加载
   ```python
   # 在_load_thumbnail_async中添加调试输出
   print(f"[DEBUG] Loading thumbnail for: {file_path}")
   print(f"[DEBUG] File exists: {os.path.exists(file_path)}")
   ```

**解决方案**:
- ✅ 确认事件绑定正确
- ✅ 检查PIL/Pillow是否安装（图片预览）
- ✅ 检查OpenCV是否安装（视频预览）
- ✅ 确认缓存键正确

### 7.5 列排序不生效

**症状**: 点击列标题，数据不排序或排序错误

**排查步骤**:
1. 检查heading是否绑定command
   ```python
   # 确认heading中有command参数
   file_tree.heading('column_name', text='列名', command=lambda: sort_function('column_name'))
   ```

2. 检查数据解析
   ```python
   # 确认正确解析百分比、数字、大小
   if column == 'similarity':
       items.sort(key=lambda x: float(x[0].replace('%', '')))
   elif column == 'count':
       items.sort(key=lambda x: int(x[0].replace('张', '').strip()))
   elif column == 'size':
       items.sort(key=lambda x: parse_size_to_bytes(x[0]))
   ```

**解决方案**:
- ✅ 在heading()中添加command参数
- ✅ 正确处理数据格式（百分比、单位等）
- ✅ 记录上次排序的列和方向

### 7.6 路径格式不匹配

**症状**: Treeview中的路径与group中的路径不一致，导致找不到文件

**原因**: 
- Treeview中存储的路径经过格式化（反斜杠）
- group中存储的路径可能是原始路径（混合斜杠）

**解决方案**:
```python
# 统一使用os.path.normpath()进行比较
import os as os_module

for file_info in group['files']:
    if os_module.path.normpath(file_info['path']) == os_module.path.normpath(file_path):
        # 找到匹配的文件
        break
```

### 7.7 多进程模块导入错误

**症状**: `[ERROR] 处理失败 ... ModuleNotFoundError: No module named 'XXX'`

**原因**: 多进程子进程使用不同的Python环境，缺少依赖库

**解决方案**:
```python
def _compute_fingerprint(file_path: str):
    """全局函数，用于多进程"""
    try:
        # 确保在多进程环境中也能正确导入模块
        import sys
        import os
        # 添加项目根目录到Python路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # 导入依赖
        import dependency_module
        # ... 其余代码
    except Exception as e:
        print(f"[ERROR] 处理失败: {e}")
        return None
```

---

## 8. 测试验证清单

### 8.1 精确匹配功能测试

- [ ] 完全相同文件检测（MD5一致）
- [ ] 大文件检测（>1GB）
- [ ] 小文件检测（<1KB）
- [ ] 增量扫描功能
- [ ] 多线程并行处理
- [ ] 结果导出JSON
- [ ] 双击行打开文件夹并选中文件
- [ ] 点击"打开"直接运行文件
- [ ] 点击"删除"成功删除文件
- [ ] 路径跳转功能

### 8.2 图片相似度功能测试

- [ ] 相同图片检测（相似度100%）
- [ ] 不同尺寸相同内容检测（相似度≥95%）
- [ ] 不同图片排除（相似度<50%）
- [ ] 快速模式 vs 精确模式对比
- [ ] 增量扫描功能
- [ ] 历史数据恢复功能
- [ ] 图片预览功能（懒加载、缓存、异步）
- [ ] 列标题排序功能
- [ ] 筛选功能（后缀、大小）
- [ ] 隐藏功能（右键菜单）
- [ ] 双击行打开文件夹并选中文件
- [ ] 点击"打开"直接运行文件
- [ ] 点击"删除"成功删除文件

### 8.3 视频相似度功能测试

- [ ] 相同视频检测（相似度100%）
- [ ] 转码视频检测（不同编码格式）
- [ ] 剪辑视频检测（片段相似）
- [ ] 调色视频检测（亮度/对比度变化）
- [ ] 动态采样帧数功能
- [ ] 滑动窗口匹配算法
- [ ] 多帧预览功能（最多5帧）
- [ ] 多进程并行计算
- [ ] 增量扫描功能
- [ ] 双击行打开文件夹并选中文件
- [ ] 点击"打开"直接运行文件
- [ ] 点击"删除"成功删除文件

### 8.4 通用交互测试

- [ ] 三个页签的双击行行为一致
- [ ] 三个页签的"打开"按钮行为一致
- [ ] 三个页签的"删除"按钮行为一致
- [ ] 列宽调整到合适宽度（操作列40px）
- [ ] 路径格式统一（Windows反斜杠）
- [ ] 异常处理完善（显示友好错误提示）
- [ ] 缓存清理正确（删除文件后清除缓存）

---

## 9. 回滚操作

### 9.1 Git回滚

**回退到指定提交**:
```bash
# 查看提交历史
git log --oneline

# 回退到某个提交（保留工作区修改）
git reset --soft <commit-hash>

# 回退到某个提交（丢弃所有修改）
git reset --hard <commit-hash>

# 回退到远程仓库的最新状态
git fetch origin
git reset --hard origin/main
```

**重要提交记录**:
- `TODO` - 添加本次修改的提交记录

### 9.2 文件备份

**备份关键文件**:
```bash
# 创建备份目录
mkdir backup_20260525

# 备份核心文件
cp gui_modules/exact_match_tab.py backup_20260525/
cp gui_modules/similarity_tab.py backup_20260525/
cp gui_modules/video_similarity_tab.py backup_20260525/
```

**恢复备份**:
```bash
# 恢复单个文件
cp backup_20260525/exact_match_tab.py gui_modules/

# 恢复整个模块
rm gui_modules/*.py
cp backup_20260525/*.py gui_modules/
```

---

## 10. 联系与支持

如遇无法解决的问题，请：

1. **查看日志**: 运行日志区域显示详细错误信息
2. **查阅文档**: 
   - [功能恢复指南](FUNCTION_RECOVERY_GUIDE.md)
   - [图片相似度检测指南](SIMILARITY_DETECTION_GUIDE.md)
   - [视频相似度检测指南](VIDEO_SIMILARITY_GUIDE.md)
   - [README.md](../README.md)
3. **Git历史**: 查看提交记录和变更说明
4. **GitHub Issues**: [项目地址](https://github.com/Xxy15021337046/duplicate-file-finder)

---

**文档版本**: v1.0.0  
**创建日期**: 2026-05-25  
**维护者**: Qoder AI Assistant
