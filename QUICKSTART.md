# 快速启动指南

## 🚀 3分钟快速开始

### 1. 安装依赖（30秒）

```bash
pip install Pillow imagehash
```

可选优化：
```bash
pip install numpy tqdm
```

### 2. 启动GUI（10秒）

```bash
python run_gui.py
```

### 3. 开始检测（2分钟）

**精确匹配**（检测完全相同的文件）:
1. 点击"添加目录"选择文件夹
2. 点击"开始扫描"
3. 等待完成后查看结果

**相似度检测**（检测内容相似的图片）:
1. 切换到"相似度检测"标签页
2. 点击"添加目录"选择图片文件夹
3. 调整相似度阈值（默认12，平衡模式）
4. 点击"开始检测"
5. 双击结果查看详情

---

## 💡 常用场景

### 场景1: 清理手机照片重复

**问题**: 手机里有很多相同照片的不同分辨率版本

**解决**:
```bash
# 使用相似度检测
python core/visual_similarity.py D:\Photos --threshold 12 --mode precise
```

**效果**: 找出所有相似照片，手动保留最佳质量版本

### 场景2: 备份去重

**问题**: 多次备份导致大量完全相同的文件

**解决**:
```bash
# 使用精确匹配
python core/duplicate_finder.py D:\Backups --output duplicates.json
```

**效果**: 快速找出并删除完全相同的备份文件

### 场景3: 设计素材整理

**问题**: 下载的设计素材有很多相似版本

**解决**:
```bash
# 宽松模式，容忍裁剪和旋转
python core/visual_similarity.py D:\Design_Assets --threshold 20 --mode precise
```

**效果**: 找出所有相似素材，保留最清晰的版本

---

## ⚙️ 参数调优

### 相似度阈值选择

| 阈值 | 模式 | 适用场景 |
|------|------|---------|
| 5-8 | 严格 | 找几乎相同的图片 |
| 9-15 | 平衡 | 通用去重（推荐） |
| 16-30 | 宽松 | 找相似素材 |

### 检测模式选择

- **快速模式**: 仅pHash，速度快，可能有少量误报
- **精确模式**: pHash+dHash+直方图，速度慢，准确率高（推荐）

### 扫描方式选择

- **全量扫描**: 清空数据库重新扫描（首次使用）
- **增量扫描**: 只处理新增/修改文件（后续更新）

---

## 🎯 GUI功能速查

### 精确匹配标签页

- **数据库**: 自定义SQLite数据库路径
- **输出文件**: JSON结果保存位置
- **并行线程**: 根据硬盘类型调整（HDD:4-8, SSD:8-16）
- **文件类型**: 可选择特定类型或全部
- **自定义后缀**: 输入框中输入，逗号分隔

### 相似度检测标签页

- **相似度阈值**: 滑块调节，实时显示模式
- **检测模式**: 快速/精确单选
- **扫描方式**: 全量/增量单选
- **图片格式**: 勾选需要的格式
- **结果列表**: 点击列标题排序
- **双击**: 查看组详情
- **右键**: 隐藏组、打开文件夹

---

## 🔧 命令行参数速查

### visual_similarity.py

```bash
python core/visual_similarity.py <目录> [选项]

选项:
  --db PATH          数据库路径 (默认: image_similarity.db)
  --threshold N      相似度阈值 (默认: 12)
  --mode MODE        检测模式: fast/precise (默认: precise)
  --incremental      增量扫描
  --output FILE      导出JSON结果
```

### duplicate_finder.py

```bash
python core/duplicate_finder.py <目录> [选项]

选项:
  --db PATH          数据库路径 (默认: file_index.db)
  --output FILE      输出JSON文件 (默认: duplicates.json)
  --workers N        并行线程数 (默认: 自动检测)
  --chunk-size N     读取块大小 (默认: 65536)
```

---

## ❓ 常见问题

### Q: 扫描很慢怎么办？

**A**: 
1. 使用SSD硬盘
2. 增加线程数（`--workers 16`）
3. 使用文件类型过滤减少扫描范围
4. 使用增量扫描（只处理新增文件）

### Q: 如何判断哪个是"最佳质量"？

**A**: 
- 看分辨率（越高越好）
- 看文件大小（通常越大质量越好）
- 看创建时间（最早的可能是原版）

### Q: 可以批量删除吗？

**A**: 
当前版本需要手动选择删除。批量删除功能正在开发中。

### Q: 支持哪些图片格式？

**A**: 
JPG, PNG, GIF, BMP, WebP

### Q: 视频可以吗？

**A**: 
视频相似度检测功能正在开发中，敬请期待。

---

## 📚 更多文档

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 项目结构说明
- [SIMILARITY_USAGE.md](SIMILARITY_USAGE.md) - 相似度检测详细用法
- [README.md](README.md) - 完整项目文档
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 实现总结

---

## 🆘 获取帮助

遇到问题？

1. 查看日志输出
2. 检查依赖是否安装
3. 查看文档中的常见问题
4. 提交Issue反馈

---

**祝您使用愉快！** 🎉
