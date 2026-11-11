"""
Automatic OpenRGB test - runs lighting effects without user input.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from led_controller import LEDController


def main():
    """Main test function."""
    print("=" * 60)
    print("OpenRGB LED Controller - Automatic Test")
    print("=" * 60)
    print()

    # Create controller
    controller = LEDController()

    # Try to connect
    if not controller.connect():
        print("\nFailed to connect to OpenRGB")
        return

    print()
    print("-" * 60)
    print("Running automatic lighting tests...")
    print("-" * 60)

    # Test 1: RGB Cycle
    print("\n[Test 1] RGB Test Pattern")
    controller.test_pattern()
    print("  Complete!")

    # Test 2: Pulse Blue (like hyperspace)
    print("\n[Test 2] Blue Pulse (FSD Jump simulation)")
    controller.pulse_color(0, 100, 255, duration=3.0)
    print("  Complete!")

    # Test 3: Flash Red (alert)
    print("\n[Test 3] Red Flash (Alert simulation)")
    controller.flash_color(255, 0, 0, count=5, on_time=0.15, off_time=0.15)
    print("  Complete!")

    # Test 4: Green static (docked)
    print("\n[Test 4] Green Static (Docked simulation)")
    controller.set_all_color(0, 255, 0)
    import time
    time.sleep(2)
    controller.set_all_color(0, 0, 0)
    print("  Complete!")

    # Test 5: Pulse Cyan (scanning)
    print("\n[Test 5] Cyan Pulse (Scanning simulation)")
    controller.pulse_color(0, 255, 255, duration=2.0)
    print("  Complete!")

    print()
    print("=" * 60)
    print("All automatic tests completed!")
    print("=" * 60)

    # Disconnect
    controller.disconnect()
    print("\nTest completed successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
