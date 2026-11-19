"""
Read-only diagnosis of the OpenRGB SDK server.

Tells apart the cases that a plain "connection failed" mixes up:

  connected            OpenRGB answered on host:port
  openrgb_no_sdk       port closed, an OpenRGB process runs: its SDK server is off
  openrgb_other_port   port closed, OpenRGB listens on another port
  not_running          port closed, no OpenRGB process
  port_busy_other      port open but the program on it is not OpenRGB
  no_reply             port open, nothing answered in time
  remote_unreachable   host is not this PC and the port does not answer

Warning (with any code): "multiple_instances" when more than one OpenRGB
process runs. Two instances fight over the SDK port and over the hardware.

It never starts, stops or reconfigures anything. On a remote host only the
protocol probe runs (processes of another PC cannot be seen from here).

The result carries codes and data only: the UI builds the sentences in its
own language (web/config/i18n/*.json, block "openrgb_diag").
"""

import ctypes
import socket
import struct
import sys
from ctypes import wintypes
from typing import Dict, List, Optional

from utils.openrgb_client import CMD_REQUEST_CONTROLLER_COUNT

_MAGIC = b"ORGB"
_HEADER = struct.Struct("<4sIII")        # magic, device index, command, payload size
_CONNECT_TIMEOUT_S = 1.0          # remote host
_LOCAL_CONNECT_TIMEOUT_S = 0.3    # per address, this PC
_REPLY_TIMEOUT_S = 1.5
_OPENRGB_EXE = "openrgb.exe"


# ── Host helpers ──────────────────────────────────────────────────────────────

def is_local_host(host: str) -> bool:
    """True when host names this PC (loopback, or one of its own addresses)."""
    h = (host or "").strip().lower()
    if h in ("localhost", "::1", "0.0.0.0", "") or h.startswith("127."):
        return True
    try:
        addr = socket.gethostbyname(h)
    except OSError:
        return False
    if addr.startswith("127."):
        return True
    try:
        own = socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        own = []
    return addr in own


# ── Protocol probe ────────────────────────────────────────────────────────────

def _connect(host: str, port: int) -> socket.socket:
    """TCP connect. On this PC IPv4 is tried first with a short timeout:
    'localhost' resolves to ::1 first, OpenRGB listens on IPv4 only, and
    Windows retries a refused loopback connect for about 2 s instead of
    failing at once. A live local server accepts in well under a millisecond."""
    if not is_local_host(host):
        return socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT_S)
    try:
        infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    except OSError:
        infos = []
    infos.sort(key=lambda i: 0 if i[0] == socket.AF_INET else 1)
    if not infos:
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", port))]
    last: Optional[OSError] = None
    for family, socktype, proto, _name, addr in infos:
        s = socket.socket(family, socktype, proto)
        s.settimeout(_LOCAL_CONNECT_TIMEOUT_S)
        try:
            s.connect(addr)
            return s
        except OSError as exc:
            last = exc
            s.close()
    raise last or OSError("no address")


def probe_protocol(host: str, port: int) -> Dict:
    """Open host:port and ask for the controller count, the one request that
    every OpenRGB version answers. Read-only: nothing is changed on the server.

    Returns {"state": "closed" | "openrgb" | "other" | "no_reply",
             "device_count": int | None, "error": str}
    """
    try:
        sock = _connect(host, port)
    except OSError as exc:
        return {"state": "closed", "device_count": None, "error": str(exc)}
    try:
        sock.settimeout(_REPLY_TIMEOUT_S)
        sock.sendall(_HEADER.pack(_MAGIC, 0, CMD_REQUEST_CONTROLLER_COUNT, 0))
        header = b""
        while len(header) < _HEADER.size:
            chunk = sock.recv(_HEADER.size - len(header))
            if not chunk:
                # Accepted, then hung up: not the OpenRGB protocol
                return {"state": "other", "device_count": None, "error": "connection closed"}
            header += chunk
            if not _MAGIC.startswith(header[:4]):
                return {"state": "other", "device_count": None, "error": "unexpected data"}
        magic, _dev, cmd, size = _HEADER.unpack(header)
        if magic != _MAGIC:
            return {"state": "other", "device_count": None, "error": "unexpected data"}
        count = None
        if cmd == CMD_REQUEST_CONTROLLER_COUNT and size >= 4:
            payload = b""
            while len(payload) < 4:
                chunk = sock.recv(4 - len(payload))
                if not chunk:
                    break
                payload += chunk
            if len(payload) == 4:
                count = struct.unpack("<I", payload)[0]
        return {"state": "openrgb", "device_count": count, "error": ""}
    except socket.timeout:
        return {"state": "no_reply", "device_count": None, "error": "timeout"}
    except OSError as exc:
        return {"state": "other", "device_count": None, "error": str(exc)}
    finally:
        try:
            sock.close()
        except OSError:
            pass


