"""ScreenCapturerService — singleton per la cattura schermo (WGC/DXGI/mss + auto-switch).

Fornisce get_latest_frame() thread-safe per uso da AmbilightService.
"""

import ctypes
import importlib.util
import threading
import time
from typing import Optional

import numpy as np


# ── Capturer implementations ─────────────────────────────────────────────────


class _WGCCapturer:
    """Windows.Graphics.Capture — coesiste con Chrome (Win10 1903+)."""

    def __init__(self, fps: int):
        from windows_capture import WindowsCapture

        self._fps = fps
        self._latest: Optional[np.ndarray] = None
        self._lock = threading.Lock()

        cap = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            monitor_index=1,
            minimum_update_interval=33,
        )

        @cap.event
        def on_frame_arrived(frame, _capture_control):
            # frame.frame_buffer è una VIEW in memoria ctypes gestita da Rust:
            # diventa invalida quando il callback ritorna → .copy() obbligatorio
            bgr = frame.frame_buffer[:, :, :3].copy()
            with self._lock:
                self._latest = bgr

        @cap.event
        def on_closed():
            pass

        self._ctrl = cap.start_free_threaded()

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            with self._lock:
                if self._latest is not None:
                    break
            time.sleep(0.05)

        print("[ScreenCapturer] WGC (Windows.Graphics.Capture)")

    def grab(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest

    def set_fps(self, fps: int) -> None:
        self._fps = fps  # WGC: rate limit gestito dal loop chiamante

    def stop(self) -> None:
        try:
            self._ctrl.stop()
        except Exception:
            pass


class _DxcamCapturer:
    """DXGI Desktop Duplication — cattura exclusive fullscreen, conflitto con Chrome GPU."""

    _RECOVERABLE = ("0x887a0026", "access lost", "access_lost", "output-change")

    def __init__(self, fps: int):
        import dxcam
        self._dxcam = dxcam
        self._fps   = fps
        # set_fps() (thread API), grab() (thread ambilight) e stop() toccano la
        # camera: senza lock grab() vedrebbe is_capturing False durante un
        # riavvio e lo scambierebbe per un loop morto.
        self._cam_lock = threading.RLock()
        self._stopped  = False
        # BGRA e non BGR: la conversione a BGR di dxcam passa da OpenCV, che
        # dxcam non installa -> nell'exe impacchettato non arrivavano frame.
        self._cam   = dxcam.create(output_color="BGRA")
        self._cam.start(target_fps=fps)
        print(f"[ScreenCapturer] DXGI (dxcam, target {fps} fps)")

    def _capture_thread_dead(self) -> bool:
        # Se il recupero interno di dxcam fallisce (cambio modalita' video,
        # lock screen, UAC, driver reset) il thread di cattura muore in silenzio:
        # get_latest_frame() continua a restituire l'ultimo frame senza eccezioni.
        thread = getattr(self._cam, "_DXCamera__thread", None)
        if thread is not None and not thread.is_alive():
            return True
        # Quando il loop va in errore dxcam azzera il proprio thread (None) e
        # mette is_capturing a False prima di rilanciare: il controllo sul
        # thread da solo non lo vede. Noi fermiamo la camera solo dentro
        # _recover/set_fps/stop, quindi qui is_capturing False = loop morto.
        return not getattr(self._cam, "is_capturing", True)

    def grab(self) -> Optional[np.ndarray]:
        try:
            with self._cam_lock:
                if self._stopped:
                    return None
                if self._capture_thread_dead():
                    self._recover()
                cam = self._cam
            frame = cam.get_latest_frame()
            return None if frame is None else frame[:, :, :3]
        except Exception as exc:
            if any(t in str(exc).lower() for t in self._RECOVERABLE):
                with self._cam_lock:
                    if not self._stopped:
                        self._recover()
            return None

    def _recover(self) -> None:
        print("[ScreenCapturer] DXGI access lost — recupero...")
        for fn in ("stop", "release"):
            try:
                getattr(self._cam, fn)()
            except Exception:
                pass
        time.sleep(0.5)
        # Il desktop puo' restare in transizione a lungo (cambio modalita',
        # lock screen): riprova con backoff crescente invece di arrendersi.
        for attempt in range(1, 11):
            try:
                self._cam = self._dxcam.create(output_color="BGRA")
                self._cam.start(target_fps=self._fps)
                print(f"[ScreenCapturer] DXGI recuperato ({attempt}/10)")
                return
            except Exception as exc:
                print(f"[ScreenCapturer] Recupero {attempt}/10 fallito: {exc}")
                for fn in ("stop", "release"):
                    try:
                        getattr(self._cam, fn)()
                    except Exception:
                        pass
                time.sleep(min(1.0 * attempt, 5.0))
        raise RuntimeError("[ScreenCapturer] DXGI: impossibile recuperare dopo 10 tentativi")

    def set_fps(self, fps: int) -> None:
        if fps == self._fps:
            return
        with self._cam_lock:
            if self._stopped:
                return
            try:
                self._cam.stop()
            except Exception:
                pass
            self._fps = fps
            self._cam = self._dxcam.create(output_color="BGRA")
            self._cam.start(target_fps=fps)

    def stop(self) -> None:
        with self._cam_lock:
            # Dopo stop() is_capturing e' False: senza questo flag un grab()
            # in volo lo prenderebbe per un loop morto e riavvierebbe la camera.
            self._stopped = True
            try:
                self._cam.stop()
            except Exception:
                pass


class _MssCapturer:
    """GDI screenshot — CPU-only, nessun conflitto GPU, no exclusive fullscreen."""

    def __init__(self) -> None:
        import mss
        self._sct     = mss.MSS()
        self._monitor = self._sct.monitors[1]
        print(f"[ScreenCapturer] mss ({self._monitor['width']}x{self._monitor['height']})")

    def grab(self) -> Optional[np.ndarray]:
        shot = self._sct.grab(self._monitor)
        arr  = np.frombuffer(shot.bgra, dtype=np.uint8).reshape((shot.height, shot.width, 4))
        return arr[:, :, :3]

    def set_fps(self, fps: int) -> None:
        pass

    def stop(self) -> None:
        self._sct.close()


# ── Auto-switch ───────────────────────────────────────────────────────────────


class _AutoSwitch:
    """Rileva frame congelati (exclusive FS) e switcha WGC <-> DXGI automaticamente."""

    STUCK_SECS  = 2.5   # frame diff sotto soglia per questo tempo -> switch a DXGI
    TRIAL_SECS  = 2.0   # durata prova WGC dopo cambio finestra foreground
    DIFF_MIN    = 3.0   # avg pixel diff < soglia = frame "congelato"
    CHECK_EVERY = 8     # ogni N frame (a 15fps ~ ogni 0.5s)

    def __init__(self, service: 'ScreenCapturerService') -> None:
        self._svc          = service
        self.prev_sample:  Optional[np.ndarray] = None
        self.stuck_since:  Optional[float]      = None
        self.fg_at_switch: int                  = 0
        self.trial_since:  Optional[float]      = None
        self.mode:         str                  = service.capturer_name

    @staticmethod
    def _sample(frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        return frame[max(0, h // 2 - 75): h // 2 + 75,
                     max(0, w // 2 - 100): w // 2 + 100]

    def _swap(self, preferred: str) -> bool:
        try:
            fps = getattr(self._svc._capturer, '_fps', 15)
            self._svc._switch_capturer(fps, preferred)
            self.mode        = self._svc.capturer_name
            self.prev_sample = None
            self.stuck_since = None
            self.trial_since = None
            print(f"[ScreenCapturer] Auto-switch -> {self._svc.capturer_name}")
            return True
        except Exception as exc:
            print(f"[ScreenCapturer] Auto-switch '{preferred}' fallito: {exc}")
            return False

    @staticmethod
    def _wgc_installed() -> bool:
        # Senza windows-capture lo swap DXGI->WGC fallirebbe: dxcam e' un singleton
        # e creare un secondo capturer dxcam mentre il primo gira da' "already running".
        return importlib.util.find_spec("windows_capture") is not None

    def _get_fg(self) -> int:
        try:
            return ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            return 0

    def check(self, frame: np.ndarray, now: float) -> None:
        sample = self._sample(frame)

        if self.prev_sample is not None and self.prev_sample.shape == sample.shape:
            diff = float(np.abs(
                sample.astype(np.float32) - self.prev_sample.astype(np.float32)
            ).mean())

            if self.trial_since is not None:
                if diff >= self.DIFF_MIN:
                    # WGC riceve frame freschi -> confermato, resta su WGC
                    self.trial_since = None
                    self.stuck_since = None
                elif now - self.trial_since >= self.TRIAL_SECS:
                    # Ancora congelato -> torna a DXGI
                    if self._swap("dxcam"):
                        self.fg_at_switch = self._get_fg()

            elif self.mode == "WGC":
                if diff < self.DIFF_MIN:
                    if self.stuck_since is None:
                        self.stuck_since = now
                    elif now - self.stuck_since >= self.STUCK_SECS:
                        # Sospetto exclusive fullscreen -> switch a DXGI
                        self.fg_at_switch = self._get_fg()
                        self._swap("dxcam")
                else:
                    self.stuck_since = None

            elif self.mode == "DXGI" and self._wgc_installed():
                fg = self._get_fg()
                if fg != 0 and fg != self.fg_at_switch:
                    # Finestra foreground cambiata -> prova ritorno a WGC
                    if self._swap("wgc"):
                        self.trial_since = now

        self.prev_sample = sample.copy()


# ── Singleton service ─────────────────────────────────────────────────────────


class ScreenCapturerService:
    """
    Singleton per la cattura schermo. Thread-safe.

    Uso::

        svc = ScreenCapturerService.get_instance()
        svc.start(fps=15, preferred="auto")
        frame = svc.get_latest_frame()   # np.ndarray BGR o None
        svc.stop()
    """

    _instance: Optional['ScreenCapturerService'] = None
    _cls_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'ScreenCapturerService':
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    obj = cls.__new__(cls)
                    obj._init_state()
                    cls._instance = obj
        return cls._instance

    def _init_state(self) -> None:
        self._capturer                           = None
        self._capturer_name: str                 = "—"
        self._lock           = threading.Lock()
        self._auto_switch: Optional[_AutoSwitch] = None
        self._frame_idx: int                     = 0

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def capturer_name(self) -> str:
        return self._capturer_name

    @property
    def is_running(self) -> bool:
        return self._capturer is not None

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, fps: int = 15, preferred: str = "auto") -> None:
        """Avvia il capturer. Idempotente se gia avviato."""
        with self._lock:
            if self._capturer is not None:
                return
            self._capturer    = self._make_capturer(fps, preferred)
            self._auto_switch = _AutoSwitch(self) if preferred == "auto" else None

    def stop(self) -> None:
        with self._lock:
            cap                 = self._capturer
            self._capturer      = None
            self._capturer_name = "—"
            self._auto_switch   = None
        if cap is not None:
            try:
                cap.stop()
            except Exception:
                pass

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Restituisce l'ultimo frame BGR o None. Chiama l'auto-switch ogni CHECK_EVERY frame."""
        cap = self._capturer
        if cap is None:
            return None
        try:
            frame = cap.grab()
        except Exception:
            return None
        if frame is None:
            return None

        self._frame_idx += 1
        sw = self._auto_switch
        if sw is not None and self._frame_idx % _AutoSwitch.CHECK_EVERY == 0:
            sw.check(frame, time.monotonic())

        return frame

    def set_fps(self, fps: int) -> None:
        cap = self._capturer
        if cap is not None:
            try:
                cap.set_fps(fps)
            except Exception:
                pass

    # ── Internal ───────────────────────────────────────────────────────────────

    def _make_capturer(self, fps: int, preferred: str):
        def _try_wgc():
            c = _WGCCapturer(fps)
            self._capturer_name = "WGC"
            return c

        def _try_dxcam():
            c = _DxcamCapturer(fps)
            self._capturer_name = "DXGI"
            return c

        def _use_mss():
            self._capturer_name = "mss"
            return _MssCapturer()

        if preferred == "wgc":
            try:
                return _try_wgc()
            except Exception as exc:
                print(f"[ScreenCapturer] WGC non disponibile ({exc}), provo dxcam")
            try:
                return _try_dxcam()
            except Exception as exc:
                print(f"[ScreenCapturer] dxcam non disponibile ({exc}), fallback mss")
                return _use_mss()
        elif preferred == "dxcam":
            try:
                return _try_dxcam()
            except Exception as exc:
                print(f"[ScreenCapturer] dxcam non disponibile ({exc}), fallback mss")
                return _use_mss()
        elif preferred == "mss":
            return _use_mss()

        # auto: WGC -> dxcam -> mss
        try:
            return _try_wgc()
        except ImportError:
            print("[ScreenCapturer] windows-capture non installato - provo dxcam")
        except Exception as exc:
            print(f"[ScreenCapturer] WGC init fallita ({exc}) - provo dxcam")
        try:
            return _try_dxcam()
        except ImportError:
            print("[ScreenCapturer] dxcam non installato - fallback mss (no exclusive FS)")
        except Exception as exc:
            print(f"[ScreenCapturer] dxcam init fallita ({exc}) - fallback mss")
        return _use_mss()

    def _switch_capturer(self, fps: int, preferred: str) -> None:
        """Sostituisce il capturer (chiamato dall'auto-switch nel thread del idle loop)."""
        new = self._make_capturer(fps, preferred)  # lento: fuori dal lock
        with self._lock:
            if self._capturer is None:
                # stop() e' stato chiamato mentre inizializzavamo il nuovo capturer
                try:
                    new.stop()
                except Exception:
                    pass
                return
            old            = self._capturer
            self._capturer = new
        if old is not None:
            try:
                old.stop()
            except Exception:
                pass
