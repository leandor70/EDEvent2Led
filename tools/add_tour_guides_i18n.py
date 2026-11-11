"""
add_tour_guides_i18n.py
Adds tour_ui and tour_guides sections to IT, DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

TOUR_UI = {
    "it": {
        "step": "Passo",
        "next": "Avanti",
        "previous": "Indietro",
        "finish": "Fine",
        "skip_tour": "Salta Guida",
        "skip_confirm": "Saltare questa guida? Puoi riattivarla in qualsiasi momento dal pulsante aiuto.",
        "dont_show_again": "Non mostrare piu questa guida"
    },
    "de": {
        "step": "Schritt",
        "next": "Weiter",
        "previous": "Zurück",
        "finish": "Fertig",
        "skip_tour": "Tour Überspringen",
        "skip_confirm": "Diese Tour überspringen? Sie können sie jederzeit über die Hilfe-Schaltfläche neu starten.",
        "dont_show_again": "Diese Anleitung nicht mehr anzeigen"
    },
    "es": {
        "step": "Paso",
        "next": "Siguiente",
        "previous": "Anterior",
        "finish": "Terminar",
        "skip_tour": "Saltar Tour",
        "skip_confirm": "¿Saltar este tour? Puedes reiniciarlo en cualquier momento desde el botón de ayuda.",
        "dont_show_again": "No mostrar más esta guía"
    },
    "fr": {
        "step": "Étape",
        "next": "Suivant",
        "previous": "Précédent",
        "finish": "Terminer",
        "skip_tour": "Sauter le Tour",
        "skip_confirm": "Sauter ce tour ? Vous pouvez le redémarrer à tout moment depuis le bouton d'aide.",
        "dont_show_again": "Ne plus afficher ce guide"
    }
}

# Italian tour guides (full translation)
TOUR_GUIDES_IT = {
    "configuration": {
        "steps": [
            {
                "target": "#openrgb-host",
                "position": "bottom",
                "title": "Connessione OpenRGB",
                "description": "Inserisci l'indirizzo del server OpenRGB. Se OpenRGB è in esecuzione sulla stessa macchina, lascia <strong>localhost</strong>. Per il controllo remoto, inserisci l'IP del server (es. <code>192.168.1.100</code>)."
            },
            {
                "target": "#openrgb-port",
                "position": "bottom",
                "title": "Porta OpenRGB",
                "description": "La porta SDK predefinita di OpenRGB è <strong>6742</strong>. Modificala solo se hai configurato OpenRGB per usare una porta diversa. Clicca <strong>Test Connessione</strong> per verificare."
            },
            {
                "target": "#btn-test-connection",
                "position": "bottom",
                "title": "Test Connessione",
                "description": "Clicca questo pulsante per verificare se ED:Event2Led può connettersi a OpenRGB. Se la connessione fallisce, assicurati che OpenRGB sia in esecuzione e che il server SDK sia abilitato nelle impostazioni di OpenRGB."
            },
            {
                "target": "#journal-directory",
                "position": "top",
                "title": "Directory Journal",
                "description": "Questa è la cartella dove Elite Dangerous salva i file journal. Il percorso predefinito è solitamente corretto. Se i tuoi file journal sono altrove (es. libreria Steam personalizzata), clicca <strong>Sfoglia</strong> per selezionare la cartella corretta."
            },
            {
                "target": "#btn-save-settings",
                "position": "top",
                "title": "Salva Impostazioni",
                "description": "Una volta configurati OpenRGB e la directory journal, clicca <strong>Salva</strong> per rendere persistenti le impostazioni. Ora sei pronto per usare ED:Event2Led! Vai all'<strong>Editor Effetti</strong> per creare effetti luminosi, oppure a <strong>Eventi</strong> per mappare gli eventi di gioco agli effetti."
            }
        ]
    },
    "effects": {
        "steps": [
            {
                "target": "#effects-library",
                "position": "right",
                "title": "Libreria Effetti",
                "description": "Questo pannello mostra tutti gli effetti visivi salvati. Ogni effetto è una sequenza di step (colori, animazioni, durate) che si attivano quando innescati da un evento di gioco. Clicca <strong>Nuovo Effetto</strong> per creare il tuo primo effetto."
            },
            {
                "target": "#btn-new-effect",
                "position": "bottom",
                "title": "Crea Nuovo Effetto",
                "description": "Clicca qui per creare un nuovo effetto. Potrai aggiungere multipli step, ognuno con il proprio tipo di effetto primitivo (colore statico, respiro, onda, ripple, ecc.), colori e durata."
            },
            {
                "target": "#effect-editor-panel",
                "position": "left",
                "title": "Editor Effetti",
                "description": "Qui costruisci la sequenza del tuo effetto. Aggiungi step, scegli effetti primitivi (Statico, Respiro, Onda, ecc.), seleziona colori, imposta durate e definisci cosa succede dopo la fine dell'effetto (loop, spegni, o mantieni ultimo colore)."
            },
            {
                "target": "#btn-test-effect",
                "position": "bottom",
                "title": "Testa Effetto",
                "description": "Una volta aggiunti step al tuo effetto, clicca <strong>Testa su Tastiera</strong> per visualizzarlo in tempo reale sul tuo hardware RGB. Questo ti aiuta a perfezionare colori e tempi prima di assegnare l'effetto agli eventi di gioco."
            },
            {
                "target": "#btn-save-effect",
                "position": "bottom",
                "title": "Salva Effetto",
                "description": "Quando sei soddisfatto del tuo effetto, clicca <strong>Salva</strong> per aggiungerlo alla libreria. Potrai poi assegnarlo agli eventi di Elite Dangerous nella pagina <strong>Eventi</strong>."
            }
        ]
    },
    "events": {
        "steps": [
            {
                "target": "#events-table",
                "position": "bottom",
                "title": "Tabella Mappatura Eventi",
                "description": "Questa tabella mostra tutti gli eventi del journal di Elite Dangerous e i loro effetti assegnati. Gli <strong>eventi mappati</strong> (con punto colorato) attiveranno illuminazione RGB. Gli <strong>eventi non mappati</strong> (punto grigio) sono inattivi. Clicca su una riga evento per assegnare o cambiare il suo effetto."
            },
            {
                "target": ".event-row",
                "position": "right",
                "title": "Riga Evento",
                "description": "Ogni riga rappresenta un evento di gioco (es. <strong>FSDJump</strong>, <strong>Docked</strong>, <strong>UnderAttack</strong>). Il punto colorato indica la priorita dell'evento (effetti con priorita maggiore prevalgono su quelli minori). Clicca una riga per aprire la modale di assegnazione effetto."
            },
            {
                "target": "#search-events",
                "position": "bottom",
                "title": "Cerca Eventi",
                "description": "Usa questa casella di ricerca per trovare rapidamente eventi specifici. Digita parole chiave come <code>jump</code>, <code>dock</code>, o <code>combat</code> per filtrare la tabella."
            },
            {
                "target": "#filter-mapped",
                "position": "bottom",
                "title": "Filtra Mappati/Non Mappati",
                "description": "Usa questi pulsanti filtro per mostrare solo eventi <strong>Mappati</strong> (con effetti assegnati), eventi <strong>Non Mappati</strong> (senza effetti), oppure <strong>Tutti</strong> gli eventi."
            }
        ]
    },
    "keyboard": {
        "steps": [
            {
                "target": "#keyboard-matrix",
                "position": "bottom",
                "title": "Matrice Tastiera",
                "description": "Questa è una rappresentazione visiva del layout LED della tua tastiera. Ogni quadrato rappresenta un LED individuale. Clicca su qualsiasi LED per cambiarne il colore, oppure usa gli strumenti sotto per applicare colori rapidamente."
            },
            {
                "target": "#color-picker-section",
                "position": "right",
                "title": "Selettore Colore",
                "description": "Seleziona un colore qui, poi clicca i LED sulla matrice tastiera per applicarlo. Puoi anche usare gli input <strong>Hex</strong> o <strong>RGB</strong> per valori colore precisi."
            },
            {
                "target": "#preset-buttons",
                "position": "bottom",
                "title": "Preset Colori",
                "description": "Puoi salvare fino a 3 configurazioni colore come preset (P1, P2, P3). Clicca <strong>Salva Preset</strong> per memorizzare il layout tastiera corrente, poi clicca <strong>P1/P2/P3</strong> per richiamarlo rapidamente. I preset possono anche essere usati come effetti nella Libreria Effetti."
            },
            {
                "target": "#keybindings-loader",
                "position": "top",
                "title": "Profili Keybinding",
                "description": "Carica il tuo file keybinding di Elite Dangerous (<code>.binds</code>) per colorare automaticamente i tasti per funzione (controlli volo, armi, targeting, ecc.). Questo rende piu facile creare layout tastiera funzionali."
            },
            {
                "target": "#btn-apply-to-hardware",
                "position": "top",
                "title": "Applica all'Hardware",
                "description": "Clicca questo pulsante per applicare immediatamente la configurazione colore corrente alla tua tastiera fisica. I colori resteranno finche non li cambi o finche non viene innescato un effetto da evento di gioco."
            }
        ]
    },
    "status": {
        "steps": [
            {
                "target": "#stats-bar",
                "position": "bottom",
                "title": "Panoramica Stato",
                "description": "Questa barra mostra lo stato del monitoraggio in tempo reale, il numero di alert attivi e i valori esadecimali dei flag di stato del gioco. ED:Event2Led interroga <code>Status.json</code> ogni 750ms per rilevare cambiamenti."
            },
            {
                "target": "#ship-systems-grid",
                "position": "bottom",
                "title": "Flag Sistemi Nave",
                "description": "Queste card rappresentano i flag di stato nave dal file <code>Status.json</code> di Elite Dangerous. Quando un flag diventa attivo (es. <strong>HardpointsDeployed</strong>, <strong>FsdCharging</strong>), la card si illumina e innesca il suo effetto RGB assegnato."
            },
            {
                "target": ".status-flag-card",
                "position": "right",
                "title": "Card Flag Stato",
                "description": "Ogni card mostra il nome del flag, il suo effetto assegnato (se presente) e un indicatore di stato live. Le <strong>barre priorita</strong> in alto mostrano il livello di priorita dell'effetto (piu barre = priorita maggiore). Clicca sul nome effetto per modificarne l'assegnazione."
            },
            {
                "target": "#odyssey-grid",
                "position": "top",
                "title": "Flag Odyssey",
                "description": "Questi sono flag specifici di Odyssey (gameplay a piedi). Flag come <strong>OnFoot</strong>, <strong>InTaxi</strong> e <strong>AimDownSight</strong> si attivano solo quando sei fuori dalla nave. Possono avere propri effetti RGB unici."
            }
        ]
    }
}

def update_file(lang_code: str, tour_guides_data: dict = None):
    """Add tour_ui and tour_guides to translation file.

    Args:
        lang_code: Language code (it, de, es, fr)
        tour_guides_data: Custom tour_guides dict, or None to copy from EN
    """
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add tour_ui
    data['tour_ui'] = TOUR_UI[lang_code]
    print(f"  [OK] Added tour_ui with 7 keys")

    # Add tour_guides
    if tour_guides_data:
        data['tour_guides'] = tour_guides_data
        print(f"  [OK] Added tour_guides with full translations")
    else:
        # Copy from EN but keep original language (for non-IT languages)
        en_file = i18n_dir / 'en.json'
        with open(en_file, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        data['tour_guides'] = en_data.get('tour_guides', {})
        print(f"  [OK] Copied tour_guides from EN (5 pages)")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Add tour system to IT (full), DE/ES/FR (copy EN)."""
    print("="*70)
    print("  Adding Contextual Tour Guides (IT, DE, ES, FR)")
    print("="*70)

    try:
        # Italian: Full custom translation
        update_file('it', TOUR_GUIDES_IT)
    except Exception as e:
        print(f"  [FAIL] Error updating it.json: {e}")

    # DE, ES, FR: Copy EN structure (can be translated later)
    for lang_code in ['de', 'es', 'fr']:
        try:
            update_file(lang_code)
        except Exception as e:
            print(f"  [FAIL] Error updating {lang_code}.json: {e}")

    print("\n" + "="*70)
    print("  DONE! All translation files updated.")
    print("  Note: DE/ES/FR use EN text for now - translate manually if needed.")
    print("="*70)

if __name__ == '__main__':
    main()
