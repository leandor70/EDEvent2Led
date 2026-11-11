/**
 * glass-select.js - every <select> opens the glass dropdown of the theme
 * (the one of the Configuration page) instead of the operating system list.
 *
 * The <select> stays where it is and stays the source of truth: the page code
 * keeps reading select.value and listening to "change" (inline onchange too).
 * Only its list is replaced:
 *   - mouse down / Space / Enter / Alt+Down / F4 on a select open a menu built
 *     from its current options (so translations and options added later by
 *     the page are always up to date);
 *   - choosing an item sets select.value and fires "input" + "change", like
 *     the native list;
 *   - one listener on the document covers every select, including the ones
 *     the page creates later.
 * The menu is appended to <body> with position: fixed, so panels with
 * overflow: hidden cannot clip it.
 * Skipped: disabled selects, <select multiple>, <select size="N>1">, and any
 * select with the attribute data-native-select.
 */
(function () {
    'use strict';

    let current = null;   // { select, menu, items, active }

    const handles = (el) =>
        el instanceof HTMLSelectElement &&
        !el.disabled && !el.multiple && !(el.size > 1) &&
        !el.hasAttribute('data-native-select');

    function close(refocus) {
        if (!current) return;
        const { select, menu } = current;
        menu.remove();
        select.classList.remove('glass-select-open');
        current = null;
        if (refocus) select.focus({ preventScroll: true });
    }

    function choose(index) {
        if (!current) return;
        const { select } = current;
        const item = current.items[index];
        if (!item || item.disabled) return;
        if (select.selectedIndex !== item.index) {
            select.selectedIndex = item.index;
            select.dispatchEvent(new Event('input', { bubbles: true }));
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }
        close(true);
    }

    function setActive(index) {
        if (!current) return;
        const { items } = current;
        if (!items.length) return;
        index = Math.max(0, Math.min(items.length - 1, index));
        current.active = index;
        items.forEach((it, i) => it.el.classList.toggle('glass-select-active', i === index));
        items[index].el.scrollIntoView({ block: 'nearest' });
    }

    function step(dir) {
        if (!current) return;
        const { items } = current;
        let i = current.active;
        for (let n = 0; n < items.length; n++) {
            i += dir;
            if (i < 0 || i >= items.length) return;
            if (!items[i].disabled) { setActive(i); return; }
        }
    }

    function place(select, menu) {
        const r = select.getBoundingClientRect();
        const gap = 4;
        menu.style.minWidth = `${r.width}px`;
        menu.style.left = `${Math.max(4, Math.min(r.left, window.innerWidth - menu.offsetWidth - 4))}px`;
        const below = window.innerHeight - r.bottom - gap - 8;
        const above = r.top - gap - 8;
        const h = menu.scrollHeight;
        if (h <= below || below >= above) {
            menu.style.top = `${r.bottom + gap}px`;
            menu.style.maxHeight = `${Math.max(120, below)}px`;
        } else {
            const mh = Math.min(h, above);
            menu.style.top = `${r.top - gap - mh}px`;
            menu.style.maxHeight = `${mh}px`;
        }
    }

    function open(select) {
        close(false);
        const menu = document.createElement('ul');
        menu.className = 'dropdown-menu glass-select-menu';
        menu.setAttribute('role', 'listbox');
        const items = [];

        const addOption = (opt, inGroup) => {
            if (opt.hidden) return;
            const li = document.createElement('li');
            li.className = 'dropdown-item' + (inGroup ? ' glass-select-indent' : '');
            li.setAttribute('role', 'option');
            li.textContent = opt.textContent.trim() || ' ';
            const disabled = opt.disabled || (opt.parentElement && opt.parentElement.disabled);
            if (disabled) li.classList.add('glass-select-disabled');
            if (opt.index === select.selectedIndex) {
                li.classList.add('selected');
                li.setAttribute('aria-selected', 'true');
            }
            const k = items.length;
            li.addEventListener('mousedown', (e) => e.preventDefault());   // keep focus
            li.addEventListener('click', () => choose(k));
            li.addEventListener('mousemove', () => { if (current && current.active !== k && !disabled) setActive(k); });
            items.push({ el: li, index: opt.index, disabled: !!disabled });
            menu.appendChild(li);
        };

        for (const child of select.children) {
            if (child.tagName === 'OPTGROUP') {
                const head = document.createElement('li');
                head.className = 'glass-select-group';
                head.textContent = child.label;
                menu.appendChild(head);
                for (const opt of child.children) if (opt.tagName === 'OPTION') addOption(opt, true);
            } else if (child.tagName === 'OPTION') {
                addOption(child, false);
            }
        }

        document.body.appendChild(menu);
        current = { select, menu, items, active: -1 };
        select.classList.add('glass-select-open');
        place(select, menu);
        const sel = items.findIndex(it => it.index === select.selectedIndex);
        if (sel >= 0) setActive(sel);
    }

    // Mouse: replace the native list
    document.addEventListener('mousedown', (e) => {
        const t = e.target;
        if (current && current.menu.contains(t)) return;
        if (handles(t)) {
            e.preventDefault();               // no OS list
            const wasOpen = current && current.select === t;
            // A mouse click is not keyboard focus: no focus ring (like the Configuration button)
            t.focus({ preventScroll: true, focusVisible: false });
            if (wasOpen) close(false); else open(t);
            return;
        }
        if (current) close(false);            // click outside
    }, true);

    // Keyboard on a focused select or inside the open menu
    document.addEventListener('keydown', (e) => {
        if (current) {
            switch (e.key) {
                case 'Escape': case 'Tab':
                    if (e.key === 'Escape') e.preventDefault();
                    close(e.key === 'Escape');
                    return;
                case 'ArrowDown': e.preventDefault(); step(+1); return;
                case 'ArrowUp': e.preventDefault(); step(-1); return;
                case 'Home': e.preventDefault(); setActive(0); return;
                case 'End': e.preventDefault(); setActive(current.items.length - 1); return;
                case 'Enter': case ' ':
                    e.preventDefault();
                    if (current.active >= 0) choose(current.active); else close(true);
                    return;
                default: return;
            }
        }
        const t = e.target;
        if (!handles(t)) return;
        const openKey = e.key === ' ' || e.key === 'Enter' || e.key === 'F4' ||
                        (e.altKey && (e.key === 'ArrowDown' || e.key === 'ArrowUp'));
        if (openKey) { e.preventDefault(); open(t); }
    }, true);

    // The list follows its select: close it when the page moves under it
    window.addEventListener('resize', () => close(false));
    document.addEventListener('scroll', (e) => {
        if (current && !current.menu.contains(e.target)) close(false);
    }, true);
    window.addEventListener('blur', () => close(false));
})();
