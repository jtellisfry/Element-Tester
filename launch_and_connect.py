"""
Auto-launch UT61E+ and Click CONNECT (Optimized Order)
=======================================================
Move mouse FIRST, then launch, then click!
"""

import subprocess
import time
import pyautogui
import pygetwindow as gw
from pathlib import Path
import datetime, os, sys

# Logging setup
LOG = Path(r"C:\Files\element tester\Element_Tester\launch_and_connect_internal.log")
LOG.parent.mkdir(parents=True, exist_ok=True)
def log(msg: str):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()} | {msg}\n")

log("=== Script started ===")
log(f"Python: {sys.executable}")
log(f"CWD: {os.getcwd()}")

# Possible UT61E+ executable locations
UT61E_PATHS = [
    Path(r"C:\Users\fryassytest\Desktop\UT61xP - Shortcut.lnk"),
    Path(r"C:\Users\fryassytest\App\UT61E+\UT61xP.exe")
]

# CONNECT button coordinates (relative to window top-left)
# CONNECT_X = 180
# CONNECT_Y = 80
CONNECT_X = 50
CONNECT_Y = 50



log("="*70)
log("AUTO-LAUNCH UT61E+ AND CONNECT")
log("="*70)

log("\n1. Searching for UT61E+ executable...")
UT61E_EXE = None
for path in UT61E_PATHS:
    if path.exists():
        UT61E_EXE = path
        log(f"   ✓ Found: {UT61E_EXE}")
        break

if not UT61E_EXE:
    log("   ❌ ERROR: UT61E+ executable not found!")
    exit(1)

# Step 2: Launch software FIRST (no mouse positioning yet)
log(f"\n2. Launching UT61E+ software...")
try:
    process = subprocess.Popen([str(UT61E_EXE)], shell=True)
    log("   ✓ Software launched")
except Exception as e:
    log(f"   ❌ ERROR: {e}")
    exit(1)

# Step 3: Wait for window to appear
log("\n3. Waiting for window to load...")
time.sleep(12)

# Try to find the UT61E+ window
log("   Searching for window...")
windows = []
for title in ['UT61E+', 'UT61xP', 'Uni-T UT61E+', 'UT61E Plus']:
    windows = gw.getWindowsWithTitle(title)
    if windows:
        break

if not windows:
    # Try partial match
    all_windows = gw.getAllWindows()
    for w in all_windows:
        if 'UT61' in w.title or 'Uni-T' in w.title:
            windows = [w]
            break

if not windows:
    log("   ❌ ERROR: UT61E+ window not found!")
    log("   Available windows:")
    for w in gw.getAllWindows()[:10]:  # Show first 10
        log(f"     - {w.title}")
    exit(1)

window = windows[0]
log(f"   ✓ Window found: '{window.title}' at ({window.left}, {window.top})")

# Step 4: Click CONNECT button relative to window
log(f"\n4. Clicking CONNECT button at relative position ({CONNECT_X}, {CONNECT_Y})...")
click_x = window.left + CONNECT_X
click_y = window.top + CONNECT_Y
log(f"   Window position: left={window.left}, top={window.top}, width={window.width}, height={window.height}")
log(f"   Calculated click position: ({click_x}, {click_y})")
log(f"   Current mouse position before move: {pyautogui.position()}")

# Activate the window
window.activate()
time.sleep(0.5)

# Move mouse to position (with duration to see it)
pyautogui.moveTo(click_x, click_y, duration=1.0)
log(f"   Mouse moved to: {pyautogui.position()}")

# Click
pyautogui.click()
log("   ✓ Clicked!")

# Step 5: Wait for connection
log("\n5. Waiting for meter connection...")
time.sleep(3)
log("   ✓ Connected")

# Step 6: Minimize window
log("\n6. Minimizing UT61E+ window...")
window.minimize()
log("   ✓ Minimized")

log("\n" + "="*70)
log("✅ UT61E+ RUNNING AND CONNECTED (MINIMIZED)")
log("="*70)
log("Software is running in background. Ready for HID reader.")
log("\nPress Enter to close software, or Ctrl+C to leave running...")


# No pause or prompt; script will just finish and leave UT61E+ running
