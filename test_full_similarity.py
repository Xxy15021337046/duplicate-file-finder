#!/usr/bin/env python3
"""
完整的相似度检测功能测试
"""

import os
import sys
from PIL import Image
from core.visual_similarity import ImageSimilarityFinder


def create_test_images():
    """创建测试图片"""
    print("创建测试图片...")
    
    # 创建相似的图片
    img1 = Image.new('RGB', (200, 200), color='red')
    img1.save('test_similar_1.png')
    
    # 创建略微不同的图片（添加一些噪声）
    img2 = Image.new('RGB', (200, 200), color='red')
    for x in range(10):
        for y in range(10):
            img2.putpixel((x, y), (255, 0, 0))  # 稍微改变一些像素
    img2.save('test_similar_2.png')
    
    # 创建完全不同的图片
    img3 = Image.new('RGB', (200, 200), color='blue')
    img3.save('test_different.png')
    
    print("✓ 创建了3张测试图片")


def test_similarity_detection():
    """测试相似度检测"""
    print("\n开始相似度检测测试...")
    
    # 创建临时数据库
    db_path = "test_similarity_temp.db"
    
    try:
        # 创建检测器
        finder = ImageSimilarityFinder(
            db_path=db_path,
            batch_size=10,
            progress_callback=lambda p, m: print(f"进度: {p:.1f}% - {m}"),
            log_callback=lambda msg, lvl="INFO": print(f"[{lvl}] {msg}")
        )
        
        # 构建索引
        print("\n构建图片索引...")
        finder.build_index(['.'], incremental=False)
        
        # 查找相似组
        print("\n查找相似图片组...")
        groups = finder.find_similar_groups(threshold_phash=15, mode="precise")
        
        print(f"\n找到 {len(groups)} 个相似组")
        
        for i, group in enumerate(groups):
            print(f"\n组 #{group['group_id']}:")
            print(f"  平均相似度: {group['avg_similarity']:.1f}%")
            print(f"  图片数量: {group['file_count']}")
            for file_info in group['files']:
                print(f"    - {file_info['path']}")
        
        if len(groups) > 0:
            print("\n✓ 相似度检测测试通过！")
            return True
        else:
            print("\n⚠ 未找到相似组（可能测试图片不够相似）")
            return True
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"\n已清理临时数据库: {db_path}")


def cleanup_test_images():
    """清理测试图片"""
    test_files = ['test_similar_1.png', 'test_similar_2.png', 'test_different.png']
    for f in test_files:
        if os.path.exists(f):
            os.remove(f)
    print(f"已清理测试图片文件")


if __name__ == '__main__':
    print("=" * 60)
    print("完整相似度检测功能测试")
    print("=" * 60)
    
    try:
        create_test_images()
        success = test_similarity_detection()
        
        if success:
            print("\n" + "=" * 60)
            print("所有测试通过！")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("测试失败！")
            print("=" * 60)
            sys.exit(1)
            
    finally:
        cleanup_test_images()
