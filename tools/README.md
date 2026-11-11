# Development Tools & Utilities

Questa directory contiene utility di sviluppo, script di esempio e tool di analisi per EDLogReader.

## 📊 Utility di Analisi

### analyze_keyboard.py
Analizza il layout della tastiera e genera mappe LED.
- Analizza la struttura matriciale della tastiera
- Identifica posizioni LED
- Genera mapping per KeyboardMatrix2D

**Uso:**
```bash
python tools/analyze_keyboard.py
```

### analyze_excel.py
Analizza file Excel con dati di configurazione.
- Legge dati eventi da Excel
- Genera configurazioni JSON
- Valida strutture dati

**Uso:**
```bash
python tools/analyze_excel.py [file.xlsx]
```

### generate_journal_events_excel.py
Genera file Excel con riferimento eventi Elite Dangerous Journal.
- Estrae eventi dal manuale ufficiale
- Crea foglio Excel con categorie, eventi e descrizioni
- Utile per mappare eventi a effetti

**Uso:**
```bash
python tools/generate_journal_events_excel.py
```

### suggest_tagwords.py
Suggerisce tag/parole chiave per categorizzare eventi.
- Analizza descrizioni eventi
- Propone tag basati su NLP
- Aiuta a organizzare libreria effetti

**Uso:**
```bash
python tools/suggest_tagwords.py
```

## 🎨 Demo ed Esempi

### demo_2d_effects.py
Demo interattivo degli effetti 2D.
- Mostra effetti spaziali 2D (gradients, waves, pulses, ripples)
- Test su tastiere con layout matriciale
- Utile per vedere effetti in azione prima di integrarli

**Uso:**
```bash
python tools/demo_2d_effects.py
```

**Requisiti:**
- OpenRGB server in esecuzione
- Tastiera RGB connessa

### demo_unified_effects.py
Demo del sistema unificato effetti.
- Test UnifiedManager
- Demo effetti multi-step
- Verifica integrazione OpenRGB

**Uso:**
```bash
python tools/demo_unified_effects.py
```

### example_integration.py
Esempio completo di integrazione EDLogReader.
- Come usare VisualEffectLibrary
- Come creare effetti custom
- Come mappare eventi a effetti
- Pattern di integrazione consigliati

**Uso:**
```bash
python tools/example_integration.py
```

## 📝 Note

Questi script sono utility di sviluppo e non fanno parte dell'applicazione principale. Sono forniti per:
- Testing durante lo sviluppo
- Esempi di utilizzo API
- Generazione dati di configurazione
- Debug e analisi

## 🔧 Dipendenze

Gli script in questa directory potrebbero richiedere dipendenze aggiuntive oltre a quelle principali del progetto:
- `openpyxl` - Per generare_journal_events_excel.py e analyze_excel.py
- `nltk` - Per suggest_tagwords.py (NLP)

Installa con:
```bash
pip install openpyxl nltk
```

---

## 📝 Template e Best Practices

### script_template.py ⭐ NUOVO (2026-02-11)
Template di riferimento per creare script Unicode-safe.

**Cosa dimostra:**
- ✅ Import corretto di `unicode_safe` utilities
- ✅ Uso di `safe_print()` per output console
- ✅ Gestione caratteri Unicode (→, ✅, ⚠️, etc.)
- ✅ Formattazione progress bar ASCII-safe
- ✅ Error handling con Unicode
- ❌ Esempi di cosa NON fare (commentati)

**Uso come base per nuovi script:**
```bash
# Copia template
cp tools/script_template.py tools/my_new_script.py

# Modifica e testa
python tools/my_new_script.py
```

**Test del template:**
```bash
python tools/script_template.py
```

### 🎯 Best Practices Unicode

**Problema**: Windows console usa encoding cp1252 che non supporta caratteri Unicode estesi (→, ✅, ⚠️, etc.), causando `UnicodeEncodeError`.

**Soluzione implementata** (modulo `src/utils/unicode_safe.py`):

```python
# In ogni nuovo script, aggiungi:
from utils.unicode_safe import safe_print, setup_unicode_console

# Setup console all'avvio
setup_unicode_console()

# Usa safe_print invece di print
safe_print("Status → Ready")  # Auto-converte a "Status -> Ready" su Windows cp1252
safe_print("✅ Success!")     # Auto-converte a "[OK] Success!"
```

**Pattern consigliato per nuovi script**:
1. Import `safe_print` e `setup_unicode_console`
2. Chiama `setup_unicode_console()` all'inizio
3. Usa `safe_print()` per tutto l'output console
4. Testa su Windows prima di commit

**Documentazione completa**:
- Guide: `docs/guides/UNICODE_BEST_PRACTICES.md`
- Summary: `docs/UNICODE_SOLUTION_SUMMARY.md`
- Memory: `.claude/memory/MEMORY.md` → Unicode Handling
