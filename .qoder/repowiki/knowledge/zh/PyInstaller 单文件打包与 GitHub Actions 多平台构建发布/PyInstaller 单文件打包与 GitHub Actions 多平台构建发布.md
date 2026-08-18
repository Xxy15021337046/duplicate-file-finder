---
kind: build_system
name: PyInstaller 单文件打包与 GitHub Actions 多平台构建发布
category: build_system
scope:
    - '**'
source_files:
    - requirements.txt
    - 文件重复校验工具.spec
    - build.sh
    - build.bat
    - build_release.bat
    - .github/workflows/build.yml
    - .github/workflows/build-and-release.yml
---

## 1. 构建系统概览

本项目采用 **PyInstaller** 作为唯一的打包工具，将 Python 桌面应用（tkinter GUI + 核心检测引擎）打包为跨平台独立可执行文件。构建流程由本地脚本（`build.sh`、`build.bat`、`build_release.bat`）和 GitHub Actions CI（`.github/workflows/`）共同驱动。

- 开发/测试阶段：使用 `run_gui.py` 直接运行 Python 源码。
- 本地打包：通过 `build.sh` / `build.bat` 调用 PyInstaller 生成单文件可执行程序。
- 发布打包：`build_release.bat` 额外生成带版本号命名的发布包并附带文档。
- CI/CD：GitHub Actions 在 push `v*` 标签时自动触发三平台（Windows/Linux/macOS）并行构建，并上传至 GitHub Releases。

## 2. 关键文件

- `requirements.txt`：声明所有运行时依赖（Pillow、imagehash、opencv-python-headless、pefile、packaging、watchdog、tqdm、numpy），是构建环境的唯一依赖来源。
- `文件重复校验工具.spec`：PyInstaller 的 spec 配置文件，定义入口 `run_gui.py`、数据目录 `core` 与 `gui_modules`、隐藏导入（PIL、imagehash、cv2、numpy、pefile、packaging）、UPX 压缩等。
- `build.sh`：Linux/macOS 一键打包脚本，包含环境检查、依赖安装、清理 dist/build、调用 PyInstaller 并输出彩色进度提示。
- `build.bat`：Windows 一键打包脚本，功能与 `build.sh` 对应，但路径分隔符使用 `;`（Windows 风格）。
- `build_release.bat`：发布专用脚本，产物命名为 `文件重复校验工具-v4.0.0.exe`，并复制 README.md、QUICK_START.md、docs/*.md 到 `release/` 目录。
- `.github/workflows/build.yml`：三平台并行构建流水线，产物按 `文件重复校验工具-${{ github.ref_name }}-{windows|linux|macos}.zip` 命名并通过 `softprops/action-gh-release@v1` 发布。
- `.github/workflows/build-and-release.yml`：简化版流水线，仅构建 Windows 平台，使用 `actions/cache@v4` 缓存 pip 包，生成 SHA256SUMS.txt 并借助 `softprops/action-gh-release@v2` 的 `generate_release_notes: true` 自动生成 Release Notes。

## 3. 架构与约定

### 3.1 打包参数约定
所有构建脚本统一使用以下 PyInstaller 参数组合：
- `--windowed`：不显示控制台窗口（GUI 应用）。
- `--onefile`：打包为单个可执行文件。
- `--add-data "core;core"` / `--add-data "gui_modules;gui_modules"`：将两个 Python 包作为数据目录嵌入，确保运行时可被动态 import。
- `--hidden-import=PIL,imagehash,cv2,numpy,pefile,packaging`：显式声明所有第三方库，避免 PyInstaller 静态分析遗漏。
- Windows 下额外添加 `--hidden-import=pefile` 与 `--hidden-import=packaging`；Linux/macOS 未包含这两项（CI 中 Linux/macOS 也未加）。

### 3.2 版本与命名约定
- 本地开发构建：产物名为 `文件重复校验工具`。
- 发布构建：`build_release.bat` 硬编码为 `文件重复校验工具-v4.0.0`（当前版本 v4.0.0）。
- CI 构建：名称模板为 `文件重复校验工具-${{ github.ref_name }}`，即从 Git tag 注入版本号。
- 发布压缩包命名：`文件重复校验工具-${{ github.ref_name }}-{windows|linux|macos}.zip`。

### 3.3 构建产物结构
```
dist/
└── 文件重复校验工具[.exe]          # PyInstaller 生成的单文件可执行
release/                            # build_release.bat 产出
├── 文件重复校验工具-v4.0.0.exe
├── README.md
├── QUICK_START.md
└── docs/
    └── *.md                        # 所有文档
```

### 3.4 CI 触发与发布策略
- 触发条件：push 匹配 `v*` 的 Git tag，或手动 `workflow_dispatch`。
- 并发构建：`build.yml` 同时启动 `build-windows`、`build-linux`、``build-macos` 三个 job。
- 发布：每个 job 在 tag 推送时调用 `softprops/action-gh-release` 创建 Release，读取 `docs/RELEASE_NOTES.md` 作为 release body（`build.yml`）或由 action 自动生成（`build-and-release.yml`）。
- artifact 保留：`build-and-release.yml` 设置 `retention-days: 30`。

### 3.5 依赖管理约束
- 所有第三方依赖必须声明于 `requirements.txt`，构建脚本均通过 `pip install -r requirements.txt` 安装。
- PyInstaller 不在 `requirements.txt` 中，而是每次构建时临时安装（`pip install pyinstaller`），避免污染项目依赖。
- 可选依赖（如 numpy、tqdm）仍写入 requirements.txt，但代码中对缺失场景有兼容处理（例如注释说明核心功能无需第三方库）。

## 4. 约定与约束

- **Python 版本**：CI 固定使用 Python 3.10（`setup-python@v4/v5 with python-version: '3.10'`），本地脚本要求 Python 3.6+。
- **构建前清理**：所有脚本在打包前删除 `dist/`、`build/` 及旧 `.spec` 文件，保证增量构建干净。
- **错误处理**：脚本对 `python --version`、`pip --version`、`pip install`、PyInstaller 返回值进行检查，失败时中止并给出中文提示。
- **跨平台差异**：`--add-data` 参数在 Windows 使用分号 `core;core`，在 Linux/macOS 使用冒号 `core:core`；CI 中各平台分别编写对应命令。
- **Release 产物完整性**：CI 会复制 `README.md`、`QUICK_START.md`、`docs/*.md` 到 release 包；`build_release.bat` 还生成 `SHA256SUMS.txt`（在 `build-and-release.yml` 中）。
- **无 Docker 化**：项目未使用 Docker 构建，完全依赖宿主机的 Python 环境与 PyInstaller。
- **无 Makefile**：构建逻辑全部以 shell/batch 脚本实现，未引入 Makefile 或其他构建系统。

## 5. 已知局限

- 版本号在 `build_release.bat` 中硬编码为 `v4.0.0`，未从 Git tag 或 `__version__` 自动推导，存在与 CI 不一致的风险。
- Linux/macOS 构建未包含 `pefile` 与 `packaging` 的 `--hidden-import`，若这些模块在运行期被动态加载可能失败（尽管当前 CI 能成功构建）。
- 未配置签名（`codesign_identity=None`、`icon='NONE'`），发布产物无数字签名与图标。
- 未使用 `pyproject.toml` / `setup.py`，纯依赖 `requirements.txt` 进行依赖声明。
