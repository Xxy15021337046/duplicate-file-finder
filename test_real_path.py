#!/usr/bin/env python3
"""
Test with real path: D:\文档
"""

import os
import sys

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.visual_similarity import ImageSimilarityFinder


def test_real_path():
    """Test with real path D:\文档"""
    test_dir = r"D:\文档"
    db_path = "test_real_db.db"

    # Remove old database if exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[INFO] Removed old database: {db_path}")

    try:
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

        if len(groups) == 0:
            print("\n[WARNING] No similar groups found!")
            print("This could mean:")
            print("1. All images are truly different")
            print("2. Threshold is too strict")
            print("3. Images were not indexed properly")
            return False

        for i, group in enumerate(groups[:10]):  # Show first 10 groups
            print(f"\nGroup #{group['group_id']} (Similarity: {group['avg_similarity']:.1f}%, {group['file_count']} images)")
            for file_info in group['files']:
                # Get relative path for better readability
                rel_path = os.path.relpath(file_info['path'], test_dir)
                filename = os.path.basename(file_info['path'])
                print(f"  - {filename} ({file_info['width']}x{file_info['height']})")
                print(f"    Path: {rel_path}")

        if len(groups) > 10:
            print(f"\n... and {len(groups) - 10} more groups")

        print(f"\n[SUCCESS] Found {len(groups)} similar groups!")
        return True

    except Exception as e:
        print(f"\n[FAILURE] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Keep database for inspection
        print(f"\n[INFO] Database saved to: {db_path}")


if __name__ == '__main__':
    success = test_real_path()
    sys.exit(0 if success else 1)
