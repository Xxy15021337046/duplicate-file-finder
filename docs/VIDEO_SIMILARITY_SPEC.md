# 视频相似度检测功能详细规格文档

## 1. 功能概述

### 1.1 功能描述
视频相似度检测模块用于查找内容相似的视频文件，即使它们的分辨率、帧率或格式不同。通过提取视频关键帧并计算感知哈希(pHash)生成视频指纹，然后比较指纹相似度来判断视频是否相似。

### 1.2 适用场景
- 查找不同分辨率的同源视频（如4K vs 1080p）
- 识别经过剪辑的视频片段
- 清理转码后的重复视频
- 发现盗用或转载的视频内容

### 1.3 核心优势
- **跨分辨率检测**: 能识别不同清晰度的相同视频
- **智能关键帧**: 根据视频时长动态调整提取策略
- **高效比对**: 视频指纹比对速度快
- **元数据缓存**: 保存视频信息避免重复解析

---

## 2. 技术实现

### 2.1 视频指纹生成流程

```
视频文件
    ↓
1. OpenCV读取视频流
    ↓
2. 提取元数据 (分辨率、帧率、时长)
    ↓
3. 根据时长确定关键帧数量N
    ↓
4. 在视频中均匀提取N个关键帧
    ↓
5. 对每个关键帧:
   ├─ 转换为灰度图
   └─ 计算pHash (64位)
    ↓
6. 组合N个pHash成视频指纹
    ↓
7. 存储到数据库
```

### 2.2 关键帧提取策略

#### 动态调整规则

| 视频时长 | 关键帧数量 | 提取位置(百分比) | 说明 |
|----------|-----------|------------------|------|
| < 5秒 | 3帧 | 0%, 50%, 100% | 短视频均匀分布 |
| 5-30秒 | 5帧 | 0%, 25%, 50%, 75%, 100% | 中短视频标准采样 |
| > 30秒 | 5帧 | 5%, 25%, 50%, 75%, 95% | 长视频跳过首尾空白 |

**设计理由**:
- **短视频(<5s)**: 内容少，3帧足够代表
- **中短视频(5-30s)**: 标准采样，覆盖完整内容
- **长视频(>30s)**: 跳过开头片头(5%)和结尾片尾/字幕(95%)

#### 代码实现

```python
import cv2
import numpy as np
import imagehash
from PIL import Image

def extract_keyframes(video_path):
    """
    从视频中提取关键帧
    
    Args:
        video_path: 视频文件路径
    
    Returns:
        list: 关键帧列表，每帧为numpy数组(BGR格式)
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return []
    
    # 获取视频信息
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    # 根据时长确定关键帧位置
    if duration < 5:
        # 短视频: 3帧
        frame_positions = [0, 0.5, 1.0]
    elif duration < 30:
        # 中短视频: 5帧
        frame_positions = [0, 0.25, 0.5, 0.75, 1.0]
    else:
        # 长视频: 5帧，跳过首尾
        frame_positions = [0.05, 0.25, 0.5, 0.75, 0.95]
    
    # 提取关键帧
    keyframes = []
    for pos in frame_positions:
        frame_idx = int(pos * (total_frames - 1)) if total_frames > 1 else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if ret:
            keyframes.append(frame)
    
    cap.release()
    return keyframes


def generate_video_fingerprint(video_path):
    """
    生成视频指纹
    
    Args:
        video_path: 视频文件路径
    
    Returns:
        dict: {
            'fingerprints': [phash1, phash2, ...],  # 每帧的pHash
            'width': 视频宽度,
            'height': 视频高度,
            'fps': 帧率,
            'duration': 时长(秒)
        }
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return None
    
    # 获取元数据
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    # 提取关键帧并计算pHash
    fingerprints = []
    frame_positions = get_frame_positions(duration)
    
    for pos in frame_positions:
        frame_idx = int(pos * (total_frames - 1)) if total_frames > 1 else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if ret:
            # BGR转RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # numpy数组转PIL Image
            pil_img = Image.fromarray(frame_rgb)
            # 计算pHash
            phash = imagehash.phash(pil_img, hash_size=8)
            fingerprints.append(str(phash))
    
    cap.release()
    
    return {
        'fingerprints': fingerprints,
        'width': width,
        'height': height,
        'fps': fps,
        'duration': duration
    }
```

### 2.3 视频相似度计算

#### 平均汉明距离

由于视频有多个关键帧，需要计算所有对应帧的平均汉明距离：

