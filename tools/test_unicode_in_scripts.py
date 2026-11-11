"""
Test script to verify Unicode-safe printing works with all emojis.

This simulates the output of various scripts to ensure Unicode characters
are handled correctly on Windows console (cp1252).
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import Unicode-safe utilities
from utils.unicode_safe import safe_print, setup_unicode_console, get_console_encoding

# Setup console
setup_unicode_console()


def test_device_inspector_emojis():
    """Test emojis from 01_device_inspector.py"""
    safe_print("=" * 80)
    safe_print("TEST: Device Inspector Emojis")
    safe_print("=" * 80)
    safe_print()

    safe_print("📋 Informazioni Generali:")
    safe_print("   Vendor: Example Corp")
    safe_print()

    safe_print("🎯 Zone Dettagliate:")
    safe_print("   Zone 0: Keyboard")
    safe_print("      Matrix Map: ✅ Yes")
    safe_print()

    safe_print("⚙️  Modalità Disponibili:")
    safe_print("      Speed: ✅ | Direction: ❌ | Brightness: ✅")
    safe_print("      Per-LED Colors: ✅ | Mode Colors: ❌ | Random: ✅")
    safe_print()

    safe_print("🎨 Stato Iniziale LED:")
    safe_print("   ⚠️  NOTA: Molti colori diversi rilevati (5)")
    safe_print("   ℹ️  Colore statico uniforme: RGB(255, 255, 0)")
    safe_print()

    safe_print("1️⃣  Modalità originale: Rainbow")
    safe_print("2️⃣  Switch a modalità Direct...")
    safe_print("   ✅ Modalità Direct attivata")
    safe_print()

    safe_print("3️⃣  Modifica LED a rosso...")
    safe_print("   ✅ Tutti i LED impostati a rosso")
    safe_print("   👁️  VERIFICA VISIVA: I LED sono rossi?")
    safe_print()

    safe_print("4️⃣  Ripristino modalità originale...")
    safe_print("   ✅ Modalità originale ripristinata")
    safe_print()

    safe_print("5️⃣  Ripristino colori originali...")
    safe_print("   ✅ Colori originali riapplicati")
    safe_print()

    safe_print("6️⃣  Verifica colori ripristinati...")
    safe_print("   ✅ Colori identici a quelli originali")
    safe_print()

    safe_print("💾 Informazioni salvate: results/device_0_info.json")
    safe_print()
    safe_print("✅ TEST 1 COMPLETATO")


def test_common_unicode_chars():
    """Test common Unicode characters used in various scripts"""
    safe_print()
    safe_print("=" * 80)
    safe_print("TEST: Common Unicode Characters")
    safe_print("=" * 80)
    safe_print()

    safe_print("Arrows:")
    safe_print("  → Right arrow")
    safe_print("  ← Left arrow")
    safe_print("  ↑ Up arrow")
    safe_print("  ↓ Down arrow")
    safe_print()

    safe_print("Check marks:")
    safe_print("  ✓ Check mark")
    safe_print("  ✗ X mark")
    safe_print("  ✅ Check emoji")
    safe_print("  ❌ Cross emoji")
    safe_print()

    safe_print("Status symbols:")
    safe_print("  ⚠️  Warning")
    safe_print("  ⚡ Lightning")
    safe_print("  ℹ️  Info")
    safe_print("  ⚙️  Settings")
    safe_print()

    safe_print("File/Folder symbols:")
    safe_print("  📁 Folder")
    safe_print("  📄 File")
    safe_print("  💾 Save")
    safe_print()

    safe_print("Other symbols:")
    safe_print("  🎯 Target")
    safe_print("  🎨 Palette")
    safe_print("  🔧 Wrench")
    safe_print("  🚀 Rocket")
    safe_print("  ⭐ Star")
    safe_print("  👁️  Eye")
    safe_print()

    safe_print("Numbered emojis:")
    safe_print("  1️⃣  One")
    safe_print("  2️⃣  Two")
    safe_print("  3️⃣  Three")
    safe_print("  4️⃣  Four")
    safe_print("  5️⃣  Five")
    safe_print("  6️⃣  Six")
    safe_print()

    safe_print("Punctuation:")
    safe_print("  • Bullet point")
    safe_print("  – En dash")
    safe_print("  — Em dash")
    safe_print("  … Ellipsis")


def test_mixed_content():
    """Test mixed ASCII and Unicode content"""
    safe_print()
    safe_print("=" * 80)
    safe_print("TEST: Mixed ASCII + Unicode Content")
    safe_print("=" * 80)
    safe_print()

    safe_print("Processing files...")
    safe_print("  [1/5] config.json → ✅ OK")
    safe_print("  [2/5] settings.json → ✅ OK")
    safe_print("  [3/5] mappings.json → ⚠️  Warning: deprecated format")
    safe_print("  [4/5] effects.json → ❌ Error: file not found")
    safe_print("  [5/5] devices.json → ✅ OK")
    safe_print()

    safe_print("Summary:")
    safe_print("  ✅ Success: 3 files")
    safe_print("  ⚠️  Warnings: 1 file")
    safe_print("  ❌ Errors: 1 file")


def main():
    """Run all Unicode tests"""
    safe_print("=" * 80)
    safe_print("UNICODE-SAFE PRINTING TEST SUITE")
    safe_print("=" * 80)
    safe_print()
    safe_print(f"Console encoding: {get_console_encoding()}")
    safe_print()

    # Run tests
    test_device_inspector_emojis()
    test_common_unicode_chars()
    test_mixed_content()

    # Final message
    safe_print()
    safe_print("=" * 80)
    safe_print("ALL TESTS COMPLETED SUCCESSFULLY! 🎉")
    safe_print("=" * 80)
    safe_print()
    safe_print("If you see this message without errors, Unicode-safe printing works!")
    safe_print()


if __name__ == "__main__":
    main()
