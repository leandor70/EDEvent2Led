"""
Auto-Reconnect Implementation Verification Script

Verifica che tutte le componenti del sistema auto-reconnect siano implementate
correttamente prima di procedere con test hardware.

Usage:
    python tools/verify_auto_reconnect_implementation.py
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def verify_tier1_decorator():
    """Verify Tier 1: Decorator implementation."""
    print("\n=== TIER 1: Lightweight Retry Decorator ===")

    try:
        from utils.openrgb_safe import retry_on_disconnect
        print("[OK] retry_on_disconnect decorator importato")

        # Check if it's a proper decorator
        if not callable(retry_on_disconnect):
            print("[FAIL] retry_on_disconnect non e' callable")
            return False

        # Test decorator structure
        test_func = lambda: "test"
        decorated = retry_on_disconnect()(test_func)

        if not callable(decorated):
            print("[FAIL] Decorator non ritorna callable")
            return False

        print("[OK] Decorator structure corretta")
        return True

    except Exception as e:
        print(f"[FAIL] Error importing decorator: {e}")
        return False


def verify_tier1_unified_manager():
    """Verify Tier 1: UnifiedManager reconnection logic."""
    print("\n=== TIER 1: UnifiedManager Reconnection ===")

    try:
        from effects.unified_manager import UnifiedEffectManager
        print("[OK] UnifiedEffectManager importato")

        # Check reconnection fields
        required_fields = [
            '_connection_lost',
            '_reconnect_attempts',
            '_max_reconnect_attempts',
            '_last_reconnect_time',
            '_reconnect_cooldown'
        ]

        # Create dummy instance to check __init__
        import inspect
        init_source = inspect.getsource(UnifiedEffectManager.__init__)

        missing = []
        for field in required_fields:
            if field not in init_source:
                missing.append(field)

        if missing:
            print(f"[FAIL] Missing fields in __init__: {missing}")
            return False

        print(f"[OK] Tutti i {len(required_fields)} campi reconnection presenti")

        # Check methods
        required_methods = ['_reconnect_openrgb', '_redetect_devices']
        missing_methods = []

        for method in required_methods:
            if not hasattr(UnifiedEffectManager, method):
                missing_methods.append(method)

        if missing_methods:
            print(f"[FAIL] Missing methods: {missing_methods}")
            return False

        print(f"[OK] Tutti i {len(required_methods)} metodi presenti")
        return True

    except Exception as e:
        print(f"[FAIL] Error verifying UnifiedManager: {e}")
        return False


def verify_tier1_effect_threads():
    """Verify Tier 1: Effect thread exception handling."""
    print("\n=== TIER 1: Effect Thread Protection ===")

    try:
        from effects.spatial_effects_1d import Animated1DEffect
        from effects.spatial_effects_2d import Animated2DEffect
        print("[OK] Effect classes importate")

        # Check error tracking fields in Animated1DEffect
        import inspect
        init_1d = inspect.getsource(Animated1DEffect.__init__)

        required_fields = ['_last_error', '_consecutive_errors', '_max_consecutive_errors']
        missing = [f for f in required_fields if f not in init_1d]

        if missing:
            print(f"[FAIL] Animated1DEffect missing fields: {missing}")
            return False

        print("[OK] Animated1DEffect error tracking fields presenti")

        # Check method
        if not hasattr(Animated1DEffect, 'get_last_error'):
            print("[FAIL] Animated1DEffect missing get_last_error()")
            return False

        print("[OK] Animated1DEffect get_last_error() presente")

        # Same checks for 2D
        init_2d = inspect.getsource(Animated2DEffect.__init__)
        missing = [f for f in required_fields if f not in init_2d]

        if missing:
            print(f"[FAIL] Animated2DEffect missing fields: {missing}")
            return False

        print("[OK] Animated2DEffect error tracking completo")
        return True

    except Exception as e:
        print(f"[FAIL] Error verifying effect threads: {e}")
        return False


def verify_tier2_async_reconnect():
    """Verify Tier 2: Async reconnection."""
    print("\n=== TIER 2: Async Reconnection ===")

    try:
        from api.settings_api import try_ensure_openrgb, with_openrgb_check, force_openrgb_reconnect
        print("[OK] Funzioni Tier 2 importate")

        # Check function signatures
        import inspect

        # try_ensure_openrgb should have notify_ui parameter
        sig = inspect.signature(try_ensure_openrgb)
        if 'notify_ui' not in sig.parameters:
            print("[FAIL] try_ensure_openrgb missing notify_ui parameter")
            return False

        print("[OK] try_ensure_openrgb ha parametro notify_ui")

        # with_openrgb_check should be a decorator
        if not callable(with_openrgb_check):
            print("[FAIL] with_openrgb_check non e' callable")
            return False

        print("[OK] with_openrgb_check decorator presente")

        # force_openrgb_reconnect should exist
        if not callable(force_openrgb_reconnect):
            print("[FAIL] force_openrgb_reconnect non e' callable")
            return False

        print("[OK] force_openrgb_reconnect API presente")
        return True

    except Exception as e:
        print(f"[FAIL] Error verifying Tier 2: {e}")
        return False


def verify_tier2_decorator_applications():
    """Verify Tier 2: Decorator applications on API functions."""
    print("\n=== TIER 2: API Decorator Applications ===")

    api_files = {
        'api.effects_api': 3,
        'api.devices_api': 9,
        'api.keyboard_api': 8,
        'api.bindings_api': 2
    }

    total_expected = sum(api_files.values())
    total_found = 0

    for module_name, expected_count in api_files.items():
        try:
            # Read file and count @with_openrgb_check occurrences
            module_path = module_name.replace('.', '/')
            file_path = Path(__file__).parent.parent / 'src' / f"{module_path}.py"

            if not file_path.exists():
                print(f"[FAIL] {file_path} non trovato")
                continue

            content = file_path.read_text(encoding='utf-8')
            count = content.count('@with_openrgb_check')

            if count != expected_count:
                print(f"[WARN] {module_name}: attesi {expected_count} decorators, trovati {count}")
            else:
                print(f"[OK] {module_name}: {count}/{expected_count} decorators")

            total_found += count

        except Exception as e:
            print(f"[FAIL] Error checking {module_name}: {e}")

    print(f"\n[INFO] Totale decorators trovati: {total_found}/{total_expected}")

    if total_found < total_expected:
        print(f"[WARN] Mancano {total_expected - total_found} decorators")
        return False

    return True


def verify_tier3_error_tracking():
    """Verify Tier 3: Error tracking in renderer."""
    print("\n=== TIER 3: Renderer Error Tracking ===")

    try:
        from core.visual_effect_renderer import VisualEffectRenderer
        print("[OK] VisualEffectRenderer importato")

        import inspect

        # Check error tracking fields
        init_source = inspect.getsource(VisualEffectRenderer.__init__)
        required_fields = ['_device_errors', '_error_threshold', '_error_window']

        missing = [f for f in required_fields if f not in init_source]

        if missing:
            print(f"[FAIL] Missing fields: {missing}")
            return False

        print(f"[OK] Tutti i {len(required_fields)} campi error tracking presenti")

        # Check methods
        required_methods = [
            '_record_device_error',
            '_check_error_threshold',
            '_trigger_connection_lost_modal'
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(VisualEffectRenderer, method):
                missing_methods.append(method)

        if missing_methods:
            print(f"[FAIL] Missing methods: {missing_methods}")
            return False

        print(f"[OK] Tutti i {len(required_methods)} metodi presenti")
        return True

    except Exception as e:
        print(f"[FAIL] Error verifying Tier 3: {e}")
        return False


def verify_tier3_frontend():
    """Verify Tier 3: Frontend modal implementation."""
    print("\n=== TIER 3: Frontend Integration ===")

    try:
        common_js = Path(__file__).parent.parent / 'web' / 'js' / 'common.js'

        if not common_js.exists():
            print(f"[FAIL] {common_js} non trovato")
            return False

        content = common_js.read_text(encoding='utf-8')

        # Check for required functions
        required_functions = [
            'show_reconnect_toast',
            'show_reconnect_success_toast',
            'show_openrgb_connection_lost_modal'
        ]

        missing = []
        for func in required_functions:
            if func not in content:
                missing.append(func)

        if missing:
            print(f"[FAIL] Missing functions in common.js: {missing}")
            return False

        print(f"[OK] Tutte le {len(required_functions)} funzioni frontend presenti")

        # Check for modal HTML structure
        if 'openrgb-lost-modal' not in content:
            print("[FAIL] Modal HTML structure non trovata")
            return False

        print("[OK] Modal HTML structure presente")

        # Check for event listeners
        if 'modal-retry-btn' not in content or 'modal-settings-btn' not in content:
            print("[FAIL] Modal buttons non trovati")
            return False

        print("[OK] Modal buttons presenti")
        return True

    except Exception as e:
        print(f"[FAIL] Error verifying frontend: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("  AUTO-RECONNECT IMPLEMENTATION VERIFICATION")
    print("=" * 70)

    results = []

    # Tier 1 checks
    results.append(("Tier 1 - Decorator", verify_tier1_decorator()))
    results.append(("Tier 1 - UnifiedManager", verify_tier1_unified_manager()))
    results.append(("Tier 1 - Effect Threads", verify_tier1_effect_threads()))

    # Tier 2 checks
    results.append(("Tier 2 - Async Reconnect", verify_tier2_async_reconnect()))
    results.append(("Tier 2 - Decorator Apps", verify_tier2_decorator_applications()))

    # Tier 3 checks
    results.append(("Tier 3 - Error Tracking", verify_tier3_error_tracking()))
    results.append(("Tier 3 - Frontend", verify_tier3_frontend()))

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    print("\n" + "=" * 70)
    print(f"  RISULTATO: {passed}/{total} checks passed")
    print("=" * 70)

    if passed == total:
        print("\n[OK] Implementazione completa! Pronto per test hardware.")
        return 0
    else:
        print(f"\n[WARN] {total - passed} checks falliti. Rivedere implementazione.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
