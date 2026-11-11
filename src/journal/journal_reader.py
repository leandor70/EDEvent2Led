"""
Elite Dangerous Journal Reader.
Monitors journal files in real-time and emits parsed events.
"""
import json
import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.log_buffer import log_entry


class JournalEventHandler(FileSystemEventHandler):
    """Handles file system events for Elite Dangerous journal files."""

    def __init__(self, callback: Callable[[dict], None]):
        super().__init__()
        self.callback = callback
        self.current_journal: Optional[Path] = None
        self.file_position = 0

    def _is_journal_file(self, filepath: str) -> bool:
        """Check if file is an Elite Dangerous journal file."""
        filename = Path(filepath).name
        return filename.startswith("Journal.") and filename.endswith(".log")

    def _read_new_lines(self, filepath: Path):
        """Read new lines from journal file since last position."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Seek to last known position
                f.seek(self.file_position)

                # Read new lines
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            self.callback(event)
                        except json.JSONDecodeError as e:
                            print(f"Error parsing JSON: {e} - Line: {line}")
                            log_entry('error', 'ERROR', f"JSON parse error in journal: {e}")

                # Update position
                self.file_position = f.tell()

        except IOError as e:
            print(f"Error reading file {filepath}: {e}")

    def _find_latest_journal(self, directory: Path) -> Optional[Path]:
        """Find the most recent journal file in directory."""
        journal_files = list(directory.glob("Journal.*.log"))
        if not journal_files:
            return None

        # Sort by modification time, most recent first
        journal_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return journal_files[0]

    def on_created(self, event):
        """Handle file creation events (new journal part)."""
        if not event.is_directory and self._is_journal_file(event.src_path):
            filepath = Path(event.src_path)
            print(f"New journal file detected: {filepath.name}")
            log_entry('info', 'EVENT', f"Journal file rotation: now watching {filepath.name}")

            # Switch to new journal file
            self.current_journal = filepath
            self.file_position = 0
            self._read_new_lines(filepath)

    def on_modified(self, event):
        """Handle file modification events (new events appended)."""
        if not event.is_directory and self._is_journal_file(event.src_path):
            filepath = Path(event.src_path)

            # If this is our current journal, read new lines
            if self.current_journal is None or filepath == self.current_journal:
                if self.current_journal is None:
                    self.current_journal = filepath
                    self.file_position = 0

                self._read_new_lines(filepath)

    def initialize(self, directory: Path):
        """Initialize by finding and reading the latest journal file."""
        latest_journal = self._find_latest_journal(directory)
        if latest_journal:
            print(f"Found latest journal: {latest_journal.name}")
            log_entry('info', 'EVENT', f"Journal monitoring started: watching {latest_journal.name}")
            self.current_journal = latest_journal
            # Seek to end of file: only process events that occur AFTER monitoring starts.
            # Reading from position 0 would replay all historical events as lighting effects.
            try:
                with open(latest_journal, 'r', encoding='utf-8') as f:
                    f.seek(0, 2)  # seek to end
                    self.file_position = f.tell()
            except IOError:
                self.file_position = 0
        else:
            print("No journal files found in directory")
            log_entry('warning', 'WARNING', f"No journal files found in {directory}")


class JournalReader:
    """
    Monitors Elite Dangerous journal directory and emits events in real-time.

    Usage:
        reader = JournalReader(journal_directory, event_callback)
        reader.start()
        # ... do other work ...
        reader.stop()
    """

    def __init__(self, journal_directory: str, event_callback: Callable[[dict], None]):
        """
        Initialize journal reader.

        Args:
            journal_directory: Path to Elite Dangerous journal directory
            event_callback: Function called for each parsed event (receives dict)
        """
        self.journal_directory = Path(journal_directory)
        self.event_callback = event_callback
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[JournalEventHandler] = None

        if not self.journal_directory.exists():
            raise ValueError(f"Journal directory does not exist: {journal_directory}")

    def start(self):
        """Start monitoring the journal directory."""
        if self.observer is not None:
            print("Journal reader already running")
            return

        print(f"Starting journal reader on: {self.journal_directory}")

        # Create event handler and observer
        self.event_handler = JournalEventHandler(self.event_callback)
        self.observer = Observer()

        # Initialize by reading latest journal
        self.event_handler.initialize(self.journal_directory)

        # Start watching for changes
        self.observer.schedule(self.event_handler, str(self.journal_directory), recursive=False)
        self.observer.start()

        print("Journal reader started - monitoring for events...")

    def stop(self):
        """Stop monitoring the journal directory."""
        if self.observer is not None:
            print("Stopping journal reader...")
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
            self.observer = None
            self.event_handler = None
            print("Journal reader stopped")

    def is_running(self) -> bool:
        """Check if the journal reader is currently running."""
        return self.observer is not None and self.observer.is_alive()
