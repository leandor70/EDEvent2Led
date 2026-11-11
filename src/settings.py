"""
Configuration management for ED:Event2Led.
Handles persistent settings like journal directory path.
"""
import json
import os
from pathlib import Path
from typing import Optional


class Settings:
    """Manages application settings with persistent storage."""

    def __init__(self, config_file: str = "config/settings.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Load settings from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_settings(self):
        """Save settings to JSON file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def get_journal_directory(self) -> Optional[str]:
        """Get the configured journal directory path."""
        return self.settings.get('journal_directory')

    def set_journal_directory(self, path: str):
        """Set the journal directory path."""
        self.settings['journal_directory'] = path
        self._save_settings()

    @staticmethod
    def get_default_journal_directory() -> str:
        """
        Get the default Elite Dangerous journal directory based on current user.
        Returns: Default path like 'C:\\Users\\<username>\\Saved Games\\Frontier Developments\\Elite Dangerous'
        """
        username = os.getenv('USERNAME') or os.getenv('USER') or 'User'
        return str(Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous")

    def get_openrgb_host(self) -> str:
        """Get OpenRGB server host (default: localhost)."""
        return self.settings.get('openrgb_host', 'localhost')

    def get_openrgb_port(self) -> int:
        """Get OpenRGB server port (default: 6742)."""
        return self.settings.get('openrgb_port', 6742)

    def set_openrgb_connection(self, host: str, port: int):
        """Set OpenRGB connection parameters."""
        self.settings['openrgb_host'] = host
        self.settings['openrgb_port'] = port
        self._save_settings()

    def get_web_port(self) -> int:
        """Get the Eel/web server port (default: 8000).

        Must be read before eel.start() — changing it at runtime has no effect.
        Edit config/settings.json and restart the application to apply.
        """
        return int(self.settings.get('web_port', 8000))

    def set_web_port(self, port: int):
        """Persist the web server port. Takes effect on next application start."""
        self.settings['web_port'] = int(port)
        self._save_settings()

    def get_show_welcome_modal(self) -> bool:
        """Get whether to show the welcome modal on startup (default: True)."""
        return self.settings.get('show_welcome_modal', True)

    def set_show_welcome_modal(self, show: bool):
        """Set whether to show the welcome modal on startup."""
        self.settings['show_welcome_modal'] = bool(show)
        self._save_settings()

