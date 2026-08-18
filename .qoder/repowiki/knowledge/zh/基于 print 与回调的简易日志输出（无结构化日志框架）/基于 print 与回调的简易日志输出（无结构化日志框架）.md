---
kind: logging_system
name: 基于 print 与回调的简易日志输出（无结构化日志框架）
category: logging_system
scope:
    - '**'
source_files:
    - run_gui.py
    - core/duplicate_finder.py
    - gui_modules/main_window.py
---

## 1. 使用的系统/方案

本仓库**没有引入任何 Python 标准库 `logging` 或第三方日志框架**。所有“日志”输出均通过以下两种原始方式实现：

- **GUI 层**：在 `gui_modules/main_window.py` 中定义 `_log(self, message, level="INFO")`，当前仅作为占位方法（委托给当前标签页），用于在 tkinter 界面的日志区域显示用户操作信息。
- **核心引擎层**：在 `core/duplicate_finder.py` 中定义私有方法 `_log(message)`，内部直接调用 `print()`，并根据运行环境尝试将消息编码为 GBK 后再输出，以兼容 Windows 控制台中文显示。

此外，`run_gui.py` 入口使用裸 `print()` 打印导入错误、异常堆栈等启动期诊断信息。

## 2. 关键文件

- `run_gui.py`：应用启动入口，捕获异常后通过 `print` + `traceback.print_exc()` 输出错误。
- `core/duplicate_finder.py`：核心扫描逻辑，包含 `_log()` 方法及大量 `print()` 进度/统计输出。
- `gui_modules/main_window.py`：主窗口类，提供 `_log()` 占位方法供各标签页调用。

## 3. 架构与约定

- **无全局 logger**：没有模块级 `logger = logging.getLogger(...)` 实例，也没有统一的日志初始化代码。
- **按组件分散输出**：每个功能模块自行决定用 `print()` 输出什么内容，不存在集中路由。
- **回调注入模式**：`DuplicateFinder.__init__` 接受可选参数 `log_callback=None`，并在构造时保存为 `self.log_callback`。但实际 `_log()` 并未调用该回调，而是直接 `print()`，因此回调目前未被使用。
- **级别字段存在但未生效**：GUI 层的 `_log` 签名带 `level="INFO"` 参数，但方法体未根据级别做过滤或差异化处理；核心引擎的 `_log` 完全忽略级别。
- **无结构化字段**：日志输出均为纯文本字符串拼接，不包含 JSON、时间戳、来源模块名、线程 ID 等结构化字段。
- **无持久化 sink**：日志不写入文件、不发送到远程服务，仅输出到标准输出（控制台）或 GUI 日志控件。

## 4. 约定与约束

- **Windows 控制台中文兼容**：`core/duplicate_finder.py` 中的 `_log` 会检测并尝试将消息以 `gbk` 编码再解码输出，以避免中文乱码。
- **错误路径统一走 `sys.exit(1)`**：`run_gui.py` 在导入失败或未知异常时打印错误后退出，属于启动期错误处理的固定模式。
- **日志级别仅为装饰**：虽然部分方法签名保留 `level` 参数，但当前实现未对级别进行任何过滤或分级输出，所有消息一律输出。
- **禁止混用多个日志源**：由于不存在共享 logger，新增日志输出应遵循现有模式——GUI 层调用 `_log()`，核心引擎使用 `_log()` 或 `print()`，避免引入新的 `logging` 实例造成输出分散。

总结：该项目采用最简化的“print 式日志”，没有日志框架、没有配置、没有结构化字段、没有持久化 sink，日志能力仅限于控制台/界面文本框的即时显示。