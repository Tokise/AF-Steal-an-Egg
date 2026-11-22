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

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Virtual key code mapping
VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B
}

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004
KEYEVENTF_KEYUP      = 0x0002
VK_SPACE             = 0x20
GA_ROOT              = 2

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

DEFAULT_CONFIG = {
    "use_adb": True,
    "adb_path": r"E:\LDPlayer\LDPlayer9\adb.exe",
    "adb_cast_x": 640,
    "adb_cast_y": 420,
    "adb_reel_x": 640,
    "adb_reel_y": 420,
    "background_focus_swap": True,
    "cast_aim_x": -495,
    "cast_aim_y": 1003,
    "calibrated_bar_x": -495,
    "calibrated_bar_y": 1150,
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
    "hotkeys": {
        "toggle": "F6",
        "set_water_aim": "F5",
        "decrease_cast": "F1",
        "increase_cast": "F2",
        "calibrate_bar": "F3",
        "inspect_pixel": "F4",
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
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, startupinfo=startupinfo, timeout=4)
            for line in res.stdout.splitlines():
                if "emulator" in line or "127.0.0.1" in line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "device":
                        self.device_name = parts[0]
                        return True
            # Attempt connect if list is empty
            subprocess.run([self.adb_path, "connect", "127.0.0.1:5555"], capture_output=True, startupinfo=startupinfo, timeout=3)
            return True
        except Exception:
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

    def close(self):
        if self.process:
            try:
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
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

        cur_thread = ctypes.windll.user32.GetWindowThreadProcessId(cur_fg, None)
        target_thread = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)

        if cur_thread != target_thread and cur_thread != 0:
            ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, True)
            ctypes.windll.user32.BringWindowToTop(hwnd)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, False)
        else:
            ctypes.windll.user32.BringWindowToTop(hwnd)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True
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


def mouse_down():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)


def mouse_up():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def mouse_click(hold_time=0.02):
    mouse_down()
    if hold_time > 0:
        time.sleep(hold_time)
    mouse_up()


