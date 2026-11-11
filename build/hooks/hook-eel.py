# PyInstaller hook for eel
# Ensures eel's internal bottle/gevent assets are included in the bundle.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('eel')
hiddenimports = collect_submodules('eel')