```python
def calculate_video_similarity(fingerprints1, fingerprints2):
    """
    计算两个视频指纹的相似度
    
    Args:
        fingerprints1: 视频1的指纹列表 ['phash1', 'phash2', ...]
        fingerprints2: 视频2的指纹列表
    
    Returns:
        float: 平均汉明距离 (越小越相似)
    """
    if len(fingerprints1) != len(fingerprints2):
        # 帧数不同，取最小值
        min_len = min(len(fingerprints1), len(fingerprints2))
        fingerprints1 = fingerprints1[:min_len]
        fingerprints2 = fingerprints2[:min_len]
    
    # 计算每对帧的汉明距离
    distances = []
    for phash1, phash2 in zip(fingerprints1, fingerprints2):
        dist = hamming_distance(phash1, phash2)
        distances.append(dist)
    
    # 返回平均距离
    avg_distance = sum(distances) / len(distances)
    return avg_distance


def hamming_distance(hash1, hash2):
    """计算两个pHash的汉明距离"""
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    xor = int1 ^ int2
    return bin(xor).count('1')
```

#### 相似度阈值参考

| 平均汉明距离 | 相似度 | 含义 |
|--------------|--------|------|
| 0-5 | 92-100% | 几乎完全相同 |
| 6-10 | 84-91% | 非常相似（可能转码） |
| 11-15 | 77-83% | 明显相似（可能有剪辑） |
| 16-20 | 69-75% | 有些相似（同源但差异大） |
| >20 | <69% | 不太相似 |

**默认阈值**: 12（平衡模式）

### 2.4 聚类算法

与图片相似度类似，使用并查集进行聚类：

```python
def cluster_video_groups(similar_pairs):
    """
    将相似视频对聚类成组
    
    Args:
        similar_pairs: [{'path1', 'path2', 'distance'}, ...]
    
    Returns:
        list: 相似组列表
    """
    uf = UnionFind()
    
    for pair in similar_pairs:
        uf.union(pair['path1'], pair['path2'])
    
    groups_dict = {}
    for pair in similar_pairs:
        root = uf.find(pair['path1'])
        groups_dict.setdefault(root, set()).add(pair['path1'])
        groups_dict[root].add(pair['path2'])
    
    groups = []
    for group_id, paths in enumerate(groups_dict.values(), start=1):
        groups.append({
            'group_id': group_id,
            'file_count': len(paths),
            'files': list(paths)
        })
    
    return groups
```

---

## 3. 数据库设计

### 3.1 表结构

```sql
CREATE TABLE video_index (
    path TEXT PRIMARY KEY,          -- 主键：视频绝对路径
    size INTEGER NOT NULL,          -- 文件大小(字节)
    width INTEGER NOT NULL,         -- 视频宽度(像素)
    height INTEGER NOT NULL,        -- 视频高度(像素)
    fps REAL NOT NULL,              -- 帧率(帧/秒)
    duration REAL NOT NULL,         -- 时长(秒)
    fingerprints TEXT NOT NULL,     -- 视频指纹(JSON数组)
    mtime REAL NOT NULL,            -- 最后修改时间(Unix时间戳)
    indexed_at REAL DEFAULT (strftime('%s', 'now')),
    
    CHECK(size > 0),
    CHECK(width > 0),
    CHECK(height > 0),
    CHECK(fps > 0),
    CHECK(duration > 0)
);

-- 索引加速查询
CREATE INDEX idx_size ON video_index(size);
CREATE INDEX idx_dimensions ON video_index(width, height);
CREATE INDEX idx_duration ON video_index(duration);
CREATE INDEX idx_mtime ON video_index(mtime);
```

**字段说明**:
- `fingerprints`: JSON格式字符串，如 `["a1b2c3d4...", "e5f6g7h8...", ...]`
- `duration`: 用于判断视频类型（短/中/长）
- `fps`: 用于计算总帧数

### 3.2 查询示例

```sql
-- 查找特定分辨率的视频
SELECT * FROM video_index 
WHERE width >= 1920 AND height >= 1080;

-- 查找特定时长范围的视频
SELECT * FROM video_index 
WHERE duration BETWEEN 60 AND 300;  -- 1-5分钟

-- 统计各分辨率的视频数量
SELECT 
    CASE 
        WHEN width >= 3840 THEN '4K'
        WHEN width >= 1920 THEN '1080p'
        WHEN width >= 1280 THEN '720p'
        ELSE 'SD'
    END as resolution_category,
    COUNT(*) as count
FROM video_index
GROUP BY resolution_category;
```

