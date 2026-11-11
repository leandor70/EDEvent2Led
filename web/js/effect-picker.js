'use strict';

/**
 * effect-picker.js — Shared effect-grid picker used by both Events and Status pages.
 *
 * Usage:
 *   const picker = new EffectPicker({ category: 'event', onSelect: id => ... });
 *   picker.mount(containerElement);
 *   await picker.load();
 *
 * The picker renders a searchable, paginated grid of effect cards with mini
 * timelines.  The calling page owns the modal shell; the picker only owns the
 * inner grid area.
 */

const PICKER_PAGE_SIZE = 12;  // 6 cols × 2 rows per page

class EffectPicker {
    /**
     * @param {object} opts
     * @param {string}   [opts.category]     Filter: 'event'|'status'|'general'|null (all+general)
     * @param {string}   [opts.selectedId]   Initially selected effect id (or null)
     * @param {Function} [opts.onSelect]     Called with (effectId|null) on selection change
     * @param {boolean}  [opts.allowNone]    Show "No Effect" deselect button (default true)
     */
    constructor(opts = {}) {
        this.category   = opts.category   || null;
        this.selectedId = opts.selectedId || null;
        this.onSelect   = opts.onSelect   || (() => {});
        this.allowNone  = opts.allowNone  !== false;

        this._effects   = [];   // full list after API load
        this._filtered  = [];   // after search
        this._page      = 0;
        this._search    = '';
        this._container = null; // DOM element provided by mount()
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /** Mount the picker into a DOM element (does not load data yet). */
    mount(containerEl) {
        this._container = containerEl;
        this._render();
    }

    /** Fetch effects from backend and re-render. */
    async load() {
        try {
            const r = await api('get_effects_list', this.category);
            this._effects = r?.effects || [];
        } catch (_) {
            this._effects = [];
        }
        this._applySearch();
        this._render();
    }

    /** Programmatically set the selected effect id. */
    setSelected(id) {
        this.selectedId = id || null;
        this._renderGrid();
        this._syncNoEffectBtn();
    }

    /** Return the currently selected effect id (or null). */
    getSelected() { return this.selectedId; }

    // ── Private: search / filter ──────────────────────────────────────────────

    _applySearch() {
        const term = this._search.toLowerCase();
        this._filtered = term
            ? this._effects.filter(e =>
                e.name.toLowerCase().includes(term) ||
                (e.description || '').toLowerCase().includes(term))
            : [...this._effects];
        this._page = 0;
    }

    // ── Private: rendering ────────────────────────────────────────────────────

    _render() {
        if (!this._container) return;
        this._container.innerHTML = `
            <div class="picker-search flex items-center gap-2 mb-3">
                <span class="material-symbols-outlined text-white/40 text-sm">search</span>
                <input class="picker-search-input flex-1 bg-transparent border-b border-white/15
                              text-sm text-white/80 outline-none pb-1 placeholder-white/30"
                       placeholder="Search effects…" value="${escapeAttr(this._search)}" />
                ${this.allowNone ? `
                <button class="picker-none-btn text-xs px-2 py-1 border rounded uppercase tracking-wider
                               transition-colors ${this.selectedId === null
                                   ? 'border-[var(--primary-accent)] text-[var(--primary-accent)]'
                                   : 'border-white/15 text-white/40 hover:border-white/30'}">
                    None
                </button>` : ''}
            </div>
            <div class="picker-grid grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2.5 mb-3 overflow-y-auto" style="max-height: 384px;"></div>
            <div class="picker-pagination flex items-center justify-between text-xs text-white/40"></div>`;

        this._container.querySelector('.picker-search-input')
            .addEventListener('input', e => {
                this._search = e.target.value;
                this._applySearch();
                this._renderGrid();
                this._renderPagination();
            });

        if (this.allowNone) {
            this._container.querySelector('.picker-none-btn')
                .addEventListener('click', () => this._selectId(null));
        }

        this._renderGrid();
        this._renderPagination();
    }

    _renderGrid() {
        const grid = this._container?.querySelector('.picker-grid');
        if (!grid) return;

        const totalPages = Math.max(1, Math.ceil(this._filtered.length / PICKER_PAGE_SIZE));
        this._page = Math.max(0, Math.min(this._page, totalPages - 1));
        const page = this._filtered.slice(
            this._page * PICKER_PAGE_SIZE,
            (this._page + 1) * PICKER_PAGE_SIZE
        );

        grid.innerHTML = '';
        if (this._filtered.length === 0) {
            grid.innerHTML = `<div class="col-span-6 py-6 text-center text-white/30 text-sm italic">
                No effects found</div>`;
            return;
        }
        page.forEach(e => grid.appendChild(this._makeCard(e)));
    }

    _makeCard(effect) {
        const sel = effect.id === this.selectedId;
        const card = document.createElement('div');
        card.className = this._cardClass(sel);
        card.dataset.effectId = effect.id;
        card.style.position = 'relative';

        const steps = (effect.steps || []).length;
        const cat   = effect.category || '';

        card.innerHTML = `
            <div class="text-sm font-semibold text-white truncate mb-1.5"
                 title="${escapeAttr(effect.name)}">${escapeHtml(effect.name)}</div>
            <canvas class="picker-timeline block rounded w-full mb-1.5" height="28"></canvas>
            <div class="text-[11px] text-white/50 font-medium">${steps} step${steps !== 1 ? 's' : ''} · ${cat}</div>
            <button class="picker-edit-btn"
                    title="Edit effect"
                    style="position:absolute;top:6px;right:6px;width:22px;height:22px;border-radius:4px;
                           background:rgba(255,102,0,0.15);border:1px solid rgba(255,102,0,0.3);
                           color:rgba(255,102,0,0.7);cursor:pointer;display:none;
                           align-items:center;justify-content:center;padding:0;transition:all 0.15s;"
                    onmouseover="this.style.background='rgba(255,102,0,0.3)';this.style.color='#ff6600'"
                    onmouseout="this.style.background='rgba(255,102,0,0.15)';this.style.color='rgba(255,102,0,0.7)'">
                <span class="material-symbols-outlined" style="font-size:13px;line-height:1;">edit</span>
            </button>`;

        card.addEventListener('mouseenter', () => {
            card.querySelector('.picker-edit-btn').style.display = 'flex';
        });
        card.addEventListener('mouseleave', () => {
            card.querySelector('.picker-edit-btn').style.display = 'none';
        });

        card.querySelector('.picker-edit-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            if (typeof openQuickEffectCreator === 'function') {
                openQuickEffectCreator({
                    existingEffect: effect,
                    onSave: async () => { await this.load(); }
                });
            }
        });

