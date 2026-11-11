"""
Update HTML files to add data-i18n attributes to hardcoded strings.
"""

import re
from pathlib import Path

def update_events_html():
    """Update events.html category filters and DEASSIGN button."""
    file_path = Path(__file__).parent.parent / "web" / "events.html"
    print(f"[OK] Processing {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define category filter replacements
    replacements = [
        ('data-category="all">All<', 'data-category="all" data-i18n="categories.all">All<'),
        ('data-category="Startup">Startup<', 'data-category="Startup" data-i18n="categories.startup">Startup<'),
        ('data-category="Travel">Travel<', 'data-category="Travel" data-i18n="categories.travel">Travel<'),
        ('data-category="Combat">Combat<', 'data-category="Combat" data-i18n="categories.combat">Combat<'),
        ('data-category="Exploration">Exploration<', 'data-category="Exploration" data-i18n="categories.exploration">Exploration<'),
        ('data-category="Trade">Trade<', 'data-category="Trade" data-i18n="categories.trade">Trade<'),
        ('data-category="Station Services">Station<', 'data-category="Station Services" data-i18n="categories.station">Station<'),
        ('data-category="Powerplay">Powerplay<', 'data-category="Powerplay" data-i18n="categories.powerplay">Powerplay<'),
        ('data-category="Squadrons">Squadrons<', 'data-category="Squadrons" data-i18n="categories.squadrons">Squadrons<'),
        ('data-category="Fleet Carriers">Fleet<', 'data-category="Fleet Carriers" data-i18n="categories.fleet">Fleet<'),
        ('data-category="Odyssey">Odyssey<', 'data-category="Odyssey" data-i18n="categories.odyssey">Odyssey<'),
        ('data-category="Other Events">Other<', 'data-category="Other Events" data-i18n="categories.other">Other<'),
        ('>DEASSIGN<', ' data-i18n="buttons.deassign">DEASSIGN<'),
    ]

    changes = 0
    for old, new in replacements:
        if old in content and new not in content:
            content = content.replace(old, new)
            changes += 1
            print(f"  + Updated: {old[:30]}...")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] {file_path.name}: {changes} changes made\n")

def update_effects_editor_html():
    """Update effects-editor.html REVERT button."""
    file_path = Path(__file__).parent.parent / "web" / "effects-editor.html"
    print(f"[OK] Processing {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find REVERT button and add data-i18n
    old = '>REVERT<'
    new = ' data-i18n="buttons.revert">REVERT<'

    if old in content and new not in content:
        content = content.replace(old, new)
        print(f"  + Updated REVERT button")
        changes = 1
    else:
        print("  - REVERT button already has data-i18n or not found")
        changes = 0

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] {file_path.name}: {changes} changes made\n")

def update_index_html():
    """Update index.html badge categories."""
    file_path = Path(__file__).parent.parent / "web" / "index.html"
    print(f"[OK] Processing {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define badge replacements
    replacements = [
        ('>Base<', ' data-i18n="badges.base">Base<'),
        ('>Forms<', ' data-i18n="badges.forms">Forms<'),
        ('>Hardware<', ' data-i18n="badges.hardware">Hardware<'),
        ('>Devices<', ' data-i18n="badges.devices">Devices<'),
        ('>Editor<', ' data-i18n="badges.editor">Editor<'),
        ('>Complex<', ' data-i18n="badges.complex">Complex<'),
    ]

    changes = 0
    for old, new in replacements:
        # Only replace if it's in a badge context (has bg-*-500/20 nearby)
        if old in content:
            # Use regex to match badge pattern
            pattern = r'(bg-\w+-500/20[^>]*>)' + re.escape(old[1:])
            replacement = r'\1' + new[1:]
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes += 1
                print(f"  + Updated badge: {old}")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] {file_path.name}: {changes} changes made\n")

if __name__ == "__main__":
    print("=" * 70)
    print("  Update HTML Files with i18n Attributes")
    print("=" * 70)
    print()

    update_events_html()
    update_effects_editor_html()
    update_index_html()

    print("=" * 70)
    print("  ALL HTML FILES UPDATED")
    print("=" * 70)
    print()
    print("Next step: Reload the application to see translated strings")
