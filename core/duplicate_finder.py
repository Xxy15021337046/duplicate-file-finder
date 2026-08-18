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
import platform
import subprocess
import glob
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import threading
from contextlib import contextmanager


class DuplicateFinder:
    """高性能重复文件检测器"""

    def __init__(
        self,
        db_path: str = "file_index.db",
        chunk_size: int = 65536,
        max_workers: int = None,
        progress_callback=None,
        stop_flag=None,
        log_callback=None,
        clear_db: bool = True,
        allowed_extensions: set = None,
    ):
        self.db_path = db_path
        self.chunk_size = chunk_size  # 读取文件的块大小（默认64KB，提升I/O效率）

        # Developed collaboratively with TRAE
        # Last AI modification: 2026-07-02 10:07 UTC+08:00
        # 修复点: 添加进度锁解决多线程竞态条件，添加磁盘类型自适应线程数
        self._progress_lock = threading.Lock()  # 保护多线程进度计数器

        # 自动检测CPU核心数，设置最优线程数
        if max_workers is None:
            import multiprocessing

            cpu_count = multiprocessing.cpu_count()
            # 根据磁盘类型自适应：SSD可多线程，HDD需减少线程避免寻道风暴
            self.max_workers = self._detect_optimal_workers(cpu_count)
        else:
            self.max_workers = max_workers

        self.lock = threading.Lock()
        self.progress_callback = progress_callback  # 进度回调函数
        self.stop_flag = stop_flag  # 停止标志
        self.log_callback = log_callback  # 日志回调函数
        self.clear_db = clear_db  # 是否清空数据库
        self.allowed_extensions = (
            allowed_extensions  # 允许的文件后缀集合（None表示不过滤）
        )
        self.stats = {
            "total_files": 0,
            "total_size": 0,
            "scanned_files": 0,
            "duplicate_groups": 0,
            "duplicate_files": 0,
            "wasted_space": 0,
        }
        self._init_database()

    def _detect_optimal_workers(self, cpu_count: int) -> int:
        """
        根据磁盘类型检测最优线程数

        Note: Developed collaboratively with TRAE
        Last AI modification: 2026-07-02 10:43 UTC+08:00
        修复点: 替换无效的fsutil方案为Get-PhysicalDisk，正确解析磁盘类型
        优化点: 将platform/subprocess/glob导入移至文件顶部，符合PEP8最佳实践

        HDD上多线程会导致磁头寻道风暴，SSD上可充分利用多线程
        """
        is_hdd = False

        try:
            if platform.system() == "Windows":
                # Developed collaboratively with TRAE
                # Last AI modification: 2026-07-02 10:20 UTC+08:00
                # 修复: fsutil需要管理员权限且不返回SSD/HDD信息
                #       改用 Get-PhysicalDisk cmdlet（Windows 8+/Server 2012+）
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "Get-PhysicalDisk | Select-Object -ExpandProperty MediaType",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # 解析输出，只要存在HDD磁盘就按HDD策略处理（保守策略）
                media_types = [
                    line.strip() for line in result.stdout.splitlines() if line.strip()
                ]
                is_hdd = any(mt.lower() == "hdd" for mt in media_types)
            else:
                # Developed collaboratively with TRAE
                # Last AI modification: 2026-07-02 10:31 UTC+08:00
                # 修复: 扩展glob模式覆盖所有块设备(sda/nvme0n1/mmcblk0/vda/hda等)
                #       原 sd* 模式会遗漏 virtio(vd*)、IDE(hd*) 等 HDD 设备
                for path in glob.glob("/sys/block/*/queue/rotational"):
                    try:
                        with open(path) as f:
                            if f.read().strip() == "1":
                                is_hdd = True
                                break
                    except (IOError, OSError):
                        continue
        except Exception:
            # 检测失败时默认按SSD处理（现代电脑SSD更普遍）
            is_hdd = False

        if is_hdd:
            # HDD: 限制2-4线程，避免寻道风暴
            return min(cpu_count, 4)
        else:
            # SSD/NVMe: 可使用更多线程
            return min(cpu_count * 2, 16)

    def _init_database(self):
        """初始化SQLite数据库，优化大规模数据性能"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 先设置PRAGMA参数（必须在事务外）
        cursor.execute("PRAGMA journal_mode=WAL")  # WAL模式提高并发性能
        cursor.execute("PRAGMA synchronous=NORMAL")  # 降低同步频率
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB缓存
        cursor.execute("PRAGMA temp_store=MEMORY")  # 临时表存储在内存
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB内存映射

        # 创建文件信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_size INTEGER NOT NULL,
                modified_time REAL NOT NULL,
                partial_hash TEXT,      -- 前1MB的MD5哈希（快速筛选）
                full_hash TEXT,         -- 完整文件的MD5哈希（精确匹配）
                scan_status TEXT DEFAULT 'pending',  -- pending, scanned, error
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 如果需要清空数据库，删除旧数据（在表创建之后执行）
        if self.clear_db:
            cursor.execute("DELETE FROM files")
            self._log("已清空数据库中的旧数据")

        # 创建索引加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_size ON files(file_size)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_partial_hash ON files(partial_hash)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_full_hash ON files(full_hash)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_scan_status ON files(scan_status)"
        )

        conn.commit()
        conn.close()

    @contextmanager
    def _get_db_connection(self):
        """获取数据库连接的上下文管理器"""
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
        """
        创建数据库连接

        Note: Developed collaboratively with TRAE
        Last AI modification: 2026-07-02 10:07 UTC+08:00
        修复点: 增加超时时间和busy_timeout，避免大规模写入时 "database is locked"
        """
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")  # 忙等待60秒，避免锁冲突
        return conn

    def _check_stop(self):
        """检查是否应该停止"""
        if self.stop_flag and self.stop_flag.is_set():
            raise InterruptedError("用户请求停止扫描")

    def scan_directories(self, directories: List[str]):
        """扫描多个目录，收集文件信息"""
        print(f"开始扫描 {len(directories)} 个目录...")

        # 通知UI开始扫描
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

            # 更新当前扫描的目录
            if self.progress_callback:
                self.progress_callback(
                    0, f"扫描目录 {i}/{len(directories)}: {os.path.basename(directory)}"
                )

            self._scan_single_directory(directory)

        elapsed = time.time() - start_time
        print(f"\n目录扫描完成! 耗时: {elapsed:.2f}秒")
        print(f"发现文件总数: {self.stats['total_files']:,}")
        print(f"文件总大小: {self._format_size(self.stats['total_size'])}")

    def _should_include_file(self, file_path: str) -> bool:
        """检查文件是否应该被包含（根据后缀过滤）"""
        if self.allowed_extensions is None:
            return True  # 不过滤，包含所有文件

        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.allowed_extensions

    def _scan_single_directory(self, directory: str):
        """扫描单个目录，使用os.walk高效遍历"""
        # 优化批量大小：减少数据库事务次数，但控制内存占用
        batch_size = 5000  # 从1000提升到5000，减少数据库写入次数
        file_batch = []
        files_scanned = 0
        files_filtered = 0  # 被过滤掉的文件数

        for root, dirs, files in os.walk(directory):
            self._check_stop()
            # 跳过隐藏目录和系统目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                file_path = os.path.join(root, filename)

                try:
                    # 跳过符号链接
                    if os.path.islink(file_path):
                        continue

                    # 应用文件类型过滤
                    if not self._should_include_file(file_path):
                        files_filtered += 1
                        continue

                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    modified_time = stat.st_mtime

                    file_batch.append(
                        {
                            "file_path": file_path,
                            "file_size": file_size,
                            "modified_time": modified_time,
                        }
                    )

                    self.stats["total_files"] += 1
                    self.stats["total_size"] += file_size
                    files_scanned += 1

                    # 批量插入数据库并更新进度
                    if len(file_batch) >= batch_size:
                        self._batch_insert_files(file_batch)
                        file_batch = []

                        # 每处理1000个文件更新一次进度（减少UI更新频率，提升性能）
                        if self.progress_callback and files_scanned % 1000 == 0:
                            detail = f"已扫描 {files_scanned:,} 个文件"
                            self.progress_callback(0, detail)

                except (OSError, PermissionError) as e:
                    print(f"警告: 无法访问文件 {file_path}: {e}")

        # 插入剩余的文件
        if file_batch:
            self._batch_insert_files(file_batch)

        # 最终更新一次进度显示总文件数
        if self.progress_callback and files_scanned > 0:
            detail = f"目录扫描完成，共 {files_scanned:,} 个文件"
            self.progress_callback(0, detail)

    def _batch_insert_files(self, file_batch: List[Dict]):
        """批量插入文件记录到数据库"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR IGNORE INTO files (file_path, file_size, modified_time)
                VALUES (:file_path, :file_size, :modified_time)
            """,
                file_batch,
            )

    def find_duplicates(self) -> List[List[Dict]]:
        """查找重复文件，使用多级哈希策略"""
        self._log("\n" + "=" * 60)
        self._log("开始查找重复文件...")
        self._log("=" * 60)

        # 第1步：基于文件大小分组，找出可能重复的大小
        self._log("\n步骤1: 基于文件大小进行初步筛选...")
        if self.progress_callback:
            self.progress_callback(0, "步骤1: 基于文件大小筛选...")

        potential_duplicates = self._find_by_size()

        # 统计总文件数
        total_files_in_groups = sum(
            len(files) for files in potential_duplicates.values()
        )
        self._log(f"发现 {len(potential_duplicates)} 个可能存在重复的文件大小组")
        self._log(f"  这些组中共有 {total_files_in_groups:,} 个文件需要进一步检查")
        if self.progress_callback:
            self.progress_callback(
                0,
                f"发现 {len(potential_duplicates)} 个候选组 ({total_files_in_groups:,} 个文件)",
            )

        if not potential_duplicates:
            self._log("\n未发现任何重复文件!")
            return []

        # 第2步：计算部分哈希（前1MB）
        self._log("\n步骤2: 计算部分哈希值（前1MB）...")
        if self.progress_callback:
            self.progress_callback(0, "步骤2: 计算部分哈希...")

        partial_hash_groups = self._compute_partial_hashes(potential_duplicates)
        self._log(f"部分哈希筛选后剩余 {len(partial_hash_groups)} 个组")
        if self.progress_callback:
            self.progress_callback(
                0, f"部分哈希完成，剩余 {len(partial_hash_groups)} 个组"
            )

        if not partial_hash_groups:
            self._log("\n未发现任何重复文件!")
            return []

        # 第3步：计算完整文件哈希
        self._log("\n步骤3: 计算完整文件哈希值...")
        if self.progress_callback:
            self.progress_callback(0, "步骤3: 计算完整哈希...")

        duplicate_groups = self._compute_full_hashes(partial_hash_groups)
        self._log(f"最终确认 {len(duplicate_groups)} 个重复文件组")
        if self.progress_callback:
            self.progress_callback(0, f"完成！发现 {len(duplicate_groups)} 个重复组")

        self.stats["duplicate_groups"] = len(duplicate_groups)

        # 统计重复文件数量和浪费空间
        for group in duplicate_groups:
            self.stats["duplicate_files"] += len(group) - 1  # 保留一个原件
            wasted = sum(f["file_size"] for f in group[1:])
            self.stats["wasted_space"] += wasted

        return duplicate_groups

    def _log(self, message: str):
        """内部日志方法，同时输出到终端和回调"""
        # 使用UTF-8编码输出，避免Windows GBK编码问题
        try:
            print(message)
        except UnicodeEncodeError:
            # 如果失败，使用errors='replace'替换无法编码的字符
            print(message.encode("gbk", errors="replace").decode("gbk"))

        # 如果有日志回调，也发送消息
        if self.log_callback:
            self.log_callback(message)

    def _find_by_size(self) -> Dict[int, List[Dict]]:
        """基于文件大小找出可能重复的文件"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            # 找出有多个文件的大小
            cursor.execute("""
                SELECT file_size, COUNT(*) as count
                FROM files
                GROUP BY file_size
                HAVING count > 1
            """)

            size_groups = {}
            for row in cursor.fetchall():
                file_size, count = row
                if count > 1:
                    cursor.execute(
                        """
                        SELECT file_path, file_size, modified_time
                        FROM files
                        WHERE file_size = ?
                    """,
                        (file_size,),
                    )

                    files = [
                        {"file_path": r[0], "file_size": r[1], "modified_time": r[2]}
                        for r in cursor.fetchall()
                    ]
                    size_groups[file_size] = files

        return size_groups

    def _compute_partial_hashes(
        self, size_groups: Dict[int, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """
        计算文件的部分哈希（前1MB），用于快速筛选

        Note: Developed collaboratively with TRAE
        Last AI modification: 2026-07-02 10:07 UTC+08:00
        修复点: 使用线程锁保护进度计数器，解决多线程竞态条件
        """
        hash_groups = defaultdict(list)
        total_files = sum(len(files) for files in size_groups.values())
        processed = 0

        def compute_partial_hash(file_info: Dict) -> Optional[Tuple[str, Dict]]:
            """计算单个文件的部分哈希"""
            try:
                self._check_stop()
                file_path = file_info["file_path"]
                hasher = hashlib.md5()

                with open(file_path, "rb") as f:
                    data = f.read(1024 * 1024)  # 读取前1MB
                    hasher.update(data)

                partial_hash = hasher.hexdigest()
                key = f"{file_info['file_size']}_{partial_hash}"

                # 使用锁保护进度更新，避免竞态条件导致计数丢失
                nonlocal processed
                with self._progress_lock:
                    processed += 1
                    current = processed
                # 减少进度更新频率，每500个文件更新一次（提升性能）
                if self.progress_callback and current % 500 == 0:
                    progress = (current / total_files) * 100
                    self.progress_callback(
                        progress, f"部分哈希: {current}/{total_files}"
                    )

                return (key, file_info)
            except InterruptedError:
                raise
            except Exception as e:
                print(f"错误: 无法读取文件 {file_path}: {e}")
                return None

        # 并行计算部分哈希
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

        # 打印部分哈希筛选结果
        self._log(f"\n  部分哈希筛选完成，发现 {len(hash_groups)} 个潜在重复组")

        # 只保留有重复的组
        return {k: v for k, v in hash_groups.items() if len(v) > 1}

    def _compute_full_hashes(
        self, hash_groups: Dict[str, List[Dict]]
    ) -> List[List[Dict]]:
        """
        计算完整文件的哈希值，确认重复

        Note: Developed collaboratively with TRAE
        Last AI modification: 2026-07-02 10:07 UTC+08:00
        修复点:
        1. 使用全局线程池替代每组创建/销毁，避免数万次线程池开销
        2. 使用线程锁保护进度计数器，解决竞态条件
        3. 进度计算改为全局连续，不再每组重置
        """
        duplicate_groups = []
        total_files = sum(len(files) for files in hash_groups.values())
        processed = 0

        def compute_full_hash(
            file_info: Dict, group_key: str
        ) -> Optional[Tuple[str, str, Dict]]:
            """计算完整文件的MD5哈希，返回(组键, 哈希, 文件信息)"""
            try:
                self._check_stop()
                file_path = file_info["file_path"]
                hasher = hashlib.md5()

                with open(file_path, "rb") as f:
                    while True:
                        data = f.read(self.chunk_size)
                        if not data:
                            break
                        hasher.update(data)

                full_hash = hasher.hexdigest()

                # 使用锁保护进度更新，避免竞态条件
                nonlocal processed
                with self._progress_lock:
                    processed += 1
                    current = processed
                if self.progress_callback and current % 100 == 0:
                    progress = (current / total_files) * 100
                    self.progress_callback(
                        progress, f"完整哈希: {current}/{total_files}"
                    )

                return (group_key, full_hash, file_info)
            except InterruptedError:
                raise
            except Exception as e:
                print(f"错误: 无法读取文件 {file_path}: {e}")
                return None

        # 收集所有需要计算完整哈希的文件及其组键
        all_tasks = []
        for group_key, files in hash_groups.items():
            if len(files) < 2:
                continue
            for f in files:
                all_tasks.append((f, group_key))

        # 按组收集哈希结果
        results_by_group = defaultdict(lambda: defaultdict(list))

        # 使用单个全局线程池处理所有组，避免反复创建/销毁线程池
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(compute_full_hash, f, gk): (f, gk)
                for f, gk in all_tasks
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        group_key, full_hash, file_info = result
                        results_by_group[group_key][full_hash].append(file_info)
                except InterruptedError:
                    raise

        # 从结果中提取确认的重复组
        for group_key, full_hash_groups in results_by_group.items():
            for full_hash, dup_files in full_hash_groups.items():
                if len(dup_files) > 1:
                    duplicate_groups.append(dup_files)
                    self._log(
                        f"  ✓ 发现 {len(dup_files)} 个重复文件 (大小: {self._format_size(dup_files[0]['file_size'])})"
                    )

        return duplicate_groups

    def export_results(
        self, duplicate_groups: List[List[Dict]], output_file: str = "duplicates.json"
    ):
        """
        导出重复文件结果为JSON格式（流式写入，避免内存峰值）

        Note: Developed collaboratively with TRAE
        Last AI modification: 2026-07-02 10:07 UTC+08:00
        修复点: 改为流式写入JSON，避免大量重复组时内存翻倍
        """
        print(f"\n正在导出结果到 {output_file}...")

        with open(output_file, "w", encoding="utf-8") as f:
            # 写入头部和摘要
            f.write("{\n")
            f.write('  "scan_summary": {\n')
            f.write(f'    "total_files_scanned": {self.stats["total_files"]},\n')
            f.write(f'    "total_size_scanned": {self.stats["total_size"]},\n')
            f.write(
                f'    "total_size_formatted": "{self._format_size(self.stats["total_size"])}",\n'
            )
            f.write(f'    "duplicate_groups": {self.stats["duplicate_groups"]},\n')
            f.write(f'    "duplicate_files": {self.stats["duplicate_files"]},\n')
            f.write(f'    "wasted_space": {self.stats["wasted_space"]},\n')
            f.write(
                f'    "wasted_space_formatted": "{self._format_size(self.stats["wasted_space"])}"\n'
            )
            f.write("  },\n")
            f.write('  "duplicate_groups": [\n')

            # 流式写入每个重复组，避免一次性构建整个JSON树
            for i, group in enumerate(duplicate_groups, 1):
                group_json = json.dumps(
                    {
                        "group_id": i,
                        "file_count": len(group),
                        "file_size": group[0]["file_size"],
                        "file_size_formatted": self._format_size(group[0]["file_size"]),
                        "files": [
                            {
                                "path": file_info["file_path"],
                                "size": file_info["file_size"],
                                "modified_time": file_info["modified_time"],
                            }
                            for file_info in group
                        ],
                    },
                    ensure_ascii=False,
                    indent=4,
                )
                # 缩进对齐
                indented = "\n".join(
                    "    " + line if line else line for line in group_json.split("\n")
                )
                f.write("    " + indented.strip())
                if i < len(duplicate_groups):
                    f.write(",")
                f.write("\n")

            f.write("  ]\n}")

        print(f"结果已保存到: {output_file}")

    def print_summary(self):
        """打印扫描摘要"""
        print("\n" + "=" * 60)
        print("扫描结果摘要")
        print("=" * 60)
        print(f"总文件数: {self.stats['total_files']:,}")
        print(f"总大小: {self._format_size(self.stats['total_size'])}")
        print(f"重复文件组: {self.stats['duplicate_groups']:,}")
        print(f"重复文件数: {self.stats['duplicate_files']:,}")
        print(f"浪费空间: {self._format_size(self.stats['wasted_space'])}")
        print("=" * 60)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def main():
    parser = argparse.ArgumentParser(
        description="高性能重复文件检测系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 扫描单个目录
  python duplicate_finder.py /path/to/directory

  # 扫描多个目录
  python duplicate_finder.py /path/to/dir1 /path/to/dir2 /path/to/dir3

  # 自定义数据库路径和输出文件
  python duplicate_finder.py /path/to/dir --db custom.db --output results.json

  # 调整并行线程数
  python duplicate_finder.py /path/to/dir --workers 16
        """,
    )

    parser.add_argument("directories", nargs="+", help="要扫描的目录路径")
    parser.add_argument("--db", default="file_index.db", help="SQLite数据库文件路径")
    parser.add_argument("--output", default="duplicates.json", help="输出JSON文件路径")
    parser.add_argument(
        "--workers", type=int, default=8, help="并行工作线程数 (默认: 8)"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=8192, help="文件读取块大小 (默认: 8192)"
    )

    args = parser.parse_args()

    # 验证目录
    for directory in args.directories:
        if not os.path.exists(directory):
            print(f"错误: 目录不存在 - {directory}")
            sys.exit(1)

    print("=" * 60)
    print("高性能重复文件检测系统")
    print("=" * 60)
    print(f"扫描目录: {', '.join(args.directories)}")
    print(f"数据库: {args.db}")
    print(f"输出文件: {args.output}")
    print(f"工作线程: {args.workers}")
    print("=" * 60)

    # 创建检测器
    finder = DuplicateFinder(
        db_path=args.db, chunk_size=args.chunk_size, max_workers=args.workers
    )

    start_time = time.time()

    # 扫描目录
    finder.scan_directories(args.directories)

    # 查找重复文件
    duplicate_groups = finder.find_duplicates()

    # 导出结果
    if duplicate_groups:
        finder.export_results(duplicate_groups, args.output)

    # 打印摘要
    finder.print_summary()

    elapsed = time.time() - start_time
    print(f"\n总耗时: {elapsed:.2f}秒 ({elapsed / 60:.2f}分钟)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
