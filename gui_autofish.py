"""
=============================================================================
Steal an Egg - Auto-Fishing GUI Dashboard (Roblox)
=============================================================================
Supports:
1. LDPlayer (ADB Mode) - 100% Background Automation:
   - Uses Android's high-speed Monkey Engine for 100% reliable hardware touch.
   - Long-press hold for casts (1.05s) with millisecond precision.
   - Turbo-speed reeling taps (16 taps in ~0.45s).
   - ZERO physical Windows mouse movement or jumping!
   - ZERO focus stealing! Browse YouTube, type, or play games freely.
2. Interactive Aim Tuner:
   - Live visual aim coordinates + Arrow buttons ([▲] [▼] [◀] [▶]) + [🎣 Test Cast].
3. Direct Windows Mode - Focus-swap automation fallback for native PC client.
4. Floating Draggable Target Pins for instant calibration on any monitor.
=============================================================================
"""

import os
import sys
import time
import json
import queue
import random
import shutil
import struct
import subprocess
import ctypes
from ctypes import wintypes
import winsound
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext

# Enable Per-Monitor DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

# Virtual key code mapping
VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B
}

MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_ABSOLUTE    = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
KEYEVENTF_KEYUP         = 0x0002
VK_SPACE                = 0x20
GA_ROOT                 = 2

SM_XVIRTUALSCREEN       = 76
SM_YVIRTUALSCREEN       = 77
SM_CXVIRTUALSCREEN      = 78
SM_CYVIRTUALSCREEN      = 79

ULONG_PTR = ctypes.c_ulonglong

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("_u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_u", _INPUT_UNION)
    ]

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32)
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

# Configure Win32 Monitor API prototypes for 64-bit safety
ctypes.windll.user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
ctypes.windll.user32.MonitorFromWindow.restype = wintypes.HMONITOR

ctypes.windll.user32.MonitorFromPoint.argtypes = [POINT, wintypes.DWORD]
ctypes.windll.user32.MonitorFromPoint.restype = wintypes.HMONITOR

ctypes.windll.user32.MonitorFromRect.argtypes = [ctypes.POINTER(RECT), wintypes.DWORD]
ctypes.windll.user32.MonitorFromRect.restype = wintypes.HMONITOR

ctypes.windll.user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEX)]
ctypes.windll.user32.GetMonitorInfoW.restype = wintypes.BOOL

DEFAULT_CONFIG = {
    "use_adb": False,
    "adb_path": r"E:\LDPlayer\LDPlayer9\adb.exe",
    "adb_cast_x": 640,
    "adb_cast_y": 420,
    "adb_reel_x": 640,
    "adb_reel_y": 420,
    "screen_selection": "🔍 Auto-Detect Screen (Roblox)",
    "cast_aim_x": -473,
    "cast_aim_y": 374,
    "calibrated_bar_x": -567,
    "calibrated_bar_y": 1174,
    "calibrated_color": [159, 204, 116],
    "cast_hold_duration": 1.05,
    "min_wait_before_bite": 1.8,
    "reeling_clicks": 16,
    "click_interval": 0.020,
    "post_catch_cooldown": 4.0,
    "max_bite_wait_seconds": 24.0,
    "color_tolerance": 55,
    "jitter_amount": 0.015,
    "anti_afk_enabled": True,
    "anti_afk_interval_seconds": 120,
    "auto_reequip_enabled": True,
    "rod_slot_number": 3,
    "rod_search_term": "rod",
    "gear_tab_x": -760,
    "gear_tab_y": 480,
    "bag_search_x": -360,
    "bag_search_y": 280,
    "bag_rod_x": -570,
    "bag_rod_y": 380,
    "rod_slot_x": -588,
    "rod_slot_y": 1215,
    "rod_slot_active_color": [255, 255, 255],
    "rod_slot_active_colors": [],
    "hotkeys": {
        "toggle": "F6",
        "decrease_cast": "F1",
        "increase_cast": "F2",
        "calibrate_bar": "F3",
        "test_single": "F7",
        "decrease_cooldown": "F9",
        "increase_cooldown": "F10",
        "exit": "F8"
    }
}


def get_ldplayer_rect():
    """Finds the LDPlayer window rect on the desktop if visible."""
    hwnd = None
    try:
        def enum_cb(h, _):
            nonlocal hwnd
            if ctypes.windll.user32.IsWindowVisible(h):
                buf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(h, buf, 256)
                cbuf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(h, cbuf, 256)
                t = buf.value.lower()
                c = cbuf.value.lower()
                if "ldplayer" in t or "ldplayer" in c or "render" in c:
                    rect = wintypes.RECT()
                    ctypes.windll.user32.GetWindowRect(h, ctypes.byref(rect))
                    w = rect.right - rect.left
                    h_win = rect.bottom - rect.top
                    if w > 300 and h_win > 200:
                        hwnd = h
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        if hwnd:
            r = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
            return r.left, r.top, r.right, r.bottom
    except Exception:
        pass
    return None


# =============================================================================
# ADB Manager for LDPlayer (High-Speed Monkey Engine)
# =============================================================================
class ADBManager:
    """Controls LDPlayer via Android's high-speed Monkey Engine.
    - ZERO physical Windows mouse movement or focus stealing.
    - 100% exact duration long-press hold for casts (1.05s).
    - Turbo-speed reeling taps (16 taps in ~0.45s).
    """
    def __init__(self, adb_path=None):
        self.adb_path = adb_path or self.find_adb()
        self.process = None
        self.connected = False
        self.device_name = "emulator-5554"
        self.lock = threading.Lock()
        self._last_cast_cfg = None
        self._last_reel_cfg = None
        self.start_session()

    @staticmethod
    def find_adb():
        candidates = [
            r"E:\LDPlayer\LDPlayer9\adb.exe",
            r"C:\LDPlayer\LDPlayer9\adb.exe",
            r"D:\LDPlayer\LDPlayer9\adb.exe",
            r"E:\LDPlayer\LDPlayer\adb.exe",
            r"C:\LDPlayer\LDPlayer\adb.exe",
            r"C:\Program Files\LDPlayer\LDPlayer9\adb.exe",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        which = shutil.which("adb")
        if which:
            return which
        return r"E:\LDPlayer\LDPlayer9\adb.exe"

    def check_device(self):
        """Checks if emulator is detected by adb devices."""
        if not self.adb_path or not os.path.exists(self.adb_path):
            self.connected = False
            return False
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, startupinfo=startupinfo, timeout=3)
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device" and ("emulator" in line or "127.0.0.1" in line):
                    self.device_name = parts[0]
                    self.connected = True
                    return True
            # Attempt connect if list is empty
            conn_res = subprocess.run([self.adb_path, "connect", "127.0.0.1:5555"], capture_output=True, text=True, startupinfo=startupinfo, timeout=2)
            if "connected to" in conn_res.stdout.lower():
                res2 = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, startupinfo=startupinfo, timeout=2)
                for line in res2.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "device":
                        self.device_name = parts[0]
                        self.connected = True
                        return True
            self.connected = False
            return False
        except Exception:
            self.connected = False
            return False

    def start_session(self):
        with self.lock:
            self.close()
            if not os.path.exists(self.adb_path):
                self.connected = False
                return False
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            try:
                self.process = subprocess.Popen(
                    [self.adb_path, "shell"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    startupinfo=startupinfo,
                    bufsize=1
                )
                self.connected = True
                return True
            except Exception:
                self.connected = False
                return False

    def send_cmd(self, cmd_str):
        with self.lock:
            if not self.process or self.process.poll() is not None:
                if not self.start_session():
                    return False
            try:
                self.process.stdin.write(cmd_str + "\n")
                self.process.stdin.flush()
                return True
            except Exception:
                self.connected = False
                return False

    def setup_cast_script(self, x, y, duration_sec):
        hold_ms = int(duration_sec * 1000)
        script = f"""type= raw events
count= 1
speed= 1.0
start data >>
DispatchPointer(1000, 1000, 0, {float(x)}, {float(y)}, 1.0, 1.0, 0, 1.0, 1.0, 0, 0)
UserWait({hold_ms})
DispatchPointer(1000, {1000 + hold_ms}, 1, {float(x)}, {float(y)}, 1.0, 1.0, 0, 1.0, 1.0, 0, 0)
"""
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            p = subprocess.Popen([self.adb_path, "shell", "cat > /data/local/tmp/cast.txt"], stdin=subprocess.PIPE, startupinfo=startupinfo)
            p.communicate(input=script.encode(), timeout=3)
            self._last_cast_cfg = (x, y, hold_ms)
            return True
        except Exception:
            return False

    def setup_reel_script(self, x, y, count=16, wait_ms=25):
        lines = [
            "type= raw events",
            f"count= {count}",
            "speed= 1.0",
            "start data >>"
        ]
        for i in range(count):
            t_down = 1000 + i * (wait_ms + 15)
            t_up = t_down + 15
            lines.append(f"DispatchPointer({t_down}, {t_down}, 0, {float(x)}, {float(y)}, 1.0, 1.0, 0, 1.0, 1.0, 0, 0)")
            lines.append(f"DispatchPointer({t_down}, {t_up}, 1, {float(x)}, {float(y)}, 1.0, 1.0, 0, 1.0, 1.0, 0, 0)")
            lines.append(f"UserWait({int(wait_ms)})")
        script = "\n".join(lines) + "\n"

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            p = subprocess.Popen([self.adb_path, "shell", "cat > /data/local/tmp/reel.txt"], stdin=subprocess.PIPE, startupinfo=startupinfo)
            p.communicate(input=script.encode(), timeout=3)
            self._last_reel_cfg = (x, y, count, wait_ms)
            return True
        except Exception:
            return False

    def cast_hold(self, x, y, duration=1.05):
        """Executes a 100% reliable long-press hold for casting via Monkey."""
        hold_ms = int(duration * 1000)
        if self._last_cast_cfg != (x, y, hold_ms):
            self.setup_cast_script(x, y, duration)

        self.send_cmd("monkey -f /data/local/tmp/cast.txt 1 > /dev/null")
        time.sleep(duration + 0.15)

    def rapid_tap(self, x, y, count=16, interval=0.020):
        """Executes high-speed reeling taps via Monkey (~0.45s)."""
        wait_ms = max(15, int(interval * 1000))
        if self._last_reel_cfg != (x, y, count, wait_ms):
            self.setup_reel_script(x, y, count, wait_ms)

        self.send_cmd("monkey -f /data/local/tmp/reel.txt 1 > /dev/null")
        total_wait = max(0.45, (count * (wait_ms + 15)) / 1000.0)
        time.sleep(total_wait)

    def anti_afk_jump(self):
        self.send_cmd("input keyevent 62")

    def drag(self, x1, y1, x2, y2, duration_ms=250):
        self.send_cmd(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {duration_ms}")

    def tap(self, x, y):
        self.send_cmd(f"input tap {int(x)} {int(y)}")

    def send_text(self, text):
        self.send_cmd(f"input text {text}")

    def clear_text(self, count=10):
        keys = " ".join(["67"] * count)
        self.send_cmd(f"input keyevent {keys}")

    def press_key(self, keycode):
        self.send_cmd(f"input keyevent {keycode}")

    def close(self):
        if self.process:
            try:
                if self.process.stdin:
                    try:
                        self.process.stdin.write("exit\n")
                        self.process.stdin.flush()
                    except Exception:
                        pass
                    try:
                        self.process.stdin.close()
                    except Exception:
                        pass
                if self.process.stdout:
                    try:
                        self.process.stdout.close()
                    except Exception:
                        pass
                if self.process.stderr:
                    try:
                        self.process.stderr.close()
                    except Exception:
                        pass
                self.process.terminate()
            except Exception:
                pass
            self.process = None
        self.connected = False


def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def get_cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_cursor_pos(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))


def focus_window(hwnd):
    if not hwnd or not ctypes.windll.user32.IsWindow(hwnd):
        return False
    try:
        cur_fg = ctypes.windll.user32.GetForegroundWindow()
        if cur_fg == hwnd:
            return True

        if ctypes.windll.user32.IsIconic(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE

        cur_thread = ctypes.windll.user32.GetWindowThreadProcessId(cur_fg, None)
        target_thread = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        my_thread = ctypes.windll.kernel32.GetCurrentThreadId()

        for t in (cur_thread, my_thread):
            if t != target_thread and t != 0:
                ctypes.windll.user32.AttachThreadInput(t, target_thread, True)

        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetForegroundWindow(hwnd)

        for t in (cur_thread, my_thread):
            if t != target_thread and t != 0:
                ctypes.windll.user32.AttachThreadInput(t, target_thread, False)

        return ctypes.windll.user32.GetForegroundWindow() == hwnd
    except Exception:
        return False


def restore_user_state(saved_hwnd, saved_x, saved_y):
    try:
        set_cursor_pos(saved_x, saved_y)
        if saved_hwnd and ctypes.windll.user32.IsWindow(saved_hwnd):
            focus_window(saved_hwnd)
    except Exception:
        pass


def color_diff(c1, c2):
    if not c1 or not c2:
        return 999
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])


