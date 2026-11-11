/**
 * Manual Viewer - In-App Browser Window
 *
 * Provides a draggable, resizable, minimizable window for viewing the manual
 * without leaving the application. Similar to VSCode integrated browser.
 */

class ManualViewer {
    constructor() {
        this.container = null;
        this.header = null;
        this.body = null;
        this.iframe = null;

        // State
        this.isMinimized = false;
        this.isFullscreen = false;
        this.isDragging = false;
        this.isResizing = false;
        this.currentResizeHandle = null;

        // Position and size (defaults)
        this.x = 100;
        this.y = 80;
        this.width = 1000;
        this.height = 700;

        // Drag state
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;

        // Resize state
        this.resizeStartX = 0;
        this.resizeStartY = 0;
        this.resizeStartWidth = 0;
        this.resizeStartHeight = 0;
        this.resizeStartLeft = 0;
        this.resizeStartTop = 0;

        // Load saved state
        this.loadState();

        // Bind methods
        this.onDragStart = this.onDragStart.bind(this);
        this.onDragMove = this.onDragMove.bind(this);
        this.onDragEnd = this.onDragEnd.bind(this);
        this.onResizeStart = this.onResizeStart.bind(this);
        this.onResizeMove = this.onResizeMove.bind(this);
        this.onResizeEnd = this.onResizeEnd.bind(this);
    }

    // ========================================
    // STATE PERSISTENCE
    // ========================================

    loadState() {
        try {
            const state = JSON.parse(localStorage.getItem('manualViewerState') || '{}');

            if (state.x !== undefined) this.x = state.x;
            if (state.y !== undefined) this.y = state.y;
            if (state.width !== undefined) this.width = state.width;
            if (state.height !== undefined) this.height = state.height;
            if (state.isMinimized !== undefined) this.isMinimized = state.isMinimized;
        } catch (e) {
            console.warn('[ManualViewer] Failed to load state:', e);
        }
    }

    saveState() {
        const state = {
            x: this.x,
            y: this.y,
            width: this.width,
            height: this.height,
            isMinimized: this.isMinimized
        };

        localStorage.setItem('manualViewerState', JSON.stringify(state));
    }

    // ========================================
    // WINDOW CREATION
    // ========================================

    // Manual in the language of the UI (same rule as openManual in common.js)
    manualFile() {
        const lang = (window.i18n?.getCurrentLanguage?.() || 'it').toLowerCase();
        const supported = ['it', 'en', 'de', 'es', 'fr'];
        return supported.includes(lang) && lang !== 'it' ? `manual_${lang}.html` : 'manual.html';
    }

    open(chapter = null) {
        const file = this.manualFile();
        if (this.container) {
            // Already open - navigate to chapter if specified
            if (chapter) {
                this.iframe.src = `${file}#${chapter}`;
                console.log(`[ManualViewer] Navigating to chapter: ${chapter}`);
            }
            this.container.style.display = 'flex';
            return;
        }

        this.createWindow();
        this.attachEventListeners();

        // Load iframe with optional chapter
        if (chapter) {
            this.iframe.src = `${file}#${chapter}`;
            console.log(`[ManualViewer] Window opened to chapter: ${chapter}`);
        } else {
            this.iframe.src = file;
            console.log('[ManualViewer] Window opened');
        }
    }

