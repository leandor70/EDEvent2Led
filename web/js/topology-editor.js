/**
 * Topology Editor - Multi-Zone Spatial Configuration
 */

// ============================================================================
// SCENE STATE
// ============================================================================

let availableDevices = [];   // device meta for the legend panel

// ============================================================================
// CANVAS TOPOLOGY RENDERER
// ============================================================================

class TopologyCanvas {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.zones = []; // Populated dynamically after device selection

        // Global effect center (topology-level, not per-zone)
        this.effectCenter = { x: 50, y: 50 }; // Percentuale 0-100
        // The world point the center is pinned to. Only the user moves it
        // (crosshair drag, X/Y inputs, presets): when zones move the bbox changes
        // and the percentages are recomputed so the center stays where it is.
        this.centerAnchor = null;

        // Rendering config
        this.ledSize = 20; // Pixel size per LED unit
        this.gridSize = 1; // LED units
        this.snapEnabled = true;
        this.showGrid = true;
        this.padding = 50; // Canvas padding

        // Interaction state
        this.selectedZone = null;
        this.hoveredZone = null;
        this.dragState = null;
        this.dragCenterState = null; // Stato per dragging del crosshair
        this.mousePos = { x: 0, y: 0 };

        // Camera for pan/zoom
        this.camera = { x: 0, y: 0, zoom: 1 };
        this.panState = null;
        // True while the view is the automatic fit (Reset View / page load): a
        // resize then re-fits. A manual pan or zoom turns it off.
        this.viewFitted = false;

        // Calibration overlay
        this.showCalibration = false;
        this.calibrationSpacing = 10;

        // Screen rectangle: where the monitor sits in the scene (world coords, y up).
        // rect = the one placed by hand (null = automatic); mode comes from the backend
        // ('manual' | 'auto'). aspect = width / height of the real screen: the rectangle
        // always keeps it. suggested = the backend's rectangle for Fit.
        // sceneKeys = devices the ambilight drives (backend): the automatic rectangle and
        // Fit frame only their LEDs, exactly like the backend (null = every device).
        this.screen = { rect: null, mode: 'auto', aspect: null, size: null, suggested: null, sceneKeys: null };
        this.screenDrag = null;

