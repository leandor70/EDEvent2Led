/**
 * Manual Navigation and Utilities
 *
 * Handles:
 * - Context-aware chapter navigation from URL hash
 * - Search functionality
 * - Active chapter highlighting in TOC
 * - Smooth scrolling
 * - Multilingual support (i18n)
 */

// ========================================
// I18N STATE
// ========================================

let currentLanguage = 'it';  // Default: Italian
let manualTranslations = {};
let isI18nLoaded = false;

// ========================================
// I18N INITIALIZATION
// ========================================

/**
 * Initialize i18n for manual with specified language.
 * @param {string} language - Language code (it, en, de, fr, es)
 * @returns {Promise<boolean>} - Success status
 */
async function initManualI18n(language = 'it') {
    console.log(`[Manual i18n] Initializing with language: ${language}`);

    const success = await loadManualLanguage(language);

    if (success) {
        applyManualTranslations();
        isI18nLoaded = true;
        console.log('[Manual i18n] Initialization complete');
    } else {
        console.error('[Manual i18n] Initialization failed');
    }

    return success;
}

/**
 * Load translation file for manual.
 * @param {string} language - Language code
 * @returns {Promise<boolean>} - Success status
 */
async function loadManualLanguage(language) {
    try {
        const response = await fetch(`/config/i18n/manual/${language}.json`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        manualTranslations = await response.json();
        currentLanguage = language;

        console.log(`[Manual i18n] Loaded manual/${language}.json successfully`);
        return true;
    } catch (error) {
        console.error(`[Manual i18n] Failed to load manual/${language}.json:`, error);

        // Fallback to Italian if other language fails
        if (language !== 'it') {
            console.log('[Manual i18n] Attempting fallback to Italian...');
            return await loadManualLanguage('it');
        }

        return false;
    }
}

/**
 * Apply translations to all elements with data-i18n-manual attribute.
 */
function applyManualTranslations() {
    const elements = document.querySelectorAll('[data-i18n-manual]');

    elements.forEach(element => {
        const key = element.getAttribute('data-i18n-manual');
        const translation = getManualTranslation(key);

        if (translation) {
            // Handle different element types
            if (element.tagName === 'INPUT' && element.type === 'text') {
                element.placeholder = translation;
            } else {
                element.textContent = translation;
            }
        }
    });

    console.log(`[Manual i18n] Applied ${elements.length} translations`);
}

/**
 * Get translation by key path (e.g., "toc.chapter1").
 * @param {string} keyPath - Dot-separated key path
 * @returns {string|null} - Translation or null if not found
 */
function getManualTranslation(keyPath) {
    const keys = keyPath.split('.');
    let value = manualTranslations;

    for (const key of keys) {
        if (value && typeof value === 'object' && key in value) {
            value = value[key];
        } else {
            console.warn(`[Manual i18n] Missing translation: ${keyPath}`);
            return null;
        }
    }

    return typeof value === 'string' ? value : null;
}

/**
 * Change manual language at runtime.
 * @param {string} language - New language code
 * @returns {Promise<boolean>} - Success status
 */
async function changeManualLanguage(language) {
    console.log(`[Manual i18n] Changing language from ${currentLanguage} to ${language}`);

    const success = await loadManualLanguage(language);

    if (success) {
        applyManualTranslations();

        // Update "no results" message if visible
        const noResults = document.querySelector('.no-results');
        if (noResults) {
            noResults.remove();
            showNoResults();  // Recreate with new language
        }

        // Save preference to localStorage
        localStorage.setItem('manualLanguage', language);
    }

    return success;
}

// ========================================
// INITIALIZATION
// ========================================

// Load i18n first, then navigate
window.addEventListener('load', async () => {
    // Try to load saved language preference
    // Each manual page is written in one language (<html lang>): its TOC and
    // labels must match it (manual_en.html with an Italian TOC otherwise).
    const savedLanguage = document.documentElement.lang || localStorage.getItem('manualLanguage') || 'it';

    // Initialize i18n
    await initManualI18n(savedLanguage);

    // Navigate to chapter
    const hash = window.location.hash;
    if (hash) {
        navigateToChapter(hash.substring(1));
    } else {
        // Default: show introduction chapter
        navigateToChapter('introduction');
    }
});

// The in-app viewer reuses the open page and only changes the #chapter
// (contextual help from another page): follow it without a reload.
window.addEventListener('hashchange', () => {
    const id = window.location.hash.substring(1);
    if (id) navigateToChapter(id);
});

// Navigate to specific chapter
function navigateToChapter(chapterId) {
    // Hide all chapters
    document.querySelectorAll('.chapter').forEach(chapter => {
        chapter.classList.remove('visible');
    });

    // Show target chapter
    const targetChapter = document.querySelector(`#${chapterId}`);
    if (targetChapter) {
        targetChapter.classList.add('visible');

        // Scroll to top of content
        document.querySelector('.manual-content').scrollTop = 0;

        // Update URL hash without jumping
        history.replaceState(null, null, `#${chapterId}`);

        // Highlight in TOC
        highlightCurrentChapter(chapterId);
    } else {
        console.warn(`Chapter not found: ${chapterId}`);
    }
}

// Highlight active chapter in TOC
function highlightCurrentChapter(chapterId) {
    document.querySelectorAll('.manual-toc a').forEach(link => {
        link.classList.remove('active');
    });

    const activeLink = document.querySelector(`.manual-toc a[href="#${chapterId}"]`);
    if (activeLink) {
        activeLink.classList.add('active');

        // Scroll TOC to make active item visible
        activeLink.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// TOC link clicks
document.querySelectorAll('.manual-toc a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const chapterId = link.getAttribute('href').substring(1);
        navigateToChapter(chapterId);
    });
});

