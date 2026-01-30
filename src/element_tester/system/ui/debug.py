from __future__ import annotations
from typing import Callable, Dict, Optional

import sys
from pathlib import Path

# Add src/ to path so element_tester can be imported
# Path calculation: __file__ -> ui/ -> system/ -> element_tester/ -> src/ -> workspace_root/
# parents[0]=ui, parents[1]=system, parents[2]=element_tester, parents[3]=src, parents[4]=workspace_root
SRC_ROOT = Path(__file__).resolve().parents[3]  # This IS src/ already
sys.path.insert(0, str(SRC_ROOT))

from PyQt6 import QtWidgets, QtCore, QtGui
import argparse
from element_tester.system.drivers.relay_mcc.driver import ERB08Driver

# =================
# Debug Dialog UI
# =================
#
# This module provides `DebugDialog`, a compact form-like dialog used to
# exercise instrument and relay actions during development.
#
# -----------------
# Standalone Usage
# -----------------
# This dialog can be run standalone for manual testing:
#   python debug.py              # Use REAL hardware (ERB08Driver with simulate=False)
#   python debug.py --simulate   # Use mock driver (safe, no hardware required)
#
# By default, the real driver is instantiated to control actual relays.
# Pass --simulate to use the mock driver for development/testing without hardware.
#
# -----------------
# Notes for maintainers
# -----------------
# - The DebugDialog class is UI-only and accepts an actions dict of callbacks.
# - The mock driver (_MockDRV) mirrors the ERB08Driver façade API so it can
#   be swapped in for testing.
# - When used in the real application (outside __main__), pass the real driver
#   and actions dict to DebugDialog at construction time.

