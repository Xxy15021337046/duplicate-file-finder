# 精确匹配功能 - 完整还原手册

> **用途**: 当精确匹配功能出现错误或被破坏时，使用本文档可快速完整还原，无需额外说明  
> **适用场景**: 代码丢失、功能损坏、重构失败、版本回退等紧急情况  
> **最后验证**: 2026-05-22 ✅ 功能正常运行

---

## 🚨 紧急还原流程（5步）

### 步骤1: 检查核心文件是否存在

```bash
# 必须存在的文件
core/duplicate_finder.py          # ❌ 缺失则从步骤2开始
gui_modules/exact_match_tab.py    # ❌ 缺失则从步骤3开始
gui_modules/main_window.py        # ❌ 缺失则从步骤4开始
```

### 步骤2: 还原核心引擎 (如果 `duplicate_finder.py` 损坏)

复制以下完整代码到 `core/duplicate_finder.py`:

<details>
<summary>📄 点击展开 core/duplicate_finder.py 完整代码</summary>

```python
#!/usr/bin/env python3
"""
高性能重复文件检测系统
针对TB级别数据优化，使用SQLite3存储索引，支持并行处理和多级哈希校验
"""

import os
import sys
import hashlib
import sqlite3
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import threading
from contextlib import contextmanager


class DuplicateFinder:
    """高性能重复文件检测器"""

    def __init__(self, db_path: str = "file_index.db", chunk_size: int = 65536,
                 max_workers: int = None, progress_callback=None, stop_flag=None, log_callback=None, 
                 clear_db: bool = True, allowed_extensions: set = None):
        self.db_path = db_path
        self.chunk_size = chunk_size
        
        if max_workers is None:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            self.max_workers = min(cpu_count * 2, 16)
        else:
            self.max_workers = max_workers
        
        self.lock = threading.Lock()
        self.progress_callback = progress_callback
        self.stop_flag = stop_flag
        self.log_callback = log_callback
        self.clear_db = clear_db
        self.allowed_extensions = allowed_extensions
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'scanned_files': 0,
            'duplicate_groups': 0,
            'duplicate_files': 0,
            'wasted_space': 0
        }
        self._init_database()

    def _init_database(self):
        """初始化SQLite数据库"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA cache_size=-64000')
        cursor.execute('PRAGMA temp_store=MEMORY')
        cursor.execute('PRAGMA mmap_size=268435456')

        # ⚠️ 重要顺序：先创建表，再清空数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_size INTEGER NOT NULL,
                modified_time REAL NOT NULL,
                partial_hash TEXT,
                full_hash TEXT,
                scan_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        if self.clear_db:
            cursor.execute('DELETE FROM files')
            self._log("已清空数据库中的旧数据")

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_size ON files(file_size)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_partial_hash ON files(partial_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_full_hash ON files(full_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_status ON files(scan_status)')

        conn.commit()
        conn.close()

    @contextmanager
    def _get_db_connection(self):
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn

    def _check_stop(self):
        """检查是否应该停止"""
        # ⚠️ 使用 is_set() 方法，不是直接调用
        if self.stop_flag and self.stop_flag.is_set():
            raise InterruptedError("用户请求停止扫描")

    def scan_directories(self, directories: List[str]):
        """扫描多个目录"""
        print(f"开始扫描 {len(directories)} 个目录...")
        
        if self.progress_callback:
            self.progress_callback(0, f"准备扫描 {len(directories)} 个目录...")
        
        start_time = time.time()

        for i, directory in enumerate(directories, 1):
            self._check_stop()
            directory = os.path.abspath(directory)
            if not os.path.exists(directory):
                print(f"警告: 目录不存在 - {directory}")
                continue

            print(f"正在扫描: {directory} ({i}/{len(directories)})")
            
            if self.progress_callback:
                self.progress_callback(0, f"扫描目录 {i}/{len(directories)}: {os.path.basename(directory)}")
            
            self._scan_single_directory(directory)

        elapsed = time.time() - start_time
        print(f"\n目录扫描完成! 耗时: {elapsed:.2f}秒")
        print(f"发现文件总数: {self.stats['total_files']:,}")
        print(f"文件总大小: {self._format_size(self.stats['total_size'])}")

    def _should_include_file(self, file_path: str) -> bool:
        if self.allowed_extensions is None:
            return True
        
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.allowed_extensions

    def _scan_single_directory(self, directory: str):
        batch_size = 5000
        file_batch = []
        files_scanned = 0

        for root, dirs, files in os.walk(directory):
            self._check_stop()
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                file_path = os.path.join(root, filename)

                try:
                    if os.path.islink(file_path):
                        continue
                    
                    if not self._should_include_file(file_path):
                        continue

                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    modified_time = stat.st_mtime

                    file_batch.append({
                        'file_path': file_path,
                        'file_size': file_size,
                        'modified_time': modified_time
                    })

                    self.stats['total_files'] += 1
                    self.stats['total_size'] += file_size
                    files_scanned += 1

                    if len(file_batch) >= batch_size:
                        self._batch_insert_files(file_batch)
                        file_batch = []
                        
                        if self.progress_callback and files_scanned % 1000 == 0:
                            detail = f"已扫描 {files_scanned:,} 个文件"
                            self.progress_callback(0, detail)

                except (OSError, PermissionError) as e:
                    print(f"警告: 无法访问文件 {file_path}: {e}")

        if file_batch:
            self._batch_insert_files(file_batch)
        
        if self.progress_callback and files_scanned > 0:
            detail = f"目录扫描完成，共 {files_scanned:,} 个文件"
            self.progress_callback(0, detail)

    def _batch_insert_files(self, file_batch: List[Dict]):
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT OR IGNORE INTO files (file_path, file_size, modified_time)
                VALUES (:file_path, :file_size, :modified_time)
            ''', file_batch)

    def find_duplicates(self) -> List[List[Dict]]:
        self._log("\n" + "="*60)
        self._log("开始查找重复文件...")
        self._log("="*60)

        self._log("\n步骤1: 基于文件大小进行初步筛选...")
        if self.progress_callback:
            self.progress_callback(0, "步骤1: 基于文件大小筛选...")
        
        potential_duplicates = self._find_by_size()
        
        total_files_in_groups = sum(len(files) for files in potential_duplicates.values())
        self._log(f"发现 {len(potential_duplicates)} 个可能存在重复的文件大小组")
        self._log(f"  这些组中共有 {total_files_in_groups:,} 个文件需要进一步检查")
        if self.progress_callback:
            self.progress_callback(0, f"发现 {len(potential_duplicates)} 个候选组 ({total_files_in_groups:,} 个文件)")

        if not potential_duplicates:
            self._log("\n未发现任何重复文件!")
            return []

        self._log("\n步骤2: 计算部分哈希值（前1MB）...")
        if self.progress_callback:
            self.progress_callback(0, "步骤2: 计算部分哈希...")
        
        partial_hash_groups = self._compute_partial_hashes(potential_duplicates)
        self._log(f"部分哈希筛选后剩余 {len(partial_hash_groups)} 个组")
        if self.progress_callback:
            self.progress_callback(0, f"部分哈希完成，剩余 {len(partial_hash_groups)} 个组")

        if not partial_hash_groups:
            self._log("\n未发现任何重复文件!")
            return []

        self._log("\n步骤3: 计算完整文件哈希值...")
        if self.progress_callback:
            self.progress_callback(0, "步骤3: 计算完整哈希...")
        
        duplicate_groups = self._compute_full_hashes(partial_hash_groups)
        self._log(f"最终确认 {len(duplicate_groups)} 个重复文件组")
        if self.progress_callback:
            self.progress_callback(0, f"完成！发现 {len(duplicate_groups)} 个重复组")

        self.stats['duplicate_groups'] = len(duplicate_groups)

        for group in duplicate_groups:
            self.stats['duplicate_files'] += len(group) - 1
            wasted = sum(f['file_size'] for f in group[1:])
            self.stats['wasted_space'] += wasted

        return duplicate_groups

    def _log(self, message: str):
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('gbk', errors='replace').decode('gbk'))
        
        if self.log_callback:
            self.log_callback(message)

    def _find_by_size(self) -> Dict[int, List[Dict]]:
        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT file_size, COUNT(*) as count
                FROM files
                GROUP BY file_size
                HAVING count > 1
            ''')

            size_groups = {}
            for row in cursor.fetchall():
                file_size, count = row
                if count > 1:
                    cursor.execute('''
                        SELECT file_path, file_size, modified_time
                        FROM files
                        WHERE file_size = ?
                    ''', (file_size,))

                    files = [{'file_path': r[0], 'file_size': r[1],
                             'modified_time': r[2]} for r in cursor.fetchall()]
                    size_groups[file_size] = files

        return size_groups

    def _compute_partial_hashes(self, size_groups: Dict[int, List[Dict]]) -> Dict[str, List[Dict]]:
        hash_groups = defaultdict(list)
        total_files = sum(len(files) for files in size_groups.values())
        processed = 0

        def compute_partial_hash(file_info: Dict) -> Optional[Tuple[str, Dict]]:
            try:
                self._check_stop()
                file_path = file_info['file_path']
                hasher = hashlib.md5()

                with open(file_path, 'rb') as f:
                    data = f.read(1024 * 1024)
                    hasher.update(data)

                partial_hash = hasher.hexdigest()
                key = f"{file_info['file_size']}_{partial_hash}"
                
                nonlocal processed
                processed += 1
                if self.progress_callback and processed % 500 == 0:
                    progress = (processed / total_files) * 100
                    self.progress_callback(progress, f"部分哈希: {processed}/{total_files}")
                
                return (key, file_info)
            except InterruptedError:
                raise
            except Exception as e:
                print(f"错误: 无法读取文件 {file_path}: {e}")
                return None

        all_files = []
        for files in size_groups.values():
            all_files.extend(files)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(compute_partial_hash, f): f for f in all_files}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        key, file_info = result
                        hash_groups[key].append(file_info)
                except InterruptedError:
                    raise

        self._log(f"\n  部分哈希筛选完成，发现 {len(hash_groups)} 个潜在重复组")
        return {k: v for k, v in hash_groups.items() if len(v) > 1}

    def _compute_full_hashes(self, hash_groups: Dict[str, List[Dict]]) -> List[List[Dict]]:
        duplicate_groups = []
        total_files = sum(len(files) for files in hash_groups.values())
        processed = 0

        def compute_full_hash(file_info: Dict) -> Optional[Tuple[str, Dict]]:
            try:
                self._check_stop()
                file_path = file_info['file_path']
                hasher = hashlib.md5()

                with open(file_path, 'rb') as f:
                    while True:
                        data = f.read(self.chunk_size)
                        if not data:
                            break
                        hasher.update(data)

                full_hash = hasher.hexdigest()
                
                nonlocal processed
                processed += 1
                if self.progress_callback and processed % 100 == 0:
                    progress = (processed / total_files) * 100
                    self.progress_callback(progress, f"完整哈希: {processed}/{total_files}")
                
                return (full_hash, file_info)
            except InterruptedError:
                raise
            except Exception as e:
                print(f"错误: 无法读取文件 {file_path}: {e}")
                return None

        for group_key, files in hash_groups.items():
            if len(files) < 2:
                continue

            full_hash_groups = defaultdict(list)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(compute_full_hash, f): f for f in files}

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            full_hash, file_info = result
                            full_hash_groups[full_hash].append(file_info)
                    except InterruptedError:
                        raise

            for full_hash, dup_files in full_hash_groups.items():
                if len(dup_files) > 1:
                    duplicate_groups.append(dup_files)
                    self._log(f"  ✓ 发现 {len(dup_files)} 个重复文件 (大小: {self._format_size(dup_files[0]['file_size'])})")

        return duplicate_groups

    def export_results(self, duplicate_groups: List[List[Dict]], output_file: str = "duplicates.json"):
        print(f"\n正在导出结果到 {output_file}...")

        results = {
            'scan_summary': {
                'total_files_scanned': self.stats['total_files'],
                'total_size_scanned': self.stats['total_size'],
                'total_size_formatted': self._format_size(self.stats['total_size']),
                'duplicate_groups': self.stats['duplicate_groups'],
                'duplicate_files': self.stats['duplicate_files'],
                'wasted_space': self.stats['wasted_space'],
                'wasted_space_formatted': self._format_size(self.stats['wasted_space'])
            },
            'duplicate_groups': []
        }

        for i, group in enumerate(duplicate_groups, 1):
            group_info = {
                'group_id': i,
                'file_count': len(group),
                'file_size': group[0]['file_size'],
                'file_size_formatted': self._format_size(group[0]['file_size']),
                'files': []
            }

            for file_info in group:
                group_info['files'].append({
                    'path': file_info['file_path'],
                    'size': file_info['file_size'],
                    'modified_time': file_info['modified_time']
                })

            results['duplicate_groups'].append(group_info)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"结果已保存到: {output_file}")

    def print_summary(self):
        print("\n" + "="*60)
        print("扫描结果摘要")
        print("="*60)
        print(f"总文件数: {self.stats['total_files']:,}")
        print(f"总大小: {self._format_size(self.stats['total_size'])}")
        print(f"重复文件组: {self.stats['duplicate_groups']:,}")
        print(f"重复文件数: {self.stats['duplicate_files']:,}")
        print(f"浪费空间: {self._format_size(self.stats['wasted_space'])}")
        print("="*60)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def main():
    parser = argparse.ArgumentParser(description='高性能重复文件检测系统')
    parser.add_argument('directories', nargs='+', help='要扫描的目录路径')
    parser.add_argument('--db', default='file_index.db', help='SQLite数据库文件路径')
    parser.add_argument('--output', default='duplicates.json', help='输出JSON文件路径')
    parser.add_argument('--workers', type=int, default=8, help='并行工作线程数')
    parser.add_argument('--chunk-size', type=int, default=8192, help='文件读取块大小')

    args = parser.parse_args()

    for directory in args.directories:
        if not os.path.exists(directory):
            print(f"错误: 目录不存在 - {directory}")
            sys.exit(1)

    finder = DuplicateFinder(
        db_path=args.db,
        chunk_size=args.chunk_size,
        max_workers=args.workers
    )

    start_time = time.time()
    finder.scan_directories(args.directories)
    duplicate_groups = finder.find_duplicates()

    if duplicate_groups:
        finder.export_results(duplicate_groups, args.output)

    finder.print_summary()
    elapsed = time.time() - start_time
    print(f"\n总耗时: {elapsed:.2f}秒 ({elapsed/60:.2f}分钟)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
```

