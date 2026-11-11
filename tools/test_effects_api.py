"""
Test Effects API - Verify effects loading
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.visual_effect_library import VisualEffectLibrary

def main():
    print("=" * 70)
    print("  Test Effects API - Load Effects")
    print("=" * 70)
    print()

    # Initialize library
    library = VisualEffectLibrary()

    # Get all effects
    all_effects = library.get_all_effects()
    print(f"[OK] Loaded {len(all_effects)} effects from library")
    print()

    # Group by category
    by_category = {}
    for effect in all_effects:
        cat = getattr(effect, 'category', 'NO_CATEGORY')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(effect)

    print("Category breakdown:")
    for cat, effects in sorted(by_category.items()):
        print(f"  {cat}: {len(effects)} effects")
        for e in effects[:3]:  # Show first 3
            print(f"    - {e.id}: {e.name}")
        if len(effects) > 3:
            print(f"    ... and {len(effects) - 3} more")

    print()
    print("[OK] Test complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