class DebugDialog(QtWidgets.QDialog):
    """
    Form-like debug console.

    - Renders the provided actions as large form-style push-buttons in two columns
      (left/right) to match the updated mockup.
    - Operator selects a button (click) then presses the "ACTUATE" button to run it.
    - The selected button is visually highlighted while running and after completion.
    - To change what a button does, pass a different callback in the `actions` dict
      when constructing this dialog (see the `if __name__ == "__main__"` block).
    """

    HIGHLIGHT_STYLE = "background-color: #FFD54F; color: #000; font-weight:600;"
    SUCCESS_STYLE = "background-color: #A5D6A7; color: #000; font-weight:600;"
    ERROR_STYLE = "background-color: #EF9A9A; color: #000; font-weight:600;"
    DEFAULT_STYLE = ""  # leave to platform default; can be customized if desired

    def __init__(self, actions: Dict[str, Callable[[], None]], parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Debug Console")
        self.resize(720, 520)

        self._actions = actions
        self._buttons: Dict[str, QtWidgets.QPushButton] = {}
        self._selected_label: Optional[str] = None

        self._build_ui()

    # -------- UI setup --------
    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)

        # Title area (big header like the mockup)
        header = QtWidgets.QLabel("DEBUG")
        header_font = QtGui.QFont()
        header_font.setPointSize(24)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(64)
        header.setStyleSheet("background-color: #0E7A7A; color: white;")
        outer.addWidget(header)

        # Buttons area (three-column form-like layout) wrapped in a scroll area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        body = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(body)
        grid.setContentsMargins(24, 12, 24, 12)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # Lay out items row-by-row:
        # - "[TITLE] ..." goes in the middle column (col 1), occupying its own row
        # - "---SEPARATOR---" spans all three columns
        # - Action buttons fill three columns from left to right
        labels = list(self._actions.keys())
        row_idx, col_idx = 0, 0

        for lbl in labels:
            if lbl == "---SEPARATOR---":
                sep = self._make_separator()
                grid.addWidget(sep, row_idx, 0, 1, 3)  # span all columns
                row_idx += 1
                col_idx = 0
            elif lbl.startswith("[TITLE]"):
                # Title cards in the second column only
                title_text = lbl.replace("[TITLE]", "").strip()
                title_label = self._make_section_title(title_text)
                grid.addWidget(title_label, row_idx, 1)  # middle column
                row_idx += 1
                col_idx = 0
            else:
                btn = self._make_action_button(lbl)
                grid.addWidget(btn, row_idx, col_idx)
                col_idx += 1
                if col_idx >= 3:
                    col_idx = 0
                    row_idx += 1

        # Push content to the top
        grid.setRowStretch(row_idx + 1, 1)

        scroll.setWidget(body)
        outer.addWidget(scroll, stretch=1)

        # Log output area
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Debug log will appear here...")
        self.log_view.setFixedHeight(120)
        outer.addWidget(self.log_view)

        # Buttons at bottom: Actuate and Close
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_actuate = QtWidgets.QPushButton("ACTUATE")
        self.btn_actuate.setFixedSize(140, 44)
        self.btn_actuate.setStyleSheet("background-color: #2E7D32; color: white; font-weight:700;")
        self.btn_close = QtWidgets.QPushButton("CLOSE")
        self.btn_close.setFixedSize(140, 44)
        self.btn_close.setStyleSheet("background-color: #C62828; color: white; font-weight:700;")
        btn_row.addWidget(self.btn_actuate)
        btn_row.addWidget(self.btn_close)

        outer.addLayout(btn_row)

        # Wire up signals
        self.btn_close.clicked.connect(self.close)
        self.btn_actuate.clicked.connect(self._on_actuate_clicked)

    def _make_action_button(self, label: str) -> QtWidgets.QPushButton:
        """
        Create a large action button and register its click to select it.
        To change button behaviour, replace the callback in the actions dict
        that is passed to this dialog (see module bottom).
        """
        btn = QtWidgets.QPushButton(label)
        btn.setCheckable(True)
        btn.setMinimumHeight(48)
        btn.setStyleSheet("font-size: 12pt; padding: 8px;")
        btn.clicked.connect(lambda checked, lb=label: self._on_action_button_clicked(lb))
        self._buttons[label] = btn
        return btn
    
    def _make_separator(self) -> QtWidgets.QFrame:
        """
        Create a horizontal separator line.
        """
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #000; height: 2px; margin: 8px 0px;")
        return line
    
    def _make_section_title(self, title: str) -> QtWidgets.QLabel:
        """
        Create a section title label (non-clickable header).
        """
        label = QtWidgets.QLabel(title)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "background-color: #3A3A3A; "
            "color: white; "
            "font-size: 11pt; "
            "font-weight: bold; "
            "padding: 8px; "
            "border-radius: 4px;"
        )
        label.setFixedHeight(40)
        return label

    # -------- Behavior / selection --------
    def _on_action_button_clicked(self, label: str):
        # Enforce exclusive selection: uncheck others
        for lb, b in self._buttons.items():
            if lb != label:
                b.setChecked(False)
                b.setStyleSheet("font-size: 12pt; padding: 8px;")  # reset style
        # Mark selected
        self._selected_label = label
        self._buttons[label].setChecked(True)
        # Visually indicate selection (lighter than actuation highlight)
        self._buttons[label].setStyleSheet("background-color: #E0E0E0; font-weight:600; padding: 8px;")
        self._append_log(f"Selected: {label}")

    def _append_log(self, text: str):
        self.log_view.appendPlainText(text)

    # -------- Actuation flow --------
    @QtCore.pyqtSlot()
    def _on_actuate_clicked(self):
        if not self._selected_label:
            QtWidgets.QMessageBox.warning(self, "No Action Selected", "Please select a debug action first.")
            return

        label = self._selected_label
        cb = self._actions.get(label)
        if cb is None:
            QtWidgets.QMessageBox.warning(self, "Unknown Action", f"No callback bound for '{label}'.")
            return

        btn = self._buttons.get(label)
        # Highlight selected button immediately
        if btn:
            btn.setStyleSheet(self.HIGHLIGHT_STYLE)
            QtWidgets.QApplication.processEvents()

        self._append_log(f"Running: {label}")
        try:
            # Run callback (synchronous). If you expect long-running tasks, run cb in a thread.
            cb()
            self._append_log(f"✓ Completed: {label}")
            if btn:
                btn.setStyleSheet(self.SUCCESS_STYLE)
        except Exception as e:
            self._append_log(f"✗ Error in '{label}': {e}")
            if btn:
                btn.setStyleSheet(self.ERROR_STYLE)
            QtWidgets.QMessageBox.critical(self, "Debug Error", f"Error while running '{label}':\n{e}")
        finally:
            # Briefly show completion state then revert to normal (non-selected) style.
            if btn:
                QtCore.QTimer.singleShot(700, lambda b=btn: self._revert_button_style(b))

    def _revert_button_style(self, btn: QtWidgets.QPushButton):
        # If still checked (selected), show selected style; otherwise clear style.
        if btn.isChecked():
            btn.setStyleSheet("background-color: #E0E0E0; font-weight:600; padding: 8px;")
        else:
            btn.setStyleSheet("font-size: 12pt; padding: 8px;")

