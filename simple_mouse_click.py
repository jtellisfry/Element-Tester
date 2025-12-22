"""
Simple Mouse Mover - Manual Testing
====================================
"""

import pyautogui
import time

CONNECT_X = 183
CONNECT_Y = 90

print("="*70)
print("SIMPLE MOUSE CLICK TEST")
print("="*70)

print(f"\nTarget: ({CONNECT_X}, {CONNECT_Y})")
print(f"Current mouse position: {pyautogui.position()}")

wait_time = int(input("\nHow many seconds to wait before clicking? (e.g., 5): "))

print(f"\nWaiting {wait_time} seconds... (launch UT61E+ now if needed)")
for i in range(wait_time, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

print(f"\nMoving mouse to ({CONNECT_X}, {CONNECT_Y})...")
pyautogui.moveTo(CONNECT_X, CONNECT_Y, duration=1)
print(f"Mouse at: {pyautogui.position()}")

time.sleep(0.5)

print("\nClicking...")
pyautogui.click()
print("✓ Clicked!")

print("\nDone!")
