"""
Ambilight sampling stability (effects.ambilight_service._sample_segment).

Bug fixed: the percentile strategies took the ONE pixel at the 80th luminance
percentile. On dark content with colored text (a chat, an IDE) a blinking
cursor moved that choice onto a pixel of another color: the LED jumped by up to
225/255 between frames. Now the mean of the brightest 20% is used.

Synthetic BGR frames, no capture and no hardware.
Run:  python tools/test_ambilight_sampling.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from effects.ambilight_service import _boost_saturation, _sample_segment  # noqa: E402

PALETTE = np.array([[53, 107, 255], [80, 200, 120], [230, 230, 230],
                    [255, 170, 60], [90, 90, 220], [200, 120, 200]], np.uint8)   # BGR


def text_segment(rng, h=108, w=160):
    """Dark background with words of colored text (one top-edge LED segment at 1080p)."""
    seg = np.full((h, w, 3), 30, np.uint8)
    cover = rng.uniform(0.08, 0.35)
    for row in range(0, h, 14):
        x = 0
        while x < w:
            n = int(rng.integers(3, 30))
            if rng.random() < cover * 2.2:
                seg[row:row + 9, x:x + n] = PALETTE[rng.integers(len(PALETTE))]
            x += n + int(rng.integers(3, 9))
    return seg


def led(seg, strategy="adaptive_smooth"):
    return np.array(_boost_saturation([_sample_segment(seg, strategy)], 1.4)[0], float)


def check(cond, msg):
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")
    return bool(cond)


def main() -> int:
    ok = True
    rng = np.random.default_rng(11)
    for strategy in ("adaptive_smooth", "smooth", "percentile", "adaptive"):
        jumps = []
        for _ in range(300):
            seg = text_segment(rng)
            on = seg.copy()
            cy, cx = rng.integers(0, seg.shape[0] - 16), rng.integers(0, seg.shape[1] - 8)
            on[cy:cy + 16, cx:cx + 8] = 240                      # cursor block
            jumps.append(np.abs(led(on, strategy) - led(seg, strategy)).max())
        jumps = np.array(jumps)
        ok &= check(jumps.max() <= 20,
                    f"{strategy:16} cursor blink moves the LED by at most {jumps.max():.1f}/255 (was up to 225)")

    # Still a "vivid" strategy: bright colors win over a dark background
    seg = np.full((100, 100, 3), 10, np.uint8)
    seg[:25] = (53, 107, 255)                                    # 25% orange (BGR)
    r, g, b = _sample_segment(seg, "percentile")
    ok &= check((r, g, b) == (255, 107, 53), f"25% orange on black -> orange {(r, g, b)}")
    seg[:10] = (53, 107, 255)
    seg[10:] = 10                                                # 10% orange: dilutes, stays orange-ish
    r, g, b = _sample_segment(seg, "percentile")
    ok &= check(r > g > b and r >= 120, f"10% orange on black -> dimmer orange {(r, g, b)}")
    ok &= check(_sample_segment(np.zeros((0, 3), np.uint8), "percentile") == (0, 0, 0), "empty segment -> black")
    ok &= check(_sample_segment(np.full((1, 1, 3), 7, np.uint8), "percentile") == (7, 7, 7), "single pixel segment")

    print()
    print("  [OK] TUTTI I CONTROLLI PASSATI" if ok else "  [FAIL] ALCUNI CONTROLLI FALLITI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