# ========== BUTTON SPECIFICATIONS ==========
# Define all debug buttons in one place for clarity.
# Format: (label, callback_name, purpose)
BUTTON_SPECS = [
    # Relay Section
    ("[TITLE] Relay", "title_relay", "Section title for relay controls"),
    ("MCC Relay 1", "relay_toggle_0", "Toggle relay bit 0"),
    ("MCC Relay 2", "relay_toggle_1", "Toggle relay bit 1"),
    ("MCC Relay 3", "relay_toggle_2", "Toggle relay bit 2"),
    ("MCC Relay 4", "relay_toggle_3", "Toggle relay bit 3"),
    ("MCC Relay 5", "relay_toggle_4", "Toggle relay bit 4"),
    ("MCC Relay 6", "relay_toggle_5", "Toggle relay bit 5"),
    ("MCC Relay 7", "relay_toggle_6", "Toggle relay bit 6"),
    ("MCC Relay 8", "relay_toggle_7", "Toggle relay bit 7"),
    ("All On", "all_on", "Turn all relays ON"),
    ("All Off", "all_off", "Turn all relays OFF"),
    ("Self Test Walk", "self_test_walk", "Walk through each relay"),
    ("HYPOT Relays", "hypot_relays", "Configure hypot relays"),
    # Separator
    ("---SEPARATOR---", "separator1", "Visual separator"),
    # Hypot Section
    ("[TITLE] Hypot", "title_hypot", "Section title for hypot controls"),
    ("HIPOT: Test Start", "hipot_cmd_test_start", "Send TEST command"),
    ("HIPOT: Test Stop", "hipot_cmd_test_stop", "Send STOP command"),
    ("HIPOT: Reset", "hipot_cmd_reset", "Send *RST command"),
    ("HIPOT: Get Result", "hipot_cmd_get_result", "Query TEST:RESULT?"),
    ("HIPOT: Read Result (RD 1?)", "hipot_cmd_read_result", "Query RD 1? for pass/fail"),
    ("HIPOT: Get Status", "hipot_cmd_get_status", "Query status"),
    # Separator
    ("---SEPARATOR---", "separator2", "Visual separator"),
    # Full test sequences
    ("HYPOT Test (Full)", "hypot_test", "Run complete hipot test"),
    ("HYPOT Reset (Full)", "hypot_reset", "Full reset sequence")
]

# ========== CALLBACK DEFINITIONS ==========
# Provide a lightweight mock driver and local_state so this module can
# be run standalone for manual testing. In the real application these
# will be provided by the higher-level runtime.
class _MockDRV:
    def __init__(self, board_num: int = 0, port: int = 12):
        # port: use 12 (first 4 relays) or 13 (next 4 relays) to simulate MCC mapping
        self.board_num = board_num
        self.port = port
        self._state = [False] * 8

    def set_relay(self, bit: int, on: bool):
        # Map logical relay index to port/bit for logging purposes.
        # Physical mapping used in some systems: relays 0-3 -> port 12 bits 0-3,
        # relays 4-7 -> port 13 bits 0-3.
        self._state[bit] = bool(on)

        port_used = 12 if bit < 4 else 13
        bit_in_port = bit if bit < 4 else (bit - 4)
        msg = (
            f"[SIM] Board {self.board_num} Port {port_used} Bit {bit_in_port} "
            f"-> {'ON' if on else 'OFF'}"
        )

        # Append to the UI log if the dialog exists, otherwise fall back to print().
        dlg_obj = globals().get("dlg")
        if dlg_obj is not None:
            try:
                dlg_obj._append_log(msg)
            except Exception:
                print(msg)
        else:
            print(msg)

    def all_off(self):
        self._state = [False] * 8
        msg = f"[SIM] Board {self.board_num} All relays -> OFF"
        if 'dlg' in globals() and globals().get('dlg') is not None:
            try:
                globals()['dlg']._append_log(msg)
            except Exception:
                print(msg)
        else:
            print(msg)

    def all_on(self):
        self._state = [True] * 8
        msg = f"[SIM] Board {self.board_num} All relays -> ON"
        if 'dlg' in globals() and globals().get('dlg') is not None:
            try:
                globals()['dlg']._append_log(msg)
            except Exception:
                print(msg)
        else:
            print(msg)

    def self_test_walk(self, delay_ms: int = 100):
        # simple sync walk for testing purpose
        for b in range(8):
            self.set_relay(b, True)
            QtWidgets.QApplication.processEvents()
            QtCore.QThread.msleep(delay_ms)
            self.set_relay(b, False)

    def shutdown(self):
        pass

