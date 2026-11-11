/**
 * load-navigation.js
 * Carica dinamicamente la sidebar navigation da un template inline
 * e attiva automaticamente la voce di menu corretta
 *
 * NOTA: Template inline per compatibilità con file:// protocol (no CORS issues)
 */

(function() {
    'use strict';

    // Inject navigation CSS into document head (for dot indicator and animation)
    if (!document.getElementById('navigation-dot-css')) {
        const style = document.createElement('style');
        style.id = 'navigation-dot-css';
        style.textContent = `
            /* Animated pulse dot */
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            @keyframes pulse-green {
                0%, 100% { opacity: 1; box-shadow: 0 0 4px 1px rgba(74,222,128,0.5); }
                50%       { opacity: 0.6; box-shadow: 0 0 8px 3px rgba(74,222,128,0.25); }
            }
            .animate-pulse {
                animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            }
            .nav-dot-active {
                animation: pulse-green 1.8s ease-in-out infinite;
                background-color: rgb(74,222,128) !important;
            }
            /* Dot indicator classes (missing from inline CSS) */
            .w-2 { width: 0.5rem; }
            .rounded-full { border-radius: 9999px; }
            .bg-orange-500 { background-color: rgb(249, 115, 22); }
        `;
        document.head.appendChild(style);
    }

    // Template della navigation (inline per evitare CORS con file://)
    const NAVIGATION_TEMPLATE = `
<nav class="relative z-20 w-64 h-full sci-fi-border border-l-0 border-y-0 carbon-pattern flex flex-col pt-8 shrink-0">
    <div class="px-6 mb-10">
        <div class="orbitron text-xs tracking-[0.2em] text-[var(--primary-accent)] uppercase mb-2" data-i18n="navigation.title">Navigation</div>
        <div class="h-0.5 w-12 bg-[var(--primary-accent)]"></div>
    </div>
    <div class="flex flex-col space-y-1">
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="index.html" data-page="index">
            <span class="material-symbols-outlined text-xl">home</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.home">Home</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="code.html" data-page="code">
            <span class="material-symbols-outlined text-xl">settings</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.configuration">Configuration</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="events.html" data-page="events">
            <span class="material-symbols-outlined text-xl">event_list</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.events">Events</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="status.html" data-page="status">
            <span class="material-symbols-outlined text-xl">sensors</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.game_status">Game Status</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="effects-lib.html" data-page="effects-lib">
            <span class="material-symbols-outlined text-xl">edit_note</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.effects_lib">Effects Lib</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="devices.html" data-page="devices">
            <span class="material-symbols-outlined text-xl">precision_manufacturing</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.devices">Devices</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="keyboard-designer.html" data-page="keyboard-designer">
            <span class="material-symbols-outlined text-xl">keyboard</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.keyboard_designer">Keyboard Designer</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="topology-editor.html" data-page="topology">
            <span class="material-symbols-outlined text-xl">hub</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.topology_editor">Topology Editor</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="ambilight.html" data-page="ambilight">
            <span class="material-symbols-outlined text-xl">light_mode</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.ambilight">Ambilight</span>
        </a>
        <a class="sidebar-item px-6 py-4 flex items-center gap-4 group" href="log.html" data-page="log">
            <span class="material-symbols-outlined text-xl">terminal</span>
            <span class="orbitron text-sm tracking-wider uppercase" data-i18n="navigation.log">Log</span>
        </a>
    </div>
    <!-- User Manual Button -->
    <div class="px-4 pb-3 border-t border-white/10 pt-4 mx-2 mt-auto">
        <button onclick="openManualViewerContextual()"
                class="w-full relative group flex items-center justify-center gap-3 py-3 rounded hover:bg-white/5 transition-colors"
                style="border: 1px solid rgba(96, 165, 250, 0.3);"
                data-i18n-attr="title:navigation.manual_tooltip" title="Open the user manual at this page's chapter">
            <span class="material-symbols-outlined text-xl text-blue-400">menu_book</span>
            <span class="orbitron text-xs tracking-wider uppercase text-blue-300" data-i18n="navigation.show_guide">Show Guide</span>
        </button>
    </div>
    <!-- Info & Donations -->
    <div class="px-4 pb-4 border-t border-white/10 pt-4 mx-2">
        <a href="index.html?show_welcome=true"
           class="sidebar-item relative group flex items-center justify-center gap-3 py-3 rounded"
           style="background: linear-gradient(135deg, rgba(255, 183, 77, 0.08) 0%, rgba(255, 152, 0, 0.08) 100%); border: 1px solid rgba(255, 183, 77, 0.2);">
            <span class="material-symbols-outlined text-xl text-amber-400">volunteer_activism</span>
            <span class="orbitron text-xs tracking-wider uppercase text-amber-300" data-i18n="navigation.info_donations">Info & Donations</span>
        </a>
    </div>
    <!-- Profile Export / Import -->
    <div class="px-4 pb-4 border-t border-white/10 pt-4 mx-2 mt-auto">
        <div class="orbitron text-[10px] tracking-[0.2em] text-white/30 uppercase mb-3" data-i18n="navigation.profiles">Profiles</div>
        <div class="flex gap-2">
            <button id="btn-export-profile"
              class="flex-1 relative group"
              data-i18n-attr="title:navigation.export_tooltip" title="Export current profile to JSON">
              <div class="absolute inset-0 bg-[var(--primary-accent)] blur-sm opacity-0 group-hover:opacity-20 transition-opacity rounded"></div>
              <div class="relative flex items-center justify-center gap-1.5 py-2 sci-fi-border border border-white/10
                          group-hover:border-[var(--primary-accent)]/50 transition-colors rounded">
                <span class="material-symbols-outlined text-[15px] text-[var(--primary-accent)]/70 group-hover:text-[var(--primary-accent)]">download</span>
                <span class="orbitron text-[9px] tracking-[0.15em] text-white/50 group-hover:text-white/80 uppercase" data-i18n="navigation.export">Export</span>
              </div>
            </button>
            <button id="btn-import-profile"
              class="flex-1 relative group"
              data-i18n-attr="title:navigation.import_tooltip" title="Import profile from JSON (replaces current)">
              <div class="absolute inset-0 bg-amber-500 blur-sm opacity-0 group-hover:opacity-15 transition-opacity rounded"></div>
              <div class="relative flex items-center justify-center gap-1.5 py-2 sci-fi-border border border-white/10
                          group-hover:border-amber-500/50 transition-colors rounded">
                <span class="material-symbols-outlined text-[15px] text-amber-400/70 group-hover:text-amber-400">upload</span>
                <span class="orbitron text-[9px] tracking-[0.15em] text-white/50 group-hover:text-white/80 uppercase" data-i18n="navigation.import">Import</span>
              </div>
            </button>
        </div>
        <input type="file" id="profile-file-input" accept=".json" class="hidden" />
    </div>
    <div class="px-4 pb-4 border-t border-white/10 pt-4 mx-2">
        <div class="text-[10px] orbitron text-white/30 uppercase tracking-widest" data-i18n="navigation.system_status">System Status</div>
        <div class="flex items-center gap-2 mt-2">
            <div id="nav-core-dot" class="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></div>
            <span id="nav-core-label" class="text-xs uppercase text-white/50">Core Online</span>
        </div>
    </div>
</nav>
    `;

    // Trova il container della navigation
    const navContainer = document.getElementById('sidebar-nav');

    if (!navContainer) {
        console.warn('[Navigation] Container #sidebar-nav non trovato');
        return;
    }

    // Leggi quale pagina deve essere attiva
    const activePage = navContainer.getAttribute('data-active-page');

    if (!activePage) {
        console.warn('[Navigation] Attributo data-active-page mancante');
        return;
    }

    // Inserisci il template nel container
    navContainer.innerHTML = NAVIGATION_TEMPLATE;

    // Trova il link corrispondente alla pagina attiva
    const activeLink = navContainer.querySelector(`a[data-page="${activePage}"]`);

    if (activeLink) {
        // Aggiungi la classe 'active' al link
        activeLink.classList.add('active');
        console.log(`[Navigation] Pagina attiva: ${activePage} ✓`);
    } else {
        console.warn(`[Navigation] Link con data-page="${activePage}" non trovato`);
    }

    // Setup profile export/import buttons
    setupProfileButtons();

    // Apply saved theme to this page (common.js exposes loadAndApplyTheme globally)
    if (typeof loadAndApplyTheme === 'function') loadAndApplyTheme();

    // ── Core Status Dot polling ─────────────────────────────────────────────────
    // Green = OpenRGB connected (stable)
    // Orange pulsing = core running but OpenRGB not connected
    function _updateCoreDot(isActive) {
        const dot   = document.getElementById('nav-core-dot');
        const label = document.getElementById('nav-core-label');
        if (!dot) return;
        if (isActive) {
            dot.classList.add('nav-dot-active');
            dot.classList.remove('animate-pulse');
            if (label) label.style.color = 'rgba(134,239,172,0.8)';
        } else {
            dot.classList.remove('nav-dot-active');
            dot.classList.add('animate-pulse');
            if (label) label.style.color = '';
        }
    }

    async function _pollCoreStatus() {
        try {
            const s = await eel.get_monitoring_status()();
            _updateCoreDot(!!(s && s.openrgb_connected));
        } catch (_) { /* eel not ready yet */ }
    }

    // First check after a short delay (eel may not be ready immediately), then every 5s
    setTimeout(_pollCoreStatus, 1500);
    setInterval(_pollCoreStatus, 5000);

    // ── Profile Export/Import ──────────────────────────────

    function setupProfileButtons() {
        const btnExport = document.getElementById('btn-export-profile');
        const btnImport = document.getElementById('btn-import-profile');
        const fileInput = document.getElementById('profile-file-input');
        if (!btnExport || !btnImport) return;

        // EXPORT: chiama API -> download file
        btnExport.addEventListener('click', async () => {
            const result = await eel.export_profile()();
            if (!result?.success) {
                if (typeof showNotification === 'function') showNotification(result?.error || 'Export failed', 'error');
                return;
            }
            const date = new Date().toISOString().slice(0, 10);
            const blob = new Blob(
                [JSON.stringify(result.profile, null, 2)],
                { type: 'application/json' }
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ed_profile_${date}.json`;
            a.click();
            URL.revokeObjectURL(url);
            if (typeof showNotification === 'function') showNotification('Profile exported', 'success');
        });

        // IMPORT: apri file picker -> conferma -> chiama API -> reload page data
        btnImport.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            fileInput.value = '';  // reset per permettere ri-selezione stesso file

            let profile;
            try {
                profile = JSON.parse(await file.text());
            } catch {
                if (typeof showNotification === 'function') showNotification('Invalid JSON file', 'error');
                return;
            }

            if (!profile.effects || !profile.mappings) {
                if (typeof showNotification === 'function') showNotification('Not a valid ED:Event2Led profile', 'error');
                return;
            }

            const effectsCount = profile.effects?.effects?.length ?? 0;
            const mappingsCount = Object.keys(profile.mappings?.mappings ?? {}).length;

            showImportConfirm(effectsCount, mappingsCount, async () => {
                const result = await eel.import_profile(profile)();
                if (!result?.success) {
                    if (typeof showNotification === 'function') showNotification(result?.error || 'Import failed', 'error');
                    return;
                }
                if (typeof showNotification === 'function') {
                    showNotification(
                        `Imported: ${result.effects_count} effects, ${result.mappings_count} mappings`,
                        'success'
                    );
                }
                // Ricarica dati della pagina corrente se disponibili
                if (typeof loadEffectsList === 'function') await loadEffectsList();
                if (typeof loadEventMappings === 'function') await loadEventMappings();
            });
        });
    }

    function showImportConfirm(effectsCount, mappingsCount, onConfirm) {
        const existing = document.getElementById('profile-import-modal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'profile-import-modal';
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center';
        modal.innerHTML = `
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>
          <div class="relative sci-fi-border bg-[#0d0d0d] border border-white/10 p-8 max-w-sm w-full mx-4">
            <div class="orbitron text-sm tracking-[0.2em] text-amber-400 mb-4">IMPORT PROFILE</div>
            <p class="text-white/70 text-sm mb-2">
              Questo sostituira <span class="text-white font-bold">${effectsCount} effetti</span>
              e <span class="text-white font-bold">${mappingsCount} assegnazioni</span>.
            </p>
            <p class="text-white/40 text-xs mb-6">La configurazione attuale verra persa.</p>
            <div class="flex gap-3 justify-end">
              <button id="profile-import-cancel"
                class="px-5 py-2 text-sm border border-white/20 text-white/60 hover:bg-white/5 transition-colors rounded">
                Annulla
              </button>
              <button id="profile-import-confirm"
                class="px-6 py-2 text-sm orbitron tracking-wider font-bold transition-colors rounded"
                style="background: rgba(245,158,11,0.85); color: black;">
                IMPORTA
              </button>
            </div>
          </div>`;

        document.body.appendChild(modal);
        modal.querySelector('#profile-import-cancel').addEventListener('click', () => modal.remove());
        modal.querySelector('.absolute').addEventListener('click', () => modal.remove());
        modal.querySelector('#profile-import-confirm').addEventListener('click', () => {
            modal.remove();
            onConfirm();
        });
    }
})();

// ========================================
// CONTEXT-AWARE MANUAL VIEWER
// ========================================

/**
 * Opens the manual viewer to the chapter corresponding to the current page.
 * Maps page identifiers (from data-active-page) to manual chapter IDs.
 */
window.openManualViewerContextual = function() {
    // Page to chapter mapping
    const PAGE_TO_CHAPTER = {
        'effects-lib': 'effects-editor',
        'events': 'events',
        'keyboard-designer': 'keyboard-designer',
        'topology': 'topology-editor',
        'status': 'status',
        'devices': 'devices',
        'test': 'test',
        'log': 'log',
        'code': 'settings',
        'ambilight': 'ambilight'
    };

    // Detect current page from sidebar navigation
    const navContainer = document.getElementById('sidebar-nav');
    const activePage = navContainer ? navContainer.getAttribute('data-active-page') : null;

    // Get corresponding chapter ID
    const chapter = activePage ? PAGE_TO_CHAPTER[activePage] : null;

    if (chapter) {
        console.log(`[Manual] Opening context-aware help: ${activePage} → ${chapter}`);
        openManualViewer(chapter);
    } else {
        console.warn(`[Manual] No chapter mapping for page: ${activePage}, opening introduction`);
        openManualViewer('introduction');
    }
};
