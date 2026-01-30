"""Simulate hipot failure - complete workflow with intentional hipot test failure.

This script simulates the complete Element Tester workflow with a FAILING hipot test:
1. Scanning Window (Work Order + Part Number entry)
2. Configuration Window (Voltage/Wattage selection)
3. Testing Window (Hipot FAILS + Measurement tests)

This allows testing of the retry logic and the 3-button dialog (Continue/Retry/Exit).

Run from the project root (PowerShell):
    & ".venv/Scripts/python.exe" scripts/simulate_hypotfail.py
"""
from pathlib import Path
import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QTimer

# Ensure src on path
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from element_tester.system.core.test_runner import TestRunner
from element_tester.system.ui.test_coordinator import TestCoordinator
import time

# IMPORTANT: Monkey-patch TestRunner.run_hipot to force failure in simulate mode
_original_run_hipot = TestRunner.run_hipot

def _patched_run_hipot(self, ui, work_order, part_number, simulate=False, keep_relay_closed=False):
    """Patched run_hipot that forces failure in simulate mode."""
    from PyQt6 import QtWidgets
    from typing import Tuple
    
    self.log.info(f"HIPOT start (FORCED FAIL) | WO={work_order} | PN={part_number}")
    
    if ui is None:
        self.log.error("HIPOT start failed: ui is None")
        return False, "UI not available", {"passed": False}

    try:
        ui.hypot_ready()
    except Exception as e:
        self.log.error(f"HIPOT: ui.hypot_ready() failed: {e}", exc_info=True)
        return False, f"UI error: {e}", {"passed": False}
    time.sleep(0.2)

    ui.hypot_running()
    QtWidgets.QApplication.processEvents()
    ui.append_hypot_log("Checking Hipot connections...")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.5)

    # Simulate the test steps but make it FAIL
    ui.append_hypot_log("Step 1/5: Reset instrument (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.8)
    ui.append_hypot_log("Step 2/5: Configure relay (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.8)
    ui.append_hypot_log("Step 3/5: Configure hipot test (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.8)
    ui.append_hypot_log("Step 4/5: Execute hipot test (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(1.5)
    ui.append_hypot_log("Step 5/5: Disable relay (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.8)
    
    # FORCE FAILURE
    passed = False
    msg = "Simulated Hipot FAIL - Current trip detected"
    
    ui.hypot_result(passed)
    QtWidgets.QApplication.processEvents()
    
    self.log.info(f"HIPOT end (FORCED FAIL) | passed={passed} | msg={msg}")
    
    detail = {
        "passed": passed,
        "work_order": work_order,
        "part_number": part_number,
        "message": msg,
        "simulate": True
    }
    
    return passed, msg, detail

# Apply the monkey patch
TestRunner.run_hipot = _patched_run_hipot

app = QtWidgets.QApplication(sys.argv)

# Create UI coordinator
coordinator = TestCoordinator()

# Create runner in simulate mode
runner = TestRunner(simulate=True)

def on_scan_completed(wo: str, pn: str):
    """Handle scan completion - show config dialog then start test."""
    print(f"Scan complete: WO={wo}, PN={pn}")
    
    # Get configuration
    config = coordinator.transition_to_configuration(wo, pn)
    
    if config is None:
        print("Configuration cancelled - returning to scan")
        coordinator.show_scan_window()
        return
    
    # Store configuration
    runner._selected_config = config
    print(f"Configuration selected: {config}")
    
    # Transition to testing window
    coordinator.transition_to_testing()
    test_window = coordinator.get_test_window()
    
    # Store callback to return to scan window
    runner._return_to_scan_callback = coordinator.transition_to_scanning
    
    # Run full test sequence after brief delay
    QTimer.singleShot(500, lambda: runner.run_full_sequence(
        ui=test_window,
        work_order=wo,
        part_number=pn
    ))

# Connect scan completion signal
coordinator.show_scan_window()
coordinator.scan_window.scanCompleted.connect(on_scan_completed)

# Auto-fill scanning window after 1 second for quick testing
def auto_fill_scan():
    """Auto-fill the scan window with test values for quick simulation."""
    if coordinator.scan_window:
        coordinator.scan_window.work_edit.setText("FAIL_TEST_WO")
        coordinator.scan_window.part_edit.setText("FAIL_TEST_PN")
        # Optionally auto-submit after another second
        QTimer.singleShot(500, lambda: coordinator.scan_window.btn_start.click() if coordinator.scan_window else None)

# Auto-fill after 1 second (for quick testing - comment out for manual entry)
QTimer.singleShot(1000, auto_fill_scan)

print("=== Element Tester HIPOT FAIL Simulation Started ===")
print("Auto-filling fields with FAIL_TEST_WO / FAIL_TEST_PN in 1 second...")
print("The hipot test will FAIL to test retry logic with Continue/Retry/Exit dialog")
print("===========================================================")
sys.exit(app.exec())