# Standalone runtime state used by the callbacks below
local_state = [False] * 8

# Define each callback with clear name and purpose
def relay_toggle_0():
    """Toggle MCC Relay 1 (bit 0)"""
    bit = 0
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def relay_toggle_1():
    """Toggle MCC Relay 2 (bit 1)"""
    bit = 1
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def relay_toggle_2():
    """Toggle MCC Relay 3 (bit 2)"""
    bit = 2
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def relay_toggle_3():
    """Toggle MCC Relay 4 (bit 3)"""
    bit = 3
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def relay_toggle_4():
    """Toggle MCC Relay 5 (bit 4)"""
    bit = 4
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def relay_toggle_5():
    """Toggle MCC Relay 6 (bit 5)"""
    bit = 5
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def relay_toggle_6():
    """Toggle MCC Relay 7 (bit 6)"""
    bit = 6
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def relay_toggle_7():
    """Toggle MCC Relay 8 (bit 7)"""
    bit = 7
    new_state = not local_state[bit]
    try:
        drv.set_relay(bit, new_state)
        local_state[bit] = new_state
        dlg._append_log(f"Relay {bit} → {'ON' if new_state else 'OFF'}")
    except Exception as e:
        dlg._append_log(f"Error toggling relay {bit}: {e}")

def all_off_cb():
    try:
        drv.all_off()
        for b in range(8):
            local_state[b] = False
        dlg._append_log("All relays → OFF")
    except Exception as e:
        dlg._append_log(f"Error all_off: {e}")

def all_on_cb():
    try:
        drv.all_on()
        for b in range(8):
            local_state[b] = True
        dlg._append_log("All relays → ON")
    except Exception as e:
        dlg._append_log(f"Error all_on: {e}")

def self_test_cb():
    try:
        dlg._append_log("Starting self-test walk...")
        drv.self_test_walk(delay_ms=100)
        dlg._append_log("Self-test walk complete")
    except Exception as e:
        dlg._append_log(f"Error self_test_walk: {e}")

def hypot_relays_cb():
    """Configure relay mapping for hypot test (placeholder for specific relay pattern)"""
    try:
        dlg._append_log("Configuring HYPOT relay pattern...")
        # Example: Set relays for hipot test configuration
        # This would typically activate specific relays needed for the hipot circuit
        # For now, demonstrate with a simple pattern
        
        # First turn off all relays (copied from individual toggle logic)
        drv.all_off()
        for b in range(8):
            local_state[b] = False
        dlg._append_log("All relays → OFF (before HYPOT setup)")
        
        # Now set specific relays for hipot pattern
        drv.set_relay(0, True)   # Example: Enable relay 0 for hipot
        drv.set_relay(1, True)   # Example: Enable relay 1 for hipot
        local_state[0] = True
        local_state[1] = True
        dlg._append_log("HYPOT relays configured (relays 0-1 ON)")
    except Exception as e:
        dlg._append_log(f"Error configuring hypot relays: {e}")

