# 🎣 Roblox: Steal an Egg — Auto-Fishing Automation Suite

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?style=flat-square&logo=windows)](https://github.com)
[![Roblox](https://img.shields.io/badge/Game-Roblox%3A%20Steal%20an%20Egg-red?style=flat-square&logo=roblox)](https://www.roblox.com)
[![Engine](https://img.shields.io/badge/Android%20Engine-LDPlayer%209%20%2B%20Monkey-orange?style=flat-square&logo=android)](https://www.ldplayer.net)

An advanced, ban-safe auto-fishing automation suite for **Roblox: Steal an Egg**. Features millisecond-precise casting holds, high-speed turbo reeling minigame taps, dynamic baseline-locked color detection for variable bite delays, and **100% true background automation** with **ZERO Windows mouse movement and ZERO focus stealing**.

---

## 📑 Table of Contents

- [Quick Comparison Matrix](#-quick-comparison-matrix)
- [📦 Version 1: Windows Client CLI / Focus-Swap Macro](#-version-1-windows-client-cli--focus-swap-macro)
- [🎨 Version 2: Multi-Monitor Dark GUI Dashboard with Draggable Pins](#-version-2-multi-monitor-dark-gui-dashboard-with-draggable-pins)
- [🛡️ Version 3: Windows Sandbox Virtual Environment (`.wsb`)](#️-version-3-windows-sandbox-virtual-environment-wsb)
- [⚡ Version 4: LDPlayer 9 + ADB Monkey Engine (Recommended)](#-version-4-ldplayer-9--adb-monkey-engine-recommended)
- [📁 Project File Structure](#-project-file-structure)

---

## 📊 Quick Comparison Matrix

| Feature | V1: CLI Focus-Swap | V2: GUI Dashboard | V3: Windows Sandbox | V4: LDPlayer 9 + ADB (Latest) |
|---|---|---|---|---|
| **User Interface** | Terminal / CLI | Dark CMD-Style GUI | Dark GUI in Sandbox | Dark CMD-Style GUI |
| **Mouse Cursor Jumps?** | Yes (Micro-swap) | Yes (Micro-swap) | No (Sandboxed cursor) | **NO (0% physical movement)** |
| **Steals Window Focus?** | Yes (For ~0.8s) | Yes (For ~0.8s) | No (Sandboxed window) | **NO (100% background)** |
| **Targeting Method** | Coordinate Hotkeys | Draggable Pins | Draggable Pins | **Auto-Mapped Touch + Pins** |
| **Bite Wait Handling** | Fixed delay | Color check | Multi-monitor color | **Dynamic Baseline Delta Lock** |
| **Random Bite Delays (3-12s)** | Prone to timeout | Prone to false bite | Moderate | **100% Perfect Detection** |
| **Reeling Tap Speed** | ~0.8s (Win32) | ~0.8s (Win32) | ~0.8s (Win32) | **<0.45s (Monkey Hardware Tap)** |
| **Roblox Platform** | Windows PC Client | Windows PC Client | Windows PC Client | **Android App (LDPlayer 9)** |

---

## 📦 Version 1: Windows Client CLI / Focus-Swap Macro

### Overview
The original lightweight script designed for the native Roblox Windows desktop client. It employs a **focus-swap micro-borrowing mechanism**: while waiting for a bite (3–12s) and during reward popups (4s), focus remains on your active window. When casting (1.05s) or reeling (~0.8s), it saves your cursor position and active window, focuses Roblox, performs the action, and instantly restores your cursor and window focus.

### Hardware Requirements
- **CPU:** Any dual-core x86/x64 processor (Intel Core i3 / AMD Ryzen 3 or equivalent).
- **RAM:** Minimum 4 GB RAM.
- **Display:** Single or multiple monitors (1080p recommended).

### Software Requirements & Dependencies
- **OS:** Windows 10 or Windows 11 (64-bit).
- **Runtime:** Python 3.10+ (if running source).
- **Roblox:** Official Roblox Windows Player desktop app.
- **Dependencies:** Built-in Python standard libraries (`ctypes`, `json`, `winsound`, `time`, `threading`).

### Configuration & Settings (`config.json`)
```json
{
  "use_adb": false,
  "background_focus_swap": true,
  "cast_aim_x": 960,
  "cast_aim_y": 540,
  "calibrated_bar_x": 960,
  "calibrated_bar_y": 780,
  "cast_hold_duration": 1.05,
  "min_wait_before_bite": 1.8,
  "reeling_clicks": 16,
  "click_interval": 0.02,
  "post_catch_cooldown": 4.0,
  "max_bite_wait_seconds": 24.0,
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
```

### Setup & Usage
1. Open the Roblox Windows client and join **Steal an Egg**.
2. Equip your fishing rod and stand at the pond dock.
3. Click **`[ 📍 Show Target Pins ]`** to place the Cyan Water Aim pin on the pond and Green Bar pin over the minigame area.
4. Press **`F7`** to test 1 cycle, or **`F6`** to start auto-fishing. Press **`F6`** again to pause.

---

## 🎨 Version 2: Multi-Monitor Dark GUI Dashboard with Draggable Pins

### Overview
Introduced a standalone **CMD-style dark graphical dashboard** and **floating topmost draggable target pins**. Designed for multi-monitor desktop setups, allowing you to browse YouTube or work on your primary display while Roblox runs on a secondary display.

### Hardware Requirements
- **CPU:** Quad-core processor (Intel Core i5 / AMD Ryzen 5).
- **RAM:** 8 GB RAM recommended for multi-monitor multitasking.
- **Display:** Dual or triple monitor setup (tested across negative and multi-DPI monitor coordinate spaces).

### Software Requirements & Dependencies
- **OS:** Windows 10 or Windows 11 (64-bit).
- **Python Libraries (if running from source):**
  ```bash
  pip install mss
  ```
- **Roblox:** Roblox Windows desktop app.

### Key Features & Controls
- **Automatic Screen & Roblox Window Detection:** Automatically identifies which physical monitor Roblox is placed on (including secondary portrait monitors like `1024x1280` with negative desktop coordinates) and updates the active screen badge with resolution and orientation.
- **Manual Screen & Preset Selector:** Dropdown menu allowing you to choose between Auto-Detect, any detected physical monitor (`DISPLAY1`, `DISPLAY2`), or common resolution presets (`1024x1280 Portrait`, `1080x1920 Portrait Full HD`, `1920x1080 Landscape Full HD`, `1366x768 HD`, `2560x1440 2K`).
- **One-Click Pin Centering (`[ 📍 Center Pins to Screen ]`):** Automatically positions the water aim (32% height) and green bar (91% height) to perfect game proportions for the selected display.
- **Normalized Virtual Desktop Input:** Uses Win32 Virtual Desktop coordinate normalization (`MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_ABSOLUTE`) with viewport activation taps so casting and reeling 100% reliably trigger on secondary/portrait screens.
- **Floating Visual Target Pins & Auto-Align:**
  - `[ 📍 Show Target Pins ]`: Displays floating Cyan (Water Aim) and Green (Minigame Bar) pins.
  - `[ 📐 Auto-Align Bar ]`: Placed directly below the Show Target Pins button to instantly align the bar target below the pond.
- **Built-in Quick Guide Window (`[ 📖 HOW TO USE ]`):** One-click in-app reference window detailing mode selection, screen setup, pin placement, testing, and shortcuts.
- **Dashboard Cards:** Live counters for Total Catches, Session Uptime, and Current Action status.
- **Live Terminal:** Real-time color-coded logging of casts, bite detection latencies, and catches.
- **Tuners:** On-screen `[-] / [+]` buttons to adjust Cast Hold (±0.05s) and Popup Wait (±0.5s).

---

## 🛡️ Version 3: Windows Sandbox Virtual Environment (`.wsb`)

### Overview
Runs both Roblox and the auto-fisher inside **Windows Sandbox** via [Roblox_AutoFish_Sandbox.wsb](file:///f:/Documents/Coding/Scipts/Roblox_AutoFish_Sandbox.wsb). Because Windows Sandbox provides a completely isolated disposable desktop session with its **own dedicated virtual mouse cursor**, the macro can click, drag, and hold with 100% physical interaction inside the sandbox without **EVER** stealing focus or moving the host desktop cursor.

### Hardware Requirements
- **CPU:** 64-bit CPU with **Hardware Virtualization (Intel VT-x / AMD-V)** enabled in BIOS.
- **RAM:** Minimum 8 GB RAM (at least 4 GB available for the sandbox).
- **GPU:** Dedicated GPU supporting DirectX 11+ with WDDM 2.5+ drivers for vGPU hardware acceleration.
- **Disk:** At least 5 GB free space on host drive.

### Software Requirements & Prerequisites
- **OS:** Windows 10 Pro / Enterprise / Education or Windows 11 Pro / Enterprise (Build 18305+).
- **Windows Feature:** `Windows Sandbox` must be enabled:
  1. Press `Win + R`, type `optionalfeatures`, and press Enter.
  2. Check **Windows Sandbox** and click **OK**.
  3. Restart your computer.

### Sandbox Configuration File (`Roblox_AutoFish_Sandbox.wsb`)
```xml
<Configuration>
  <VGpu>Enable</VGpu>
  <Networking>Default</Networking>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>F:\Documents\Coding\Scipts</HostFolder>
      <SandboxFolder>C:\Users\WDAGUtilityAccount\Desktop\Scripts</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>explorer.exe C:\Users\WDAGUtilityAccount\Desktop\Scripts</Command>
  </LogonCommand>
</Configuration>
```

### Setup & Usage
1. Double-click [Roblox_AutoFish_Sandbox.wsb](file:///f:/Documents/Coding/Scipts/Roblox_AutoFish_Sandbox.wsb).
2. Inside the fresh sandbox desktop, open Edge, install Roblox Player, and log in.
3. Open the mapped `Scripts` folder on the sandbox desktop.
4. Run `StealAnEgg_AutoFish.exe` inside the sandbox, place your pins, and press **`F6`**.
5. Switch freely back to your host desktop — browse, game, or type without interference.

---

## ⚡ Version 4: LDPlayer 9 + ADB Monkey Engine (Recommended)

### Overview
The ultimate, production-grade automation setup. Runs Roblox inside **LDPlayer 9** (Android 9 x86_64) using the **Android Monkey Engine** over ADB. This achieves **100% true background automation**:
1. **Zero Mouse Movement:** Never moves the physical Windows mouse cursor.
2. **Zero Focus Stealing:** Does not require focusing or activating the LDPlayer window.
3. **Exact Cast Duration:** Injects native `MotionEvent` down/wait/up events via Monkey with exact millisecond hold timing (`1.05s`).
4. **Turbo Reeling Speed:** Fires 16 discrete taps in **0.45 seconds** with zero per-tap process spawning lag.
5. **Dynamic Baseline Color Lock:** Takes a baseline color snapshot right as the bobber lands; triggers **ONLY** when pixels dynamically change (`diff > 35`) into the lime-green bar or red STOP button. Static grass, buttons, and desktop wallpaper are 100% ignored!
6. **Handles Random Bite Delays:** Continuously polls at 50 Hz through any random bite delay (2s to 12s+) without timing out or prematurely reeling.

### Hardware Requirements
- **CPU:** Intel or AMD CPU with Virtualization (VT-x / AMD-V) enabled.
- **RAM:** Minimum 8 GB RAM (allocate 2–4 GB to LDPlayer).
- **GPU:** Dedicated GPU or modern integrated graphics supporting OpenGL 4.0+.
- **Disk:** 3 GB free disk space for LDPlayer 9 and Roblox app.

### Software Requirements & Prerequisites
- **OS:** Windows 10 or Windows 11 (Home, Pro, or Enterprise).
- **Emulator:** **[LDPlayer 9](https://www.ldplayer.net/)** (64-bit Android 9 kernel).
  - Recommended emulator resolution: **1280x720 (DPI: 240)**.
- **ADB:** Included automatically inside LDPlayer at `E:\LDPlayer\LDPlayer9\adb.exe` (or `C:\LDPlayer\LDPlayer9\adb.exe`).
- **Roblox:** Roblox Mobile App installed inside LDPlayer from Google Play Store or APK.
- **No Python Required:** If using [StealAnEgg_AutoFish.exe](file:///f:/Documents/Coding/Scipts/StealAnEgg_AutoFish.exe).

### Optimized Configuration (`config.json`)
```json
{
  "use_adb": true,
  "adb_path": "E:\\LDPlayer\\LDPlayer9\\adb.exe",
  "adb_cast_x": 640,
  "adb_cast_y": 420,
  "adb_reel_x": 640,
  "adb_reel_y": 420,
  "background_focus_swap": true,
  "cast_aim_x": -495,
  "cast_aim_y": 1003,
  "calibrated_bar_x": -495,
  "calibrated_bar_y": 1150,
  "calibrated_color": [159, 204, 116],
  "cast_hold_duration": 1.05,
  "min_wait_before_bite": 1.8,
  "reeling_clicks": 16,
  "click_interval": 0.02,
  "post_catch_cooldown": 4.0,
  "max_bite_wait_seconds": 24.0,
  "color_tolerance": 55,
  "jitter_amount": 0.015,
  "anti_afk_enabled": true,
  "anti_afk_interval_seconds": 120
}
```

### Step-by-Step Setup
1. **Launch LDPlayer 9 & Roblox:**
   - Open LDPlayer 9.
   - Launch Roblox and enter **Steal an Egg**.
   - Walk your character to the wooden bridge at the purple pond and hold your fishing rod.
2. **Launch the Macro:**
   - Double-click **[StealAnEgg_AutoFish.exe](file:///f:/Documents/Coding/Scipts/StealAnEgg_AutoFish.exe)** (or run `start.bat`).
   - The top badge will show `[ ⚡ ADB: emulator-5554 ]` in green once connected.
3. **Place Pins & Test 1 Cycle:**
   - Click **`[ 📍 Show Target Pins ]`** (or **`[ 📍 Center Pins to Screen ]`**) to position your targets.
   - Click **`[ 🎯 TEST 1 CYCLE (F7) ]`**: Automatically hides pins and executes a single full cycle (cast hold -> bite watch -> rapid reeling) to verify your setup before starting continuous fishing.
4. **Start Auto-Fishing:**
   - Press **`F6`** (or click **`▶ START`**).
   - Target pins auto-hide.
   - The bot casts with exact 1.05s hold timing, waits for the bobber to settle (1.8s), and dynamically waits through the variable bite delay (3–10s+).
   - The instant the green minigame bar appears, 16 turbo taps fire in <0.45s, securing the catch!

---

## 📁 Project File Structure

Following cleanup, this repository contains only the essential, clean files:

```
F:\Documents\Coding\Scipts\
│
├── StealAnEgg_AutoFish.exe     # Standalone compiled Windows binary (13.7 MB)
├── gui_autofish.py             # Main GUI dashboard & ADB Monkey fishing engine source
├── start.bat                   # 1-click launcher batch script (launches py or exe)
├── Roblox_AutoFish_Sandbox.wsb # Windows Sandbox isolated configuration file
├── config.json                 # Auto-saved user targeting & timing settings
├── README.md                   # Comprehensive 4-version documentation & guide
└── .gitignore                  # Git ignore rules for build artifacts & temp files
```

---

## ⚖️ Disclaimer

This software is developed strictly for educational and automation testing purposes. Use responsibly in accordance with Roblox Terms of Service.
