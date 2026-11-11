"""
test_capturer_recovery.py

Verifica _DxcamCapturer con una camera dxcam finta:

  1. camera sana: nessun recupero
  2. loop crashato (thread azzerato a None + is_capturing False): camera ricreata
  3. thread presente ma morto: camera ricreata (caso gia' coperto)
  4. set_fps: riavvia la camera senza che grab() lo scambi per un crash
  5. stop(): un grab() successivo non riavvia la camera

Nessuna GPU ne' dxcam reale. Output ASCII-safe (regola Windows-unicode-handling).
"""
import sys
import threading
from pathlib import Path
from types import ModuleType

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import screen_capturer_service as scs  # noqa: E402

_failures = []


def check(label, ok, detail=""):
    print(f"  {'[OK]' if ok else '[FAIL]'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failures.append(label)


class FakeCam:
    """Replica lo stato di DXCamera dopo un'eccezione nel loop di cattura."""

    def __init__(self):
        self.is_capturing = False
        self._DXCamera__thread = None
        self.crashed = False

    def start(self, target_fps=60):
        self.is_capturing = True

    def stop(self):
        self.is_capturing = False

    def release(self):
        pass

    def crash(self):
        self.crashed = True
        self.is_capturing = False
        self._DXCamera__thread = None

    def get_latest_frame(self):
        return None if self.crashed else np.zeros((8, 8, 4), dtype=np.uint8)


def make_capturer():
    created = []

    def create(output_color="BGRA"):
        cam = FakeCam()
        created.append(cam)
        return cam

    fake = ModuleType("dxcam")
    fake.create = create
    sys.modules["dxcam"] = fake
    scs.time.sleep = lambda s: None
    return scs._DxcamCapturer(15), created


def main():
    print("=" * 70)
    print("  Test recupero cattura DXGI")
    print("=" * 70)

    print("\n1. camera sana")
    cap, created = make_capturer()
    check("frame restituito", cap.grab() is not None)
    check("nessuna camera ricreata", len(created) == 1, len(created))

    print("\n2. loop crashato (thread None, is_capturing False)")
    cap, created = make_capturer()
    created[0].crash()
    frame = cap.grab()
    frame = frame if frame is not None else cap.grab()
    check("camera ricreata e attiva", len(created) == 2 and created[1].is_capturing, len(created))
    check("frame di nuovo disponibile", frame is not None)

    print("\n3. thread presente ma morto")
    cap, created = make_capturer()
    t = threading.Thread(target=lambda: None)
    t.start()
    t.join()
    created[0]._DXCamera__thread = t
    created[0].is_capturing = True
    cap.grab()
    check("camera ricreata", len(created) == 2, len(created))

    print("\n4. set_fps")
    cap, created = make_capturer()
    cap.set_fps(30)
    check("camera ricreata una sola volta dal cambio fps", len(created) == 2, len(created))
    cap.grab()
    check("grab dopo set_fps non innesca un recupero", len(created) == 2, len(created))

    print("\n5. stop")
    cap, created = make_capturer()
    cap.stop()
    check("grab dopo stop non restituisce frame", cap.grab() is None)
    check("grab dopo stop non riavvia la camera", len(created) == 1 and not created[0].is_capturing)
    cap.set_fps(30)
    check("set_fps dopo stop non crea camere", len(created) == 1, len(created))

    print()
    if _failures:
        print(f"  [FAIL] {len(_failures)} controlli falliti")
        return 1
    print("  [OK] TUTTI I CONTROLLI PASSATI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