def hypot_test_cb():
    """Run a hypot test using the AR3865 driver"""
    try:
        dlg._append_log("Starting HYPOT test...")
        # Import hypot driver
        from element_tester.system.drivers.hypot3865.driver import AR3865Driver
        from element_tester.system.drivers.hypot3865.commands import HipotConfig
        
        # Create driver in simulate mode
        hipot_drv = AR3865Driver(resource='serial://COM3', simulate=True)
        hipot_drv.initialize()
        dlg._append_log(f"HYPOT device: {hipot_drv.idn()}")
        
        # Configure test parameters
        cfg = HipotConfig(
            voltage_v=1500.0,
            current_trip_mA=5.0,
            ramp_time_s=1.0,
            dwell_time_s=1.0,
            fall_time_s=0.5,
            polarity='POS'
        )
        hipot_drv.configure(cfg)
        dlg._append_log(f"Configured: {cfg.voltage_v}V, {cfg.current_trip_mA}mA trip")
        
        # Run test
        passed, raw = hipot_drv.run_once(cfg, timeout_s=5.0)
        result_str = "PASS ✓" if passed else "FAIL ✗"
        dlg._append_log(f"HYPOT test result: {result_str} ({raw})")
        
        hipot_drv.shutdown()
        dlg._append_log("HYPOT test complete")
    except Exception as e:
        dlg._append_log(f"Error running hypot test: {e}")

def hypot_reset_cb():
    """Reset the AR3865 hipot tester to default state"""
    try:
        dlg._append_log("Resetting HYPOT device...")
        from element_tester.system.drivers.hypot3865.driver import AR3865Driver
        
        hipot_drv = AR3865Driver(resource='serial://COM6', simulate=False)
        hipot_drv.initialize()  # This includes *RST, *CLS, SYST:CLE
        dlg._append_log(f"HYPOT reset complete: {hipot_drv.idn()}")
        hipot_drv.shutdown()
    except Exception as e:
        dlg._append_log(f"Error resetting hypot: {e}")

# ========== INDIVIDUAL HIPOT COMMAND CALLBACKS ==========
# Global hipot transport/commands instance for individual command testing
_hipot_transport = None
_hipot_commands = None

def _ensure_hipot_connection():
    """Ensure hipot transport is connected (lazy init)."""
    global _hipot_transport, _hipot_commands
    if _hipot_transport is None or _hipot_commands is None:
        from element_tester.system.drivers.hypot3865.transport import AR3865Transport, AR3865OpenParams
        from element_tester.system.drivers.hypot3865.commands import AR3865Commands
        
        params = AR3865OpenParams(
            resource="serial://COM6",
            baudrate=38400,
            simulate=False
        )
        _hipot_transport = AR3865Transport(params)
        _hipot_transport.open()
        _hipot_commands = AR3865Commands(_hipot_transport)
        dlg._append_log("✓ HIPOT connection established (COM6 @ 38400 baud)")

def hipot_cmd_test_start_cb():
    """Send TEST or TEST:START command to hipot"""
    try:
        _ensure_hipot_connection()
        cmd = _hipot_commands
        if cmd is None:
            dlg._append_log("✗ HIPOT not connected")
            return
        dlg._append_log("Sending: TEST")
        cmd.cmd_test()
        dlg._append_log("✓ Command sent")
    except Exception as e:
        dlg._append_log(f"✗ Error: {e}")

def hipot_cmd_test_stop_cb():
    """Send STOP or TEST:STOP command to hipot"""
    try:
        _ensure_hipot_connection()
        cmd = _hipot_commands
        if cmd is None:
            dlg._append_log("✗ HIPOT not connected")
            return
        dlg._append_log("Sending: TEST:STOP")
        cmd.cmd_stop_test()
        dlg._append_log("✓ Command sent")
    except Exception as e:
        dlg._append_log(f"✗ Error: {e}")

def hipot_cmd_reset_cb():
    """Send RESET command to hipot"""
    try:
        _ensure_hipot_connection()
        cmd = _hipot_commands
        if cmd is None:
            dlg._append_log("✗ HIPOT not connected")
            return
        dlg._append_log("Sending: RESET + *CLS")
        cmd.cmd_reset()
        dlg._append_log("✓ Reset complete")
    except Exception as e:
        dlg._append_log(f"✗ Error: {e}")

