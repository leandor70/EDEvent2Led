#!/usr/bin/env python3
"""
Update HTML files to use local fonts instead of Google Fonts CDN
"""
import re
from pathlib import Path

# Pattern to match and remove
OLD_PATTERN = r'''<link rel="preconnect" href="https://fonts\.googleapis\.com"/>
<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin/>
<link rel="preload" as="style" href="https://fonts\.googleapis\.com/css2\?family=Orbitron.*?display=block"/>
<link href="css/tailwind\.min\.css" rel="stylesheet">
<link href="https://fonts\.googleapis\.com/css2\?family=Orbitron.*?display=block" rel="stylesheet"/>'''

# Replacement
NEW_PATTERN = '''<link href="css/tailwind.min.css" rel="stylesheet">
<link href="css/fonts.css" rel="stylesheet">'''

# Files to update
WEB_DIR = Path(__file__).parent.parent / 'web'
FILES = [
    'effects-editor.html',
    'events.html',
    'keyboard-designer.html',
    'status.html',
    'devices.html',
    'log.html',
    'code.html',
    'loading.html'
]

def main():
    updated = 0
    errors = 0

    for filename in FILES:
        filepath = WEB_DIR / filename

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if pattern exists
            if 'fonts.googleapis.com' not in content:
                print(f"  [OK] {filename} - Already updated")
                continue

            # Replace pattern
            new_content = re.sub(OLD_PATTERN, NEW_PATTERN, content, flags=re.DOTALL)

            if new_content == content:
                print(f"  [FAIL] {filename} - Pattern not found")
                errors += 1
                continue

            # Write back
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"  [OK] {filename} - Updated")
            updated += 1

        except Exception as e:
            print(f"  [ERROR] {filename} - {e}")
            errors += 1

    print(f"\n[SUMMARY] {updated} updated, {errors} errors, {len(FILES)} total")
    return 0 if errors == 0 else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
