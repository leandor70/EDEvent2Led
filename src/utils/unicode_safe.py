"""
Unicode-safe utilities for Windows console output.

This module provides utilities to handle Unicode characters safely on Windows,
preventing UnicodeEncodeError when printing to console with cp1252 encoding.
"""
import sys
import os
from typing import Any


def setup_unicode_console():
    """
    Configure Python to use UTF-8 encoding for stdout/stderr.

    This should be called at application startup before any print statements.
    Works on Python 3.7+ with proper Windows console support.

    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        # Try to enable UTF-8 mode (Python 3.7+)
        if sys.version_info >= (3, 7):
            # Reconfigure stdout/stderr to use UTF-8
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            return True
    except Exception as e:
        print(f"Warning: Could not setup UTF-8 console: {e}")
        return False

    return False


def safe_print(*args, **kwargs):
    """
    Print with automatic Unicode fallback for Windows.

    Replaces problematic Unicode characters with ASCII alternatives
    if encoding fails. This prevents UnicodeEncodeError on Windows
    consoles using cp1252 encoding.

    Args:
        *args: Arguments to print (same as built-in print)
        **kwargs: Keyword arguments (same as built-in print)

    Examples:
        safe_print("Processing file → done")  # Arrow replaced if needed
        safe_print("Status: ✅ Success")       # Emoji replaced if needed
    """
    try:
        # Try normal print first
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # If it fails, replace problematic characters and retry
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(_sanitize_unicode(arg))
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)


def _sanitize_unicode(text: str) -> str:
    """
    Replace common Unicode characters with ASCII alternatives.

    Args:
        text: String potentially containing Unicode characters

    Returns:
        str: String with Unicode characters replaced by ASCII equivalents
    """
    # Common Unicode replacements
    replacements = {
        '→': '->',      # Arrow right
        '←': '<-',      # Arrow left
        '↑': '^',       # Arrow up
        '↓': 'v',       # Arrow down
        '✓': '[OK]',    # Check mark
        '✗': '[X]',     # X mark
        '✅': '[OK]',    # Check mark emoji
        '❌': '[ERROR]', # Cross mark emoji
        '⚠': '[WARN]',  # Warning sign
        '⚡': '[!]',     # Lightning bolt
        '🔧': '[TOOL]',  # Wrench
        '📁': '[DIR]',   # Folder
        '📄': '[FILE]',  # Document
        '🚀': '[GO]',    # Rocket
        '⭐': '[*]',     # Star
        '•': '*',       # Bullet point
        '–': '-',       # En dash
        '—': '--',      # Em dash
        ''': "'",       # Left single quote
        ''': "'",       # Right single quote
        '"': '"',       # Left double quote
        '"': '"',       # Right double quote
        '…': '...',     # Ellipsis
    }

    result = text
    for unicode_char, ascii_char in replacements.items():
        result = result.replace(unicode_char, ascii_char)

    return result


def format_progress(current: int, total: int, prefix: str = "Progress") -> str:
    """
    Create a safe progress bar string without Unicode characters.

    Args:
        current: Current progress value
        total: Total value (100%)
        prefix: Prefix text for progress bar

    Returns:
        str: ASCII progress bar string

    Example:
        >>> format_progress(7, 10, "Loading")
        'Loading: [=======...] 70%'
    """
    if total == 0:
        return f"{prefix}: [??????????] 0%"

    percentage = int((current / total) * 100)
    filled = int((current / total) * 10)
    bar = '=' * filled + '.' * (10 - filled)

    return f"{prefix}: [{bar}] {percentage}%"


def get_console_encoding() -> str:
    """
    Get the current console encoding.

    Returns:
        str: Encoding name (e.g., 'cp1252', 'utf-8')
    """
    return sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else 'unknown'


def is_unicode_safe() -> bool:
    """
    Check if current console can handle Unicode characters.

    Returns:
        bool: True if UTF-8 or similar encoding, False if cp1252 or ASCII
    """
    encoding = get_console_encoding().lower()
    return 'utf' in encoding or encoding == 'utf-8'


# Test function for debugging
def test_unicode_support():
    """
    Test Unicode support in current console.
    Prints various Unicode characters to check rendering.
    """
    print("\n" + "=" * 60)
    print("Unicode Support Test")
    print("=" * 60)
    print(f"Console encoding: {get_console_encoding()}")
    print(f"Unicode safe: {is_unicode_safe()}")
    print()

    test_strings = [
        ("Arrows", "→ ← ↑ ↓"),
        ("Check marks", "✓ ✗ ✅ ❌"),
        ("Symbols", "⚠ ⚡ 🔧 📁 📄 🚀 ⭐"),
        ("Punctuation", "• – — ' ' " " …"),
    ]

    print("Testing characters:")
    for category, chars in test_strings:
        try:
            print(f"  {category}: {chars}")
        except UnicodeEncodeError:
            print(f"  {category}: [ERROR - Cannot display]")

    print("\nUsing safe_print:")
    for category, chars in test_strings:
        safe_print(f"  {category}: {chars}")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Run test if module is executed directly
    test_unicode_support()
