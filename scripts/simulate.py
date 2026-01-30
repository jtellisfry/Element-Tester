"""Full simulate runner - complete workflow from scanning to testing.

This script simulates the complete Element Tester workflow:
1. Scanning Window (Work Order + Part Number entry)
2. Configuration Window (Voltage/Wattage selection)
3. Testing Window (Hipot + Measurement tests)

Run from the project root (PowerShell):
    & ".venv/Scripts/python.exe" scripts/run_simulate.py
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
        coordinator.scan_window.work_edit.setText("TEST_WO")
        coordinator.scan_window.part_edit.setText("TEST_PN")
        # Optionally auto-submit after another second
        QTimer.singleShot(500, lambda: coordinator.scan_window.btn_start.click() if coordinator.scan_window else None)

# Auto-fill after 1 second (for quick testing - comment out for manual entry)
QTimer.singleShot(1000, auto_fill_scan)

print("=== Element Tester Simulation Started ===")
print("Auto-filling fields with TEST_WO / TEST_PN in 1 second...")
print("Enter different values for custom simulation")
print("==========================================")
sys.exit(app.exec())
