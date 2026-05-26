# 项目文档索引

本文档集记录了"文件重复校验工具"的完整技术规格和实现细节，用于后续开发参考和功能还原。

---

##  文档列表

### 1. [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) - 项目总体架构文档 (18KB)
**适用对象**: 新加入的开发者、项目经理

**内容概要**:
- 项目概述与目标
- 技术栈介绍
- 目录结构与分层架构
- 三大核心功能模块概览
- 关键技术实现原理
- 性能优化要点
- 常见问题解决方案

**阅读建议**: 首次接触项目时必读，快速了解项目全貌

---

### 2. [EXACT_MATCH_SPEC.md](./EXACT_MATCH_SPEC.md) - 精确匹配功能详细规格 (17KB)
**适用对象**: 后端开发者、算法工程师

**内容概要**:
- 三级过滤策略详解（大小→部分哈希→完整哈希）
- 并行处理架构（线程池/进程池）
- 增量扫描机制
- 数据库表设计与查询优化
- GUI界面规范（列定义、交互行为）
- API参考与工具函数
- 性能基准测试数据

**关键知识点**:
- MD5哈希算法
- 分块读取大文件
- SQLite索引优化
- 并发编程最佳实践

---

### 3. [IMAGE_SIMILARITY_SPEC.md](./IMAGE_SIMILARITY_SPEC.md) - 图片相似度检测详细规格 (22KB)
**适用对象**: 图像处理开发者、算法工程师

**内容概要**:
- 感知哈希(pHash)算法原理与实现
- 汉明距离计算与相似度度量
- 阈值配置指南（严格/平衡/宽松模式）
- 并查集聚类算法
- 数据库设计与高效查询策略
- 图片预览与缓存机制
- 性能优化技巧

**关键知识点**:
- DCT离散余弦变换
- pHash vs aHash vs dHash对比
- 图片缩放与重采样
- LRU缓存策略

---

### 4. [VIDEO_SIMILARITY_SPEC.md](./VIDEO_SIMILARITY_SPEC.md) - 视频相似度检测详细规格 (25KB)
**适用对象**: 视频处理开发者、多媒体工程师

**内容概要**:
- 视频指纹生成流程
- 动态关键帧提取策略（根据时长调整）
- 多帧相似度平均算法
- 视频元数据缓存
- 多帧预览UI实现（主图+缩略图）
- 闭包问题与工厂函数模式
- 性能瓶颈分析与优化

**关键知识点**:
- OpenCV视频处理
- 关键帧提取算法
- 视频编码格式支持
- 异步加载与UI刷新

---

### 5. [GUI_SPECIFICATION.md](./GUI_SPECIFICATION.md) - GUI界面规范文档 (20KB)
**适用对象**: UI开发者、前端工程师

**内容概要**:
- 总体设计原则（一致性、简洁性、响应性）
- 主窗口布局与组件规范
- Treeview列配置模板（stretch参数详解）
- 详情窗口布局模式
- Tooltip实现
- 对话框规范
- 响应式设计与性能优化

**关键知识点**:
- Tkinter/ttk组件使用
- pack/grid布局管理
- 事件绑定与回调
- 自定义样式配置
- 常见UI bug解决方案

---

### 6. [COMMON_COMPONENTS_GUIDE.md](./COMMON_COMPONENTS_GUIDE.md) - 公共组件使用指南 (21KB)
**适用对象**: 所有开发者

**内容概要**:
- 公共组件架构设计（配置驱动）
- DetailWindowConfig配置详解
- 工厂函数使用示例
- 格式化函数编写规范
- 事件处理通用模式
- 预览功能扩展方法
- 如何添加新页签

**关键知识点**:
- 配置驱动架构
- 工厂设计模式
- 代码复用与DRY原则
- 可扩展性设计

---

## 🎯 快速导航

### 按场景查找

#### 场景1: 修复列宽不生效的bug
1. 查看 [GUI_SPECIFICATION.md](./GUI_SPECIFICATION.md) → "10.1 列宽不生效"
2. 查看 [COMMON_COMPONENTS_GUIDE.md](./COMMON_COMPONENTS_GUIDE.md) → "10.1 列宽设置不生效"

#### 场景2: 调整相似度阈值
1. 查看 [IMAGE_SIMILARITY_SPEC.md](./IMAGE_SIMILARITY_SPEC.md) → "2.3 相似度阈值配置"
2. 查看 [VIDEO_SIMILARITY_SPEC.md](./VIDEO_SIMILARITY_SPEC.md) → "2.3 视频相似度计算"

#### 场景3: 新增一个功能页签
1. 查看 [COMMON_COMPONENTS_GUIDE.md](./COMMON_COMPONENTS_GUIDE.md) → "11. 扩展新页签"
2. 参考现有配置模板

#### 场景4: 优化扫描性能
1. 查看 [EXACT_MATCH_SPEC.md](./EXACT_MATCH_SPEC.md) → "7. 性能基准"
2. 查看 [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) → "7. 性能优化要点"

#### 场景5: 修复视频预览点击无效
1. 查看 [VIDEO_SIMILARITY_SPEC.md](./VIDEO_SIMILARITY_SPEC.md) → "9.4 视频预览显示相同帧"
2. 查看 [COMMON_COMPONENTS_GUIDE.md](./COMMON_COMPONENTS_GUIDE.md) → "10.4 视频预览点击无效"

---

##  阅读顺序建议

### 新人入门路径
1. **第一天**: [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) - 了解项目全貌
2. **第二天**: [GUI_SPECIFICATION.md](./GUI_SPECIFICATION.md) - 熟悉界面结构
3. **第三天**: 选择专精方向
   - 精确匹配: [EXACT_MATCH_SPEC.md](./EXACT_MATCH_SPEC.md)
   - 图片相似度: [IMAGE_SIMILARITY_SPEC.md](./IMAGE_SIMILARITY_SPEC.md)
   - 视频相似度: [VIDEO_SIMILARITY_SPEC.md](./VIDEO_SIMILARITY_SPEC.md)
4. **第四天**: [COMMON_COMPONENTS_GUIDE.md](./COMMON_COMPONENTS_GUIDE.md) - 掌握公共组件

### 问题排查路径
1. 先在对应功能文档中搜索关键词
2. 查看"常见问题排查"章节
3. 参考"最佳实践"章节

---

## 🔧 文档维护

### 更新原则
- **准确性**: 文档必须与实际代码保持一致
- **完整性**: 关键逻辑必须有文档说明
- **可读性**: 使用清晰的标题层级和代码示例
- **及时性**: 代码变更后同步更新文档

### 版本历史
| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v4.0.0 | 2026-05-26 | 新增多版本软件检测功能，添加PE元数据提取、智能软件识别、语义化版本比较、文件格式过滤等功能 |
| v3.0.0 | 2026-05-26 | 初始版本发布，包含6个核心文档 |

### 贡献指南
如需补充或修改文档：
1. 确保内容准确无误
2. 遵循现有文档风格
3. 添加示例代码和图表
4. 更新版本历史记录

---

## 📞 支持与反馈

如有文档相关问题：
1. 检查是否有拼写错误或表述不清
2. 确认是否在其他章节已有说明
3. 提出改进建议或补充需求

---

*文档集版本: v4.0.0*  
*最后更新: 2026-05-26*  
*维护者: Qoder AI Assistant*