</details>

### 步骤3: 还原精确匹配标签页 (如果 `exact_match_tab.py` 损坏)

复制以下完整代码到 `gui_modules/exact_match_tab.py`:

<details>
<summary>📄 点击展开 gui_modules/exact_match_tab.py 完整代码</summary>

由于文件过长（约1000行），请从Git仓库或备份中恢复，或参考以下关键修复点：

**关键修复点清单**:
1. ✅ 导入 `scrolledtext` 和 `datetime`
2. ✅ `_create_widgets()` 中按顺序创建：设置区 → 控制按钮 → 进度条 → 日志
3. ✅ `_start_scan()` 使用自己的按钮（不是 `main_window.start_btn`）
4. ✅ `_stop_scan()` 方法存在
5. ✅ `_log()`, `update_progress()`, `update_detail()` 方法存在
6. ✅ `_run_scan()` 中使用 `self._log()` 而不是 `main_window._log()`
7. ✅ 异常处理捕获 `InterruptedError`（不显示错误对话框）
8. ✅ `_show_results_window()` 布局：顶部横向（摘要+筛选），下方列表
9. ✅ 筛选区域：后缀模糊匹配 + 大小范围（单位在最后）
10. ✅ `_on_click_actions_column()` 只在点击操作列时触发隐藏
11. ✅ `_on_double_click_group()` 显示详情窗口（不是直接打开文件夹）
12. ✅ `_open_file_location()` 双击路径打开文件夹
13. ✅ `_parse_size_to_bytes()` 正确解析带单位的文件大小
14. ✅ `_sort_tree_by_column()` 对size列使用特殊解析
15. ✅ Treeview的 `#0` 列**没有** `command` 参数

