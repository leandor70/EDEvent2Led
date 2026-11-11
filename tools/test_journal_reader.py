"""
Test script for Journal Reader.
Tests real-time monitoring of Elite Dangerous journal files.
"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from settings import Settings
from journal_reader import JournalReader


def event_callback(event: dict):
    """Callback function that prints received events."""
    timestamp = event.get('timestamp', 'N/A')
    event_type = event.get('event', 'Unknown')

    print(f"[{timestamp}] {event_type}")

    # Print additional details for interesting events
    if event_type == "FSDJump":
        system = event.get('StarSystem', 'Unknown')
        print(f"  -> Jumped to: {system}")
    elif event_type == "Docked":
        station = event.get('StationName', 'Unknown')
        print(f"  -> Docked at: {station}")
    elif event_type == "Undocked":
        station = event.get('StationName', 'Unknown')
        print(f"  -> Undocked from: {station}")
    elif event_type == "LoadGame":
        commander = event.get('Commander', 'Unknown')
        ship = event.get('Ship', 'Unknown')
        print(f"  -> Commander: {commander}, Ship: {ship}")
    elif event_type == "Location":
        system = event.get('StarSystem', 'Unknown')
        print(f"  -> Current system: {system}")


def main():
    """Main test function."""
    print("=" * 60)
    print("Elite Dangerous Journal Reader - Test")
    print("=" * 60)

    # Load settings
    settings = Settings()

    # Get journal directory
    configured_dir = settings.get_journal_directory()

    if configured_dir:
        print(f"\nConfigured journal directory: {configured_dir}")
        use_configured = input("Use this directory? (y/n): ").lower().strip()
        if use_configured != 'y':
            configured_dir = None

    if not configured_dir:
        # Propose default directory
        default_dir = Settings.get_default_journal_directory()
        print(f"\nProposed directory: {default_dir}")

        # Check if it exists
        if Path(default_dir).exists():
            print("[OK] Directory exists")
        else:
            print("[!] Directory does not exist")

        choice = input("\n1. Use proposed directory\n2. Use test directory (GameLogs)\n3. Enter custom path\nChoice (1-3): ").strip()

        if choice == '1':
            journal_dir = default_dir
        elif choice == '2':
            journal_dir = str(Path(__file__).parent / "GameLogs")
        else:
            journal_dir = input("Enter journal directory path: ").strip()

        # Save to settings
        settings.set_journal_directory(journal_dir)
    else:
        journal_dir = configured_dir

    print(f"\nUsing journal directory: {journal_dir}")

    # Verify directory exists
    if not Path(journal_dir).exists():
        print(f"ERROR: Directory does not exist: {journal_dir}")
        return

    # Create and start journal reader
    try:
        reader = JournalReader(journal_dir, event_callback)
        reader.start()

        print("\nMonitoring journal files... (Press Ctrl+C to stop)")
        print("-" * 60)

        # Keep running until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping...")
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        if 'reader' in locals():
            reader.stop()

    print("\nTest completed")


if __name__ == "__main__":
    main()