---

## 4. GUI界面规范

### 4.1 页签布局

```
──────────────────────────────────────────────────┐
│  检测设置                                         │
│  ├─ 相似度阈值: [━━━━━●━━━━━] 12 (平衡模式)       │
│  │           5              30                   │
│  ├─ 扫描方式: ○ 全量扫描  ● 增量扫描              │
│  ├─ 数据库: [video_similarity.db_______] [浏览...] │
│  ─ [开始检测] [停止] [结果]                       │
├──────────────────────────────────────────────────┤
│  视频格式过滤                                     │
│  ☑ 全部  ☑ MP4  ☑ AVI  ☑ MKV  ☑ MOV  ☑ WMV      │
│  ☑ FLV  ☑ WebM                                   │
│  自定义后缀: [____________________]               │
├──────────────────────────────────────────────────┤
│  进度条: ██████████░░░░ 55%                       │
│  状态: 正在提取关键帧... (2345/5678)              │
──────────────────────────────────────────────────┤
│  运行日志                                         │
│  [17:12:34] [INFO] 开始视频相似度检测...          │
│  [17:12:38] [INFO] 找到 5678 个视频               │
│  [17:15:20] [INFO] 发现 45 个相似组               │
──────────────────────────────────────────────────┘
```

### 4.2 结果列表列定义

| 列标识 | 列名 | 宽度 | 对齐 | Stretch | 说明 |
|--------|------|------|------|---------|------|
| #0 | # | 40px | Center | False | 序号 |
| duration | 时长 | 80px | W | False | 视频时长(M:S) |
| resolution | 分辨率 | 100px | W | False | 视频分辨率(WxH) |
| fps | 帧率 | 60px | W | False | 帧率(FPS) |
| size | 大小 | 80px | W | False | 文件大小(MB/GB) |
| path | 完整路径 | 300px | W | True | 文件绝对路径 |
| open | 打开 | 35px | Center | False | 打开文件位置按钮 |
| delete | 删除 | 35px | Center | False | 删除文件按钮 |

**关键配置**:
```python
'no_stretch_columns': {'#0', 'duration', 'resolution', 'fps', 'size', 'open', 'delete'}
```

### 4.3 视频预览区域

```
┌─────────────────────────────────────┐
│  视频预览                             │
│  ┌─────────────────────────────────┐ │
│  │                                 │ │
│  │     [主预览图 300x200px]        │ │
│  │     (第一帧或选中帧)             │ │
│  │                                 │ │
│  ─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │ [缩略图1] [缩略图2] [缩略图3]   │ │
│  │  00:02   00:04   00:07   00:15  │ │
│  │  (横向排列，点击切换主图)        │ │
│  ─────────────────────────────────┘ │
─────────────────────────────────────┘
```

**特性**:
- 主图固定宽度300px，高度自适应（最大200px）
- 缩略图统一80x60px，横向并排显示
- 每个缩略图下方显示时间戳(MM:SS)
- 点击缩略图即时切换主图显示

---

## 5. 详情窗口规格

### 5.1 窗口布局

```
┌─────────────────────────────────────────────────┐
│  相似视频组 #12 详情                               │
│  平均相似度: 91.3%  |  共 3 个相似视频            │
──────────────────────────┬──────────────────────┤
│  文件列表                 │  视频预览             │
│  ┌────────────────────┐   │  ┌────────────────  │
│  │ # | 时长 | 分辨率  │   │  │                │  │
│  │ 1 | 15:23| 1920x1080│   │  │  [主图300x200] │  │
│  │ 2 | 15:23| 1280x720 │   │  │                │  │
│  │ 3 | 15:22| 3840x2160│   │  └────────────────  │
│  └────────────────────┘   │  [小图1][小图2][小图3]│
│                           │  00:02  00:07  00:15 │
└──────────────────────────┴──────────────────────┘
```

### 5.2 配置定义

```python
VIDEO_SIMILARITY_CONFIG = {
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
    'no_stretch_columns': {'#0', 'duration', 'resolution', 'fps', 'size', 'open', 'delete'},
    'info_label_format': '平均相似度: {:.1f}%  |  共 {} 个相似视频',
    'has_preview': True,
    'preview_type': 'video',
    'preview_title': '视频预览'
}
```

### 5.3 交互行为

#### 双击行
- 打开文件所在文件夹并选中该文件

#### 单击行
- 右侧预览区显示该视频的多帧预览
- 自动生成/加载缓存的关键帧

