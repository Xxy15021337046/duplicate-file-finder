# 文件重复校验工具 - 项目总体架构文档

## 1. 项目概述

### 1.1 项目名称
文件重复校验工具 (File Duplicate Checker)

### 1.2 项目目标
开发一个支持TB级大规模文件扫描的重复文件检测工具，具备以下核心能力：
- **精确匹配**：基于MD5哈希的精确文件内容比对
- **图片相似度**：基于感知哈希(pHash)的图片相似度检测
- **视频相似度**：基于关键帧提取和视频指纹的相似度检测

### 1.3 技术栈
- **语言**: Python 3.6+
- **GUI框架**: Tkinter
- **数据库**: SQLite3
- **图像处理**: Pillow, imagehash
- **视频处理**: OpenCV (cv2)
- **并行处理**: multiprocessing, concurrent.futures
- **打包工具**: PyInstaller

### 1.4 项目特点
- ✅ 支持增量扫描（保留历史索引）
- ✅ 支持多目录并行处理
- ✅ 支持断点续扫
- ✅ 内存优化设计（适合TB级数据）
- ✅ 模块化架构设计

---

## 2. 项目架构

### 2.1 目录结构

```
文件重复校验/
├── run_gui.py                    # 程序入口
├── requirements.txt              # 依赖包列表
├── README.md                     # 项目说明文档
├── build.bat / build.sh          # 构建脚本
│
├── core/                         # 核心业务层
│   ├── __init__.py
│   ├── duplicate_finder.py       # 精确匹配引擎
│   ├── visual_similarity.py      # 图片相似度引擎
│   └── video_similarity.py       # 视频相似度引擎
│
├── gui_modules/                  # GUI展示层
│   ├── __init__.py
│   ├── main_window.py            # 主窗口
│   ├── exact_match_tab.py        # 精确匹配页签
│   ├── similarity_tab.py         # 图片相似度页签
│   ├── video_similarity_tab.py   # 视频相似度页签
│   └── detail_window.py          # 公共详情窗口组件
│
├── docs/                         # 项目文档
│   └── PROJECT_OVERVIEW.md       # 本文档
│
└── *.db                          # SQLite数据库文件
    ├── file_index.db             # 精确匹配索引
    ├── image_similarity.db       # 图片相似度索引
    └── video_similarity.db       # 视频相似度索引
```

### 2.2 分层架构

```
┌─────────────────────────────────────────┐
│           GUI Layer (gui_modules/)       │
│  ┌──────────────┬───────────────┐        │
│  │ Main Window  │  Tab Pages     │        │
│  │              │  ├─ Exact Match│        │
│  │              │  ├─ Image Sim  │        │
│  │              │  └─ Video Sim  │        │
│  └──────────────┴───────────────┘        │
─────────────────────────────────────────┤
│         Core Layer (core/)               │
│  ┌──────────────┬───────────────┐        │
│  │ Finder       │  Similarity   │        │
│  │ Engine       │  Engines      │        │
│  └──────────────┴───────────────┘        │
├─────────────────────────────────────────┤
│         Data Layer (SQLite)              │
│  ┌─────────────────────────────┐         │
│  │  Index Tables + Metadata    │         │
│  └─────────────────────────────┘         │
└─────────────────────────────────────────┘
```

---

## 3. 核心功能模块

### 3.1 精确匹配模块 (Exact Match)

**位置**: `core/duplicate_finder.py`

**功能描述**:
- 使用MD5哈希算法进行文件内容精确比对
- 支持大文件分块读取（避免内存溢出）
- 三级过滤策略：大小 → 部分哈希 → 完整哈希

**关键特性**:
- 文件大小预筛选（快速排除不同大小的文件）
- 增量扫描模式（只扫描新增/修改的文件）
- 并行哈希计算（提高扫描速度）
- 断点续扫支持（意外中断后可恢复）

**数据库表结构**:
```sql
-- 文件索引表
CREATE TABLE file_index (
    path TEXT PRIMARY KEY,      -- 文件绝对路径
    size INTEGER,               -- 文件大小(字节)
    mtime REAL,                 -- 修改时间戳
    hash TEXT                   -- MD5哈希值
);

-- 重复组表
CREATE TABLE duplicate_groups (
    group_id INTEGER PRIMARY KEY,
    file_hash TEXT,             -- 文件哈希
    file_count INTEGER          -- 重复文件数量
);
```

