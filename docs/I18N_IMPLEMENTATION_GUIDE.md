# i18n Implementation Guide

## Overview

Il sistema di internazionalizzazione (i18n) è ora completamente implementato per ED:Event2Led. Questo documento spiega come utilizzarlo e completare l'aggiunta di traduzioni alle pagine HTML.

## Struttura File

```
config/i18n/
├── en.json    # English
├── it.json    # Italiano
├── de.json    # Deutsch (German)
├── fr.json    # Français (French)
└── es.json    # Español (Spanish)
```

Ogni file JSON segue la stessa struttura gerarchica:

```json
{
  "pages": {
    "configuration": {
      "title": "CONFIGURATION"
    }
  },
  "sections": {
    "openrgb": {
      "title": "OpenRGB Connection"
    }
  },
  "buttons": {
    "save": "SAVE"
  }
}
```

## Come Aggiungere Traduzioni all'HTML

### 1. Aggiungere l'attributo `data-i18n`

Per ogni elemento di testo che deve essere tradotto, aggiungi l'attributo `data-i18n` con la chiave della traduzione:

**Prima:**
```html
<h1>CONFIGURATION</h1>
```

**Dopo:**
```html
<h1 data-i18n="pages.configuration.title">CONFIGURATION</h1>
```

### 2. Traduzioni con Variabili

Per traduzioni che contengono variabili dinamiche (es. conteggi), usa `data-i18n-vars`:

**File JSON:**
```json
{
  "openrgb": {
    "device_count": "{{count}} device(s)"
  }
}
```

**HTML:**
```html
<span data-i18n="sections.openrgb.device_count"
      data-i18n-vars='{"count": "3"}'>
  3 device(s)
</span>
```