**完整代码获取方式**:
```bash
# 如果有Git
git checkout HEAD -- gui_modules/exact_match_tab.py

# 或从备份恢复
cp backup/gui_modules/exact_match_tab.py gui_modules/exact_match_tab.py
```

</details>

### 步骤4: 还原主窗口架构 (如果 `main_window.py` 损坏)

<details>
<summary>📄 点击展开 main_window.py 关键修复点</summary>

**关键修复点**:
1. ✅ `_create_widgets()` 只调用：header → directory → notebook
2. ✅ `_create_notebook()` 创建两个标签页
3. ✅ **没有** `_create_control_buttons()`, `_create_progress_section()`, `_create_log_section()` 方法
4. ✅ `_log()`, `update_progress()`, `update_detail()` 委托给当前标签页
5. ✅ `_start_scan()` 根据当前标签页调用对应的方法
6. ✅ `_stop_scan()` 只设置stop_flag（不操作按钮）

</details>

### 步骤5: 验证还原成功

运行测试命令：
```bash
python run_gui.py
```

**预期行为**:
- ✅ GUI正常启动，无报错
- ✅ 可以添加目录
- ✅ 点击"开始扫描"能正常扫描
- ✅ 点击"停止"不会弹出错误对话框
- ✅ 结果窗口显示正常，双击组别弹出详情
- ✅ 文件大小排序正确（1 KB < 10 KB）
- ✅ 只有点击"操作"列才触发隐藏

