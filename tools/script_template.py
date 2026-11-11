"""
Template script showing Unicode-safe best practices.

This template demonstrates the correct way to write Python scripts
that work reliably on Windows with cp1252 console encoding.

Usage:
    python script_template.py
"""
import sys
from pathlib import Path

# Add src to path if running from tools/ directory
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import Unicode-safe utilities
from utils.unicode_safe import (
    safe_print,
    setup_unicode_console,
    get_console_encoding,
    is_unicode_safe,
    format_progress
)

# Setup Unicode console (optional but recommended for scripts)
setup_unicode_console()


def main():
    """Main function demonstrating Unicode-safe practices."""

    # Print header (safe way)
    safe_print("=" * 60)
    safe_print("TEMPLATE SCRIPT - UNICODE SAFE")
    safe_print("=" * 60)
    safe_print()

    # Show console info
    safe_print(f"Console encoding: {get_console_encoding()}")
    safe_print(f"Unicode support: {'Yes ✅' if is_unicode_safe() else 'No (using fallback)'}")
    safe_print()

    # Example 1: Status messages with Unicode symbols
    safe_print("[STEP 1] Checking system status...")
    safe_print("  -> Connection: ✅ OK")
    safe_print("  -> Devices: ⚠️ Warning - 1 offline")
    safe_print("  -> Storage: ✓ Available")
    safe_print()

    # Example 2: Progress indication
    safe_print("[STEP 2] Processing files...")
    import time
    for i in range(11):
        progress = format_progress(i, 10, "Progress")
        print(progress, end='\r')
        time.sleep(0.1)
    print()  # New line after progress
    safe_print("  -> Processing complete!")
    safe_print()

    # Example 3: Arrows and navigation symbols
    safe_print("[STEP 3] Navigation flow:")
    safe_print("  Start → Initialize → Process → Complete")
    safe_print("  ↓")
    safe_print("  Results:")
    safe_print("    • Item 1: Success")
    safe_print("    • Item 2: Success")
    safe_print("    • Item 3: Pending...")
    safe_print()

    # Example 4: Error handling
    safe_print("[STEP 4] Simulating error handling...")
    try:
        # Simulate an error
        raise ValueError("Example error for demonstration")
    except ValueError as e:
        safe_print(f"  ❌ Error occurred: {e}")
        safe_print("  → Applying fallback strategy...")
        safe_print("  ✅ Recovery successful!")
    safe_print()

    # Example 5: Final status
    safe_print("=" * 60)
    safe_print("SCRIPT COMPLETED SUCCESSFULLY 🚀")
    safe_print("=" * 60)


def example_bad_practices():
    """
    Examples of what NOT to do (for reference only).

    These will cause UnicodeEncodeError on Windows cp1252 console.
    """
    # BAD: Direct print with Unicode
    # print("Status → Ready")  # ❌ Will crash on Windows

    # BAD: Unicode in string constants without safe_print
    # MESSAGE = "Processing → Done"
    # print(MESSAGE)  # ❌ Will crash

    # BAD: Emoji in print statements
    # print("✅ Test passed")  # ❌ Will crash

    # GOOD: Use safe_print instead
    safe_print("Status → Ready")  # ✅ Auto-converts to "Status -> Ready"
    safe_print("✅ Test passed")  # ✅ Auto-converts to "[OK] Test passed"


def example_good_practices():
    """
    Examples of correct Unicode handling.
    """
    # GOOD: Import and use safe_print
    from utils.unicode_safe import safe_print

    # GOOD: Unicode in output
    safe_print("Processing → Complete")

    # GOOD: Status messages
    safe_print("Status: ✅ Connected")

    # GOOD: Progress indication
    safe_print("Loading: [==========] 100%")

    # GOOD: Arrows and symbols
    safe_print("Step 1 → Step 2 → Done")

    # GOOD: Check console support and adapt
    from utils.unicode_safe import is_unicode_safe
    if is_unicode_safe():
        safe_print("Full Unicode available 🎉")
    else:
        safe_print("Using ASCII fallback mode")


if __name__ == "__main__":
    # Run main function
    main()

    # Optional: Show examples (uncomment to see)
    # print("\n" + "=" * 60)
    # print("GOOD PRACTICES EXAMPLES")
    # print("=" * 60)
    # example_good_practices()
