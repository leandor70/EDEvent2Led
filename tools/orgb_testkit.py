"""
OpenRGB SDK test kit: record and replay the TCP conversation with an OpenRGB server.

Used to migrate from openrgb-python (GPLv3) to the built-in client without
changing behavior:

  RecordingProxy  sits between a client and the real OpenRGB server and logs
                  every packet in both directions. Read-only use: it forwards,
                  it never sends anything of its own.
  ReplayServer    a fake OpenRGB server. Answers each request with what the
                  real server answered during a recording, and logs every
                  packet the client sends. No hardware is touched.

Packet format (all little-endian): "ORGB" | device u32 | command u32 | size u32 | payload
"""
from __future__ import annotations

import json
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HEADER = struct.Struct("<4sIII")
MAGIC = b"ORGB"

# Commands that never get a reply: the client just sends them.
WRITE_COMMANDS = {1050, 1051, 1052, 1100, 1101, 1102, 50, 1000, 1001}

COMMAND_NAMES = {
    0: "REQUEST_CONTROLLER_COUNT", 1: "REQUEST_CONTROLLER_DATA",
    40: "REQUEST_PROTOCOL_VERSION", 50: "SET_CLIENT_NAME", 51: "DEVICE_LIST_UPDATED",
    150: "REQUEST_PROFILE_LIST", 151: "REQUEST_SAVE_PROFILE", 152: "REQUEST_LOAD_PROFILE",
    153: "REQUEST_DELETE_PROFILE", 200: "REQUEST_PLUGIN_LIST", 250: "PLUGIN_SPECIFIC",
    1000: "RGBCONTROLLER_RESIZEZONE", 1050: "RGBCONTROLLER_UPDATELEDS",
    1051: "RGBCONTROLLER_UPDATEZONELEDS", 1052: "RGBCONTROLLER_UPDATESINGLELED",
    1100: "RGBCONTROLLER_SETCUSTOMMODE", 1101: "RGBCONTROLLER_UPDATEMODE",
    1102: "RGBCONTROLLER_SAVEMODE",
}


def packet(device: int, command: int, payload: bytes) -> bytes:
    return HEADER.pack(MAGIC, device, command, len(payload)) + payload


class PacketReader:
    """Splits a TCP byte stream into packets."""

    def __init__(self) -> None:
        self._buf = b""

    def feed(self, data: bytes) -> List[Tuple[int, int, bytes]]:
        self._buf += data
        out = []
        while len(self._buf) >= HEADER.size:
            magic, dev, cmd, size = HEADER.unpack_from(self._buf)
            if magic != MAGIC:
                raise ValueError(f"bad magic {magic!r}")
            if len(self._buf) < HEADER.size + size:
                break
            out.append((dev, cmd, self._buf[HEADER.size:HEADER.size + size]))
            self._buf = self._buf[HEADER.size + size:]
        return out


def entry(direction: str, dev: int, cmd: int, payload: bytes) -> dict:
    return {"dir": direction, "dev": dev, "cmd": cmd,
            "name": COMMAND_NAMES.get(cmd, str(cmd)), "payload": payload.hex()}


# ── Recording proxy ────────────────────────────────────────────────────────────


class RecordingProxy:
    """Listens on 127.0.0.1:<port>, forwards one client to the real server, logs packets."""

    def __init__(self, upstream: Tuple[str, int]) -> None:
        self.upstream = upstream
        self.log: List[dict] = []
        self._lock = threading.Lock()
        self._srv = socket.socket()
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(1)
        self.port = self._srv.getsockname()[1]
        self._threads: List[threading.Thread] = []
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        try:
            client, _ = self._srv.accept()
        except OSError:
            return
        server = socket.create_connection(self.upstream)
        for src, dst, direction in ((client, server, "c2s"), (server, client, "s2c")):
            t = threading.Thread(target=self._pump, args=(src, dst, direction), daemon=True)
            t.start()
            self._threads.append(t)

    def _pump(self, src: socket.socket, dst: socket.socket, direction: str) -> None:
        reader = PacketReader()
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                with self._lock:
                    for dev, cmd, payload in reader.feed(data):
                        self.log.append(entry(direction, dev, cmd, payload))
                dst.sendall(data)
        except OSError:
            pass
        finally:
            for s in (src, dst):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def close(self) -> None:
        self._srv.close()
        for t in self._threads:
            t.join(timeout=2)


# ── Replay server ──────────────────────────────────────────────────────────────


def build_replies(log: List[dict]) -> Dict[Tuple[int, int, str], List[dict]]:
    """Map each recorded request (dev, cmd, payload) to the packets the server sent after it."""
    replies: Dict[Tuple[int, int, str], List[dict]] = {}
    current: Optional[Tuple[int, int, str]] = None
    for e in log:
        if e["dir"] == "c2s":
            current = (e["dev"], e["cmd"], e["payload"])
            replies.setdefault(current, [])
        elif current is not None and e["cmd"] != 51:     # DEVICE_LIST_UPDATED is unsolicited
            if e not in replies[current]:
                replies[current].append(e)
    return replies


class ScriptServer:
    """Fake OpenRGB server driven by a handler.

    handler(dev, cmd, payload) -> list of (dev, cmd, payload) packets to send back
    (empty list = no reply). Every packet the client sends is logged.
    """

    def __init__(self, handler) -> None:
        self.handler = handler
        self.received: List[dict] = []
        self._lock = threading.Lock()
        self._conns: List[socket.socket] = []
        self._srv = socket.socket()
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(4)
        self.port = self._srv.getsockname()[1]
        self._stop = False
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        while not self._stop:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                return
            with self._lock:
                self._conns.append(conn)
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        reader = PacketReader()
        try:
            while True:
                data = conn.recv(65536)
                if not data:
                    return
                for dev, cmd, payload in reader.feed(data):
                    with self._lock:
                        self.received.append(entry("c2s", dev, cmd, payload))
                    out = b"".join(packet(d, c, p) for d, c, p in self.handler(dev, cmd, payload))
                    if out:
                        conn.sendall(out)
        except OSError:
            pass
        finally:
            conn.close()

    def push(self, dev: int, cmd: int, payload: bytes = b"") -> None:
        """Send an unsolicited packet to every connected client."""
        with self._lock:
            for c in self._conns:
                try:
                    c.sendall(packet(dev, cmd, payload))
                except OSError:
                    pass

    def drop_clients(self) -> None:
        """Close every client connection (simulates OpenRGB going away)."""
        with self._lock:
            conns, self._conns = self._conns, []
        for c in conns:
            try:
                c.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            c.close()

    def take(self) -> List[dict]:
        """Packets received since the last take()."""
        with self._lock:
            out, self.received = self.received, []
        return out

    def close(self) -> None:
        self._stop = True
        self.drop_clients()
        self._srv.close()


class ReplayServer(ScriptServer):
    """Fake OpenRGB server: replays recorded replies, logs what the client sends."""

    def __init__(self, recorded: List[dict]) -> None:
        self.replies = build_replies(recorded)
        self.unknown: List[dict] = []
        super().__init__(self._replay)

    def _replay(self, dev: int, cmd: int, payload: bytes):
        key = (dev, cmd, payload.hex())
        if key in self.replies:
            return [(r["dev"], r["cmd"], bytes.fromhex(r["payload"])) for r in self.replies[key]]
        if cmd not in WRITE_COMMANDS:
            self.unknown.append(entry("c2s", dev, cmd, payload))
        return []


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def settle(seconds: float = 0.3) -> None:
    time.sleep(seconds)
