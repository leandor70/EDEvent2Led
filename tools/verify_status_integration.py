"""
Quick Verification Script for Status Monitor Integration
Tests that all modules load correctly without starting the full GUI

Usage:
    python tools/verify_status_integration.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_imports():
    """Test that all required modules can be imported"""
    print("[1/5] Testing module imports...")

    try:
        from journal.status_monitor import StatusMonitor
        print("  [OK] StatusMonitor imported")
    except Exception as e:
        print(f"  [FAIL] Failed to import StatusMonitor: {e}")
        return False

    try:
        from journal.event_processor import EventProcessor
        print("  [OK] EventProcessor imported")
    except Exception as e:
        print(f"  [FAIL] Failed to import EventProcessor: {e}")
        return False

    try:
        from effects.unified_manager import UnifiedEffectManager
        print("  [OK] UnifiedEffectManager imported")
    except Exception as e:
        print(f"  [FAIL] Failed to import UnifiedEffectManager: {e}")
        return False

    return True


def test_status_monitor_flags():
    """Test that StatusMonitor has correct flag definitions"""
    print("\n[2/5] Testing StatusMonitor flag definitions...")

    from journal.status_monitor import StatusMonitor

    # Check MONITORED_FLAGS
    flags_count = len(StatusMonitor.MONITORED_FLAGS)
    print(f"  [OK] MONITORED_FLAGS: {flags_count} flags defined")

    # Check MONITORED_FLAGS2
    flags2_count = len(StatusMonitor.MONITORED_FLAGS2)
    print(f"  [OK] MONITORED_FLAGS2: {flags2_count} flags defined")

    # Verify some critical flags exist
    critical_flags = [20, 22, 23, 19]  # Overheating, Interdiction, Danger, LowFuel
    for bit in critical_flags:
        if bit in StatusMonitor.MONITORED_FLAGS:
            flag_info = StatusMonitor.MONITORED_FLAGS[bit]
            print(f"  [OK] Flag bit {bit}: {flag_info['name']} -> {flag_info['effect']}")
        else:
            print(f"  [FAIL] Critical flag bit {bit} not found!")
            return False

    return True


def test_event_processor_methods():
    """Test that EventProcessor has required methods"""
    print("\n[3/5] Testing EventProcessor methods...")

    from journal.event_processor import EventProcessor

    # Check that process_status_flag method exists
    if hasattr(EventProcessor, 'process_status_flag'):
        print("  [OK] process_status_flag() method exists")
    else:
        print("  [FAIL] process_status_flag() method not found!")
        return False

    # Check signature
    import inspect
    sig = inspect.signature(EventProcessor.process_status_flag)
    params = list(sig.parameters.keys())
    expected_params = ['self', 'flag_name', 'is_active', 'effect_id', 'priority']

    if params == expected_params:
        print(f"  [OK] Method signature correct: {', '.join(expected_params)}")
    else:
        print(f"  [FAIL] Method signature incorrect!")
        print(f"    Expected: {expected_params}")
        print(f"    Got: {params}")
        return False

    return True


def test_visual_effects():
    """Test that required visual effects exist"""
    print("\n[4/5] Testing visual effects library...")

    import json
    effects_file = Path(__file__).parent.parent / 'config' / 'visual_effects.json'

    if not effects_file.exists():
        print(f"  [FAIL] Effects file not found: {effects_file}")
        return False

    with open(effects_file, 'r', encoding='utf-8') as f:
        effects_data = json.load(f)

    effects = effects_data.get('effects', [])
    print(f"  [OK] Effects library loaded: {len(effects)} effects")

    # Check for status effects
    status_effects = [e for e in effects if e.get('category') == 'status']
    print(f"  [OK] Status effects: {len(status_effects)} effects")

    # Verify some critical effects exist
    critical_effect_ids = ['overheat_warning', 'interdiction_alert', 'danger_alert', 'low_fuel_warning']
    found_effects = []

    for effect in effects:
        if effect['id'] in critical_effect_ids:
            found_effects.append(effect['id'])
            print(f"  [OK] Effect '{effect['id']}' found")

    if len(found_effects) == len(critical_effect_ids):
        print(f"  [OK] All {len(critical_effect_ids)} critical status effects present")
    else:
        missing = set(critical_effect_ids) - set(found_effects)
        print(f"  [FAIL] Missing effects: {missing}")
        return False

    return True


def test_integration():
    """Test that components can be instantiated together"""
    print("\n[5/5] Testing integration...")

    from journal.status_monitor import StatusMonitor
    from journal.event_processor import EventProcessor

    # Create a mock callback
    def mock_callback(flag_name, is_active, effect_id, priority):
        print(f"    Callback triggered: {flag_name} -> {effect_id} (active={is_active}, priority={priority})")

    # Create test Status.json in temp location
    test_dir = Path("test_journal_verify")
    test_dir.mkdir(exist_ok=True)
    status_file = test_dir / "Status.json"

    # Write initial status
    import json
    with open(status_file, 'w') as f:
        json.dump({
            "timestamp": "2025-01-01T00:00:00Z",
            "event": "Status",
            "Flags": 0,
            "Flags2": 0
        }, f)

    print(f"  [OK] Created test Status.json: {status_file}")

    # Create StatusMonitor
    try:
        monitor = StatusMonitor(
            status_file_path=str(status_file),
            callback=mock_callback
        )
        print("  [OK] StatusMonitor instantiated")
    except Exception as e:
        print(f"  [FAIL] Failed to create StatusMonitor: {e}")
        return False

    # Try to start (will succeed even if file doesn't exist)
    try:
        if monitor.start():
            print("  [OK] StatusMonitor started")
            monitor.stop()
            print("  [OK] StatusMonitor stopped")
        else:
            print("  [FAIL] StatusMonitor failed to start")
            return False
    except Exception as e:
        print(f"  [FAIL] Error during start/stop: {e}")
        return False

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print("  [OK] Cleaned up test files")

    return True


def main():
    """Run all tests"""
    print("=" * 70)
    print("  Status Monitor Integration Verification")
    print("=" * 70)
    print()

    tests = [
        ("Module Imports", test_imports),
        ("Status Monitor Flags", test_status_monitor_flags),
        ("Event Processor Methods", test_event_processor_methods),
        ("Visual Effects Library", test_visual_effects),
        ("Component Integration", test_integration),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  [FAIL] Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print()
    print("=" * 70)
    print("  TEST RESULTS")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}  {name}")

    print()
    print(f"  Results: {passed}/{total} tests passed")

    if passed == total:
        print()
        print("  [OK] ALL TESTS PASSED!")
        print("  Status Monitor integration is ready to use.")
        print()
        print("  Next steps:")
        print("    1. Run application: python src/main.py")
        print("    2. Start Elite Dangerous")
        print("    3. Watch console for Status monitor messages")
        print("    4. Test in-game: deploy hardpoints, overheat, etc.")
        return 0
    else:
        print()
        print("  [FAIL] SOME TESTS FAILED")
        print("  Please fix the issues before running the application.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
