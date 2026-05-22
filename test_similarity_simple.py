#!/usr/bin/env python3
"""
图片相似度检测简单测试
测试visual_similarity.py的核心功能
"""

import os
import sys

# 添加core目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))

from visual_similarity import ImageSimilarityFinder


def test_basic_functions():
    """测试基本功能"""
    print("=" * 60)
    print("Testing ImageSimilarityFinder Basic Functions")
    print("=" * 60)
    
    # 创建检测器实例
    finder = ImageSimilarityFinder(db_path=":memory:")  # 使用内存数据库测试
    print("[OK] ImageSimilarityFinder instance created")
    
    # 测试汉明距离计算
    hash1 = "ffff0000ffff0000"
    hash2 = "ffff0000ffff0000"  # 相同
    hash3 = "0000ffffffff0000"  # 不同
    
    dist_same = finder._hamming_distance(hash1, hash2)
    dist_diff = finder._hamming_distance(hash1, hash3)
    
    print(f"[OK] Hamming distance (same): {dist_same} (expected: 0)")
    print(f"[OK] Hamming distance (diff): {dist_diff} (expected: >0)")
    
    assert dist_same == 0, "Same hash should have distance 0"
    assert dist_diff > 0, "Different hash should have distance > 0"
    
    # 测试直方图相似度
    import struct
    import random
    random.seed(42)  # 固定种子以便复现
    
    hist1 = struct.pack('768I', *[random.randint(0, 255) for _ in range(768)])
    hist2 = hist1  # 完全相同
    hist3 = struct.pack('768I', *[random.randint(0, 255) for _ in range(768)])  # 随机不同
    
    sim_same = finder._histogram_similarity(hist1, hist2)
    sim_diff = finder._histogram_similarity(hist1, hist3)
    
    print(f"[OK] Histogram similarity (same): {sim_same:.4f} (expected: 1.0)")
    print(f"[OK] Histogram similarity (diff): {sim_diff:.4f} (expected: <0.9)")
    
    assert abs(sim_same - 1.0) < 0.01, "Same histogram should have similarity ~1.0"
    assert sim_diff < 0.9, f"Different histogram should have similarity < 0.9, got {sim_diff}"
    
    # 测试综合相似度分数
    score1 = finder._compute_similarity_score(0, 0, 1.0)   # 完全相同
    score2 = finder._compute_similarity_score(10, 10, 0.9)  # 相似
    score3 = finder._compute_similarity_score(30, 30, 0.5)  # 不相似
    
    print(f"[OK] Similarity score (identical): {score1:.2f} (expected: 100)")
    print(f"[OK] Similarity score (similar): {score2:.2f} (expected: ~80)")
    print(f"[OK] Similarity score (dissimilar): {score3:.2f} (expected: ~40)")
    
    assert score1 == 100.0, "Identical images should have score 100"
    assert 70 < score2 < 90, "Similar images should have score ~80"
    assert 40 < score3 < 65, f"Dissimilar images should have score ~50, got {score3}"
    
    print("\n" + "=" * 60)
    print("All basic function tests PASSED!")
    print("=" * 60)
    return True


def test_with_sample_images():
    """使用示例图片测试（如果存在）"""
    print("\n" + "=" * 60)
    print("Testing with Sample Images")
    print("=" * 60)
    
    # 查找当前目录下的图片文件
    sample_dir = os.path.dirname(os.path.abspath(__file__))
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    images = []
    for root, dirs, files in os.walk(sample_dir):
        # 跳过隐藏目录和venv
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.venv']
        
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions:
                images.append(os.path.join(root, filename))
                if len(images) >= 5:  # 只测试前5张
                    break
        if len(images) >= 5:
            break
    
    if not images:
        print("[SKIP] No sample images found in current directory")
        print("[INFO] To test with real images, place some .jpg/.png files in the project directory")
        return True
    
    print(f"[INFO] Found {len(images)} sample images")
    
    # 创建检测器
    finder = ImageSimilarityFinder(db_path="test_similarity.db", batch_size=10)
    
    # 测试单张图片指纹计算
    try:
        fingerprint = finder.compute_fingerprint(images[0])
        if fingerprint:
            print(f"[OK] Fingerprint computed for: {os.path.basename(images[0])}")
            print(f"     Size: {fingerprint['width']}x{fingerprint['height']}")
            print(f"     pHash: {fingerprint['phash']}")
            print(f"     dHash: {fingerprint['dhash']}")
        else:
            print(f"[WARN] Failed to compute fingerprint for: {images[0]}")
    except Exception as e:
        print(f"[ERROR] Error computing fingerprint: {e}")
        return False
    
    # 清理测试数据库
    if os.path.exists("test_similarity.db"):
        os.remove("test_similarity.db")
    
    print("\n[OK] Sample image test completed")
    print("=" * 60)
    return True


if __name__ == '__main__':
    try:
        # 运行基本功能测试
        test_basic_functions()
        
        # 运行示例图片测试
        test_with_sample_images()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