        card.addEventListener('click', () => this._selectId(effect.id));

        requestAnimationFrame(() => {
            const cv = card.querySelector('.picker-timeline');
            if (!cv) return;
            const w = cv.offsetWidth || 120;
            cv.width = w;
            _drawPickerTimeline(cv, effect.steps || []);
        });

        return card;
    }

    _cardClass(selected) {
        const base = 'picker-card cursor-pointer rounded p-2.5 transition-all duration-150';
        return selected
            ? `${base} border-2 border-[var(--primary-accent)] bg-[var(--primary-accent)]/10 shadow-lg`
            : `${base} border border-white/10 bg-black/40 hover:border-[var(--primary-accent)]/40 hover:bg-white/5 hover:shadow-md`;
    }

    _renderPagination() {
        const el = this._container?.querySelector('.picker-pagination');
        if (!el) return;
        const total = Math.max(1, Math.ceil(this._filtered.length / PICKER_PAGE_SIZE));
        if (total <= 1) { el.innerHTML = ''; return; }

        el.innerHTML = `
            <button class="picker-prev px-2 py-0.5 border border-white/15 rounded
                           disabled:opacity-30 hover:border-white/30"
                    ${this._page === 0 ? 'disabled' : ''}>‹</button>
            <span>${this._page + 1} / ${total}</span>
            <button class="picker-next px-2 py-0.5 border border-white/15 rounded
                           disabled:opacity-30 hover:border-white/30"
                    ${this._page >= total - 1 ? 'disabled' : ''}>›</button>`;

        el.querySelector('.picker-prev')?.addEventListener('click', () => {
            if (this._page > 0) { this._page--; this._renderGrid(); this._renderPagination(); }
        });
        el.querySelector('.picker-next')?.addEventListener('click', () => {
            if (this._page < total - 1) { this._page++; this._renderGrid(); this._renderPagination(); }
        });
    }

    _selectId(id) {
        this.selectedId = id;
        this._renderGrid();
        this._syncNoEffectBtn();
        this.onSelect(id);
    }

    _syncNoEffectBtn() {
        const btn = this._container?.querySelector('.picker-none-btn');
        if (!btn) return;
        const active = this.selectedId === null;
        btn.className = btn.className
            .replace(/border-\[var\(--primary-accent\)\] text-\[var\(--primary-accent\)\]|border-white\/15 text-white\/40 hover:border-white\/30/g, '')
            .trim()
            + (active
                ? ' border-[var(--primary-accent)] text-[var(--primary-accent)]'
                : ' border-white/15 text-white/40 hover:border-white/30');
    }
}


// ── Mini timeline drawing (shared, mirrors events.js logic) ──────────────────

function _drawPickerTimeline(canvas, steps) {
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    if (!steps?.length) {
        ctx.fillStyle = 'rgba(255,255,255,0.06)';
        ctx.fillRect(0, 0, W, H);
        return;
    }
    const totalMs = steps.reduce((s, st) => s + (st.params?.duration_ms || 500), 0) || 1;
    let x = 0;
    steps.forEach(st => {
        const w = Math.max(1, ((st.params?.duration_ms || 500) / totalMs) * W);
        const colors = st.params?.colors || [];
        if (colors.length === 0) {
            ctx.fillStyle = 'rgba(255,255,255,0.08)';
            ctx.fillRect(x, 0, w, H);
        } else if (colors.length === 1) {
            const [r, g, b] = colors[0];
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            ctx.fillRect(x, 0, w, H);
        } else {
            const grad = ctx.createLinearGradient(x, 0, x + w, 0);
            colors.forEach((c, i) => {
                const [r, g, b] = c;
                grad.addColorStop(i / (colors.length - 1), `rgb(${r},${g},${b})`);
            });
            ctx.fillStyle = grad;
            ctx.fillRect(x, 0, w, H);
        }
        x += w;
    });
}
