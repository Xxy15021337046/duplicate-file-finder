# 功能恢复指南

本文档用于在后续开发导致原有功能出现bug时，快速定位问题并还原功能。

## 目录

1. [相似度检测功能](#1-相似度检测功能)
2. [精确匹配功能](#2-精确匹配功能)
3. [GUI界面功能](#3-gui界面功能)
4. [数据库结构](#4-数据库结构)
5. [关键算法](#5-关键算法)
6. [常见问题排查流程](#6-常见问题排查流程)

---

## 1. 相似度检测功能

### 1.1 核心文件

| 文件 | 说明 | 关键类/函数 |
|------|------|------------|
| `core/visual_similarity.py` | 相似度检测引擎 | `ImageSimilarityFinder`, `_compute_image_fingerprint()` |
| `gui_modules/similarity_tab.py` | GUI标签页和结果展示 | `SimilarityTab`, `_show_group_details()` |

### 1.2 功能清单

#### ✅ 必须保留的核心功能

1. **三级过滤策略**
   - pHash快速筛选（汉明距离≤阈值）
   - dHash二次验证（仅精确模式）
   - 颜色直方图精确比对（余弦相似度≥75%）
   - 综合评分：pHash×0.5 + dHash×0.3 + 直方图×0.2

2. **多进程并行计算**
   - 使用`ProcessPoolExecutor`
   - 自动检测CPU核心数（最多8个进程）
   - 全局函数`_compute_image_fingerprint()`避免传递self对象

3. **数据库索引管理**
   - SQLite3存储图片指纹
   - 增量扫描支持（保留已有数据）
   - 批量插入（1000条/批）

4. **结果展示与交互**
   - 结果窗口显示相似组列表
   - 详情窗口显示文件列表和图片预览
   - 列标题点击排序（相似度、数量、大小）
   - 筛选功能（后缀、大小范围）
   - 隐藏功能（右键菜单）

5. **图片预览功能**
   - 懒加载机制（点击时才加载）
   - 缩略图缓存（内存字典）
   - 异步加载（后台线程）
   - 自适应缩放（最大280x400像素）

6. **历史数据恢复**
   - 重启后从数据库提取目录
   - 自动重新执行检测
   - 无需用户手动添加目录

### 1.3 关键代码片段

#### 三级过滤核心逻辑

```python
# 位置: core/visual_similarity.py -> find_similar_groups()

# 第1级：pHash快速筛选
phash_dist = self._hamming_distance(img1[5], img2[5])
if phash_dist > threshold_phash:
    continue

# 第2级：dHash二次验证（仅精确模式）
if mode == "precise":
    dhash_dist = self._hamming_distance(img1[6], img2[6])
    if dhash_dist > threshold_phash:
        continue
    
    # 第3级：直方图精确比对
    if img1[7] and img2[7]:
        hist_sim = self._histogram_similarity(img1[7], img2[7])
        if hist_sim < 0.75:  # 相似度低于75%排除
            continue
    
    # 计算综合相似度
    score = self._compute_similarity_score(phash_dist, dhash_dist, hist_sim)
```

#### 多进程计算指纹

```python
# 位置: core/visual_similarity.py -> build_index()

# 多进程并行计算指纹（使用全局函数，避免传递包含Tkinter对象的self）
with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
    futures = {
        executor.submit(_compute_image_fingerprint, img['path']): img
        for img in images
    }
    
    for future in as_completed(futures):
        result = future.result()
        if result:
            batch.append(result)
```

#### 图片预览懒加载

```python
# 位置: gui_modules/similarity_tab.py -> _on_file_select()

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

#### 历史数据恢复

```python
# 位置: gui_modules/similarity_tab.py -> _show_results_window()

if not self.current_groups:
    db_path = self.db_path_var.get()
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM image_index")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # 从路径中提取唯一的根目录
                cursor = conn.execute("SELECT DISTINCT path FROM image_index")
                paths = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                directories = set()
                for path in paths:
                    parent = os.path.dirname(path)
                    while parent and not os.path.exists(parent):
                        parent = os.path.dirname(parent)
                    if parent and os.path.exists(parent):
                        directories.add(parent)
                
                if directories:
                    temp_directories = list(directories)
                    thread = threading.Thread(
                        target=self._run_scan_with_directories,
                        args=(temp_directories,),
                        daemon=True
                    )
                    thread.start()
                    return
```

### 1.4 依赖库版本

```bash
Pillow>=9.0.0      # 图片处理
imagehash>=4.3.0   # 感知哈希算法
numpy>=1.21.0      # 数值计算（imagehash依赖）
```

### 1.5 测试用例

**测试相同图片检测**:
```bash
# 准备两个完全相同的图片文件
# 运行相似度检测，阈值设为12
# 预期结果：相似度100%，汉明距离0
```

**测试不同尺寸相同内容**:
```bash
# 准备同一图片的不同尺寸版本（如100x100和200x200）
# 运行相似度检测
# 预期结果：相似度≥95%（pHash抗缩放）
```

**测试历史数据恢复**:
```bash
# 1. 执行一次完整检测
# 2. 重启程序
# 3. 不添加任何目录，直接点击"结果"
# 4. 预期：自动从数据库提取目录并重新检测，显示相同结果
```

---

## 2. 精确匹配功能

### 2.1 核心文件

| 文件 | 说明 | 关键类/函数 |
|------|------|------------|
| `core/duplicate_finder.py` | 精确匹配引擎 | `DuplicateFinder` |
| `gui_modules/exact_match_tab.py` | GUI标签页 | `ExactMatchTab` |

### 2.2 功能清单

#### ✅ 必须保留的核心功能

1. **三级哈希策略**
   - 文件大小初步分组
   - 部分哈希（前1MB MD5）快速筛选
   - 完整哈希（全文件MD5）精确验证

2. **多线程并行处理**
   - 自动检测CPU核心数×2
   - 最多16线程
   - I/O密集型优化

3. **SQLite3数据库**
   - WAL模式提高并发性能
   - 批量插入（5000条/批）
   - 增量扫描支持

4. **结果展示**
   - 重复组列表
   - 文件跳转（双击打开文件夹）
   - 右键隐藏功能
   - 筛选和排序

### 2.3 关键代码片段

#### 三级哈希核心逻辑

```python
# 位置: core/duplicate_finder.py

# 第1级：按文件大小分组
size_groups = defaultdict(list)
for file_info in files:
    size_groups[file_info['size']].append(file_info)

# 第2级：部分哈希（前1MB）
partial_hash = self._calculate_partial_hash(file_path, chunk_size=1048576)

# 第3级：完整哈希
full_hash = self._calculate_md5(file_path)
```

---

## 3. GUI界面功能

### 3.1 主窗口结构

```
MainWindow (gui_modules/main_window.py)
├── 扫描目录区域
│   ├── 目录列表框
│   └── 添加/移除/清空按钮
├── 标签页区域
│   ├── 精确匹配标签页
│   │   ├── 检测设置
│   │   ├── 开始/停止按钮
│   │   └── 运行日志
│   └── 相似度检测标签页
│       ├── 检测设置（阈值、模式、扫描方式）
│       ├── 图片格式选择
│       ├── 开始/停止/结果按钮
│       └── 运行日志
── 状态栏
```

### 3.2 关键事件绑定

```python
# 相似度检测结果窗口事件绑定
self.results_tree.bind('<Double-Button-1>', self._on_double_click_group)  # 双击打开详情
self.results_tree.bind('<Button-3>', self._show_context_menu)              # 右键菜单
self.results_tree.bind('<ButtonRelease-1>', self._on_click_actions_column) # 点击隐藏按钮

# 详情窗口事件绑定
file_tree.bind('<Double-Button-1>', lambda e: self._open_file_from_detail(file_tree))  # 双击打开文件夹
file_tree.bind('<<TreeviewSelect>>', lambda e: self._on_file_select(...))              # 选中行显示预览
```

### 3.3 路径处理规范

**Windows路径统一使用反斜杠**:
```python
# 确保路径使用Windows标准格式（统一使用反斜杠）
if os.name == 'nt':
    path = path.replace('/', '\\')
```

**打开资源管理器选中文件**:
```python
# 使用列表形式避免shell转义问题
cmd = ['explorer', '/select,', file_path]
subprocess.run(cmd, shell=False)
```

---

## 4. 数据库结构

### 4.1 相似度检测数据库

**表名**: `image_index`

```sql
CREATE TABLE IF NOT EXISTS image_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,        -- 文件完整路径
    size INTEGER NOT NULL,            -- 文件大小(字节)
    width INTEGER,                    -- 图片宽度
    height INTEGER,                   -- 图片高度
    phash TEXT NOT NULL,              -- pHash指纹(16位十六进制)
    dhash TEXT NOT NULL,              -- dHash指纹(16位十六进制)
    histogram BLOB,                   -- 颜色直方图(768字节)
    modified_time REAL,               -- 最后修改时间
    processed_at TIMESTAMP            -- 处理时间
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_phash ON image_index(phash);
CREATE INDEX IF NOT EXISTS idx_dhash ON image_index(dhash);
CREATE INDEX IF NOT EXISTS idx_size ON image_index(size);
CREATE INDEX IF NOT EXISTS idx_path ON image_index(path);
```

**表名**: `similarity_groups`（预留，当前未使用）

```sql
CREATE TABLE IF NOT EXISTS similarity_groups (
    group_id INTEGER,
    image_id INTEGER,
    similarity_score REAL,
    is_representative BOOLEAN DEFAULT 0,
    FOREIGN KEY (image_id) REFERENCES image_index(id)
);
```

### 4.2 精确匹配数据库

**表名**: `file_index`

```sql
CREATE TABLE IF NOT EXISTS file_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    size INTEGER NOT NULL,
    partial_hash TEXT,
    full_hash TEXT,
    modified_time REAL,
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_size ON file_index(size);
CREATE INDEX IF NOT EXISTS idx_partial_hash ON file_index(partial_hash);
CREATE INDEX IF NOT EXISTS idx_full_hash ON file_index(full_hash);
```

---

## 5. 关键算法

### 5.1 汉明距离计算

```python
@staticmethod
def _hamming_distance(hash1: str, hash2: str) -> int:
    """
    计算两个十六进制哈希的汉明距离
    
    Args:
        hash1: 第一个哈希（16位十六进制字符串）
        hash2: 第二个哈希（16位十六进制字符串）
    
    Returns:
        汉明距离（0-64）
    """
    h1 = int(hash1, 16)
    h2 = int(hash2, 16)
    xor = h1 ^ h2
    return bin(xor).count('1')
```

### 5.2 颜色直方图相似度

```python
@staticmethod
def _histogram_similarity(hist1: bytes, hist2: bytes) -> float:
    """
    计算两个直方图的相似度（余弦相似度）
    
    Args:
        hist1: 第一个直方图（768字节）
        hist2: 第二个直方图（768字节）
    
    Returns:
        相似度分数（0-1）
    """
    import math
    
    # 解包为整数列表
    h1 = struct.unpack('768I', hist1)
    h2 = struct.unpack('768I', hist2)
    
    # 计算余弦相似度
    dot_product = sum(a * b for a, b in zip(h1, h2))
    norm1 = math.sqrt(sum(a * a for a in h1))
    norm2 = math.sqrt(sum(b * b for b in h2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)
```

### 5.3 综合相似度评分

```python
def _compute_similarity_score(self, phash_dist: int, dhash_dist: int,
                               hist_sim: float) -> float:
    """
    计算综合相似度分数
    
    Args:
        phash_dist: pHash汉明距离（0-64）
        dhash_dist: dHash汉明距离（0-64）
        hist_sim: 直方图相似度（0-1）
    
    Returns:
        综合相似度分数（0-100）
    """
    # pHash分数（距离0-64，越小越好）
    phash_score = max(0, 100 - (phash_dist / 64 * 100))
    
    # dHash分数
    dhash_score = max(0, 100 - (dhash_dist / 64 * 100))
    
    # 直方图分数（已经是0-1）
    hist_score = hist_sim * 100
    
    # 加权平均
    final_score = (
        phash_score * 0.5 +
        dhash_score * 0.3 +
        hist_score * 0.2
    )
    
    return round(final_score, 2)
```

### 5.4 MD5哈希计算

```python
def _calculate_md5(self, file_path: str) -> str:
    """计算文件完整MD5哈希"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)  # 64KB块
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()

def _calculate_partial_hash(self, file_path: str, chunk_size: int = 1048576) -> str:
    """计算文件部分哈希（前chunk_size字节）"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        data = f.read(chunk_size)
        md5.update(data)
    return md5.hexdigest()
```

---

## 6. 常见问题排查流程

### 6.1 相似度检测无结果

**症状**: 点击"结果"按钮提示"还没有检测结果"或结果为空

**排查步骤**:
1. 检查数据库中是否有数据
   ```python
   import sqlite3
   conn = sqlite3.connect('image_similarity.db')
   cursor = conn.execute("SELECT COUNT(*) FROM image_index")
   print(cursor.fetchone()[0])  # 应该>0
   ```

2. 检查`current_groups`是否为空
   ```python
   # 在_show_results_window()中添加调试输出
   print(f"[DEBUG] current_groups: {len(self.current_groups)}")
   ```

3. 检查历史数据恢复逻辑
   ```python
   # 确认数据库路径正确
   db_path = self.db_path_var.get()
   print(f"[DEBUG] DB path: {db_path}, exists: {os.path.exists(db_path)}")
   ```

**解决方案**:
- 如果数据库为空 → 重新执行检测
- 如果`current_groups`为空但数据库有数据 → 检查`_show_results_window()`中的历史数据恢复逻辑
- 如果路径错误 → 检查`db_path_var.get()`返回的路径是否正确

### 6.2 图片预览不显示

**症状**: 点击详情窗口的文件行，右侧预览区域无变化

**排查步骤**:
1. 检查事件绑定是否正确
   ```python
   # 在_show_group_details()中确认
   print(f"[DEBUG] Binding TreeviewSelect event")
   file_tree.bind('<<TreeviewSelect>>', 
                 lambda e: self._on_file_select(file_tree, preview_label, thumbnail_cache))
   ```

2. 检查缩略图生成是否成功
   ```python
   # 在_load_thumbnail_async()中添加调试输出
   print(f"[DEBUG] Loading thumbnail for: {file_path}")
   print(f"[DEBUG] File exists: {os.path.exists(file_path)}")
   ```

3. 检查PIL/Pillow是否安装
   ```bash
   pip list | grep -i pillow
   ```

**解决方案**:
- 如果事件未绑定 → 检查`_show_group_details()`中的bind语句
- 如果文件不存在 → 检查路径是否正确（使用反斜杠）
- 如果PIL未安装 → `pip install Pillow`

### 6.3 路径跳转失败

**症状**: 双击详情窗口的路径，无法打开文件夹或打开错误的文件夹

**排查步骤**:
1. 检查路径格式
   ```python
   # 确认路径使用反斜杠
   print(f"[DEBUG] File path: {file_path}")
   print(f"[DEBUG] Path uses forward slash: {'/' in file_path}")
   ```

2. 检查explorer命令
   ```python
   # 确认使用列表形式调用
   cmd = ['explorer', '/select,', file_path]
   print(f"[DEBUG] Command: {' '.join(cmd)}")
   ```

3. 检查文件是否存在
   ```python
   print(f"[DEBUG] File exists: {os.path.exists(file_path)}")
   ```

**解决方案**:
- 如果路径包含正斜杠 → 使用`path.replace('/', '\\')`转换
- 如果使用shell=True → 改为`shell=False`并使用列表形式
- 如果文件不存在 → 检查源文件是否已被删除或移动

### 6.4 列排序不生效

**症状**: 点击列标题，数据不排序或排序错误

**排查步骤**:
1. 检查heading是否绑定command
   ```python
   # 在_show_results_window()中确认
   self.results_tree.heading('similarity', text='平均相似度', 
                            command=lambda: self._sort_results_tree('similarity'))
   ```

2. 检查排序方法中的数据解析
   ```python
   # 确认正确解析百分比、数字、大小
   if column == 'similarity':
       items.sort(key=lambda x: float(x[0].replace('%', '')))
   elif column == 'count':
       items.sort(key=lambda x: int(x[0].replace('张', '').strip()))
   elif column == 'size':
       items.sort(key=lambda x: self._parse_size_to_bytes(x[0]))
   ```

3. 检查排序状态记录
   ```python
   # 确认记录了上次排序的列和方向
   if self._results_last_sort_column == column:
       self._results_sort_reverse = not self._results_sort_reverse
   else:
       self._results_sort_reverse = False
       self._results_last_sort_column = column
   ```

**解决方案**:
- 如果未绑定command → 在heading()中添加command参数
- 如果数据解析错误 → 检查replace()和类型转换逻辑
- 如果排序方向不变 → 检查`_results_sort_reverse`和`_results_last_sort_column`的更新逻辑

### 6.5 多进程模块导入错误

**症状**: `[ERROR] 处理图片失败 ... ModuleNotFoundError: No module named 'PIL'`

**原因**: 多进程子进程使用不同的Python环境，缺少依赖库

**解决方案**:
1. 在全局函数中添加路径设置
   ```python
   def _compute_image_fingerprint(image_path: str) -> Optional[Dict]:
       try:
           # 确保在多进程环境中也能正确导入模块
           import sys
           import os
           # 添加项目根目录到Python路径
           project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
           if project_root not in sys.path:
               sys.path.insert(0, project_root)
           
           from PIL import Image
           import imagehash
           # ... 其余代码
   ```

2. 统一使用虚拟环境
   ```bash
   # 激活虚拟环境
   .venv\Scripts\activate
   
   # 安装依赖
   pip install Pillow imagehash numpy
   
   # 使用虚拟环境Python运行
   .venv\Scripts\python.exe run_gui.py
   ```

### 6.6 数据库锁定错误

**症状**: `sqlite3.OperationalError: database is locked`

**原因**: 多个进程/线程同时写入数据库

**解决方案**:
1. 启用WAL模式
   ```python
   cursor.execute('PRAGMA journal_mode=WAL')
   cursor.execute('PRAGMA synchronous=NORMAL')
   ```

2. 增加超时时间
   ```python
   conn = sqlite3.connect(self.db_path, timeout=30.0)
   ```

3. 使用批量插入减少事务次数
   ```python
   # 每1000条插入一次
   if len(batch) >= self.batch_size:
       self._batch_insert(batch)
       batch = []
   ```

---

## 7. 版本兼容性

### 7.1 Python版本要求

- **最低版本**: Python 3.6+
- **推荐版本**: Python 3.10+
- **测试环境**: Python 3.10.8

### 7.2 依赖库版本

```txt
# 精确匹配（可选）
无额外依赖，仅使用Python标准库

# 相似度检测（必需）
Pillow>=9.0.0
imagehash>=4.3.0
numpy>=1.21.0
```

### 7.3 操作系统兼容性

- **Windows**: ✅ 完全支持（主要开发平台）
- **Linux**: ️ 需要修改路径跳转代码（使用xdg-open代替explorer）
- **macOS**: ⚠️ 需要修改路径跳转代码（使用open代替explorer）

---

## 8. 回滚操作

### 8.1 Git回滚

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
- `62e3889` - docs: 新增图片相似度检测完整文档 (2026-05-25)
- `66161e6` - feat(similarity): 支持从历史数据自动提取目录并重新检测 (2026-05-25)
- `c108982` - feat(similarity): 添加详情窗口图片预览功能（懒加载+缓存） (2026-05-25)
- `32eeda2` - feat(similarity): 为相似度检测结果添加列标题点击排序功能 (2026-05-25)
- `8d9cb42` - fix(similarity): 移除历史数据提示框，自动执行检测 (2026-05-25)

### 8.2 文件备份

**备份关键文件**:
```bash
# 创建备份目录
mkdir backup_$(date +%Y%m%d)

# 备份核心文件
cp core/visual_similarity.py backup_$(date +%Y%m%d)/
cp gui_modules/similarity_tab.py backup_$(date +%Y%m%d)/
cp image_similarity.db backup_$(date +%Y%m%d)/
```

**恢复备份**:
```bash
# 恢复单个文件
cp backup_20260525/visual_similarity.py core/

# 恢复整个项目
rm -rf *
cp -r backup_20260525/* .
```

---

## 9. 测试验证清单

### 9.1 相似度检测功能测试

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
- [ ] 路径跳转功能（双击打开文件夹）

### 9.2 精确匹配功能测试

- [ ] 完全相同文件检测（MD5一致）
- [ ] 大文件检测（>1GB）
- [ ] 小文件检测（<1KB）
- [ ] 增量扫描功能
- [ ] 多线程并行处理
- [ ] 结果导出JSON
- [ ] 路径跳转功能
- [ ] 隐藏功能

### 9.3 GUI界面测试

- [ ] 多目录添加/移除/清空
- [ ] 文件类型过滤
- [ ] 进度条实时更新
- [ ] 日志信息显示
- [ ] 停止功能（中断扫描）
- [ ] 结果窗口显示
- [ ] 详情窗口显示
- [ ] 右键菜单功能

### 9.4 性能测试

- [ ] 1000张图片扫描速度
- [ ] 10000张图片扫描速度
- [ ] 100000张图片扫描速度
- [ ] 内存占用监控
- [ ] CPU利用率监控
- [ ] 数据库大小增长

---

## 10. 联系与支持

如遇无法解决的问题，请：

1. **查看日志**: 运行日志区域显示详细错误信息
2. **查阅文档**: 
   - [图片相似度检测完整指南](SIMILARITY_DETECTION_GUIDE.md)
   - [README.md](../README.md)
3. **Git历史**: 查看提交记录和变更说明
4. **GitHub Issues**: [项目地址](https://github.com/Xxy15021337046/duplicate-file-finder)

---

**最后更新**: 2026-05-25  
**文档版本**: v1.0.0  
**适用版本**: v2.1.0+