**NOTA**: `data-i18n-vars` deve contenere JSON valido (usa virgolette singole per l'attributo e doppie per il JSON).

### 3. Aggiornamento Dinamico da JavaScript

Per aggiornare traduzioni dinamicamente (es. dopo una chiamata API):

```javascript
// Metodo 1: Usando data-i18n
element.setAttribute('data-i18n-vars', JSON.stringify({count: deviceCount}));
window.i18n.apply();

// Metodo 2: Diretto
element.textContent = window.i18n.get('sections.openrgb.device_count', {count: deviceCount});
```

## Elementi da Tradurre in code.html

### ✅ Già Implementato

- Modulo i18n.js caricato
- Integrazione con settings.js
- Cambio lingua automatico

### 📝 Da Completare

Aggiungi `data-i18n` a questi elementi:

#### 1. Titolo Pagina (riga ~277)
```html
<!-- Prima -->
<h1 class="orbitron text-4xl font-bold...">ED:EVENT2LED</h1>

<!-- Dopo -->
<h1 class="orbitron text-4xl font-bold..." data-i18n="app.name">ED:EVENT2LED</h1>
```

#### 2. Sottotitolo (riga ~283)
```html
<!-- Prima -->
<p class="text-sm uppercase...">Translating Elite Dangerous Logs...</p>

<!-- Dopo -->
<p class="text-sm uppercase..." data-i18n="app.tagline">Translating...</p>
```

#### 3. Sezione System Settings (riga ~327)
```html
<!-- Prima -->
<div class="orbitron...">System Settings</div>

<!-- Dopo -->
<div class="orbitron..." data-i18n="sections.system_settings.title">System Settings</div>
```

#### 4. Language Selection (riga ~330)
```html
<!-- Prima -->
<div class="text-xs...">Language Selection</div>

<!-- Dopo -->
<div class="text-xs..." data-i18n="sections.system_settings.language_label">Language Selection</div>
```

#### 5. Theme Colors (riga ~336)
```html
<!-- Prima -->
<div class="text-xs...">Theme Colors</div>

<!-- Dopo -->
<div class="text-xs..." data-i18n="sections.system_settings.theme_label">Theme Colors</div>
```

#### 6. Theme Names (righe ~355, 365, 375, 385)
```html
<!-- Elite -->
<div class="text-[10px]..." data-i18n="sections.system_settings.theme_elite">Elite</div>

<!-- Violet -->
<div class="text-[10px]..." data-i18n="sections.system_settings.theme_violet">Violet</div>

<!-- Cyan -->
<div class="text-[10px]..." data-i18n="sections.system_settings.theme_cyan">Cyan</div>

<!-- Matrix -->
<div class="text-[10px]..." data-i18n="sections.system_settings.theme_matrix">Matrix</div>
```

#### 7. OpenRGB Connection (riga ~396)
```html
<div class="orbitron..." data-i18n="sections.openrgb.title">OpenRGB Connection</div>
```

#### 8. OpenRGB Labels (righe ~407, 412)
```html
<div class="text-[10px]..." data-i18n="sections.openrgb.host_label">Server IP:</div>
<div class="text-[10px]..." data-i18n="sections.openrgb.port_label">Server Port:</div>
```

#### 9. Test Connection Button (riga ~418)
```html
<span class="orbitron..." data-i18n="buttons.test_connection">TEST CONNECTION</span>
```

#### 10. Game Integration (riga ~421)
```html
<div class="orbitron..." data-i18n="sections.game_integration.title">Game Integration</div>
```

#### 11. Journal Path (riga ~435)
```html
<div class="text-[10px]..." data-i18n="sections.game_integration.journal_path_label">Journal Path:</div>
```

#### 12. Browse Directory (riga ~440)
```html
<div class="text-[10px]..." data-i18n="sections.game_integration.browse_label">Browse Directory:</div>
<span class="orbitron..." data-i18n="buttons.browse_directory">BROWSE DIRECTORY</span>
```

#### 13. Verify Path (riga ~444)
```html
<span class="orbitron..." data-i18n="buttons.verify_path">VERIFY PATH</span>
```

#### 14. Save Button (riga ~454)
```html
<span class="orbitron..." data-i18n="buttons.save">SAVE</span>
```

#### 15. Footer (righe ~463-466)
```html
<div class="text-[10px]..." data-i18n="app.version">v1.2.4</div>
<div class="text-[10px]..." data-i18n="app.build">Build 2024.10.27</div>
<p class="text-[10px]..." data-i18n="app.status">All systems nominal.</p>
```

## Status Messages Dinamici

Per messaggi di stato che cambiano dinamicamente, modifica il JavaScript in `settings.js`:

### OpenRGB Status (già implementato in testOpenRGB)
```javascript
// Prima
statusSpan.textContent = `Status: Connected (${result.device_count} device(s))`;

// Dopo
statusSpan.textContent = window.i18n.get('sections.openrgb.status_connected');
// Per il conteggio dispositivi, aggiungi:
// + ` (${window.i18n.get('sections.openrgb.device_count', {count: result.device_count})})`;
```

### Journal Status (già implementato in verifyJournalPath)
```javascript
// Prima
statusSpan.textContent = `Status: Verified (${result.file_count} file(s))`;

// Dopo
statusSpan.textContent = window.i18n.get('sections.game_integration.status_verified');
// + ` (${window.i18n.get('sections.game_integration.file_count', {count: result.file_count})})`;
```

## Testing

1. Avvia l'applicazione: `python src/main_eel.py`
2. Apri `http://localhost:8000/code.html`
3. Cambia lingua dal dropdown → Tutti i testi dovrebbero aggiornarsi istantaneamente
4. Verifica ogni lingua: EN, IT, DE, FR, ES

## Aggiungere Nuove Traduzioni

### 1. Aggiungi la chiave in TUTTI i file JSON

**en.json:**
```json
{
  "sections": {
    "new_section": {
      "title": "New Section Title"
    }
  }
}
```

**it.json:**
```json
{
  "sections": {
    "new_section": {
      "title": "Titolo Nuova Sezione"
    }
  }
}
```

*Ripeti per de.json, fr.json, es.json*

### 2. Usa la chiave nell'HTML

```html
<div data-i18n="sections.new_section.title">New Section Title</div>
```

## API JavaScript i18n

### Funzioni Disponibili

```javascript
// Inizializza con una lingua
await window.i18n.init('it');

// Cambia lingua a runtime
await window.i18n.change('de');

// Ottieni traduzione
const text = window.i18n.get('buttons.save');
const textWithVars = window.i18n.get('sections.openrgb.device_count', {count: 5});

// Applica tutte le traduzioni (dopo DOM update)
window.i18n.apply();

// Traduci un elemento specifico
window.i18n.translateElement(element, 'buttons.save');

// Get lingua corrente
const lang = window.i18n.getCurrentLanguage(); // 'en', 'it', etc.
```

## Checklist Completamento i18n

- [ ] Aggiungi `data-i18n` a tutti gli elementi di testo in `code.html`
- [ ] Aggiungi `data-i18n` a `effects-editor.html` (segui stesso pattern)
- [ ] Aggiungi `data-i18n` a `events.html`
- [ ] Modifica status messages in `settings.js` per usare i18n.get()
- [ ] Testa tutte le 5 lingue
- [ ] Verifica che traduzioni con variabili funzionino (device count, file count)
- [ ] Aggiungi traduzione dropdown lingue stesse (già in languages.* keys)

## Note

- Il testo di default nell'HTML è **English** - serve come fallback se i18n non si carica
- Le traduzioni sono **cache-free** - ogni cambio lingua ricarica il file JSON
- Il sistema supporta **interpolazione variabili** con sintassi `{{variable}}`
- Se una chiave non esiste, viene mostrata la chiave stessa (es. "buttons.missing_key")
- Console log `[i18n]` mostrano caricamento e applicazione traduzioni

## Troubleshooting

**Problema**: Traduzione non appare dopo cambio lingua
- Verifica che la chiave esista in TUTTI i file JSON
- Controlla console per errori `[i18n] Key not found`
- Verifica sintassi JSON (virgole, parentesi)

**Problema**: Variabili non interpolate (vedi `{{count}}` nel testo)
- Verifica sintassi `data-i18n-vars`: deve essere JSON valido
- Usa `JSON.stringify()` quando imposti da JavaScript

**Problema**: i18n non si carica
- Verifica che `i18n.js` sia caricato PRIMA di `settings.js`
- Controlla path `/config/i18n/*.json` sia accessibile
- Verifica console per errori HTTP 404
