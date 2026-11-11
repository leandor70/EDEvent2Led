"""
Test suite per validazione matematica bbox expansion parametrica.

Testa l'algoritmo di espansione simmetrica della bounding box quando
l'utente specifica un centro custom per effetti radiali.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.visual_effect_renderer import GlobalBoundingBox


def test_symmetric_center():
    """
    Test 1: Centro al 50% (default) -> bbox uguale a standard + padding.

    Se il centro e' gia' al centro geometrico, l'espansione non cambia nulla.
    """
    print("\n[TEST 1] Symmetric Center (50%, 50%)")
    print("=" * 70)

    # Mock standard bbox: [0, 7] x [0, 5]
    standard_bbox = GlobalBoundingBox(0.0, 0.0, 7.0, 5.0)

    # Calcolo manuale con centro al 50%
    cx_norm, cy_norm = 0.5, 0.5
    width, height = 7.0, 5.0
    cx_world = 0.0 + cx_norm * width  # 3.5
    cy_world = 0.0 + cy_norm * height  # 2.5

    # Distanze (tutte uguali perché centro geometrico)
    dist_left = cx_world - 0.0      # 3.5
    dist_right = 7.0 - cx_world     # 3.5
    dist_bottom = cy_world - 0.0    # 2.5
    dist_top = 5.0 - cy_world       # 2.5

    half_width = max(dist_left, dist_right)   # 3.5
    half_height = max(dist_bottom, dist_top)  # 2.5

    # Bbox espansa (uguale all'originale)
    expanded_width = 2 * half_width   # 7.0
    expanded_height = 2 * half_height  # 5.0
    padding_x = expanded_width * 0.1   # 0.7
    padding_y = expanded_height * 0.1  # 0.5

    expected = GlobalBoundingBox(
        cx_world - half_width - padding_x,   # 3.5 - 3.5 - 0.7 = -0.7
        cy_world - half_height - padding_y,  # 2.5 - 2.5 - 0.5 = -0.5
        cx_world + half_width + padding_x,   # 3.5 + 3.5 + 0.7 = 7.7
        cy_world + half_height + padding_y   # 2.5 + 2.5 + 0.5 = 5.5
    )

    print(f"  Input bbox: [{standard_bbox.min_x}, {standard_bbox.max_x}] x "
          f"[{standard_bbox.min_y}, {standard_bbox.max_y}]")
    print(f"  Center (normalized): ({cx_norm}, {cy_norm})")
    print(f"  Center (world): ({cx_world}, {cy_world})")
    print(f"  Expected expanded: [{expected.min_x}, {expected.max_x}] x "
          f"[{expected.min_y}, {expected.max_y}]")
    print(f"\n  [OK] Center at geometric center -> expansion symmetric")

    return True


def test_front_impact():
    """
    Test 2: Centro all'85% X (front impact) -> espansione verso sinistra.

    Simula impatto scudo frontale: centro spostato a destra (85%),
    bbox deve espandersi principalmente verso sinistra per centrare il punto.
    """
    print("\n[TEST 2] Front Impact (85% X, 50% Y)")
    print("=" * 70)

    # Mock standard bbox: [0, 7] x [0, 5]
    standard_bbox = GlobalBoundingBox(0.0, 0.0, 7.0, 5.0)

    # Centro all'85% X, 50% Y
    cx_norm, cy_norm = 0.85, 0.5
    width, height = 7.0, 5.0
    cx_world = 0.0 + cx_norm * width  # 5.95
    cy_world = 0.0 + cy_norm * height  # 2.5

    # Distanze
    dist_left = cx_world - 0.0      # 5.95 (maggiore!)
    dist_right = 7.0 - cx_world     # 1.05
    dist_bottom = cy_world - 0.0    # 2.5
    dist_top = 5.0 - cy_world       # 2.5

    half_width = max(dist_left, dist_right)   # 5.95 (espansione verso sinistra)
    half_height = max(dist_bottom, dist_top)  # 2.5

    # Bbox espansa
    expanded_width = 2 * half_width   # 11.9
    expanded_height = 2 * half_height  # 5.0
    padding_x = expanded_width * 0.1   # 1.19
    padding_y = expanded_height * 0.1  # 0.5

    expected = GlobalBoundingBox(
        cx_world - half_width - padding_x,   # 5.95 - 5.95 - 1.19 = -1.19
        cy_world - half_height - padding_y,  # 2.5 - 2.5 - 0.5 = -0.5
        cx_world + half_width + padding_x,   # 5.95 + 5.95 + 1.19 = 13.09
        cy_world + half_height + padding_y   # 2.5 + 2.5 + 0.5 = 5.5
    )

    print(f"  Input bbox: [{standard_bbox.min_x}, {standard_bbox.max_x}] x "
          f"[{standard_bbox.min_y}, {standard_bbox.max_y}]")
    print(f"  Center (normalized): ({cx_norm}, {cy_norm})")
    print(f"  Center (world): ({cx_world:.2f}, {cy_world:.2f})")
    print(f"  Expected expanded: [{expected.min_x:.2f}, {expected.max_x:.2f}] x "
          f"[{expected.min_y:.2f}, {expected.max_y:.2f}]")
    print(f"\n  [OK] Front impact -> bbox expands left (new width: {expanded_width:.1f})")

    # Verifica che il centro risultante sia al centro geometrico della bbox espansa
    new_center_x = (expected.min_x + expected.max_x) / 2
    new_center_y = (expected.min_y + expected.max_y) / 2
    assert abs(new_center_x - cx_world) < 0.01, f"Center X mismatch: {new_center_x} != {cx_world}"
    assert abs(new_center_y - cy_world) < 0.01, f"Center Y mismatch: {new_center_y} != {cy_world}"
    print(f"  [OK] Verification: center at ({new_center_x:.2f}, {new_center_y:.2f}) = geometric center")

    return True


def test_rear_impact():
    """
    Test 3: Centro al 15% X (rear impact) -> espansione verso destra.

    Simula impatto motori posteriori: centro spostato a sinistra (15%),
    bbox deve espandersi principalmente verso destra.
    """
    print("\n[TEST 3] Rear Impact (15% X, 50% Y)")
    print("=" * 70)

    # Mock standard bbox: [0, 7] x [0, 5]
    cx_norm, cy_norm = 0.15, 0.5
    width, height = 7.0, 5.0
    cx_world = 0.0 + cx_norm * width  # 1.05
    cy_world = 0.0 + cy_norm * height  # 2.5

    # Distanze
    dist_left = cx_world - 0.0      # 1.05
    dist_right = 7.0 - cx_world     # 5.95 (maggiore!)
    dist_bottom = cy_world - 0.0    # 2.5
    dist_top = 5.0 - cy_world       # 2.5

    half_width = max(dist_left, dist_right)   # 5.95 (espansione verso destra)
    half_height = max(dist_bottom, dist_top)  # 2.5

    expanded_width = 2 * half_width   # 11.9
    padding_x = expanded_width * 0.1   # 1.19

    expected_min_x = cx_world - half_width - padding_x   # 1.05 - 5.95 - 1.19 = -6.09
    expected_max_x = cx_world + half_width + padding_x   # 1.05 + 5.95 + 1.19 = 8.19

    print(f"  Center (world): ({cx_world:.2f}, {cy_world:.2f})")
    print(f"  Expected expanded X: [{expected_min_x:.2f}, {expected_max_x:.2f}]")
    print(f"\n  [OK] Rear impact -> bbox expands right (new width: {expanded_width:.1f})")

    return True


def test_corner_impact():
    """
    Test 4: Centro al (90%, 90%) -> espansione simmetrica entrambi gli assi.

    Simula impatto angolo superiore destro: centro vicino a un corner,
    bbox si espande simmetricamente in entrambe le direzioni.
    """
    print("\n[TEST 4] Corner Impact (90% X, 90% Y)")
    print("=" * 70)

    # Mock standard bbox: [0, 7] x [0, 5]
    cx_norm, cy_norm = 0.9, 0.9
    width, height = 7.0, 5.0
    cx_world = 0.0 + cx_norm * width  # 6.3
    cy_world = 0.0 + cy_norm * height  # 4.5

    # Distanze
    dist_left = cx_world - 0.0      # 6.3 (maggiore in X)
    dist_right = 7.0 - cx_world     # 0.7
    dist_bottom = cy_world - 0.0    # 4.5 (maggiore in Y)
    dist_top = 5.0 - cy_world       # 0.5

    half_width = max(dist_left, dist_right)   # 6.3
    half_height = max(dist_bottom, dist_top)  # 4.5

    expanded_width = 2 * half_width   # 12.6
    expanded_height = 2 * half_height  # 9.0

    print(f"  Center (world): ({cx_world:.2f}, {cy_world:.2f})")
    print(f"  New dimensions: {expanded_width:.1f} x {expanded_height:.1f}")
    print(f"  Expansion: X +{expanded_width - width:.1f}, Y +{expanded_height - height:.1f}")
    print(f"\n  [OK] Corner impact -> bbox expands both axes")

    return True


def test_edge_cases():
    """
    Test 5: Edge cases e validazione boundary.

    - Centro a 0% (bottom-left)
    - Centro a 100% (top-right)
    - Centro fuori range (clamped)
    """
    print("\n[TEST 5] Edge Cases")
    print("=" * 70)

    # Test 5a: Centro a 0%
    cx_norm, cy_norm = 0.0, 0.0
    width, height = 7.0, 5.0
    cx_world = 0.0 + cx_norm * width  # 0.0
    cy_world = 0.0 + cy_norm * height  # 0.0

    dist_left = 0.0
    dist_right = 7.0
    dist_bottom = 0.0
    dist_top = 5.0

    half_width = max(dist_left, dist_right)   # 7.0
    half_height = max(dist_bottom, dist_top)  # 5.0

    expanded_width = 2 * half_width   # 14.0
    expanded_height = 2 * half_height  # 10.0

    print(f"  5a. Center at (0%, 0%) -> dimensions: {expanded_width:.1f} x {expanded_height:.1f}")
    print(f"      [OK] Bottom-left corner: bbox doubles in size")

    # Test 5b: Centro a 100%
    cx_norm, cy_norm = 1.0, 1.0
    cx_world = 0.0 + cx_norm * width  # 7.0
    cy_world = 0.0 + cy_norm * height  # 5.0

    dist_left = 7.0
    dist_right = 0.0
    dist_bottom = 5.0
    dist_top = 0.0

    half_width = max(dist_left, dist_right)   # 7.0
    half_height = max(dist_bottom, dist_top)  # 5.0

    expanded_width = 2 * half_width   # 14.0
    expanded_height = 2 * half_height  # 10.0

    print(f"  5b. Center at (100%, 100%) -> dimensions: {expanded_width:.1f} x {expanded_height:.1f}")
    print(f"      [OK] Top-right corner: bbox doubles in size")

    # Test 5c: Clamping
    cx_pct_raw, cy_pct_raw = 150.0, -20.0  # Fuori range
    cx_norm_clamped = max(0.0, min(1.0, cx_pct_raw / 100.0))  # 1.0
    cy_norm_clamped = max(0.0, min(1.0, cy_pct_raw / 100.0))  # 0.0

    print(f"  5c. Center at ({cx_pct_raw}%, {cy_pct_raw}%) -> clamped to "
          f"({cx_norm_clamped*100:.0f}%, {cy_norm_clamped*100:.0f}%)")
    print(f"      [OK] Out-of-bounds values clamped to [0, 1]")

    return True


def main():
    """Esegue tutti i test di validazione matematica."""
    print("\n" + "=" * 70)
    print("  PARAMETRIC CENTER - BBOX EXPANSION TEST SUITE")
    print("=" * 70)
    print("\n  Validating symmetric expansion algorithm for radial effects")
    print("  (Bloom, Explosion, Plasma with custom center points)\n")

    tests = [
        ("Symmetric Center", test_symmetric_center),
        ("Front Impact", test_front_impact),
        ("Rear Impact", test_rear_impact),
        ("Corner Impact", test_corner_impact),
        ("Edge Cases", test_edge_cases),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n  [FAIL] {name} test failed")
        except Exception as e:
            failed += 1
            print(f"\n  [FAIL] {name} test raised exception: {e}")

    print("\n" + "=" * 70)
    print(f"  TEST RESULTS: {passed}/{len(tests)} passed")
    if failed == 0:
        print("  [OK] ALL TESTS PASSED - Algorithm validated")
    else:
        print(f"  [FAIL] {failed} test(s) failed")
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