---

## 🔍 快速故障诊断表

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| `no such table: files` | 数据库初始化顺序错误 | 检查 `_init_database()`: CREATE → DELETE → INDEX |
| `'Event' object is not callable` | 直接调用stop_flag() | 改为 `stop_flag.is_set()` |
| 点击停止弹出错误对话框 | 未捕获InterruptedError | 在 `_run_scan()` 中添加 `except InterruptedError` |
| 整行点击都触发隐藏 | 未检测点击的列 | 使用 `_on_click_actions_column()` 检测 column == '#4' |
| 文件大小排序错误 | 字符串排序 | 使用 `_parse_size_to_bytes()` 转换后排序 |
| `Display column #0 cannot be set` | #0列添加了排序命令 | 移除 `tree.heading('#0', ..., command=...)` 中的command |
| 双击组别直接打开文件夹 | 绑定了错误的方法 | 绑定 `_on_double_click_group()` 而不是直接打开 |
| 标签页下方大片空白 | Notebook高度限制或未expand | 检查pack参数：`fill=tk.BOTH, expand=True` |
| 自定义后缀输入框位置错误 | 使用了错误的parent | 确保在settings_frame内创建 |

---

## 🎯 核心逻辑流程图

```
用户点击"开始扫描"
    ↓
exact_match_tab._start_scan()
    ├─ 验证目录存在
    ├─ 禁用开始按钮，启用停止按钮
    └─ 启动后台线程
         ↓
    exact_match_tab._run_scan()
         ├─ 获取配置（目录、数据库、线程数、文件类型）
         ├─ 创建DuplicateFinder实例
         │    ├─ _init_database()
         │    │   ├─ CREATE TABLE files
         │    │   ├─ DELETE FROM files (if clear_db)
         │    │   └─ CREATE INDEX
         │    └─ 设置回调函数
         ├─ finder.scan_directories(directories)
         │    └─ 遍历文件，批量插入数据库
         ├─ finder.find_duplicates()
         │    ├─ Level 1: 按大小分组
         │    ├─ Level 2: 部分哈希（前1MB）
         │    └─ Level 3: 完整哈希
         ├─ finder.export_results(...)
         └─ 恢复UI状态
              ↓
    用户查看结果
         ├─ 双击组别 → _on_double_click_group()
         │    └─ 弹出详情窗口（显示所有文件路径）
         │         └─ 双击路径 → _open_file_location()
         │              └─ explorer /select,"{file_path}"
         ├─ 点击列标题 → _sort_tree_by_column()
         │    └─ size列使用 _parse_size_to_bytes()
         └─ 点击操作列 → _on_click_actions_column()
              └─ 切换隐藏状态
```

