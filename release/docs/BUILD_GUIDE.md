# 打包指南 - 生成可执行文件

本文档说明如何将项目打包成独立的可执行文件，方便在没有Python环境的计算机上使用。

---

##  打包方式

### 方法一：使用自动打包脚本（推荐）

#### Windows系统

1. **双击运行** `build.bat` 文件
2. 等待脚本自动完成以下操作：
   - 检测Python环境
   - 安装项目依赖
   - 安装PyInstaller
   - 清理旧文件
   - 打包可执行程序
3. 打包完成后，在 `dist` 文件夹中找到 `文件重复校验工具.exe`

#### Linux/macOS系统

1. **赋予执行权限**：
   ```bash
   chmod +x build.sh
   ```

2. **运行脚本**：
   ```bash
   ./build.sh
   ```

3. 打包完成后，在 `dist` 文件夹中找到 `文件重复校验工具` 可执行文件

---

### 方法二：手动打包（高级用户）

#### 1. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装PyInstaller
pip install pyinstaller
```

#### 2. 执行打包命令

**Windows**:
```bash
pyinstaller --name="文件重复校验工具" ^
    --windowed ^
    --onefile ^
    --add-data "core;core" ^
    --add-data "gui_modules;gui_modules" ^
    --hidden-import=PIL ^
    --hidden-import=imagehash ^
    --hidden-import=cv2 ^
    --hidden-import=numpy ^
    run_gui.py
```

**Linux/macOS**:
```bash
pyinstaller --name="文件重复校验工具" \
    --windowed \
    --onefile \
    --add-data "core:core" \
    --add-data "gui_modules:gui_modules" \
    --hidden-import=PIL \
    --hidden-import=imagehash \
    --hidden-import=cv2 \
    --hidden-import=numpy \
    run_gui.py
```

#### 3. 获取可执行文件

打包完成后，在 `dist` 目录中找到生成的可执行文件。

---

## 📋 打包参数说明

| 参数 | 说明 |
|------|------|
| `--name` | 可执行文件名称 |
| `--windowed` | 不显示控制台窗口（GUI程序必需） |
| `--onefile` | 打包成单个exe文件（方便分发） |
| `--add-data` | 添加额外数据文件（格式：源路径;目标路径） |
| `--hidden-import` | 显式导入隐藏模块（避免遗漏依赖） |

---

## ⚙️ 常见问题

### Q1: 打包后exe文件很大怎么办？

**原因**: `--onefile` 模式会将所有依赖打包到一个文件中

**解决方案**:
- 使用 `--onedir` 替代 `--onefile`（生成文件夹，体积更小）
- 使用UPX压缩（需单独安装UPX）

```bash
pyinstaller --name="文件重复校验工具" --windowed --onedir ...
```

### Q2: 打包后运行闪退？

**可能原因**:
1. 缺少依赖模块
2. 路径问题导致找不到资源文件

**解决方案**:
1. 先不带 `--windowed` 参数打包，查看错误信息
2. 检查 `--add-data` 参数是否正确
3. 确保所有隐藏模块都已添加

```bash
# 调试模式（显示控制台）
pyinstaller --name="文件重复校验工具" --onefile ...

# 运行生成的exe，查看错误信息
```

### Q3: 如何减小exe体积？

**优化方法**:

1. **排除不必要的模块**:
   ```bash
   --exclude-module=tkinter.test)
   --exclude-module=pip
   --exclude-module=setuptools
   ```

2. **使用UPX压缩**:
   ```bash
   # 下载UPX: https://upx.github.io/
   pyinstaller --upx-dir=/path/to/upx ...
   ```

3. **使用虚拟环境**:
   ```bash
   # 创建干净的虚拟环境
   python -m venv build_env
   build_env\Scripts\activate
   pip install -r requirements.txt
   pip install pyinstaller
   
   # 在虚拟环境中打包
   pyinstaller ...
   ```

### Q4: macOS打包后无法打开？

**原因**: macOS安全策略阻止未签名应用

**解决方案**:
1. 右键点击应用 → 打开
2. 或在终端中运行：
   ```bash
   xattr -cr dist/文件重复校验工具.app
   ```

### Q5: Linux打包后在其他发行版无法运行？

**原因**: glibc版本不兼容

**解决方案**:
- 在最低版本的系统上打包
- 或使用Docker容器打包

---

##  最佳实践

### 1. 使用虚拟环境打包

```bash
# 创建干净的虚拟环境
python -m venv build_env

# 激活虚拟环境
# Windows:
build_env\Scripts\activate
# Linux/macOS:
source build_env/bin/activate

# 安装最小依赖
pip install -r requirements.txt
pip install pyinstaller

# 打包
pyinstaller ...

# 退出虚拟环境
deactivate
```

### 2. 测试打包结果

打包完成后，务必在以下环境测试：
- ✅ 开发机（有Python环境）
- ✅ 干净虚拟机（无Python环境）
- ✅ 不同Windows版本（Win7/Win10/Win11）

### 3. 版本号管理

建议在打包前更新版本号：

```python
# 在 run_gui.py 或 main_window.py 中添加
__version__ = "3.0.0"
```

并在打包命令中使用：

```bash
pyinstaller --name="文件重复校验工具-v3.0.0" ...
```

---

## 📊 打包后文件结构

### --onefile 模式（单文件）

```
dist/
└── 文件重复校验工具.exe    # 单个可执行文件（约100-200MB）
```

**优点**: 
- 方便分发
- 用户只需复制一个文件

**缺点**:
- 体积较大
- 首次启动较慢（需解压）

### --onedir 模式（文件夹）

```
dist/
└── 文件重复校验工具/
    ├── 文件重复校验工具.exe
    ├── PIL/                 # 依赖库
    ├── cv2/
    ├── numpy/
    ├── core/                # 项目模块
    ├── gui_modules/
    ── ...                  # 其他依赖
```

**优点**:
- 总体积较小
- 启动速度快

**缺点**:
- 文件较多，不便分发
- 用户需复制整个文件夹

---

##  高级配置

### 自定义图标

1. 准备 `.ico` 文件（Windows）或 `.icns` 文件（macOS）
2. 添加到打包命令：

```bash
# Windows
pyinstaller --icon=myicon.ico ...

# macOS
pyinstaller --icon=myicon.icns ...
```

### 添加版本信息（Windows）

创建 `version.txt` 文件：

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(3, 0, 0, 0),
    prodvers=(3, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904b0',
        [StringStruct(u'CompanyName', u'Your Company'),
        StringStruct(u'FileDescription', u'文件重复校验工具'),
        StringStruct(u'FileVersion', u'3.0.0'),
        StringStruct(u'InternalName', u'FileDuplicateChecker'),
        StringStruct(u'LegalCopyright', u'Copyright © 2026'),
        StringStruct(u'OriginalFilename', u'文件重复校验工具.exe'),
        StringStruct(u'ProductName', u'文件重复校验工具'),
        StringStruct(u'ProductVersion', u'3.0.0')])
    ])
  ]
)
```

然后在打包命令中添加：

```bash
pyinstaller --version-file=version.txt ...
```

---

##  更新日志

**v1.0** (2026-05-25):
- 初始版本发布
- 支持Windows/Linux/macOS自动打包
- 提供完整的打包文档

---

**最后更新**: 2026-05-25  
**维护者**: Qoder AI Assistant
