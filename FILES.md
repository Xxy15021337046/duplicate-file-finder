# 项目文件清单

## 📁 目录结构

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
│
├── test_duplicate_finder.py       # 精确匹配单元测试
├── test_similarity_simple.py      # 相似度检测单元测试
│
├── requirements.txt               # 依赖包清单
├── .gitignore                    # Git忽略配置
│
├── README.md                      # 项目说明文档
├── QUICKSTART.md                  # 快速启动指南 ⭐推荐先看
├── PROJECT_STRUCTURE.md           # 项目结构说明
├── SIMILARITY_USAGE.md            # 相似度检测使用说明
├── IMPLEMENTATION_SUMMARY.md      # 实现总结
└── FILES.md                       # 本文件
```

## 📄 文件说明

### 核心模块 (core/)

| 文件 | 大小 | 说明 |
|------|------|------|
| `__init__.py` | 253B | 包初始化，导出核心类 |
| `duplicate_finder.py` | 24KB | 精确匹配引擎（MD5哈希，三级过滤） |
| `visual_similarity.py` | 21KB | 相似度检测引擎（pHash/dHash，新增功能） |

### GUI模块 (gui_modules/)

| 文件 | 大小 | 说明 |
|------|------|------|
| `__init__.py` | 266B | 包初始化，导出GUI类 |
| `main_window.py` | 9.7KB | 主窗口框架和标签页容器 |
| `exact_match_tab.py` | 16KB | 精确匹配标签页UI |
| `similarity_tab.py` | 23KB | 相似度检测标签页UI（新增功能） |

### 启动脚本

| 文件 | 大小 | 说明 |
|------|------|------|
| `run_gui.py` | 940B | **推荐使用** - 新版模块化GUI启动入口 |

### 测试文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `test_duplicate_finder.py` | 5.9KB | 精确匹配单元测试 |
| `test_similarity_simple.py` | 5.4KB | 相似度检测单元测试 |

### 配置文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `requirements.txt` | 833B | Python依赖包清单 |
| `.gitignore` | 439B | Git忽略配置 |

### 文档

| 文件 | 大小 | 说明 | 优先级 |
|------|------|------|--------|
| `README.md` | 12KB | 完整项目文档 | ⭐⭐⭐ |
| `QUICKSTART.md` | 4.8KB | **快速启动指南** | ⭐⭐⭐⭐⭐ |
| `PROJECT_STRUCTURE.md` | 6.2KB | 项目结构说明 | ⭐⭐ |
| `SIMILARITY_USAGE.md` | 5.4KB | 相似度检测详细用法 | ⭐⭐⭐ |
| `IMPLEMENTATION_SUMMARY.md` | 11KB | 实现总结和技术细节 | ⭐⭐ |
| `FILES.md` | - | 本文件 | - |

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install Pillow imagehash
```

### 2. 启动GUI
```bash
python run_gui.py
```

### 3. 查看文档
- **新手**: 阅读 [QUICKSTART.md](QUICKSTART.md)
- **进阶**: 阅读 [README.md](README.md)
- **开发者**: 阅读 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## 🗑️ 已删除的文件

以下文件已被清理（不需要）：

- ❌ `gui.py` - 旧版单文件GUI（已重构为模块化架构）
- ❌ `gui_backup.py` - GUI备份
- ❌ `gui_v1_backup.py` - GUI v1备份
- ❌ `run.py` - 旧版启动脚本（已被run_gui.py替代）
- ❌ `duplicates.json` - 临时输出文件
- ❌ `file_index.db` - 临时数据库文件

## 📊 统计信息

| 类型 | 数量 | 总大小 |
|------|------|--------|
| Python源文件 | 8个 | ~100KB |
| Markdown文档 | 6个 | ~40KB |
| 配置文件 | 2个 | ~1.3KB |
| 测试文件 | 2个 | ~11KB |
| **总计** | **18个** | **~152KB** |

## 🔍 文件用途速查

### 我想...

**启动程序**:
→ 运行 `python run_gui.py`

**命令行使用**:
→ 查看 [SIMILARITY_USAGE.md](SIMILARITY_USAGE.md)

**了解项目结构**:
→ 阅读 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

**快速上手**:
→ 阅读 [QUICKSTART.md](QUICKSTART.md)

**查看完整文档**:
→ 阅读 [README.md](README.md)

**运行测试**:
→ `python test_similarity_simple.py`

**修改核心算法**:
→ 编辑 `core/visual_similarity.py` 或 `core/duplicate_finder.py`

**修改GUI界面**:
→ 编辑 `gui_modules/main_window.py` 或对应标签页文件

**添加新功能**:
→ 参考 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 中的扩展方向

---

**更新日期**: 2026-05-22  
**版本**: v2.0  
**维护者**: Qoder AI Assistant
