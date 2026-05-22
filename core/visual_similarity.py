#!/usr/bin/env python3
"""
图片相似度检测引擎
基于感知哈希(pHash)、差异哈希(dHash)和颜色直方图的三级过滤策略
支持TB级大规模数据的高效相似图片检测
"""

import os
import sys
import struct
import time
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Optional, Iterator
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
import multiprocessing


def _compute_image_fingerprint(image_path: str) -> Optional[Dict]:
    """
    计算单张图片的指纹（全局函数，用于多进程并行计算）
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        包含指纹信息的字典，失败返回None
    """
    try:
        # 确保在多进程环境中也能正确导入模块
        import sys
        import os
        # 添加项目根目录到Python路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from PIL import Image
        import imagehash

        # 加载图片
        img = Image.open(image_path)

        # 处理透明通道和调色板模式
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 获取尺寸
        width, height = img.size

        # 超大图片先缩小（避免内存溢出）
        max_size = 4096
        if width > max_size or height > max_size:
            ratio = min(max_size / width, max_size / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # 计算 pHash（感知哈希）
        phash = imagehash.phash(img, hash_size=8)  # 8x8 = 64位
        phash_str = str(phash)  # 转为16位十六进制字符串

        # 计算 dHash（差异哈希）
        dhash = imagehash.dhash(img, hash_size=8)
        dhash_str = str(dhash)

        # 计算颜色直方图（RGB各256 bins，共768个值）
        histogram = img.histogram()
        histogram_bytes = struct.pack('768I', *histogram)

        return {
            'path': image_path,
            'width': width,
            'height': height,
            'phash': phash_str,
            'dhash': dhash_str,
            'histogram': histogram_bytes
        }

    except Exception as e:
        # 注意：多进程环境中不能直接使用 self._log
        import sys
        import traceback
        error_msg = f"[ERROR] 处理图片失败 {image_path}: {e}\n"
        error_msg += f"Python path: {sys.path}\n"
        error_msg += f"Traceback: {traceback.format_exc()}"
        print(error_msg)
        return None


class ImageSimilarityFinder:
    """图片相似度检测器"""

    # 支持的图片格式
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

    def __init__(self, db_path: str = "image_similarity.db", batch_size: int = 1000,
                 progress_callback=None, log_callback=None):
        """
        初始化相似度检测器

        Args:
            db_path: SQLite数据库路径
            batch_size: 批处理大小（默认1000张/批）
            progress_callback: 进度回调函数 callback(progress: float, message: str)
            log_callback: 日志回调函数 callback(message: str, level: str)
        """
        self.db_path = db_path
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.lock = threading.Lock()

        # 自动检测CPU核心数
        cpu_count = multiprocessing.cpu_count()
        self.max_workers = min(cpu_count, 8)  # 最多8个进程

        self._init_database()

    def _init_database(self):
        """初始化SQLite数据库，创建表和索引"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 设置PRAGMA优化性能
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA cache_size=-64000')  # 64MB缓存
        cursor.execute('PRAGMA temp_store=MEMORY')
        cursor.execute('PRAGMA mmap_size=268435456')  # 256MB内存映射

        # 创建图片索引表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                size INTEGER NOT NULL,
                width INTEGER,
                height INTEGER,
                phash TEXT NOT NULL,
                dhash TEXT NOT NULL,
                histogram BLOB,
                modified_time REAL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建索引加速查询
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_phash ON image_index(phash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dhash ON image_index(dhash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_size ON image_index(size)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_path ON image_index(path)')

        # 创建相似组表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS similarity_groups (
                group_id INTEGER,
                image_id INTEGER,
                similarity_score REAL,
                is_representative BOOLEAN DEFAULT 0,
                FOREIGN KEY (image_id) REFERENCES image_index(id)
            )
        ''')

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
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] {message}")

    def _on_progress(self, progress: float, message: str):
        """触发进度回调"""
        if self.progress_callback:
            self.progress_callback(progress, message)

    def scan_images(self, directories: List[str]) -> Iterator[Dict]:
        """
        扫描目录中的所有图片文件

        Args:
            directories: 要扫描的目录列表

        Yields:
            包含文件信息的字典 {'path': str, 'size': int, 'modified_time': float}
        """
        for directory in directories:
            if not os.path.exists(directory):
                self._log(f"目录不存在: {directory}", "WARNING")
                continue

            for root, dirs, files in os.walk(directory):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for filename in files:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in self.SUPPORTED_FORMATS:
                        file_path = os.path.join(root, filename)

                        # 跳过符号链接
                        if os.path.islink(file_path):
                            continue

                        try:
                            stat = os.stat(file_path)
                            yield {
                                'path': file_path,
                                'size': stat.st_size,
                                'modified_time': stat.st_mtime
                            }
                        except OSError as e:
                            self._log(f"无法访问文件 {file_path}: {e}", "WARNING")
                            continue

    def compute_fingerprint(self, image_path: str) -> Optional[Dict]:
        """
        计算单张图片的指纹（实例方法，委托给全局函数）

        Args:
            image_path: 图片文件路径

        Returns:
            包含指纹信息的字典，失败返回None
        """
        return _compute_image_fingerprint(image_path)

    def build_index(self, directories: List[str], incremental: bool = False):
        """
        构建图片索引

        Args:
            directories: 要扫描的目录列表
            incremental: 是否增量扫描（默认False全量扫描）
        """
        self._log("开始构建图片索引...")

        # 如果需要全量扫描，清空旧数据
        if not incremental:
            with self._get_db_connection() as conn:
                conn.execute("DELETE FROM image_index")
                conn.execute("DELETE FROM similarity_groups")
                self._log("已清空数据库中的旧数据")

        # 扫描所有图片文件
        images = list(self.scan_images(directories))
        total = len(images)

        if total == 0:
            self._log("未找到任何图片文件", "WARNING")
            return

        self._log(f"找到 {total} 张图片，开始计算指纹...")

        # 多进程并行计算指纹（使用全局函数，避免传递包含Tkinter对象的self）
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(_compute_image_fingerprint, img['path']): img
                for img in images
            }

            batch = []
            processed = 0

            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if result:
                    batch.append(result)

                processed += 1

                # 批量插入
                if len(batch) >= self.batch_size:
                    self._batch_insert(batch)
                    batch = []

                # 更新进度
                if processed % 100 == 0 or processed == total:
                    progress = processed / total * 100
                    self._on_progress(progress, f"已处理 {processed}/{total} 张图片 ({progress:.1f}%)")

            # 插入剩余数据
            if batch:
                self._batch_insert(batch)

        self._log(f"索引构建完成，共处理 {total} 张图片")

    def _batch_insert(self, batch: List[Dict]):
        """批量插入数据库"""
        data = [(
            img['path'],
            os.path.getsize(img['path']) if os.path.exists(img['path']) else 0,
            img.get('width', 0),
            img.get('height', 0),
            img['phash'],
            img['dhash'],
            img['histogram'],
            os.path.getmtime(img['path']) if os.path.exists(img['path']) else 0,
            time.time()
        ) for img in batch]

        with self._get_db_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO image_index 
                (path, size, width, height, phash, dhash, histogram, modified_time, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)

    @staticmethod
    def _hamming_distance(hash1: str, hash2: str) -> int:
        """
        计算两个十六进制哈希的汉明距离

        Args:
            hash1: 第一个哈希（16位十六进制字符串）
            hash2: 第二个哈希（16位十六进制字符串）

        Returns:
            汉明距离（0-64）
        """
        h1 = int(hash1, 16)
        h2 = int(hash2, 16)
        xor = h1 ^ h2
        return bin(xor).count('1')

    @staticmethod
    def _histogram_similarity(hist1: bytes, hist2: bytes) -> float:
        """
        计算两个直方图的相似度（余弦相似度）

        Args:
            hist1: 第一个直方图（768字节）
            hist2: 第二个直方图（768字节）

        Returns:
            相似度分数（0-1）
        """
        import math

        # 解包为整数列表
        h1 = struct.unpack('768I', hist1)
        h2 = struct.unpack('768I', hist2)

        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(h1, h2))
        norm1 = math.sqrt(sum(a * a for a in h1))
        norm2 = math.sqrt(sum(b * b for b in h2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _compute_similarity_score(self, phash_dist: int, dhash_dist: int,
                                   hist_sim: float) -> float:
        """
        计算综合相似度分数

        Args:
            phash_dist: pHash汉明距离（0-64）
            dhash_dist: dHash汉明距离（0-64）
            hist_sim: 直方图相似度（0-1）

        Returns:
            综合相似度分数（0-100）
        """
        # pHash分数（距离0-64，越小越好）
        phash_score = max(0, 100 - (phash_dist / 64 * 100))

        # dHash分数
        dhash_score = max(0, 100 - (dhash_dist / 64 * 100))

        # 直方图分数（已经是0-1）
        hist_score = hist_sim * 100

        # 加权平均
        final_score = (
            phash_score * 0.5 +
            dhash_score * 0.3 +
            hist_score * 0.2
        )

        return round(final_score, 2)

    def find_similar_groups(self, threshold_phash: int = 12, mode: str = "precise") -> List[Dict]:
        """
        查找相似图片组

        Args:
            threshold_phash: pHash汉明距离阈值（默认12）
            mode: 检测模式（"fast" 快速模式 或 "precise" 精确模式）

        Returns:
            相似组列表
        """
        self._log(f"开始查找相似图片组（阈值={threshold_phash}, 模式={mode}）...")

        # 获取所有图片
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT id, path, size, width, height, phash, dhash, histogram 
            FROM image_index 
            ORDER BY size DESC
        """)

        images = cursor.fetchall()
        conn.close()

        total = len(images)
        if total == 0:
            self._log("数据库中没有图片数据", "WARNING")
            return []

        used_ids = set()
        similar_groups = []

        # 遍历每张图片
        for i, img1 in enumerate(images):
            if img1[0] in used_ids:
                continue

            group = [img1]
            group_scores = []

            # 与其他图片比较
            for j, img2 in enumerate(images[i+1:], start=i+1):
                if img2[0] in used_ids:
                    continue

                # 第1级：pHash快速筛选
                phash_dist = self._hamming_distance(img1[5], img2[5])
                if phash_dist > threshold_phash:
                    continue

                # 第2级：dHash二次验证（仅精确模式）
                if mode == "precise":
                    dhash_dist = self._hamming_distance(img1[6], img2[6])
                    if dhash_dist > threshold_phash:
                        continue

                    # 第3级：直方图精确比对
                    if img1[7] and img2[7]:  # 确保直方图存在
                        hist_sim = self._histogram_similarity(img1[7], img2[7])
                        if hist_sim < 0.75:  # 相似度低于75%排除（从85%降低到75%，更宽松）
                            continue
                    else:
                        hist_sim = 0.9  # 无直方图数据时假设相似

                    # 计算综合相似度
                    score = self._compute_similarity_score(phash_dist, dhash_dist, hist_sim)
                else:
                    # 快速模式：仅使用pHash
                    score = max(0, 100 - (phash_dist / 64 * 100))

                group.append(img2)
                group_scores.append(score)

            # 如果找到相似图片，添加到结果
            if len(group) > 1:
                # 将整个组的所有图片标记为已使用（包括基准图片img1）
                for img in group:
                    used_ids.add(img[0])

                # 计算组内平均相似度
                avg_score = sum(group_scores) / len(group_scores) if group_scores else 0

                similar_groups.append({
                    'group_id': len(similar_groups) + 1,
                    'file_count': len(group),
                    'avg_similarity': avg_score,
                    'files': [
                        {
                            'id': img[0],
                            'path': img[1],
                            'size': img[2],
                            'width': img[3],
                            'height': img[4]
                        } for img in group
                    ]
                })

                # 更新进度
                if len(similar_groups) % 10 == 0:
                    progress = len([g for g in similar_groups]) / max(1, total - len(used_ids)) * 100
                    self._on_progress(progress, f"已找到 {len(similar_groups)} 个相似组")

        self._log(f"相似检测完成，共找到 {len(similar_groups)} 个相似组")
        return similar_groups

    def delete_image(self, image_id: int) -> bool:
        """
        删除指定的图片记录

        Args:
            image_id: 图片ID

        Returns:
            是否成功删除
        """
        try:
            with self._get_db_connection() as conn:
                conn.execute("DELETE FROM image_index WHERE id = ?", (image_id,))
                conn.execute("DELETE FROM similarity_groups WHERE image_id = ?", (image_id,))
            return True
        except Exception as e:
            self._log(f"删除图片记录失败: {e}", "ERROR")
            return False

    def get_statistics(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 总图片数
        cursor.execute("SELECT COUNT(*) FROM image_index")
        total_images = cursor.fetchone()[0]

        # 总文件大小
        cursor.execute("SELECT SUM(size) FROM image_index")
        total_size = cursor.fetchone()[0] or 0

        # 不同分辨率数量
        cursor.execute("SELECT COUNT(DISTINCT width || 'x' || height) FROM image_index")
        unique_resolutions = cursor.fetchone()[0]

        conn.close()

        return {
            'total_images': total_images,
            'total_size': total_size,
            'total_size_formatted': self._format_size(total_size),
            'unique_resolutions': unique_resolutions
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="图片相似度检测工具")
    parser.add_argument('directories', nargs='+', help='要扫描的目录')
    parser.add_argument('--db', default='image_similarity.db', help='数据库路径')
    parser.add_argument('--threshold', type=int, default=12, help='相似度阈值（汉明距离）')
    parser.add_argument('--mode', choices=['fast', 'precise'], default='precise', help='检测模式')
    parser.add_argument('--incremental', action='store_true', help='增量扫描')
    parser.add_argument('--output', help='输出JSON文件路径')

    args = parser.parse_args()

    # 创建检测器
    finder = ImageSimilarityFinder(db_path=args.db)

    # 构建索引
    finder.build_index(args.directories, incremental=args.incremental)

    # 查找相似组
    groups = finder.find_similar_groups(threshold_phash=args.threshold, mode=args.mode)

    # 输出结果
    if args.output:
        import json
        result = {
            'statistics': finder.get_statistics(),
            'similar_groups': groups
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {args.output}")
    else:
        # 控制台输出
        print(f"\n找到 {len(groups)} 个相似组:\n")
        for group in groups[:10]:  # 只显示前10个
            print(f"组 #{group['group_id']} (相似度: {group['avg_similarity']:.1f}%, {group['file_count']}张图片)")
            for file_info in group['files'][:3]:  # 每组只显示前3个
                print(f"  - {file_info['path']}")
            if len(group['files']) > 3:
                print(f"  ... 还有 {len(group['files']) - 3} 张图片")
            print()


if __name__ == '__main__':
    main()
