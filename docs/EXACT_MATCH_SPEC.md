# 精确匹配功能详细规格文档

## 1. 功能概述

### 1.1 功能描述
精确匹配模块用于检测完全相同的文件副本，基于MD5哈希算法进行文件内容比对。只有当两个文件的MD5哈希值完全相同时，才判定为重复文件。

### 1.2 适用场景
- 清理备份产生的重复文件
- 查找下载多次的相同文件
- 整理照片库中的重复照片
- 磁盘空间优化

### 1.3 核心优势
- **准确性**: MD5哈希碰撞概率极低（理论上存在但实际几乎不可能）
- **速度快**: 三级过滤策略大幅减少完整哈希计算量
- **内存友好**: 分块读取大文件，避免OOM
- **增量扫描**: 只处理新增或修改的文件

---

## 2. 技术实现

### 2.1 三级过滤策略

#### Level 1: 文件大小筛选
```python
# 伪代码
files_by_size = {}
for file in all_files:
    size = os.path.getsize(file)
    files_by_size.setdefault(size, []).append(file)

# 只保留有多个文件的组（可能有重复）
potential_duplicates = {
    size: files for size, files in files_by_size.items() 
    if len(files) > 1
}
```

**原理**: 大小不同的文件内容必然不同，可快速排除。

**性能收益**: 通常可减少80%-90%的文件进入下一级

#### Level 2: 部分哈希筛选
```python
def partial_hash(filepath, chunk_size=4096):
    """读取文件前4KB计算部分哈希"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        data = f.read(chunk_size)
        hasher.update(data)
    return hasher.hexdigest()
```

**原理**: 读取文件开头固定大小（默认4KB）计算哈希，快速排除内容不同的文件。

**chunk_size选择**:
- 太小：区分度不够，大量文件进入下一级
- 太大：I/O开销增加
- 推荐值：4KB-8KB

#### Level 3: 完整MD5哈希
```python
def md5_hash(filepath, chunk_size=8*1024*1024):
    """分块读取文件计算完整MD5"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()
```

**分块读取原因**:
- 避免大文件一次性读入内存导致OOM
- chunk_size=8MB平衡了I/O效率和内存占用

### 2.2 并行处理架构

#### 线程池模型
```python
from concurrent.futures import ThreadPoolExecutor

def parallel_hash_calculation(file_groups, max_workers=4):
    """多线程并行计算哈希"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(calculate_group_hash, group) 
            for group in file_groups
        ]
        for future in futures:
            results.append(future.result())
    return results
```

**线程数选择**:
- I/O密集型任务：线程数 = CPU核数 × 2
- CPU密集型任务：线程数 = CPU核数
- 默认值：4线程（平衡性能和资源占用）

#### 进程池模型（可选）
对于CPU密集型的哈希计算，可使用多进程：
```python
from multiprocessing import Pool

def multiprocess_hash(files):
    """多进程并行哈希计算"""
    with Pool(processes=4) as pool:
        results = pool.map(md5_hash, files)
    return results
```

**注意**: 多进程有启动开销，适合大批量文件场景。

### 2.3 增量扫描机制

#### 数据库记录结构
```sql
CREATE TABLE file_index (
    path TEXT PRIMARY KEY,      -- 文件绝对路径
    size INTEGER NOT NULL,      -- 文件大小(字节)
    mtime REAL NOT NULL,        -- 修改时间戳
    hash TEXT,                  -- MD5哈希值
    indexed_at REAL DEFAULT (strftime('%s', 'now'))  -- 索引时间
);

CREATE INDEX idx_mtime ON file_index(mtime);
```

#### 增量逻辑
```python
def should_reindex(filepath, db_record):
    """判断文件是否需要重新索引"""
    if not db_record:
        return True  # 新文件，需要索引
    
    current_mtime = os.path.getmtime(filepath)
    if current_mtime != db_record['mtime']:
        return True  # 文件已修改，需要重新索引
    
    return False  # 文件未变化，跳过
```

#### 工作流程
```
1. 遍历文件系统获取所有文件
2. 对每个文件：
   ├─ 查询数据库中是否有记录
   ├─ 如果有且mtime未变 → 跳过
   └─ 否则 → 重新计算哈希并更新数据库
3. 删除数据库中已不存在的文件记录（可选）
```

---

## 3. 数据库设计

### 3.1 表结构详解

#### file_index 表
```sql
CREATE TABLE file_index (
    path TEXT PRIMARY KEY,          -- 主键：文件绝对路径
    size INTEGER NOT NULL,          -- 文件大小(字节)
    mtime REAL NOT NULL,            -- 最后修改时间(Unix时间戳)
    hash TEXT,                      -- MD5哈希值(十六进制字符串)
    indexed_at REAL DEFAULT (strftime('%s', 'now')),  -- 索引创建时间
    updated_at REAL DEFAULT (strftime('%s', 'now'))   -- 最后更新时间
);

-- 索引加速查询
CREATE INDEX idx_size ON file_index(size);
CREATE INDEX idx_hash ON file_index(hash);
CREATE INDEX idx_mtime ON file_index(mtime);
```

