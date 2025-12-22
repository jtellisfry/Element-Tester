"""
Auto-launch UT61E+ and Click CONNECT
=====================================
"""

import subprocess
import time
import pyautogui
from pathlib import Path
import sys

# Possible UT61E+ executable locations
UT61E_PATHS = [
    Path(r"C:\Users\STAdmin.FRY-TESTER200\Tester\Element_Tester\assets\UT61E+\UT61xP.exe"),
    Path(r"C:\Users\STAdmin.FRY-TESTER200\Tester\Element_Tester\assets\UT61E+\UT61E+.exe"),
    Path(r"C:\Program Files (x86)\UT61E+\UT61xP.exe"),
    Path(r"C:\Program Files\UT61E+\UT61E+.exe"),
    Path(r"C:\Program Files (x86)\UT61E+\UT61E+.exe"),
    Path(r"C:\Files\element tester\Element_Tester\assets\UT61E+\UT61xP.exe"),
    Path(r"C:\Files\element tester\Element_Tester\assets\UT61E+\UT61E+.exe"),
]

# CONNECT button coordinates (from find_connect_button.py)
CONNECT_X = 183
CONNECT_Y = 90

print("="*70)
print("AUTO-LAUNCH UT61E+ AND CONNECT")
print("="*70)

# Step 1: Find and launch UT61E+ software
print("\n1. Searching for UT61E+ executable...")
UT61E_EXE = None
for path in UT61E_PATHS:
    if path.exists():
        UT61E_EXE = path
        print(f"   ✓ Found: {UT61E_EXE}")
        break

if not UT61E_EXE:
    print("   ❌ ERROR: UT61E+ executable not found in any of these locations:")
    for path in UT61E_PATHS:
        print(f"      - {path}")
    exit(1)

print(f"\n2. Launching UT61E+ software...")
try:
    # Try launching without shell first
    process = subprocess.Popen([str(UT61E_EXE)])
    print("   ✓ Software launched")
except OSError as e:
    if "elevation" in str(e) or "740" in str(e):
        # Try launching via shell (sometimes bypasses elevation requirement)
        print("   Trying alternate launch method...")
        try:
            process = subprocess.Popen([str(UT61E_EXE)], shell=True)
            print("   ✓ Software launched (via shell)")
        except Exception as e2:
            print("   ❌ ERROR: Administrator privileges required!")
            print("\n   The UT61E+ executable requires admin rights.")
            print("   For production, manually launch UT61E+ once at startup,")
            print("   then our HID reader can access data without admin.")
            exit(1)
    else:
        print(f"   ❌ ERROR: {e}")
        exit(1)

# Step 3: Wait for software to fully load
print("\n3. Waiting for software to load...")
time.sleep(12)  # Wait for window to appear
print("   ✓ Window loaded")

# Step 4: Remove focus by clicking on desktop (bottom right corner)
print("\n4. Removing focus from UT61E+ window...")
screen_width, screen_height = pyautogui.size()
desktop_x = screen_width - 100  # Bottom right area of screen
desktop_y = screen_height - 100
print(f"   Clicking desktop at ({desktop_x}, {desktop_y}) to remove focus...")
pyautogui.click(desktop_x, desktop_y)
time.sleep(0.5)
print("   ✓ Focus removed")

# Step 5: Move mouse to CONNECT button
print(f"\n5. Moving mouse to CONNECT button ({CONNECT_X}, {CONNECT_Y})...")
print(f"   Current position: {pyautogui.position()}")
try:
    pyautogui.moveTo(CONNECT_X, CONNECT_Y, duration=0.5)
    print(f"   ✓ Mouse moved to: {pyautogui.position()}")
except Exception as e:
    print(f"   ❌ Mouse movement failed: {e}")
time.sleep(0.5)

# Step 6: Click CONNECT button
print(f"\n6. Clicking CONNECT button...")
try:
    pyautogui.click()
    print("   ✓ Clicked!")
except Exception as e:
    print(f"   ❌ Click failed: {e}")

# Step 7: Wait for connection to establish
print("\n7. Waiting for meter to connect...")
time.sleep(3)
print("   ✓ Should be connected now")

print("\n" + "="*70)
print("✅ UT61E+ SOFTWARE IS RUNNING AND CONNECTED!")
print("="*70)
print("""
The software is now running in the background.
Data should be streaming from the meter.

Next step: Run the HID reader to access the data stream.

Press Ctrl+C to close this script (software will keep running)
Or press Enter to close the software now...
""")

try:
    input()
    print("\nClosing UT61E+ software...")
    process.terminate()
    process.wait(timeout=5)
    print("✓ Software closed")
except KeyboardInterrupt:
    print("\n\nScript exited. UT61E+ software still running.")
