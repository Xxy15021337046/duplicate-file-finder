#!/usr/bin/env python3
"""
视频相似度检测引擎
基于关键帧序列匹配的视频相似度检测，支持抗剪辑、抗转码、抗调色检测
"""

import os
import sys
import json
import time
import struct
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Optional, Iterator, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
import multiprocessing


def _compute_video_fingerprint(video_path: str) -> Optional[Dict]:
    """
    计算单个视频的指纹（全局函数，用于多进程并行计算）
    
    Args:
        video_path: 视频文件路径
    
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
        
        # 延迟导入OpenCV（避免未安装时崩溃）
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import imagehash
        except ImportError as e:
            print(f"[ERROR] 缺少依赖库: {e}")
            print("[INFO] 请运行: pip install opencv-python-headless Pillow imagehash numpy")
            return None
        
        # 检查文件是否存在
        if not os.path.exists(video_path):
            print(f"[ERROR] 视频文件不存在: {video_path}")
            return None
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ERROR] 无法打开视频文件: {video_path}")
            return None
        
        try:
            # 获取视频信息
            duration = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0  # 总时长（秒）
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 如果duration为0，尝试从帧数和FPS计算
            if duration == 0 and fps > 0 and total_frames > 0:
                duration = total_frames / fps
            
            # 根据视频时长动态确定采样帧数
            num_frames = calculate_sample_frames(duration)
            
            # 计算均匀分布的采样时间点
            if num_frames == 1:
                sample_times = [duration / 2]  # 短视频只取中间帧
            else:
                sample_times = [
                    i * duration / (num_frames - 1) 
                    for i in range(num_frames)
                ]
            
            # 提取关键帧并计算指纹
            frame_hashes = []
            max_size = 640  # 帧最大尺寸
            
            for t in sample_times:
                # 定位到指定时间点
                frame_idx = int(t * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                # 预处理帧
                # 1. 缩放到统一尺寸
                h, w = frame.shape[:2]
                if w > max_size or h > max_size:
                    ratio = min(max_size / w, max_size / h)
                    new_size = (int(w * ratio), int(h * ratio))
                    frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)
                
                # 2. 转换为RGB（OpenCV默认BGR）
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 3. 转为PIL Image
                pil_img = Image.fromarray(frame_rgb)
                
                # 4. 计算pHash
                phash = imagehash.phash(pil_img, hash_size=8)
                phash_str = str(phash)
                
                # 5. 计算dHash（可选，用于精确模式）
                dhash = imagehash.dhash(pil_img, hash_size=8)
                dhash_str = str(dhash)
                
                frame_hashes.append({
                    'timestamp': round(t, 2),
                    'phash': phash_str,
                    'dhash': dhash_str
                })
            
            # 至少需要1帧才能生成指纹
            if not frame_hashes:
                print(f"[WARNING] 未能提取任何关键帧: {video_path}")
                return None
            
            return {
                'path': video_path,
                'size': os.path.getsize(video_path),
                'duration': round(duration, 2),
                'width': width,
                'height': height,
                'fps': round(fps, 2),
                'num_frames': total_frames,
                'frame_hashes': frame_hashes
            }
        
        finally:
            cap.release()
    
    except Exception as e:
        import traceback
        error_msg = f"[ERROR] 处理视频失败 {video_path}: {e}\n"
        error_msg += f"Traceback: {traceback.format_exc()}"
        print(error_msg)
        return None


def calculate_sample_frames(duration_seconds: float) -> int:
    """
    根据视频时长动态确定采样帧数
    
    Args:
        duration_seconds: 视频时长（秒）
    
    Returns:
        采样帧数
    """
    if duration_seconds < 10:
        return 5          # 短视频：5帧
    elif duration_seconds < 60:
        return 10         # 中短视频：10帧
    elif duration_seconds < 300:
        return 20         # 中长视频：20帧
    else:
        return min(50, int(duration_seconds / 60))  # 长视频：最多50帧


class VideoSimilarityFinder:
    """视频相似度检测器"""
    
    # 支持的视频格式
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
                        '.mpeg', '.mpg', '.3gp', '.m4v', '.rmvb', '.rm', '.ts',
                        '.mts', '.f4v', '.f4p', '.asf', '.vob'}
    
    def __init__(self, db_path: str = "video_similarity.db", batch_size: int = 100,
                 progress_callback=None, log_callback=None):
        """
        初始化视频相似度检测器
        
        Args:
            db_path: SQLite数据库路径
            batch_size: 批处理大小（默认100个视频/批）
            progress_callback: 进度回调函数 callback(progress: float, message: str)
            log_callback: 日志回调函数 callback(message: str, level: str)
        """
        self.db_path = db_path
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.lock = threading.Lock()
        
        # 自动检测CPU核心数（视频解码是I/O密集型，限制进程数）
        cpu_count = multiprocessing.cpu_count()
        self.max_workers = min(cpu_count, 4)  # 最多4个进程
        
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
        
        # 创建视频索引表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                size INTEGER NOT NULL,
                duration REAL,
                width INTEGER,
                height INTEGER,
                fps REAL,
                num_frames INTEGER,
                frame_hashes TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引加速查询
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_duration ON video_index(duration)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_size ON video_index(size)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_path ON video_index(path)')
        
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
    
    def scan_videos(self, directories: List[str]) -> Iterator[Dict]:
        """
        扫描目录中的所有视频文件
        
        Args:
            directories: 要扫描的目录列表
        
        Yields:
            包含文件信息的字典 {'path': str, 'size': int}
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
                                'size': stat.st_size
                            }
                        except OSError as e:
                            self._log(f"无法访问文件 {file_path}: {e}", "WARNING")
                            continue
    
    def build_index(self, directories: List[str], incremental: bool = False):
        """
        构建视频索引
        
        Args:
            directories: 要扫描的目录列表
            incremental: 是否增量扫描（默认False全量扫描）
        """
        self._log("开始构建视频索引...")
        
        # 如果需要全量扫描，清空旧数据
        if not incremental:
            with self._get_db_connection() as conn:
                conn.execute("DELETE FROM video_index")
                self._log("已清空数据库中的旧数据")
        
        # 扫描所有视频文件
        videos = list(self.scan_videos(directories))
        total = len(videos)
        
        if total == 0:
            self._log("未找到任何视频文件", "WARNING")
            return
        
        self._log(f"找到 {total} 个视频，开始提取关键帧...")
        
        # 多进程并行提取关键帧
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(_compute_video_fingerprint, video['path']): video
                for video in videos
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
                if processed % 10 == 0 or processed == total:
                    progress = processed / total * 100
                    self._on_progress(progress, f"已处理 {processed}/{total} 个视频 ({progress:.1f}%)")
            
            # 插入剩余数据
            if batch:
                self._batch_insert(batch)
        
        self._log(f"索引构建完成，共处理 {total} 个视频")
    
    def _batch_insert(self, batch: List[Dict]):
        """批量插入数据库"""
        data = [(
            video['path'],
            video['size'],
            video.get('duration', 0),
            video.get('width', 0),
            video.get('height', 0),
            video.get('fps', 0),
            video.get('num_frames', 0),
            json.dumps(video['frame_hashes'])
        ) for video in batch]
        
        with self._get_db_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO video_index 
                (path, size, duration, width, height, fps, num_frames, frame_hashes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    def _find_diagonal_sequences(matrix: List[List[int]], min_length: int = 2) -> List[Tuple[int, int, int, int]]:
        """
        在匹配矩阵中寻找长度≥min_length的对角线序列
        
        Args:
            matrix: 匹配矩阵（二维列表）
            min_length: 最小序列长度
        
        Returns:
            序列列表 [(row_start, row_end, col_start, col_end), ...]
        """
        sequences = []
        rows = len(matrix)
        cols = len(matrix[0]) if rows > 0 else 0
        
        for i in range(rows):
            for j in range(cols):
                if matrix[i][j] == 1:
                    # 向右下延伸
                    length = 1
                    while (i + length < rows and 
                           j + length < cols and 
                           matrix[i + length][j + length] == 1):
                        length += 1
                    
                    if length >= min_length:
                        sequences.append((i, i + length - 1, j, j + length - 1))
        
        # 合并重叠的序列
        sequences = VideoSimilarityFinder._merge_overlapping_sequences(sequences)
        return sequences
    
    @staticmethod
    def _merge_overlapping_sequences(sequences: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """
        合并重叠的序列
        
        Args:
            sequences: 序列列表
        
        Returns:
            合并后的序列列表
        """
        if not sequences:
            return []
        
        # 按起始位置排序
        sorted_seqs = sorted(sequences, key=lambda x: (x[0], x[2]))
        merged = [sorted_seqs[0]]
        
        for current in sorted_seqs[1:]:
            last = merged[-1]
            # 检查是否重叠（行或列有交集）
            if (current[0] <= last[1] + 1 and current[2] <= last[3] + 1):
                # 合并：扩展结束位置
                merged[-1] = (
                    last[0],
                    max(last[1], current[1]),
                    last[2],
                    max(last[3], current[3])
                )
            else:
                merged.append(current)
        
        return merged
    
    @staticmethod
    def _calculate_time_coverage(segments: List[Tuple[int, int, int, int]], 
                                 duration1: float, duration2: float) -> float:
        """
        计算匹配片段的时间覆盖率
        
        Args:
            segments: 匹配片段列表
            duration1: 视频1总时长
            duration2: 视频2总时长
        
        Returns:
            时间覆盖率（0-100）
        """
        if not segments or duration1 == 0 or duration2 == 0:
            return 0.0
        
        # 简化版：基于匹配帧数占比
        total_matched_frames = sum(seg[1] - seg[0] + 1 for seg in segments)
        
        # 假设帧均匀分布，计算时间覆盖比例
        coverage = min(total_matched_frames / max(len(segments), 1), 1.0) * 100
        
        return coverage
    
    def _compute_video_similarity(self, frames1: List[Dict], frames2: List[Dict], 
                                   threshold_phash: int = 12) -> Tuple[float, List[Tuple]]:
        """
        计算两个视频的相似度
        
        Args:
            frames1: 视频1的关键帧列表 [{'timestamp': t, 'phash': h}, ...]
            frames2: 视频2的关键帧列表
            threshold_phash: pHash汉明距离阈值
        
        Returns:
            (similarity_score, matched_segments)
        """
        if not frames1 or not frames2:
            return 0.0, []
        
        # 步骤1：构建匹配矩阵
        rows = len(frames1)
        cols = len(frames2)
        match_matrix = [[0] * cols for _ in range(rows)]
        
        for i, frame1 in enumerate(frames1):
            for j, frame2 in enumerate(frames2):
                dist = self._hamming_distance(frame1['phash'], frame2['phash'])
                if dist <= threshold_phash:
                    match_matrix[i][j] = 1
        
        # 步骤2：寻找对角线序列（连续匹配片段）
        matched_segments = self._find_diagonal_sequences(match_matrix, min_length=2)
        
        if not matched_segments:
            return 0.0, []
        
        # 步骤3：计算相似度分数
        # 方法1：基于匹配帧数的Jaccard相似度
        matched_frame_count = sum(seg[1] - seg[0] + 1 for seg in matched_segments)
        total_frames = rows + cols - matched_frame_count
        jaccard_sim = (matched_frame_count / total_frames * 100) if total_frames > 0 else 0
        
        # 方法2：基于时间覆盖率的相似度
        duration1 = frames1[-1]['timestamp'] if frames1 else 0
        duration2 = frames2[-1]['timestamp'] if frames2 else 0
        time_coverage = self._calculate_time_coverage(matched_segments, duration1, duration2)
        
        # 综合评分（加权平均）
        final_score = jaccard_sim * 0.6 + time_coverage * 0.4
        
        return round(final_score, 2), matched_segments
    
    def find_similar_groups(self, threshold_phash: int = 12, mode: str = "precise") -> List[Dict]:
        """
        查找相似视频组
        
        Args:
            threshold_phash: pHash汉明距离阈值（默认12）
            mode: 检测模式（当前仅支持"precise"）
        
        Returns:
            相似组列表
        """
        self._log(f"开始查找相似视频组（阈值={threshold_phash}）...")
        
        # 获取所有视频
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT id, path, size, duration, width, height, fps, num_frames, frame_hashes 
            FROM video_index 
            ORDER BY size DESC
        """)
        
        videos = cursor.fetchall()
        conn.close()
        
        total = len(videos)
        if total == 0:
            self._log("数据库中没有视频数据", "WARNING")
            return []
        
        used_ids = set()
        similar_groups = []
        
        # 遍历每个视频
        for i, vid1 in enumerate(videos):
            if vid1[0] in used_ids:
                continue
            
            group = [vid1]
            group_scores = []
            
            # 与其他视频比较
            for j, vid2 in enumerate(videos[i+1:], start=i+1):
                if vid2[0] in used_ids:
                    continue
                
                # 第1级：快速筛选（元数据比对）
                # 时长差异 > 50%？
                if vid1[3] > 0 and vid2[3] > 0:
                    duration_diff = abs(vid1[3] - vid2[3]) / max(vid1[3], vid2[3])
                    if duration_diff > 0.5:
                        continue
                
                # 文件大小差异 > 10倍？
                if vid1[2] > 0 and vid2[2] > 0:
                    size_ratio = max(vid1[2], vid2[2]) / min(vid1[2], vid2[2])
                    if size_ratio > 10:
                        continue
                
                # 第2级：关键帧序列匹配
                try:
                    frames1 = json.loads(vid1[8])
                    frames2 = json.loads(vid2[8])
                    
                    score, segments = self._compute_video_similarity(frames1, frames2, threshold_phash)
                    
                    if score >= 50:  # 相似度≥50%判定为相似
                        group.append(vid2)
                        group_scores.append(score)
                except Exception as e:
                    self._log(f"比对视频失败: {e}", "DEBUG")
                    continue
            
            # 如果找到相似视频，添加到结果
            if len(group) > 1:
                # 将整个组的所有视频标记为已使用
                for vid in group:
                    used_ids.add(vid[0])
                
                # 计算组内平均相似度
                avg_score = sum(group_scores) / len(group_scores) if group_scores else 0
                
                similar_groups.append({
                    'group_id': len(similar_groups) + 1,
                    'file_count': len(group),
                    'avg_similarity': avg_score,
                    'files': [
                        {
                            'id': vid[0],
                            'path': vid[1],
                            'size': vid[2],
                            'duration': vid[3],
                            'width': vid[4],
                            'height': vid[5],
                            'fps': vid[6],
                            'num_frames': vid[7]
                        } for vid in group
                    ]
                })
                
                # 更新进度
                if len(similar_groups) % 5 == 0:
                    self._on_progress(len(similar_groups) / max(1, total - len(used_ids)) * 100, 
                                    f"已找到 {len(similar_groups)} 个相似组")
        
        self._log(f"相似检测完成，共找到 {len(similar_groups)} 个相似组")
        return similar_groups
    
    def delete_video(self, video_id: int) -> bool:
        """
        删除指定的视频记录
        
        Args:
            video_id: 视频ID
        
        Returns:
            是否成功删除
        """
        try:
            with self._get_db_connection() as conn:
                conn.execute("DELETE FROM video_index WHERE id = ?", (video_id,))
            return True
        except Exception as e:
            self._log(f"删除视频记录失败: {e}", "ERROR")
            return False
    
    def get_statistics(self) -> Dict:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 总视频数
        cursor.execute("SELECT COUNT(*) FROM video_index")
        total_videos = cursor.fetchone()[0]
        
        # 总文件大小
        cursor.execute("SELECT SUM(size) FROM video_index")
        total_size = cursor.fetchone()[0] or 0
        
        # 总时长
        cursor.execute("SELECT SUM(duration) FROM video_index")
        total_duration = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_videos': total_videos,
            'total_size': total_size,
            'total_size_formatted': self._format_size(total_size),
            'total_duration': total_duration,
            'total_duration_formatted': self._format_duration(total_duration)
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化时长"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="视频相似度检测工具")
    parser.add_argument('directories', nargs='+', help='要扫描的目录')
    parser.add_argument('--db', default='video_similarity.db', help='数据库路径')
    parser.add_argument('--threshold', type=int, default=12, help='相似度阈值（汉明距离）')
    parser.add_argument('--output', help='输出JSON文件路径')
    
    args = parser.parse_args()
    
    # 创建检测器
    finder = VideoSimilarityFinder(db_path=args.db)
    
    # 构建索引
    finder.build_index(args.directories)
    
    # 查找相似组
    groups = finder.find_similar_groups(threshold_phash=args.threshold)
    
    # 输出结果
    if args.output:
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
            print(f"组 #{group['group_id']} (相似度: {group['avg_similarity']:.1f}%, {group['file_count']}个视频)")
            for file_info in group['files'][:3]:  # 每组只显示前3个
                print(f"  - {file_info['path']} (时长: {VideoSimilarityFinder._format_duration(file_info['duration'])})")
            if len(group['files']) > 3:
                print(f"  ... 还有 {len(group['files']) - 3} 个视频")
            print()


if __name__ == '__main__':
    main()