        this.setupEventListeners();
        this.render();
    }

    // ------------------------------------------------------------------------
    // Event Handlers
    // ------------------------------------------------------------------------

    setupEventListeners() {
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.onMouseLeave(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e), { passive: false });
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        document.addEventListener('keydown', (e) => this.onKeyDown(e));
    }

    onMouseDown(e) {
        // Middle mouse: pan
        if (e.button === 1) {
            const pos = this.getMousePos(e);
            this.panState = { startPos: pos, startCamX: this.camera.x, startCamY: this.camera.y };
            this.canvas.style.cursor = 'grabbing';
            e.preventDefault();
            return;
        }

        const screenPos = this.getMousePos(e);
        const worldPos = this.screenToWorld(screenPos);

        // Priority 1: Check if clicking on effect center crosshair
        if (this.isPointOnEffectCenter(screenPos)) {
            this.dragCenterState = {
                startCenter: { ...this.effectCenter }
            };
            this.render();
            return;
        }

        // Priority 2: the screen rectangle (corner = resize, border = move)
        const sh = this.hitScreenRect(screenPos);
        if (sh) {
            // The rectangle becomes "placed by hand" only once it is really dragged
            // (see onMouseMove): a plain click leaves an automatic rectangle automatic.
            const r0 = { ...this.effectiveScreenRect() };
            this.screenDrag = { ...sh, start: worldPos, startScreen: screenPos, r0, moved: false };
            return;
        }

        // Priority 3: Check if clicking on a zone
        const clickedZone = this.findZoneAt(worldPos);

        if (clickedZone) {
            this.selectZone(clickedZone);
            this.dragState = {
                zone: clickedZone,
                startPos: { ...clickedZone.position },
                offset: {
                    x: worldPos.x - clickedZone.position.x,
                    y: worldPos.y - clickedZone.position.y
                }
            };
        } else {
            this.selectZone(null);
        }

        this.render();
    }

    onMouseMove(e) {
        // Pan with middle mouse
        if (this.panState) {
            const pos = this.getMousePos(e);
            this.camera.x = this.panState.startCamX + (pos.x - this.panState.startPos.x);
            this.camera.y = this.panState.startCamY + (pos.y - this.panState.startPos.y);
            this.viewFitted = false;
            this.render();
            return;
        }

        const screenPos = this.getMousePos(e);
        const worldPos = this.screenToWorld(screenPos);
        this.mousePos = worldPos;

        // Update mouse position display
        document.getElementById('mouse-pos').textContent =
            `X: ${worldPos.x.toFixed(1)}, Y: ${worldPos.y.toFixed(1)}`;

        // Priority 1: Dragging effect center
        if (this.dragCenterState) {
            const bbox = this.calculateBoundingBox();
            if (bbox) {
                // Snap world position to grid (same as zones)
                let snappedX = worldPos.x;
                let snappedY = worldPos.y;

                if (this.snapEnabled) {
                    snappedX = Math.round(worldPos.x / this.gridSize) * this.gridSize;
                    snappedY = Math.round(worldPos.y / this.gridSize) * this.gridSize;
                }

                // Convert snapped world coords to percentage within bbox
                const width = bbox.max_x - bbox.min_x;
                const height = bbox.max_y - bbox.min_y;

                let newCenterX = ((snappedX - bbox.min_x) / width) * 100;
                let newCenterY = ((snappedY - bbox.min_y) / height) * 100;

                // Clamp to 0-100%
                newCenterX = Math.max(0, Math.min(100, newCenterX));
                newCenterY = Math.max(0, Math.min(100, newCenterY));

                this.effectCenter.x = newCenterX;
                this.effectCenter.y = newCenterY;
                this.anchorCenter();

                this.updateEffectCenterInputs();
                this.render();   // render() syncs the LEDs when calibrating
            }
            return;
        }

        // Priority 2: Dragging the screen rectangle
        if (this.screenDrag) {
            if (!this.screenDrag.moved) {
                const p = this.getMousePos(e), s0 = this.screenDrag.startScreen;
                if (Math.hypot(p.x - s0.x, p.y - s0.y) < 3) return;   // not a drag yet
                this.screenDrag.moved = true;
            }
            const snap = v => this.snapEnabled ? Math.round(v / this.gridSize) * this.gridSize : v;
            const d = this.screenDrag, r0 = d.r0;
            const dx = worldPos.x - d.start.x, dy = worldPos.y - d.start.y;
            const r = { ...r0 };
            if (d.type === 'move') {
                const mx = snap(r0.x_min + dx) - r0.x_min, my = snap(r0.y_min + dy) - r0.y_min;
                r.x_min += mx; r.x_max += mx; r.y_min += my; r.y_max += my;
            } else {
                // the opposite corner stays put; the size follows the larger movement
                // and keeps the proportions of the real screen
                const fx = d.cx === 'min' ? r0.x_max : r0.x_min;
                const fy = d.cy === 'min' ? r0.y_max : r0.y_min;
                const px = snap((d.cx === 'min' ? r0.x_min : r0.x_max) + dx);
                const py = snap((d.cy === 'min' ? r0.y_min : r0.y_max) + dy);
                let w = Math.max(1, d.cx === 'min' ? fx - px : px - fx);
                let h = Math.max(1, d.cy === 'min' ? fy - py : py - fy);
                const a = this.screen.aspect;
                if (a) { if (w / h > a) h = w / a; else w = h * a; }
                if (d.cx === 'min') { r.x_min = fx - w; r.x_max = fx; } else { r.x_min = fx; r.x_max = fx + w; }
                if (d.cy === 'min') { r.y_min = fy - h; r.y_max = fy; } else { r.y_min = fy; r.y_max = fy + h; }
            }
            this.screen.rect = r;
            updateScreenPanel();
            this.render();
            return;
        }

        // Priority 3: Dragging zone
        if (this.dragState) {
            let newX = worldPos.x - this.dragState.offset.x;
            let newY = worldPos.y - this.dragState.offset.y;

            // Snap to grid
            if (this.snapEnabled) {
                newX = Math.round(newX / this.gridSize) * this.gridSize;
                newY = Math.round(newY / this.gridSize) * this.gridSize;
            }

            this.dragState.zone.position.x = newX;
            this.dragState.zone.position.y = newY;

            this.updateInspector();
            this.checkOverlaps();
            this.updateBoundingBox();  // Update in real-time during drag
            this.render();
        } else {
            // Hover detection (cursor style)
            const sh = this.isPointOnEffectCenter(screenPos) ? null : this.hitScreenRect(screenPos);
            if (this.isPointOnEffectCenter(screenPos)) {
                this.canvas.style.cursor = 'grab';
            } else if (sh) {
                this.canvas.style.cursor = sh.type === 'move' ? 'move'
                    : ((sh.cx === 'min') === (sh.cy === 'max') ? 'nwse-resize' : 'nesw-resize');
                if (this.hoveredZone) { this.hoveredZone = null; this.render(); }
            } else {
                const hoveredZone = this.findZoneAt(worldPos);
                if (hoveredZone !== this.hoveredZone) {
                    this.hoveredZone = hoveredZone;
                    this.canvas.style.cursor = hoveredZone ? 'move' : 'crosshair';
                    this.render();
                }
            }
        }
    }

    onMouseUp(e) {
        if (e.button === 1 && this.panState) {
            this.panState = null;
            this.canvas.style.cursor = 'crosshair';
            return;
        }
        if (this.dragCenterState) {
            this.dragCenterState = null;
            this.canvas.style.cursor = 'crosshair';
            this.updateBoundingBox();
            this.render();
        }
        if (this.dragState) {
            this.dragState = null;
            this.updateBoundingBox();
        }
        if (this.screenDrag) {
            this.screenDrag = null;
            this.render();
        }
    }

    onMouseLeave(e) {
        this.panState = null;
        this.dragCenterState = null;
        this.dragState = null;
        this.screenDrag = null;
        this.hoveredZone = null;
        this.canvas.style.cursor = 'crosshair';
        this.render();
    }

    onWheel(e) {
        e.preventDefault();
        const mousePos = this.getMousePos(e);
        const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
        const newZoom = Math.max(0.1, Math.min(8, this.camera.zoom * zoomFactor));

        // Keep world point under mouse fixed: camera.x_new = mousePos.x - baseX * newZoom
        const baseX = (mousePos.x - this.camera.x) / this.camera.zoom;
        const baseY = (mousePos.y - this.camera.y) / this.camera.zoom;
        this.camera.x = mousePos.x - baseX * newZoom;
        this.camera.y = mousePos.y - baseY * newZoom;
        this.camera.zoom = newZoom;
        this.viewFitted = false;

        this.updateZoomDisplay();
        this.render();
    }

    resetCamera() {
        this.viewFitted = true;
        // Frame everything the editor draws: zones, the effects' virtual bbox
        // (symmetric around the effect center) and the screen rectangle.
        let bbox = this.calculateBoundingBox();
        if (bbox) {
            const extra = [this.calculateVirtualBBox()];
            const sr = this.effectiveScreenRect ? this.effectiveScreenRect() : null;
            if (sr) extra.push({ min_x: sr.x_min, max_x: sr.x_max, min_y: sr.y_min, max_y: sr.y_max });
            for (const b of extra) {
                if (!b) continue;
                bbox = {
                    min_x: Math.min(bbox.min_x, b.min_x), max_x: Math.max(bbox.max_x, b.max_x),
                    min_y: Math.min(bbox.min_y, b.min_y), max_y: Math.max(bbox.max_y, b.max_y),
                };
            }
        }

        if (!bbox || this.zones.length === 0) {
            this.camera = { x: 0, y: 0, zoom: 1 };
            this.updateZoomDisplay();
            this.render();
            return;
        }

        // Bbox center and size in base pixels (zoom=1, cam=0)
        const fitPad = 80;
        const cx_base = this.padding + ((bbox.min_x + bbox.max_x) / 2) * this.ledSize;
        const cy_base = this.canvas.height - this.padding - ((bbox.min_y + bbox.max_y) / 2) * this.ledSize;
        const bboxW_px = (bbox.max_x - bbox.min_x) * this.ledSize;
        const bboxH_px = (bbox.max_y - bbox.min_y) * this.ledSize;

        // Scale to fit bbox in available canvas area (at least 1 LED wide to avoid div/0)
        const availW = this.canvas.width - fitPad * 2;
        const availH = this.canvas.height - fitPad * 2;
        const zoom = Math.max(0.1, Math.min(8,
            Math.min(availW / Math.max(bboxW_px, this.ledSize),
                     availH / Math.max(bboxH_px, this.ledSize))
        ));

        // Center bbox in canvas
        this.camera = {
            x: this.canvas.width / 2 - cx_base * zoom,
            y: this.canvas.height / 2 - cy_base * zoom,
            zoom
        };

        this.updateZoomDisplay();
        this.render();
    }

    updateZoomDisplay() {
        const el = document.getElementById('zoom-level');
        if (el) el.textContent = `${Math.round(this.camera.zoom * 100)}%`;
    }

    onKeyDown(e) {
        if (!this.selectedZone) return;

        // R / Shift+R: Rotate (90° snapping)
        if (e.key === 'r' || e.key === 'R') {
            const increment = e.shiftKey ? -90 : 90;
            this.selectedZone.rotation = (this.selectedZone.rotation + increment + 360) % 360;
            this.checkOverlaps();
            this.updateBoundingBox();
            this.updateInspector();
            this.render();
        }

        // F: Flip direction
        if (e.key === 'f' || e.key === 'F') {
            this.selectedZone.direction = this.selectedZone.direction === 'forward' ? 'reverse' : 'forward';
            this.updateInspector();
            this.render();
        }

        // Arrow keys: Nudge
        const nudgeAmount = e.shiftKey ? 0.1 : 1;
        switch(e.key) {
            case 'ArrowLeft':
                this.selectedZone.position.x -= nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
            case 'ArrowRight':
                this.selectedZone.position.x += nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
            case 'ArrowUp':
                this.selectedZone.position.y += nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
            case 'ArrowDown':
                this.selectedZone.position.y -= nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
        }
    }

    // ------------------------------------------------------------------------
    // Rendering
    // ------------------------------------------------------------------------

    // Pin the center to the world point its current percentages point at.
    // Call after the USER sets the center (drag, inputs, presets, load).
    anchorCenter() {
        this.centerAnchor = this._calibrationCenter();
    }

    // Zones moved => bbox changed: recompute the percentages so the center keeps
    // its world position. Clamped to 0-100 (the saved format); the anchor itself
    // is kept, so the center comes back if the bbox grows again.
    _followCenterAnchor() {
        if (!this.centerAnchor) return;
        const bbox = this.calculateBoundingBox();
        if (!bbox) return;
        const w = bbox.max_x - bbox.min_x;
        const h = bbox.max_y - bbox.min_y;
        if (w <= 0 || h <= 0) return;
        const clamp = v => Math.max(0, Math.min(100, v));
        const x = clamp((this.centerAnchor.x - bbox.min_x) / w * 100);
        const y = clamp((this.centerAnchor.y - bbox.min_y) / h * 100);
        if (Math.abs(x - this.effectCenter.x) < 1e-9 && Math.abs(y - this.effectCenter.y) < 1e-9) return;
        this.effectCenter = { x, y };
        this.updateEffectCenterInputs();
    }

    render() {
        this._followCenterAnchor();
        this.clear();

        if (this.showGrid) {
            this.drawGrid();
        }

        // Screen rectangle under the zones
        this.drawScreenRect();

        // Draw zones (unselected first, selected last for z-order)
        const unselected = this.zones.filter(z => z !== this.selectedZone);
        const selected = this.zones.filter(z => z === this.selectedZone);

        unselected.forEach(zone => this.drawZone(zone, false, zone === this.hoveredZone));
        selected.forEach(zone => this.drawZone(zone, true, false));

        // Calibration overlay (above zones, below bboxes and crosshair)
        this.drawCalibrationOverlay();

        // Draw Virtual BBox first (background layer)
        this.drawVirtualBBox();

        // Draw standard BBox (foreground layer)
        this.drawBoundingBox();

        // Draw effect center (always visible on global bbox)
        this.drawEffectCenter();

        // Every visible change (center inputs, presets, drags, rotate/flip,
        // inspector, spacing) passes through here: keep the LEDs in sync.
        if (this.showCalibration) this._syncHardwareCalibration();
    }

    // Restart the hardware calibration only when what it would show changes
    // (a hover re-render must not restart it).
    _syncHardwareCalibration() {
        const plan = this.calibrationPlan();
        const sig = plan ? JSON.stringify(plan.leds) : '';
        if (sig === this._calibSig) return;
        this._calibSig = sig;
        triggerHardwareCalibration();
    }

    clear() {
        this.ctx.fillStyle = '#0a0a0c';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    drawGrid() {
        const gridSpacing = this.gridSize * this.ledSize;
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Compute visible range in base coords (before camera)
        const baseX0 = (0 - this.camera.x) / this.camera.zoom;
        const baseX1 = (width - this.camera.x) / this.camera.zoom;
        const baseY0 = (0 - this.camera.y) / this.camera.zoom;
        const baseY1 = (height - this.camera.y) / this.camera.zoom;

        const startX = Math.floor(baseX0 / gridSpacing) * gridSpacing;
        const startY = Math.floor(baseY0 / gridSpacing) * gridSpacing;

        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        this.ctx.lineWidth = 1;

        for (let bx = startX; bx <= baseX1; bx += gridSpacing) {
            const sx = bx * this.camera.zoom + this.camera.x;
            this.ctx.beginPath();
            this.ctx.moveTo(sx, 0);
            this.ctx.lineTo(sx, height);
            this.ctx.stroke();
        }

        for (let by = startY; by <= baseY1; by += gridSpacing) {
            const sy = by * this.camera.zoom + this.camera.y;
            this.ctx.beginPath();
            this.ctx.moveTo(0, sy);
            this.ctx.lineTo(width, sy);
            this.ctx.stroke();
        }
    }

    // Slot (0 = the zone's anchor end) where LED i sits. Flip ("reverse") means the
    // zone is wired the other way round: LED 0 is at the far end. Same rule as the
    // backend (effects/topology_geometry.py::led_world_position), so effects,
    // calibration and ambilight all follow what is drawn.
    _slot(zone, i) { return zone.direction === 'reverse' ? zone.led_count - 1 - i : i; }

    // World-space centre of a LED (y up) = the centre of the square drawn by
    // drawZone: local ((slot + 0.5) * spacing, -0.5), rotated by the (continuous)
    // rotation. Single source of truth for calibration, screen rectangle and per-LED view.
    _ledWorldPos(zone, ledIndex) {
        const ledSpacing = zone.led_spacing ?? 1.0;
        const lx_local = (this._slot(zone, ledIndex) + 0.5) * ledSpacing;
        const ly_local = -0.5;
        const rad = zone.rotation * Math.PI / 180;
        return {
            x: zone.position.x + lx_local * Math.cos(rad) - ly_local * Math.sin(rad),
            y: zone.position.y + lx_local * Math.sin(rad) + ly_local * Math.cos(rad),
        };
    }

    // Effect center in world coordinates (percentages of the drawn scene bbox).
    _calibrationCenter() {
        const bbox = this.calculateBoundingBox();
        if (!bbox) return null;
        return {
            x: bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100),
            y: bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100),
        };
    }

    _calibrationColor(zone, ledIndex) {
        // Returns CSS color string for a LED based on its distance from the effect center.
        const RING_COLORS = ['#FFFFFF', '#FF3C3C', '#507FFF', '#3CD250'];
        const c = this._calibrationCenter();
        if (!c) return zone.color;
        const { x: wx, y: wy } = this._ledWorldPos(zone, ledIndex);
        const ringIdx = Math.floor(Math.hypot(wx - c.x, wy - c.y) / (this.calibrationSpacing || 10));
        return RING_COLORS[ringIdx % 4];
    }

    // What the hardware calibration shows, computed from what is DRAWN (live
    // zones, unsaved edits included, only the devices in this scene): ring of
    // every LED and the center LED (the one nearest the effect center). The
    // backend only maps each entry to its physical LED, so LEDs and canvas
    // cannot disagree.
    calibrationPlan() {
        const c = this._calibrationCenter();
        if (!c) return null;
        const spacing = this.calibrationSpacing || 10;
        const zones = [];
        const leds = [];
        let best = null;
        for (const z of this.zones) {
            if (!z.device_id || !z.position || !(z.led_count > 0)) continue;
            zones.push({ device_id: z.device_id, zone_index: z.zone_index, led_count: z.led_count });
            for (let i = 0; i < z.led_count; i++) {
                const p = this._ledWorldPos(z, i);
                const d = Math.hypot(p.x - c.x, p.y - c.y);
                const led = { device_id: z.device_id, zone_index: z.zone_index, led_index: i,
                              ring: Math.floor(d / spacing), center: false };
                leds.push(led);
                if (!best || d < best.d) best = { d, led, p };
            }
        }
        if (best) best.led.center = true;
        return { zones, leds, centerPos: best ? best.p : null };
    }

    drawZone(zone, isSelected, isHovered) {
        if (!zone.position || zone.led_count <= 0) return;
        const { x, y } = this.worldToScreen(zone.position);
        const ledSpacing = zone.led_spacing ?? 1.0;
        const eff = this.ledSize * this.camera.zoom; // effective LED size in screen pixels
        const ledWidth = eff;                         // strip depth (1 unit)
        // Each LED owns a cell as long as its spacing: the cells tile the strip
        // (___|___|___) and the cell centre is the LED's world position
        // (_ledWorldPos: (slot + 0.5) * spacing), the point every backend uses.
        const cellW = eff * ledSpacing;

        const kinds = this.showCalibration ? null : this.ledKinds(zone);

        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(-zone.rotation * Math.PI / 180);

        for (let i = 0; i < zone.led_count; i++) {
            const ledX = this._slot(zone, i) * cellW;
            const midX = ledX + cellW / 2;
            const off = kinds && kinds[i] === 'off';

            this.ctx.fillStyle = this.showCalibration ? this._calibrationColor(zone, i) : zone.color;
            this.ctx.globalAlpha = this.showCalibration ? 0.9 : off ? 0.12 : (isSelected ? 0.8 : (isHovered ? 0.6 : 0.5));
            this.ctx.fillRect(ledX, 0, cellW, ledWidth);
            if (kinds && kinds[i] === 'area') {              // reads the point of the screen under it
                this.ctx.globalAlpha = 0.85;
                this.ctx.fillStyle = '#FFFFFF';
                this.ctx.beginPath();
                this.ctx.arc(midX, ledWidth / 2, Math.max(1.5, ledWidth * 0.12), 0, Math.PI * 2);
                this.ctx.fill();
            }

            this.ctx.globalAlpha = 1;
            this.ctx.strokeStyle = isSelected ? '#FF6600' : '#666666';
            this.ctx.lineWidth = 1;
            this.ctx.strokeRect(ledX, 0, cellW, ledWidth);   // shared borders = the | separators

            if (i === 0 || i === zone.led_count - 1) {
                this.ctx.fillStyle = '#FFFFFF';
                this.ctx.font = `${Math.max(7, 9 * this.camera.zoom)}px Rajdhani`;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.globalAlpha = 0.6;
                this.ctx.fillText(i.toString(), midX, ledWidth / 2);
            }
        }

        this.drawDirectionArrow(zone, eff);

        // Zone label (fixed screen size, always readable)
        this.ctx.globalAlpha = 1;
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.font = 'bold 11px Rajdhani';
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'top';
        this.ctx.fillText(zone.name, 0, -16);

        if (isSelected || isHovered) {
            const outlineWidth = zone.led_count * eff * ledSpacing;
            this.ctx.strokeStyle = isSelected ? '#FF6600' : '#FFFFFF';
            this.ctx.lineWidth = 1;
            this.ctx.globalAlpha = isSelected ? 1 : 0.5;
            this.ctx.strokeRect(-5, -5, outlineWidth + 10, ledWidth + 10);
        }

        if (zone.hasOverlap) {
            const outlineWidth = zone.led_count * eff * ledSpacing;
            this.ctx.strokeStyle = '#FF0000';
            this.ctx.lineWidth = 3;
            this.ctx.globalAlpha = 0.8;
            this.ctx.setLineDash([5, 5]);
            this.ctx.strokeRect(-7, -7, outlineWidth + 14, ledWidth + 14);
            this.ctx.setLineDash([]);
        }

        this.ctx.restore();
    }

    drawDirectionArrow(zone, eff = this.ledSize) {
        const ledSpacing = zone.led_spacing ?? 1.0;
        const arrowLedIndex = zone.direction === 'forward' ? zone.led_count - 1 : 0;
        // Centre of the end cell (cells are spacing wide, see drawZone)
        const arrowX = (arrowLedIndex + 0.5) * eff * ledSpacing;
        const arrowY = eff / 2;

        this.ctx.fillStyle = '#FFFF00';
        this.ctx.globalAlpha = 1;

        // Triangle arrow pointing in direction of flow
        const arrowSize = Math.max(4, 6 * this.camera.zoom);
        this.ctx.beginPath();
        if (zone.direction === 'forward') {
            // Arrow pointing right
            this.ctx.moveTo(arrowX + arrowSize, arrowY);
            this.ctx.lineTo(arrowX - arrowSize, arrowY - arrowSize);
            this.ctx.lineTo(arrowX - arrowSize, arrowY + arrowSize);
        } else {
            // Arrow pointing left
            this.ctx.moveTo(arrowX - arrowSize, arrowY);
            this.ctx.lineTo(arrowX + arrowSize, arrowY - arrowSize);
            this.ctx.lineTo(arrowX + arrowSize, arrowY + arrowSize);
        }
        this.ctx.closePath();
        this.ctx.fill();

        // Arrow outline
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 1;
        this.ctx.stroke();
    }

    // ── Screen rectangle ────────────────────────────────────────────────────
    // Same rule as the backend (effects/ambilight_service.py): a LED near a side of
    // the rectangle reads that side of the screen, inside it reads the point of the
    // screen under it, outside it stays off. The zone names decide nothing: only
    // where the LEDs are (the centres of the drawn squares, see _ledWorldPos).

    _ledPoints(zone) {
        const pts = [];
        for (let i = 0; i < zone.led_count; i++) pts.push(this._ledWorldPos(zone, i));
        return pts;
    }

    // Rectangle around the LEDs of the devices the ambilight drives (all devices when
    // none is on), grown to the screen proportions. Same rule as the backend
    // (ambilight_service.screen_frame / suggest_screen_rect), on the zones as they are
    // NOW in the editor, so it follows a zone while it is dragged.
    sceneScreenRect() {
        const keys = this.screen.sceneKeys;
        const zones = keys ? this.zones.filter(z => keys.includes(z.device_id)) : this.zones;
        const pts = zones.flatMap(z => this._ledPoints(z));
        if (!pts.length) return null;
        const r = {
            x_min: Math.min(...pts.map(p => p.x)), x_max: Math.max(...pts.map(p => p.x)),
            y_min: Math.min(...pts.map(p => p.y)), y_max: Math.max(...pts.map(p => p.y)),
        };
        return (r.x_max - r.x_min > 0 && r.y_max - r.y_min > 0) ? this.fitAspect(r) : null;
    }

    // Automatic rectangle (nothing placed by hand): the scene as it is now
    autoScreenRect() { return this.sceneScreenRect(); }

    // Starting rectangle for Fit: computed from the zones as they are now (the
    // backend's `suggested` is only the state at page load).
    fitScreenRect() { return this.sceneScreenRect(); }

    // Grow the rectangle around its centre to the real screen proportions (never shrink)
    fitAspect(r) {
        const a = this.screen.aspect;
        const w = r.x_max - r.x_min, h = r.y_max - r.y_min;
        if (!a || w <= 0 || h <= 0) return r;
        if (w / h < a) { const g = (h * a - w) / 2; return { ...r, x_min: r.x_min - g, x_max: r.x_max + g }; }
        const g = (w / a - h) / 2;
        return { ...r, y_min: r.y_min - g, y_max: r.y_max + g };
    }

    effectiveScreenRect() { return this.screen.rect || this.autoScreenRect(); }

    // Within the band ACROSS a side, and within its length ALONG it (+- reach, half
    // a LED): past a corner a LED is outside. Mirrors _classify_led (backend, band 15%).
    _classifyLed(p, r, axis, reach = 0.5) {
        const w = r.x_max - r.x_min, h = r.y_max - r.y_min;
        const band = Math.max(1, 0.15 * Math.min(w, h));
        const d = { left: p.x - r.x_min, right: r.x_max - p.x, top: r.y_max - p.y, bottom: p.y - r.y_min };
        const inX = p.x >= r.x_min - reach && p.x <= r.x_max + reach;
        const inY = p.y >= r.y_min - reach && p.y <= r.y_max + reach;
        let near = Object.keys(d).filter(k => Math.abs(d[k]) <= band && ((k === 'top' || k === 'bottom') ? inX : inY));
        if (axis) near = near.filter(k => (k === 'top' || k === 'bottom') === (axis === 'x'));   // only sides parallel to the strip
        if (near.length) return near.reduce((a, b) => Math.abs(d[a]) <= Math.abs(d[b]) ? a : b);
        return (p.x >= r.x_min && p.x <= r.x_max && p.y >= r.y_min && p.y <= r.y_max) ? 'area' : 'off';
    }

    // Per LED: 'top' | 'right' | 'bottom' | 'left' | 'area' | 'off', or null when there is no rectangle
    ledKinds(zone) {
        const r = this.effectiveScreenRect();
        if (!r) return null;
        const pts = this._ledPoints(zone);
        let axis = null;
        if (pts.length > 1) {
            const a = pts[0], b = pts[pts.length - 1];
            axis = Math.abs(b.x - a.x) >= Math.abs(b.y - a.y) ? 'x' : 'y';
        }
        const reach = Math.max(0.5, (zone.led_spacing ?? 1.0) / 2);
        return pts.map(p => this._classifyLed(p, r, axis, reach));
    }

    _screenCorners(r) {
        return {
            tl: this.worldToScreen({ x: r.x_min, y: r.y_max }),
            br: this.worldToScreen({ x: r.x_max, y: r.y_min }),
        };
    }

    drawScreenRect() {
        const r = this.effectiveScreenRect();
        if (!r) return;
        const { tl, br } = this._screenCorners(r);
        const manual = !!this.screen.rect;
        const acc = '0, 200, 255';
        const w = br.x - tl.x, h = br.y - tl.y;
        this.ctx.save();
        this.ctx.fillStyle = `rgba(${acc}, ${manual ? 0.07 : 0.04})`;
        this.ctx.fillRect(tl.x, tl.y, w, h);
        this.ctx.strokeStyle = `rgba(${acc}, ${this.screenDrag ? 1 : 0.75})`;
        this.ctx.lineWidth = 2;
        if (!manual) this.ctx.setLineDash([6, 4]);
        this.ctx.strokeRect(tl.x, tl.y, w, h);
        this.ctx.setLineDash([]);
        this.ctx.fillStyle = `rgba(${acc}, 0.9)`;
        this.ctx.font = 'bold 11px Rajdhani';
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'bottom';
        this.ctx.fillText(manual ? screenText('screen_label', 'SCREEN') : screenText('screen_label_auto', 'SCREEN (automatic)'),
                          tl.x + 2, tl.y - 4);
        for (const [cx, cy] of [[tl.x, tl.y], [br.x, tl.y], [tl.x, br.y], [br.x, br.y]]) {
            this.ctx.fillStyle = '#0a0a0c';
            this.ctx.fillRect(cx - 5, cy - 5, 10, 10);
            this.ctx.strokeStyle = `rgba(${acc}, 0.95)`;
            this.ctx.lineWidth = 1.5;
            this.ctx.strokeRect(cx - 5, cy - 5, 10, 10);
        }
        this.ctx.restore();
    }

    // {type:'corner', cx:'min'|'max', cy:'min'|'max'} | {type:'move'} | null
    hitScreenRect(screenPos) {
        const r = this.effectiveScreenRect();
        if (!r) return null;
        const { tl, br } = this._screenCorners(r);
        const near = (a, b) => Math.abs(a - b) <= 7;
        // A selected zone under the pointer keeps the click (its corner LEDs often sit
        // right on a corner of the rectangle): select the zone elsewhere, then drag it.
        const sel = this.selectedZone;
        const onSelected = sel && this.isPointInZone(this.screenToWorld(screenPos), sel);
        if (!onSelected) for (const [px, cx] of [[tl.x, 'min'], [br.x, 'max']]) {
            for (const [py, cy] of [[tl.y, 'max'], [br.y, 'min']]) {
                if (near(screenPos.x, px) && near(screenPos.y, py)) return { type: 'corner', cx, cy };
            }
        }
        const inX = screenPos.x >= tl.x - 5 && screenPos.x <= br.x + 5;
        const inY = screenPos.y >= tl.y - 5 && screenPos.y <= br.y + 5;
        const onV = inY && (Math.abs(screenPos.x - tl.x) <= 5 || Math.abs(screenPos.x - br.x) <= 5);
        const onH = inX && (Math.abs(screenPos.y - tl.y) <= 5 || Math.abs(screenPos.y - br.y) <= 5);
        // a zone drawn on the border keeps its clicks: the border moves only where no LED is
        if ((onV || onH) && !this.findZoneAt(this.screenToWorld(screenPos))) return { type: 'move' };
        return null;
    }

    drawVirtualBBox() {
        const vbbox = this.calculateVirtualBBox();
        if (!vbbox) return;

        const topLeft = this.worldToScreen({ x: vbbox.min_x, y: vbbox.max_y });
        const bottomRight = this.worldToScreen({ x: vbbox.max_x, y: vbbox.min_y });

        const width = bottomRight.x - topLeft.x;
        const height = bottomRight.y - topLeft.y;

        // Fill with semi-transparent gray
        this.ctx.fillStyle = 'rgba(128, 128, 128, 0.15)';
        this.ctx.fillRect(topLeft.x, topLeft.y, width, height);

        // Dashed gray border
        this.ctx.strokeStyle = 'rgba(128, 128, 128, 0.4)';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([8, 4]);
        this.ctx.strokeRect(topLeft.x, topLeft.y, width, height);
        this.ctx.setLineDash([]);

        // VBBox label
        this.ctx.fillStyle = 'rgba(128, 128, 128, 0.7)';
        this.ctx.font = '10px Rajdhani';
        this.ctx.fillText(
            `VBBox: ${(vbbox.max_x - vbbox.min_x).toFixed(1)} × ${(vbbox.max_y - vbbox.min_y).toFixed(1)}`,
            topLeft.x,
            topLeft.y - 5
        );
    }

    drawBoundingBox() {
        const bbox = this.calculateBoundingBox();
        if (!bbox) return;

        const topLeft = this.worldToScreen({ x: bbox.min_x, y: bbox.max_y });
        const bottomRight = this.worldToScreen({ x: bbox.max_x, y: bbox.min_y });

        const width = bottomRight.x - topLeft.x;
        const height = bottomRight.y - topLeft.y;

        this.ctx.strokeStyle = 'rgba(255, 102, 0, 0.3)';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([10, 5]);
        this.ctx.strokeRect(topLeft.x, topLeft.y, width, height);
        this.ctx.setLineDash([]);

        // BBox label
        this.ctx.fillStyle = 'rgba(255, 102, 0, 0.6)';
        this.ctx.font = '10px Rajdhani';
        this.ctx.fillText(
            `BBox: ${(bbox.max_x - bbox.min_x).toFixed(1)} × ${(bbox.max_y - bbox.min_y).toFixed(1)}`,
            topLeft.x,
            topLeft.y - 5
        );
    }

    drawEffectCenter() {
        // Always visible - renders on global bbox
        const bbox = this.calculateBoundingBox();
        if (!bbox) return;

        // Calcola world position del centro dalla bbox globale
        const cx_world = bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100);
        const cy_world = bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100);
        const screenPos = this.worldToScreen({ x: cx_world, y: cy_world });

        // Disegna crosshair cyan (più grande e visibile)
        this.ctx.strokeStyle = this.dragCenterState ? '#00FFFF' : 'rgba(0, 255, 255, 0.8)';
        this.ctx.lineWidth = this.dragCenterState ? 3 : 2;
        const size = 15;

        // Linee verticale e orizzontale
        this.ctx.beginPath();
        this.ctx.moveTo(screenPos.x - size, screenPos.y);
        this.ctx.lineTo(screenPos.x + size, screenPos.y);
        this.ctx.moveTo(screenPos.x, screenPos.y - size);
        this.ctx.lineTo(screenPos.x, screenPos.y + size);
        this.ctx.stroke();

        // Centro dot (draggable handle)
        this.ctx.fillStyle = this.dragCenterState ? '#00FFFF' : 'rgba(0, 255, 255, 0.7)';
        this.ctx.beginPath();
        this.ctx.arc(screenPos.x, screenPos.y, 6, 0, Math.PI * 2);
        this.ctx.fill();

        // Outer ring per highlight durante drag
        if (this.dragCenterState) {
            this.ctx.strokeStyle = 'rgba(0, 255, 255, 0.3)';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.arc(screenPos.x, screenPos.y, 10, 0, Math.PI * 2);
            this.ctx.stroke();
        }
    }

    drawCalibrationOverlay() {
        if (!this.showCalibration) return;
        const bbox = this.calculateBoundingBox();
        if (!bbox) return;

        const RING_COLORS = [
            [255, 255, 255],  // white
            [255,  60,  60],  // red
            [ 80, 140, 255],  // blue
            [ 60, 210,  70],  // green
        ];

        // Effect center in screen space
        const cx_w = bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100);
        const cy_w = bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100);
        const cs = this.worldToScreen({ x: cx_w, y: cy_w });

        // Ring spacing in screen pixels
        const spacingPx = this.calibrationSpacing * this.ledSize * this.camera.zoom;
        if (spacingPx < 1) return;

        // How many rings needed to cover the whole canvas
        const corners = [[0,0],[this.canvas.width,0],[0,this.canvas.height],[this.canvas.width,this.canvas.height]];
        const maxR = Math.max(...corners.map(([cx, cy]) => Math.hypot(cx - cs.x, cy - cs.y)));
        const ringCount = Math.ceil(maxR / spacingPx);

        this.ctx.save();

        // Draw rings (innermost last so inner color wins at overlap)
        for (let i = ringCount; i >= 1; i--) {
            const r = i * spacingPx;
            const [R, G, B] = RING_COLORS[(i - 1) % 4];
            this.ctx.strokeStyle = `rgba(${R},${G},${B},0.5)`;
            this.ctx.lineWidth = Math.max(1, 1.5 * this.camera.zoom);
            this.ctx.beginPath();
            this.ctx.arc(cs.x, cs.y, r, 0, Math.PI * 2);
            this.ctx.stroke();
        }

        // Distance labels: shown if zoom is readable, thinned out if many rings
        if (this.camera.zoom >= 0.25 && ringCount > 0) {
            const labelStep = ringCount > 20 ? Math.ceil(ringCount / 15) : 1;
            const fontSize = Math.max(9, Math.min(13, 10 * this.camera.zoom));
            this.ctx.font = `${fontSize}px Rajdhani`;

            // Candidate angles for label placement (right, top, left, bottom)
            const ANGLES = [0, -Math.PI / 2, Math.PI, Math.PI / 2];

            for (let i = 1; i <= ringCount; i++) {
                if (i % labelStep !== 0) continue;
                const r = i * spacingPx;
                const [R, G, B] = RING_COLORS[(i - 1) % 4];
                const label = `${i * this.calibrationSpacing}u`;
                const textW = this.ctx.measureText(label).width;
                const margin = 6;

                for (const angle of ANGLES) {
                    const lx = cs.x + (r + margin) * Math.cos(angle);
                    const ly = cs.y + (r + margin) * Math.sin(angle);
                    const hw = textW / 2 + 2;
                    if (lx - hw > 0 && lx + hw < this.canvas.width && ly > 12 && ly < this.canvas.height - 5) {
                        this.ctx.fillStyle = `rgba(${R},${G},${B},0.85)`;
                        this.ctx.textAlign = 'center';
                        this.ctx.textBaseline = 'middle';
                        this.ctx.fillText(label, lx, ly);
                        break;
                    }
                }
            }
        }

        // The center LED (the one that blinks on the hardware): white ring around it
        const plan = this.calibrationPlan();
        if (plan && plan.centerPos) {
            const lp = this.worldToScreen(plan.centerPos);
            this.ctx.strokeStyle = '#FFFFFF';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.arc(lp.x, lp.y, Math.max(6, 0.9 * this.ledSize * this.camera.zoom), 0, Math.PI * 2);
            this.ctx.stroke();
        }

        // Center dot — solid white with glow
        this.ctx.shadowColor = 'rgba(255,255,255,0.9)';
        this.ctx.shadowBlur = 8;
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.beginPath();
        this.ctx.arc(cs.x, cs.y, Math.max(4, 5 * Math.min(1, this.camera.zoom)), 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;

        this.ctx.restore();
    }

    isPointOnEffectCenter(screenPos) {
        // Controlla se il click è sul crosshair (handle draggable)
        const bbox = this.calculateBoundingBox();
        if (!bbox) return false;

        const cx_world = bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100);
        const cy_world = bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100);
        const centerScreen = this.worldToScreen({ x: cx_world, y: cy_world });

        const dx = screenPos.x - centerScreen.x;
        const dy = screenPos.y - centerScreen.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        return distance <= 10; // 10px hit radius
    }

    // ------------------------------------------------------------------------
    // Coordinate Transforms
    // ------------------------------------------------------------------------

    worldToScreen(worldPos) {
        // World → base pixels → screen (apply camera)
        const baseX = this.padding + worldPos.x * this.ledSize;
        const baseY = this.canvas.height - this.padding - worldPos.y * this.ledSize;
        return {
            x: baseX * this.camera.zoom + this.camera.x,
            y: baseY * this.camera.zoom + this.camera.y
        };
    }

    screenToWorld(screenPos) {
        // Screen → base pixels (undo camera) → world
        const baseX = (screenPos.x - this.camera.x) / this.camera.zoom;
        const baseY = (screenPos.y - this.camera.y) / this.camera.zoom;
        return {
            x: (baseX - this.padding) / this.ledSize,
            y: (this.canvas.height - this.padding - baseY) / this.ledSize
        };
    }

    getMousePos(e) {
        // clientLeft/Top = border width: canvas pixels start inside the border.
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left - this.canvas.clientLeft,
            y: e.clientY - rect.top - this.canvas.clientTop
        };
    }

    // Keep the canvas pixel size equal to its displayed size (CSS fills the
    // container). World y grows from the bottom edge (height - padding), so a
    // height change would slide the scene: the camera is shifted so the point at
    // the centre of the view stays at the centre.
    resizeToContainer() {
        const w = Math.max(100, this.canvas.clientWidth);
        const h = Math.max(100, this.canvas.clientHeight);
        const dW = w - this.canvas.width;
        const dH = h - this.canvas.height;
        if (dW === 0 && dH === 0) return;
        this.canvas.width = w;
        this.canvas.height = h;
        if (this.viewFitted) {
            this.resetCamera();
            return;
        }
        this.camera.x += dW / 2;
        this.camera.y += dH / 2 - dH * this.camera.zoom;
        this.render();
    }

    // ------------------------------------------------------------------------
    // Zone Hit Detection
    // ------------------------------------------------------------------------

    findZoneAt(worldPos) {
        // Check zones in reverse order (last drawn = top z-order)
        for (let i = this.zones.length - 1; i >= 0; i--) {
            const zone = this.zones[i];
            if (this.isPointInZone(worldPos, zone)) {
                return zone;
            }
        }
        return null;
    }

    isPointInZone(worldPos, zone) {
        // Transform point to zone local space
        const dx = worldPos.x - zone.position.x;
        const dy = worldPos.y - zone.position.y;

        // Rotate point by -zone.rotation
        const rad = -zone.rotation * Math.PI / 180;
        const localX = dx * Math.cos(rad) - dy * Math.sin(rad);
        const localY = dx * Math.sin(rad) + dy * Math.cos(rad);

        // Check if inside zone bounding box (local space)
        const zoneWidth = zone.led_count * (zone.led_spacing ?? 1.0);
        return localX >= 0 && localX <= zoneWidth &&
               localY >= -1 && localY <= 0;
    }

    // ------------------------------------------------------------------------
    // Utilities
    // ------------------------------------------------------------------------

    selectZone(zone) {
        this.selectedZone = zone;
        this.updateZonesList();
        this.updateInspector();
    }

    calculateBoundingBox() {
        if (this.zones.length === 0) return null;

        let min_x = Infinity, min_y = Infinity;
        let max_x = -Infinity, max_y = -Infinity;

        this.zones.forEach(zone => {
            const corners = this.getZoneCorners(zone);
            corners.forEach(corner => {
                min_x = Math.min(min_x, corner.x);
                min_y = Math.min(min_y, corner.y);
                max_x = Math.max(max_x, corner.x);
                max_y = Math.max(max_y, corner.y);
            });
        });

        return { min_x, min_y, max_x, max_y };
    }

    calculateVirtualBBox() {
        const standardBbox = this.calculateBoundingBox();
        if (!standardBbox) return null;

        // Convert effect center percentage to normalized [0,1]
        const cx_norm = Math.max(0.0, Math.min(1.0, this.effectCenter.x / 100.0));
        const cy_norm = Math.max(0.0, Math.min(1.0, this.effectCenter.y / 100.0));

        // Convert to world coords
        const width = standardBbox.max_x - standardBbox.min_x;
        const height = standardBbox.max_y - standardBbox.min_y;
        const cx_world = standardBbox.min_x + cx_norm * width;
        const cy_world = standardBbox.min_y + cy_norm * height;

        // Calculate symmetric expansion
        const dist_left = cx_world - standardBbox.min_x;
        const dist_right = standardBbox.max_x - cx_world;
        const dist_bottom = cy_world - standardBbox.min_y;
        const dist_top = standardBbox.max_y - cy_world;

        const half_width = Math.max(dist_left, dist_right);
        const half_height = Math.max(dist_bottom, dist_top);

        // Apply 10% padding (5% per side to total 10%)
        const padding_x = half_width * 0.05;
        const padding_y = half_height * 0.05;

        return {
            min_x: cx_world - half_width - padding_x,
            min_y: cy_world - half_height - padding_y,
            max_x: cx_world + half_width + padding_x,
            max_y: cy_world + half_height + padding_y,
            center_world: { x: cx_world, y: cy_world }
        };
    }

    getZoneCorners(zone) {
        const w = zone.led_count * (zone.led_spacing ?? 1.0);
        const corners = [
            { x: 0, y: -1 },  // bottom-left
            { x: w,  y: -1 }, // bottom-right
            { x: w,  y: 0  }, // top-right
            { x: 0,  y: 0  }  // top-left
        ];

        // Rotate corners
        const rad = zone.rotation * Math.PI / 180;
        return corners.map(c => ({
            x: zone.position.x + (c.x * Math.cos(rad) - c.y * Math.sin(rad)),
            y: zone.position.y + (c.x * Math.sin(rad) + c.y * Math.cos(rad))
        }));
    }

    checkOverlaps() {
        // Reset overlap flags
        this.zones.forEach(z => z.hasOverlap = false);

        // Check all pairs
        for (let i = 0; i < this.zones.length; i++) {
            for (let j = i + 1; j < this.zones.length; j++) {
                if (this.zonesOverlap(this.zones[i], this.zones[j])) {
                    this.zones[i].hasOverlap = true;
                    this.zones[j].hasOverlap = true;
                }
            }
        }

        // Show/hide warning
        const hasAnyOverlap = this.zones.some(z => z.hasOverlap);
        document.getElementById('overlap-warning').classList.toggle('hidden', !hasAnyOverlap);
    }

    zonesOverlap(zone1, zone2) {
        const corners1 = this.getZoneCorners(zone1);
        const corners2 = this.getZoneCorners(zone2);

        // Simple AABB overlap check on rotated corners
        const bbox1 = {
            min_x: Math.min(...corners1.map(c => c.x)),
            max_x: Math.max(...corners1.map(c => c.x)),
            min_y: Math.min(...corners1.map(c => c.y)),
            max_y: Math.max(...corners1.map(c => c.y))
        };

        const bbox2 = {
            min_x: Math.min(...corners2.map(c => c.x)),
            max_x: Math.max(...corners2.map(c => c.x)),
            min_y: Math.min(...corners2.map(c => c.y)),
            max_y: Math.max(...corners2.map(c => c.y))
        };

        // Allow edge-to-edge contact (<=) instead of requiring gap (<)
        // This prevents false positives when zones are adjacent but not overlapping
        return !(bbox1.max_x <= bbox2.min_x || bbox1.min_x >= bbox2.max_x ||
                 bbox1.max_y <= bbox2.min_y || bbox1.min_y >= bbox2.max_y);
    }

    updateBoundingBox() {
        const bbox = this.calculateBoundingBox();
        if (bbox) {
            const width = (bbox.max_x - bbox.min_x).toFixed(1);
            const height = (bbox.max_y - bbox.min_y).toFixed(1);
            document.getElementById('bbox-info').textContent = `BBox: ${width}×${height}`;
        }

        // Update Virtual BBox (expanded based on effect center)
        const vbbox = this.calculateVirtualBBox();
        if (vbbox) {
            const vwidth = (vbbox.max_x - vbbox.min_x).toFixed(1);
            const vheight = (vbbox.max_y - vbbox.min_y).toFixed(1);
            document.getElementById('vbbox-info').textContent = `VBBox: ${vwidth}×${vheight}`;
        }
    }

    updateZonesList() {
        const list = document.getElementById('zones-list');

        // Group zones by device_id for display
        const byDevice = {};
        this.zones.forEach(zone => {
            const did = zone.device_id || 'unknown';
            if (!byDevice[did]) byDevice[did] = [];
            byDevice[did].push(zone);
        });

        // Build device group display names from availableDevices lookup
        const deviceNames = {};
        availableDevices.forEach(d => { deviceNames[d.device_id] = d.name; });

        list.innerHTML = Object.entries(byDevice).map(([did, zones]) => {
            const label = deviceNames[did] || did.split('::')[0];
            return `
                <div class="mb-3">
                    <div class="text-[10px] text-white/40 uppercase tracking-widest mb-1 px-1">${label}</div>
                    ${zones.map(zone => {
                        const uid = `${zone.device_id}::${zone.zone_index}`;
                        return `
                        <div class="zone-card p-2 border rounded text-xs mb-1 ${zone === this.selectedZone ? 'selected' : ''}"
                             data-zone-uid="${uid}"
                             style="border-color: ${zone.color};">
                            <div class="font-bold" style="color: ${zone.color};">${zone.name}</div>
                            <div class="text-white/40 text-[10px]">${screenText('zone_meta', '{{count}} LEDs · {{rotation}}° · {{direction}}', {
                                count: zone.led_count, rotation: zone.rotation,
                                direction: zone.direction === 'reverse'
                                    ? screenText('dir_reverse_short', 'reverse')
                                    : screenText('dir_forward_short', 'forward') })}</div>
                        </div>`;
                    }).join('')}
                </div>`;
        }).join('');

        // Click handlers — find zone by composite uid (device_id::zone_index)
        list.querySelectorAll('.zone-card').forEach(card => {
            card.addEventListener('click', () => {
                const uid = card.dataset.zoneUid;
                const parts = uid.split('::');
                const zoneIdx = parts[parts.length - 1];
                const did = parts.slice(0, -1).join('::');
                const zone = this.zones.find(z => z.device_id === did && String(z.zone_index) === zoneIdx);
                if (zone) { this.selectZone(zone); this.render(); }
            });
        });
    }

    updateInspector() {
        const noSelection = document.getElementById('no-selection');
        const inspectorFields = document.getElementById('inspector-fields');

        if (!this.selectedZone) {
            noSelection.classList.remove('hidden');
            inspectorFields.classList.add('hidden');
            return;
        }

        noSelection.classList.add('hidden');
        inspectorFields.classList.remove('hidden');

        const zone = this.selectedZone;
        document.getElementById('zone-name').value = zone.name;
        document.getElementById('zone-x').value = zone.position.x.toFixed(1);
        document.getElementById('zone-y').value = zone.position.y.toFixed(1);

        // Update rotation buttons
        document.querySelectorAll('.rotation-btn').forEach(btn => {
            const rotation = parseInt(btn.dataset.rotation);
            if (rotation === zone.rotation) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        document.getElementById('zone-direction').value = zone.direction;
        document.getElementById('zone-device').textContent = zone.device_id;
        document.getElementById('zone-index').textContent = zone.zone_index;
        document.getElementById('zone-led-count').textContent = zone.led_count;

        // Physical length
        const physInput = document.getElementById('zone-physical-length');
        if (physInput) {
            physInput.value = zone.physical_length_cm != null ? zone.physical_length_cm : '';
            const spacingEl = document.getElementById('zone-spacing-display');
            if (spacingEl) {
                const sp = zone.led_spacing ?? 1.0;
                spacingEl.textContent = sp !== 1.0
                    ? screenText('spacing_value', '{{value}} units/LED', { value: sp.toFixed(2) })
                    : screenText('spacing_default', '1.0 (default)');
            }
        }
    }

    updateEffectCenterInputs() {
        const centerX = document.getElementById('center-x');
        const centerY = document.getElementById('center-y');

        if (centerX && centerY) {
            centerX.value = Math.round(this.effectCenter.x);
            centerY.value = Math.round(this.effectCenter.y);
        }

        // Update active preset button if values match a preset
        const presets = {
            'center': { x: 50, y: 50 },
            'top': { x: 50, y: 90 },
            'bottom': { x: 50, y: 10 },
            'left': { x: 10, y: 50 },
            'right': { x: 90, y: 50 }
        };

        let matchedPreset = null;
        for (const [name, preset] of Object.entries(presets)) {
            if (Math.abs(this.effectCenter.x - preset.x) < 0.5 &&
                Math.abs(this.effectCenter.y - preset.y) < 0.5) {
                matchedPreset = name;
                break;
            }
        }

        // Update active state on preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            if (btn.dataset.preset === matchedPreset) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    autoLayout() {
        // Group zones by device, stack devices vertically with inter-device gap
        const byDevice = {};
        this.zones.forEach(z => {
            const did = z.device_id || 'unknown';
            if (!byDevice[did]) byDevice[did] = [];
            byDevice[did].push(z);
        });

        let currentY = 5;
        const zoneGap = 2;       // gap between zones of same device
        const deviceGap = 5;     // extra gap between devices

        Object.values(byDevice).forEach((zones, devIdx) => {
            zones.forEach(zone => {
                zone.position.x = 5;
                zone.position.y = currentY;
                zone.rotation = 0;
                currentY += 1 + zoneGap;
            });
            currentY += deviceGap;  // extra space after each device group
        });

        this.updateInspector();
        this.checkOverlaps();
        this.updateBoundingBox();
        this.render();
    }

    reset() {
        this.zones = [];
        this.selectedZone = null;
        loadAndRenderScene();
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

let canvas;

// Calibration blink config — read from panel controls
let calibrationConfig = {
    center: { blink: true,  period_ms: 333  },
    white:  { blink: false, period_ms: 1000 },
    red:    { blink: false, period_ms: 1000 },
    blue:   { blink: false, period_ms: 1000 },
    green:  { blink: false, period_ms: 1000 },
};

function readCalibrationConfig() {
    document.querySelectorAll('#calibration-panel .calib-row').forEach(row => {
        const key = row.dataset.key;
        const blink = row.querySelector('.calib-blink').checked;
        const period = parseInt(row.querySelector('.calib-speed').value);
        calibrationConfig[key] = { blink, period_ms: period };
    });
    return calibrationConfig;
}

// Debounced hardware calibration — module-level so class methods can call it
let _calibrationTimer = null;
function triggerHardwareCalibration() {
    if (!canvas || !canvas.showCalibration) return;
    clearTimeout(_calibrationTimer);
    _calibrationTimer = setTimeout(() => {
        api('test_topology_calibration', canvas.effectCenter, canvas.calibrationSpacing,
            readCalibrationConfig(), canvas.calibrationPlan())
            .then(res => {
                // api() swallows exceptions: show the failure instead of dark LEDs
                if (res && res.success === false) {
                    console.warn('[Topology] Calibration failed:', res.error);
                    if (typeof showNotification === 'function') {
                        showNotification(screenText('calibration_failed', 'Calibration: {{error}}',
                                                    { error: res.error || 'failed' }), 'error');
                    }
                }
            });
    }, 80);
}

async function loadSceneTopology() {
    try {
        console.log('[Topology] Loading unified scene topology...');
        const result = await eel.get_scene_topology()();
        if (result.success) {
            console.log(`[Topology] Scene loaded: ${result.zones.length} zones, ${result.devices.length} devices`);
            return result;
        }
        console.warn('[Topology] Scene load failed:', result.error);
    } catch (e) {
        console.warn('[Topology] Failed to load scene:', e);
    }
    return { zones: [], devices: [], global_effect_center: { x: 50, y: 50 } };
}

// ── Screen rectangle panel ───────────────────────────────────────────────────

// Translated text of the Screen panel (pages.topology.*), English if the key is missing
function screenText(key, fallback, vars) {
    const full = 'pages.topology.' + key;
    const v = window.i18n && window.i18n.get ? window.i18n.get(full, vars || null) : null;
    if (v && v !== full) return v;
    return vars ? fallback.replace(/\{\{(\w+)\}\}/g, (m, k) => (k in vars ? vars[k] : m)) : fallback;
}

async function loadScreenRect() {
    try {
        const res = await eel.get_screen_rect()();
        if (res && res.success) {
            canvas.screen.mode = res.mode;
            canvas.screen.rect = res.rect ? { ...res.rect } : null;
            canvas.screen.suggested = res.suggested || null;
            canvas.screen.sceneKeys = Array.isArray(res.scene_keys) ? res.scene_keys : null;
            canvas.screen.size = res.screen || null;
            canvas.screen.aspect = res.screen ? res.screen[0] / res.screen[1] : null;
        }
    } catch (e) {
        console.warn('[Topology] Screen rectangle not loaded:', e);
    }
    canvas.screen.savedJson = JSON.stringify(canvas.screen.rect);

    // A rectangle saved with other proportions (drawn by hand, or another monitor):
    // adapt it, but leave it UNSAVED: growing it can move strips from a side to
    // the inside, so the user checks the canvas and saves (or not).
    const sr = canvas.screen.rect, a = canvas.screen.aspect;
    if (sr && a && Math.abs((sr.x_max - sr.x_min) / (sr.y_max - sr.y_min) - a) / a > 0.01) {
        canvas.screen.rect = canvas.fitAspect(sr);
        showNotification(screenText('screen_adapted',
            'The screen rectangle was adapted to the proportions of your screen. ' +
            'Check that the strips are still on its sides, then save.'), 'warning', 9000);
    }
    updateScreenPanel();
}

function updateScreenPanel() {
    const el = document.getElementById('screen-mode');
    if (!el) return;
    const sc = canvas.screen;
    el.textContent = sc.rect
        ? screenText('screen_mode_manual', 'Placed by hand. LEDs on a side read that side of the screen, LEDs inside read the point under them, LEDs outside are left alone.')
        : screenText('screen_mode_auto', 'Automatic: the screen frames the LEDs of the devices the ambilight drives. Press Fit, or drag a corner or the border, to place it where your monitor is, then save.');
    const auto = document.getElementById('btn-screen-auto');
    if (auto) auto.disabled = !sc.rect;
    const size = document.getElementById('screen-size');
    if (size) {
        size.textContent = sc.size
            ? screenText('screen_size', 'Proportions of your screen: {{w}}×{{h}} ({{ratio}}:1), always kept.',
                         { w: sc.size[0], h: sc.size[1], ratio: (sc.size[0] / sc.size[1]).toFixed(2) })
            : screenText('screen_size_unknown', 'Proportions of your screen: not known yet (start the ambilight once).');
    }
}

// Saves the rectangle when it differs from the file. true = nothing to do or saved.
async function saveScreenRectIfChanged() {
    const json = JSON.stringify(canvas.screen.rect);
    if (json === canvas.screen.savedJson) return true;
    const res = await eel.set_screen_rect(canvas.screen.rect)();
    if (!res || !res.success) {
        showNotification((res && res.error) || screenText('screen_save_error', 'Could not save the screen rectangle'), 'error');
        return false;
    }
    canvas.screen.savedJson = json;
    await loadScreenRect();
    canvas.render();
    return true;
}

async function loadAndRenderScene() {
    const scene = await loadSceneTopology();
    availableDevices = scene.devices || [];

    // Stamp each zone with a unique _uid for zone list lookups
    canvas.zones = JSON.parse(JSON.stringify(scene.zones)).map(z => ({
        ...z,
        id: z.zone_index,
    }));

    canvas.effectCenter = {
        x: scene.global_effect_center?.x ?? 50,
        y: scene.global_effect_center?.y ?? 50,
    };
    canvas.selectedZone = null;
    canvas.anchorCenter();   // the saved center, pinned where it is now

    await loadScreenRect();

    renderDeviceLegend(availableDevices);
    canvas.updateZonesList();
    canvas.updateInspector();
    canvas.updateEffectCenterInputs();
    canvas.updateBoundingBox();
    canvas.render();
}

function renderDeviceLegend(devices) {
    const noDevicesEl = document.getElementById('no-devices-state');
    const listEl = document.getElementById('topology-device-list');
    listEl.innerHTML = '';

    if (!devices || devices.length === 0) {
        noDevicesEl.classList.remove('hidden');
        return;
    }
    noDevicesEl.classList.add('hidden');

    devices.forEach(dev => {
        const card = document.createElement('div');
        card.className = 'device-selector-card';
        card.dataset.deviceId = dev.device_id;
        card.innerHTML = `
            <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2 min-w-0">
                    <div class="w-3 h-3 rounded-sm shrink-0" style="background:${dev.color};"></div>
                    <div class="min-w-0">
                        <div class="device-selector-name truncate">${dev.name}</div>
                        <div class="device-selector-meta">${screenText('device_meta', '{{zones}} zones · {{leds}} LEDs', { zones: dev.zone_count, leds: dev.led_count })}</div>
                    </div>
                </div>
                <button class="flash-btn shrink-0 w-7 h-7 flex items-center justify-center rounded border border-white/20 text-white/50 hover:text-[var(--primary-accent)] hover:border-[var(--primary-accent)] transition-colors"
                        title="${screenText('flash_tooltip', 'Flash to identify')}" data-device-id="${dev.device_id}">
                    <span class="material-symbols-outlined" style="font-size:16px;">bolt</span>
                </button>
            </div>`;
        card.querySelector('.flash-btn').addEventListener('click', async (e) => {
            e.stopPropagation();
            const btn = e.currentTarget;
            btn.style.color = 'var(--primary-accent)';
            btn.style.borderColor = 'var(--primary-accent)';
            await api('flash_topology_device', dev.device_id);
            setTimeout(() => { btn.style.color = ''; btn.style.borderColor = ''; }, 400);
        });
        listEl.appendChild(card);
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Topology Editor] Initializing...');

    // Initialize canvas (empty — scene loaded below)
    const canvasElement = document.getElementById('topology-canvas');
    canvas = new TopologyCanvas(canvasElement);
    // Size the canvas to the available area before the first fit, then follow
    // window / layout changes.
    canvas.resizeToContainer();
    if (window.ResizeObserver) {
        new ResizeObserver(() => canvas.resizeToContainer()).observe(canvasElement);
    } else {
        window.addEventListener('resize', () => canvas.resizeToContainer());
    }
    canvas.updateZonesList();
    canvas.updateInspector();
    canvas.updateEffectCenterInputs();
    canvas.render();

    // Load all devices + zones as a unified scene, then frame it
    await loadAndRenderScene();
    canvas.resetCamera();

    // Grid controls
    document.getElementById('grid-size').addEventListener('input', (e) => {
        canvas.gridSize = parseFloat(e.target.value);
        document.getElementById('grid-size-value').textContent = e.target.value;
        canvas.render();
    });

    document.getElementById('snap-enabled').addEventListener('change', (e) => {
        canvas.snapEnabled = e.target.checked;
    });

    document.getElementById('show-grid').addEventListener('change', (e) => {
        canvas.showGrid = e.target.checked;
        canvas.render();
    });

    // Inspector controls
    document.getElementById('zone-name').addEventListener('input', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.name = e.target.value;
            canvas.updateZonesList();
            canvas.render();
        }
    });

    document.getElementById('zone-x').addEventListener('input', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.position.x = parseFloat(e.target.value) || 0;
            canvas.checkOverlaps();
            canvas.updateBoundingBox();
            canvas.render();
        }
    });

    document.getElementById('zone-y').addEventListener('input', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.position.y = parseFloat(e.target.value) || 0;
            canvas.checkOverlaps();
            canvas.updateBoundingBox();
            canvas.render();
        }
    });

    // Rotation buttons (90° snapping)
    document.querySelectorAll('.rotation-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (canvas.selectedZone) {
                const rotation = parseInt(btn.dataset.rotation);
                canvas.selectedZone.rotation = rotation;

                // Update button states
                document.querySelectorAll('.rotation-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                canvas.checkOverlaps();
                canvas.updateBoundingBox();
                canvas.render();
            }
        });
    });

    document.getElementById('zone-direction').addEventListener('change', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.direction = e.target.value;
            canvas.render();
        }
    });

    document.getElementById('btn-flip-direction').addEventListener('click', () => {
        if (canvas.selectedZone) {
            canvas.selectedZone.direction = canvas.selectedZone.direction === 'forward' ? 'reverse' : 'forward';
            canvas.updateInspector();
            canvas.render();
        }
    });

    document.getElementById('zone-physical-length').addEventListener('input', (e) => {
        if (!canvas.selectedZone) return;
        const zone = canvas.selectedZone;
        const cm = parseFloat(e.target.value);
        if (!isNaN(cm) && cm > 0 && zone.led_count > 0) {
            zone.physical_length_cm = cm;
            zone.led_spacing = cm / zone.led_count;
        } else if (e.target.value === '') {
            zone.physical_length_cm = null;
            zone.led_spacing = 1.0;
        }
        canvas.updateInspector();
        canvas.checkOverlaps();
        canvas.updateBoundingBox();
        canvas.render();
    });

    // Global Effect Center Controls (topology-level)

    document.getElementById('center-x').addEventListener('input', (e) => {
        canvas.effectCenter.x = Math.max(0, Math.min(100, parseFloat(e.target.value) || 50));
        canvas.anchorCenter();
        // Remove active state from all preset buttons (manual input)
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        canvas.updateBoundingBox();
        canvas.render();
    });

    document.getElementById('center-y').addEventListener('input', (e) => {
        canvas.effectCenter.y = Math.max(0, Math.min(100, parseFloat(e.target.value) || 50));
        canvas.anchorCenter();
        // Remove active state from all preset buttons (manual input)
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        canvas.updateBoundingBox();
        canvas.render();
    });

    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const presets = {
                'center': { x: 50, y: 50 },
                'top': { x: 50, y: 90 },
                'bottom': { x: 50, y: 10 },
                'left': { x: 10, y: 50 },
                'right': { x: 90, y: 50 }
            };

            // Toggle active state (same pattern as rotation buttons)
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            canvas.effectCenter = { ...presets[btn.dataset.preset] };
            canvas.anchorCenter();
            canvas.updateEffectCenterInputs();
            canvas.updateBoundingBox();
            canvas.render();
        });
    });

    // Zones list click handler (event delegation) — uses composite uid
    document.getElementById('zones-list').addEventListener('click', (e) => {
        const zoneCard = e.target.closest('.zone-card');
        if (zoneCard) {
            const uid = zoneCard.dataset.zoneUid;
            if (uid) {
                const parts = uid.split('::');
                const zoneIdx = parts[parts.length - 1];
                const did = parts.slice(0, -1).join('::');
                const zone = canvas.zones.find(z => z.device_id === did && String(z.zone_index) === zoneIdx);
                if (zone) { canvas.selectZone(zone); canvas.render(); }
            }
        }
    });

    // Canvas controls
    document.getElementById('btn-auto-layout').addEventListener('click', () => {
        canvas.autoLayout();
        showNotification(screenText('notif_auto_layout', 'Auto layout applied'), 'success');
    });

    document.getElementById('btn-reset').addEventListener('click', () => {
        if (confirm(screenText('confirm_reset', 'Reset all zones to default positions?'))) {
            canvas.reset();
            showNotification(screenText('notif_reset', 'Topology reset'), 'success');
        }
    });

    document.getElementById('btn-reset-view').addEventListener('click', () => {
        canvas.resetCamera();
    });

    document.getElementById('btn-calibration-toggle').addEventListener('click', async (e) => {
        canvas.showCalibration = !canvas.showCalibration;
        e.currentTarget.classList.toggle('active', canvas.showCalibration);
        document.getElementById('calibration-panel').classList.toggle('hidden', !canvas.showCalibration);
        // Turning on: forget the last plan so render() sends the current one.
        canvas._calibSig = null;
        if (!canvas.showCalibration) {
            clearTimeout(_calibrationTimer);
            api('stop_topology_calibration');
        }
        canvas.render();
    });

    document.getElementById('calibration-spacing').addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (val > 0) {
            canvas.calibrationSpacing = val;
            if (canvas.showCalibration) canvas.render();   // render() syncs the LEDs
        }
    });

    // Calibration panel: blink checkboxes and speed sliders
    document.querySelectorAll('#calibration-panel .calib-row').forEach(row => {
        const blinkCb = row.querySelector('.calib-blink');
        const speedRow = row.querySelector('.calib-speed-row');
        const speedInput = row.querySelector('.calib-speed');
        const speedLabel = row.querySelector('.calib-speed-label');

        blinkCb.addEventListener('change', () => {
            speedRow.classList.toggle('hidden', !blinkCb.checked);
            triggerHardwareCalibration();
        });

        speedInput.addEventListener('input', () => {
            speedLabel.textContent = `${speedInput.value}ms`;
            triggerHardwareCalibration();
        });
    });

    document.getElementById('btn-reload-openrgb').addEventListener('click', async () => {
        try {
            const result = await eel.reload_scene_from_openrgb()();
            if (result.success) {
                // Merge reloaded zones back (preserving positions from current canvas)
                const reloadedMap = {};
                result.zones.forEach(z => {
                    const uid = `${z.device_id}::${z.zone_index}`;
                    reloadedMap[uid] = z;
                });
                canvas.zones = canvas.zones.map(z => {
                    const uid = `${z.device_id}::${z.zone_index}`;
                    return reloadedMap[uid] ? { ...z, led_count: reloadedMap[uid].led_count } : z;
                });
                // Add newly detected zones that weren't on canvas
                result.zones.forEach(z => {
                    const uid = `${z.device_id}::${z.zone_index}`;
                    const exists = canvas.zones.find(cz => `${cz.device_id}::${cz.zone_index}` === uid);
                    if (!exists) canvas.zones.push({ ...z, id: z.zone_index });
                });

                const hasNew = Object.values(result.changes).some(c => c.new_zones?.length > 0);
                if (hasNew) canvas.autoLayout();
                else { canvas.render(); canvas.updateZonesList(); }
                showNotification(screenText('notif_reloaded', 'Scene reloaded from OpenRGB'), 'success');
            } else {
                showNotification(result.error || screenText('notif_reload_failed', 'Failed to reload from OpenRGB'), 'error');
            }
        } catch (e) {
            showNotification(screenText('notif_reload_failed', 'Failed to reload from OpenRGB'), 'error');
        }
    });

    document.getElementById('btn-save').addEventListener('click', async () => {
        try {
            const result = await eel.save_scene_topology(canvas.zones, canvas.effectCenter)();
            if (result.success) {
                if (await saveScreenRectIfChanged()) {
                    showNotification(screenText('notif_saved', 'Scene saved'), 'success');
                }
            } else {
                showNotification(result.error || screenText('notif_save_failed', 'Failed to save scene'), 'error');
            }
        } catch (e) {
            showNotification(screenText('notif_save_failed', 'Failed to save scene'), 'error');
        }
    });

    // Texts written by JS (zone list, device cards, spacing, Screen panel)
    // were rendered before the translations arrived: redraw them now.
    window.addEventListener('i18nLoaded', () => {
        renderDeviceLegend(availableDevices);
        canvas.updateZonesList();
        canvas.updateInspector();
        updateScreenPanel();
        canvas.render();
    });

    document.getElementById('btn-screen-fit').addEventListener('click', () => {
        const r = canvas.fitScreenRect();
        if (!r) { showNotification(screenText('screen_no_zones', 'No zones to fit the screen on'), 'warning'); return; }
        canvas.screen.rect = canvas.fitAspect(r);
        updateScreenPanel();
        canvas.render();
    });
    document.getElementById('btn-screen-auto').addEventListener('click', () => {
        canvas.screen.rect = null;
        updateScreenPanel();
        canvas.render();
    });

    console.log('[Topology Editor] Ready');
});

// Leaving the editor with calibration on: stop it, otherwise its thread keeps
// driving the LEDs. Best effort — the server also stops it on disconnect.
window.addEventListener('pagehide', () => {
    if (canvas && canvas.showCalibration) {
        api('stop_topology_calibration');
    }
});

// Fade in page
window.addEventListener('load', () => {
    document.body.classList.add('loaded');
});