#### 点击缩略图
- 主图区域切换到对应帧的大图显示
- 保持缩略图尺寸不变

#### 点击"打开"列
- 同双击行效果

#### 点击"删除"列
- 弹出确认对话框
- 使用批处理延迟删除（避免文件占用）
- 从列表中移除，如果为空则关闭窗口

#### 鼠标悬停
- 路径长度 > 30字符时显示tooltip

---

## 6. API参考

### 6.1 VideoSimilarityFinder类

```python
class VideoSimilarityFinder:
    """视频相似度检测器"""
    
    def __init__(self, db_path='video_similarity.db', batch_size=100):
        """
        初始化检测器
        
        Args:
            db_path: SQLite数据库路径
            batch_size: 批量处理大小
        """
        self.SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', 
                                   '.wmv', '.flv', '.webm', '.mpeg', 
                                   '.mpg', '.3gp', '.m4v', '.rmvb', 
                                   '.rm', '.ts', '.mts'}
    
    def build_index(self, directories, incremental=True, progress_callback=None):
        """
        构建视频索引
        
        Args:
            directories: 要扫描的目录列表
            incremental: 是否启用增量扫描
            progress_callback: 进度回调函数
        
        Returns:
            dict: 索引统计信息
        """
    
    def find_similar_groups(self, threshold_phash=12):
        """
        查找相似视频组
        
        Args:
            threshold_phash: 平均汉明距离阈值 (默认12)
        
        Returns:
            list: 相似组列表，每组包含:
                - group_id: 组编号
                - avg_similarity: 平均相似度(%)
                - file_count: 视频数量
                - files: 视频信息列表
        """
    
    def extract_video_info(self, video_path):
        """
        提取视频元数据和指纹
        
        Args:
            video_path: 视频路径
        
        Returns:
            dict: {
                'width': 宽度,
                'height': 高度,
                'fps': 帧率,
                'duration': 时长,
                'fingerprints': [phash1, phash2, ...]
            }
        """
```

### 6.2 工具函数

```python
def format_duration(seconds):
    """
    格式化时长字符串
    
    Args:
        seconds: 时长(秒)
    
    Returns:
        str: 格式化的时长 (如 "15m 23s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def get_frame_positions(duration):
    """
    根据视频时长确定关键帧位置
    
    Args:
        duration: 视频时长(秒)
    
    Returns:
        list: 关键帧位置百分比列表 [0.0, 0.25, 0.5, 0.75, 1.0]
    """
    if duration < 5:
        return [0, 0.5, 1.0]
    elif duration < 30:
        return [0, 0.25, 0.5, 0.75, 1.0]
    else:
        return [0.05, 0.25, 0.5, 0.75, 0.95]


def is_supported_video(filepath):
    """检查是否为支持的视频格式"""
    _, ext = os.path.splitext(filepath)
    return ext.lower() in SUPPORTED_FORMATS
```

---

## 7. 性能优化

### 7.1 批量处理

```python
def batch_process_videos(video_list, batch_size=50):
    """
    批量处理视频，减少数据库事务开销
    
    Args:
        video_list: 视频路径列表
        batch_size: 批次大小（视频处理较慢，批次较小）
    
    Yields:
        list: 每批次的处理结果
    """
    results = []
    for i, video_path in enumerate(video_list, start=1):
        result = process_single_video(video_path)
        results.append(result)
        
        if i % batch_size == 0:
            yield results
            results = []
    
    if results:
        yield results
```

### 7.2 缓存策略

```python
# 视频帧缓存（LRU）
video_thumbnail_cache = {}
MAX_VIDEO_CACHE_SIZE = 10

def get_video_thumbnails(video_path):
    """
    获取或生成视频多帧缩略图
    
    Args:
        video_path: 视频路径
    
    Returns:
        dict: {
            'frames': [photo1, photo2, ...],  # PhotoImage对象
            'timestamps': [ts1, ts2, ...]      # 时间戳列表
        }
    """
    if video_path in video_thumbnail_cache:
        return video_thumbnail_cache[video_path]
    
    # 生成多帧缩略图
    frames_data = extract_and_create_thumbnails(video_path)
    
    # 更新缓存
    if len(video_thumbnail_cache) >= MAX_VIDEO_CACHE_SIZE:
        video_thumbnail_cache.pop(next(iter(video_thumbnail_cache)))
    video_thumbnail_cache[video_path] = frames_data
    
    return frames_data
```