// Search functionality
const searchInput = document.getElementById('search-manual');
let searchTimeout;

searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);

    const query = e.target.value.toLowerCase().trim();

    // Debounce search
    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300);
});

function performSearch(query) {
    if (!query) {
        // Reset: show current chapter only
        const currentHash = window.location.hash.substring(1) || 'topology-editor';
        navigateToChapter(currentHash);
        return;
    }

    // Search logic: show all chapters that match
    let foundAny = false;

    document.querySelectorAll('.chapter').forEach(chapter => {
        const text = chapter.textContent.toLowerCase();
        const matches = text.includes(query);

        if (matches) {
            chapter.classList.add('visible');
            foundAny = true;

            // Highlight search terms (simple implementation)
            highlightSearchTerms(chapter, query);
        } else {
            chapter.classList.remove('visible');
        }
    });

    // Update TOC to show which chapters have results
    document.querySelectorAll('.manual-toc a').forEach(link => {
        const chapterId = link.getAttribute('href').substring(1);
        const chapter = document.querySelector(`#${chapterId}`);

        if (chapter && chapter.classList.contains('visible')) {
            link.style.opacity = '1';
            link.style.fontWeight = '500';
        } else {
            link.style.opacity = '0.4';
            link.style.fontWeight = '400';
        }
    });

    if (!foundAny) {
        // Show "no results" message
        showNoResults();
    }
}

function highlightSearchTerms(chapter, query) {
    // Simple highlight: add background to matching text
    // Note: This is a basic implementation. For production, use a proper search library.
    const paragraphs = chapter.querySelectorAll('p, li, td');

    paragraphs.forEach(p => {
        const text = p.textContent;
        const lowerText = text.toLowerCase();
        const index = lowerText.indexOf(query);

        if (index !== -1) {
            // Add a subtle background highlight
            p.style.background = 'rgba(255, 107, 53, 0.1)';
            p.style.borderRadius = '4px';
            p.style.padding = '5px';
        } else {
            p.style.background = '';
            p.style.padding = '';
        }
    });
}

function showNoResults() {
    // Create temporary "no results" message
    const content = document.querySelector('.manual-content');
    const existing = content.querySelector('.no-results');

    if (existing) return;

    // Get translations (with fallback to Italian)
    const title = getManualTranslation('search.noResults') || 'Nessun risultato trovato';
    const subtitle = getManualTranslation('search.tryDifferent') || 'Prova con parole chiave diverse';

    const noResults = document.createElement('div');
    noResults.className = 'no-results';
    noResults.style.cssText = `
        text-align: center;
        padding: 60px 20px;
        color: rgba(255, 255, 255, 0.5);
    `;
    noResults.innerHTML = `
        <span class="material-symbols-outlined" style="font-size: 64px; opacity: 0.3;">search_off</span>
        <p style="font-size: 1.2rem; margin-top: 20px;">${title}</p>
        <p style="font-size: 0.9rem;">${subtitle}</p>
    `;

    content.appendChild(noResults);

    // Remove after search is cleared
    setTimeout(() => {
        if (searchInput.value.trim() === '') {
            noResults.remove();
        }
    }, 100);
}

// Clear search highlighting when input is cleared
searchInput.addEventListener('input', (e) => {
    if (e.target.value.trim() === '') {
        // Remove all highlights
        document.querySelectorAll('.chapter p, .chapter li, .chapter td').forEach(el => {
            el.style.background = '';
            el.style.padding = '';
        });

        // Reset TOC opacity
        document.querySelectorAll('.manual-toc a').forEach(link => {
            link.style.opacity = '1';
            link.style.fontWeight = '';
        });

        // Remove no-results message
        const noResults = document.querySelector('.no-results');
        if (noResults) noResults.remove();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + F: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
    }

    // Escape: Clear search
    if (e.key === 'Escape' && document.activeElement === searchInput) {
        searchInput.value = '';
        searchInput.dispatchEvent(new Event('input'));
        searchInput.blur();
    }
});

console.log('[Manual] Navigation system loaded');
