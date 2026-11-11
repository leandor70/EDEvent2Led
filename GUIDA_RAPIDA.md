# ED:Event2Led — Guida Rapida

> Versione per i tester · Aggiornata a marzo 2026

---

## Cos'è ED:Event2Led

ED:Event2Led è un'applicazione che **sincronizza le luci RGB del tuo PC con gli eventi di Elite Dangerous** in tempo reale. Quando salti in iperspazio, vieni attaccato, inizi a fare scooping del carburante o attivi il supercruise, le luci della tua tastiera, mouse e altri dispositivi RGB cambiano automaticamente per riflettere quello che succede nel gioco.

L'applicazione funziona come server locale: apre una pagina web nel tuo browser da cui puoi configurare tutto senza dover toccare alcun file di configurazione a mano.

---

## Prerequisiti

Prima di avviare ED:Event2Led assicurati che:

1. **OpenRGB** sia installato e in esecuzione (con privilegi di **amministratore**)
   - Scaricalo da [openrgb.org](https://openrgb.org)
   - Una volta aperto: `Settings → SDK Server → Start Server` (porta default: 6742)

2. **Elite Dangerous** sia installato (non è necessario che sia in esecuzione per configurare gli effetti)

3. Il PC sia connesso a internet **solo alla prima installazione** (per scaricare le dipendenze)

---

## Prima installazione

1. Estrai la cartella `ED-Event2Led` dove preferisci
2. Fai doppio click su **`install.bat`**
   - Scarica e configura automaticamente Python e le dipendenze (~2 minuti)
   - Richiede connessione internet solo questa volta
3. Al termine, clicca su qualsiasi tasto per chiudere

---

## Avvio normale

Doppio click su **`start.bat`**

Il browser si apre automaticamente su `http://localhost:8000`
Lascia la finestra della console aperta finché usi l'app.

> **Nota:** Se la porta 8000 è già usata da un altro programma, apri `config/settings.json` con un editor di testo e aggiungi `"web_port": 8081` (o un altro numero a tua scelta). Poi riavvia.

---

## Panoramica dell'interfaccia

La barra di navigazione laterale sinistra ti porta alle diverse sezioni:

| Sezione | A cosa serve |
|---------|-------------|
| **Home** | Stato di connessione (OpenRGB, monitoraggio journal), avvio/stop monitoring |
| **Effects Editor** | Creare e modificare gli effetti luminosi |
| **Events** | Collegare gli eventi di gioco agli effetti |
| **Game Status** | Monitorare i flag di stato della nave e assegnare effetti ai cambi di stato |
| **Keyboard Designer** | Personalizzare i colori dei singoli tasti |
| **Devices** | Gestire i dispositivi RGB (abilitare/disabilitare, testare) |
| **Configuration** | Impostazioni: lingua, tema, connessione OpenRGB |
| **Log** | Visualizzare l'attività in tempo reale |

---

## Come funziona (concetto base)

```
Elite Dangerous  →  Evento (es. FSDJump)
                         ↓
              ED:Event2Led lo rileva
                         ↓
              Cerca l'effetto associato
                         ↓
              Invia i colori ad OpenRGB
                         ↓
               Luci RGB si aggiornano
```

Tutto ruota attorno a tre elementi:
- **Effetti**: sequenze di animazioni luminose (cosa mostrare)
- **Mappature**: quale effetto mostrare per quale evento
- **Dispositivi**: su quali luci mostrarlo

---

## Sezione: Effects Editor

Qui crei e modifichi gli effetti luminosi. Ogni effetto è una **sequenza di step**, dove ogni step è un effetto primitivo (onda, breath, fuoco, matrix rain, ecc.).

### Creare un nuovo effetto

1. Clicca **+ New Effect** in basso nella colonna sinistra
2. Dai un nome all'effetto in alto
3. Clicca **+ Add Step** per aggiungere il primo step
4. Per ogni step:
   - Scegli il **tipo di effetto** (Wave, Breath, Bloom, Fire...)
   - Imposta i **colori** cliccando sui quadratini colorati
   - Regola la **durata** con lo slider o i preset (250ms · 500ms · 1s · 2s)
   - Configura i parametri specifici (direzione, velocità, loop...)
5. Clicca **Save Effect**

### Categoria effetto

Ogni effetto ha una categoria che determina dove appare nelle liste di selezione:
- **Event** → per gli eventi journal (FSDJump, attacchi, docking...)
- **Status** → per i cambi di stato (surriscaldamento, scudi, SRV...)
- **General** → appare in entrambi i contesti

### Effetti predefiniti

L'applicazione include 12 effetti già pronti con i nomi degli eventi di gioco corrispondenti (FSD Hyperspace Jump, Under Attack, Docked Safe, ecc.). Puoi usarli così come sono, modificarli o clonarli come punto di partenza.

### Dissolvenza (Fade-In)

In fondo a ogni step trovi i pulsanti **Off · Fast · Med · Slow**: aggiungono una transizione morbida all'inizio dello step, utile per evitare tagli netti tra un effetto e l'altro.

---

## Sezione: Events

Qui colleghi gli eventi di gioco agli effetti. La pagina mostra tutti gli eventi di Elite Dangerous, sia quelli già mappati che quelli senza effetto.

### Assegnare un effetto a un evento

1. Trova l'evento nella tabella (puoi filtrare per categoria o cercare per nome)
2. Clicca sulla riga dell'evento
3. Si apre la modale di selezione: scegli l'effetto dalla griglia
4. Regola la **priorità** (determina quale effetto prevale se due si sovrappongono)
5. Clicca **Save**

### Priorità

Gli effetti hanno una priorità da 1 a 10. Se due eventi si attivano contemporaneamente, quello con priorità più alta prevale. Gli eventi critici (attacco, interdizione) hanno priorità alta (8-10); quelli informativi hanno priorità bassa (1-3).

### Attacchi direzionali

L'evento **UnderAttack** supporta quattro varianti direzionali:
- `UnderAttack_Right` — colpito da destra (dritta)
- `UnderAttack_Left` — colpito da sinistra (babordo)
- `UnderAttack_Front` — colpito davanti
- `UnderAttack_Rear` — colpito da dietro

Puoi assegnare effetti diversi per ogni direzione: l'effetto **Directional Flash** è progettato appositamente per questo, illuminando il quarto di tastiera corrispondente al lato colpito.

---

## Sezione: Game Status

Questa pagina mostra in tempo reale i **flag di stato** letti da `Status.json` di Elite Dangerous. Ogni card rappresenta un flag (es. Overheating, HardpointsDeployed, InSRV) e si illumina con un bordo pulsante quando il flag è attivo.

### Filtri

- **All · Ship · Odyssey**: mostra solo i flag della nave o solo quelli Odyssey
- **Slider priorità**: nasconde i flag di bassa importanza (informativi come HasLatLong)

### Assegnare effetti ai cambi di stato

A differenza degli eventi (che scattano una volta), i flag di stato hanno un momento di **attivazione** e uno di **disattivazione**. Puoi assegnare un effetto diverso per ciascuno:

1. Clicca su una card (es. "Overheating")
2. Si apre la modale con due slot:
   - 🟢 **On Activation** — effetto che parte quando il flag si attiva
   - ⚪ **On Deactivation** — effetto che parte quando il flag si disattiva
3. Seleziona l'effetto in ciascuno slot (o lascia vuoto per non fare nulla)
4. Clicca **Save**

Il **puntino verde** nell'angolo di ogni card indica che ha almeno un effetto assegnato.

---

## Sezione: Keyboard Designer

Qui puoi colorare i singoli tasti della tastiera e salvare configurazioni (preset).

### Colorare i tasti

1. Carica la matrice LED del tuo dispositivo con **Load Device**
2. Clicca su un tasto sulla tastiera virtuale
3. Scegli il colore nel pannello di destra
4. Ripeti per tutti i tasti che vuoi colorare

### Preset (P1 · P2 · P3)

Puoi salvare tre configurazioni separate. Il preset attivo viene usato dall'effetto speciale **Keyboard Default** (che ripristina la tastiera alla configurazione salvata dopo qualsiasi effetto di gioco).

### Live Preview

Attiva il **Live Preview** per vedere le modifiche applicate alla tastiera fisica in tempo reale mentre lavori. Quando lo attivi, la tastiera fisica si sincronizza immediatamente con la tastiera virtuale.

### Keybinding Profile

Clicca **Load ED Keybindings** per caricare automaticamente i binding di Elite Dangerous: i tasti assegnati alle funzioni di gioco si colorano automaticamente per categoria (blu = volo, rosso = combattimento, giallo = sistemi nave, ecc.).

---

## Sezione: Devices

Lista di tutti i dispositivi RGB rilevati da OpenRGB.

- **Abilita/Disabilita**: un dispositivo disabilitato viene ignorato da tutti gli effetti
- **On Disable**: cosa fare quando si disabilita (mantieni colori · spegni · ripristina modalità hardware)
- **Test**: invia un flash rapido per identificare fisicamente il dispositivo

---

## Sezione: Configuration

| Impostazione | Descrizione |
|-------------|-------------|
| **OpenRGB Host/Port** | Indirizzo del server OpenRGB (default: localhost:6742) |
| **Journal Directory** | Cartella dei log di Elite Dangerous (rilevata automaticamente) |
| **Language** | Lingua dell'interfaccia (IT, EN, DE, ES, FR) |
| **Theme** | Tema colore: Elite (arancione), Event2Led (viola), Dark (ciano), Light (verde) |

---

## Avviare il monitoraggio

Dalla **Home**, clicca **Start Monitoring** per attivare il monitoraggio del journal di Elite Dangerous. Da quel momento l'applicazione rileva gli eventi in tempo reale e attiva gli effetti corrispondenti.

Il pulsante diventa **Stop Monitoring** per fermare. Il monitoraggio si ferma automaticamente alla chiusura dell'app.

> **Suggerimento:** avvia il monitoraggio prima di lanciare Elite Dangerous, così l'app è pronta a reagire dal primo evento.

---

## Risoluzione problemi

| Problema | Soluzione |
|---------|-----------|
| "OpenRGB not connected" | Apri OpenRGB, vai in Settings → Enable SDK Server → Start |
| Luci non reagiscono | Verifica che OpenRGB sia aperto **con SDK Server attivo** |
| Il browser non si apre | Vai manualmente su `http://localhost:8000` |
| La porta 8000 è occupata | Aggiungi `"web_port": 8081` in `config/settings.json` |
| Effetti non si attivano | Controlla che il monitoring sia attivo (Home → Start Monitoring) |
| Tastiera fisica diversa dalla virtuale | Controlla che il dispositivo sia abilitato nella sezione Devices |

---

## Struttura cartella

```
ED-Event2Led/
├── start.bat           ← avvio quotidiano
├── install.bat         ← solo la prima volta
├── config/             ← le tue configurazioni (effetti, mapping, preset)
├── src/                ← codice sorgente (non modificare)
├── web/                ← interfaccia web (non modificare)
└── python/             ← Python embedded (non modificare)
```

I tuoi dati sono tutti in `config/`: puoi farne backup o condividerli con altri utenti.

---

*Per segnalare bug o suggerire miglioramenti, includi il contenuto della console (finestra `start.bat`) e descrivi cosa stavi facendo quando si è verificato il problema.*
