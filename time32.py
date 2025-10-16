# activity_lib.py
# Windows-only helpers for activity snapshots + visible window listing.
# psutil is required (for CPU and network metrics).

import ctypes
import time
import shutil
import psutil
from typing import List, Tuple
from ctypes import wintypes

# --- WinAPI setup ---
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Activity-related API calls
GetLastInputInfo = user32.GetLastInputInfo
GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextW = user32.GetWindowTextW
GetTickCount = ctypes.windll.kernel32.GetTickCount

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD)
    ]

# Window enumeration-related API calls
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
QueryFullProcessImageNameW = getattr(kernel32, "QueryFullProcessImageNameW", None)
OpenProcess = kernel32.OpenProcess
CloseHandle = kernel32.CloseHandle

# ---------------- Activity (idle, foreground, cpu/net) ----------------

def get_idle_seconds() -> float:
    """Seconds since last keyboard/mouse input."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not GetLastInputInfo(ctypes.byref(lii)):
        return -1.0
    tick_now = GetTickCount()
    elapsed_ms = (tick_now - lii.dwTime) & 0xFFFFFFFF
    return elapsed_ms / 1000.0

def get_foreground_title() -> str:
    """Title of the current foreground window."""
    hwnd = GetForegroundWindow()
    if not hwnd:
        return ""
    length = GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def get_cpu_percent(sample_seconds: float = 1.0) -> float:
    """CPU % over a short interval."""
    psutil.cpu_percent(None)  # establish baseline
    time.sleep(sample_seconds)
    return psutil.cpu_percent(None)

def get_net_rates(sample_seconds: float = 1.0) -> Tuple[float, float]:
    """Return (bytes_sent_per_sec, bytes_recv_per_sec)."""
    c0 = psutil.net_io_counters()
    time.sleep(sample_seconds)
    c1 = psutil.net_io_counters()
    up = (c1.bytes_sent - c0.bytes_sent) / sample_seconds
    down = (c1.bytes_recv - c0.bytes_recv) / sample_seconds
    return up, down

def human_rate(bps: float) -> str:
    """Human-friendly KB/s or MB/s string."""
    kb = bps / 1024.0
    if kb < 1024:
        return f"{kb:,.1f} KB/s"
    return f"{kb/1024.0:,.2f} MB/s"

def truncate(s: str, max_len: int) -> str:
    return s if len(s) <= max_len else s[: max_len - 1] + "…"

def print_table(rows: List[Tuple[str, str]]) -> None:
    """Simple two-column table that fits the terminal width."""
    term_width = shutil.get_terminal_size((80, 20)).columns
    key_w = max(len(k) for k, _ in rows) + 2
    for k, v in rows:
        val = str(v)
        available = max(10, term_width - key_w)
        print(f"{k:<{key_w}}{truncate(val, available)}")

def build_activity_snapshot(cpu_seconds: float = 0.8, net_seconds: float = 0.2) -> dict:
    """Build a one-shot activity snapshot dict."""
    cpu = get_cpu_percent(sample_seconds=cpu_seconds)
    up_bps, down_bps = get_net_rates(sample_seconds=net_seconds)
    idle = get_idle_seconds()
    title = get_foreground_title() or "(no title / none)"
    return {
        "idle_seconds": idle,
        "foreground_title": title,
        "cpu_percent": cpu,
        "net_up_bps": up_bps,
        "net_down_bps": down_bps,
        "timestamp": time.time(),
    }

def print_activity_snapshot(snapshot: dict | None = None) -> None:
    """Pretty-print a snapshot (builds one if not provided)."""
    if snapshot is None:
        snapshot = build_activity_snapshot()
    rows = [
        ("Idle (kbd/mouse)", f"{snapshot['idle_seconds']:.1f} s since last input"),
        ("Foreground window", snapshot["foreground_title"]),
        ("CPU usage", f"{snapshot['cpu_percent']:.1f} %"),
        ("Network ↑/↓", f"{human_rate(snapshot['net_up_bps'])} / {human_rate(snapshot['net_down_bps'])}"),
    ]
    print_table(rows)

# ---------------- Window enumeration ----------------

def get_window_title(hwnd: int) -> str:
    length = GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def get_window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def get_process_name(pid: int) -> str:
    """Process name using WinAPI."""
    if not QueryFullProcessImageNameW:
        return ""
    hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hProcess:
        return ""
    try:
        size = wintypes.DWORD(260)
        buf = ctypes.create_unicode_buffer(size.value)
        if QueryFullProcessImageNameW(hProcess, 0, buf, ctypes.byref(size)):
            path = buf.value
            return path.split("\\")[-1]
        return ""
    finally:
        CloseHandle(hProcess)

def list_visible_windows() -> List[Tuple[int, str, int, str]]:
    """Return a list of (hwnd, title, pid, process_name) for visible top-level windows."""
    windows: List[Tuple[int, str, int, str]] = []

    def callback(hwnd, lparam):
        if IsWindowVisible(hwnd):
            title = get_window_title(hwnd)
            if title.strip():
                pid = get_window_pid(hwnd)
                pname = get_process_name(pid)
                windows.append((hwnd, title, pid, pname))
        return True

    EnumWindows(EnumWindowsProc(callback), 0)
    return windows

def print_window_list() -> None:
    """Print visible top-level windows, marking the foreground one with '*'."""
    fg = GetForegroundWindow()
    windows = list_visible_windows()
    windows.sort(key=lambda x: x[1].lower())
    print("Open windows (visible, top-level). The focused one is marked with '*':\n")
    for hwnd, title, pid, pname in windows:
        star = "*" if hwnd == fg else " "
        exe = f" ({pname})" if pname else ""
        print(f"[{star}] hwnd=0x{hwnd:08X}  pid={pid}{exe}  title=\"{title}\"")

__all__ = [
    "get_idle_seconds", "get_foreground_title", "get_cpu_percent", "get_net_rates",
    "human_rate", "truncate", "print_table", "build_activity_snapshot", "print_activity_snapshot",
    "get_window_title", "get_window_pid", "get_process_name", "list_visible_windows", "print_window_list",
]