# ── Windows: who listens on which port ────────────────────────────────────────

_AF_INET, _AF_INET6 = 2, 23
_TCP_TABLE_OWNER_PID_LISTENER = 3
_ERROR_INSUFFICIENT_BUFFER = 122
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _listeners() -> List[Dict]:
    """Every listening TCP socket on this PC: [{"port", "pid"}] (IPv4 + IPv6)."""
    if sys.platform != "win32":
        return []
    iphlpapi = ctypes.WinDLL("iphlpapi")
    out: List[Dict] = []
    for family, row_size, port_off, pid_off in (
        (_AF_INET, 24, 8, 20),     # MIB_TCPROW_OWNER_PID: 6 DWORDs
        (_AF_INET6, 56, 20, 52),   # MIB_TCP6ROW_OWNER_PID
    ):
        size = wintypes.DWORD(0)
        iphlpapi.GetExtendedTcpTable(None, ctypes.byref(size), False, family,
                                     _TCP_TABLE_OWNER_PID_LISTENER, 0)
        for _ in range(3):   # the table can grow between the two calls
            buf = ctypes.create_string_buffer(size.value or 4)
            rc = iphlpapi.GetExtendedTcpTable(buf, ctypes.byref(size), False, family,
                                              _TCP_TABLE_OWNER_PID_LISTENER, 0)
            if rc != _ERROR_INSUFFICIENT_BUFFER:
                break
        if rc != 0:
            continue
        raw = buf.raw
        (count,) = struct.unpack_from("<I", raw, 0)
        for i in range(count):
            base = 4 + i * row_size
            # The port is in network byte order in the low 16 bits of a DWORD
            port = struct.unpack_from(">H", raw, base + port_off)[0]
            (pid,) = struct.unpack_from("<I", raw, base + pid_off)
            out.append({"port": port, "pid": pid})
    return out


