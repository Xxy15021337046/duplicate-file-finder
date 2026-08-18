---
kind: configuration_system
name: 配置系统 — 硬编码默认值 + GUI 输入字段 + CLI 参数三源并存，无集中配置文件
category: configuration_system
scope:
    - '**'
source_files:
    - core/duplicate_finder.py
    - gui_modules/main_window.py
    - gui_modules/exact_match_tab.py
    - gui_modules/similarity_tab.py
    - gui_modules/video_similarity_tab.py
    - gui_modules/software_version_tab.py
    - gui_modules/detail_window.py
    - run_gui.py
---

## 1. 整体方案

本仓库**没有统一的配置文件加载器**（不存在 `config/`、`*.yaml`、`*.toml`、`.env`、`settings.py` 等集中式配置）。运行时配置通过三种来源并存的方式提供：

1. **Python 源码中的默认值**：核心类构造函数的参数默认值充当“内置默认配置”。
2. **GUI 界面输入字段**：tkinter 的 `StringVar` / `IntVar` / `BooleanVar` 作为用户可编辑的配置项。
3. **命令行参数**：`core/duplicate_finder.py` 的 `argparse` 子命令暴露 CLI 入口。

三者之间是**单向覆盖**关系：CLI 参数 → 构造函数参数 → 源码默认值；GUI 模式不读取 CLI 参数，而是直接实例化引擎并传入 UI 控件的值。

## 2. 关键文件与位置

- **CLI 入口与默认值**：`core/duplicate_finder.py` 的 `DuplicateFinder.__init__` 定义所有可调参数的默认值（`db_path="file_index.db"`、`chunk_size=65536`、`max_workers=None`、`clear_db=True`、`allowed_extensions=None`），并通过 `main()` 中的 `argparse` 暴露 `--db`、`--output`、`--workers`、`--chunk-size` 四个参数。
- **GUI 主窗口默认值**：`gui_modules/main_window.py` 的 `DuplicateFinderGUI.__init__` 中硬编码了共享配置：`self.db_path = "file_index.db"`、`self.output_path = "duplicates.json"`、`self.workers = 8`、`self.similarity_db_path = "image_similarity.db"`、`self.similarity_threshold = 12`、`self.similarity_mode = "precise"`、`self.incremental_scan = False`。
- **各标签页独立配置**：每个功能标签页维护自己的 tk 变量集合：
  - `exact_match_tab.py`：`db_var`、`output_var`、`workers_var`、`filter_*` 布尔变量、`custom_extensions_var`。
  - `similarity_tab.py`：`threshold_var`、`mode_var`、`incremental_var`、`db_path_var`、`format_*` 布尔变量、`custom_format_var`。
  - `video_similarity_tab.py`：`threshold_var`、`db_path_var`、`incremental_var`、`format_*` 布尔变量、`custom_format_var`。
  - `software_version_tab.py`：`db_path_var`、`output_path_var`、`incremental_var`、`format_*` 布尔变量、`custom_format_var`。
- **详情窗口配置**：`gui_modules/detail_window.py` 中的 `DetailWindowConfig` 类以字典形式描述详情窗口的标题、尺寸、列、预览类型等显示配置，由调用方按功能传入。

## 3. 架构与约定

- **无持久化配置存储**：应用重启后所有配置回到源码默认值。唯一持久化的数据是 SQLite 数据库文件（`file_index.db`、`image_similarity.db`、`video_similarity.db`、`software_versions.db`）和 JSON 结果文件（`duplicates.json`、`software_versions.json`），这些被视为**运行产物**而非配置。
- **配置即代码**：所有可调参数均以 Python 字面量或 tkinter 控件默认值的形式写在模块内，新增配置需要修改对应模块源码。
- **每标签页自管配置**：GUI 采用“标签页自治”模式，每个标签页持有自身配置变量并在 `_start_scan` / `start_scan` 中读取并传给底层引擎，主窗口只负责目录选择和调度。
- **CLI 与 GUI 解耦**：`run_gui.py` 仅启动 Tk 主循环并创建 `DuplicateFinderGUI`；`core/duplicate_finder.py` 的 `main()` 是独立的 CLI 入口，两者互不依赖。
- **SQLite PRAGMA 作为内部调优配置**：`_init_database` 中设置 `WAL`、`synchronous=NORMAL`、`cache_size=-64000`、`temp_store=MEMORY`、`mmap_size=268435456`、`busy_timeout=60000` 等数据库级行为参数，属于引擎内部优化，不对用户暴露。

## 4. 约定与约束

- **默认值必须为不可变字面量**：所有默认值在源码中以字符串、整数、布尔值或 `None` 形式声明，避免可变默认参数带来的副作用。
- **GUI 控件变量命名统一**：路径类使用 `*_var` 后缀（如 `db_path_var`、`output_path_var`），开关类使用 `*_var` 并配合 `BooleanVar`/`IntVar`/`StringVar`，格式过滤使用 `format_*` 前缀加扩展名小写。
- **增量扫描开关统一为单选按钮对**：相似度与软件版本检测均提供“全量扫描”和“增量扫描（仅新增/修改）”两个互斥选项，默认值为 `False`（全量）。
- **文件类型过滤遵循“全选 + 常用格式 + 自定义后缀”三段式 UI**：每个支持格式过滤的标签页都提供 `format_all` 复选框、一组预设格式复选框和一个 `custom_format_var` 文本框，解析时合并为扩展名集合。
- **线程数建议文案作为软约束**：精确匹配标签页的 Spinbox 旁标注“(建议: HDD用4-8, SSD用8-16)”，但实际仍允许用户输入任意 1–32 的整数值，无前端校验强制上限。
- **无环境变量注入**：整个仓库未出现 `os.environ`、`python-dotenv`、`pydantic-settings` 等 env 相关用法，配置不通过环境变量注入。
- **打包产物不包含配置模板**：根目录仅有 `requirements.txt` 和 PyInstaller spec（`文件重复校验工具.spec`），没有 `.env.example`、`config.yaml` 等模板文件。