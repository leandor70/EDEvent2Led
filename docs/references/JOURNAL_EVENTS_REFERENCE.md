# Elite Dangerous Journal Events - Quick Reference

## Panoramica

Repository completo di tutti gli eventi del Journal di Elite Dangerous, categorizzati e taggati per facilitare lo sviluppo di ED:Event2Led.

## File Principale

📊 **`Journal Manual/Elite_Dangerous_Journal_Events.xlsx`**
- 239 eventi documentati
- 11 categorie (Startup, Travel, Combat, Exploration, Trade, etc.)
- Colonne: Category, Event Name, Description, Importance, Tagwords
- Fonte: https://elite-journal.readthedocs.io/en/latest/

## Documentazione Completa

📖 **Leggi la documentazione completa**: `Journal Manual/README.md`

La documentazione include:
- Descrizione dettagliata di tutte le categorie
- Sistema completo di tagwords (20+ tag)
- Script Python per generazione e aggiornamento
- Esempi di utilizzo nel codice
- Processo di creazione passo-passo
- Suggerimenti per mapping eventi → effetti RGB

## Quick Start

### Aprire il File Excel
```bash
start "Journal Manual/Elite_Dangerous_Journal_Events.xlsx"
```

### Esempi di Ricerca

**Eventi di combattimento**:
- Filtra Tagwords: "combat"
- Risultato: 30 eventi (Bounty, UnderAttack, Died, etc.)

**Eventi importanti da loggare**:
- Filtra Importance: >= 4
- Ordina per Category

**Eventi di acquisto/vendita**:
- Filtra Tagwords: "buy" o "sell"
- Risultato: eventi commerciali

### Utilizzo nel Codice

```python
import pandas as pd

# Carica eventi
events = pd.read_excel('Journal Manual/Elite_Dangerous_Journal_Events.xlsx')

# Eventi importanti per RGB effects
rgb_events = events[events['Importance'] >= 4]

# Eventi di una categoria
combat = events[events['Category'] == 'Combat']

# Eventi con tag specifico
jumps = events[events['Tagwords'].str.contains('jump', na=False)]
```

## Script Disponibili

| Script | Descrizione |
|--------|-------------|
| `generate_journal_events_excel.py` | Genera il file Excel da zero |
| `suggest_tagwords.py` | Analizza eventi e suggerisce tagwords |
| `write_tagwords_to_excel.py` | Applica tagwords al file Excel |
| `analyze_excel.py` | Mostra statistiche e struttura |

## Tag Più Utilizzati

| Tag | Eventi | Descrizione |
|-----|--------|-------------|
| **combat** | 30 | Combattimento |
| **ship** | 50 | Nave/moduli |
| **station** | 43 | Servizi stazione |
| **scan** | 18 | Scansioni |
| **buy/sell** | 15/12 | Commercio |
| **jump** | 13 | Salti FSD |
| **docking** | 19 | Attracco |

## Categorie Eventi

```
Startup (14)         → Inizializzazione gioco
Travel (19)          → Navigazione e salti
Combat (16)          → Combattimento
Exploration (18)     → Esplorazione e scansioni
Trade (7)            → Commercio
Station Services (43)→ Servizi stazione
Powerplay (9)        → Meccaniche Powerplay
Squadrons (12)       → Gestione Squadron
Fleet Carriers (16)  → Gestione Carrier
Odyssey (32)         → Contenuti on-foot
Other Events (53)    → Eventi vari
```

## Per Saperne di Più

Consulta la documentazione completa in `Journal Manual/README.md` per:
- Processo di creazione dettagliato
- Logica completa del sistema di tagging
- Esempi di integrazione con ED:Event2Led
- Suggerimenti per mapping eventi → effetti RGB
- Come aggiornare e modificare il sistema

## Risorse

- 📚 Documentazione Elite: https://elite-journal.readthedocs.io/
- 📁 File Excel: `Journal Manual/Elite_Dangerous_Journal_Events.xlsx`
- 📖 README completo: `Journal Manual/README.md`
- 🎮 Elite Dangerous: https://www.elitedangerous.com/

---

*Ultimo aggiornamento: 2025-12-12*
