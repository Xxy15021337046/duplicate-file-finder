#!/usr/bin/env python3
"""
测试相似度检测修复
验证相同图片能否被正确识别
"""

import os
import sys
import tempfile
import shutil
from PIL import Image, ImageDraw

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.visual_similarity import ImageSimilarityFinder


def create_test_images(test_dir: str):
    """创建测试图片"""
    # 创建测试目录
    os.makedirs(test_dir, exist_ok=True)

    # 创建完全相同的图片（复制）
    img1 = Image.new('RGB', (100, 100), color='red')
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle((10, 10, 90, 90), fill='blue')
    img1.save(os.path.join(test_dir, 'test1_original.png'))

    # 复制相同的图片
    img1.save(os.path.join(test_dir, 'test1_copy1.png'))
    img1.save(os.path.join(test_dir, 'test1_copy2.png'))

    # 创建另一组相同的图片
    img2 = Image.new('RGB', (100, 100), color='green')
    draw2 = ImageDraw.Draw(img2)
    draw2.ellipse((10, 10, 90, 90), fill='yellow')
    img2.save(os.path.join(test_dir, 'test2_original.png'))
    img2.save(os.path.join(test_dir, 'test2_copy.png'))

    # 创建不同的图片
    img3 = Image.new('RGB', (100, 100), color='white')
    draw3 = ImageDraw.Draw(img3)
    draw3.polygon([(10, 10), (90, 50), (10, 90)], fill='black')
    img3.save(os.path.join(test_dir, 'test3_different.png'))

    print(f"✓ 创建了 {len(os.listdir(test_dir))} 张测试图片")


def test_similarity_detection():
    """测试相似度检测"""
    # 创建临时测试目录
    test_dir = tempfile.mkdtemp(prefix="similarity_test_")
    db_path = os.path.join(test_dir, "test.db")

    try:
        # 创建测试图片
        create_test_images(test_dir)

        # 创建检测器
        finder = ImageSimilarityFinder(
            db_path=db_path,
            batch_size=100,
            progress_callback=lambda p, m: print(f"进度: {p:.1f}% - {m}"),
            log_callback=lambda m, l="INFO": print(f"[{l}] {m}")
        )

        # 构建索引
        print("\n=== 开始构建索引 ===")
        finder.build_index([test_dir], incremental=False)

        # 查找相似组（使用宽松阈值）
        print("\n=== 开始查找相似组 ===")
        groups = finder.find_similar_groups(threshold_phash=20, mode="precise")

        # 显示结果
        print(f"\n=== 检测结果 ===")
        print(f"找到 {len(groups)} 个相似组")

        for group in groups:
            print(f"\n组 #{group['group_id']} (相似度: {group['avg_similarity']:.1f}%, {group['file_count']}张图片)")
            for file_info in group['files']:
                filename = os.path.basename(file_info['path'])
                print(f"  - {filename} ({file_info['width']}x{file_info['height']})")

        # 验证结果
        expected_groups = 2  # 应该有2组：红色矩形组和绿色圆形组
        if len(groups) >= expected_groups:
            print(f"\n✅ 测试通过！找到了 {len(groups)} 个相似组（预期至少 {expected_groups} 个）")
            
            # 检查每组是否包含正确的图片
            has_red_group = False
            has_green_group = False
            
            for group in groups:
                filenames = [os.path.basename(f['path']) for f in group['files']]
                
                # 检查红色组
                if any('test1' in f for f in filenames):
                    has_red_group = True
                    print(f"  ✓ 红色矩形组包含 {len(filenames)} 张图片")
                
                # 检查绿色组
                if any('test2' in f for f in filenames):
                    has_green_group = True
                    print(f"  ✓ 绿色圆形组包含 {len(filenames)} 张图片")
            
            if has_red_group and has_green_group:
                print("\n✅ 所有相同图片都被正确识别！")
            else:
                print("\n❌ 部分相同图片未被识别")
        else:
            print(f"\n❌ 测试失败！只找到 {len(groups)} 个相似组，预期至少 {expected_groups} 个")

    finally:
        # 清理临时文件
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"\n已清理测试目录: {test_dir}")


if __name__ == '__main__':
    test_similarity_detection()
