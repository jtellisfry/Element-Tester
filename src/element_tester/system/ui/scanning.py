# scanning.py
from __future__ import annotations
from typing import Optional

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QMessageBox

try:
    from element_tester.system.ui.debug import DebugDialog
except Exception:
    DebugDialog = None


class ScanWindow(QtWidgets.QWidget):
    """
    First screen shown on startup.

    - Scan Work Order Number
    - Scan Part Number
    - START → emits scanCompleted(work_order, part_number)
    - EXIT  → closes program
    """

    scanCompleted = QtCore.pyqtSignal(str, str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Scan Work Order / Part Number")
        self.resize(900, 520)
        self._build_ui()
        self._wire_signals()

    # ---------------- UI ----------------
    def _build_ui(self):
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#D9D9D9"))
        self.setPalette(pal)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(32)

        # ---- Scan Work Order ----
        self.work_header = self._make_header_label("Scan Work Order Number")
        root.addWidget(self.work_header)

        self.work_edit = self._make_input_line()
        wo_row = QtWidgets.QHBoxLayout()
        wo_row.addStretch(1)
        wo_row.addWidget(self.work_edit, 3)
        wo_row.addStretch(1)
        root.addLayout(wo_row)

        root.addSpacing(24)

        # ---- Scan Part Number ----
        self.part_header = self._make_header_label("Scan Part Number:")
        root.addWidget(self.part_header)

        self.part_edit = self._make_input_line()
        pn_row = QtWidgets.QHBoxLayout()
        pn_row.addStretch(1)
        pn_row.addWidget(self.part_edit, 3)
        pn_row.addStretch(1)
        root.addLayout(pn_row)

        root.addStretch(1)

        # ---- Bottom Buttons: START / EXIT ----
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_start = QtWidgets.QPushButton("START")
        self.btn_exit = QtWidgets.QPushButton("EXIT")

        self._style_main_button(self.btn_start, bg="#4CAF50")
        self._style_main_button(self.btn_exit, bg="#C62828")

        self.btn_start.setEnabled(False)   # enabled once both fields filled

        btn_row.addWidget(self.btn_start)
        btn_row.addSpacing(20)
        btn_row.addWidget(self.btn_exit)

        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # ---- Revision Date (bottom left) ----
        revision_row = QtWidgets.QHBoxLayout()
        self.revision_label = QtWidgets.QLabel("Last Revision: January 9, 2026 | 11:39AM")
        self.revision_label.setStyleSheet(
            """
            QLabel {
                background-color: #FFFFFF;
                color: #000000;
                padding: 4px 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            """
        )
        f = self.revision_label.font()
        f.setPointSize(10)
        self.revision_label.setFont(f)
        revision_row.addWidget(self.revision_label)
        revision_row.addStretch(1)
        root.addLayout(revision_row)

        QtCore.QTimer.singleShot(0, self.work_edit.setFocus)

    # ---------------- Helpers ----------------
    def _make_header_label(self, text: str) -> QtWidgets.QLabel:
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

    def _make_input_line(self) -> QtWidgets.QLineEdit:
        edit = QtWidgets.QLineEdit()
        edit.setPlaceholderText("Value")
        f = edit.font()
        f.setPointSize(16)
        edit.setFont(f)
        edit.setMinimumHeight(40)
        edit.setStyleSheet(
            """
            QLineEdit {
                background-color: #FFFFFF;
                color: #000000;
                border-radius: 8px;
                border: 2px solid #CCCCCC;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border: 2px solid #4A90E2;
            }
            """
        )
        return edit

    def _style_main_button(self, btn: QtWidgets.QPushButton, bg: str):
        btn.setMinimumWidth(160)
        btn.setMinimumHeight(45)
        f = btn.font()
        f.setPointSize(16)
        f.setBold(True)
        btn.setFont(f)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border-radius: 10px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{
                background-color: {bg}CC;
            }}
            QPushButton:disabled {{
                background-color: #999999;
            }}
            """
        )

    # ---------------- Logic ----------------
    def _wire_signals(self):
        self.work_edit.returnPressed.connect(self._focus_part)
        self.part_edit.returnPressed.connect(self._emit_scan_completed)

        # Enable START when both fields have values
        self.work_edit.textChanged.connect(self._check_ready)
        self.part_edit.textChanged.connect(self._check_ready)

        # Button actions
        self.btn_start.clicked.connect(self._emit_scan_completed)
        self.btn_exit.clicked.connect(self._exit_app)
        # Optional debug button (only if present in UI)
        btn_dbg = getattr(self, "btn_debug", None)
        if btn_dbg is not None:
            btn_dbg.clicked.connect(self._on_debug_clicked)

    def _focus_part(self):
        self.part_edit.setFocus()
        self.part_edit.selectAll()

    def _check_ready(self):
        wo = self.work_edit.text().strip()
        pn = self.part_edit.text().strip()
        self.btn_start.setEnabled(bool(wo and pn))

    def clear_fields(self):
        """Clear both input fields and reset START button state."""
        self.work_edit.clear()
        self.part_edit.clear()
        self.btn_start.setEnabled(False)
        self.work_edit.setFocus()

    def showEvent(self, event):
        """Override showEvent to clear fields whenever window is shown."""
        super().showEvent(event)
        self.clear_fields()

    def _emit_scan_completed(self):
        wo = self.work_edit.text().strip()
        pn = self.part_edit.text().strip()
        if not wo or not pn:
            QtWidgets.QMessageBox.warning(self, "Missing Data",
                "Please scan both the Work Order and Part Number.")
            return

        # Emit to whoever is listening
        self.scanCompleted.emit(wo, pn)

    def _exit_app(self):
        QtWidgets.QApplication.quit()

    def _on_debug_clicked(self):
        if DebugDialog is None:
            QMessageBox.warning(self, "Debug Not Available", "DebugDialog import failed or is unavailable.")
            return

        actions = { "Placeholder": lambda: None }
        dlg = DebugDialog(actions)
        dlg.exec()  # <-- This shows the dialog modally


# Standalone tester
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = ScanWindow()

    def dbg(wo, pn):
        print("Scan Completed:", wo, pn)

    w.scanCompleted.connect(dbg)
    w.show()
    sys.exit(app.exec())
