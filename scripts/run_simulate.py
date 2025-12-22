"""Quick runner to exercise the simulate flow without scanning UI.

This script creates TestRunner in simulate mode, applies a selected configuration
(208V, 7000W) using the `ConfigurationWindow.RESISTANCE_RANGE` mapping if present,
shows the MainTestWindow, and runs the full sequence.

Run from the project root (PowerShell):
    & ".\.venv\Scripts\python.exe" "scripts\run_simulate.py"
"""
from pathlib import Path
import sys
from PyQt6 import QtWidgets

# Ensure src on path
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from element_tester.system.core.test_runner import TestRunner
from element_tester.system.ui.testing import MainTestWindow

# Import configuration mapping
try:
    from element_tester.system.ui.configuration_ui import ConfigurationWindow
except Exception:
    ConfigurationWindow = None

app = QtWidgets.QApplication(sys.argv)

runner = TestRunner(simulate=True)
main = MainTestWindow()
main.show()

# Prepare selected config (208 V, 7000 W)
selected = {"voltage": 208, "wattage": 7000}

# Ensure we have access to the ConfigurationWindow class and its mapping.
if ConfigurationWindow is None:
    # Try a safe importlib fallback in case the direct import above failed
    try:
        import importlib
        mod = importlib.import_module("element_tester.system.ui.configuration_ui")
        ConfigurationWindow = getattr(mod, "ConfigurationWindow", None)
    except Exception:
        ConfigurationWindow = None

# Obtain the resistance-range mapping; prefer the class attribute when available.
rr = {}
if ConfigurationWindow is not None:
    try:
        rr = getattr(ConfigurationWindow, "RESISTANCE_RANGE", {}) or {}
    except Exception:
        rr = {}

print("RESISTANCE_RANGE keys:", list(rr.keys()))

# Look up the (voltage, wattage) tuple in the mapping and attach it to the
# selected config. If not present, keep (0.0, 0.0) to indicate 'not configured'.
selected["resistance_range"] = tuple(rr.get((selected["voltage"], selected["wattage"]), (5.0, 8.0)))

# Ensure the selected config includes a resistance_range; if it's missing or
# the placeholder (0.0, 0.0), try to pull the real mapping from
# ConfigurationWindow.RESISTANCE_RANGE.
try:
    rr = getattr(ConfigurationWindow, "RESISTANCE_RANGE", {})
except Exception:
    rr = {}

current_rr = selected.get("resistance_range", None)
if not current_rr or (isinstance(current_rr, (list, tuple)) and tuple(current_rr) == (0.0, 0.0)):
    selected["resistance_range"] = tuple(rr.get((selected["voltage"], selected["wattage"]), (0.0, 0.0)))

runner._selected_config = selected
runner._main_window = main

# Show the chosen config in the UI measurement log and explicitly append the
# expected resistance for the selected voltage/wattage immediately below it.
try:
    main.append_measurement_log(f"Selected config: {selected['voltage']}V, {selected['wattage']}W")
    rmin, rmax = selected.get("resistance_range", (0.0, 0.0))
    if rmin == 0.0 and rmax == 0.0:
        main.append_measurement_log(f"Resistance range: not configured for {selected['voltage']} V / {selected['wattage']} W")
    else:
        main.append_measurement_log(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")
except Exception:
    pass

# Debug: print selected config stored on runner
print("Runner selected config before run:", getattr(runner, '_selected_config', None))

# Run the test sequence (simulate_for_run True)
ok, msg = runner.run_full_sequence(main, "AUTO_WO", "AUTO_PN")
print("Run finished:", ok, msg)

sys.exit(app.exec())