### 3.2 图片相似度模块 (Image Similarity)

**位置**: `core/visual_similarity.py`

**功能描述**:
- 使用感知哈希(pHash)算法检测相似图片
- 支持多种图片格式：JPG, PNG, GIF, BMP, TIFF等
- 汉明距离(Hamming Distance)作为相似度度量

**关键特性**:
- pHash算法对缩放、旋转、亮度变化鲁棒
- 可配置相似度阈值（默认≤10表示相似）
- 增量索引构建
- 批量处理优化

**相似度阈值参考**:
- ≤8: 严格模式（几乎相同）
- ≤12: 平衡模式（轻微差异）
- ≤20: 宽松模式（明显相似）

**数据库表结构**:
```sql
CREATE TABLE image_index (
    path TEXT PRIMARY KEY,      -- 图片路径
    size INTEGER,               -- 文件大小
    width INTEGER,              -- 图片宽度
    height INTEGER,             -- 图片高度
    phash TEXT,                 -- 感知哈希值(16进制字符串)
    mtime REAL                  -- 修改时间
);
```

### 3.3 视频相似度模块 (Video Similarity)

**位置**: `core/video_similarity.py`

**功能描述**:
- 从视频中提取关键帧生成视频指纹
- 比较关键帧的pHash值判断视频相似度
- 支持动态调整关键帧数量（根据视频时长）

**关键特性**:
- 智能关键帧提取策略：
  - 短视频(<5s): 提取3帧
  - 中短视频(5-30s): 提取5帧
  - 长视频(>30s): 提取5帧，跳过首尾空白
- 视频元数据缓存（分辨率、帧率、时长）
- 多格式支持：MP4, AVI, MKV, MOV, WMV, FLV, WebM等

**视频指纹生成流程**:
```
视频文件 → OpenCV读取 → 提取N个关键帧 → 
每帧转灰度 → 计算pHash → 组合成视频指纹
```

**数据库表结构**:
```sql
CREATE TABLE video_index (
    path TEXT PRIMARY KEY,      -- 视频路径
    size INTEGER,               -- 文件大小
    width INTEGER,              -- 视频宽度
    height INTEGER,             -- 视频高度
    fps REAL,                   -- 帧率
    duration REAL,              -- 时长(秒)
    fingerprints TEXT,          -- 视频指纹(JSON数组)
    mtime REAL                  -- 修改时间
);
```

---

## 4. GUI界面模块

### 4.1 主窗口 (main_window.py)

**功能**:
- 提供统一的应用程序窗口
- 管理多个功能页签(Tab)
- 处理全局状态（扫描标志、停止标志）
- 提供日志输出区域

**界面布局**:
```
┌─────────────────────────────────────────────┐
│  Title Bar                                   │
├─────────────────────────────────────────────┤
│  Directory List (添加/删除扫描目录)           │
─────────────────────────────────────────────┤
│  Tab Control:                                │
│  ┌─────────────────────────────────────┐     │
│  │ [精确匹配] [图片相似度] [视频相似度] │     │
│  └─────────────────────────────────────┘     │
├─────────────────────────────────────────────┤
│  Log Area (运行日志)                          │
─────────────────────────────────────────────┘
```

### 4.2 精确匹配页签 (exact_match_tab.py)

**功能**:
- 配置扫描参数（线程数、增量模式）
- 启动/停止扫描
- 显示检测结果列表
- 提供结果操作（打开、删除、隐藏）

**结果列表列**:
| 列名 | 宽度 | 说明 |
|------|------|------|
| # | 40px | 序号 |
| 大小 | 80px | 文件大小 |
| 后缀 | 60px | 文件扩展名 |
| 完整路径 | 310px | 文件绝对路径 |
| 打开 | 35px | 打开文件按钮 |
| 删除 | 35px | 删除文件按钮 |

### 4.3 图片相似度页签 (similarity_tab.py)

**功能**:
- 配置相似度阈值（滑动条5-30）
- 选择图片格式过滤器
- 显示相似图片组
- 图片预览功能

**结果列表列**:
| 列名 | 宽度 | 说明 |
|------|------|------|
| # | 40px | 序号 |
| 分辨率 | 100px | 图片分辨率 |
| 大小 | 80px | 文件大小 |
| 完整路径 | 500px | 文件绝对路径 |
| 打开 | 35px | 打开文件按钮 |
| 删除 | 35px | 删除文件按钮 |