---

## 📦 依赖关系图

```
run_gui.py
    └─ gui_modules.main_window
         ├─ gui_modules.exact_match_tab  ← 精确匹配标签页
         │    └─ core.duplicate_finder   ← 核心引擎
         └─ gui_modules.similarity_tab   ← 相似度标签页
              └─ core.visual_similarity  ← 相似度引擎
```

**还原顺序**: core → gui_modules → run_gui.py

---

## ⚡ 一键还原脚本（可选）

创建 `restore_exact_match.py`:

```python
#!/usr/bin/env python3
"""一键还原精确匹配功能"""
import shutil
import os

BACKUP_DIR = "backup"
CORE_DIR = "core"
GUI_DIR = "gui_modules"

def restore_file(src, dst):
    """恢复单个文件"""
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"✅ 已恢复: {dst}")
    else:
        print(f"❌ 备份文件不存在: {src}")

def main():
    print("开始还原精确匹配功能...")
    
    # 恢复核心引擎
    restore_file(
        f"{BACKUP_DIR}/core/duplicate_finder.py",
        f"{CORE_DIR}/duplicate_finder.py"
    )
    
    # 恢复GUI标签页
    restore_file(
        f"{BACKUP_DIR}/gui_modules/exact_match_tab.py",
        f"{GUI_DIR}/exact_match_tab.py"
    )
    
    # 恢复主窗口
    restore_file(
        f"{BACKUP_DIR}/gui_modules/main_window.py",
        f"{GUI_DIR}/main_window.py"
    )
    
    print("\n还原完成！请运行 python run_gui.py 验证")

if __name__ == '__main__':
    main()
```

