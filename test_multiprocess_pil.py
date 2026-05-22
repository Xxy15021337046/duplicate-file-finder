#!/usr/bin/env python3
"""
测试多进程环境下的PIL导入问题
"""

import sys
import os
from concurrent.futures import ProcessPoolExecutor, as_completed


def test_pil_import_in_process(image_path):
    """在多进程中测试PIL导入"""
    try:
        # 模拟visual_similarity.py中的导入方式
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from PIL import Image
        import imagehash
        
        print(f"✓ 成功在子进程中导入PIL和imagehash")
        print(f"  PIL路径: {Image.__file__}")
        print(f"  imagehash路径: {imagehash.__file__}")
        
        # 尝试打开图片
        img = Image.open(image_path)
        print(f"✓ 成功打开图片: {image_path}")
        print(f"  尺寸: {img.size}")
        
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # 创建一个测试图片
    from PIL import Image
    test_image = "test_image.png"
    
    print("创建测试图片...")
    img = Image.new('RGB', (100, 100), color='red')
    img.save(test_image)
    
    print(f"\n测试单张图片的多进程处理...")
    
    # 使用ProcessPoolExecutor测试多进程
    with ProcessPoolExecutor(max_workers=2) as executor:
        future = executor.submit(test_pil_import_in_process, test_image)
        result = future.result()
        
        if result:
            print("\n✓ 多进程PIL导入测试通过！")
        else:
            print("\n✗ 多进程PIL导入测试失败！")
    
    # 清理测试文件
    if os.path.exists(test_image):
        os.remove(test_image)
        print(f"已清理测试文件: {test_image}")
