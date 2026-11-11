"""
Simple non-interactive test for Journal Reader.
Uses the GameLogs directory directly.
"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

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
    print("Elite Dangerous Journal Reader - Simple Test")
    print("=" * 60)

    # Use GameLogs directory
    journal_dir = str(Path(__file__).parent / "GameLogs")
    print(f"\nUsing test directory: {journal_dir}")

    # Create and start journal reader
    try:
        reader = JournalReader(journal_dir, event_callback)
        reader.start()

        print("\nReading journal file events...")
        print("-" * 60)

        # Wait a bit for events to be processed
        time.sleep(2)

        print("-" * 60)
        print("\nTest completed successfully!")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'reader' in locals():
            reader.stop()


if __name__ == "__main__":
    main()
