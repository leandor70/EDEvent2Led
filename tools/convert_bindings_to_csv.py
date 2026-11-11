"""
Converte Custom.4.2.xml (Elite Dangerous key bindings) in CSV.

Output columns:
    action              - Nome dell'azione (es. RollLeftButton)
    primary_device      - Device del binding primario (Keyboard / {NoDevice} / ...)
    primary_key         - Tasto primario senza prefisso Key_ (es. A, LeftShift)
    primary_modifiers   - Modifier del primario separati da + (es. LeftCtrl+LeftShift)
    secondary_device    - Device del binding secondario
    secondary_key       - Tasto secondario
    secondary_modifiers - Modifier del secondario

Usage:
    python tools/convert_bindings_to_csv.py
    python tools/convert_bindings_to_csv.py path/to/Custom.4.2.xml output.csv
"""
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def clean_key(key: str) -> str:
    """Rimuove il prefisso Key_ dai nomi tasto."""
    return key.removeprefix('Key_') if key else ''


def clean_device(device: str) -> str:
    """Semplifica {NoDevice} in stringa vuota."""
    return '' if device in ('{NoDevice}', '') else device


def parse_binding_node(node) -> tuple[str, str, str]:
    """
    Estrae device, key e modifiers da un nodo <Primary> o <Secondary>.
    Ritorna (device, key, modifiers_str).
    """
    if node is None:
        return '', '', ''

    device = clean_device(node.get('Device', ''))
    key    = clean_key(node.get('Key', ''))

    modifiers = [
        clean_key(m.get('Key', ''))
        for m in node.findall('Modifier')
        if m.get('Key')
    ]
    modifiers_str = '+'.join(modifiers)

    return device, key, modifiers_str


def convert(xml_path: Path, csv_path: Path) -> int:
    """
    Converte il file XML nel CSV.
    Ritorna il numero di azioni esportate.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    rows = []
    for action in root:
        tag = action.tag

        primary   = action.find('Primary')
        secondary = action.find('Secondary')

        # Salta elementi senza Primary/Secondary (impostazioni come MouseSensitivity)
        if primary is None and secondary is None:
            continue

        pdev, pkey, pmods = parse_binding_node(primary)
        sdev, skey, smods = parse_binding_node(secondary)

        # Salta azioni completamente non assegnate
        if not pkey and not skey:
            continue

        rows.append({
            'action':              tag,
            'primary_device':      pdev,
            'primary_key':         pkey,
            'primary_modifiers':   pmods,
            'secondary_device':    sdev,
            'secondary_key':       skey,
            'secondary_modifiers': smods,
        })

    fieldnames = [
        'action',
        'primary_device', 'primary_key', 'primary_modifiers',
        'secondary_device', 'secondary_key', 'secondary_modifiers',
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    base = Path(__file__).parent.parent

    xml_path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        base / 'support_files' / 'KeyBindings' / 'Custom.4.2.xml'

    csv_path = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        base / 'support_files' / 'KeyBindings' / 'Custom.4.2.csv'

    if not xml_path.exists():
        print(f'[ERROR] File non trovato: {xml_path}')
        sys.exit(1)

    count = convert(xml_path, csv_path)
    print(f'[OK] {count} azioni esportate -> {csv_path}')


if __name__ == '__main__':
    main()
