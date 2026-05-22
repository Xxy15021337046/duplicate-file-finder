# 项目结构说明 v2.0

## 目录结构

```
文件重复校验/
├── core/                          # 核心检测引擎模块
│   ├── __init__.py               # 包初始化
│   ├── duplicate_finder.py       # 精确匹配引擎（MD5哈希）
│   └── visual_similarity.py      # 相似度检测引擎（pHash/dHash）
│
├── gui_modules/                   # GUI界面模块
│   ├── __init__.py               # 包初始化
│   ├── main_window.py            # 主窗口和标签页架构
│   ├── exact_match_tab.py        # 精确匹配标签页
│   └── similarity_tab.py         # 相似度检测标签页
│
├── run_gui.py                     # GUI启动入口（新版）
├── run.py                         # 旧版启动脚本（保留兼容）
├── gui.py                         # 旧版单文件GUI（备份）
├── gui_backup.py                  # GUI备份
├── gui_v1_backup.py              # GUI v1备份
│
├── test_similarity_simple.py      # 相似度检测单元测试
├── test_duplicate_finder.py       # 精确匹配单元测试
│
├── requirements.txt               # 依赖包清单
├── README.md                      # 项目说明文档
├── SIMILARITY_USAGE.md           # 相似度检测使用说明
└── PROJECT_STRUCTURE.md          # 本文件
```

## 模块说明

### core/ - 核心检测引擎

**duplicate_finder.py**
- **功能**: 精确文件匹配（MD5哈希）
- **类**: `DuplicateFinder`
- **特性**:
  - 三级过滤策略（文件大小 → 部分哈希 → 完整哈希）
  - 多线程并行处理
  - SQLite3数据库存储
  - 支持文件类型过滤
  - 增量扫描支持

**visual_similarity.py**
- **功能**: 图片相似度检测（感知哈希）
- **类**: `ImageSimilarityFinder`
- **特性**:
  - pHash（感知哈希）- 抗缩放/旋转/亮度变化
  - dHash（差异哈希）- 减少误报
  - 颜色直方图 - 检测色调调整
  - 多进程并行计算
  - 分级过滤优化
  - 支持快速/精确两种模式

### gui_modules/ - GUI界面模块

**main_window.py**
- **功能**: 主窗口和标签页架构
- **类**: `DuplicateFinderGUI`
- **职责**:
  - 创建主窗口框架
  - 管理标签页容器（ttk.Notebook）
  - 提供共享方法和变量
  - 处理目录选择
  - 管理全局进度和日志

**exact_match_tab.py**
- **功能**: 精确匹配标签页
- **类**: `ExactMatchTab`
- **职责**:
  - 扫描配置UI（数据库、输出、线程数）
  - 文件类型过滤UI
  - 执行精确匹配扫描
  - 显示扫描结果
  - 结果详情查看

**similarity_tab.py**
- **功能**: 相似度检测标签页
- **类**: `SimilarityTab`
- **职责**:
  - 相似度配置UI（阈值、模式、格式）
  - 执行相似度检测
  - 显示相似图片组
  - 双击查看详情
  - 右键菜单（隐藏、打开文件夹）
  - 统计信息查看

## 使用方式

### 启动新版模块化GUI（推荐）

```bash
python run_gui.py
```

### 使用命令行工具

**精确匹配**:
```bash
python core/duplicate_finder.py /path/to/directory --output results.json
```

**相似度检测**:
```bash
python core/visual_similarity.py /path/to/images --threshold 12 --mode precise --output results.json
```

### 运行测试

**相似度检测测试**:
```bash
python test_similarity_simple.py
```

**精确匹配测试**:
```bash
python test_duplicate_finder.py
```

## 架构优势

### 1. 模块化设计
- **清晰分离**: 核心逻辑与GUI完全分离
- **易于维护**: 每个模块职责明确，代码量适中
- **可复用性**: 核心引擎可在不同项目中复用

### 2. 可扩展性
- **新增功能**: 添加新标签页只需创建新模块
- **算法升级**: 替换核心引擎不影响GUI
- **多后端支持**: 可轻松添加其他检测算法

### 3. 可测试性
- **单元测试**: 核心引擎独立，易于测试
- **集成测试**: GUI模块可单独测试
- **Mock支持**: 依赖注入便于模拟测试

### 4. 性能优化
- **多进程并行**: 相似度检测使用ProcessPoolExecutor
- **批量处理**: 数据库操作批量提交
- **分级过滤**: 减少不必要的计算

## 依赖关系

```
run_gui.py
    └─ gui_modules/
        ├─ main_window.py
        │   ├─ exact_match_tab.py
        │   │   └─ core/duplicate_finder.py
        │   └─ similarity_tab.py
        │       └─ core/visual_similarity.py
        └─ __init__.py

core/__init__.py
    ├─ duplicate_finder.py
    └─ visual_similarity.py
```

## 数据流

### 精确匹配流程
```
用户选择目录 → ExactMatchTab.start_scan() 
    → DuplicateFinder.find_duplicates() 
    → 三级过滤（大小→部分哈希→完整哈希）
    → 保存JSON结果 → 显示结果窗口
```

### 相似度检测流程
```
用户配置参数 → SimilarityTab.start_scan()
    → ImageSimilarityFinder.build_index()
    → 多进程计算指纹（pHash+dHash+直方图）
    → ImageSimilarityFinder.find_similar_groups()
    → 分级过滤匹配 → 显示相似组列表
```

## 未来扩展方向

1. **视频相似度检测**
   - 新建 `core/video_similarity.py`
   - 关键帧提取 + pHash序列匹配

2. **GPU加速**
   - 新建 `core/gpu_accelerator.py`
   - CuPy加速DCT变换和批量处理

3. **Web界面**
   - 新建 `web_app/` 目录
   - Flask/FastAPI后端 + React前端

4. **云存储支持**
   - 新建 `core/cloud_storage.py`
   - 支持OSS/S3等云存储扫描

5. **智能推荐**
   - 新建 `core/recommender.py`
   - 自动保留最佳质量版本

## 版本历史

### v2.0 (当前版本)
- ✅ 模块化架构重构
- ✅ 新增图片相似度检测
- ✅ 标签页式GUI设计
- ✅ 多进程并行处理
- ✅ 完善的单元测试

### v1.0
- ✅ 基础精确匹配功能
- ✅ 单文件GUI
- ✅ SQLite3数据库存储
- ✅ 多线程并行处理

---

**更新日期**: 2026-05-22  
**维护者**: Qoder AI Assistant  
**许可证**: MIT License
