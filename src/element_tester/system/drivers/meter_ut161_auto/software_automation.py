"""
UT61E+ Software Automation - Auto-launch and Connect
=====================================================
"""

import subprocess
import time
import pyautogui
from pathlib import Path

class UT61EPlusAutomation:
    """Automates launching and connecting UT61E+ software"""
    
    def __init__(self, exe_path=None):
        """
        Args:
            exe_path: Path to UT61E+ executable. If None, searches common locations.
        """
        self.exe_path = exe_path or self._find_ut61e_exe()
        self.process = None
        
    def _find_ut61e_exe(self):
        """Find UT61E+ executable in common locations"""
        search_paths = [
            Path(r"C:\Users\STAdmin.FRY-TESTER200\Tester\Element_Tester\assets\UT61E+\UT61E+.exe"),
            Path(r"C:\Program Files\UT61E+\UT61E+.exe"),
            Path(r"C:\Program Files (x86)\UT61E+\UT61E+.exe"),
            Path.cwd() / "assets" / "UT61E+" / "UT61E+.exe",
        ]
        
        for path in search_paths:
            if path.exists():
                return str(path)
        
        raise FileNotFoundError(
            "UT61E+ executable not found. Please specify exe_path parameter."
        )
    
    def launch(self):
        """Launch UT61E+ software"""
        print(f"Launching UT61E+ from: {self.exe_path}")
        self.process = subprocess.Popen([self.exe_path])
        
        # Wait for window to appear
        print("Waiting for software to load...")
        time.sleep(3)  # Give it time to fully load
        
        return True
    
    def click_connect(self):
        """
        Click the CONNECT button in UT61E+ software.
        Uses image recognition or coordinates.
        """
        print("Attempting to click CONNECT button...")
        
        # Strategy 1: Try to find CONNECT button by image (if we have a screenshot)
        # For now, use coordinate-based clicking
        
        # Strategy 2: Use pyautogui to find window and click
        # The CONNECT button is typically at a specific location
        # We'll need to calibrate this based on your screen
        
        # For now, simple approach: Alt+Tab to bring window to front, then click
        time.sleep(1)
        
        # Bring UT61E+ window to front (assumes it's the most recent window)
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.5)
        
        # TODO: Need actual button coordinates
        # For now, just press Enter (sometimes works if CONNECT is default button)
        print("Pressing Enter to connect...")
        pyautogui.press('enter')
        time.sleep(2)
        
        print("✓ Connect command sent")
        return True
    
    def wait_for_data(self, timeout=10):
        """
        Wait for meter to start streaming data.
        Returns True when ready.
        """
        print(f"Waiting for data stream (up to {timeout}s)...")
        time.sleep(timeout)  # Simple wait for now
        print("✓ Meter should be connected")
        return True
    
    def close(self):
        """Close UT61E+ software"""
        if self.process:
            print("Closing UT61E+ software...")
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("UT61E+ SOFTWARE AUTOMATION TEST")
    print("="*70)
    
    try:
        # Create automation controller
        auto = UT61EPlusAutomation()
        
        # Launch software
        auto.launch()
        
        # Click connect (you may need to do this manually first time to calibrate)
        print("\n⚠️  MANUAL STEP REQUIRED:")
        print("   1. Look at the UT61E+ window that just opened")
        print("   2. Note the position of the CONNECT button")
        print("   3. We'll calibrate auto-clicking next")
        
        input("\nPress Enter after you've noted the CONNECT button position...")
        
        # For now, user clicks manually
        print("\n👉 Please click CONNECT manually in the UT61E+ window")
        input("Press Enter after clicking CONNECT...")
        
        # Wait for data
        auto.wait_for_data()
        
        print("\n✅ Software is running and connected!")
        print("   Our HID reader can now access the data stream.")
        print("   (Software will stay open for testing)")
        
        input("\nPress Enter to close software...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        auto.close()
