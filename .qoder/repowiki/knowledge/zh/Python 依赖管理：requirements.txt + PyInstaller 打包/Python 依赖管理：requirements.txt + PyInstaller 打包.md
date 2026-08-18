---
kind: dependency_management
name: Python 依赖管理：requirements.txt + PyInstaller 打包
category: dependency_management
scope:
    - '**'
source_files:
    - requirements.txt
    - 文件重复校验工具.spec
    - build_release.bat
    - run_gui.py
---

## 1. 使用的系统与工具

本项目采用 Python 生态的标准依赖管理方式，核心由以下组件构成：
- **pip + requirements.txt**：通过根目录的 `requirements.txt` 集中声明所有第三方依赖及最低版本约束。
- **PyInstaller**：用于将 Python 应用与依赖打包为独立可执行文件（`.exe`），发布时用户无需安装 Python 环境。
- **虚拟环境 `.venv/`**：项目根目录存在 `.venv` 目录，表明开发时使用 Python 虚拟环境隔离依赖。
- **构建脚本**：`build_release.bat`、`build.sh`、`build.bat` 等脚本封装了依赖安装与打包流程。

## 2. 关键文件

- `requirements.txt`：唯一的外部依赖清单，按功能域分组注释（基础依赖、图片相似度、视频相似度、多版本软件检测等）。
- `文件重复校验工具.spec`：PyInstaller 打包配置文件，显式声明 `hiddenimports`（PIL、imagehash、cv2、numpy、pefile、packaging）和数据资源（`core`、`gui_modules` 目录）。
- `build_release.bat`：发布版打包主脚本，顺序执行 pip 升级、`pip install -r requirements.txt`、安装 PyInstaller、清理旧产物、调用 PyInstaller 生成单文件 exe。
- `run_gui.py`：GUI 入口，被 PyInstaller 作为打包目标。

## 3. 架构与约定

- **单一依赖源**：所有第三方包版本在 `requirements.txt` 中以 `>=` 下限形式声明（如 `Pillow>=9.0.0`、`opencv-python-headless>=4.5.0`、`pefile>=2021.9.3`），没有使用 `poetry.lock`、`pipenv.lock` 或 `Pipfile.lock` 等锁定文件。这意味着依赖版本在每次安装时可能解析到最新兼容版本。
- **可选依赖通过注释区分**：`requirements.txt` 中用注释标明哪些功能是“可选优化”（如 `numpy`、`tqdm`）以及各模块所需的最小依赖集，便于按需安装。
- **打包阶段补充隐藏导入**：由于 PyInstaller 静态分析无法自动发现某些动态导入的库（如 `cv2`、`pefile`、`packaging`），这些依赖在 `.spec` 文件的 `hiddenimports` 中显式声明，确保打包产物包含必要模块。
- **无私有仓库配置**：未发现 `pip.conf`、`setup.cfg`、`pyproject.toml` 中的 index URL 或认证配置，依赖全部从默认 PyPI 获取。
- **无 vendoring**：未使用 `vendor/` 目录或 `pip --no-index --find-links` 等离线依赖策略，依赖均为在线安装。

## 4. 约定与约束

- **依赖声明位置固定**：所有第三方依赖必须添加到根目录 `requirements.txt`，并通过 `>=` 指定最低版本，禁止在代码中直接 `import` 未在清单中声明的包。
- **发布前需重新运行构建脚本**：`build_release.bat` 会先 `pip install -r requirements.txt` 再调用 PyInstaller，因此修改依赖后必须重新执行该脚本才能生成正确的可执行文件。
- **PyInstaller 隐藏导入与依赖清单保持同步**：新增第三方库时，除更新 `requirements.txt` 外，还需在 `文件重复校验工具.spec` 的 `hiddenimports` 中添加对应模块名（如 `PIL`、`imagehash`、`cv2`、`numpy`、`pefile`、`packaging`），否则打包产物运行时可能报 `ImportError`。
- **标准库不列入依赖**：`requirements.txt` 顶部注释明确列出 `os`、`sys`、`hashlib`、`sqlite3`、`json`、`time`、`argparse`、`pathlib`、`concurrent.futures`、`collections`、`typing`、`threading`、`contextlib` 等标准库“无需安装”，仅第三方包需要声明。
- **构建产物隔离**：`build_release.bat` 在打包前删除 `dist/`、`build/`、`*.spec`、`release/` 目录，保证每次发布从零开始，避免历史缓存干扰。
- **无 CI 自动化依赖检查**：`.github/workflows/` 下仅有 `build.yml` 和 `build-and-release.yml`，当前未见对 `requirements.txt` 做 `pip check`、`pip freeze` 对比或安全扫描的强制步骤，依赖一致性主要依赖开发者手动维护。