"""
Launch and Connect to UT61E+ Meter Application

Uses pywinauto for reliable Windows GUI automation instead of
coordinate-based pyautogui clicking.
"""

import subprocess
import sys
import time
from pathlib import Path

# pywinauto for reliable Windows GUI automation
from pywinauto import Application, Desktop
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.timings import wait_until_passes
import win32gui
import win32con


UT61E_BATCH = Path(r"C:\Files\element tester\Element_Tester\ut61xp_elevated.bat")

# Window title patterns to search for
WINDOW_TITLES = ['UT61E+', 'UT61xP', 'Uni-T UT61E+', 'UT61E Plus']

# Button text to look for (try multiple variations)
CONNECT_BUTTON_TEXTS = ['Connect', 'CONNECT', '&Connect', 'connect']


def minimize_all_windows():
    """Minimize all windows using Windows API (like Win+D)."""
    print("[DEBUG] Minimizing all windows...")
    # Find the shell window and send minimize all command
    shell = win32gui.FindWindow("Shell_TrayWnd", None)
    win32gui.SendMessage(shell, win32con.WM_COMMAND, 419, 0)  # 419 = minimize all
    time.sleep(0.5)
    print("[DEBUG] All windows minimized.")


def find_minimized_meter_window():
    """
    Find a minimized meter window using win32gui enumeration.
    Returns the window handle if found, None otherwise.
    """
    found_hwnd = None
    
    def enum_callback(hwnd, _):
        nonlocal found_hwnd
        if win32gui.IsWindow(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and any(pattern.lower() in title.lower() for pattern in ['UT61', 'Uni-T']):
                print(f"[DEBUG] Found window via win32gui: '{title}' (hwnd={hwnd}, minimized={win32gui.IsIconic(hwnd)})")
                found_hwnd = hwnd
                return False  # Stop enumeration
        return True
    
    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception:
        pass  # EnumWindows raises when callback returns False
    
    return found_hwnd


def restore_minimized_window(hwnd):
    """Restore a minimized window given its handle."""
    try:
        if win32gui.IsIconic(hwnd):
            print(f"[DEBUG] Window is minimized, restoring via win32gui...")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
        # Bring to foreground
        win32gui.SetForegroundWindow(hwnd)
        print(f"[DEBUG] Window restored and brought to foreground.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to restore window: {e}")
        return False


def find_meter_window(timeout: float = 15.0) -> Application:
    """
    Find the meter application window, waiting up to timeout seconds.
    Returns a pywinauto Application connected to the window.
    Also handles minimized windows by restoring them.
    """
    print(f"[DEBUG] Searching for meter window (timeout: {timeout}s)...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Search for window by title patterns
        for title in WINDOW_TITLES:
            try:
                app = Application(backend='uia').connect(title_re=f".*{title}.*", timeout=1)
                print(f"[DEBUG] Found window matching '{title}'")
                return app
            except ElementNotFoundError:
                pass
            except Exception as e:
                # Connection failed, try next pattern
                pass
        
        # Also try partial match on all windows
        try:
            desktop = Desktop(backend='uia')
            for win in desktop.windows():
                title = win.window_text()
                if any(pattern.lower() in title.lower() for pattern in ['UT61', 'Uni-T']):
                    app = Application(backend='uia').connect(handle=win.handle)
                    print(f"[DEBUG] Found window: '{title}'")
                    return app
        except Exception:
            pass
        
        # Check for minimized window that pywinauto might not see
        hwnd = find_minimized_meter_window()
        if hwnd:
            print(f"[DEBUG] Found minimized/hidden window, attempting to restore...")
            if restore_minimized_window(hwnd):
                time.sleep(0.5)
                # Now try to connect via pywinauto
                try:
                    app = Application(backend='uia').connect(handle=hwnd)
                    print(f"[DEBUG] Successfully connected to restored window.")
                    return app
                except Exception as e:
                    print(f"[DEBUG] Failed to connect after restore: {e}")
        
        time.sleep(0.5)
    
    return None


def ensure_window_visible(app: Application):
    """Make sure the window is restored (not minimized) and in foreground."""
    try:
        main_win = app.top_window()
        title = main_win.window_text()
        print(f"[DEBUG] Working with window: '{title}'")
        
        # Restore if minimized
        if main_win.is_minimized():
            print("[DEBUG] Window is minimized, restoring...")
            main_win.restore()
            time.sleep(0.3)
        
        # Bring to front
        main_win.set_focus()
        print("[DEBUG] Window focused and brought to front.")
        time.sleep(0.5)
        
        return main_win
    except Exception as e:
        print(f"[ERROR] Failed to ensure window visible: {e}")
        return None


def click_connect_button(main_win) -> bool:
    """
    Find and click the Connect button using pywinauto.
    Returns True if successful, False otherwise.
    """
    print("[DEBUG] Looking for Connect button...")
    
    # Method 1: Try to find button by text
    for button_text in CONNECT_BUTTON_TEXTS:
        try:
            button = main_win.child_window(title=button_text, control_type="Button")
            if button.exists(timeout=1):
                print(f"[DEBUG] Found button with text '{button_text}', clicking...")
                button.click_input()
                print("[DEBUG] Clicked Connect button via control.")
                return True
        except Exception:
            pass
    
    # Method 2: Try all buttons and look for one containing "connect"
    try:
        buttons = main_win.descendants(control_type="Button")
        for btn in buttons:
            btn_text = btn.window_text().lower()
            if 'connect' in btn_text:
                print(f"[DEBUG] Found button '{btn.window_text()}', clicking...")
                btn.click_input()
                print("[DEBUG] Clicked Connect button via search.")
                return True
    except Exception as e:
        print(f"[DEBUG] Button search failed: {e}")
    
    # Method 3: Fallback to coordinate-based click (last resort)
    print("[DEBUG] Button not found by control, falling back to coordinate click...")
    try:
        rect = main_win.rectangle()
        # Click near top-left where Connect button typically is
        click_x = rect.left + 50
        click_y = rect.top + 50
        
        import pyautogui
        pyautogui.click(click_x, click_y)
        print(f"[DEBUG] Fallback click at ({click_x}, {click_y})")
        return True
    except Exception as e:
        print(f"[ERROR] Fallback click failed: {e}")
        return False


def minimize_window(main_win):
    """Minimize the meter application window."""
    try:
        print("[DEBUG] Minimizing meter window...")
        main_win.minimize()
        print("[DEBUG] Window minimized.")
    except Exception as e:
        print(f"[ERROR] Failed to minimize: {e}")


def main():
    # Step 1: Minimize all windows
    minimize_all_windows()
    
    # Step 2: Find the already-running meter application window
    # (Batch file launch removed - meter app should already be running)
    print("[DEBUG] Looking for already-running meter window...")
    app = find_meter_window(timeout=15.0)
    
    if app is None:
        print("[ERROR] Could not find meter application window!")
        sys.exit(1)
    
    # Step 4: Ensure window is visible and in foreground
    main_win = ensure_window_visible(app)
    if main_win is None:
        print("[ERROR] Could not bring window to foreground!")
        sys.exit(1)
    
    time.sleep(1)  # Brief pause before clicking
    
    # Step 5: Click the Connect button
    if not click_connect_button(main_win):
        print("[WARNING] Could not click Connect button!")
    
    # Step 6: Wait for connection to establish
    print("[DEBUG] Waiting for connection...")
    time.sleep(3)
    
    # Step 7: Minimize the meter window
    minimize_window(main_win)
    
    print("[DEBUG] Done! Meter application running in background.")


if __name__ == "__main__":
    main()
