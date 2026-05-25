#!/usr/bin/env python3
"""
视频相似度检测核心功能测试脚本
用于验证OpenCV安装、关键帧提取、指纹计算等基础功能
"""

import os
import sys


def test_opencv_installation():
    """测试OpenCV是否正确安装"""
    print("=" * 60)
    print("测试1: OpenCV安装验证")
    print("=" * 60)
    
    try:
        import cv2
        print(f"✓ OpenCV版本: {cv2.__version__}")
        
        # 检查是否有视频编解码器支持
        print(f"✓ OpenCV可用编解码器: {len(cv2.videoio_registry.getBackendList())}个")
        
        return True
    except ImportError as e:
        print(f"✗ OpenCV未安装或导入失败: {e}")
        print("\n请运行: pip install opencv-python-headless")
        return False


def test_pillow_installation():
    """测试Pillow是否正确安装"""
    print("\n" + "=" * 60)
    print("测试2: Pillow安装验证")
    print("=" * 60)
    
    try:
        from PIL import Image
        print(f"✓ Pillow已安装")
        return True
    except ImportError as e:
        print(f"✗ Pillow未安装或导入失败: {e}")
        print("\n请运行: pip install Pillow")
        return False


def test_imagehash_installation():
    """测试imagehash是否正确安装"""
    print("\n" + "=" * 60)
    print("测试3: imagehash安装验证")
    print("=" * 60)
    
    try:
        import imagehash
        print(f"✓ imagehash已安装")
        return True
    except ImportError as e:
        print(f"✗ imagehash未安装或导入失败: {e}")
        print("\n请运行: pip install imagehash")
        return False


def test_numpy_installation():
    """测试numpy是否正确安装"""
    print("\n" + "=" * 60)
    print("测试4: NumPy安装验证")
    print("=" * 60)
    
    try:
        import numpy as np
        print(f"✓ NumPy版本: {np.__version__}")
        return True
    except ImportError as e:
        print(f"✗ NumPy未安装或导入失败: {e}")
        print("\n请运行: pip install numpy")
        return False


def test_video_module_import():
    """测试video_similarity模块是否可以导入"""
    print("\n" + "=" * 60)
    print("测试5: video_similarity模块导入验证")
    print("=" * 60)
    
    try:
        # 添加项目根目录到Python路径
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from core.video_similarity import VideoSimilarityFinder, calculate_sample_frames
        
        print(f"✓ video_similarity模块导入成功")
        print(f"✓ VideoSimilarityFinder类可用")
        print(f"✓ calculate_sample_frames函数可用")
        
        return True
    except Exception as e:
        print(f"✗ video_similarity模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hamming_distance():
    """测试汉明距离计算"""
    print("\n" + "=" * 60)
    print("测试6: 汉明距离计算验证")
    print("=" * 60)
    
    try:
        from core.video_similarity import VideoSimilarityFinder
        
        # 测试相同哈希
        hash1 = "a3f5b2c1d4e6f789"
        hash2 = "a3f5b2c1d4e6f789"
        dist = VideoSimilarityFinder._hamming_distance(hash1, hash2)
        assert dist == 0, f"相同哈希的汉明距离应为0，实际为{dist}"
        print(f"✓ 相同哈希测试通过 (距离={dist})")
        
        # 测试不同哈希
        hash3 = "b4g6c3d2e5f7h890"
        dist2 = VideoSimilarityFinder._hamming_distance(hash1, hash3)
        assert dist2 > 0, f"不同哈希的汉明距离应>0，实际为{dist2}"
        print(f"✓ 不同哈希测试通过 (距离={dist2})")
        
        return True
    except Exception as e:
        print(f"✗ 汉明距离计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sample_frames_calculation():
    """测试采样帧数计算"""
    print("\n" + "=" * 60)
    print("测试7: 采样帧数计算验证")
    print("=" * 60)
    
    try:
        from core.video_similarity import calculate_sample_frames
        
        test_cases = [
            (5, 5),    # <10秒 → 5帧
            (30, 10),  # 10-60秒 → 10帧
            (150, 20), # 60-300秒 → 20帧
            (600, 50), # >300秒 → 最多50帧
        ]
        
        for duration, expected in test_cases:
            result = calculate_sample_frames(duration)
            status = "✓" if result == expected else "✗"
            print(f"{status} 时长{duration}秒 → {result}帧 (期望{expected}帧)")
            
            if result != expected:
                return False
        
        return True
    except Exception as e:
        print(f"✗ 采样帧数计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_initialization():
    """测试数据库初始化"""
    print("\n" + "=" * 60)
    print("测试8: 数据库初始化验证")
    print("=" * 60)
    
    try:
        from core.video_similarity import VideoSimilarityFinder
        
        # 创建临时测试数据库
        test_db = "test_video_db.db"
        finder = VideoSimilarityFinder(db_path=test_db)
        
        # 检查数据库文件是否创建
        if os.path.exists(test_db):
            print(f"✓ 数据库文件创建成功: {test_db}")
            
            # 清理测试文件
            os.remove(test_db)
            print(f"✓ 测试数据库已清理")
            
            return True
        else:
            print(f"✗ 数据库文件未创建")
            return False
            
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("视频相似度检测核心功能测试")
    print("=" * 60)
    
    tests = [
        ("OpenCV安装", test_opencv_installation),
        ("Pillow安装", test_pillow_installation),
        ("imagehash安装", test_imagehash_installation),
        ("NumPy安装", test_numpy_installation),
        ("模块导入", test_video_module_import),
        ("汉明距离计算", test_hamming_distance),
        ("采样帧数计算", test_sample_frames_calculation),
        ("数据库初始化", test_database_initialization),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n{name}测试异常: {e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")
    
    print("\n" + "-" * 60)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！视频相似度检测环境准备就绪。")
        print("\n下一步:")
        print("1. 准备测试视频文件")
        print("2. 运行完整功能测试: python test_video_similarity.py")
        print("3. 启动GUI界面: python run_gui.py")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败，请检查依赖安装。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
