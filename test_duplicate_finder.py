#!/usr/bin/env python3
"""
测试脚本：创建测试环境验证重复文件检测功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path


def create_test_environment():
    """创建测试目录和文件"""
    test_dir = tempfile.mkdtemp(prefix='duplicate_test_')
    print(f"创建测试目录: {test_dir}")

    # 创建子目录
    dir1 = os.path.join(test_dir, 'folder1')
    dir2 = os.path.join(test_dir, 'folder2')
    dir3 = os.path.join(test_dir, 'folder3')
    os.makedirs(dir1)
    os.makedirs(dir2)
    os.makedirs(dir3)

    # 创建测试文件
    # 1. 创建重复文件（相同内容）
    content1 = b"This is a test file for duplicate detection. " * 100
    content2 = b"Another unique file with different content. " * 150
    content3 = b"Small file" * 10

    # 在folder1中创建文件
    file1_1 = os.path.join(dir1, 'file_a.txt')
    file1_2 = os.path.join(dir1, 'file_b.txt')
    file1_3 = os.path.join(dir1, 'file_c.txt')

    with open(file1_1, 'wb') as f:
        f.write(content1)
    with open(file1_2, 'wb') as f:
        f.write(content2)
    with open(file1_3, 'wb') as f:
        f.write(content3)

    # 在folder2中创建重复文件
    file2_1 = os.path.join(dir2, 'file_a_copy.txt')
    file2_2 = os.path.join(dir2, 'file_b_copy.txt')
    file2_3 = os.path.join(dir2, 'unique_file.txt')

    with open(file2_1, 'wb') as f:
        f.write(content1)  # 与file1_1重复
    with open(file2_2, 'wb') as f:
        f.write(content2)  # 与file1_2重复
    with open(file2_3, 'wb') as f:
        f.write(b"Unique content in folder2")

    # 在folder3中创建更多重复
    file3_1 = os.path.join(dir3, 'file_a_another_copy.txt')
    file3_2 = os.path.join(dir3, 'file_d.txt')

    with open(file3_1, 'wb') as f:
        f.write(content1)  # 与file1_1、file2_1重复
    with open(file3_2, 'wb') as f:
        f.write(b"Completely new file")

    print(f"\n测试文件结构:")
    print(f"  folder1/:")
    print(f"    - file_a.txt (重复组1)")
    print(f"    - file_b.txt (重复组2)")
    print(f"    - file_c.txt (唯一)")
    print(f"  folder2/:")
    print(f"    - file_a_copy.txt (重复组1)")
    print(f"    - file_b_copy.txt (重复组2)")
    print(f"    - unique_file.txt (唯一)")
    print(f"  folder3/:")
    print(f"    - file_a_another_copy.txt (重复组1)")
    print(f"    - file_d.txt (唯一)")

    return test_dir, [dir1, dir2, dir3]


def run_test():
    """运行测试"""
    print("="*60)
    print("重复文件检测系统 - 功能测试")
    print("="*60 + "\n")

    test_dir = None
    try:
        # 创建测试环境
        test_dir, directories = create_test_environment()

        # 导入检测器
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from duplicate_finder import DuplicateFinder

        # 创建检测器实例
        db_path = os.path.join(test_dir, 'test.db')
        finder = DuplicateFinder(db_path=db_path, max_workers=4)

        # 扫描目录
        print("\n" + "="*60)
        finder.scan_directories(directories)

        # 查找重复
        print("\n" + "="*60)
        duplicate_groups = finder.find_duplicates()

        # 打印结果
        finder.print_summary()

        # 导出JSON
        output_path = os.path.join(test_dir, 'test_results.json')
        if duplicate_groups:
            finder.export_results(duplicate_groups, output_path)

            # 读取并显示JSON内容
            import json
            with open(output_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            print("\n" + "="*60)
            print("详细结果:")
            print("="*60)
            print(f"发现 {len(duplicate_groups)} 个重复文件组\n")

            for i, group in enumerate(duplicate_groups, 1):
                print(f"重复组 {i}:")
                print(f"  文件大小: {finder._format_size(group[0]['file_size'])}")
                print(f"  文件数量: {len(group)}")
                print(f"  文件列表:")
                for file_info in group:
                    filename = os.path.basename(file_info['file_path'])
                    print(f"    - {filename}")
                print()

        # 验证结果
        print("="*60)
        print("测试结果验证:")
        print("="*60)

        expected_groups = 2  # 应该有两个重复组
        expected_duplicates = 3  # file_a有3个副本，file_b有2个副本

        actual_groups = len(duplicate_groups)
        actual_duplicates = sum(len(g) - 1 for g in duplicate_groups)

        print(f"预期重复组数: {expected_groups}")
        print(f"实际重复组数: {actual_groups}")
        status1 = "PASS" if actual_groups == expected_groups else "FAIL"
        print(f"状态: {status1}\n")

        print(f"预期重复文件数: {expected_duplicates}")
        print(f"实际重复文件数: {actual_duplicates}")
        status2 = "PASS" if actual_duplicates == expected_duplicates else "FAIL"
        print(f"状态: {status2}\n")

        if actual_groups == expected_groups and actual_duplicates == expected_duplicates:
            print("\n[SUCCESS] 所有测试通过！")
            return True
        else:
            print("\n[ERROR] 测试失败！")
            return False

    except Exception as e:
        print(f"\n[ERROR] 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理测试环境
        if test_dir and os.path.exists(test_dir):
            print(f"\n清理测试目录: {test_dir}")
            shutil.rmtree(test_dir)


if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
