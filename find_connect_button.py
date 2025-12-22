"""
Find UT61E+ CONNECT Button Coordinates
=======================================
Helper script to locate the CONNECT button for automation
"""

import pyautogui
import time
from PIL import ImageGrab

print("="*70)
print("UT61E+ CONNECT BUTTON FINDER")
print("="*70)

print("""
This script will help you find the CONNECT button coordinates.

INSTRUCTIONS:
1. Launch UT61E+ software manually
2. Position the window where you want it
3. Run this script
4. Move your mouse over the CONNECT button
5. Press Ctrl+C when hovering over the button
6. We'll record those coordinates
""")

input("\nPress Enter when UT61E+ is open and ready...")

print("\n🖱️  Move your mouse over the CONNECT button...")
print("   Press Ctrl+C when hovering over it\n")

try:
    while True:
        x, y = pyautogui.position()
        print(f"\rCurrent position: X={x:4d} Y={y:4d}", end="", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    x, y = pyautogui.position()
    print(f"\n\n✅ CONNECT button coordinates: X={x}, Y={y}")
    print(f"\nAdd this to your code:")
    print(f"    pyautogui.click({x}, {y})")
    
    # Test click
    print("\n⚠️  Testing click in 3 seconds...")
    print("   Make sure the CONNECT button is still in the same place!")
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    
    pyautogui.click(x, y)
    print("✓ Clicked!")
    print("\nDid it work? If yes, save these coordinates.")
