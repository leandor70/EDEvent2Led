"""
Test Status Monitor Integration
Standalone example demonstrating full integration of StatusMonitor with EventProcessor

This script:
1. Creates a test Status.json file
2. Initializes StatusMonitor to watch it
3. Simulates flag changes (Overheating, Interdiction, Combat, etc.)
4. Shows how EventProcessor receives and processes status flag callbacks

Usage:
    python tools/test_status_integration.py
"""
import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from journal.status_monitor import StatusMonitor


class MockEffectManager:
    """Mock UnifiedEffectManager for testing"""

    def __init__(self):
        self.devices = []
        self.active_effects = []

    def play_fused_effect(self, effect_id, devices=None, blocking=False):
        print(f"  [MockEffectManager] Playing effect: {effect_id}")
        self.active_effects.append(effect_id)

    def stop_all_effects(self):
        print(f"  [MockEffectManager] Stopping all effects")
        self.active_effects.clear()


class MockEventProcessor:
    """Mock EventProcessor to demonstrate callback handling"""

    def __init__(self, effect_manager):
        self.effect_manager = effect_manager
        self.active_status_effects = {}

    def process_status_flag(self, flag_name: str, is_active: bool, effect_id: str, priority: int):
        """Process Status flag change (called by StatusMonitor)"""

        if is_active:
            print(f"\n  [EventProcessor] Status flag ON: {flag_name}")
            print(f"                   Effect: {effect_id}, Priority: {priority}")

            # Simulate playing effect
            if self.effect_manager:
                self.effect_manager.play_fused_effect(
                    effect_id=effect_id,
                    devices=None,
                    blocking=False
                )

            # Track active effect
            self.active_status_effects[flag_name] = effect_id

        else:
            print(f"\n  [EventProcessor] Status flag OFF: {flag_name}")

            if flag_name in self.active_status_effects:
                effect_id = self.active_status_effects[flag_name]
                print(f"                   Stopping effect: {effect_id}")

                # In real implementation, would call effect_manager.cancel_effect(effect_id)
                # For now, just remove from tracking
                del self.active_status_effects[flag_name]

    def get_active_effects(self):
        """Get currently active status effects"""
        return self.active_status_effects.copy()


def create_status_file(test_dir: Path, flags: int, flags2: int = 0):
    """Create/update test Status.json file"""
    status_file = test_dir / "Status.json"

    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "Status",
        "Flags": flags,
        "Flags2": flags2
    }

    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return status_file


def main():
    """Run integration test"""
    print("=" * 70)
    print("  Status Monitor Integration Test")
    print("=" * 70)
    print()

    # Create test directory
    test_dir = Path("test_journal")
    test_dir.mkdir(exist_ok=True)
    status_file = test_dir / "Status.json"

    print(f"[INFO] Test directory: {test_dir.absolute()}")
    print(f"[INFO] Status file: {status_file}")
    print()

    # Initialize mock system
    print("[STEP 1] Initializing mock system...")
    effect_manager = MockEffectManager()
    event_processor = MockEventProcessor(effect_manager)
    print("  [OK] Mock system initialized")
    print()

    # Create initial Status.json (no flags)
    print("[STEP 2] Creating initial Status.json...")
    create_status_file(test_dir, flags=0, flags2=0)
    print("  [OK] Status.json created with no flags")
    print()

    # Initialize StatusMonitor
    print("[STEP 3] Starting StatusMonitor...")
    status_monitor = StatusMonitor(
        status_file_path=str(status_file),
        callback=event_processor.process_status_flag
    )

    if not status_monitor.start():
        print("[ERROR] Failed to start StatusMonitor")
        return 1

    print("  [OK] StatusMonitor started")
    print()

    # Wait for initial read
    time.sleep(0.5)

    # Test sequence: simulate various game states
    print("[STEP 4] Simulating game state changes...")
    print("-" * 70)

    test_sequence = [
        {
            "description": "Normal flight",
            "flags": 0,
            "flags2": 0,
            "wait": 1.5
        },
        {
            "description": "Deploy hardpoints (Combat Ready)",
            "flags": (1 << 6),  # Bit 6: HardpointsDeployed
            "flags2": 0,
            "wait": 2.0
        },
        {
            "description": "Ship overheating! (Critical)",
            "flags": (1 << 6) | (1 << 20),  # Hardpoints + Overheating
            "flags2": 0,
            "wait": 2.0
        },
        {
            "description": "Being interdicted! (Emergency)",
            "flags": (1 << 22),  # Bit 22: BeingInterdicted
            "flags2": 0,
            "wait": 2.0
        },
        {
            "description": "Interdiction escaped, entering supercruise",
            "flags": (1 << 4),  # Bit 4: Supercruise
            "flags2": 0,
            "wait": 2.0
        },
        {
            "description": "Low fuel warning",
            "flags": (1 << 4) | (1 << 19),  # Supercruise + LowFuel
            "flags2": 0,
            "wait": 2.0
        },
        {
            "description": "Fuel scooping",
            "flags": (1 << 4) | (1 << 11),  # Supercruise + ScoopingFuel
            "flags2": 0,
            "wait": 2.0
        },
        {
            "description": "Docked at station (Safe)",
            "flags": (1 << 0),  # Bit 0: Docked
            "flags2": 0,
            "wait": 1.5
        },
        {
            "description": "Disembarked (On foot - Odyssey)",
            "flags": 0,
            "flags2": (1 << 0),  # Flags2 bit 0: OnFoot
            "wait": 2.0
        },
        {
            "description": "Low oxygen warning!",
            "flags": 0,
            "flags2": (1 << 0) | (1 << 6),  # OnFoot + LowOxygen
            "wait": 2.0
        },
        {
            "description": "All systems normal",
            "flags": 0,
            "flags2": 0,
            "wait": 1.0
        }
    ]

    for i, step in enumerate(test_sequence, 1):
        print(f"\n[{i}/{len(test_sequence)}] {step['description']}")
        print(f"      Flags: {step['flags']:#034b} ({step['flags']})")
        print(f"      Flags2: {step['flags2']:#034b} ({step['flags2']})")

        # Update Status.json
        create_status_file(test_dir, step['flags'], step['flags2'])

        # Wait for StatusMonitor to detect change
        time.sleep(step['wait'])

    print()
    print("-" * 70)

    # Show final state
    print()
    print("[STEP 5] Final state")
    active_effects = event_processor.get_active_effects()
    print(f"  Active status effects: {len(active_effects)}")
    for flag_name, effect_id in active_effects.items():
        print(f"    - {flag_name}: {effect_id}")
    print()

    # Cleanup
    print("[STEP 6] Cleanup")
    status_monitor.stop()
    print("  [OK] StatusMonitor stopped")
    print()

    print("=" * 70)
    print("  Test completed successfully!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
