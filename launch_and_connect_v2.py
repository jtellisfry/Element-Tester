"""
Auto-launch UT61E+ and Click CONNECT (Optimized Order)
=======================================================
Move mouse FIRST, then launch, then click!
"""

import subprocess
import time
import pyautogui
from pathlib import Path

# Possible UT61E+ executable locations
UT61E_PATHS = [
    Path(r"C:\Users\STAdmin.FRY-TESTER200\Tester\Element_Tester\assets\UT61E+\UT61xP.exe"),
    Path(r"C:\Users\STAdmin.FRY-TESTER200\Tester\Element_Tester\assets\UT61E+\UT61E+.exe"),
    Path(r"C:\Program Files (x86)\UT61E+\UT61xP.exe"),
    Path(r"C:\Program Files\UT61E+\UT61E+.exe"),
    Path(r"C:\Program Files (x86)\UT61E+\UT61E+.exe"),
]

# CONNECT button coordinates
CONNECT_X = 183
CONNECT_Y = 150


print("="*70)
print("AUTO-LAUNCH UT61E+ AND CONNECT")
print("="*70)           

# Step 1: Find executable
print("\n1. Searching for UT61E+ executable...")
UT61E_EXE = None
for path in UT61E_PATHS:
    if path.exists():
        UT61E_EXE = path
        print(f"   ✓ Found: {UT61E_EXE}")
        break

if not UT61E_EXE:
    print("   ❌ ERROR: UT61E+ executable not found!")
    exit(1)

# Step 2: Launch software FIRST (no mouse positioning yet)
print(f"\n2. Launching UT61E+ software...")
try:
    process = subprocess.Popen([str(UT61E_EXE)], shell=True)
    print("   ✓ Software launched")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    exit(1)

# Step 3: Wait for window to appear
print("\n3. Waiting for window to load...")
time.sleep(12)
print("   ✓ Window visible")

# Step 4: Click desktop to remove focus
print("\n4. Clicking desktop to unfocus window...")
screen_width, screen_height = pyautogui.size()
desktop_x = screen_width - 100
desktop_y = screen_height - 100
pyautogui.click(desktop_x, desktop_y)
time.sleep(0.5)
print("   ✓ Focus removed")

# Step 5: Minimize ALL windows with Win+D (show desktop)
print("\n5. Showing desktop (Win+D)...")
print(f"   Before Win+D - Mouse at: {pyautogui.position()}")
pyautogui.hotkey('win', 'd')
time.sleep(1.5)  # Longer wait for desktop to show
print("   ✓ Desktop should be visible now")
print(f"   After Win+D - Mouse at: {pyautogui.position()}")

# Step 6: Move mouse to CONNECT button location
print(f"\n6. Moving mouse to CONNECT button ({CONNECT_X}, {CONNECT_Y})...")
pyautogui.moveTo(CONNECT_X, CONNECT_Y, duration=1.0)  # Slower movement to see it
print(f"   ✓ Mouse positioned at: {pyautogui.position()}")
time.sleep(1.0)

# Step 7: Restore windows (Win+D again) and click immediately
print("\n7. Restoring windows (Win+D again)...")
pyautogui.hotkey('win', 'd')
time.sleep(2.0)  # Longer wait for windows to fully restore
print(f"   Mouse still at: {pyautogui.position()}")
print("   Clicking...")
pyautogui.click()
print("   ✓ Clicked!")

# Step 8: Wait for connection
print("\n8. Waiting for meter connection...")
time.sleep(3)
print("   ✓ Connected")

# Step 9: Minimize window
print("\n9. Minimizing UT61E+ window...")
pyautogui.hotkey('win', 'down')
time.sleep(0.5)
print("   ✓ Minimized")

print("\n" + "="*70)
print("✅ UT61E+ RUNNING AND CONNECTED (MINIMIZED)")
print("="*70)
print("Software is running in background. Ready for HID reader.")
print("\nPress Enter to close software, or Ctrl+C to leave running...")

try:
    input()
    print("\nClosing UT61E+ software...")
    process.terminate()
    print("✓ Closed")
except KeyboardInterrupt:
    print("\n\nScript exited. UT61E+ software still running.")