**预览区域**:
- 左侧：文件列表Treeview
- 右侧：图片预览区（最大280x280px）

### 4.4 视频相似度页签 (video_similarity_tab.py)

**功能**:
- 配置相似度阈值
- 选择视频格式过滤器
- 显示相似视频组
- 视频多帧预览功能

**结果列表列**:
| 列名 | 宽度 | 说明 |
|------|------|------|
| # | 40px | 序号 |
| 时长 | 80px | 视频时长 |
| 分辨率 | 100px | 视频分辨率 |
| 帧率 | 60px | 帧率(FPS) |
| 大小 | 80px | 文件大小 |
| 完整路径 | 300px | 文件绝对路径 |
| 打开 | 35px | 打开文件按钮 |
| 删除 | 35px | 删除文件按钮 |

**视频预览区域**:
- 上方：主预览图（300x200px，第一帧或选中帧）
- 下方：横向排列的缩略图（80x60px，带时间戳）
- 点击缩略图切换主图显示

### 4.5 公共详情窗口组件 (detail_window.py)

**设计目的**: 统一三个页签的详情页面代码，减少重复

**核心类**:
1. `TreeviewTooltip`: Treeview单元格鼠标悬停提示
2. `DetailWindowConfig`: 详情窗口配置类
3. `FileDetailWindow`: 通用详情窗口类

**工厂函数**:
- `create_exact_match_detail()`: 创建精确匹配详情窗口
- `create_image_similarity_detail()`: 创建图片相似度详情窗口
- `create_video_similarity_detail()`: 创建视频相似度详情窗口

**配置项说明**:
```python
{
    'title_prefix': '组',                    # 标题前缀
    'window_size': '900x600',                # 窗口尺寸
    'columns': ('size', 'ext', 'path', ...), # 列定义
    'headings': {...},                       # 列头文本
    'column_widths': {...},                  # 列宽
    'no_stretch_columns': {...},             # 不拉伸的列
    'info_label_format': '...',              # 信息标签格式
    'has_preview': True/False,               # 是否有预览
    'preview_type': 'image'/'video'/None     # 预览类型
}
```

---

## 5. 关键技术实现

### 5.1 三级过滤策略（精确匹配）

为优化大规模文件扫描性能，采用三级过滤：

```
Level 1: 文件大小筛选
  ↓ (相同大小的文件)
Level 2: 部分哈希筛选 (读取文件前4KB)
  ↓ (部分哈希相同的文件)
Level 3: 完整MD5哈希计算
  ↓ (哈希完全相同的文件 = 重复文件)
```

### 5.2 感知哈希算法 (pHash)

**原理**:
1. 缩小图片到32x32像素
2. 转换为灰度图
3. 计算DCT（离散余弦变换）
4. 取左上角8x8低频区域
5. 计算中位数，生成64位哈希

**优势**:
- 对缩放不敏感
- 对轻微旋转不敏感
- 对亮度/对比度变化鲁棒
- 计算速度快

### 5.3 视频关键帧提取策略

根据视频时长动态调整提取策略：

| 视频时长 | 关键帧数量 | 提取位置 |
|----------|-----------|----------|
| < 5秒 | 3帧 | 0%, 50%, 100% |
| 5-30秒 | 5帧 | 0%, 25%, 50%, 75%, 100% |
| > 30秒 | 5帧 | 5%, 25%, 50%, 75%, 95% |

**设计理由**:
- 短视频：均匀分布即可
- 长视频：跳过首尾可能的黑屏/字幕

### 5.4 增量扫描机制

**实现方式**:
1. 检查数据库中是否已有该路径的记录
2. 比较文件修改时间(mtime)
3. 如果未修改，跳过该文件
4. 如果已修改或新增，重新计算索引

**优势**:
- 大幅减少重复扫描时间
- 适合定期更新检测场景

---

## 6. 数据流转

### 6.1 精确匹配流程

```
用户添加目录 → 遍历文件系统 → 
  ↓
文件大小筛选 → 按大小分组 → 
  ↓
部分哈希计算 → 部分哈希分组 → 
  ↓
完整MD5计算 → 哈希分组 → 
  ↓
存储到SQLite → 生成重复组报告
```

### 6.2 图片相似度流程

