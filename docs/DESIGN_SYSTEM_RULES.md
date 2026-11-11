# Design System Rules - Separation of Concerns

This document defines the strict separation of concerns between `themes.py` and `design_system.py` to maintain consistency and prevent conflicts.

## 📋 Critical Rules

### ✅ `themes.py` - ONLY Colors

**What belongs here:**
- ✓ Color values (background-color, color, border-color, selection-color)
- ✓ Theme variants (elite, dark, light) with different color palettes
- ✓ Color tokens referencing (e.g., `{colors['primary-500']}`)

**What MUST NOT be here:**
- ✗ Numeric dimensions (width, height, padding, margin)
- ✗ Font sizes (use `FONT_SIZES` from design_system.py)
- ✗ Border widths (use `BORDER_WIDTHS` from design_system.py)
- ✗ Border radius (use `RADIUS` from design_system.py)
- ✗ Spacing values (use `SPACING_SCALE` from design_system.py)
- ✗ Component dimensions (use `COMPONENT_HEIGHTS`, `COMPONENT_WIDTHS` from design_system.py)

### ✅ `design_system.py` - ALL Structural Properties

**What belongs here:**
- ✓ Spacing scale (`SPACING_SCALE`)
- ✓ Component heights (`COMPONENT_HEIGHTS`)
- ✓ Component widths (`COMPONENT_WIDTHS`)
- ✓ Border widths (`BORDER_WIDTHS`)
- ✓ Border radius (`RADIUS`)
- ✓ Icon sizes (`ICON_SIZES`)
- ✓ Font properties (`FONT_SIZES`, `FONT_WEIGHTS`, `FONT_FAMILY`)
- ✓ Slider dimensions (`SLIDER_DIMENSIONS`)
- ✓ Reusable style generators (`get_button_style`, `get_combobox_style`, etc.)
- ✓ Base color palette (`ELITE_COLORS`)

**What MUST NOT be here:**
- ✗ Theme-specific color variations (those go in themes.py theme functions)

## 📐 Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Application                      │
│                                                     │
│  ┌──────────────┐         ┌──────────────┐         │
│  │  themes.py   │────────▶│design_system.│         │
│  │              │ imports │      py      │         │
│  │              │         │              │         │
│  │ - Colors     │         │ - Dimensions │         │
│  │ - Palettes   │         │ - Spacing    │         │
│  │ - Variants   │         │ - Fonts      │         │
│  └──────────────┘         └──────────────┘         │
│         │                         │                 │
│         │ setStyleSheet()         │ constants       │
│         ▼                         ▼                 │
│  ┌─────────────────────────────────────────┐       │
│  │          UI Components                  │       │
│  │  (buttons, inputs, comboboxes, etc.)    │       │
│  └─────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

## 🔍 Verification

### Check for violations in themes.py:

```bash
# Search for hardcoded pixel values (should find NONE except in variable names)
grep -nE '\b[0-9]+px\b' src/themes.py | grep -v "BORDER_WIDTHS\|ICON_SIZES\|COMPONENT_WIDTHS\|COMPONENT_HEIGHTS\|SLIDER_DIMENSIONS\|SPACING_SCALE\|RADIUS\|FONT_SIZES"
```

**Expected result:** No output (no hardcoded values)

### Check for color definitions in design_system.py:

```bash
# ELITE_COLORS is the only color definition allowed
grep -nE "'#[0-9A-Fa-f]{3,6}'" src/ui/design_system.py
```

**Expected result:** Only lines within `ELITE_COLORS` dictionary

## 📝 Examples

### ✅ CORRECT Usage in themes.py:

```python
# Good: Uses constants from design_system.py
buttons = f"""
QPushButton {{
    border: {BORDER_WIDTHS['default']}px solid {colors['primary-500']};
    border-radius: {RADIUS['md']}px;
    padding: {SPACING_SCALE['sm']}px {SPACING_SCALE['lg']}px;
    font-size: {FONT_SIZES['body']}px;
}}
"""
```

### ❌ INCORRECT Usage in themes.py:

