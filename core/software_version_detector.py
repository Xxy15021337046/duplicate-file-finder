#!/usr/bin/env python3
"""
多版本软件检测引擎
用于识别同一软件的多个版本，解决MD5相同但实际是不同版本的问题
"""

import os
import sys
import re
import json
import sqlite3
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

try:
    import pefile
except ImportError:
    print("Warning: pefile not installed. Install with: pip install pefile")
    pefile = None

try:
    from packaging import version as pkg_version
except ImportError:
    print("Warning: packaging not installed. Install with: pip install packaging")
    pkg_version = None


class SoftwareVersionDetector:
    """多版本软件检测器"""
    
    # 支持的 executable 文件格式
    SUPPORTED_EXTENSIONS = {'.exe', '.dll', '.msi', '.jar', '.pyd'}
    
    # 常见软件模式匹配
    SOFTWARE_PATTERNS = {
        r'python(\d+\.\d+)': ('Python', 'Python.org'),
        r'node(js)?(\d+\.\d+)': ('Node.js', 'Node.js Foundation'),
        r'java.*?jdk[-_]?(\d+)': ('JDK', 'Oracle'),
        r'chrome': ('Chrome', 'Google'),
        r'firefox': ('Firefox', 'Mozilla'),
        r'edge': ('Edge', 'Microsoft'),
        r'opera': ('Opera', 'Opera Software'),
        r'safari': ('Safari', 'Apple'),
        r'vlc': ('VLC Media Player', 'VideoLAN'),
        r'7z': ('7-Zip', 'Igor Pavlov'),
        r'winrar': ('WinRAR', 'win.rar GmbH'),
        r'adobe.*?(reader|acrobat)': ('Adobe Reader', 'Adobe Systems'),
        r'photoshop': ('Photoshop', 'Adobe Systems'),
        r'illustrator': ('Illustrator', 'Adobe Systems'),
        r'office': ('Microsoft Office', 'Microsoft'),
        r'word': ('Microsoft Word', 'Microsoft'),
        r'excel': ('Microsoft Excel', 'Microsoft'),
        r'powerpoint': ('Microsoft PowerPoint', 'Microsoft'),
        r'visual.?studio': ('Visual Studio', 'Microsoft'),
        r'vscode': ('VS Code', 'Microsoft'),
        r'eclipse': ('Eclipse IDE', 'Eclipse Foundation'),
        r'intellij': ('IntelliJ IDEA', 'JetBrains'),
        r'pycharm': ('PyCharm', 'JetBrains'),
        r'webstorm': ('WebStorm', 'JetBrains'),
        r'android.?studio': ('Android Studio', 'Google'),
        r'xcode': ('Xcode', 'Apple'),
        r'docker': ('Docker', 'Docker Inc.'),
        r'git': ('Git', 'Git SCM'),
        r'sublime.?text': ('Sublime Text', 'Sublime HQ'),
        r'notepad\+\+': ('Notepad++', 'Don Ho'),
        r'vim': ('Vim', 'Bram Moolenaar'),
        r'emacs': ('Emacs', 'GNU'),
    }
    
    def __init__(self, 
                 db_path: str = "software_versions.db",
                 progress_callback=None,
                 log_callback=None):
        """
        初始化检测器
        
        Args:
            db_path: SQLite数据库路径
            progress_callback: 进度回调函数 callback(progress, message)
            log_callback: 日志回调函数 callback(message, level)
        """
        self.db_path = db_path
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        
        # PE信息缓存（LRU）
        self._pe_cache = {}
        self._max_cache_size = 1000
        
        # 初始化数据库
        self._init_database()
        
        self._log("SoftwareVersionDetector initialized", "INFO")
    
    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] {message}")
    
    def _update_progress(self, progress: float, message: str):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    def _init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 优化SQLite性能
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA cache_size=-64000')  # 64MB缓存
        cursor.execute('PRAGMA temp_store=MEMORY')
        
        # 创建软件索引表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS software_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                software_key TEXT NOT NULL,
                software_name TEXT NOT NULL,
                publisher TEXT,
                version TEXT,
                install_path TEXT,
                modified_time REAL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建软件分组表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS software_groups (
                software_key TEXT PRIMARY KEY,
                software_name TEXT NOT NULL,
                publisher TEXT,
                version_count INTEGER DEFAULT 0,
                total_files INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                latest_version TEXT,
                oldest_version TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_software_key ON software_index(software_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON software_index(file_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_install_path ON software_index(install_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_version_count ON software_groups(version_count)')
        
        conn.commit()
        conn.close()
        
        self._log("Database initialized", "INFO")
    
    def _compute_md5(self, filepath: str) -> str:
        """计算文件MD5哈希"""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(8192)  # 8KB chunks
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            self._log(f"Error computing MD5 for {filepath}: {e}", "ERROR")
            return ""
    
    def extract_pe_info(self, filepath: str) -> Optional[Dict]:
        """
        提取PE文件元数据
        
        Args:
            filepath: 文件路径
        
        Returns:
            dict: PE信息字典，失败返回None
        """
        if not pefile:
            return None
        
        # 检查缓存
        if filepath in self._pe_cache:
            return self._pe_cache[filepath]
        
        try:
            pe = pefile.PE(filepath, fast_load=True)
            
            info = {
                'company_name': '',
                'product_name': '',
                'file_version': '',
                'product_version': '',
                'file_description': '',
                'original_filename': ''
            }
            
            # 读取版本信息
            if hasattr(pe, 'VS_VERSIONINFO'):
                for fileinfo in pe.FileInfo:
                    for entry in fileinfo:
                        if entry.Key == b'StringFileInfo':
                            for st_entry in entry.StringTable:
                                for str_entry in st_entry.entries.items():
                                    try:
                                        key = str_entry[0].decode('utf-8', errors='ignore')
                                        value = str_entry[1].decode('utf-8', errors='ignore')
                                        
                                        if key == 'CompanyName':
                                            info['company_name'] = value
                                        elif key == 'ProductName':
                                            info['product_name'] = value
                                        elif key == 'FileVersion':
                                            info['file_version'] = value
                                        elif key == 'ProductVersion':
                                            info['product_version'] = value
                                        elif key == 'FileDescription':
                                            info['file_description'] = value
                                        elif key == 'OriginalFilename':
                                            info['original_filename'] = value
                                    except:
                                        continue
            
            pe.close()
            
            # 更新缓存
            if len(self._pe_cache) >= self._max_cache_size:
                self._pe_cache.pop(next(iter(self._pe_cache)))
            self._pe_cache[filepath] = info
            
            return info
            
        except Exception as e:
            self._log(f"Error extracting PE info from {filepath}: {e}", "WARNING")
            return None
    
    def identify_software(self, filepath: str, pe_info: Optional[Dict] = None) -> Dict:
        """
        识别软件身份
        
        Args:
            filepath: 文件路径
            pe_info: PE信息（可选）
        
        Returns:
            dict: 软件信息
        """
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0].lower()
        file_dir = os.path.dirname(filepath)
        
        # 优先级1：使用PE信息
        if pe_info and pe_info.get('product_name') and pe_info.get('company_name'):
            software_key = f"{pe_info['product_name']}_{pe_info['company_name']}"
            version_str = pe_info.get('file_version') or pe_info.get('product_version') or 'unknown'
            
            return {
                'software_key': software_key,
                'software_name': pe_info['product_name'],
                'publisher': pe_info['company_name'],
                'version': version_str,
                'install_path': file_dir
            }
        
        # 优先级2：模式匹配
        for pattern, (name, publisher) in self.SOFTWARE_PATTERNS.items():
            match = re.search(pattern, base_name, re.IGNORECASE)
            if match:
                # 尝试从匹配中提取版本号
                version_str = 'unknown'
                if match.lastindex:
                    version_str = match.group(match.lastindex)
                
                software_key = f"{name}_{publisher}"
                return {
                    'software_key': software_key,
                    'software_name': name,
                    'publisher': publisher,
                    'version': version_str,
                    'install_path': file_dir
                }
        
        # 优先级3：从路径中提取版本号
        # 常见路径模式：C:\Program Files\Python3.9\python.exe 或 C:\Software\Node.js\v16.14.0\node.exe
        version_patterns = [
            r'[vV]?(\d+\.\d+\.\d+)',  # v1.2.3 或 1.2.3
            r'[vV]?(\d+\.\d+)',       # v1.2 或 1.2
            r'[vV]?(\d+)',            # v1 或 1
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, file_dir)
            if match:
                version_str = match.group(1)
                break
        else:
            version_str = 'unknown'
        
        # 优先级3：使用文件名作为软件名
        software_key = f"{base_name}_Unknown"
        return {
            'software_key': software_key,
            'software_name': base_name,
            'publisher': 'Unknown',
            'version': version_str,
            'install_path': file_dir
        }
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """
        比较两个版本号
        
        Args:
            v1, v2: 版本号字符串
        
        Returns:
            int: -1 (v1 < v2), 0 (v1 == v2), 1 (v1 > v2)
        """
        if not pkg_version:
            # 降级为字符串比较
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        
        try:
            ver1 = pkg_version.parse(v1)
            ver2 = pkg_version.parse(v2)
            
            if ver1 < ver2:
                return -1
            elif ver1 > ver2:
                return 1
            else:
                return 0
        except:
            # 无法解析时按字符串比较
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
    
    def _scan_executables(self, directories: List[str], extensions: Optional[set] = None) -> List[str]:
        """
        扫描目录中的可执行文件
        
        Args:
            directories: 目录列表
            extensions: 要扫描的文件扩展名集合（None表示使用默认SUPPORTED_EXTENSIONS）
        
        Returns:
            list: 可执行文件路径列表
        """
        executables = []
        
        # 如果未指定extensions，使用默认的SUPPORTED_EXTENSIONS
        if extensions is None:
            extensions = self.SUPPORTED_EXTENSIONS
            self._log(f"Using default extensions: {sorted(extensions)}", "INFO")
        else:
            self._log(f"Using custom extensions filter: {sorted(extensions)}", "INFO")
        
        for directory in directories:
            if not os.path.exists(directory):
                self._log(f"Directory not found: {directory}", "WARNING")
                continue
            
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in extensions:
                        filepath = os.path.join(root, filename)
                        executables.append(filepath)
        
        self._log(f"Found {len(executables)} executable files", "INFO")
        return executables
    
    def build_index(self, directories: List[str], incremental: bool = True, extensions: Optional[set] = None):
        """
        构建软件索引
        
        Args:
            directories: 要扫描的目录列表
            incremental: 是否启用增量扫描
            extensions: 要扫描的文件扩展名集合（None表示使用默认SUPPORTED_EXTENSIONS）
        """
        self._log("Starting to build software index...", "INFO")
        
        # 扫描可执行文件，传入格式过滤
        executables = self._scan_executables(directories, extensions)
        total = len(executables)
        
        if total == 0:
            self._log("No executable files found", "WARNING")
            return
        
        # 批量处理
        batch_size = 100
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        processed = 0
        for i in range(0, total, batch_size):
            batch = executables[i:i + batch_size]
            
            for filepath in batch:
                try:
                    # 获取文件信息
                    file_size = os.path.getsize(filepath)
                    modified_time = os.path.getmtime(filepath)
                    file_hash = self._compute_md5(filepath)
                    
                    if not file_hash:
                        continue
                    
                    # 检查是否需要重新处理（增量模式）
                    if incremental:
                        cursor.execute(
                            'SELECT id FROM software_index WHERE path = ? AND file_hash = ?',
                            (filepath, file_hash)
                        )
                        if cursor.fetchone():
                            continue
                    
                    # 提取PE信息
                    pe_info = self.extract_pe_info(filepath)
                    
                    # 识别软件
                    software_info = self.identify_software(filepath, pe_info)
                    
                    # 插入数据库
                    cursor.execute('''
                        INSERT OR REPLACE INTO software_index 
                        (path, file_size, file_hash, software_key, software_name, 
                         publisher, version, install_path, modified_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        filepath,
                        file_size,
                        file_hash,
                        software_info['software_key'],
                        software_info['software_name'],
                        software_info['publisher'],
                        software_info['version'],
                        software_info['install_path'],
                        modified_time
                    ))
                    
                    processed += 1
                    
                except Exception as e:
                    self._log(f"Error processing {filepath}: {e}", "ERROR")
                    continue
            
            # 更新进度
            progress = min(100, (i + batch_size) / total * 100)
            self._update_progress(progress, f"Processing executables... ({min(i + batch_size, total)}/{total})")
            
            # 提交当前批次
            conn.commit()
        
        # 更新软件分组表
        self._update_software_groups(cursor)
        conn.commit()
        conn.close()
        
        self._log(f"Index built successfully. Processed {processed} files.", "SUCCESS")
        self._update_progress(100, "Index building completed")
    
    def _update_software_groups(self, cursor):
        """更新软件分组统计表"""
        # 清空旧数据
        cursor.execute('DELETE FROM software_groups')
        
        # 重新统计
        cursor.execute('''
            SELECT 
                software_key,
                software_name,
                publisher,
                COUNT(*) as version_count,
                SUM(file_size) as total_size,
                GROUP_CONCAT(version) as versions
            FROM software_index
            GROUP BY software_key
        ''')
        
        rows = cursor.fetchall()
        
        for row in rows:
            software_key, software_name, publisher, version_count, total_size, versions_str = row
            
            # 解析版本列表并找出最新和最旧版本
            versions = [v.strip() for v in versions_str.split(',') if v.strip()]
            latest_version = max(versions, key=lambda v: self._version_sort_key(v)) if versions else ''
            oldest_version = min(versions, key=lambda v: self._version_sort_key(v)) if versions else ''
            
            cursor.execute('''
                INSERT INTO software_groups 
                (software_key, software_name, publisher, version_count, total_files, 
                 total_size, latest_version, oldest_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                software_key,
                software_name,
                publisher,
                version_count,
                version_count,  # total_files = version_count (one file per version)
                total_size,
                latest_version,
                oldest_version
            ))
    
    def _version_sort_key(self, version_str: str):
        """生成版本排序键"""
        if not pkg_version:
            return (0, version_str)
        
        try:
            ver = pkg_version.parse(version_str)
            # 返回元组 (1, Version对象) 表示有效版本号
            return (1, ver)
        except:
            # 返回元组 (0, 字符串) 表示无效版本号（如 'unknown'）
            return (0, version_str)
    
    def find_multiple_versions(self, min_versions: int = 2) -> List[Dict]:
        """
        查找具有多个版本的软件
        
        Args:
            min_versions: 最小版本数（默认2）
        
        Returns:
            list: 多版本软件组列表
        """
        self._log("Finding software with multiple versions...", "INFO")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询多版本软件
        cursor.execute('''
            SELECT * FROM software_groups 
            WHERE version_count >= ?
            ORDER BY version_count DESC, total_size DESC
        ''', (min_versions,))
        
        groups = []
        for idx, row in enumerate(cursor.fetchall(), start=1):
            (software_key, software_name, publisher, version_count, 
             total_files, total_size, latest_version, oldest_version) = row[:8]
            
            # 获取该软件的详细文件列表
            cursor.execute('''
                SELECT path, file_size, file_hash, version, install_path, modified_time
                FROM software_index
                WHERE software_key = ?
                ORDER BY path
            ''', (software_key,))
            
            files = []
            for file_row in cursor.fetchall():
                path, size, hash_val, version, install_path, mtime = file_row
                files.append({
                    'path': path,
                    'size': size,
                    'hash': hash_val,
                    'version': version,
                    'install_path': install_path,
                    'modified_time': mtime
                })
            
            group = {
                'group_id': idx,
                'software_key': software_key,
                'software_name': software_name,
                'publisher': publisher,
                'version_count': version_count,
                'total_size': total_size,
                'latest_version': latest_version,
                'oldest_version': oldest_version,
                'files': files
            }
            
            groups.append(group)
        
        conn.close()
        
        self._log(f"Found {len(groups)} software with multiple versions", "SUCCESS")
        return groups
    
    def export_results(self, groups: List[Dict], output_path: str):
        """
        导出结果为JSON
        
        Args:
            groups: 软件组列表
            output_path: 输出文件路径
        """
        self._log(f"Exporting results to {output_path}...", "INFO")
        
        # 计算统计信息
        total_files = sum(g['version_count'] for g in groups)
        total_size = sum(g['total_size'] for g in groups)
        
        results = {
            'scan_summary': {
                'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_software_detected': len(groups),
                'multiple_version_software': len(groups),
                'total_files_scanned': total_files,
                'total_wasted_space': total_size,
                'total_wasted_space_formatted': self._format_size(total_size)
            },
            'software_groups': []
        }
        
        for group in groups:
            group_data = {
                'group_id': group['group_id'],
                'software_key': group['software_key'],
                'software_name': group['software_name'],
                'publisher': group['publisher'],
                'version_count': group['version_count'],
                'total_size': group['total_size'],
                'total_size_formatted': self._format_size(group['total_size']),
                'latest_version': group['latest_version'],
                'oldest_version': group['oldest_version'],
                'files': []
            }
            
            for file_info in group['files']:
                file_data = {
                    'path': file_info['path'],
                    'version': file_info['version'],
                    'size': file_info['size'],
                    'size_formatted': self._format_size(file_info['size']),
                    'modified_time': file_info['modified_time']
                }
                group_data['files'].append(file_data)
            
            results['software_groups'].append(group_data)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self._log(f"Results exported successfully", "SUCCESS")
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    def delete_file(self, filepath: str) -> bool:
        """
        删除文件并更新数据库
        
        Args:
            filepath: 要删除的文件路径
        
        Returns:
            bool: 是否成功
        """
        try:
            # 删除文件
            os.remove(filepath)
            
            # 更新数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 删除索引记录
            cursor.execute('DELETE FROM software_index WHERE path = ?', (filepath,))
            
            # 更新分组统计
            self._update_software_groups(cursor)
            
            conn.commit()
            conn.close()
            
            self._log(f"Deleted file: {filepath}", "INFO")
            return True
            
        except Exception as e:
            self._log(f"Error deleting file {filepath}: {e}", "ERROR")
            return False


if __name__ == '__main__':
    # 测试代码
    detector = SoftwareVersionDetector(
        db_path="test_software.db",
        progress_callback=lambda p, m: print(f"Progress: {p}% - {m}"),
        log_callback=lambda m, l: print(f"[{l}] {m}")
    )
    
    # 示例：扫描指定目录
    test_dirs = [r"C:\Program Files"]
    detector.build_index(test_dirs)
    
    # 查找多版本软件
    groups = detector.find_multiple_versions()
    
    # 导出结果
    if groups:
        detector.export_results(groups, "test_results.json")
        print(f"\nFound {len(groups)} software with multiple versions")
        for group in groups[:5]:  # 只显示前5个
            print(f"  - {group['software_name']}: {group['version_count']} versions")
