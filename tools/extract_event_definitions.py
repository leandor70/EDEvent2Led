"""
Extract event definitions from Elite_Dangerous_Journal_Events.xlsx
and create a JSON file for frontend use.
"""

import json
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError:
    print("[ERROR] openpyxl not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
    from openpyxl import load_workbook

def extract_event_definitions():
    """Extract event names and descriptions from Excel file."""
    excel_path = Path(__file__).parent.parent / "support_files" / "Journal Manual" / "Elite_Dangerous_Journal_Events.xlsx"

    if not excel_path.exists():
        print(f"[ERROR] Excel file not found: {excel_path}")
        return None

    print(f"[OK] Reading Excel file: {excel_path.name}")

    # Load workbook
    wb = load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active

    # Get column names (first row)
    headers = [cell.value for cell in ws[1]]
    print(f"[DEBUG] Columns found: {headers}")

    # Find Event and Description columns
    event_col_idx = None
    desc_col_idx = None

    for idx, header in enumerate(headers):
        if header and 'event' in str(header).lower():
            event_col_idx = idx
        if header and ('description' in str(header).lower() or 'desc' in str(header).lower()):
            desc_col_idx = idx

    if event_col_idx is None:
        print("[ERROR] Could not find Event column")
        return None

    print(f"[OK] Event column: index {event_col_idx}")
    if desc_col_idx is not None:
        print(f"[OK] Description column: index {desc_col_idx}")
    else:
        print("[WARNING] Description column not found")

    # Extract event definitions
    event_definitions = {}
    row_count = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        event_name = row[event_col_idx] if event_col_idx < len(row) else None
        description = row[desc_col_idx] if desc_col_idx is not None and desc_col_idx < len(row) else None

        if event_name and isinstance(event_name, str) and event_name.strip():
            event_definitions[event_name.strip()] = description.strip() if description else ""
            row_count += 1

    print(f"[OK] Extracted {row_count} event definitions")

    # Show first 5 events
    print("\n[DEBUG] First 5 events:")
    for i, (event, desc) in enumerate(list(event_definitions.items())[:5]):
        desc_preview = desc[:60] + "..." if len(desc) > 60 else desc
        print(f"  {i+1}. {event}: {desc_preview}")

    wb.close()
    return event_definitions

def save_to_json(event_definitions):
    """Save event definitions to JSON file."""
    if not event_definitions:
        print("[ERROR] No event definitions to save")
        return False

    output_path = Path(__file__).parent.parent / "web" / "config" / "event_definitions.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(event_definitions, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Saved to: {output_path}")
    print(f"[OK] Total events: {len(event_definitions)}")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("  Extract Event Definitions from Excel")
    print("=" * 70)
    print()

    event_definitions = extract_event_definitions()

    if event_definitions:
        save_to_json(event_definitions)
        print("\n" + "=" * 70)
        print("  EXTRACTION COMPLETE")
        print("=" * 70)
    else:
        print("\n[ERROR] Extraction failed")