def hipot_cmd_get_result_cb():
    """Query TEST:RESULT? from hipot"""
    try:
        _ensure_hipot_connection()
        cmd = _hipot_commands
        if cmd is None:
            dlg._append_log("✗ HIPOT not connected")
            return
        dlg._append_log("Querying: TEST:RESULT?")
        result = cmd.cmd_get_result()
        dlg._append_log(f"✓ Result: {repr(result)}")
    except Exception as e:
        dlg._append_log(f"✗ Error: {e}")

def hipot_cmd_read_result_cb():
    """Query RD 1? from hipot (AR3865 specific result command)"""
    try:
        _ensure_hipot_connection()
        cmd = _hipot_commands
        if cmd is None:
            dlg._append_log("✗ HIPOT not connected")
            return
        dlg._append_log("Querying: RD 1?")
        result = cmd.cmd_get_result()
        dlg._append_log(f"✓ Result: {repr(result)}")
        # Also interpret it
        r_upper = (result or "").upper().strip()
        if "PASS" in r_upper or r_upper == "P":
            dlg._append_log("  → Interpreted as: PASS ✓")
        elif "FAIL" in r_upper or r_upper == "F" or "HI-LIMIT" in r_upper:
            dlg._append_log("  → Interpreted as: FAIL ✗")
        else:
            dlg._append_log(f"  → Interpreted as: {result}")
    except Exception as e:
        dlg._append_log(f"✗ Error: {e}")

def hipot_cmd_get_status_cb():
    """Query status from hipot"""
    try:
        _ensure_hipot_connection()
        cmd = _hipot_commands
        if cmd is None:
            dlg._append_log("✗ HIPOT not connected")
            return
        dlg._append_log("Querying: *IDN?")
        idn = cmd.cmd_idn()
        dlg._append_log(f"✓ IDN: {repr(idn)}")
    except Exception as e:
        dlg._append_log(f"✗ Error: {e}")


# ========== BUILD ACTIONS DICT ==========
# Map button labels to callbacks using specs above
if __name__ == "__main__":
    # Parse command-line arguments to decide between real and simulate mode
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", help="Use simulated (fake) relay driver instead of real hardware")
    args = parser.parse_args()

    # Instantiate driver: real by default, mock only if --simulate is passed
    if args.simulate:
        # Use mock driver for safe testing without hardware
        drv = _MockDRV()
    else:
        # Use real ERB08Driver for actual hardware control
        # Hardware config: Relays 0-3 on port 12, Relays 4-7 on port 13
        drv = ERB08Driver(board_num=0, port_low=12, port_high=13, simulate=False)

    # Build actions dict only when running standalone
    actions = {}
    callback_map = {
        "relay_toggle_0": relay_toggle_0,
        "relay_toggle_1": relay_toggle_1,
        "relay_toggle_2": relay_toggle_2,
        "relay_toggle_3": relay_toggle_3,
        "relay_toggle_4": relay_toggle_4,
        "relay_toggle_5": relay_toggle_5,
        "relay_toggle_6": relay_toggle_6,
        "relay_toggle_7": relay_toggle_7,
        "all_off": all_off_cb,
        "all_on": all_on_cb,
        "self_test_walk": self_test_cb,
        "hypot_relays": hypot_relays_cb,
        "hypot_test": hypot_test_cb,
        "hypot_reset": hypot_reset_cb,
        # Individual hipot commands
        "hipot_cmd_test_start": hipot_cmd_test_start_cb,
        "hipot_cmd_test_stop": hipot_cmd_test_stop_cb,
        "hipot_cmd_reset": hipot_cmd_reset_cb,
        "hipot_cmd_get_result": hipot_cmd_get_result_cb,
        "hipot_cmd_read_result": hipot_cmd_read_result_cb,
        "hipot_cmd_get_status": hipot_cmd_get_status_cb,
        # Separators and titles don't need callbacks
        "separator1": lambda: None,
        "separator2": lambda: None,
        "title_relay": lambda: None,
        "title_hypot": lambda: None,
    }
    for label, callback_name, purpose in BUTTON_SPECS:
        if callback_name in callback_map:
            actions[label] = callback_map[callback_name]

    app = QtWidgets.QApplication(sys.argv)
    dlg = DebugDialog(actions)
    try:
        dlg.show()
        app.exec()
    finally:
        try:
            drv.shutdown()
        except Exception:
            pass