**字段说明**:
- `path`: 使用绝对路径确保唯一性
- `size`: 用于第一级快速筛选
- `mtime`: 用于增量扫描判断
- `hash`: 完整的MD5哈希值
- `indexed_at/updated_at`: 审计和清理用

#### duplicate_groups 视图
```sql
-- 动态生成重复组（不物理存储）
CREATE VIEW duplicate_groups AS
SELECT 
    hash,
    COUNT(*) as file_count,
    GROUP_CONCAT(path) as file_paths,
    SUM(size) as total_wasted  -- 浪费的空间(保留一份，其余都是浪费)
FROM file_index
WHERE hash IS NOT NULL
GROUP BY hash
HAVING COUNT(*) > 1;
```

### 3.2 查询优化

#### 查找重复组
```sql
SELECT 
    hash,
    COUNT(*) as count,
    GROUP_CONCAT(path) as paths
FROM file_index
WHERE hash IN (
    SELECT hash FROM file_index 
    GROUP BY hash 
    HAVING COUNT(*) > 1
)
GROUP BY hash
ORDER BY count DESC;
```

#### 按大小范围查询
```sql
SELECT * FROM file_index
WHERE size BETWEEN ? AND ?
AND hash IN (
    SELECT hash FROM file_index 
    WHERE size BETWEEN ? AND ?
    GROUP BY hash 
    HAVING COUNT(*) > 1
);
```

---

## 4. GUI界面规范

### 4.1 页签布局

```
┌──────────────────────────────────────────────────┐
│  检测设置                                         │
│  ├─ 线程数: [4 ▼]                                 │
│  ├─ 扫描方式: ○ 全量扫描  ● 增量扫描              │
│  └─ [开始检测] [停止] [结果]                       │
├──────────────────────────────────────────────────┤
│  进度条: ████████░░░░░░░░ 45%                     │
│  状态: 正在计算哈希... (1234/5678)                │
──────────────────────────────────────────────────┤
│  运行日志                                         │
│  [16:23:45] [INFO] 开始扫描...                    │
│  [16:23:46] [INFO] 找到 5678 个文件               │
│  [16:23:50] [INFO] 发现 234 个重复组              │
└──────────────────────────────────────────────────┘
```

### 4.2 结果列表列定义

| 列标识 | 列名 | 宽度 | 对齐 | Stretch | 说明 |
|--------|------|------|------|---------|------|
| #0 | # | 40px | Center | False | 序号 |
| size | 大小 | 80px | W | False | 文件大小(KB/MB/GB) |
| ext | 后缀 | 60px | W | False | 文件扩展名 |
| path | 完整路径 | 310px | W | True | 文件绝对路径 |
| open | 打开 | 35px | Center | False | 打开文件位置按钮 |
| delete | 删除 | 35px | Center | False | 删除文件按钮 |

**关键配置**:
```python
'no_stretch_columns': {'#0', 'size', 'ext', 'open', 'delete'}
```

### 4.3 交互行为

#### 双击行
- **动作**: 打开文件所在文件夹并选中该文件
- **实现**:
```python
subprocess.Popen(f'explorer /select,"{file_path}"')
```

#### 点击"打开"列
- **动作**: 同双击行，打开文件位置

#### 点击"删除"列
- **动作**: 弹出确认对话框 → 删除文件 → 从列表中移除
- **安全机制**:
  - 二次确认
  - 使用批处理延迟删除（避免文件占用）
  - 删除失败时显示错误信息

#### 鼠标悬停
- **动作**: 显示完整路径tooltip（路径过长时）
- **触发条件**: 单元格文本长度 > 30字符

---

## 5. 详情窗口规格

### 5.1 窗口布局

```
┌─────────────────────────────────────────────┐
│  组 #14 详情                                 │
│  文件大小: 12.5 MB  |  共 3 个重复文件        │
──────────────────────────┬──────────────────┤
│  文件列表                 │                  │
│  ┌────────────────────┐   │  (无预览区域)     │
│  │ # | 大小 | 后缀 |   │   │                  │
│  │ 1 | 12.5M| .jpg |   │   │                  │
│  │ 2 | 12.5M| .jpg |   │   │                  │
│  │ 3 | 12.5M| .jpg |   │   │                  │
│  └────────────────────┘   │                  │
└──────────────────────────┴──────────────────┘
```

### 5.2 列配置

```python
EXACT_MATCH_CONFIG = {
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
    'no_stretch_columns': {'#0', 'size', 'ext', 'open', 'delete'},
    'info_label_format': '文件大小: {}  |  共 {} 个重复文件',
    'has_preview': False
}
```

---

## 6. API参考

### 6.1 DuplicateFinder类

