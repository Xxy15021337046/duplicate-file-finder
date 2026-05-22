#!/usr/bin/env python3
"""
Complete test for similarity detection
Test algorithm, GUI integration, and all features
"""

import os
import sys
import tempfile
import shutil
from PIL import Image, ImageDraw

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.visual_similarity import ImageSimilarityFinder


def create_comprehensive_test_images(test_dir: str):
    """Create comprehensive test images"""
    os.makedirs(test_dir, exist_ok=True)

    # Group 1: 3 identical red squares
    img1 = Image.new('RGB', (100, 100), color='red')
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle((10, 10, 90, 90), fill='blue')
    img1.save(os.path.join(test_dir, 'red_1.png'))
    img1.save(os.path.join(test_dir, 'red_copy1.png'))
    img1.save(os.path.join(test_dir, 'red_copy2.png'))

    # Group 2: 2 identical green circles
    img2 = Image.new('RGB', (100, 100), color='green')
    draw2 = ImageDraw.Draw(img2)
    draw2.ellipse((10, 10, 90, 90), fill='yellow')
    img2.save(os.path.join(test_dir, 'green_1.png'))
    img2.save(os.path.join(test_dir, 'green_copy.png'))

    # Group 3: Different image
    img3 = Image.new('RGB', (100, 100), color='white')
    draw3 = ImageDraw.Draw(img3)
    draw3.polygon([(10, 10), (90, 50), (10, 90)], fill='black')
    img3.save(os.path.join(test_dir, 'different.png'))

    print(f"[TEST] Created {len(os.listdir(test_dir))} test images")
    return test_dir


def test_algorithm():
    """Test the core algorithm"""
    print("\n" + "="*60)
    print("TEST 1: Core Algorithm")
    print("="*60)
    
    test_dir = tempfile.mkdtemp(prefix="similarity_test_")
    db_path = os.path.join(test_dir, "test.db")

    try:
        # Create test images
        create_comprehensive_test_images(test_dir)

        # Create finder
        finder = ImageSimilarityFinder(
            db_path=db_path,
            batch_size=100,
            progress_callback=lambda p, m: None,  # Silent
            log_callback=lambda m, l="INFO": None  # Silent
        )

        # Build index
        print("[STEP 1] Building index...")
        finder.build_index([test_dir], incremental=False)
        print("  [OK] Index built successfully")

        # Find similar groups with loose threshold
        print("[STEP 2] Finding similar groups (threshold=30)...")
        groups = finder.find_similar_groups(threshold_phash=30, mode="precise")
        print(f"  [OK] Found {len(groups)} similar groups")

        # Verify results
        print("[STEP 3] Verifying results...")
        
        has_red_group = False
        has_green_group = False
        
        for group in groups:
            filenames = [os.path.basename(f['path']) for f in group['files']]
            
            if any('red' in f for f in filenames):
                has_red_group = True
                red_count = sum(1 for f in filenames if 'red' in f)
                print(f"  [OK] Red group: {red_count} images (expected 3)")
                assert red_count == 3, f"Expected 3 red images, got {red_count}"
            
            if any('green' in f for f in filenames):
                has_green_group = True
                green_count = sum(1 for f in filenames if 'green' in f)
                print(f"  [OK] Green group: {green_count} images (expected 2)")
                assert green_count == 2, f"Expected 2 green images, got {green_count}"
        
        assert has_red_group, "Red group not found"
        assert has_green_group, "Green group not found"
        
        print("\n[SUCCESS] All algorithm tests passed!")
        return True

    except Exception as e:
        print(f"\n[FAILURE] Algorithm test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_gui_integration():
    """Test GUI integration"""
    print("\n" + "="*60)
    print("TEST 2: GUI Integration")
    print("="*60)
    
    try:
        from gui_modules.similarity_tab import SimilarityTab
        print("[OK] GUI module imported successfully")
        
        # Check that required methods exist
        required_methods = [
            '_show_results_window',
            '_display_all_results',
            '_on_click_actions_column',
            '_on_double_click_group',
            '_hide_group_by_num',
            '_hide_group',
            '_show_all_groups'
        ]
        
        for method in required_methods:
            assert hasattr(SimilarityTab, method), f"Missing method: {method}"
            print(f"  [OK] Method exists: {method}")
        
        print("\n[SUCCESS] All GUI integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n[FAILURE] GUI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("COMPLETE SIMILARITY DETECTION TEST SUITE")
    print("="*60)
    
    test1_passed = test_algorithm()
    test2_passed = test_gui_integration()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Algorithm Test:       {'[PASSED]' if test1_passed else '[FAILED]'}")
    print(f"GUI Integration Test: {'[PASSED]' if test2_passed else '[FAILED]'}")
    print("="*60)
    
    if test1_passed and test2_passed:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n[FAILURE] SOME TESTS FAILED!")
        sys.exit(1)