    createWindow() {
        // Backdrop
        const backdrop = document.createElement('div');
        backdrop.id = 'manual-viewer-backdrop';
        backdrop.style.cssText = `
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(2px);
            z-index: 9998;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 20px;
        `;

        // Main container
        this.container = document.createElement('div');
        this.container.id = 'manual-viewer';
        this.container.style.cssText = `
            position: absolute;
            left: ${this.x}px;
            top: ${this.y}px;
            width: ${this.width}px;
            height: ${this.isMinimized ? 'auto' : this.height + 'px'};
            background: #1a1a2e;
            border: 1px solid rgba(255, 107, 53, 0.3);
            border-radius: 8px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
            z-index: 9999;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            font-family: 'Rajdhani', sans-serif;
        `;

        // Header
        this.header = document.createElement('div');
        this.header.className = 'manual-viewer-header';
        this.header.style.cssText = `
            background: linear-gradient(135deg, rgba(127, 19, 236, 0.1), rgba(255, 107, 53, 0.1));
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: move;
            user-select: none;
        `;

        // Title
        const title = document.createElement('div');
        title.style.cssText = `
            display: flex;
            align-items: center;
            gap: 10px;
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.95rem;
            font-weight: 600;
            letter-spacing: 0.05em;
        `;
        title.innerHTML = `
            <span class="material-symbols-outlined" style="font-size: 20px; color: #ff6b35;">menu_book</span>
            <span>USER MANUAL</span>
        `;

        // Controls
        const controls = document.createElement('div');
        controls.style.cssText = `
            display: flex;
            gap: 8px;
            align-items: center;
        `;

        // Minimize button
        const minimizeBtn = document.createElement('button');
        minimizeBtn.className = 'manual-viewer-control';
        minimizeBtn.innerHTML = '<span class="material-symbols-outlined">minimize</span>';
        minimizeBtn.title = 'Minimize';
        minimizeBtn.onclick = () => this.toggleMinimize();

        // Fullscreen button
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.className = 'manual-viewer-control';
        fullscreenBtn.innerHTML = '<span class="material-symbols-outlined">fullscreen</span>';
        fullscreenBtn.title = 'Fullscreen';
        fullscreenBtn.onclick = () => this.toggleFullscreen();

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'manual-viewer-control';
        closeBtn.innerHTML = '<span class="material-symbols-outlined">close</span>';
        closeBtn.title = 'Close';
        closeBtn.onclick = () => this.close();

        controls.appendChild(minimizeBtn);
        controls.appendChild(fullscreenBtn);
        controls.appendChild(closeBtn);

        this.header.appendChild(title);
        this.header.appendChild(controls);

        // Body (iframe container)
        this.body = document.createElement('div');
        this.body.className = 'manual-viewer-body';
        this.body.style.cssText = `
            flex: 1;
            overflow: hidden;
            display: ${this.isMinimized ? 'none' : 'block'};
        `;

        // Iframe
        this.iframe = document.createElement('iframe');
        this.iframe.style.cssText = `
            width: 100%;
            height: 100%;
            border: none;
            background: transparent;
        `;

        this.body.appendChild(this.iframe);

        // Resize handles (8 handles: 4 corners + 4 sides)
        this.createResizeHandles();

        // Assemble window
        this.container.appendChild(this.header);
        this.container.appendChild(this.body);

        backdrop.appendChild(this.container);
        document.body.appendChild(backdrop);

        // Backdrop click closes window
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                this.close();
            }
        });

        // Add control button styles
        this.addStyles();
    }

    createResizeHandles() {
        const handles = [
            { position: 'top', cursor: 'ns-resize' },
            { position: 'bottom', cursor: 'ns-resize' },
            { position: 'left', cursor: 'ew-resize' },
            { position: 'right', cursor: 'ew-resize' },
            { position: 'top-left', cursor: 'nwse-resize' },
            { position: 'top-right', cursor: 'nesw-resize' },
            { position: 'bottom-left', cursor: 'nesw-resize' },
            { position: 'bottom-right', cursor: 'nwse-resize' }
        ];

        handles.forEach(({ position, cursor }) => {
            const handle = document.createElement('div');
            handle.className = `resize-handle resize-${position}`;
            handle.dataset.position = position;
            handle.style.cssText = this.getResizeHandleStyle(position, cursor);

            this.container.appendChild(handle);
        });
    }

    getResizeHandleStyle(position, cursor) {
        const base = `
            position: absolute;
            background: transparent;
            cursor: ${cursor};
            z-index: 10;
        `;

        // Corner handles: 12x12px
        if (position.includes('-')) {
            const [vertical, horizontal] = position.split('-');
            return base + `
                width: 12px;
                height: 12px;
                ${vertical}: -6px;
                ${horizontal}: -6px;
            `;
        }

        // Side handles: 6px thick
        if (position === 'top' || position === 'bottom') {
            return base + `
                left: 0;
                right: 0;
                height: 6px;
                ${position}: -3px;
            `;
        } else {
            return base + `
                top: 0;
                bottom: 0;
                width: 6px;
                ${position}: -3px;
            `;
        }
    }

    addStyles() {
        if (document.getElementById('manual-viewer-styles')) return;

        const style = document.createElement('style');
        style.id = 'manual-viewer-styles';
        style.textContent = `
            .manual-viewer-control {
                width: 28px;
                height: 28px;
                border: none;
                background: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border-radius: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                padding: 0;
            }

            .manual-viewer-control:hover {
                background: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.9);
            }

            .manual-viewer-control:active {
                background: rgba(255, 255, 255, 0.15);
            }

            .manual-viewer-control .material-symbols-outlined {
                font-size: 18px;
                font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 20;
            }

            #manual-viewer.fullscreen {
                left: 20px !important;
                top: 20px !important;
                width: calc(100vw - 40px) !important;
                height: calc(100vh - 40px) !important;
            }

            #manual-viewer.dragging {
                transition: none;
                user-select: none;
            }

            #manual-viewer.resizing {
                transition: none;
                user-select: none;
            }
        `;

        document.head.appendChild(style);
    }

    // ========================================
    // WINDOW CONTROLS
    // ========================================

    close() {
        const backdrop = document.getElementById('manual-viewer-backdrop');
        if (backdrop) {
            backdrop.remove();
        }

        this.container = null;
        this.header = null;
        this.body = null;
        this.iframe = null;

        console.log('[ManualViewer] Window closed');
    }

    toggleMinimize() {
        this.isMinimized = !this.isMinimized;

        if (this.isMinimized) {
            this.body.style.display = 'none';
            this.container.style.height = 'auto';

            // Hide resize handles when minimized
            this.container.querySelectorAll('.resize-handle').forEach(h => {
                h.style.display = 'none';
            });
        } else {
            this.body.style.display = 'block';
            this.container.style.height = this.height + 'px';

            // Show resize handles
            this.container.querySelectorAll('.resize-handle').forEach(h => {
                h.style.display = 'block';
            });
        }

        this.saveState();
    }

    toggleFullscreen() {
        this.isFullscreen = !this.isFullscreen;

        if (this.isFullscreen) {
            this.container.classList.add('fullscreen');

            // Hide resize handles in fullscreen
            this.container.querySelectorAll('.resize-handle').forEach(h => {
                h.style.display = 'none';
            });
        } else {
            this.container.classList.remove('fullscreen');

            // Restore resize handles
            if (!this.isMinimized) {
                this.container.querySelectorAll('.resize-handle').forEach(h => {
                    h.style.display = 'block';
                });
            }
        }
    }

    // ========================================
    // DRAG & DROP
    // ========================================

    attachEventListeners() {
        // Drag on header
        this.header.addEventListener('mousedown', this.onDragStart);

        // Resize on handles
        this.container.querySelectorAll('.resize-handle').forEach(handle => {
            handle.addEventListener('mousedown', this.onResizeStart);
        });
    }

    onDragStart(e) {
        if (e.target.closest('.manual-viewer-control')) return;
        if (this.isFullscreen) return;

        this.isDragging = true;
        this.container.classList.add('dragging');

        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.dragOffsetX = e.clientX - this.x;
        this.dragOffsetY = e.clientY - this.y;

        document.addEventListener('mousemove', this.onDragMove);
        document.addEventListener('mouseup', this.onDragEnd);

        e.preventDefault();
    }

    onDragMove(e) {
        if (!this.isDragging) return;

        this.x = e.clientX - this.dragOffsetX;
        this.y = e.clientY - this.dragOffsetY;

        // Constrain to viewport
        const minX = 0;
        const minY = 0;
        const maxX = window.innerWidth - 200; // Keep 200px visible
        const maxY = window.innerHeight - 50;  // Keep header visible

        this.x = Math.max(minX, Math.min(maxX, this.x));
        this.y = Math.max(minY, Math.min(maxY, this.y));

        this.container.style.left = this.x + 'px';
        this.container.style.top = this.y + 'px';
    }

    onDragEnd() {
        if (!this.isDragging) return;

        this.isDragging = false;
        this.container.classList.remove('dragging');

        document.removeEventListener('mousemove', this.onDragMove);
        document.removeEventListener('mouseup', this.onDragEnd);

        this.saveState();
    }

    // ========================================
    // RESIZE
    // ========================================

    onResizeStart(e) {
        if (this.isFullscreen || this.isMinimized) return;

        this.isResizing = true;
        this.currentResizeHandle = e.target.dataset.position;
        this.container.classList.add('resizing');

        this.resizeStartX = e.clientX;
        this.resizeStartY = e.clientY;
        this.resizeStartWidth = this.width;
        this.resizeStartHeight = this.height;
        this.resizeStartLeft = this.x;
        this.resizeStartTop = this.y;

        document.addEventListener('mousemove', this.onResizeMove);
        document.addEventListener('mouseup', this.onResizeEnd);

        e.preventDefault();
        e.stopPropagation();
    }

    onResizeMove(e) {
        if (!this.isResizing) return;

        const deltaX = e.clientX - this.resizeStartX;
        const deltaY = e.clientY - this.resizeStartY;

        const position = this.currentResizeHandle;

        // Minimum size constraints
        const minWidth = 400;
        const minHeight = 300;

        // Apply resize based on handle position
        if (position.includes('right')) {
            this.width = Math.max(minWidth, this.resizeStartWidth + deltaX);
        }

        if (position.includes('left')) {
            const newWidth = Math.max(minWidth, this.resizeStartWidth - deltaX);
            if (newWidth > minWidth) {
                this.x = this.resizeStartLeft + deltaX;
                this.width = newWidth;
            }
        }

        if (position.includes('bottom')) {
            this.height = Math.max(minHeight, this.resizeStartHeight + deltaY);
        }

        if (position.includes('top')) {
            const newHeight = Math.max(minHeight, this.resizeStartHeight - deltaY);
            if (newHeight > minHeight) {
                this.y = this.resizeStartTop + deltaY;
                this.height = newHeight;
            }
        }

        // Apply new dimensions
        this.container.style.left = this.x + 'px';
        this.container.style.top = this.y + 'px';
        this.container.style.width = this.width + 'px';
        this.container.style.height = this.height + 'px';
    }

    onResizeEnd() {
        if (!this.isResizing) return;

        this.isResizing = false;
        this.currentResizeHandle = null;
        this.container.classList.remove('resizing');

        document.removeEventListener('mousemove', this.onResizeMove);
        document.removeEventListener('mouseup', this.onResizeEnd);

        this.saveState();
    }
}

// ========================================
// GLOBAL INSTANCE
// ========================================

// Create singleton instance
window.manualViewer = new ManualViewer();

// Expose open method globally with optional chapter parameter
window.openManualViewer = (chapter = null) => {
    window.manualViewer.open(chapter);
};

console.log('[ManualViewer] Module loaded');
