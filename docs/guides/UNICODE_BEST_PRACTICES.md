# Unicode Best Practices for Windows Development

**Date**: 2026-02-11
**Status**: ✅ Active Guidelines

---

## 🎯 Problem Overview

Windows consoles use **cp1252** (Western European) encoding by default, which doesn't support extended Unicode characters like:

- Arrows: `→ ← ↑ ↓`
- Emojis: `✅ ❌ ⚠️ 🔧 🚀`
- Special symbols: `• ✓ ✗ ⭐`

When Python scripts print these characters, you get:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'
in position X: character maps to <undefined>
```

---

## ✅ Solution Implemented

We've created `src/utils/unicode_safe.py` with utilities to handle Unicode safely.

### 1. Application Startup Setup

**In `src/main.py`** (already configured):

```python
from utils.unicode_safe import setup_unicode_console, get_console_encoding

# Call this BEFORE any print statements
setup_unicode_console()
print(f"[DEBUG] Console encoding: {get_console_encoding()}")
```

This reconfigures `sys.stdout` and `sys.stderr` to use UTF-8 with automatic fallback.

### 2. Safe Printing in Scripts

**For all Python scripts that print to console**, use `safe_print()` instead of `print()`:

```python
from utils.unicode_safe import safe_print

# Old way (unsafe):
print("Processing file → done")        # ❌ UnicodeEncodeError on Windows

# New way (safe):
safe_print("Processing file → done")   # ✅ Auto-converts to "Processing file -> done"
```

### 3. Check Unicode Support

Before using Unicode characters, check if the console supports them:

```python
from utils.unicode_safe import is_unicode_safe

if is_unicode_safe():
    print("Status: ✅ Success")
else:
    print("Status: [OK] Success")  # ASCII fallback
```

### 4. Progress Bars Without Unicode

Use the built-in ASCII progress formatter:

```python
from utils.unicode_safe import format_progress

# Instead of: "Progress: ████████░░ 80%"
# Use:
progress_str = format_progress(8, 10, "Loading")
print(progress_str)  # "Loading: [========..] 80%"
```

---

## 📋 Character Replacement Table

The `safe_print()` function automatically replaces these characters:

| Unicode | ASCII | Description |
|---------|-------|-------------|
| `→` | `->` | Arrow right |
| `←` | `<-` | Arrow left |
| `✓` | `[OK]` | Check mark |
| `✗` | `[X]` | X mark |
| `✅` | `[OK]` | Check mark emoji |
| `❌` | `[ERROR]` | Cross mark emoji |
| `⚠` | `[WARN]` | Warning sign |
| `⚡` | `[!]` | Lightning bolt |
| `🔧` | `[TOOL]` | Wrench |
| `📁` | `[DIR]` | Folder |
| `📄` | `[FILE]` | Document |
| `🚀` | `[GO]` | Rocket |
| `⭐` | `[*]` | Star |
| `•` | `*` | Bullet point |
| `–` | `-` | En dash |
| `—` | `--` | Em dash |
| `…` | `...` | Ellipsis |

---

## 🛠️ Guidelines for New Code

### ✅ DO

1. **Use `safe_print()` for console output**:
   ```python
   from utils.unicode_safe import safe_print
   safe_print(f"Status: ✅ {status}")
   ```

2. **Use ASCII alternatives in docstrings/comments**:
   ```python
   # Good: "Navigate -> next page"
   # Bad:  "Navigate → next page"
   ```

3. **Use ASCII in variable names and code**:
   ```python
   # Good: arrow_right = "->"
   # Bad:  arrow_right = "→"
   ```

4. **Test scripts on Windows before committing**:
   ```bash
   python your_script.py
   # Should run without UnicodeEncodeError
   ```

### ❌ DON'T

1. **Don't use Unicode in `print()` statements**:
   ```python
   # Bad:
   print("Processing → done")  # Will crash on Windows cp1252
   ```

2. **Don't assume UTF-8 console**:
   ```python
   # Bad:
   print("✅ Test passed")  # Not portable

   # Good:
   safe_print("✅ Test passed")  # Auto-converts to "[OK] Test passed"
   ```

3. **Don't use Unicode box-drawing characters**:
   ```python
   # Bad: "┌─────┐"
   # Good: "+-----+"
   ```

4. **Don't use emoji in critical error messages**:
   ```python
   # Bad:
   raise ValueError("❌ Invalid input")

   # Good:
   raise ValueError("Invalid input")  # Plain ASCII
   ```

---

## 🧪 Testing Unicode Support

Run the built-in test utility:

```bash
cd src
python -m utils.unicode_safe
```

Output shows:

```
============================================================
Unicode Support Test
============================================================
Console encoding: utf-8
Unicode safe: True

Testing characters:
  Arrows: → ← ↑ ↓
  Check marks: ✓ ✗ ✅ ❌
  Symbols: ⚠ ⚡ 🔧 📁 📄 🚀 ⭐
  Punctuation: • – — ' ' " " …

Using safe_print:
  Arrows: -> <- ^ v
  Check marks: [OK] [X] [OK] [ERROR]
  Symbols: [WARN] [!] [TOOL] [DIR] [FILE] [GO] [*]
  Punctuation: * - -- ' ' " " ...
============================================================
```

---

## 🔧 Troubleshooting

### Issue: Still getting UnicodeEncodeError

**Solution 1**: Ensure `setup_unicode_console()` is called at startup:

```python
# In main.py or script entry point:
from utils.unicode_safe import setup_unicode_console
setup_unicode_console()
```

**Solution 2**: Use `safe_print()` instead of `print()`:

```python
from utils.unicode_safe import safe_print
safe_print("Your message with → Unicode")
```

**Solution 3**: Check if you're using Unicode in string constants:

```python
# Bad:
MESSAGE = "Status → Ready"  # Unicode in constant

# Good:
MESSAGE = "Status -> Ready"  # ASCII in constant
```

### Issue: Wrong characters displayed

**Cause**: Console encoding is cp1252 but script uses UTF-8 characters.

**Solution**: Use `safe_print()` which auto-converts characters to ASCII equivalents.

### Issue: Need to keep Unicode for specific output

**Solution**: Use conditional printing:

```python
from utils.unicode_safe import is_unicode_safe

if is_unicode_safe():
    print("Progress: █████░░░░░ 50%")  # Unicode bars
else:
    print("Progress: [=====.....] 50%")  # ASCII bars
```

---

## 📚 Additional Resources

- **Python Unicode HOWTO**: https://docs.python.org/3/howto/unicode.html
- **Windows Console Encoding**: https://docs.python.org/3/using/windows.html#utf-8-mode
- **PEP 540 (UTF-8 Mode)**: https://peps.python.org/pep-0540/

---

## 🎯 Quick Reference Card

**Import at top of file**:
```python
from utils.unicode_safe import safe_print, setup_unicode_console
```

**At application startup**:
```python
setup_unicode_console()
```

**For console output**:
```python
safe_print("Message with → Unicode")  # Auto-converts
```

**For logging/files**:
```python
# UTF-8 works fine in files:
with open('log.txt', 'w', encoding='utf-8') as f:
    f.write("Unicode → works here!\n")
```

---

**Last Updated**: 2026-02-11
**Module**: `src/utils/unicode_safe.py`
**Applies to**: All Python scripts in EDLogReader project
