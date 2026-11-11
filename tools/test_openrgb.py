"""
Test script for OpenRGB LED Controller.
Tests connection to OpenRGB and basic lighting controls.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from led_controller import LEDController


def main():
    """Main test function."""
    print("=" * 60)
    print("OpenRGB LED Controller - Connection Test")
    print("=" * 60)
    print()
    print("Make sure OpenRGB is running with SDK Server enabled!")
    print("(Settings -> Enable SDK Server)")
    print()

    # Create controller
    controller = LEDController()

    # Try to connect
    if not controller.connect():
        print("\nFailed to connect. Please check:")
        print("1. OpenRGB is running")
        print("2. SDK Server is enabled (Settings -> Enable SDK Server)")
        print("3. No firewall blocking port 6742")
        return

    print()
    print("-" * 60)

    # Show device details
    if controller.get_device_count() > 0:
        print("\nDevice Details:")
        print("-" * 60)
        for i in range(controller.get_device_count()):
            info = controller.get_device_info(i)
            if info:
                print(f"\nDevice {i}: {info['name']}")
                print(f"  Type: {info['type']}")
                print(f"  LEDs: {info['leds']}")
                print(f"  Zones: {info['zones']}")
                print(f"  Available Modes: {', '.join(info['modes'][:5])}...")

        # Ask if user wants to run tests
        print()
        print("-" * 60)
        choice = input("\nRun lighting tests? (y/n): ").lower().strip()

        if choice == 'y':
            print("\n" + "=" * 60)
            print("Running Lighting Tests")
            print("=" * 60)

            # Test 1: Static colors
            print("\n[Test 1] Static Colors")
            input("Press Enter to set all LEDs to RED...")
            controller.set_all_color(255, 0, 0)

            input("Press Enter to set all LEDs to GREEN...")
            controller.set_all_color(0, 255, 0)

            input("Press Enter to set all LEDs to BLUE...")
            controller.set_all_color(0, 0, 255)

            # Test 2: RGB cycle
            print("\n[Test 2] RGB Test Pattern (auto)")
            controller.test_pattern()

            # Test 3: Pulse effect
            print("\n[Test 3] Pulse Effect")
            input("Press Enter to start BLUE pulse...")
            controller.pulse_color(0, 100, 255, duration=2.0)

            # Test 4: Flash effect
            print("\n[Test 4] Flash Effect")
            input("Press Enter to start RED flash...")
            controller.flash_color(255, 0, 0, count=5, on_time=0.15, off_time=0.15)

            # Reset to off
            print("\n[Test 5] Reset to OFF")
            controller.set_all_color(0, 0, 0)
            print("All LEDs turned off")

            print("\n" + "=" * 60)
            print("All tests completed!")
            print("=" * 60)
    else:
        print("\nNo RGB devices detected by OpenRGB.")
        print("Make sure your RGB hardware is connected and detected in OpenRGB.")

    # Disconnect
    print()
    controller.disconnect()
    print("\nTest completed")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