```python
# Bad: Hardcoded dimensions
buttons = f"""
QPushButton {{
    border: 2px solid {colors['primary-500']};  # ❌ Should use BORDER_WIDTHS['default']
    border-radius: 6px;                         # ❌ Should use RADIUS['md']
    padding: 8px 16px;                          # ❌ Should use SPACING_SCALE
    font-size: 12px;                            # ❌ Should use FONT_SIZES['body']
}}
"""
```

### ✅ CORRECT: Adding new dimension

If you need a new dimension, add it to `design_system.py` first:

```python
# design_system.py
COMPONENT_WIDTHS = {
    'dropdown': 30,
    'scrollbar': 10,
    'new-component': 50,  # Add here first
}
```

Then use it in `themes.py`:

```python
# themes.py
component = f"""
QMyComponent {{
    width: {COMPONENT_WIDTHS['new-component']}px;
    background-color: {colors['surface-2']};
}}
"""
```

## 🎯 Benefits

1. **Single Source of Truth**: All dimensions defined once in `design_system.py`
2. **Consistent Theming**: All themes use identical structure, only colors differ
3. **Easy Maintenance**: Change a dimension once, affects all themes automatically
4. **No Conflicts**: Clear separation prevents stylesheet conflicts
5. **Scalability**: Add new themes without duplicating structural code

## 🚨 Enforcement

Before committing changes to `themes.py`:

1. Run the verification grep command above
2. Ensure no hardcoded `px` values except in variable names
3. All dimensions MUST reference `design_system.py` constants
4. All themes (elite, dark, light) MUST use identical structure

## 📚 Reference

### Available Constants from design_system.py:

- `SPACING_SCALE`: {'xs': 4, 'sm': 8, 'md': 12, 'lg': 16, 'xl': 24, 'xxl': 32, 'xxxl': 48}
- `COMPONENT_HEIGHTS`: {'compact': 24, 'default': 30, 'comfortable': 36, 'spacious': 44}
- `COMPONENT_WIDTHS`: {'dropdown': 30, 'scrollbar': 10, 'sidebar': 240, 'button-min': 80}
- `BORDER_WIDTHS`: {'thin': 1, 'default': 2, 'thick': 3, 'extra-thick': 4}
- `ICON_SIZES`: {'xs': 12, 'sm': 16, 'md': 24, 'lg': 32, 'xl': 48}
- `RADIUS`: {'sm': 4, 'md': 6, 'lg': 8, 'xl': 12, 'round': 9999}
- `FONT_SIZES`: {'caption': 10, 'body': 12, 'body-large': 13, 'subtitle': 14, 'title': 16, 'headline': 20, 'display': 24}
- `FONT_WEIGHTS`: {'regular': 400, 'medium': 500, 'bold': 700}
- `SLIDER_DIMENSIONS`: {'groove-height': 8, 'handle-size': 18, 'handle-margin': -5}

### Color Palette (ELITE_COLORS):

**Primary (Orange):**
- `primary-900`: #8B4500
- `primary-700`: #CC7000
- `primary-500`: #FF8C00 ⭐ Main
- `primary-300`: #FFA733
- `primary-100`: #FFDDB3

**Accent:**
- `accent-gold`: #FFD700

**Surfaces:**
- `surface-1`: #0F0F0F (main background)
- `surface-2`: #1A1A1A (cards)
- `surface-3`: #252525 (hover)
- `surface-4`: #303030 (active)

**Text:**
- `text-primary`: #FF8C00 (main orange)
- `text-secondary`: #CCCCCC
- `text-tertiary`: #999999
- `text-disabled`: #666666
- `text-inverse`: #000000 (on orange)
- `text-white`: #FFFFFF

**Borders:**
- `border-subtle`: #333333
- `border-default`: #444444 ⭐ Main
- `border-strong`: #666666

## 🔄 Migration Checklist

When refactoring existing code:

- [ ] Identify all hardcoded `px` values in themes.py
- [ ] Check if corresponding constant exists in design_system.py
- [ ] If missing, add constant to appropriate dictionary in design_system.py
- [ ] Replace hardcoded value with constant reference
- [ ] Update imports in themes.py to include new constants
- [ ] Test all themes (elite, dark, light) to verify consistency
- [ ] Run verification grep to ensure no hardcoded values remain

---

**Last Updated:** 2026-01-28
**Enforced in:** ED:Event2Led v2.0+
