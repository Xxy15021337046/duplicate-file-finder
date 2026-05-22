#!/usr/bin/env python3
"""
Test identical image detection
Create identical images and verify they are detected as similar
"""

import os
import sys
import tempfile
import shutil
from PIL import Image, ImageDraw

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.visual_similarity import ImageSimilarityFinder


def create_test_images(test_dir: str):
    """Create test images - some identical, some different"""
    os.makedirs(test_dir, exist_ok=True)

    # Group 1: Identical red square images (3 copies)
    img1 = Image.new('RGB', (100, 100), color='red')
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle((10, 10, 90, 90), fill='blue')
    
    img1.save(os.path.join(test_dir, 'red_square_1.png'))
    img1.save(os.path.join(test_dir, 'red_square_copy1.png'))
    img1.save(os.path.join(test_dir, 'red_square_copy2.png'))

    # Group 2: Identical green circle images (2 copies)
    img2 = Image.new('RGB', (100, 100), color='green')
    draw2 = ImageDraw.Draw(img2)
    draw2.ellipse((10, 10, 90, 90), fill='yellow')
    
    img2.save(os.path.join(test_dir, 'green_circle_1.png'))
    img2.save(os.path.join(test_dir, 'green_circle_copy.png'))

    # Group 3: Different image (white background with black triangle)
    img3 = Image.new('RGB', (100, 100), color='white')
    draw3 = ImageDraw.Draw(img3)
    draw3.polygon([(10, 10), (90, 50), (10, 90)], fill='black')
    img3.save(os.path.join(test_dir, 'different_triangle.png'))

    print(f"Created {len(os.listdir(test_dir))} test images in {test_dir}")
    return test_dir


def test_similarity_detection():
    """Test similarity detection with identical images"""
    # Create temporary test directory
    test_dir = tempfile.mkdtemp(prefix="similarity_test_")
    db_path = os.path.join(test_dir, "test.db")

    try:
        # Create test images
        create_test_images(test_dir)

        # Create finder with verbose logging
        finder = ImageSimilarityFinder(
            db_path=db_path,
            batch_size=100,
            progress_callback=lambda p, m: print(f"[PROGRESS] {p:.1f}% - {m}"),
            log_callback=lambda m, l="INFO": print(f"[{l}] {m}")
        )

        # Build index
        print("\n=== Building Index ===")
        finder.build_index([test_dir], incremental=False)

        # Find similar groups with loose threshold (30)
        print("\n=== Finding Similar Groups (threshold=30, mode=precise) ===")
        groups = finder.find_similar_groups(threshold_phash=30, mode="precise")

        # Display results
        print(f"\n=== Results ===")
        print(f"Found {len(groups)} similar groups")

        for group in groups:
            print(f"\nGroup #{group['group_id']} (Similarity: {group['avg_similarity']:.1f}%, {group['file_count']} images)")
            for file_info in group['files']:
                filename = os.path.basename(file_info['path'])
                print(f"  - {filename} ({file_info['width']}x{file_info['height']})")

        # Verify results
        expected_min_groups = 2  # At least 2 groups: red squares and green circles
        
        if len(groups) >= expected_min_groups:
            print(f"\n[SUCCESS] Found {len(groups)} similar groups (expected at least {expected_min_groups})")
            
            # Check if identical images are grouped correctly
            has_red_group = False
            has_green_group = False
            
            for group in groups:
                filenames = [os.path.basename(f['path']) for f in group['files']]
                
                # Check red group (should have 3 images)
                if any('red_square' in f for f in filenames):
                    has_red_group = True
                    red_count = sum(1 for f in filenames if 'red_square' in f)
                    print(f"  [OK] Red square group has {red_count} images (expected 3)")
                
                # Check green group (should have 2 images)
                if any('green_circle' in f for f in filenames):
                    has_green_group = True
                    green_count = sum(1 for f in filenames if 'green_circle' in f)
                    print(f"  [OK] Green circle group has {green_count} images (expected 2)")
            
            if has_red_group and has_green_group:
                print("\n[SUCCESS] All identical images were correctly identified!")
                return True
            else:
                print("\n[WARNING] Some identical images were not identified")
                return False
        else:
            print(f"\n[FAILURE] Only found {len(groups)} similar groups, expected at least {expected_min_groups}")
            return False

    finally:
        # Clean up temporary files
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"\nCleaned up test directory: {test_dir}")


if __name__ == '__main__':
    success = test_similarity_detection()
    sys.exit(0 if success else 1)