### 7.3 并行处理

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_video_processing(videos, max_workers=2):
    """
    多线程并行处理视频（I/O密集型，线程数不宜过多）
    
    Args:
        videos: 视频路径列表
        max_workers: 线程数（视频处理较重，默认2）
    
    Returns:
        dict: {path: info} 映射
    """
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(extract_video_info, vid): vid 
            for vid in videos
        }
        
        for future in futures.as_completed(future_to_path):
            vid_path = future_to_path[future]
            try:
                info = future.result()
                if info:
                    results[vid_path] = info
            except Exception as e:
                print(f"Error processing {vid_path}: {e}")
    
    return results
```

---

## 8. 性能基准

### 8.1 测试环境
- CPU: Intel i5-10400
- RAM: 16GB
- 存储: SSD
- 视频数: 1,000个
- 总大小: 50GB
- 平均时长: 5分钟

### 8.2 扫描性能

| 操作 | 数量 | 耗时 | 速度 |
|------|------|------|------|
| 视频元数据提取 | 1K视频 | 8分钟 | ~2视频/秒 |
| 关键帧提取+pHash | 1K视频 | 15分钟 | ~1视频/秒 |
| 相似度比对 | 1K视频 | 3分钟 | O(n²)优化后 |
| 增量扫描(无变化) | 1K视频 | 1分钟 | ~16视频/秒 |

### 8.3 内存占用

| 阶段 | 内存使用 |
|------|----------|
| 空闲 | ~50MB |
| 扫描中 | ~300MB |
| 预览中 | ~400MB（含缓存） |

---

## 9. 常见问题排查

### 9.1 某些相似视频未检测到

**可能原因**:
1. 视频内容差异过大（如严重剪辑）
2. 关键帧位置恰好错过重要画面

**解决方案**:
- 调高阈值（如从12调到15）
- 增加关键帧数量（需修改代码）

### 9.2 不相似的视频被判定为相似

**可能原因**:
1. 阈值设置过高
2. 视频本身确实有相似特征（如同类宣传片）

**解决方案**:
- 降低阈值（如从12调到8）
- 人工审核确认

### 9.3 视频预览显示相同帧

**可能原因**:
1. 视频总帧数获取错误
2. 关键帧位置计算bug

**解决方案**:
```python
# 确保正确获取总帧数
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
duration = total_frames / fps if fps > 0 else 0  # 不要用CAP_PROP_POS_MSEC
```

### 9.4 扫描速度极慢

**可能原因**:
1. 大量长视频（>30分钟）
2. 机械硬盘I/O瓶颈
3. 网络驱动器延迟高

**解决方案**:
- 使用SSD存储
- 排除网络驱动器
- 减少线程数（避免I/O竞争）

### 9.5 内存溢出

**可能原因**:
1. 同时缓存过多视频帧
2. 高分辨率视频未缩放

**解决方案**:
```python
# 减小缓存大小
MAX_VIDEO_CACHE_SIZE = 5

# 限制帧尺寸
img.thumbnail((300, 200))  # 主图最大300x200
img.thumbnail((80, 60))    # 缩略图最大80x60
```

---

## 10. 最佳实践

### 10.1 阈值选择
1. **首次运行**: 使用默认阈值12
2. **跨分辨率检测**: 阈值12-15（容忍压缩伪影）
3. **精确匹配**: 阈值8-10（几乎相同）
4. **片段检测**: 阈值15-20（容忍剪辑）

### 10.2 格式支持
- 主流格式：MP4, MKV, AVI（推荐）
- 兼容格式：MOV, WMV, FLV
- 特殊格式：RMVB, TS（可能需要额外解码器）

### 10.3 定期维护
- 每月清理无效索引
- 每季度备份数据库
- 监控磁盘空间（视频占用大）

### 10.4 性能调优
```python
# 根据硬件调整参数
if has_ssd:
    batch_size = 100
    max_workers = 4
else:  # HDD
    batch_size = 50
    max_workers = 2

# 根据视频类型调整
if mostly_short_videos:
    batch_size = 200  # 短视频处理快
else:
    batch_size = 50   # 长视频处理慢
```

---

## 11. 扩展阅读

- [OpenCV视频处理教程](https://docs.opencv.org/master/dd/d43/tutorial_py_video_display.html)
- [FFmpeg命令行工具](https://ffmpeg.org/documentation.html)（可选后端）
- [视频指纹技术综述](https://en.wikipedia.org/wiki/Video_fingerprinting)

---

*文档版本: v3.0.0*  
*最后更新: 2026-05-26*
