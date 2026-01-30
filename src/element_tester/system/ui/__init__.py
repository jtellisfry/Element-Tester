# ============================================================================
# element_tester.system.ui Package
# ============================================================================
#
# PyQt6-based user interface components for the Element Tester application.
#
# MODULES:
# - scanning.py : Work Order / Part Number input window (entry point)
# - testing.py  : Main test display with Hipot and Measurement results
# - debug.py    : Standalone debug console for relay/instrument testing
#
# PURPOSE:
# - Separates UI code from business logic (drivers, procedures)
# - All UI modules use PyQt6 signals/slots for event handling
# - Each module can be run standalone for testing (if __name__ == "__main__")
#
# HOW TO MODIFY:
# - Add new UI modules (e.g., settings.py) as separate files in this directory
# - Keep UI logic minimal—delegate hardware control to drivers
# - Use signals to communicate between windows:
#     scanCompleted = pyqtSignal(str, str)  # work_order, part_number
# - To export UI classes for easier import:
#     from .scanning import ScanWindow
#     from .testing import TestingWindow
#     from .debug import DebugDialog
#     __all__ = ["ScanWindow", "TestingWindow", "DebugDialog"]
# ============================================================================