def is_green_or_stop(r, g, b):
    if not r and not g and not b:
        return False, None
    # Bright lime green bar: G is high, and clearly dominant over R and B
    if g > 170 and g > r * 1.15 and g > b * 1.3:
        return True, "GREEN_BAR"
    if r > 195 and g < 115 and b < 115:
        return True, "STOP_BUTTON"
    return False, None


class MultiMonitorManager:
    def __init__(self):
        self.dcs = {}
        self.sct = mss.MSS() if HAS_MSS else None

    def get_dc(self, szDevice):
        if szDevice not in self.dcs:
            hdc = ctypes.windll.gdi32.CreateDCW(szDevice, None, None, None)
            self.dcs[szDevice] = hdc
        return self.dcs[szDevice]

    def get_pixel(self, x, y):
        # 1. Direct monitor DC GetPixel
        try:
            pt = POINT(int(x), int(y))
            hmon = ctypes.windll.user32.MonitorFromPoint(pt, 2)
            info = MONITORINFOEX()
            info.cbSize = ctypes.sizeof(MONITORINFOEX)
            if ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
                hdc = self.get_dc(info.szDevice)
                if hdc:
                    local_x = int(x) - info.rcMonitor.left
                    local_y = int(y) - info.rcMonitor.top
                    col = ctypes.windll.gdi32.GetPixel(hdc, local_x, local_y)
                    if col != -1 and col is not None:
                        return (col & 0xFF, (col >> 8) & 0xFF, (col >> 16) & 0xFF)
        except Exception:
            pass

        # 2. Win32 BitBlt via 1x1 memory DC (composited DWM compatible)
        try:
            hdc0 = ctypes.windll.user32.GetDC(0)
            if hdc0:
                hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc0)
                hbm = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc0, 1, 1)
                old_bm = ctypes.windll.gdi32.SelectObject(hdc_mem, hbm)
                ctypes.windll.gdi32.BitBlt(hdc_mem, 0, 0, 1, 1, hdc0, int(x), int(y), 0x00CC0020)
                col = ctypes.windll.gdi32.GetPixel(hdc_mem, 0, 0)
                ctypes.windll.gdi32.SelectObject(hdc_mem, old_bm)
                ctypes.windll.gdi32.DeleteObject(hbm)
                ctypes.windll.gdi32.DeleteDC(hdc_mem)
                ctypes.windll.user32.ReleaseDC(0, hdc0)
                if col != -1 and col is not None:
                    return (col & 0xFF, (col >> 8) & 0xFF, (col >> 16) & 0xFF)
        except Exception:
            pass

        # 3. MSS fallback
        if self.sct:
            try:
                img = self.sct.grab({"top": int(y), "left": int(x), "width": 1, "height": 1})
                return img.pixel(0, 0)[:3]
            except Exception:
                pass

        # 4. Standard DC fallback
        try:
            hdc0 = ctypes.windll.user32.GetDC(0)
            col = ctypes.windll.gdi32.GetPixel(hdc0, int(x), int(y))
            ctypes.windll.user32.ReleaseDC(0, hdc0)
            if col != -1 and col is not None:
                return (col & 0xFF, (col >> 8) & 0xFF, (col >> 16) & 0xFF)
        except Exception:
            pass

        return None

    def close(self):
        for hdc in self.dcs.values():
            try:
                ctypes.windll.gdi32.DeleteDC(hdc)
            except Exception:
                pass
        self.dcs.clear()
        if self.sct:
            try:
                self.sct.close()
            except Exception:
                pass


def human_sleep(duration, jitter=0.015):
    if jitter > 0:
        actual_delay = max(0.01, duration + random.uniform(-jitter, jitter))
    else:
        actual_delay = max(0.01, duration)
    time.sleep(actual_delay)
    return actual_delay


def _send_mouse_event(flags, x, y):
    vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = max(1, ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    vh = max(1, ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    norm_x = int((int(x) - vx) * 65535 / max(1, vw - 1))
    norm_y = int((int(y) - vy) * 65535 / max(1, vh - 1))

    try:
        inp = INPUT()
        inp.type = 0
        inp.mi.dx = norm_x
        inp.mi.dy = norm_y
        inp.mi.dwFlags = flags
        sent = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if sent:
            return
    except Exception:
        pass
    ctypes.windll.user32.mouse_event(flags, norm_x, norm_y, 0, 0)


def send_mouse_down_at(x, y):
    _send_mouse_event(MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, x, y)


def send_mouse_up_at(x, y):
    _send_mouse_event(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, x, y)


def mouse_click_at(x, y, hold_time=0.02):
    send_mouse_down_at(x, y)
    if hold_time > 0:
        time.sleep(hold_time)
    send_mouse_up_at(x, y)


def mouse_down():
    x, y = get_cursor_pos()
    send_mouse_down_at(x, y)


def mouse_up():
    x, y = get_cursor_pos()
    send_mouse_up_at(x, y)


def mouse_click(hold_time=0.02):
    x, y = get_cursor_pos()
    mouse_click_at(x, y, hold_time=hold_time)


def key_tap(vk_code):
    scan = ctypes.windll.user32.MapVirtualKeyW(vk_code, 0)
    ctypes.windll.user32.keybd_event(vk_code, scan, 0, 0)
    time.sleep(0.06)
    ctypes.windll.user32.keybd_event(vk_code, scan, KEYEVENTF_KEYUP, 0)


def mouse_drag_at(x1, y1, x2, y2, duration=0.25, steps=15):
    move_flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK

    # Hover over source item first so Roblox UI registers the drag target
    _send_mouse_event(move_flags, x1, y1)
    time.sleep(0.08)
    send_mouse_down_at(x1, y1)
    time.sleep(0.10)

    for i in range(1, steps + 1):
        frac = i / steps
        cur_x = int(x1 + (x2 - x1) * frac)
        cur_y = int(y1 + (y2 - y1) * frac)
        _send_mouse_event(move_flags, cur_x, cur_y)
        time.sleep(max(0.005, duration / steps))

    # Pause over destination slot before releasing so Roblox registers the drop
    time.sleep(0.10)
    send_mouse_up_at(x2, y2)


def send_text(text):
    for ch in text:
        vk = ctypes.windll.user32.VkKeyScanW(ord(ch))
        if vk != -1:
            code = vk & 0xFF
            scan = ctypes.windll.user32.MapVirtualKeyW(code, 0)
            shift = bool((vk >> 8) & 1)
            shift_scan = ctypes.windll.user32.MapVirtualKeyW(0x10, 0) if shift else 0
            if shift:
                ctypes.windll.user32.keybd_event(0x10, shift_scan, 0, 0)
            ctypes.windll.user32.keybd_event(code, scan, 0, 0)
            time.sleep(0.02)
            ctypes.windll.user32.keybd_event(code, scan, KEYEVENTF_KEYUP, 0)
            if shift:
                ctypes.windll.user32.keybd_event(0x10, shift_scan, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)


def clear_text_box():
    ctrl_scan = ctypes.windll.user32.MapVirtualKeyW(0x11, 0)
    a_scan = ctypes.windll.user32.MapVirtualKeyW(0x41, 0)
    # Ctrl + A
    ctypes.windll.user32.keybd_event(0x11, ctrl_scan, 0, 0)  # VK_CONTROL
    ctypes.windll.user32.keybd_event(0x41, a_scan, 0, 0)     # 'A'
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(0x41, a_scan, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(0x11, ctrl_scan, KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)
    # Backspace + Delete
    key_tap(0x08)
    time.sleep(0.03)
    key_tap(0x2E)
    time.sleep(0.04)


def get_system_monitors():
    monitors = []
    def _cb(hmon, hdc, lprect, lparam):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        w = mi.rcMonitor.right - mi.rcMonitor.left
        h = mi.rcMonitor.bottom - mi.rcMonitor.top
        is_primary = bool(mi.dwFlags & 1)
        orient = "Portrait" if h > w else "Landscape"
        idx = len(monitors) + 1
        dev_clean = mi.szDevice.split("\\")[-1] or f"DISPLAY{idx}"
        primary_tag = ", Primary" if is_primary else ""
        label = f"Monitor {idx}: {w}x{h} ({orient}{primary_tag}) [{dev_clean}]"
        monitors.append({
            "index": idx,
            "handle": hmon,
            "device": mi.szDevice,
            "dev_name": dev_clean,
            "left": mi.rcMonitor.left,
            "top": mi.rcMonitor.top,
            "right": mi.rcMonitor.right,
            "bottom": mi.rcMonitor.bottom,
            "width": w,
            "height": h,
            "is_primary": is_primary,
            "orientation": orient,
            "label": label
        })
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)
    ctypes.windll.user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_cb), 0)
    return monitors


def detect_roblox_screen(roblox_hwnd=None):
    monitors = get_system_monitors()
    if not monitors:
        return None, None, "No active monitors detected."

    if roblox_hwnd:
        if not ctypes.windll.user32.IsWindow(roblox_hwnd):
            try:
                hdesk = ctypes.windll.user32.OpenDesktopW("default", 0, False, 0x01FF)
                if hdesk:
                    ctypes.windll.user32.SetThreadDesktop(hdesk)
            except Exception:
                pass

        if ctypes.windll.user32.IsWindow(roblox_hwnd):
            r = RECT()
            ctypes.windll.user32.GetWindowRect(roblox_hwnd, ctypes.byref(r))
            hmon = ctypes.windll.user32.MonitorFromWindow(roblox_hwnd, 2)
            for m in monitors:
                if m["handle"] == hmon:
                    return m, r, f"Roblox window detected on {m['label']}"
            # Fallback to rect center intersection
            cx = (r.left + r.right) // 2
            cy = (r.top + r.bottom) // 2
            for m in monitors:
                if m["left"] <= cx < m["right"] and m["top"] <= cy < m["bottom"]:
                    return m, r, f"Roblox window detected on {m['label']}"

    for m in monitors:
        if m["is_primary"]:
            return m, None, f"Using Primary {m['label']} (Roblox not detected)"
    return monitors[0], None, f"Using {monitors[0]['label']}"


# =============================================================================
# Floating Draggable Target Pin Widget
# =============================================================================
class DraggablePin(tk.Toplevel):
    def __init__(self, master, label_text, initial_x, initial_y, accent_color, on_moved=None):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.90)
        self.accent_color = accent_color
        self.on_moved = on_moved

        self.configure(bg=accent_color)

        frame = tk.Frame(self, bg='#0d1117', bd=1, relief='solid')
        frame.pack(fill='both', expand=True, padx=2, pady=2)

        self.title_lbl = tk.Label(frame, text=label_text, fg=accent_color, bg='#0d1117', font=('Consolas', 9, 'bold'))
        self.title_lbl.pack(padx=6, pady=(3, 0))

        self.pos_lbl = tk.Label(frame, text=f"({initial_x}, {initial_y})", fg='#c9d1d9', bg='#0d1117', font=('Consolas', 8))
        self.pos_lbl.pack(padx=6, pady=(0, 3))

        self.geometry(f"+{int(initial_x)}+{int(initial_y)}")

        for w in (self, frame, self.title_lbl, self.pos_lbl):
            w.bind("<Button-1>", self.on_start)
            w.bind("<B1-Motion>", self.on_drag)
            w.bind("<ButtonRelease-1>", self.on_release)

    def on_start(self, event):
        self._start_x = event.x_root
        self._start_y = event.y_root
        self._win_x = self.winfo_x()
        self._win_y = self.winfo_y()

    def on_drag(self, event):
        dx = event.x_root - self._start_x
        dy = event.y_root - self._start_y
        new_x = self._win_x + dx
        new_y = self._win_y + dy
        self.geometry(f"+{new_x}+{new_y}")
        self.pos_lbl.config(text=f"({new_x}, {new_y})")

    def on_release(self, event):
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        self.pos_lbl.config(text=f"({cur_x}, {cur_y})")
        if self.on_moved:
            self.on_moved(cur_x, cur_y)

    def update_coords(self, x, y):
        self.geometry(f"+{int(x)}+{int(y)}")
        self.pos_lbl.config(text=f"({int(x)}, {int(y)})")