```python
class DuplicateFinder:
    """精确重复文件检测器"""
    
    def __init__(self, db_path='file_index.db', batch_size=100):
        """
        初始化检测器
        
        Args:
            db_path: SQLite数据库路径
            batch_size: 批量处理大小
        """
    
    def build_index(self, directories, incremental=True, progress_callback=None):
        """
        构建文件索引
        
        Args:
            directories: 要扫描的目录列表
            incremental: 是否启用增量扫描
            progress_callback: 进度回调函数 callback(progress, message)
        
        Returns:
            dict: 索引统计信息
        """
    
    def find_duplicates(self, min_size=0):
        """
        查找重复文件
        
        Args:
            min_size: 最小文件大小过滤(字节)
        
        Returns:
            list: 重复组列表，每组包含:
                - group_id: 组编号
                - hash: 文件哈希
                - file_count: 文件数量
                - files: 文件信息列表
                - wasted_space: 浪费的空间
        """
    
    def delete_file(self, filepath):
        """
        删除文件并更新数据库
        
        Args:
            filepath: 要删除的文件路径
        
        Returns:
            bool: 是否成功
        """
```

### 6.2 工具函数

```python
def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_file_extension(filepath):
    """获取文件扩展名（小写）"""
    _, ext = os.path.splitext(filepath)
    return ext.lower() if ext else '(无)'


def calculate_partial_hash(filepath, chunk_size=4096):
    """计算文件部分哈希（前N字节）"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        data = f.read(chunk_size)
        hasher.update(data)
    return hasher.hexdigest()


def calculate_md5(filepath, chunk_size=8*1024*1024):
    """计算文件完整MD5哈希"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()
```

---

## 7. 性能基准

### 7.1 测试环境
- CPU: Intel i5-10400 (6核12线程)
- RAM: 16GB DDR4
- 存储: SSD NVMe
- 文件数: 100,000个
- 总大小: 500GB

### 7.2 扫描性能

| 扫描类型 | 文件数 | 耗时 | 速度 |
|----------|--------|------|------|
| 首次全量扫描 | 100K | 8分钟 | ~200文件/秒 |
| 增量扫描(无变化) | 100K | 30秒 | ~3300文件/秒 |
| 增量扫描(10%变化) | 100K | 2分钟 | ~800文件/秒 |

### 7.3 内存占用

| 阶段 | 内存使用 |
|------|----------|
| 空闲 | ~50MB |
| 扫描中 | ~150MB |
| 结果展示 | ~100MB |

---

## 8. 常见问题排查

### 8.1 扫描速度慢

**可能原因**:
1. 机械硬盘I/O瓶颈
2. 网络驱动器延迟高
3. 线程数设置过低

**解决方案**:
- 使用SSD存储
- 排除网络驱动器
- 增加线程数（但不超过CPU核数×2）

### 8.2 内存溢出

**可能原因**:
1. chunk_size设置过大
2. 并发线程过多

**解决方案**:
```python
# 减小chunk_size
finder = DuplicateFinder(chunk_size=4*1024*1024)  # 4MB

# 减少线程数
finder = DuplicateFinder(max_workers=2)
```

### 8.3 数据库锁定

**可能原因**:
1. 多个进程同时写入
2. 事务未正确提交

**解决方案**:
```python
# 使用WAL模式提高并发性能
conn.execute('PRAGMA journal_mode=WAL')

# 确保事务提交
try:
    conn.execute('INSERT INTO ...')
    conn.commit()
except:
    conn.rollback()
    raise
```

### 8.4 误判重复

**罕见情况**: MD5哈希碰撞（理论存在，实际几乎不可能）

**验证方法**:
```python
# 对疑似碰撞的文件进行逐字节比较
def verify_identical(file1, file2):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        while True:
            chunk1 = f1.read(8192)
            chunk2 = f2.read(8192)
            if chunk1 != chunk2:
                return False
            if not chunk1:
                return True
```

---

## 9. 最佳实践

### 9.1 扫描策略
1. **首次运行**: 全量扫描建立基线
2. **日常维护**: 增量扫描（每天/每周）
3. **定期清理**: 每月执行一次全量扫描清理无效记录

### 9.2 参数调优
```python
# 小文件为主 (< 1MB)
batch_size = 500      # 增大批次
chunk_size = 4096     # 减小分块
max_workers = 8       # 增加线程

# 大文件为主 (> 100MB)
batch_size = 50       # 减小批次
chunk_size = 16*1024*1024  # 增大分块
max_workers = 2       # 减少线程（I/O瓶颈）
```

### 9.3 数据安全
- 删除操作前务必备份重要数据
- 使用"隐藏"功能临时排除不确定的文件
- 定期检查数据库完整性：`PRAGMA integrity_check`

---

## 10. 扩展阅读

- [MD5算法原理](https://en.wikipedia.org/wiki/MD5)
- [SQLite性能优化指南](https://www.sqlite.org/performance.html)
- [Python并发编程最佳实践](https://docs.python.org/3/library/concurrent.futures.html)

---

*文档版本: v3.0.0*  
*最后更新: 2026-05-26*
