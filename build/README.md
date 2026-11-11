# Build System

## Prerequisiti

| Tool | Versione | Link |
|------|----------|------|
| Python | 3.11+ | https://python.org |
| PyInstaller | 6.x | `pip install pyinstaller` |
| Inno Setup | 6.x | https://jrsoftware.org/isinfo.php |
| UPX (opzionale) | any | https://upx.github.io/ |

## File nella cartella build/

| File | Scopo |
|------|-------|
| `EDEvent2Led.spec` | Configurazione PyInstaller |
| `installer.iss` | Script Inno Setup |
| `build.bat` | Script di build automatizzato |
| `hooks/hook-eel.py` | Hook PyInstaller per libreria eel |
| `icon.ico` | Icona app Windows (**da creare, vedi sotto**) |

## Icona (icon.ico)

PyInstaller e Inno Setup richiedono un file `icon.ico` in questa cartella.

Per generarlo dal favicon SVG del progetto:

```bash
# Con Inkscape (CLI):
inkscape web/favicon.svg --export-type=png --export-width=256 --export-filename=build/icon_256.png
# Poi converti in .ico con ImageMagick:
magick build/icon_256.png -define icon:auto-resize=256,128,64,48,32,16 build/icon.ico
```

Oppure usa un tool online come https://convertio.co/svg-ico/ con il file `web/favicon.svg`.

## Build completo

```bat
build\build.bat
```

Output:
- `dist\EDEvent2Led\` — cartella app (PyInstaller)
- `dist\EDEvent2Led-Setup-x.y.z.exe` — installer Windows (Inno Setup)

## Build solo PyInstaller (senza installer)

```bat
pyinstaller build\EDEvent2Led.spec --noconfirm
```

## Struttura dist\EDEvent2Led\ (output PyInstaller)

```
dist\EDEvent2Led\
  EDEvent2Led.exe       <- entry point
  web\                  <- frontend (HTML/JS/CSS/fonts)
  config\               <- configurazioni default
  _internal\            <- Python runtime + dipendenze
```

## Note

- **`config/`** è inclusa nel bundle come configurazione di default.
  L'utente la modificherà durante l'uso normale dell'app.
  L'uninstaller NON cancella `config/` (preserva le impostazioni utente).

- **Nessun `console=True`**: l'app non apre finestra console.
  Per debug, cambia `console=False` → `console=True` nel `.spec`.