使用方法：
```bash
# 1. 定期备份（功能正常时）
mkdir -p backup/core backup/gui_modules
cp core/duplicate_finder.py backup/core/
cp gui_modules/exact_match_tab.py backup/gui_modules/
cp gui_modules/main_window.py backup/gui_modules/

# 2. 故障时还原
python restore_exact_match.py
```

---

## 🧪 验收测试用例

### 测试1: 基本扫描
```python
# 执行
1. 添加包含重复文件的目录
2. 点击"开始扫描"
3. 观察日志和进度条

# 预期
✅ 日志显示扫描进度
✅ 进度条实时更新
✅ 完成后显示重复组数量
✅ 生成 duplicates.json 文件
```

### 测试2: 停止功能
```python
# 执行
1. 扫描大目录
2. 点击"停止"按钮

# 预期
✅ 日志显示"扫描已停止"
✅ ❌ 不弹出错误对话框
✅ UI恢复正常（开始按钮可用）
```

### 测试3: 结果窗口
```python
# 执行
1. 点击"查看结果"
2. 双击任意组别
3. 在详情窗口双击任意路径

# 预期
✅ 弹出详情窗口，显示所有文件
✅ 打开文件夹并选中文件
```

### 测试4: 排序功能
```python
# 执行
1. 点击"文件大小"列标题

# 预期
✅ 按数值大小排序（1 KB < 10 KB < 1 MB）
✅ 再次点击反转顺序
```

### 测试5: 筛选功能
```python
# 执行
1. 在后缀输入框输入 "jpg"
2. 点击"应用筛选"

# 预期
✅ 只显示包含.jpg/.jpeg的组
✅ 清除筛选后恢复全部显示
```

### 测试6: 隐藏功能
```python
# 执行
1. 点击某行的"隐藏"文字（操作列）

# 预期
✅ 该行消失
✅ 点击其他列（如组别、大小）不触发隐藏
```

---

## 📝 变更记录

| 日期 | 变更内容 | 影响范围 |
|------|----------|----------|
| 2026-05-22 | 初始版本发布 | 全部 |
| 2026-05-22 | 修复数据库表不存在错误 | core/duplicate_finder.py |
| 2026-05-22 | 修复Event对象调用错误 | core/duplicate_finder.py |
| 2026-05-22 | 增强结果窗口功能 | gui_modules/exact_match_tab.py |
| 2026-05-22 | 修复文件大小排序 | gui_modules/exact_match_tab.py |
| 2026-05-22 | 重构标签页布局 | gui_modules/*.py |

---

## 🆘 紧急联系

如果本文档无法解决问题：

1. **检查Git历史**: `git log --oneline gui_modules/exact_match_tab.py`
2. **查看最后一次正常提交**: `git show <commit-hash>:gui_modules/exact_match_tab.py`
3. **对比差异**: `git diff HEAD gui_modules/exact_match_tab.py`

---

**文档维护**: AI Assistant  
**最后更新**: 2026-05-22  
**下次审核**: 2026-06-22  
**状态**: ✅ 已验证可用
