ED:Event2Led v1.0 - Guida rapida
====================================

PREREQUISITI
------------
1. Windows 10/11 x64
2. OpenRGB installato e in esecuzione
   - Apri OpenRGB > Settings > Enable SDK Server > Start
   - (default: porta 6742)
3. Elite Dangerous installato (per monitoraggio live)

AVVIO
------
Doppio click su EDEvent2Led.exe
L'app apre il browser su http://localhost:8000

NUOVA IN v1.0: AMBILIGHT
-------------------------
La pagina Ambilight permette di sincronizzare i LED con lo
schermo in tempo reale. Richiede che la topologia del device
sia configurata con le zone MonitorLeft/Right/Top/Bottom.
Il servizio screen capture usa Windows.Graphics.Capture
con fallback automatico a mss (compatibile con tutti i PC).

AGGIORNAMENTO DA UNA VERSIONE PRECEDENTE
----------------------------------------
1. Chiudi l'app. OpenRGB deve restare acceso.
2. Scarica la nuova versione in una cartella nuova.
3. Copia la cartella config\ della vecchia versione dentro
   quella nuova (sovrascrivendo i file).
4. Avvia EDEvent2Led.exe: i file di configurazione dei
   dispositivi vengono aggiornati automaticamente al primo
   avvio. Le copie dei file originali si chiamano
   *.v1.bak.json e restano in config\.
Se qualcosa non torna, ripristina un file rinominando la sua
copia (es. device_config.v1.bak.json -> device_config.json).

NOTE
----
- Se la porta 8000 e' occupata: modifica config\settings.json
  aggiungendo  "web_port": 8081  (o altra porta libera)
- I tuoi effetti e mappature vengono salvati in config\
- Per segnalare un bug: includi il contenuto della console

VERSIONE: v1.0
DATA BUILD: 2026-05-26