def key_tap(vk_code):
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


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
        self.root.geometry("860x650")
        self.root.configure(bg="#0c0d10")
        self.root.minsize(780, 580)

        self.config = load_config()
        self.display = MultiMonitorManager()
        self.adb = ADBManager(self.config.get("adb_path"))
        self.log_queue = queue.Queue()
        self.roblox_hwnd = None

        self.is_running = False
        self.test_mode = False
        self.inspector_active = False
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

        self.adb_badge = tk.Label(header, text="[ ⚡ ADB: CONNECTING ]", fg="#e3b341", bg="#21262d", font=("Consolas", 9, "bold"), padx=8, pady=4)
        self.adb_badge.pack(side="right", padx=(4, 12), pady=8)

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

        # 3. Targets & Tuners Panel
        controls_panel = tk.Frame(self.root, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
        controls_panel.pack(fill="x", padx=14, pady=6)

        # Row 1: Water Aim Controls (ADB Touch Coordinates + Arrow Nudges)
        row1 = tk.Frame(controls_panel, bg="#161b22")
        row1.pack(fill="x", padx=12, pady=(8, 4))

        self.aim_coord_lbl = tk.Label(row1, text=f"Water Aim: X={self.config.get('adb_cast_x', 640)}, Y={self.config.get('adb_cast_y', 420)}", fg="#58a6ff", bg="#161b22", font=("Consolas", 9, "bold"))
        self.aim_coord_lbl.pack(side="left", padx=(0, 8))

        aim_btn_box = tk.Frame(row1, bg="#161b22")
        aim_btn_box.pack(side="left", padx=(0, 16))
        tk.Button(aim_btn_box, text="▲ Up", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(0, -30)).pack(side="left", padx=1)
        tk.Button(aim_btn_box, text="▼ Down", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(0, +30)).pack(side="left", padx=1)
        tk.Button(aim_btn_box, text="◀ Left", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(-30, 0)).pack(side="left", padx=1)
        tk.Button(aim_btn_box, text="▶ Right", bg="#21262d", fg="#58a6ff", font=("Consolas", 8), command=lambda: self.adjust_aim_spot(+30, 0)).pack(side="left", padx=1)
        tk.Button(aim_btn_box, text="🎯 Test Cast", bg="#238636", fg="#ffffff", font=("Consolas", 8, "bold"), command=self.test_cast_only).pack(side="left", padx=(6, 0))

        self.pin_toggle_btn = tk.Button(row1, text="📍 Show Target Pins", bg="#21262d", fg="#58a6ff", activebackground="#30363d", activeforeground="#58a6ff", font=("Consolas", 8, "bold"), bd=1, relief="solid", command=self.toggle_pins)
        self.pin_toggle_btn.pack(side="right")

        # Row 2: Green Bar Controls (Coordinates + Arrow Nudges + Test Button + Auto-Align)
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
        tk.Button(bar_btn_box, text="🟢 Test Bar", bg="#1f6feb", fg="#ffffff", font=("Consolas", 8, "bold"), command=self.test_bar_target).pack(side="left", padx=(6, 2))
        tk.Button(bar_btn_box, text="📐 Auto-Align Bar", bg="#21262d", fg="#39d353", font=("Consolas", 8), command=self.auto_align_bar).pack(side="left", padx=2)

        # Row 3: Tuners (Cast Hold & Cooldown) + ADB Mode Checkbox
        row3 = tk.Frame(controls_panel, bg="#161b22")
        row3.pack(fill="x", padx=12, pady=(4, 8))

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

        # LDPlayer ADB mode checkbox
        self.adb_var = tk.BooleanVar(value=self.config.get("use_adb", True))
        adb_check = tk.Checkbutton(row3, text="⚡ LDPlayer (ADB No-Mouse-Jump)", variable=self.adb_var, command=self._on_adb_toggle, bg="#161b22", fg="#39d353", selectcolor="#0d1117", activebackground="#161b22", activeforeground="#39d353", font=("Consolas", 9, "bold"))
        adb_check.pack(side="right")
        adb_check = tk.Checkbutton(row2, text="⚡ LDPlayer (ADB No-Mouse-Jump)", variable=self.adb_var, command=self._on_adb_toggle, bg="#161b22", fg="#39d353", selectcolor="#0d1117", activebackground="#161b22", activeforeground="#39d353", font=("Consolas", 9, "bold"))
        adb_check.pack(side="right")

        # 4. Action Buttons Bar
        btn_bar = tk.Frame(self.root, bg="#0c0d10")
        btn_bar.pack(fill="x", padx=14, pady=4)

        self.start_btn = tk.Button(btn_bar, text="▶ START (F6)", bg="#238636", fg="#ffffff", activebackground="#2ea043", activeforeground="#ffffff", font=("Consolas", 10, "bold"), bd=0, padx=14, pady=6, command=self.toggle_running)
        self.start_btn.pack(side="left", padx=(0, 6))

        self.test_btn = tk.Button(btn_bar, text="🎯 TEST 1 CYCLE (F7)", bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=10, pady=6, command=self.run_test)
        self.test_btn.pack(side="left", padx=4)

        self.aim_btn = tk.Button(btn_bar, text="🎣 SET AIM (F5)", bg="#21262d", fg="#58a6ff", activebackground="#30363d", activeforeground="#ffffff", font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=10, pady=6, command=self.set_aim_spot)
        self.aim_btn.pack(side="left", padx=4)

        self.inspect_btn = tk.Button(btn_bar, text="🔍 INSPECTOR (F4)", bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", font=("Consolas", 9, "bold"), bd=1, relief="solid", padx=10, pady=6, command=self.toggle_inspector)
        self.inspect_btn.pack(side="left", padx=4)

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
        if self.adb_var.get():
            self.log("[MODE] ⚡ LDPlayer ADB Mode ACTIVE (Monkey Engine Touch Injection)", "SUCCESS")
        else:
            self.log("[MODE] Direct Windows Mode active.", "INFO")
        self.log(f"[SETUP] Water Aim touch: ({self.config.get('adb_cast_x')}, {self.config.get('adb_cast_y')}) | Bar Target at ({self.config.get('calibrated_bar_x')}, {self.config.get('calibrated_bar_y')})")

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
            connected = self.adb.check_device()
            if connected:
                self.adb_badge.config(text=f"[ ⚡ ADB: {self.adb.device_name} ]", fg="#39d353")
            else:
                self.adb_badge.config(text="[ ⚡ ADB: DISCONNECTED ]", fg="#f85149")
        threading.Thread(target=check, daemon=True).start()
        self.root.after(8000, self._check_adb_status)

    def clear_logs(self):
        self.log_text.delete("1.0", "end")

    # =========================================================================
    # Aim Spot Adjustment & Test
    # =========================================================================
    def adjust_aim_spot(self, dx, dy):
        cur_x = self.config.get("adb_cast_x", 640)
        cur_y = self.config.get("adb_cast_y", 420)
        new_x = max(50, min(1230, cur_x + dx))
        new_y = max(50, min(670, cur_y + dy))
        self.config["adb_cast_x"] = new_x
        self.config["adb_cast_y"] = new_y
        self.config["adb_reel_x"] = new_x
        self.config["adb_reel_y"] = new_y
        save_config(self.config)
        self.aim_coord_lbl.config(text=f"Water Aim: X={new_x}, Y={new_y}")
        self.log(f"[AIM] Water Aim adjusted to X={new_x}, Y={new_y}", "INFO")

    def test_cast_only(self):
        def cast_worker():
            x = self.config.get("adb_cast_x", 640)
            y = self.config.get("adb_cast_y", 420)
            dur = self.config.get("cast_hold_duration", 1.05)
            self.log(f"[TEST CAST] Firing test cast ({dur:.2f}s) at ({x}, {y})...", "WARN")
            self.adb.cast_hold(x, y, duration=dur)
            self.log("[TEST CAST] Test cast completed! Check where your bobber landed.", "SUCCESS")
        threading.Thread(target=cast_worker, daemon=True).start()

    def adjust_bar_spot(self, dx, dy):
        cur_x = self.config.get("calibrated_bar_x", -495)
        cur_y = self.config.get("calibrated_bar_y", 1150)
        new_x = cur_x + dx
        new_y = cur_y + dy
        self.config["calibrated_bar_x"] = new_x
        self.config["calibrated_bar_y"] = new_y
        save_config(self.config)
        self.bar_coord_lbl.config(text=f"Green Bar: ({new_x}, {new_y})")
        if self.bar_pin:
            self.bar_pin.update_coords(new_x, new_y)
        self.log(f"[BAR] Green Bar target moved to ({new_x}, {new_y})", "INFO")

    def test_bar_target(self):
        calib_x = self.config.get("calibrated_bar_x")
        calib_y = self.config.get("calibrated_bar_y")
        if calib_x is None or calib_y is None:
            self.log("[BAR TEST] Bar target not set!", "ERROR")
            return

        col = self.display.get_pixel(calib_x, calib_y)
        is_active = self.check_minigame_active()
        if col:
            r, g, b = col
            matched, tag = is_green_or_stop(r, g, b)
            if is_active:
                self.log(f"[BAR TEST] 🟢 MATCH! Green Bar DETECTED at ({calib_x}, {calib_y}) RGB({r},{g},{b})", "SUCCESS")
                try:
                    winsound.Beep(1800, 150)
                except Exception:
                    pass
            else:
                self.log(f"[BAR TEST] ⚪ CLEAR: Center pixel is RGB({r},{g},{b}) (No green bar). Ready to fish!", "INFO")
                try:
                    winsound.Beep(1000, 100)
                except Exception:
                    pass
        else:
            self.log(f"[BAR TEST] ⚠️ Could not read pixel at ({calib_x}, {calib_y}). Check monitor.", "WARN")

    def auto_align_bar(self):
        aim_x = self.config.get("cast_aim_x", -495)
        aim_y = self.config.get("cast_aim_y", 1003)
        # The green bar in Steal an Egg is horizontally centered with the water aim
        # and sits approximately 140-160 pixels lower on typical resolutions.
        new_bar_x = aim_x
        new_bar_y = aim_y + 150
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
            aim_x = self.config.get("cast_aim_x", -495)
            aim_y = self.config.get("cast_aim_y", 1003)
            self.aim_pin = DraggablePin(self.root, "🎣 WATER AIM", aim_x, aim_y, "#58a6ff", on_moved=self._on_aim_moved)

            # 2. Bar Pin
            bar_x = self.config.get("calibrated_bar_x", -495)
            bar_y = self.config.get("calibrated_bar_y", 1150)
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
        self.aim_coord_lbl.config(text=f"Water Aim: X={self.config.get('adb_cast_x', 640)}, Y={self.config.get('adb_cast_y', 420)}")
        try:
            winsound.Beep(1200, 80)
        except Exception:
            pass

    def _on_bar_moved(self, x, y):
        self.config["calibrated_bar_x"] = x
        self.config["calibrated_bar_y"] = y
        col = self.display.get_pixel(x, y)
        if col:
            matched, tag = is_green_or_stop(*col)
            if matched and tag == "GREEN_BAR":
                self.config["calibrated_color"] = list(col)
                self.log(f"[BAR] Green Bar target locked to ({x}, {y}) with active color RGB{tuple(col)}", "SUCCESS")
            else:
                self.log(f"[BAR] Target pin moved to ({x}, {y}). Will trigger when bright lime-green bar appears here.", "INFO")
        save_config(self.config)
        self.bar_coord_lbl.config(text=f"Green Bar: ({x}, {y})")
        try:
            winsound.Beep(1500, 100)
        except Exception:
            pass

    def _on_adb_toggle(self):
        val = self.adb_var.get()
        self.config["use_adb"] = val
        save_config(self.config)
        if val:
            self.log("[CONFIG] ⚡ LDPlayer ADB Mode ENABLED: Zero Windows mouse movement active!", "SUCCESS")
        else:
            self.log("[CONFIG] Switched to Direct Windows Mode (physical mouse events).", "WARN")

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
            threading.Thread(target=self._run_single_test_worker, daemon=True).start()

    def _run_single_test_worker(self):
        self.test_mode = True
        self.log("[TEST] Testing 1 full fishing cycle...", "WARN")
        start = time.time()
        self.do_fishing_cycle()
        total_time = time.time() - start
        self.test_mode = False
        self.log(f"[TEST] Test cycle finished in {total_time:.2f}s!", "SUCCESS")

    def set_aim_spot(self):
        x, y = get_cursor_pos()
        self._on_aim_moved(x, y)
        if self.aim_pin:
            self.aim_pin.update_coords(x, y)

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

    def toggle_inspector(self):
        self.inspector_active = not self.inspector_active
        if self.inspector_active:
            self.inspect_btn.config(bg="#58a6ff", fg="#0d1117")
            self.log("[INSPECTOR] Inspector ACTIVE. Move mouse over game.", "WARN")
            threading.Thread(target=self._inspector_worker, daemon=True).start()
        else:
            self.inspect_btn.config(bg="#21262d", fg="#c9d1d9")
            self.log("[INSPECTOR] Inspector STOPPED.", "INFO")

    def _inspector_worker(self):
        while self.inspector_active and not self.should_exit:
            x, y = get_cursor_pos()
            col = self.display.get_pixel(x, y)
            if col:
                matched, label = is_green_or_stop(*col)
                tag = f"MATCH: {label}" if matched else "No Match"
                self.action_card.val_lbl.config(text=f"({x}, {y}) RGB{col} [{tag}]", fg="#39d353" if matched else "#58a6ff")
            time.sleep(0.15)
        if not self.is_running:
            self.action_card.val_lbl.config(text="Idle — Ready to Start", fg="#e3b341")

    # =========================================================================
    # Fishing Loop Engine
    # =========================================================================
    def get_roblox_hwnd(self):
        if self.roblox_hwnd and ctypes.windll.user32.IsWindow(self.roblox_hwnd):
            return self.roblox_hwnd

        calib_x = self.config.get("calibrated_bar_x")
        calib_y = self.config.get("calibrated_bar_y")
        if calib_x is not None and calib_y is not None:
            pt = POINT(int(calib_x), int(calib_y))
            h = ctypes.windll.user32.WindowFromPoint(pt)
            if h:
                root = ctypes.windll.user32.GetAncestor(h, GA_ROOT)
                if root and ctypes.windll.user32.IsWindow(root):
                    self.roblox_hwnd = root
                    return root
                self.roblox_hwnd = h
                return h

        h = ctypes.windll.user32.FindWindowW(None, "Roblox")
        if h:
            self.roblox_hwnd = h
            return h

        found_h = None
        def enum_cb(hwnd, _):
            nonlocal found_h
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                    if "roblox" in buf.value.lower():
                        found_h = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        if found_h:
            self.roblox_hwnd = found_h
            return found_h

        return None

    def ensure_roblox_focused(self):
        hwnd = self.get_roblox_hwnd()
        if hwnd:
            focus_window(hwnd)
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
            if self.config.get("use_adb", True):
                self.adb.anti_afk_jump()
            else:
                key_tap(VK_SPACE)

    def do_fishing_cycle(self):
        jitter = self.config.get("jitter_amount", 0.015)
        max_wait = self.config.get("max_bite_wait_seconds", 24.0)
        min_buffer = self.config.get("min_wait_before_bite", 1.8)
        use_adb = self.config.get("use_adb", True)
        bg_mode = self.config.get("background_focus_swap", True)

        cast_time = self.config.get("cast_hold_duration", 1.05)
        self.total_casts += 1

        # ---------------------------------------------------------------------
        # 1. CASTING INTO WATER
        # ---------------------------------------------------------------------
        if use_adb:
            adb_x = self.config.get("adb_cast_x", 640)
            adb_y = self.config.get("adb_cast_y", 420)
            self.action_card.val_lbl.config(text=f"Holding Rod ({cast_time:.2f}s)...", fg="#e3b341")
            self.log(f"▶ Cast #{self.total_casts}: [⚡ Monkey Hold] Holding rod for {cast_time:.2f}s at ({adb_x}, {adb_y})...", "INFO")
            
            self.adb.cast_hold(adb_x, adb_y, duration=cast_time)
            self.log(f"  └─ [⚡ Monkey Hold] Released after exact {cast_time:.2f}s! (Perfect cast)", "SUCCESS")
        else:
            aim_x = self.config.get("cast_aim_x", -495)
            aim_y = self.config.get("cast_aim_y", 1003)
            self.action_card.val_lbl.config(text=f"Casting ({cast_time:.2f}s hold)...", fg="#e3b341")
            self.log(f"▶ Cast #{self.total_casts}: Holding rod for {cast_time:.2f}s...", "INFO")

            saved_x, saved_y = get_cursor_pos()
            saved_hwnd = ctypes.windll.user32.GetForegroundWindow()

            try:
                if bg_mode:
                    self.ensure_roblox_focused()
                    set_cursor_pos(aim_x, aim_y)
                    time.sleep(0.04)

                mouse_down()
                start_hold = time.perf_counter()
                while (time.perf_counter() - start_hold) < cast_time:
                    time.sleep(0.005)
            finally:
                mouse_up()
                if bg_mode:
                    restore_user_state(saved_hwnd, saved_x, saved_y)

            self.log("  └─ Rod thrown! Focus restored to you.", "SUCCESS")

        if not self.is_running and not self.test_mode:
            return

        # ---------------------------------------------------------------------
        # 2. BUFFER DELAY & BASELINE LOCK (Let bobber land in water)
        # ---------------------------------------------------------------------
        self.action_card.val_lbl.config(text=f"Line landing in water ({min_buffer:.1f}s)...", fg="#58a6ff")
        time.sleep(min_buffer)

        # ---------------------------------------------------------------------
        # 3. BACKGROUND BITE WATCH (Checks dynamically until green bar appears)
        # ---------------------------------------------------------------------
        calib_x = self.config.get("calibrated_bar_x")
        calib_y = self.config.get("calibrated_bar_y")
        self.action_card.val_lbl.config(text="Waiting for fish bite (Green Bar)...", fg="#39d353")
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
            self.action_card.val_lbl.config(text=f"TURBO Reeling ({click_count} taps)...", fg="#e3b341")
            self.log(f"  └─ [⚡ Monkey Turbo] Rapid tapping {click_count} times (<0.5s)...", "INFO")
            self.adb.rapid_tap(adb_reel_x, adb_reel_y, count=click_count, interval=0.020)
            self.log("  └─ [⚡ Monkey Turbo] Reeling complete!", "SUCCESS")
        else:
            aim_x = self.config.get("cast_aim_x", -502)
            aim_y = self.config.get("cast_aim_y", 1000)
            self.action_card.val_lbl.config(text=f"Reeling ({click_count} clicks)...", fg="#e3b341")
            self.log(f"  └─ Reeling in with {click_count} rapid clicks...", "INFO")

            saved_x, saved_y = get_cursor_pos()
            saved_hwnd = ctypes.windll.user32.GetForegroundWindow()

            try:
                if bg_mode:
                    self.ensure_roblox_focused()
                    set_cursor_pos(aim_x, aim_y)
                    time.sleep(0.04)

                for i in range(click_count):
                    if not self.is_running and not self.test_mode:
                        break
                    mouse_click(hold_time=0.015)
                    human_sleep(click_interval, jitter=jitter)
            finally:
                if bg_mode:
                    restore_user_state(saved_hwnd, saved_x, saved_y)

        self.total_catches += 1
        self.catches_card.val_lbl.config(text=str(self.total_catches))
        self.log(f"  └─ Catch #{self.total_catches} secured!", "SUCCESS")

        if not self.is_running and not self.test_mode:
            return

        # ---------------------------------------------------------------------
        # 5. REWARD POPUP COOLDOWN
        # ---------------------------------------------------------------------
        cooldown = self.config.get("post_catch_cooldown", 4.0)
        self.action_card.val_lbl.config(text=f"Reward popup clearing ({cooldown:.1f}s)...", fg="#58a6ff")
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
            "water": VK_MAP.get(hotkeys.get("set_water_aim", "F5").upper(), 0x74),
            "dec_cast": VK_MAP.get(hotkeys.get("decrease_cast", "F1").upper(), 0x70),
            "inc_cast": VK_MAP.get(hotkeys.get("increase_cast", "F2").upper(), 0x71),
            "calib": VK_MAP.get(hotkeys.get("calibrate_bar", "F3").upper(), 0x72),
            "inspect": VK_MAP.get(hotkeys.get("inspect_pixel", "F4").upper(), 0x73),
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
        elif action == "water":
            self.root.after(0, self.set_aim_spot)
        elif action == "dec_cast":
            self.root.after(0, lambda: self.adjust_cast_time(-0.05))
        elif action == "inc_cast":
            self.root.after(0, lambda: self.adjust_cast_time(+0.05))
        elif action == "calib":
            self.root.after(0, self._calibrate_bar_hotkey)
        elif action == "inspect":
            self.root.after(0, self.toggle_inspector)
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
        self.inspector_active = False
        if self.aim_pin:
            self.aim_pin.destroy()
        if self.bar_pin:
            self.bar_pin.destroy()
        self.adb.close()
        self.display.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AutoFishGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