```
用户添加目录 → 遍历图片文件 → 
  ↓
Pillow加载图片 → 计算pHash → 
  ↓
存储到SQLite → 
  ↓
两两比较汉明距离 → 
  ↓
聚类生成相似组 → 生成报告
```

### 6.3 视频相似度流程

```
用户添加目录 → 遍历视频文件 → 
  ↓
OpenCV读取视频 → 提取元数据 → 
  ↓
提取关键帧 → 计算每帧pHash → 
  ↓
组合成视频指纹 → 存储到SQLite → 
  ↓
比较指纹相似度 → 生成相似组报告
```

---

## 7. 性能优化要点

### 7.1 内存优化
- 大文件分块读取（chunk_size=8MB）
- 图片缩略图缓存限制（LRU策略）
- 视频帧按需加载，不全部载入内存

### 7.2 并发优化
- 多线程I/O操作（文件读取）
- 多进程CPU密集型任务（哈希计算）
- 线程池管理（避免过度创建线程）

### 7.3 数据库优化
- 使用索引加速查询
- 批量插入减少事务开销
- WAL模式提高并发读写性能

---

## 8. 常见问题与解决方案

### 8.1 列宽设置不生效

**问题**: Treeview列设置了width但实际很宽

**原因**: 没有设置`stretch=False`，Tkinter会自动拉伸列

**解决**:
```python
tree.column(col, width=35, anchor=tk.CENTER, stretch=False)
```

### 8.2 双击跳转路径错误

**问题**: 双击行跳转到桌面而非文件位置

**原因**: 直接使用原始路径，未标准化

**解决**:
```python
file_path = os.path.normpath(file_path)
subprocess.Popen(f'explorer /select,"{file_path}"')
```

### 8.3 视频预览点击无效

**问题**: 点击缩略图无法切换主图

**原因**: 循环中的闭包问题，所有handler引用最后一个变量

**解决**: 使用工厂函数模式
```python
def make_click_handler(photo):
    def handler(event=None):
        label.config(image=photo)
    return handler

click_handler = make_click_handler(frame_photo)
label.bind('<Button-1>', click_handler)
```

### 8.4 操作列点击事件错位

**问题**: 点击"打开"无反应，点击"删除"变成打开

**原因**: 列索引计算错误

**解决**: 动态查找列位置
```python
open_idx = columns.index('open')
open_col = f'#{open_idx + 1}'
```

---

## 9. 开发规范

### 9.1 代码组织原则
- 核心逻辑与UI分离（core/ vs gui_modules/）
- 公共组件抽取复用（detail_window.py）
- 配置驱动设计（DetailWindowConfig）

### 9.2 命名规范
- 类名：PascalCase（如 `FileDetailWindow`）
- 函数/变量：snake_case（如 `on_double_click`）
- 常量：UPPER_CASE（如 `SUPPORTED_FORMATS`）
- 私有方法：前导下划线（如 `_build_ui`）

### 9.3 注释规范
- 模块级docstring说明功能
- 复杂逻辑添加行内注释
- 关键参数添加Args/Returns说明

---

## 10. 后续扩展方向

### 10.1 功能增强
- [ ] 支持云端存储扫描（OSS/S3）
- [ ] 支持压缩包内文件检测
- [ ] 支持自定义相似度算法
- [ ] 导出结果为Excel/PDF

### 10.2 性能提升
- [ ] GPU加速图片/视频处理
- [ ] 分布式扫描（多机协同）
- [ ] 更智能的增量策略

### 10.3 用户体验
- [ ] 深色主题支持
- [ ] 多语言国际化
- [ ] 拖拽添加目录
- [ ] 扫描进度预估

---

## 附录A: 依赖包清单

```
Pillow>=9.0.0          # 图像处理
imagehash>=4.3.0       # 感知哈希算法
opencv-python>=4.5.0   # 视频处理
numpy>=1.21.0          # 数值计算
```

## 附录B: 支持的图片格式

- JPEG/JPG
- PNG
- GIF
- BMP
- TIFF/TIF
- WebP
- ICO
- PSD (部分支持)

## 附录C: 支持的视频格式

- MP4
- AVI
- MKV
- MOV
- WMV
- FLV
- WebM
- MPEG/MPG
- 3GP
- M4V
- RMVB/RM
- TS/MTS

---

*文档版本: v3.0.0*  
*最后更新: 2026-05-26*  
*维护者: Qoder AI Assistant*
