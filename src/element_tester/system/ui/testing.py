from __future__ import annotations
from typing import Optional, Literal

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QMessageBox

# Import DebugDialog so the Testing UI can open the standalone debug form.
# Edit the callbacks in the `_open_debug_dialog()` helper below to change what
# each debug button does (this is the single place to customize on-click behavior).
try:
    from element_tester.system.ui.debug import DebugDialog
except Exception:
    DebugDialog = None


HypotState = Literal["ready", "running", "pass", "fail"]


class MainTestWindow(QtWidgets.QWidget):
    """
    Main testing window for the Element Tester.

    Sections:
      - HYPOT: header, status line, log area
      - MEASURING: left/right blocks with pin summaries

    Signals:
      - readyToStart: emitted when operator confirms "all connections done"
    """
    readyToStart = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Element Tester - Main")
        self.resize(1000, 650)
        self._build_ui()
        self.set_hypot_state("ready", "READY")
        # Start in fullscreen mode
        self.showMaximized()

    # ---------------- UI BUILD ----------------
    def _build_ui(self):
        # Background
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#D9D9D9"))
        self.setPalette(pal)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        root.setSpacing(20)

        # ===== HYPOT SECTION =====
        self.hypot_header = self._make_section_header("HYPOT")
        root.addWidget(self.hypot_header)

        # Status line
        self.hypot_status = QtWidgets.QLabel("Status: READY")
        f = self.hypot_status.font()
        f.setPointSize(14)
        self.hypot_status.setFont(f)
        self.hypot_status.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.hypot_status.setMinimumHeight(40)
        root.addWidget(self.hypot_status)

        # Log area
        self.hypot_log = QtWidgets.QPlainTextEdit()
        self.hypot_log.setReadOnly(True)
        self.hypot_log.setMinimumHeight(95)  # Reduced from 160 (about 3/5 = 60%)
        self.hypot_log.setMaximumHeight(110)  # Limit max height to prevent expansion
        self.hypot_log.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #E3E3E3;
                border: 1px solid #AAAAAA;
                color: #000000;
            }
            """
        )
        root.addWidget(self.hypot_log)

        # Separator (simple line)
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        root.addWidget(line)

        # ===== MEASURING SECTION =====
        self.meas_header = self._make_section_header("MEASURING")
        root.addWidget(self.meas_header)

        meas_row = QtWidgets.QHBoxLayout()
        meas_row.setSpacing(60)
        meas_row.addStretch(1)

        self.left_panel = self._make_meas_panel("L")
        self.right_panel = self._make_meas_panel("R")

        meas_row.addWidget(self.left_panel)
        meas_row.addWidget(self.right_panel)
        meas_row.addStretch(1)

        root.addLayout(meas_row)
        # Remove addStretch here to prevent compression in fullscreen

        # Measurement log area with toggle button (collapsible)
        log_container = QtWidgets.QWidget()
        log_layout = QtWidgets.QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(4)
        
        # Toggle button row
        toggle_row = QtWidgets.QHBoxLayout()
        toggle_row.addStretch(1)
        self.btn_toggle_log = QtWidgets.QPushButton("▲ Show Log")
        self.btn_toggle_log.setFixedSize(120, 30)
        self.btn_toggle_log.setStyleSheet(
            """
            QPushButton {
                background-color: #5C4B4B;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #6C5B5B;
            }
            """
        )
        self.btn_toggle_log.clicked.connect(self._toggle_measurement_log)
        toggle_row.addWidget(self.btn_toggle_log)
        log_layout.addLayout(toggle_row)
        
        # Measurement log
        self.measurement_log = QtWidgets.QPlainTextEdit()
        self.measurement_log.setReadOnly(True)
        self.measurement_log.setMinimumHeight(120)
        self.measurement_log.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                color: #000000;
            }
            """
        )
        self.measurement_log.hide()  # Start hidden by default
        log_layout.addWidget(self.measurement_log)
        
        root.addWidget(log_container)
        self._log_visible = False  # Start with log hidden

        # ===== Bottom action row =====
        # Adds a DEBUG button at bottom-right that opens the standalone DebugDialog.
        bottom_row = QtWidgets.QHBoxLayout()
        bottom_row.addStretch(1)

        self.btn_debug = QtWidgets.QPushButton("DEBUG")
        self.btn_debug.setFixedSize(110, 44)
        self.btn_debug.setStyleSheet("background-color: #1976D2; color: white; font-weight:700;")
        self.btn_debug.clicked.connect(self._on_debug_clicked)
        bottom_row.addWidget(self.btn_debug)

        root.addLayout(bottom_row)

    def _make_section_header(self, text: str) -> QtWidgets.QLabel:
        lab = QtWidgets.QLabel(text)
        f = lab.font()
        f.setPointSize(24)
        f.setBold(True)
        lab.setFont(f)
        lab.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lab.setMinimumHeight(60)
        lab.setStyleSheet(
            """
            QLabel {
                background-color: #5C4B4B;
                color: #FFFFFF;
                padding: 10px;
            }
            """
        )
        return lab

    def _make_meas_panel(self, side_label: str) -> QtWidgets.QWidget:
        """
        Create one of the 'L' / 'R' boxes with 3 rows.
        """
        outer = QtWidgets.QFrame()
        outer.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        outer.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 4px; }")
        outer.setMinimumWidth(420)  # Increased from 380 for fullscreen
        outer.setMinimumHeight(200)  # Ensure minimum height
        # Set size policy to prefer expanding but respect minimum size
        outer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Minimum)

        vbox = QtWidgets.QVBoxLayout(outer)
        vbox.setContentsMargins(0, 0, 0, 10)
        vbox.setSpacing(8)

        # Top header
        header = QtWidgets.QLabel(side_label)
        f = header.font()
        f.setPointSize(18)
        f.setBold(True)
        header.setFont(f)
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        header.setMinimumHeight(40)
        header.setStyleSheet(
            """
            QLabel {
                background-color: #5C4B4B;
                color: #FFFFFF;
                padding: 4px;
            }
            """
        )
        vbox.addWidget(header)

        # Body with 3 rows
        body = QtWidgets.QWidget()
        body_v = QtWidgets.QVBoxLayout(body)
        body_v.setContentsMargins(16, 10, 16, 10)
        body_v.setSpacing(12)

        labels = []
        # Use explicit row labels for correct pin pairings (no trailing colon here;
        # the value insertion in the measuring code will add the ": <value>" part)
        row_names = ["Pin 1 to 6: ---", "Pin 2 to 5: ---", "Pin 3 to 4: ---"]
        for i in range(3):
            lab = QtWidgets.QLabel(row_names[i])
            f = lab.font()
            f.setPointSize(14)  # Increased from 12 for better readability
            lab.setFont(f)
            lab.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            lab.setWordWrap(False)  # Prevent wrapping for cleaner display
            # Make the label look like a touch-friendly rounded box and allow it
            # to expand horizontally to fill the white panel area.
            lab.setMinimumHeight(55)  # Increased for better visibility in fullscreen
            lab.setMaximumHeight(70)  # Prevent excessive stretching
            lab.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
            lab.setStyleSheet(
                """
                QLabel {
                    background-color: #FFFFFF;
                    color: #000000;
                    padding: 8px;
                    border-radius: 6px;
                }
                """
            )
            body_v.addWidget(lab)
            labels.append(lab)

        body.setProperty("side", side_label)
        body.meas_labels = labels  # attach list for later updates
        vbox.addWidget(body)

        # store for later access
        if side_label.upper() == "L":
            self._meas_labels_L = labels
        else:
            self._meas_labels_R = labels

        return outer

    # ---------------- HYPOT BEHAVIOR ----------------
    def append_hypot_log(self, line: str):
        self.hypot_log.appendPlainText(line)

    def append_measurement_log(self, line: str):
        """Append a line to the measurement log area (touch/print friendly)."""
        # Create the widget lazily if layout changes occur elsewhere
        try:
            self.measurement_log.appendPlainText(line)
        except Exception:
            # Fallback: also append to hypot log if measurement log missing
            self.append_hypot_log(line)

    def _toggle_measurement_log(self):
        """Toggle visibility of the measurement log area."""
        self._log_visible = not self._log_visible
        if self._log_visible:
            self.measurement_log.show()
            self.btn_toggle_log.setText("▼ Hide Log")
        else:
            self.measurement_log.hide()
            self.btn_toggle_log.setText("▲ Show Log")

    def set_hypot_state(self, state: HypotState, message: str):
        """
        Update status label and color based on state.

        state: "ready", "running", "pass", "fail"
        message: text after "Status:"
        """
        self.hypot_status.setText(f"Status: {message}")

        if state == "ready":
            style = """
                QLabel {
                    background-color: #E0E0E0;
                    color: #000000;
                    border-radius: 4px;
                    padding: 6px;
                }
            """
        elif state == "running":
            style = """
                QLabel {
                    background-color: #FFF3CD;
                    color: #856404;
                    border-radius: 4px;
                    padding: 6px;
                }
            """
        elif state == "pass":
            style = """
                QLabel {
                    background-color: #C8E6C9;
                    color: #1B5E20;
                    border-radius: 4px;
                    padding: 6px;
                }
            """
        elif state == "fail":
            style = """
                QLabel {
                    background-color: #FFCDD2;
                    color: #B71C1C;
                    border-radius: 4px;
                    padding: 6px;
                }
            """
        else:
            style = ""

        self.hypot_status.setStyleSheet(style)

    # Convenience helpers for typical flow
    def hypot_ready(self):
        self.set_hypot_state("ready", "READY")
        self.append_hypot_log("Hypot Ready...")

    def hypot_running(self):
        self.set_hypot_state("running", "IN PROGRESS")
        self.append_hypot_log("Hypot in progress...")

    def hypot_result(self, passed: bool):
        if passed:
            self.set_hypot_state("pass", "PASS")
            self.append_hypot_log("Hypot PASS.")
        else:
            self.set_hypot_state("fail", "FAIL")
            self.append_hypot_log("Hypot FAIL.")

    # ---------------- MEASURING BEHAVIOR ----------------
    def update_measurement(
        self,
        side: Literal["L", "R"],
        row_index: int,
        text: str,
        passed: Optional[bool] = None,
    ):
        """
        Update one of the measurement rows.

        side: "L" or "R"
        row_index: 0, 1, or 2
        text: e.g. "Pin 1 to 6: 12.34 Ω"
        passed: True -> green, False -> red, None -> neutral
        """
        if side.upper() == "L":
            labels = getattr(self, "_meas_labels_L", [])
        else:
            labels = getattr(self, "_meas_labels_R", [])

        if not (0 <= row_index < len(labels)):
            return

        lab = labels[row_index]
        lab.setText(text)

        if passed is True:
            style = """
                QLabel {
                    background-color: #C8E6C9;
                    color: #1B5E20;
                    padding: 8px;
                    border-radius: 6px;
                }
            """
        elif passed is False:
            style = """
                QLabel {
                    background-color: #FFCDD2;
                    color: #B71C1C;
                    padding: 8px;
                    border-radius: 6px;
                }
            """
        else:
            style = """
                QLabel {
                    background-color: #FFFFFF;
                    color: #000000;
                    padding: 8px;
                    border-radius: 6px;
                }
            """
        lab.setStyleSheet(style)

    # ---------------- NEW: connection confirmation API ----------------
    def confirm_ready_to_test(self) -> bool:
        """
        Ask the operator to confirm all connections are made and the unit is ready.
        Returns True if operator confirms, False otherwise.

        Typical usage (TestRunner or caller):
            if main_window.confirm_ready_to_test():
                proceed_with_test()
        Also emits the `readyToStart` signal when confirmed.
        """
        resp = QMessageBox.question(
            self,
            "Confirm Connections",
            "Are all connections made and is the unit ready to be tested?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.append_hypot_log("Operator confirmed: unit ready")
            self.readyToStart.emit()
            return True

        self.append_hypot_log("Operator did NOT confirm readiness")
        return False

    def confirm_retry_test(self, test_section: str, error_msg: str) -> bool:
        """
        Ask the operator if they want to retry after a test failure.
        
        Args:
            test_section: Name of the section that failed (e.g., "Hipot", "Measurement")
            error_msg: Brief description of the error
            
        Returns:
            True if operator wants to retry, False if they want to exit
        """
        resp = QMessageBox.critical(
            self,
            f"{test_section} Test Failed",
            f"{test_section} test failed:\n\n{error_msg}\n\nDo you want to retry the test?",
            QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Retry,
        )
        
        if resp == QMessageBox.StandardButton.Retry:
            self.append_hypot_log(f"Operator chose to RETRY {test_section} test")
            return True
        else:
            self.append_hypot_log(f"Operator chose to EXIT after {test_section} failure")
            return False

    # ---------------- NEW: debug dialog integration ----------------
    def _on_debug_clicked(self):
        """
        Create and show the DebugDialog. Modify the `actions` dict below to
        change what each debug button does — this is the single central place
        to edit debug callbacks for the testing UI.
        """
        if DebugDialog is None:
            QMessageBox.warning(self, "Debug Not Available", "DebugDialog import failed or is unavailable.")
            return

        # ======== EDIT HERE: change callbacks for debug buttons ========
        # Each entry: "Label": callable(). Replace lambdas with real calls to drivers/procedures.
        actions = {
            # Hipot placeholders
            "HYPOT Relays": lambda: self.append_hypot_log("HYPOT Relays (debug)"),
            "HYPOT Test": lambda: self.append_hypot_log("HYPOT Test (debug)"),
            # MCC relays examples
            "MCC Relay 1": lambda: self.append_hypot_log("MCC Relay 1 toggled (debug)"),
            "MCC Relay 2": lambda: self.append_hypot_log("MCC Relay 2 toggled (debug)"),
            "MCC Relay 3": lambda: self.append_hypot_log("MCC Relay 3 toggled (debug)"),
            "MCC Relay 4": lambda: self.append_hypot_log("MCC Relay 4 toggled (debug)"),
            "All On": lambda: self.append_hypot_log("All On (debug)"),
            "All Off": lambda: self.append_hypot_log("All Off (debug)"),
            "Self Test Walk": lambda: self.append_hypot_log("Self Test Walk (debug)"),
        }
        # ======== end editable section ========

        dlg = DebugDialog(actions)
        dlg.exec()


# Standalone test harness (optional)
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = MainTestWindow()
    w.show()

    # Demo behavior
    w.hypot_ready()
    w.update_measurement("L", 0, "Pin 1 to 6: 12.34 Ω", True)
    w.update_measurement("R", 1, "Pin 1 to 6: 25.67 Ω", False)

    QtCore.QTimer.singleShot(2000, w.hypot_running)
    QtCore.QTimer.singleShot(4000, lambda: w.hypot_result(True))

    sys.exit(app.exec())