# =============================================================================
# Main GUI Dashboard Application
# =============================================================================
class AutoFishGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Steal an Egg - Auto-Fishing Command Console")
        self.root.geometry("860x700")
        self.root.configure(bg="#0c0d10")
        self.root.minsize(780, 600)

        self.config = load_config()
        self.display = MultiMonitorManager()
        self.adb = ADBManager(self.config.get("adb_path"))
        self.log_queue = queue.Queue()
        self.roblox_hwnd = None
        self.monitors_cache = []
        self.active_monitor = None

        self.is_running = False
        self.test_mode = False
        self.should_exit = False
        self.total_catches = 0
        self.total_casts = 0
        self.start_time = None
        self.last_anti_afk = time.time()
        self.lock = threading.Lock()

        # Pin overlays
        self.pins_visible = False
        self.aim_pin = None
        self.bar_pin = None
        self.instructions_win = None

        self.reequip_pins_visible = False
        self.gear_pin = None
        self.search_pin = None
        self.bag_rod_pin = None
        self.slot_pin = None

        # Build UI layout
        self._build_ui()

        # Hotkeys listener thread
        self.hotkey_thread = threading.Thread(target=self._hotkey_listener, daemon=True)
        self.hotkey_thread.start()

        # Fishing loop worker thread
        self.worker_thread = threading.Thread(target=self._fishing_worker, daemon=True)
        self.worker_thread.start()

        # Start periodic GUI queue processor & timer
        self.root.after(100, self._process_log_queue)
        self.root.after(1000, self._update_uptime_timer)
        self.root.after(1500, self._check_adb_status)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        # 1. Top Header Banner
        header = tk.Frame(self.root, bg="#161b22", bd=0, relief="flat", highlightbackground="#30363d", highlightthickness=1)
        header.pack(fill="x", padx=14, pady=(12, 6))

        title_lbl = tk.Label(header, text="🎣 STEAL AN EGG — AUTO-FISHING COMMAND CONSOLE", fg="#58a6ff", bg="#161b22", font=("Consolas", 12, "bold"))
        title_lbl.pack(side="left", padx=12, pady=10)

        self.mode_badge = tk.Label(header, text="[ 🖥️ MODE: DIRECT WINDOWS ]", fg="#58a6ff", bg="#21262d", font=("Consolas", 9, "bold"), padx=8, pady=4)
        self.mode_badge.pack(side="right", padx=(4, 12), pady=8)
        self.adb_badge = self.mode_badge

        self.status_badge = tk.Label(header, text="[ PAUSED ]", fg="#f85149", bg="#21262d", font=("Consolas", 10, "bold"), padx=10, pady=4)
        self.status_badge.pack(side="right", padx=4, pady=8)

        # 2. Stats & Status Row
        stats_frame = tk.Frame(self.root, bg="#0c0d10")
        stats_frame.pack(fill="x", padx=14, pady=4)

        self.catches_card = self._create_card(stats_frame, "TOTAL CATCHES", "0", "#39d353")
        self.catches_card.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.uptime_card = self._create_card(stats_frame, "SESSION UPTIME", "00:00:00", "#58a6ff")
        self.uptime_card.pack(side="left", fill="both", expand=True, padx=4)

        self.action_card = self._create_card(stats_frame, "CURRENT ACTION", "Idle — Ready to Start", "#e3b341")
        self.action_card.pack(side="left", fill="both", expand=True, padx=(4, 0))

        # 2b. Client Mode Selector Bar
        mode_bar = tk.Frame(self.root, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
        mode_bar.pack(fill="x", padx=14, pady=(2, 4))

        tk.Label(mode_bar, text="CLIENT MODE:", fg="#8b949e", bg="#161b22", font=("Consolas", 8, "bold")).pack(side="left", padx=10, pady=6)

        self.btn_mode_win = tk.Button(
            mode_bar, text="🖥️ Plain Windows Mode (Roblox PC Client)",
            font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=12, pady=4,
            command=lambda: self.switch_mode(False)
        )
        self.btn_mode_win.pack(side="left", padx=4, pady=4)

        self.btn_mode_adb = tk.Button(
            mode_bar, text="⚡ LDPlayer ADB Mode (Touch Injection)",
            font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=12, pady=4,
            command=lambda: self.switch_mode(True)
        )
        self.btn_mode_adb.pack(side="left", padx=4, pady=4)

        # 2c. Display & Screen Resolution Bar
        screen_bar = tk.Frame(self.root, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
        screen_bar.pack(fill="x", padx=14, pady=(2, 4))

        tk.Label(screen_bar, text="SCREEN / MONITOR:", fg="#8b949e", bg="#161b22", font=("Consolas", 8, "bold")).pack(side="left", padx=10, pady=6)

        self.screen_mode_var = tk.StringVar(value=self.config.get("screen_selection", "🔍 Auto-Detect Screen (Roblox)"))
        self.screen_combo = ttk.Combobox(screen_bar, textvariable=self.screen_mode_var, state="readonly", width=38, font=("Consolas", 8))
        self.screen_combo.pack(side="left", padx=4, pady=4)
        self.screen_combo.bind("<<ComboboxSelected>>", self._on_screen_selected)

        self.btn_detect_screen = tk.Button(
            screen_bar, text="🔍 Detect Roblox Screen",
            bg="#21262d", fg="#58a6ff", activebackground="#30363d", activeforeground="#58a6ff",
            font=("Consolas", 8, "bold"), bd=1, relief="solid", padx=8, pady=2,
            command=self.auto_detect_screen
        )
        self.btn_detect_screen.pack(side="left", padx=4, pady=4)

        self.btn_center_pins = tk.Button(
            screen_bar, text="📍 Center Pins to Screen",
            bg="#21262d", fg="#39d353", activebackground="#30363d", activeforeground="#39d353",
            font=("Consolas", 8), bd=1, relief="solid", padx=6, pady=2,
            command=self.center_pins_for_current_screen
        )
        self.btn_center_pins.pack(side="left", padx=4, pady=4)

        self.screen_badge = tk.Label(screen_bar, text="[ SCREEN: DETECTING... ]", fg="#39d353", bg="#21262d", font=("Consolas", 8, "bold"), padx=6, pady=3)
        self.screen_badge.pack(side="right", padx=(4, 10), pady=4)

        # 3. Targets & Tuners Panel
        controls_panel = tk.Frame(self.root, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
        controls_panel.pack(fill="x", padx=14, pady=4)

        # Row 1: Water Aim Controls (Screen / ADB Coordinates + Arrow Nudges)
        row1 = tk.Frame(controls_panel, bg="#161b22")
        row1.pack(fill="x", padx=12, pady=(8, 4))

        self.aim_coord_lbl = tk.Label(row1, text="Water Aim: (960, 540)", fg="#58a6ff", bg="#161b22", font=("Consolas", 9, "bold"))
        self.aim_coord_lbl.pack(side="left", padx=(0, 8))

        aim_btn_box = tk.Frame(row1, bg="#161b22")
        aim_btn_box.pack(side="left", padx=(0, 16))
        tk.Button(aim_btn_box, text="▲ Up", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(0, -30)).pack(side="left", padx=1)
        tk.Button(aim_btn_box, text="▼ Down", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(0, +30)).pack(side="left", padx=1)
        tk.Button(aim_btn_box, text="◀ Left", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(-30, 0)).pack(side="left", padx=1)
        tk.Button(aim_btn_box, text="▶ Right", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(+30, 0)).pack(side="left", padx=1)

        self.pin_toggle_btn = tk.Button(row1, text="📍 Show Target Pins", bg="#21262d", fg="#58a6ff", activebackground="#30363d", activeforeground="#58a6ff", font=("Consolas", 8, "bold"), bd=1, relief="solid", width=22, command=self.toggle_pins)
        self.pin_toggle_btn.pack(side="right")

        # Row 2: Green Bar Controls (Coordinates + Arrow Nudges)
        row2 = tk.Frame(controls_panel, bg="#161b22")
        row2.pack(fill="x", padx=12, pady=4)

        self.bar_coord_lbl = tk.Label(row2, text=f"Green Bar: ({self.config.get('calibrated_bar_x')}, {self.config.get('calibrated_bar_y')})", fg="#39d353", bg="#161b22", font=("Consolas", 9, "bold"))
        self.bar_coord_lbl.pack(side="left", padx=(0, 8))

        bar_btn_box = tk.Frame(row2, bg="#161b22")
        bar_btn_box.pack(side="left", padx=(0, 16))
        tk.Button(bar_btn_box, text="▲ Up", bg="#21262d", fg="#39d353", font=("Consolas", 8), command=lambda: self.adjust_bar_spot(0, -25)).pack(side="left", padx=1)
        tk.Button(bar_btn_box, text="▼ Down", bg="#21262d", fg="#39d353", font=("Consolas", 8), command=lambda: self.adjust_bar_spot(0, +25)).pack(side="left", padx=1)
        tk.Button(bar_btn_box, text="◀ Left", bg="#21262d", fg="#39d353", font=("Consolas", 8), command=lambda: self.adjust_bar_spot(-25, 0)).pack(side="left", padx=1)
        tk.Button(bar_btn_box, text="▶ Right", bg="#21262d", fg="#39d353", font=("Consolas", 8), command=lambda: self.adjust_bar_spot(+25, 0)).pack(side="left", padx=1)

        self.btn_auto_align = tk.Button(row2, text="📐 Auto-Align Bar", bg="#21262d", fg="#39d353", activebackground="#30363d", activeforeground="#39d353", font=("Consolas", 8, "bold"), bd=1, relief="solid", width=22, command=self.auto_align_bar)
        self.btn_auto_align.pack(side="right")

        # Row 3: Tuners (Cast Hold & Cooldown)
        row3 = tk.Frame(controls_panel, bg="#161b22")
        row3.pack(fill="x", padx=12, pady=(4, 4))

        # Cast hold tuner
        cast_box = tk.Frame(row3, bg="#161b22")
        cast_box.pack(side="left", padx=(0, 20))
        tk.Label(cast_box, text="Cast Hold (F1/F2):", fg="#c9d1d9", bg="#161b22", font=("Consolas", 9)).pack(side="left", padx=(0, 6))
        tk.Button(cast_box, text="-", bg="#21262d", fg="#fff", width=2, command=lambda: self.adjust_cast_time(-0.05)).pack(side="left")
        self.cast_val_lbl = tk.Label(cast_box, text=f"{self.config.get('cast_hold_duration', 1.05):.2f}s", fg="#e3b341", bg="#161b22", font=("Consolas", 9, "bold"), width=7)
        self.cast_val_lbl.pack(side="left")
        tk.Button(cast_box, text="+", bg="#21262d", fg="#fff", width=2, command=lambda: self.adjust_cast_time(+0.05)).pack(side="left")

        # Cooldown tuner
        cd_box = tk.Frame(row3, bg="#161b22")
        cd_box.pack(side="left", padx=(0, 20))
        tk.Label(cd_box, text="Popup Wait (F9/F10):", fg="#c9d1d9", bg="#161b22", font=("Consolas", 9)).pack(side="left", padx=(0, 6))
        tk.Button(cd_box, text="-", bg="#21262d", fg="#fff", width=2, command=lambda: self.adjust_cooldown(-0.5)).pack(side="left")
        self.cd_val_lbl = tk.Label(cd_box, text=f"{self.config.get('post_catch_cooldown', 4.0):.1f}s", fg="#39d353", bg="#161b22", font=("Consolas", 9, "bold"), width=6)
        self.cd_val_lbl.pack(side="left")
        tk.Button(cd_box, text="+", bg="#21262d", fg="#fff", width=2, command=lambda: self.adjust_cooldown(+0.5)).pack(side="left")

        # Row 4: Auto Re-Equip Rod (Slot 3)
        row4 = tk.Frame(controls_panel, bg="#161b22")
        row4.pack(fill="x", padx=12, pady=(4, 8))

        self.auto_reequip_var = tk.BooleanVar(value=self.config.get("auto_reequip_enabled", True))
        reequip_check = tk.Checkbutton(
            row4, text="🔄 Auto Re-Equip Rod (Slot 3)",
            variable=self.auto_reequip_var, command=self._on_auto_reequip_toggle,
            bg="#161b22", fg="#bc8cff", selectcolor="#0d1117",
            activebackground="#161b22", activeforeground="#bc8cff",
            font=("Consolas", 9, "bold")
        )
        reequip_check.pack(side="left", padx=(0, 8))

        self.btn_test_reequip = tk.Button(
            row4, text="🧪 Test Re-Equip", bg="#21262d", fg="#e3b341",
            activebackground="#30363d", activeforeground="#ffffff",
            font=("Consolas", 8, "bold"), bd=1, relief="solid", padx=8, pady=2,
            command=self.test_reequip_flow
        )
        self.btn_test_reequip.pack(side="left", padx=4)

        self.btn_reequip_pins = tk.Button(
            row4, text="🎒 Re-Equip Pins", bg="#21262d", fg="#bc8cff",
            activebackground="#30363d", activeforeground="#ffffff",
            font=("Consolas", 8, "bold"), bd=1, relief="solid", width=22,
            command=self.toggle_reequip_pins
        )
        self.btn_reequip_pins.pack(side="right")

        # 4. Action Buttons Bar
        btn_bar = tk.Frame(self.root, bg="#0c0d10")
        btn_bar.pack(fill="x", padx=14, pady=4)

        self.start_btn = tk.Button(btn_bar, text="▶ START (F6)", bg="#238636", fg="#ffffff", activebackground="#2ea043", activeforeground="#ffffff", font=("Consolas", 10, "bold"), bd=0, padx=14, pady=6, command=self.toggle_running)
        self.start_btn.pack(side="left", padx=(0, 6))

        self.test_btn = tk.Button(btn_bar, text="🎯 TEST 1 CYCLE (F7)", bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=10, pady=6, command=self.run_test)
        self.test_btn.pack(side="left", padx=4)

        self.guide_btn = tk.Button(btn_bar, text="📖 HOW TO USE", bg="#21262d", fg="#58a6ff", activebackground="#30363d", activeforeground="#ffffff", font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=10, pady=6, command=self.show_instructions)
        self.guide_btn.pack(side="left", padx=4)

        clear_btn = tk.Button(btn_bar, text="CLEAR LOGS", bg="#0c0d10", fg="#8b949e", activebackground="#161b22", activeforeground="#c9d1d9", font=("Consolas", 8), bd=0, command=self.clear_logs)
        clear_btn.pack(side="right", padx=(4, 0))

        # 5. Live Console Terminal
        term_frame = tk.Frame(self.root, bg="#0d1117", highlightbackground="#30363d", highlightthickness=1)
        term_frame.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        self.log_text = scrolledtext.ScrolledText(term_frame, bg="#0d1117", fg="#c9d1d9", insertbackground="#58a6ff", font=("Consolas", 9), bd=0, relief="flat", wrap="none")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

        # Configure color tags for terminal logs
        self.log_text.tag_config("TIME", foreground="#8b949e")
        self.log_text.tag_config("INFO", foreground="#58a6ff")
        self.log_text.tag_config("SUCCESS", foreground="#39d353")
        self.log_text.tag_config("WARN", foreground="#e3b341")
        self.log_text.tag_config("ERROR", foreground="#f85149")
        self.log_text.tag_config("MAGENTA", foreground="#d2a8ff")

        self.log("[SYSTEM] Auto-Fisher GUI initialized. Ready to fish.")
        self._update_mode_ui()
        self._update_aim_label()
        self._populate_screen_options()
        self.root.after(200, lambda: self.auto_detect_screen(quiet=False))
        if self.config.get("use_adb", False):
            self.log("[MODE] ⚡ LDPlayer ADB Mode ACTIVE (Monkey Engine Touch Injection)", "SUCCESS")
        else:
            self.log("[MODE] 🖥️ Plain Windows Mode ACTIVE (Roblox PC Client - Mouse Events)", "INFO")
        self.log(f"[SETUP] Screen Aim: ({self.config.get('cast_aim_x', 960)}, {self.config.get('cast_aim_y', 540)}) | Bar Target: ({self.config.get('calibrated_bar_x', 960)}, {self.config.get('calibrated_bar_y', 720)})")

    def _create_card(self, parent, title, val, color):
        frame = tk.Frame(parent, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
        tk.Label(frame, text=title, fg="#8b949e", bg="#161b22", font=("Consolas", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        lbl = tk.Label(frame, text=val, fg=color, bg="#161b22", font=("Consolas", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(0, 6))
        frame.val_lbl = lbl
        return frame

    def log(self, text, tag="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((ts, text, tag))

    def _process_log_queue(self):
        while not self.log_queue.empty():
            ts, text, tag = self.log_queue.get()
            self.log_text.insert("end", f"[{ts}] ", "TIME")
            self.log_text.insert("end", f"{text}\n", tag)
            self.log_text.see("end")
        self.root.after(100, self._process_log_queue)

    def _update_uptime_timer(self):
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            self.uptime_card.val_lbl.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")
        self.root.after(1000, self._update_uptime_timer)

    def _check_adb_status(self):
        def check():
            if not self.config.get("use_adb", False):
                return
            connected = self.adb.check_device()
            if self.config.get("use_adb", False):
                if connected:
                    self.mode_badge.config(text=f"[ ⚡ ADB: {self.adb.device_name} ]", fg="#39d353")
                else:
                    self.mode_badge.config(text="[ ⚡ ADB: DISCONNECTED ]", fg="#f85149")
        threading.Thread(target=check, daemon=True).start()
        self.root.after(8000, self._check_adb_status)

    def clear_logs(self):
        self.log_text.delete("1.0", "end")

    # =========================================================================
    # Mode Switcher & Coordinate Labels
    # =========================================================================
    def switch_mode(self, use_adb):
        self.config["use_adb"] = bool(use_adb)
        save_config(self.config)
        self._update_mode_ui()
        self._update_aim_label()
        if self.pins_visible and self.aim_pin:
            x = self.config.get("cast_aim_x", 960)
            y = self.config.get("cast_aim_y", 540)
            self.aim_pin.update_coords(x, y)
        if use_adb:
            self.log("[MODE] ⚡ Switched to LDPlayer ADB Mode (Touch Injection).", "SUCCESS")
            def check_now():
                connected = self.adb.check_device()
                if self.config.get("use_adb", False):
                    if connected:
                        self.mode_badge.config(text=f"[ ⚡ ADB: {self.adb.device_name} ]", fg="#39d353")
                    else:
                        self.mode_badge.config(text="[ ⚡ ADB: DISCONNECTED ]", fg="#f85149")
            threading.Thread(target=check_now, daemon=True).start()
        else:
            self.log("[MODE] 🖥️ Switched to Plain Windows Mode (Roblox PC Client - Mouse Events).", "INFO")
            self.mode_badge.config(text="[ 🖥️ MODE: DIRECT WINDOWS ]", fg="#58a6ff")

    def _update_mode_ui(self):
        use_adb = self.config.get("use_adb", False)
        if use_adb:
            self.btn_mode_adb.config(bg="#238636", fg="#ffffff", activebackground="#2ea043", activeforeground="#ffffff")
            self.btn_mode_win.config(bg="#21262d", fg="#8b949e", activebackground="#30363d", activeforeground="#c9d1d9")
            if self.adb.connected:
                self.mode_badge.config(text=f"[ ⚡ ADB: {self.adb.device_name} ]", fg="#39d353")
            else:
                self.mode_badge.config(text="[ ⚡ ADB: CONNECTING ]", fg="#e3b341")
        else:
            self.btn_mode_win.config(bg="#1f6feb", fg="#ffffff", activebackground="#388bfd", activeforeground="#ffffff")
            self.btn_mode_adb.config(bg="#21262d", fg="#8b949e", activebackground="#30363d", activeforeground="#c9d1d9")
            self.mode_badge.config(text="[ 🖥️ MODE: DIRECT WINDOWS ]", fg="#58a6ff")

    def _update_aim_label(self):
        if self.config.get("use_adb", False):
            ax = self.config.get("adb_cast_x", 640)
            ay = self.config.get("adb_cast_y", 420)
            self.aim_coord_lbl.config(text=f"Water Aim (ADB): ({ax}, {ay})")
        else:
            wx = self.config.get("cast_aim_x", 960)
            wy = self.config.get("cast_aim_y", 540)
            self.aim_coord_lbl.config(text=f"Water Aim (Screen): ({wx}, {wy})")

    # =========================================================================
    # Screen & Display Management (Multi-Monitor & Portrait Support)
    # =========================================================================
    def _populate_screen_options(self):
        monitors = get_system_monitors()
        self.monitors_cache = monitors
        options = ["🔍 Auto-Detect Screen (Roblox)"]
        for m in monitors:
            options.append(m["label"])
        options.extend([
            "Preset: 1024x1280 (Portrait Secondary)",
            "Preset: 1080x1920 (Portrait Full HD)",
            "Preset: 1920x1080 (Landscape Full HD)",
            "Preset: 1366x768 (Landscape HD)",
            "Preset: 2560x1440 (2K QHD)"
        ])
        self.screen_combo["values"] = options
        saved = self.config.get("screen_selection")
        if saved and saved in options:
            self.screen_mode_var.set(saved)
        else:
            self.screen_mode_var.set(options[0])

    def auto_detect_screen(self, quiet=False):
        r_hwnd = self.get_roblox_hwnd()
        mon, rect, msg = detect_roblox_screen(r_hwnd)
        if mon:
            self.active_monitor = mon
            dev_name = mon.get("dev_name") or mon["device"].split("\\")[-1]
            badge_text = f"[ 🖥️ {mon['width']}x{mon['height']} {mon['orientation']} • {dev_name} ]"
            self.screen_badge.config(text=badge_text, fg="#39d353")
            self.config["detected_screen_width"] = mon["width"]
            self.config["detected_screen_height"] = mon["height"]
            self.config["detected_screen_orientation"] = mon["orientation"]
            self.config["detected_screen_device"] = mon["device"]
            save_config(self.config)
            if not quiet:
                self.log(f"[SCREEN] {msg}", "SUCCESS")
                if rect:
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    self.log(f"  └─ Roblox Rect: ({rect.left}, {rect.top}) to ({rect.right}, {rect.bottom}) | Window Size: {w}x{h}", "INFO")
        else:
            self.screen_badge.config(text="[ SCREEN: UNKNOWN ]", fg="#f85149")
            if not quiet:
                self.log(f"[SCREEN] {msg}", "WARN")

    def _on_screen_selected(self, event=None):
        sel = self.screen_mode_var.get()
        self.config["screen_selection"] = sel
        save_config(self.config)
        if "Auto-Detect" in sel:
            self.auto_detect_screen()
            return
        for m in getattr(self, "monitors_cache", []):
            if m["label"] == sel:
                self.active_monitor = m
                dev_name = m.get("dev_name") or m["device"].split("\\")[-1]
                badge_text = f"[ 🖥️ {m['width']}x{m['height']} {m['orientation']} • {dev_name} ]"
                self.screen_badge.config(text=badge_text, fg="#58a6ff")
                self.log(f"[SCREEN] Switched to {sel}", "INFO")
                return
        presets = {
            "1024x1280": (1024, 1280, "Portrait"),
            "1080x1920": (1080, 1920, "Portrait"),
            "1920x1080": (1920, 1080, "Landscape"),
            "1366x768":  (1366, 768,  "Landscape"),
            "2560x1440": (2560, 1440, "Landscape"),
        }
        for k, (w, h, orient) in presets.items():
            if k in sel:
                badge_text = f"[ 🖥️ {w}x{h} {orient} Preset ]"
                self.screen_badge.config(text=badge_text, fg="#e3b341")
                self.log(f"[SCREEN] Selected Preset: {w}x{h} ({orient})", "INFO")
                return

    def center_pins_for_current_screen(self):
        mon = getattr(self, "active_monitor", None)
        if not mon:
            r_hwnd = self.get_roblox_hwnd()
            mon, _, _ = detect_roblox_screen(r_hwnd)

        if mon:
            left, top, w, h = mon["left"], mon["top"], mon["width"], mon["height"]
        else:
            sel = self.screen_mode_var.get()
            if "1024x1280" in sel:
                left, top, w, h = -1024, 8, 1024, 1280
            elif "1080x1920" in sel:
                left, top, w, h = 0, 0, 1080, 1920
            elif "1920x1080" in sel:
                left, top, w, h = 0, 0, 1920, 1080
            else:
                left, top, w, h = 0, 0, 1366, 768

        new_aim_x = left + int(w * 0.50)
        new_aim_y = top + int(h * 0.32)
        new_bar_x = left + int(w * 0.50)
        new_bar_y = top + int(h * 0.91)

        is_portrait = h > w
        if is_portrait:
            new_gear_x = left + int(w * 0.05)
            new_gear_y = top + int(h * 0.38)
            new_search_x = left + int(w * 0.65)
            new_search_y = top + int(h * 0.22)
            new_rod_x = left + int(w * 0.45)
            new_rod_y = top + int(h * 0.30)
            new_slot_x = left + int(w * 0.42)
            new_slot_y = top + int(h * 0.95)
        else:
            new_gear_x = left + int(w * 0.12)
            new_gear_y = top + int(h * 0.40)
            new_search_x = left + int(w * 0.70)
            new_search_y = top + int(h * 0.25)
            new_rod_x = left + int(w * 0.45)
            new_rod_y = top + int(h * 0.38)
            new_slot_x = left + int(w * 0.43)
            new_slot_y = top + int(h * 0.94)

        self.config["cast_aim_x"] = new_aim_x
        self.config["cast_aim_y"] = new_aim_y
        self.config["calibrated_bar_x"] = new_bar_x
        self.config["calibrated_bar_y"] = new_bar_y
        self.config["gear_tab_x"] = new_gear_x
        self.config["gear_tab_y"] = new_gear_y
        self.config["bag_search_x"] = new_search_x
        self.config["bag_search_y"] = new_search_y
        self.config["bag_rod_x"] = new_rod_x
        self.config["bag_rod_y"] = new_rod_y
        self.config["rod_slot_x"] = new_slot_x
        self.config["rod_slot_y"] = new_slot_y
        save_config(self.config)

        self._update_aim_label()
        self.bar_coord_lbl.config(text=f"Green Bar: ({new_bar_x}, {new_bar_y})")
        if self.aim_pin:
            self.aim_pin.update_coords(new_aim_x, new_aim_y)
        if self.bar_pin:
            self.bar_pin.update_coords(new_bar_x, new_bar_y)
        if self.gear_pin:
            self.gear_pin.update_coords(new_gear_x, new_gear_y)
        if self.search_pin:
            self.search_pin.update_coords(new_search_x, new_search_y)
        if self.bag_rod_pin:
            self.bag_rod_pin.update_coords(new_rod_x, new_rod_y)
        if self.slot_pin:
            self.slot_pin.update_coords(new_slot_x, new_slot_y)

        self.log(f"[PINS] Centered pins for {w}x{h} -> Water Aim: ({new_aim_x}, {new_aim_y}), Green Bar: ({new_bar_x}, {new_bar_y})", "SUCCESS")
        try:
            winsound.Beep(1300, 100)
        except Exception:
            pass

    # =========================================================================
    # Aim Spot Adjustment & Test
    # =========================================================================
    def adjust_aim_spot(self, dx, dy):
        use_adb = self.config.get("use_adb", False)
        if use_adb:
            cur_x = self.config.get("adb_cast_x", 640)
            cur_y = self.config.get("adb_cast_y", 420)
            new_x = max(50, min(1230, cur_x + dx))
            new_y = max(50, min(670, cur_y + dy))
            self.config["adb_cast_x"] = new_x
            self.config["adb_cast_y"] = new_y
            self.config["adb_reel_x"] = new_x
            self.config["adb_reel_y"] = new_y
            save_config(self.config)
            self._update_aim_label()
            self.log(f"[AIM] Water Aim (ADB) adjusted to ({new_x}, {new_y})", "INFO")
        else:
            cur_x = self.config.get("cast_aim_x", 960)
            cur_y = self.config.get("cast_aim_y", 540)
            new_x = cur_x + dx
            new_y = cur_y + dy
            self.config["cast_aim_x"] = new_x
            self.config["cast_aim_y"] = new_y
            save_config(self.config)
            self._update_aim_label()
            if self.aim_pin:
                self.aim_pin.update_coords(new_x, new_y)
            self.log(f"[AIM] Water Aim (Screen) adjusted to ({new_x}, {new_y})", "INFO")

    def adjust_bar_spot(self, dx, dy):
        cur_x = self.config.get("calibrated_bar_x", 960)
        cur_y = self.config.get("calibrated_bar_y", 720)
        new_x = cur_x + dx
        new_y = cur_y + dy
        self.config["calibrated_bar_x"] = new_x
        self.config["calibrated_bar_y"] = new_y
        save_config(self.config)
        self.bar_coord_lbl.config(text=f"Green Bar: ({new_x}, {new_y})")
        if self.bar_pin:
            self.bar_pin.update_coords(new_x, new_y)
        self.log(f"[BAR] Green Bar target moved to ({new_x}, {new_y})", "INFO")

    def auto_align_bar(self):
        aim_x = self.config.get("cast_aim_x", 960)
        aim_y = self.config.get("cast_aim_y", 540)
        mon = getattr(self, "active_monitor", None)
        if mon and mon.get("orientation") == "Portrait":
            new_bar_x = aim_x
            new_bar_y = mon.get("top", 0) + int(mon.get("height", 1280) * 0.91)
        else:
            new_bar_x = aim_x
            new_bar_y = aim_y + 160
        self.config["calibrated_bar_x"] = new_bar_x
        self.config["calibrated_bar_y"] = new_bar_y
        save_config(self.config)
        self.bar_coord_lbl.config(text=f"Green Bar: ({new_bar_x}, {new_bar_y})")
        if self.bar_pin:
            self.bar_pin.update_coords(new_bar_x, new_bar_y)
        self.log(f"[ALIGN] Bar pin auto-aligned below Water Aim to ({new_bar_x}, {new_bar_y})", "SUCCESS")
        try:
            winsound.Beep(1400, 100)
        except Exception:
            pass

    # =========================================================================
    # Draggable Target Pins
    # =========================================================================
    def toggle_pins(self):
        self.pins_visible = not self.pins_visible
        if self.pins_visible:
            self.pin_toggle_btn.config(text="📍 Hide Target Pins", bg="#58a6ff", fg="#0d1117")
            # 1. Aim Pin
            aim_x = self.config.get("cast_aim_x", 960)
            aim_y = self.config.get("cast_aim_y", 540)
            self.aim_pin = DraggablePin(self.root, "🎣 WATER AIM", aim_x, aim_y, "#58a6ff", on_moved=self._on_aim_moved)

            # 2. Bar Pin
            bar_x = self.config.get("calibrated_bar_x", 960)
            bar_y = self.config.get("calibrated_bar_y", 720)
            self.bar_pin = DraggablePin(self.root, "🎯 GREEN BAR", bar_x, bar_y, "#39d353", on_moved=self._on_bar_moved)
            self.log("[PINS] Target pins shown! Drag the green pin directly over Roblox's minigame bar.", "INFO")
        else:
            self.pin_toggle_btn.config(text="📍 Show Target Pins", bg="#21262d", fg="#58a6ff")
            if self.aim_pin:
                self.aim_pin.destroy()
                self.aim_pin = None
            if self.bar_pin:
                self.bar_pin.destroy()
                self.bar_pin = None
            self.log("[PINS] Target pins hidden.", "INFO")

    def _on_aim_moved(self, x, y):
        self.config["cast_aim_x"] = x
        self.config["cast_aim_y"] = y

        # Auto-map to LDPlayer touch coordinates if dropped inside LDPlayer window
        rect = get_ldplayer_rect()
        if rect:
            l, t, r, b = rect
            w = r - l
            h = b - t
            if l <= x <= r and t <= y <= b and w > 100 and h > 100:
                ax = int(((x - l) / w) * 1280)
                ay = int(((y - t) / h) * 720)
                self.config["adb_cast_x"] = max(50, min(1230, ax))
                self.config["adb_cast_y"] = max(50, min(670, ay))
                self.config["adb_reel_x"] = max(50, min(1230, ax))
                self.config["adb_reel_y"] = max(50, min(670, ay))
                self.log(f"[AIM] Pin auto-mapped to LDPlayer touch: X={self.config['adb_cast_x']}, Y={self.config['adb_cast_y']}", "SUCCESS")

        save_config(self.config)
        self._update_aim_label()
        try:
            winsound.Beep(1200, 80)
        except Exception:
            pass

    def _on_bar_moved(self, x, y):
        self.config["calibrated_bar_x"] = int(x)
        self.config["calibrated_bar_y"] = int(y)
        save_config(self.config)
        self.bar_coord_lbl.config(text=f"Green Bar: ({int(x)}, {int(y)})")
        col = self.display.get_pixel(x, y)
        if col:
            matched, tag = is_green_or_stop(*col)
            if matched and tag == "GREEN_BAR":
                self.config["calibrated_color"] = list(col)
                self.log(f"[BAR] Green Bar target locked to ({x}, {y}) with active color RGB{tuple(col)}", "SUCCESS")
            else:
                self.log(f"[BAR] Target pin moved to ({x}, {y}). Will trigger when bright lime-green bar appears here.", "INFO")
        try:
            winsound.Beep(1500, 100)
        except Exception:
            pass

    # =========================================================================
    # Auto Re-Equip Rod System (Slot 3)
    # =========================================================================
    def _on_auto_reequip_toggle(self):
        val = self.auto_reequip_var.get()
        self.config["auto_reequip_enabled"] = val
        save_config(self.config)
        status_str = "ENABLED" if val else "DISABLED"
        self.log(f"[RE-EQUIP] Auto Re-Equip {status_str}.", "INFO")
        try:
            winsound.Beep(1300 if val else 800, 80)
        except Exception:
            pass

    def _on_gear_moved(self, x, y):
        self.config["gear_tab_x"] = int(x)
        self.config["gear_tab_y"] = int(y)
        save_config(self.config)
        self.log(f"[RE-EQUIP] Gear Tab set to ({int(x)}, {int(y)})", "INFO")
        try:
            winsound.Beep(1200, 80)
        except Exception:
            pass

    def _on_search_moved(self, x, y):
        self.config["bag_search_x"] = int(x)
        self.config["bag_search_y"] = int(y)
        save_config(self.config)
        self.log(f"[RE-EQUIP] Bag Search Box set to ({int(x)}, {int(y)})", "INFO")
        try:
            winsound.Beep(1200, 80)
        except Exception:
            pass

    def _on_bag_rod_moved(self, x, y):
        self.config["bag_rod_x"] = int(x)
        self.config["bag_rod_y"] = int(y)
        save_config(self.config)
        self.log(f"[RE-EQUIP] Bag Rod Position set to ({int(x)}, {int(y)})", "INFO")
        try:
            winsound.Beep(1200, 80)
        except Exception:
            pass

    def _set_action_status(self, text, fg="#e3b341"):
        """Thread-safe update for the Current Action status card."""
        try:
            self.root.after(0, lambda t=text, c=fg: self.action_card.val_lbl.config(text=t, fg=c))
        except Exception:
            pass

    def _sample_slot_cross(self, slot_x, slot_y):
        """Samples a 5-point cross around (slot_x, slot_y) for resilient icon comparison."""
        offsets = [(0, 0), (-8, 0), (8, 0), (0, -8), (0, 8)]
        samples = []
        for dx, dy in offsets:
            col = self.display.get_pixel(slot_x + dx, slot_y + dy)
            samples.append(list(col) if col else None)
        return samples

    def _on_slot_moved(self, x, y):
        self.config["rod_slot_x"] = int(x)
        self.config["rod_slot_y"] = int(y)
        col = self.display.get_pixel(x, y)
        samples = self._sample_slot_cross(x, y)
        if col:
            self.config["rod_slot_active_color"] = list(col)
            if all(s is not None for s in samples):
                self.config["rod_slot_active_colors"] = samples
            self.log(f"[RE-EQUIP] Rod Slot 3 locked to ({int(x)}, {int(y)}) with baseline RGB{tuple(col)}", "SUCCESS")
        else:
            self.log(f"[RE-EQUIP] Rod Slot 3 set to ({int(x)}, {int(y)})", "INFO")
        save_config(self.config)
        try:
            winsound.Beep(1400, 80)
        except Exception:
            pass

    def toggle_reequip_pins(self):
        self.reequip_pins_visible = not self.reequip_pins_visible
        if self.reequip_pins_visible:
            self.btn_reequip_pins.config(text="🎒 Hide Re-Equip Pins", bg="#bc8cff", fg="#0d1117")
            # Focus Roblox and send '~' to open bag
            if not self.config.get("use_adb", False):
                self._send_tilde_to_roblox()
            else:
                self.adb.press_key(68) # KEYCODE_GRAVE

            gx = self.config.get("gear_tab_x", -760)
            gy = self.config.get("gear_tab_y", 480)
            self.gear_pin = DraggablePin(self.root, "⚙️ GEAR TAB", gx, gy, "#58a6ff", on_moved=self._on_gear_moved)

            sx = self.config.get("bag_search_x", -360)
            sy = self.config.get("bag_search_y", 280)
            self.search_pin = DraggablePin(self.root, "🔍 BAG SEARCH", sx, sy, "#e3b341", on_moved=self._on_search_moved)

            rx = self.config.get("bag_rod_x", -570)
            ry = self.config.get("bag_rod_y", 380)
            self.bag_rod_pin = DraggablePin(self.root, "🎣 ROD IN BAG", rx, ry, "#ff7b72", on_moved=self._on_bag_rod_moved)

            slot_x = self.config.get("rod_slot_x", -588)
            slot_y = self.config.get("rod_slot_y", 1215)
            self.slot_pin = DraggablePin(self.root, "🔢 ROD SLOT 3", slot_x, slot_y, "#bc8cff", on_moved=self._on_slot_moved)

            self.log("[PINS] Re-Equip pins shown & Bag opened! Drag the 4 pins to calibrate:", "SUCCESS")
            self.log("  1. ⚙️ GEAR TAB (Blue) -> Place on the Gear/Bat icon on the left.", "INFO")
            self.log("  2. 🔍 BAG SEARCH (Yellow) -> Place on the 'search' text box.", "INFO")
            self.log("  3. 🎣 ROD IN BAG (Orange) -> Place on the first rod item in the bag.", "INFO")
            self.log("  4. 🔢 ROD SLOT 3 (Purple) -> Place on Hotbar Slot 3.", "INFO")
        else:
            self.btn_reequip_pins.config(text="🎒 Re-Equip Pins", bg="#21262d", fg="#bc8cff")
            for pin in [self.gear_pin, self.search_pin, self.bag_rod_pin, self.slot_pin]:
                if pin:
                    try:
                        pin.destroy()
                    except Exception:
                        pass
            self.gear_pin = None
            self.search_pin = None
            self.bag_rod_pin = None
            self.slot_pin = None

            # Focus Roblox and send '~' to close bag
            if not self.config.get("use_adb", False):
                self.ensure_roblox_focused()
                time.sleep(0.08)
                key_tap(0xC0) # Close bag
            else:
                self.adb.press_key(68)
            self.log("[PINS] Re-Equip pins hidden & Bag closed.", "INFO")

    def _is_slot_displaced(self, slot_x, slot_y, active_colors):
        """Returns (displaced: bool, changed_count: int, max_diff: int) for a 5-point cross."""
        cur_samples = self._sample_slot_cross(slot_x, slot_y)
        changed = 0
        max_diff = 0
        valid = 0
        for cur, base in zip(cur_samples, active_colors):
            if cur is None or base is None:
                continue
            valid += 1
            d = color_diff(cur, base)
            if d > max_diff:
                max_diff = d
            if d > 110:
                changed += 1
        if valid == 0:
            return False, 0, 0
        # Require at least 3 of 5 points (majority) to change drastically
        needed = min(3, max(1, (valid + 1) // 2))
        return changed >= needed, changed, max_diff

    def check_rod_equipped(self) -> bool:
        """
        Verifies the rod is in Slot N by comparing a 5-point cross baseline.
        On first use, auto-captures the 5-point baseline.
        Uses majority voting (>= 3/5 points shifted > 110) + a 0.35s confirmation
        re-check to prevent random false positives from weather/lighting/popups.
        Returns True (rod OK) or False (rod missing, re-equip needed).
        """
        if not self.config.get("auto_reequip_enabled", True):
            return True

        slot_x = self.config.get("rod_slot_x")
        slot_y = self.config.get("rod_slot_y")
        if slot_x is None or slot_y is None:
            return True

        active_col = self.config.get("rod_slot_active_color")
        active_colors = self.config.get("rod_slot_active_colors") or []

        # Auto-capture 5-point baseline if unset or upgrading from legacy single-pixel config
        if not active_col or active_col == [255, 255, 255] or len(active_colors) != 5:
            samples = self._sample_slot_cross(slot_x, slot_y)
            if not samples[0]:
                return True
            self.config["rod_slot_active_color"] = samples[0]
            if all(s is not None for s in samples):
                self.config["rod_slot_active_colors"] = samples
            save_config(self.config)
            self.log(
                f"[RE-EQUIP] 📸 Captured 5-pt rod baseline at ({slot_x},{slot_y}) = RGB{tuple(samples[0])}",
                "SUCCESS"
            )
            return True

        displaced, changed, max_diff = self._is_slot_displaced(slot_x, slot_y, active_colors)
        if not displaced:
            return True

        # Confirmation re-check after 0.35s to filter transient overlays/lighting flashes
        time.sleep(0.35)
        if not self.is_running and not self.test_mode:
            return True
        displaced2, changed2, max_diff2 = self._is_slot_displaced(slot_x, slot_y, active_colors)
        if not displaced2:
            return True

        self.log(
            f"[RE-EQUIP] ⚠ Rod slot confirmed changed ({changed2}/5 pts, max_diff={max_diff2}). Rod displaced!",
            "WARN"
        )
        return False

    def _send_tilde_to_roblox(self):
        """
        Reliably sends the ~ key to open/close the bag in Roblox.
        Brings Roblox to the foreground and uses PostMessage so the key
        reaches the game even if another window steals focus mid-sequence.
        VK_OEM_3 = 0xC0, scan code = 0x29.
        """
        r_hwnd = self.get_roblox_hwnd()
        if r_hwnd:
            focus_window(r_hwnd)
            time.sleep(0.10)
        scan = ctypes.windll.user32.MapVirtualKeyW(0xC0, 0)  # → 0x29
        # Use both keybd_event AND PostMessage for maximum reliability
        ctypes.windll.user32.keybd_event(0xC0, scan, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(0xC0, scan, KEYEVENTF_KEYUP, 0)

    def execute_reequip(self) -> bool:
        """Executes the full bag-open → gear tab → search → drag → close → equip sequence."""
        use_adb = self.config.get("use_adb", False)
        gear_x  = self.config.get("gear_tab_x")
        gear_y  = self.config.get("gear_tab_y")
        search_x = self.config.get("bag_search_x")
        search_y = self.config.get("bag_search_y")
        rod_x   = self.config.get("bag_rod_x")
        rod_y   = self.config.get("bag_rod_y")
        slot_x  = self.config.get("rod_slot_x")
        slot_y  = self.config.get("rod_slot_y")
        search_term = self.config.get("rod_search_term", "rod")
        slot_num    = self.config.get("rod_slot_number", 3)

        if any(v is None for v in [gear_x, gear_y, search_x, search_y, rod_x, rod_y, slot_x, slot_y]):
            self.log("[RE-EQUIP] ✗ Coordinates not set — click [🎒 Re-Equip Pins] to calibrate.", "ERROR")
            return False

        self.log(">>> [RE-EQUIP] Starting rod re-equip sequence...", "WARN")
        self._set_action_status("Re-Equipping Rod...", "#bc8cff")

        r_hwnd = self.get_roblox_hwnd()

        # ── Helper: focus Roblox before every step ───────────────────────────
        def focus_game():
            if r_hwnd:
                focus_window(r_hwnd)
                time.sleep(0.12)

        # ── 1. Open Bag ───────────────────────────────────────────────────────
        self.log("  └─ 1. Opening bag [~]...", "INFO")
        if use_adb:
            self.adb.press_key(68)   # KEYCODE_GRAVE
            time.sleep(0.75)
        else:
            self._send_tilde_to_roblox()
            time.sleep(0.85)         # Wait for bag open animation

        # ── 2. Click Gear tab ─────────────────────────────────────────────────
        self.log(f"  └─ 2. Gear tab → ({gear_x}, {gear_y})...", "INFO")
        if use_adb:
            self.adb.tap(gear_x, gear_y)
        else:
            focus_game()
            mouse_click_at(gear_x, gear_y, hold_time=0.08)
        time.sleep(0.45)

        # ── 3. Search for rod ─────────────────────────────────────────────────
        self.log(f"  └─ 3. Search '{search_term}' at ({search_x}, {search_y})...", "INFO")
        if use_adb:
            self.adb.tap(search_x, search_y)
            time.sleep(0.20)
            self.adb.clear_text(10)
            time.sleep(0.10)
            self.adb.send_text(search_term)
        else:
            focus_game()
            mouse_click_at(search_x, search_y, hold_time=0.08)
            time.sleep(0.25)
            clear_text_box()
            time.sleep(0.05)
            send_text(search_term)
        time.sleep(0.55)  # Wait for results

        # ── 4. Drag Rod → Slot ────────────────────────────────────────────────
        self.log(f"  └─ 4. Drag rod ({rod_x},{rod_y}) → slot {slot_num} ({slot_x},{slot_y})...", "INFO")
        if use_adb:
            self.adb.drag(rod_x, rod_y, slot_x, slot_y, duration_ms=600)
        else:
            focus_game()
            mouse_drag_at(rod_x, rod_y, slot_x, slot_y, duration=0.60, steps=30)
        time.sleep(0.45)

        # ── 5. Close Bag ──────────────────────────────────────────────────────
        self.log("  └─ 5. Closing bag [~]...", "INFO")
        if use_adb:
            self.adb.press_key(68)
            time.sleep(0.45)
        else:
            self._send_tilde_to_roblox()
            time.sleep(0.55)

        # ── 6. Press slot key to equip ────────────────────────────────────────
        self.log(f"  └─ 6. Pressing '{slot_num}' to equip rod...", "INFO")
        if use_adb:
            self.adb.press_key(7 + slot_num)
        else:
            focus_game()
            key_tap(0x30 + slot_num)   # 0x31='1' … 0x33='3'
        time.sleep(0.35)

        # ── 7. Only capture baseline if never calibrated (never overwrite good baseline) ──
        existing_col = self.config.get("rod_slot_active_color")
        existing_cross = self.config.get("rod_slot_active_colors") or []
        if not existing_col or existing_col == [255, 255, 255] or len(existing_cross) != 5:
            time.sleep(0.15)
            samples = self._sample_slot_cross(slot_x, slot_y)
            if samples[0]:
                self.config["rod_slot_active_color"] = samples[0]
                if all(s is not None for s in samples):
                    self.config["rod_slot_active_colors"] = samples
                save_config(self.config)
                self.log(f"  └─ Baseline captured: Slot {slot_num} = RGB{tuple(samples[0])}", "INFO")

        self.log(f">>> [RE-EQUIP] ✔ Rod back in Slot {slot_num}!", "SUCCESS")
        try:
            winsound.Beep(1800, 150)
        except Exception:
            pass
        return True

    def test_reequip_flow(self):
        """Manual test trigger for the re-equip workflow."""
        if self.is_running or self.test_mode:
            self.log("[TEST] Please pause fishing before running Re-Equip test.", "WARN")
            return
        def worker():
            self.root.after(0, lambda: self.btn_test_reequip.config(state="disabled", text="⏳ TESTING..."))
            try:
                self.execute_reequip()
            finally:
                self.root.after(0, lambda: self.btn_test_reequip.config(state="normal", text="🧪 Test Re-Equip"))
                self._set_action_status("Idle — Ready to Start", "#e3b341")
        threading.Thread(target=worker, daemon=True).start()


    # =========================================================================
    # Controls & Tuners
    # =========================================================================
    def toggle_running(self):
        with self.lock:
            self.is_running = not self.is_running
            if self.is_running:
                # Automatically hide pins so they never contaminate screen pixels
                if self.pins_visible:
                    self.toggle_pins()
                if self.reequip_pins_visible:
                    self.toggle_reequip_pins()
                if self.start_time is None:
                    self.start_time = time.time()
                self.status_badge.config(text="[ FISHING ]", fg="#2ea043", bg="#161b22")
                self.start_btn.config(text="⏸ PAUSE (F6)", bg="#da3633", activebackground="#f85149")
                self.action_card.val_lbl.config(text="Running — Auto Fishing", fg="#39d353")
                self.log(">>> AUTO-FISHING STARTED! Multitasking active.", "SUCCESS")
                try:
                    winsound.Beep(1200, 150)
                except Exception:
                    pass
            else:
                self.status_badge.config(text="[ PAUSED ]", fg="#f85149", bg="#21262d")
                self.start_btn.config(text="▶ START (F6)", bg="#238636", activebackground="#2ea043")
                self.action_card.val_lbl.config(text="Paused", fg="#e3b341")
                self.log(f">>> AUTO-FISHING PAUSED. Total catches so far: {self.total_catches}", "WARN")
                try:
                    winsound.Beep(700, 150)
                except Exception:
                    pass

    def run_test(self):
        if not self.is_running and not self.test_mode:
            # Auto-hide pins immediately on UI thread so clicks & pixel detection reach the game window
            if self.pins_visible:
                self.toggle_pins()
            if self.reequip_pins_visible:
                self.toggle_reequip_pins()
            threading.Thread(target=self._run_single_test_worker, daemon=True).start()

    def _run_single_test_worker(self):
        with self.lock:
            self.test_mode = True

        self.root.after(0, lambda: self.status_badge.config(text="[ TESTING 1 CYCLE ]", fg="#e3b341", bg="#161b22"))
        self.root.after(0, lambda: self.test_btn.config(text="⏳ TESTING...", bg="#da3633", fg="#ffffff"))
        self.log(">>> [TEST] Starting 1 full fishing cycle test (Throw -> Bite Watch -> Reel)...", "WARN")
        try:
            start = time.time()
            self.do_fishing_cycle()
            total_time = time.time() - start
            self.log(f">>> [TEST] Test cycle finished in {total_time:.2f}s!", "SUCCESS")
        except Exception as e:
            self.log(f">>> [TEST] Test cycle error: {e}", "ERROR")
        finally:
            with self.lock:
                self.test_mode = False
            self.root.after(0, lambda: self.status_badge.config(text="[ PAUSED ]", fg="#f85149", bg="#21262d"))
            self.root.after(0, lambda: self.test_btn.config(text="🎯 TEST 1 CYCLE (F7)", bg="#21262d", fg="#c9d1d9"))
            self.root.after(0, lambda: self.action_card.val_lbl.config(text="Idle — Ready to Start", fg="#e3b341"))

    def adjust_cast_time(self, delta):
        cur = self.config.get("cast_hold_duration", 1.05)
        new_val = round(max(0.2, min(5.0, cur + delta)), 2)
        self.config["cast_hold_duration"] = new_val
        save_config(self.config)
        self.cast_val_lbl.config(text=f"{new_val:.2f}s")
        self.log(f"[CONFIG] Cast Hold set to {new_val:.2f}s", "INFO")
        try:
            winsound.Beep(1100 if delta > 0 else 800, 80)
        except Exception:
            pass

    def adjust_cooldown(self, delta):
        cur = self.config.get("post_catch_cooldown", 4.0)
        new_val = round(max(1.5, min(10.0, cur + delta)), 1)
        self.config["post_catch_cooldown"] = new_val
        save_config(self.config)
        self.cd_val_lbl.config(text=f"{new_val:.1f}s")
        self.log(f"[CONFIG] Popup Wait set to {new_val:.1f}s", "INFO")
        try:
            winsound.Beep(1100 if delta > 0 else 800, 80)
        except Exception:
            pass

    def show_instructions(self):
        if self.instructions_win and self.instructions_win.winfo_exists():
            self.instructions_win.lift()
            self.instructions_win.focus_force()
            return

        win = tk.Toplevel(self.root)
        self.instructions_win = win
        win.title("📖 How to Use — Auto-Fisher Quick Guide")
        win.geometry("540x510")
        win.configure(bg="#0c0d10")
        win.resizable(False, False)
        win.attributes("-topmost", True)

        try:
            self.root.update_idletasks()
            rx = self.root.winfo_x()
            ry = self.root.winfo_y()
            rw = self.root.winfo_width()
            rh = self.root.winfo_height()
            x = max(0, rx + (rw - 540) // 2)
            y = max(0, ry + (rh - 510) // 2)
            win.geometry(f"+{x}+{y}")
        except Exception:
            pass

        hdr = tk.Frame(win, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
        hdr.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(hdr, text="🎣 QUICK START & INSTRUCTION GUIDE", fg="#58a6ff", bg="#161b22", font=("Consolas", 10, "bold")).pack(side="left", padx=10, pady=8)

        content_frame = tk.Frame(win, bg="#0d1117", highlightbackground="#30363d", highlightthickness=1)
        content_frame.pack(fill="both", expand=True, padx=12, pady=6)

        txt = scrolledtext.ScrolledText(content_frame, bg="#0d1117", fg="#c9d1d9", font=("Consolas", 9), bd=0, relief="flat", wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)

        txt.tag_config("HEADER", foreground="#58a6ff", font=("Consolas", 9, "bold"))
        txt.tag_config("STEP", foreground="#39d353", font=("Consolas", 9, "bold"))
        txt.tag_config("KEY", foreground="#e3b341", font=("Consolas", 9, "bold"))
        txt.tag_config("BODY", foreground="#c9d1d9")

        instructions = [
            ("STEP 1: SELECT CLIENT MODE", "HEADER"),
            ("\n• ", "BODY"),
            ("🖥️ Plain Windows Mode:", "STEP"),
            (" For standard Roblox PC desktop client.\n• ", "BODY"),
            ("⚡ LDPlayer ADB Mode:", "STEP"),
            (" For LDPlayer emulator (100% background, zero mouse movement).\n\n", "BODY"),

            ("STEP 2: SCREEN / MONITOR SETUP", "HEADER"),
            ("\n• Click ", "BODY"),
            ("[ 🔍 Detect Roblox Screen ]", "KEY"),
            (" to auto-detect the screen Roblox is running on (Landscape or Portrait).\n• Click ", "BODY"),
            ("[ 📍 Center Pins to Screen ]", "KEY"),
            (" to reset targeting pins to default game proportions.\n\n", "BODY"),

            ("STEP 3: PLACE TARGET PINS", "HEADER"),
            ("\n• Click ", "BODY"),
            ("[ 📍 Show Target Pins ]", "KEY"),
            (" to display the two floating pins:\n", "BODY"),
            ("   1. 🎣 WATER AIM (Cyan):", "STEP"),
            (" Drag onto the purple pond where your rod should cast.\n", "BODY"),
            ("   2. 🎯 GREEN BAR (Green):", "STEP"),
            (" Drag over where the minigame green bar appears.\n", "BODY"),
            ("• Tip: Click ", "BODY"),
            ("[ 📐 Auto-Align Bar ]", "KEY"),
            (" to place the bar pin right below the water aim.\n\n", "BODY"),

            ("STEP 4: TEST 1 CYCLE", "HEADER"),
            ("\n• Click ", "BODY"),
            ("[ 🎯 TEST 1 CYCLE (F7) ]", "KEY"),
            (" to verify your setup.\n  Target pins automatically hide so clicks and color sampling reach Roblox directly.\n\n", "BODY"),

            ("STEP 5: START AUTO-FISHING", "HEADER"),
            ("\n• Press ", "BODY"),
            ("F6", "KEY"),
            (" or click ", "BODY"),
            ("[ ▶ START (F6) ]", "STEP"),
            (" to start auto-fishing.\n• Press ", "BODY"),
            ("F6", "KEY"),
            (" again anytime to pause.\n\n", "BODY"),

            ("STEP 6: AUTO RE-EQUIP ROD (SLOT 3)", "HEADER"),
            ("\n• When your hotbar fills up with caught eggs, Roblox pushes your fishing rod into your backpack.\n• Check ", "BODY"),
            ("[✔] Auto Re-Equip Rod (Slot 3)", "STEP"),
            (" to keep fishing forever unattended!\n• Click ", "BODY"),
            ("[ 🎒 Re-Equip Pins ]", "KEY"),
            (" to open the game bag and calibrate the 4 pins:\n", "BODY"),
            ("   1. ⚙️ GEAR TAB (Blue):", "STEP"),
            (" Place on the Gear/Bat icon on the bag's left sidebar.\n", "BODY"),
            ("   2. 🔍 BAG SEARCH (Yellow):", "STEP"),
            (" Place on the bag's 'search' text box.\n", "BODY"),
            ("   3. 🎣 ROD IN BAG (Orange):", "STEP"),
            (" Place on the first rod item in the bag.\n", "BODY"),
            ("   4. 🔢 ROD SLOT 3 (Purple):", "STEP"),
            (" Place on Hotbar Slot 3.\n", "BODY"),
            ("• Click ", "BODY"),
            ("[ 🧪 Test Re-Equip ]", "KEY"),
            (" anytime to test the automated bag opening, search, and swap sequence.\n\n", "BODY"),

            ("SHORTCUT HOTKEYS", "HEADER"),
            ("\n• ", "BODY"),
            ("F6:", "KEY"),
            (" Start / Pause Auto-Fisher\n• ", "BODY"),
            ("F7:", "KEY"),
            (" Test 1 Fishing Cycle\n• ", "BODY"),
            ("F1 / F2:", "KEY"),
            (" Decrease / Increase Cast Hold (±0.05s)\n• ", "BODY"),
            ("F9 / F10:", "KEY"),
            (" Decrease / Increase Popup Wait (±0.5s)\n• ", "BODY"),
            ("F8:", "KEY"),
            (" Exit Application\n", "BODY")
        ]

        for text, tag in instructions:
            txt.insert("end", text, tag)
        txt.config(state="disabled")

        btn_box = tk.Frame(win, bg="#0c0d10")
        btn_box.pack(fill="x", padx=12, pady=(4, 10))
        tk.Button(
            btn_box, text="✔ Got It / Close", bg="#21262d", fg="#58a6ff",
            activebackground="#30363d", activeforeground="#ffffff",
            font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=16, pady=4,
            command=win.destroy
        ).pack(side="right")

    # =========================================================================
    # Fishing Loop Engine
    # =========================================================================
    def get_roblox_hwnd(self):
        if self.roblox_hwnd and ctypes.windll.user32.IsWindow(self.roblox_hwnd):
            return self.roblox_hwnd

        # 1. Try class name WINDOWSCLIENT (Standard Roblox desktop client)
        h = ctypes.windll.user32.FindWindowW("WINDOWSCLIENT", None)
        if h and ctypes.windll.user32.IsWindow(h):
            self.roblox_hwnd = h
            return h

        # 2. Try window title "Roblox"
        h = ctypes.windll.user32.FindWindowW(None, "Roblox")
        if h and ctypes.windll.user32.IsWindow(h):
            self.roblox_hwnd = h
            return h

        # 3. EnumWindows checking class name, window title, or player name
        found_h = None
        def enum_cb(hwnd, _):
            nonlocal found_h
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                cbuf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, cbuf, 256)
                if cbuf.value == "WINDOWSCLIENT":
                    found_h = hwnd
                    return False
                buf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                title = buf.value.lower()
                if "roblox" in title:
                    found_h = hwnd
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        if not found_h:
            try:
                hdesk = ctypes.windll.user32.OpenDesktopW("default", 0, False, 0x01FF)
                if hdesk:
                    def enum_desk_cb(hwnd, _):
                        nonlocal found_h
                        if ctypes.windll.user32.IsWindowVisible(hwnd):
                            cbuf = ctypes.create_unicode_buffer(256)
                            ctypes.windll.user32.GetClassNameW(hwnd, cbuf, 256)
                            if cbuf.value == "WINDOWSCLIENT":
                                found_h = hwnd
                                return False
                            buf = ctypes.create_unicode_buffer(256)
                            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                            title = buf.value.lower()
                            if "roblox" in title:
                                found_h = hwnd
                                return False
                        return True
                    ctypes.windll.user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_desk_cb), 0)
                    ctypes.windll.user32.CloseDesktop(hdesk)
            except Exception:
                pass
        if found_h:
            self.roblox_hwnd = found_h
            return found_h

        # 4. Check window directly under the calibrated bar or water aim point
        for pt_key in [("calibrated_bar_x", "calibrated_bar_y"), ("cast_aim_x", "cast_aim_y")]:
            cx = self.config.get(pt_key[0])
            cy = self.config.get(pt_key[1])
            if cx is not None and cy is not None:
                pt = POINT(int(cx), int(cy))
                h = ctypes.windll.user32.WindowFromPoint(pt)
                if h:
                    root = ctypes.windll.user32.GetAncestor(h, GA_ROOT)
                    target = root if (root and ctypes.windll.user32.IsWindow(root)) else h
                    self.roblox_hwnd = target
                    return target

        return None

    def ensure_roblox_focused(self):
        hwnd = self.get_roblox_hwnd()
        if hwnd:
            focus_window(hwnd)
            time.sleep(0.06)
            return True
        return False

    def check_minigame_active(self, baseline_colors=None):
        calib_x = self.config.get("calibrated_bar_x")
        calib_y = self.config.get("calibrated_bar_y")

        if calib_x is None or calib_y is None:
            return False

        # Scan a horizontal strip of points across the minigame bar:
        # The bar in Roblox is ~350-400px wide. Checking multiple offsets ensures that
        # even if the user pinned slightly left, right, or directly over the center fish icon,
        # the vibrant lime-green segmented bar wings or STOP button are caught immediately.
        offsets = [(-60, 0), (-35, 0), (0, 0), (35, 0), (60, 0), (-25, -4), (25, 4)]
        for i, (dx, dy) in enumerate(offsets):
            col = self.display.get_pixel(calib_x + dx, calib_y + dy)
            if col:
                r, g, b = col
                # If baseline is provided, require a noticeable change from pre-cast state
                # to prevent static grass, static wallpaper, or static UI from ever triggering!
                if baseline_colors and i < len(baseline_colors):
                    br, bg, bb = baseline_colors[i]
                    diff = abs(r - br) + abs(g - bg) + abs(b - bb)
                    if diff < 35:
                        continue # Unchanged pixel -> ignore static background

                is_match, tag = is_green_or_stop(r, g, b)
                if is_match and (tag == "GREEN_BAR" or tag == "STOP_BUTTON"):
                    return True
        return False

    def run_anti_afk(self):
        if not self.config.get("anti_afk_enabled", True):
            return
        now = time.time()
        interval = self.config.get("anti_afk_interval_seconds", 120)
        if now - self.last_anti_afk >= interval:
            self.last_anti_afk = now
            self.log("[ANTI-AFK] Resetting Roblox 20-min idle timer...", "MAGENTA")
            if self.config.get("use_adb", False):
                self.adb.anti_afk_jump()
            else:
                key_tap(VK_SPACE)

    def do_fishing_cycle(self):
        jitter = self.config.get("jitter_amount", 0.015)
        max_wait = self.config.get("max_bite_wait_seconds", 24.0)
        min_buffer = self.config.get("min_wait_before_bite", 1.8)
        use_adb = self.config.get("use_adb", False)

        cast_time = self.config.get("cast_hold_duration", 1.05)
        self.total_casts += 1

        # Check if rod is equipped in slot 3 before casting
        if self.config.get("auto_reequip_enabled", True):
            if not self.check_rod_equipped():
                self.log("[RE-EQUIP] Rod appears missing or displaced from Slot 3! Initiating auto re-equip...", "WARN")
                self.execute_reequip()
                if not self.is_running and not self.test_mode:
                    return

        # ---------------------------------------------------------------------
        # 1. CASTING INTO WATER
        # ---------------------------------------------------------------------
        if use_adb:
            adb_x = self.config.get("adb_cast_x", 640)
            adb_y = self.config.get("adb_cast_y", 420)
            self._set_action_status(f"Holding Rod ({cast_time:.2f}s)...", "#e3b341")
            self.log(f"▶ Cast #{self.total_casts}: [⚡ Monkey Hold] Holding rod for {cast_time:.2f}s at ({adb_x}, {adb_y})...", "INFO")
            
            self.adb.cast_hold(adb_x, adb_y, duration=cast_time)
            self.log(f"  └─ [⚡ Monkey Hold] Released after exact {cast_time:.2f}s! (Perfect cast)", "SUCCESS")
        else:
            aim_x = self.config.get("cast_aim_x", 960)
            aim_y = self.config.get("cast_aim_y", 540)
            self._set_action_status(f"Casting ({cast_time:.2f}s hold)...", "#e3b341")
            self.log(f"▶ Cast #{self.total_casts}: Holding rod for {cast_time:.2f}s at ({aim_x}, {aim_y})...", "INFO")

            r_hwnd = self.get_roblox_hwnd()
            if r_hwnd:
                focus_window(r_hwnd)
                time.sleep(0.08)

            try:
                # Single continuous long-press hold for exact cast_time (1.05s) - NO premature taps!
                send_mouse_down_at(aim_x, aim_y)
                start_hold = time.perf_counter()
                while (time.perf_counter() - start_hold) < cast_time:
                    time.sleep(0.005)
            finally:
                send_mouse_up_at(aim_x, aim_y)

            self.log(f"  └─ Rod thrown! Released after exact {cast_time:.2f}s! (Perfect cast)", "SUCCESS")

        if not self.is_running and not self.test_mode:
            return

        # ---------------------------------------------------------------------
        # 2. BUFFER DELAY & BASELINE LOCK (Let bobber land in water)
        # ---------------------------------------------------------------------
        self._set_action_status(f"Line landing in water ({min_buffer:.1f}s)...", "#58a6ff")
        time.sleep(min_buffer)

        # ---------------------------------------------------------------------
        # 3. BACKGROUND BITE WATCH (Checks dynamically until green bar appears)
        # ---------------------------------------------------------------------
        calib_x = self.config.get("calibrated_bar_x", 960)
        calib_y = self.config.get("calibrated_bar_y", 720)
        self._set_action_status("Waiting for fish bite (Green Bar)...", "#39d353")
        self.log(f"  └─ Line in water! Waiting for green bar to appear (random 3-12s)...", "INFO")

        # Establish baseline colors across the detection strip right after line lands
        offsets = [(-60, 0), (-35, 0), (0, 0), (35, 0), (60, 0), (-25, -4), (25, 4)]
        baseline_colors = []
        for dx, dy in offsets:
            col = self.display.get_pixel(calib_x + dx, calib_y + dy)
            baseline_colors.append(col or (0, 0, 0))

        bite_detected = False
        watch_start = time.time()

        while (time.time() - watch_start) < max_wait:
            if not self.is_running and not self.test_mode:
                return

            if self.check_minigame_active(baseline_colors=baseline_colors):
                bite_detected = True
                break

            time.sleep(0.02) # 50 Hz responsive check

        wait_dur = time.time() - watch_start

        if not bite_detected:
            self.log(f"  └─ No bite detected ({wait_dur:.1f}s timeout). Recasting...", "WARN")
            if self.config.get("auto_reequip_enabled", True):
                if not self.check_rod_equipped():
                    self.log("[RE-EQUIP] Rod appears to have been displaced! Re-equipping now...", "WARN")
                    self.execute_reequip()
            human_sleep(1.0, jitter)
            return

        self.log(f"  └─ 🐟 FISH BIT! Green Bar detected after {wait_dur + min_buffer:.2f}s!", "SUCCESS")
        try:
            winsound.Beep(1600, 120)
        except Exception:
            pass

        # ---------------------------------------------------------------------
        # 4. RAPID REELING
        # ---------------------------------------------------------------------
        click_count = self.config.get("reeling_clicks", 16)
        click_interval = self.config.get("click_interval", 0.020)

        if use_adb:
            adb_reel_x = self.config.get("adb_reel_x", 640)
            adb_reel_y = self.config.get("adb_reel_y", 420)
            self._set_action_status(f"TURBO Reeling ({click_count} taps)...", "#e3b341")
            self.log(f"  └─ [⚡ Monkey Turbo] Rapid tapping {click_count} times (<0.5s)...", "INFO")
            self.adb.rapid_tap(adb_reel_x, adb_reel_y, count=click_count, interval=0.020)
            self.log("  └─ [⚡ Monkey Turbo] Reeling complete!", "SUCCESS")
        else:
            aim_x = self.config.get("cast_aim_x", 960)
            aim_y = self.config.get("cast_aim_y", 540)
            self._set_action_status(f"Reeling ({click_count} clicks)...", "#e3b341")
            self.log(f"  └─ Reeling in with {click_count} rapid clicks at ({aim_x}, {aim_y})...", "INFO")

            r_hwnd = self.get_roblox_hwnd()
            if r_hwnd:
                focus_window(r_hwnd)
                time.sleep(0.06)

            for i in range(click_count):
                if not self.is_running and not self.test_mode:
                    break
                mouse_click_at(aim_x, aim_y, hold_time=0.015)
                human_sleep(click_interval, jitter=jitter)

            self.log(f"  └─ Reeling complete ({click_count} clicks executed)!", "SUCCESS")

        self.total_catches += 1
        catches_str = str(self.total_catches)
        self.root.after(0, lambda s=catches_str: self.catches_card.val_lbl.config(text=s))
        self.log(f"  └─ Catch #{self.total_catches} secured!", "SUCCESS")

        if not self.is_running and not self.test_mode:
            return

        # ---------------------------------------------------------------------
        # 5. REWARD POPUP COOLDOWN
        # ---------------------------------------------------------------------
        cooldown = self.config.get("post_catch_cooldown", 4.0)
        self._set_action_status(f"Reward popup clearing ({cooldown:.1f}s)...", "#58a6ff")
        self.log(f"  └─ Waiting {cooldown:.1f}s for reward popup to clear...", "INFO")

        elapsed = 0.0
        step = 0.5
        while elapsed < cooldown:
            if not self.is_running and not self.test_mode:
                return
            time.sleep(step)
            elapsed += step

        self.log("  └─ Popup cleared! Ready for next cast.", "SUCCESS")

        # ---------------------------------------------------------------------
        # 6. ANTI-AFK
        # ---------------------------------------------------------------------
        self.run_anti_afk()

    def _fishing_worker(self):
        while not self.should_exit:
            if self.is_running:
                self.do_fishing_cycle()
            else:
                time.sleep(0.1)

    def _hotkey_listener(self):
        last_states = {}
        hotkeys = self.config.get("hotkeys", {})
        vk_keys = {
            "toggle": VK_MAP.get(hotkeys.get("toggle", "F6").upper(), 0x75),
            "dec_cast": VK_MAP.get(hotkeys.get("decrease_cast", "F1").upper(), 0x70),
            "inc_cast": VK_MAP.get(hotkeys.get("increase_cast", "F2").upper(), 0x71),
            "calib": VK_MAP.get(hotkeys.get("calibrate_bar", "F3").upper(), 0x72),
            "test": VK_MAP.get(hotkeys.get("test_single", "F7").upper(), 0x76),
            "dec_cd": VK_MAP.get(hotkeys.get("decrease_cooldown", "F9").upper(), 0x78),
            "inc_cd": VK_MAP.get(hotkeys.get("increase_cooldown", "F10").upper(), 0x79),
            "exit": VK_MAP.get(hotkeys.get("exit", "F8").upper(), 0x77),
        }

        while not self.should_exit:
            for action, vk in vk_keys.items():
                pressed = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
                if pressed and not last_states.get(action, False):
                    self._on_hotkey(action)
                last_states[action] = pressed
            time.sleep(0.04)

    def _on_hotkey(self, action):
        if action == "toggle":
            self.root.after(0, self.toggle_running)
        elif action == "dec_cast":
            self.root.after(0, lambda: self.adjust_cast_time(-0.05))
        elif action == "inc_cast":
            self.root.after(0, lambda: self.adjust_cast_time(+0.05))
        elif action == "calib":
            self.root.after(0, self._calibrate_bar_hotkey)
        elif action == "test":
            self.root.after(0, self.run_test)
        elif action == "dec_cd":
            self.root.after(0, lambda: self.adjust_cooldown(-0.5))
        elif action == "inc_cd":
            self.root.after(0, lambda: self.adjust_cooldown(+0.5))
        elif action == "exit":
            self.root.after(0, self.on_close)

    def _calibrate_bar_hotkey(self):
        x, y = get_cursor_pos()
        self._on_bar_moved(x, y)
        if self.bar_pin:
            self.bar_pin.update_coords(x, y)

    def on_close(self):
        self.should_exit = True
        self.is_running = False
        if self.aim_pin:
            self.aim_pin.destroy()
        if self.bar_pin:
            self.bar_pin.destroy()
        if self.reequip_pins_visible:
            for pin in [self.gear_pin, self.search_pin, self.bag_rod_pin, self.slot_pin]:
                if pin:
                    try:
                        pin.destroy()
                    except Exception:
                        pass
        if hasattr(self, "instructions_win") and self.instructions_win:
            try:
                self.instructions_win.destroy()
            except Exception:
                pass
        self.adb.close()
        self.display.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AutoFishGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