def _kernel32():
    """kernel32 with the signatures this module uses: on 64-bit Windows a
    HANDLE passed without argtypes is truncated to a 32-bit int."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    return k32


def _process_path(pid: int) -> str:
    """Full path of a process image, '' when Windows does not tell us."""
    if sys.platform != "win32" or pid <= 4:
        return ""
    k32 = _kernel32()
    h = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buf))
        if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        k32.CloseHandle(h)


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
    ]


def _processes() -> Dict[int, str]:
    """{pid: exe name} of every running process."""
    if sys.platform != "win32":
        return {}
    k32 = _kernel32()
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
    if not snap or snap == ctypes.c_void_p(-1).value:    # INVALID_HANDLE_VALUE
        return {}
    procs: Dict[int, str] = {}
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            procs[entry.th32ProcessID] = entry.szExeFile
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return procs


class _SERVICE_STATUS_PROCESS(ctypes.Structure):
    _fields_ = [(n, wintypes.DWORD) for n in (
        "dwServiceType", "dwCurrentState", "dwControlsAccepted", "dwWin32ExitCode",
        "dwServiceSpecificExitCode", "dwCheckPoint", "dwWaitHint", "dwProcessId",
        "dwServiceFlags")]


class _ENUM_SERVICE_STATUS_PROCESSW(ctypes.Structure):
    _fields_ = [("lpServiceName", wintypes.LPWSTR), ("lpDisplayName", wintypes.LPWSTR),
                ("ServiceStatusProcess", _SERVICE_STATUS_PROCESS)]


def _services_by_pid() -> Dict[int, str]:
    """{pid: service display name} of the running Win32 services."""
    if sys.platform != "win32":
        return {}
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    adv.OpenSCManagerW.restype = wintypes.HANDLE
    adv.OpenSCManagerW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    adv.EnumServicesStatusExW.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD), wintypes.LPCWSTR]
    adv.CloseServiceHandle.argtypes = [wintypes.HANDLE]
    scm =adv.OpenSCManagerW(None, None, 0x0004)          # SC_MANAGER_ENUMERATE_SERVICE
    if not scm:
        return {}
    result: Dict[int, str] = {}
    try:
        needed, count, resume = wintypes.DWORD(0), wintypes.DWORD(0), wintypes.DWORD(0)
        # SC_ENUM_PROCESS_INFO=0, SERVICE_WIN32=0x30, SERVICE_ACTIVE=1
        adv.EnumServicesStatusExW(scm, 0, 0x30, 1, None, 0, ctypes.byref(needed),
                                  ctypes.byref(count), ctypes.byref(resume), None)
        if not needed.value:
            return {}
        buf = ctypes.create_string_buffer(needed.value + 4096)
        resume = wintypes.DWORD(0)
        if not adv.EnumServicesStatusExW(scm, 0, 0x30, 1, buf, len(buf), ctypes.byref(needed),
                                         ctypes.byref(count), ctypes.byref(resume), None):
            return {}
        arr = ctypes.cast(buf, ctypes.POINTER(_ENUM_SERVICE_STATUS_PROCESSW))
        for i in range(count.value):
            pid = arr[i].ServiceStatusProcess.dwProcessId
            if pid:
                result[pid] = arr[i].lpDisplayName or arr[i].lpServiceName or ""
    finally:
        adv.CloseServiceHandle(scm)
    return result


def _describe(pid: int, name: str, services: Dict[int, str]) -> Dict:
    """One process as the UI shows it."""
    return {
        "pid": pid,
        "name": name,
        "path": _process_path(pid),
        "service": services.get(pid, ""),   # '' = ordinary process
    }


# ── Diagnosis ─────────────────────────────────────────────────────────────────

def diagnose(host: str, port: int) -> Dict:
    """Diagnose the OpenRGB SDK server at host:port. Never raises.

    Returns {
        "code": see module docstring,
        "host", "port", "local": bool,
        "device_count": int | None,      # only when code == "connected"
        "owner": {pid, name, path, service} | None,   # who listens on `port`
        "openrgb_processes": [{pid, name, path, service, ports}],
        "other_ports": [int],            # ports an OpenRGB process listens on
        "warnings": ["multiple_instances"],
        "error": str,                    # raw detail, for the log only
    }
    """
    port = int(port)
    local = is_local_host(host)
    result: Dict = {
        "code": "", "host": host, "port": port, "local": local,
        "device_count": None, "owner": None, "openrgb_processes": [],
        "other_ports": [], "warnings": [], "error": "",
    }

    probe = probe_protocol(host, port)
    result["error"] = probe["error"]

    if local:
        try:
            procs = _processes()
            listeners = _listeners()
            services = _services_by_pid()
        except Exception as exc:                 # diagnosis must never break startup
            procs, listeners, services = {}, [], {}
            result["error"] = (result["error"] + f" | process scan failed: {exc}").strip(" |")

        owner_pid = next((l["pid"] for l in listeners if l["port"] == port), None)
        if owner_pid is not None:
            result["owner"] = _describe(owner_pid, procs.get(owner_pid, ""), services)

        for pid, name in sorted(procs.items()):
            if name.lower() == _OPENRGB_EXE:
                info = _describe(pid, name, services)
                info["ports"] = sorted({l["port"] for l in listeners if l["pid"] == pid})
                result["openrgb_processes"].append(info)
        result["other_ports"] = sorted({p for o in result["openrgb_processes"]
                                        for p in o["ports"] if p != port})
        if len(result["openrgb_processes"]) > 1:
            result["warnings"].append("multiple_instances")

    state = probe["state"]
    if state == "openrgb":
        result["code"] = "connected"
        result["device_count"] = probe["device_count"]
    elif state == "other":
        result["code"] = "port_busy_other"
    elif state == "no_reply":
        result["code"] = "no_reply"
    elif not local:
        result["code"] = "remote_unreachable"
    elif result["other_ports"]:
        result["code"] = "openrgb_other_port"
    elif result["openrgb_processes"]:
        result["code"] = "openrgb_no_sdk"
    else:
        result["code"] = "not_running"
    return result


def summary_line(d: Dict) -> str:
    """One ASCII line for the console and the activity log (English)."""
    where = f"{d['host']}:{d['port']}"
    owner = d.get("owner") or {}
    who = ""
    if owner:
        kind = f"service '{owner['service']}'" if owner.get("service") else "process"
        who = f" [{owner.get('name') or '?'} PID {owner['pid']}, {kind}]"
    code = d["code"]
    if code == "connected":
        n = d.get("device_count")
        text = f"OpenRGB SDK server answers at {where}{who}" + (f", {n} device(s)" if n is not None else "")
    elif code == "openrgb_no_sdk":
        text = f"OpenRGB is running but its SDK server is off (nothing on {where})"
    elif code == "openrgb_other_port":
        ports = ", ".join(str(p) for p in d["other_ports"])
        text = f"OpenRGB listens on port {ports}, not on {where}: check the port in Configuration"
    elif code == "not_running":
        text = f"OpenRGB is not running (nothing on {where})"
    elif code == "port_busy_other":
        text = f"Port {d['port']} is used by another program, not OpenRGB{who}"
    elif code == "no_reply":
        text = f"Something listens on {where} but does not answer{who}"
    else:
        text = f"OpenRGB host {where} is not reachable"
    if "multiple_instances" in d.get("warnings", []):
        pids = ", ".join(str(p["pid"]) for p in d["openrgb_processes"])
        text += f" | WARNING: {len(d['openrgb_processes'])} OpenRGB processes running (PID {pids})"
    return text
