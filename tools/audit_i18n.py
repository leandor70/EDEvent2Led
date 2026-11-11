"""
audit_i18n.py
Analyzes HTML files to find hardcoded text strings that should use i18n.

Usage:
    python tools/audit_i18n.py
"""

import re
import json
import sys
from pathlib import Path
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Patterns to identify hardcoded text
PATTERNS = {
    # Text content between tags (excluding script/style)
    'text_content': re.compile(r'>([A-Z][^<]{2,})<', re.MULTILINE),
    # Placeholder attributes
    'placeholder': re.compile(r'placeholder="([^"]+)"'),
    # Title attributes
    'title': re.compile(r'title="([^"]+)"'),
    # Alt attributes
    'alt': re.compile(r'alt="([^"]+)"'),
}

# Strings to ignore (technical terms, variable names, etc.)
IGNORE_PATTERNS = [
    r'^\d+$',  # Pure numbers
    r'^[A-Z_]+$',  # ALL_CAPS constants
    r'^[\d\s\-:\.]+$',  # Dates/times
    r'^\w+\(\)$',  # Function calls
    r'^#[0-9A-F]{6}$',  # Hex colors
    r'^(src|href|id|class|style|onclick)=',  # HTML attributes
    r'material-symbols',  # Icon font
    r'sci-fi-border',  # CSS class
]

def should_ignore(text: str) -> bool:
    """Check if text should be ignored."""
    text = text.strip()

    if len(text) < 3:
        return True

    for pattern in IGNORE_PATTERNS:
        if re.match(pattern, text):
            return True

    return False

def extract_hardcoded_strings(html_path: Path) -> dict:
    """Extract hardcoded strings from HTML file."""
    content = html_path.read_text(encoding='utf-8')

    # Remove script and style tags
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)

    results = defaultdict(list)

    for pattern_name, pattern in PATTERNS.items():
        matches = pattern.findall(content)

        for match in matches:
            text = match.strip()

            # Skip if already has data-i18n nearby
            if 'data-i18n' in content[max(0, content.find(text)-200):content.find(text)+200]:
                continue

            # Skip if should ignore
            if should_ignore(text):
                continue

            # Find line number
            line_num = content[:content.find(text)].count('\n') + 1

            results[pattern_name].append({
                'text': text,
                'line': line_num
            })

    return results

def load_translation_file(lang_path: Path) -> dict:
    """Load and flatten translation JSON."""
    with open(lang_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def flatten(d, prefix=''):
        items = []
        for k, v in d.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.extend(flatten(v, new_key))
            else:
                items.append((new_key, v))
        return items

    return dict(flatten(data))

def main():
    """Main audit function."""
    web_dir = Path('web')
    i18n_dir = web_dir / 'config' / 'i18n'

    # Load English translations
    en_translations = load_translation_file(i18n_dir / 'en.json')
    print(f"[OK] Loaded {len(en_translations)} translation keys from en.json\n")

    # Analyze HTML files
    html_files = [
        'index.html',
        'code.html',
        'effects-editor.html',
        'events.html',
        'devices.html',
        'log.html',
        'keyboard-designer.html',
        'status.html',
        'loading.html'
    ]

    total_issues = 0

    for html_file in html_files:
        html_path = web_dir / html_file

        if not html_path.exists():
            print(f"[SKIP] {html_file} (not found)")
            continue

        print(f"\n{'='*70}")
        print(f"  {html_file}")
        print(f"{'='*70}")

        results = extract_hardcoded_strings(html_path)

        if not any(results.values()):
            print("[OK] No hardcoded strings found")
            continue

        for pattern_name, matches in results.items():
            if not matches:
                continue

            print(f"\n[{pattern_name.upper()}] {len(matches)} hardcoded strings:")

            for match in matches[:10]:  # Limit to first 10
                text = match['text']
                line = match['line']

                # Check if similar key exists in translations
                similar = [k for k, v in en_translations.items() if v.lower() == text.lower()]

                if similar:
                    print(f"  Line {line:4d}: \"{text}\"")
                    print(f"            -> Use existing key: {similar[0]}")
                else:
                    print(f"  Line {line:4d}: \"{text}\"")
                    print(f"            -> NEW translation needed")

                total_issues += 1

            if len(matches) > 10:
                print(f"  ... and {len(matches) - 10} more")

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"Total hardcoded strings found: {total_issues}")
    print(f"Translation keys available: {len(en_translations)}")
    print(f"\n[ACTION REQUIRED]")
    print(f"1. Add data-i18n attributes to HTML elements")
    print(f"2. Add missing keys to all translation files (en, it, de, es, fr)")
    print(f"3. Test language switching in UI")

if __name__ == '__main__':
    main()
