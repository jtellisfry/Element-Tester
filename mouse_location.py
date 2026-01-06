import pyautogui
import time
import sys

print("Move your mouse to the desired location and press Ctrl+C to record the position.")
try:
    while True:
        x, y = pyautogui.position()
        print(f"Current mouse position: ({x}, {y})", end='\r')
        time.sleep(0.1)
except KeyboardInterrupt:
    x, y = pyautogui.position()
    print(f"\nRecorded mouse position: ({x}, {y})")
    with open("mouse_location.txt", "w") as f:
        f.write(f"{x},{y}\n")
    print("Saved to mouse_location.txt")
