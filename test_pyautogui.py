"""
Test PyAutoGUI Mouse Movement
==============================
"""

import pyautogui
import time

print("Testing PyAutoGUI...")
print(f"Current mouse position: {pyautogui.position()}")

print("\nMoving mouse to (500, 500) in 2 seconds...")
try:
    pyautogui.moveTo(500, 500, duration=2)
    print(f"✓ Mouse moved to: {pyautogui.position()}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nMoving mouse to (183, 90) in 1 second...")
try:
    pyautogui.moveTo(183, 90, duration=1)
    print(f"✓ Mouse moved to: {pyautogui.position()}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nClicking...")
try:
    pyautogui.click()
    print("✓ Clicked!")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nPyAutoGUI settings:")
print(f"  FAILSAFE: {pyautogui.FAILSAFE}")
print(f"  PAUSE: {pyautogui.PAUSE}")
