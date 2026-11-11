"""
Path resolution for ED:Event2Led.

Handles the difference between:
- Development: running from project root with `python src/main.py`
- Frozen: running as a PyInstaller .exe from the install directory

The base directory is where `web/`, `config/`, and `log/` live.
"""
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """
    Return the application base directory.

    Frozen (PyInstaller one-folder):
        base = directory containing the .exe
        web/, config/, log/ are siblings of the .exe

    Development:
        base = project root (parent of src/)
        web/, config/, log/ are siblings of src/
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # src/utils/paths.py -> src/utils/ -> src/ -> project root
    return Path(__file__).parent.parent.parent
