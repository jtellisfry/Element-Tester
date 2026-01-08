from __future__ import annotations
from typing import Tuple
from PyQt6 import QtWidgets, QtCore, QtGui


class TouchSelector(QtWidgets.QWidget):
    """A touch-friendly selector: large left/right buttons and a central value display.

    Keeps a hidden QComboBox as the data store so callers can use `currentData()`.
    """

    def __init__(self, items: Tuple[int, ...], parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._items = list(items)
        self._combo = QtWidgets.QComboBox()
        for it in self._items:
            self._combo.addItem(str(it), it)
        self._combo.setCurrentIndex(0)

        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(12)

        self.btn_prev = QtWidgets.QPushButton("❮")
        self.btn_next = QtWidgets.QPushButton("❯")
        self.btn_prev.setMinimumSize(64, 64)
        self.btn_next.setMinimumSize(64, 64)
        self.btn_prev.setFont(self._big_font(22))
        self.btn_next.setFont(self._big_font(22))
        self.btn_prev.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.btn_next.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.value_label = QtWidgets.QLabel(str(self._items[0]))
        self.value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumWidth(180)
        self.value_label.setMinimumHeight(64)
        self.value_label.setFont(self._big_font(20))
        self.value_label.setStyleSheet("color: #2E0B46;")

        h.addWidget(self.btn_prev)
        h.addWidget(self.value_label, stretch=1)
        h.addWidget(self.btn_next)

        self.btn_prev.clicked.connect(self._decrement)
        self.btn_next.clicked.connect(self._increment)

        # keep hidden combo for API compatibility
        self._combo.hide()

    def _big_font(self, pts: int) -> QtGui.QFont:
        f = QtGui.QFont()
        f.setPointSize(pts)
        f.setBold(True)
        return f

    def _increment(self):
        idx = self._combo.currentIndex()
        idx = (idx + 1) % len(self._items)
        self._combo.setCurrentIndex(idx)
        self.value_label.setText(str(self._items[idx]))

    def _decrement(self):
        idx = self._combo.currentIndex()
        idx = (idx - 1) % len(self._items)
        self._combo.setCurrentIndex(idx)
        self.value_label.setText(str(self._items[idx]))

    # API compatibility methods
    def currentData(self):
        return self._combo.currentData()

    def currentIndex(self):
        return self._combo.currentIndex()

    def setCurrentIndex(self, idx: int):
        self._combo.setCurrentIndex(idx)
        self.value_label.setText(str(self._items[idx]))

class ConfigurationWindow(QtWidgets.QDialog):
    """Configuration form shown after scanning WO/PN.

    - Choose element voltage and wattage from predefined tuples
    - Emits `configConfirmed(voltage, wattage)` when Continue pressed
    """

    configConfirmed = QtCore.pyqtSignal(int, int)

    VOLTAGE_OPTIONS: Tuple[int, ...] = (115,208,220,230,240,440,480)
    WATTAGE_OPTIONS: Tuple[int, ...] = (7000,7500,8000,8500,9000,11000,12800,14000)

    # Manual mapping: keys are (voltage, wattage) tuples, values are (r_min_ohm, r_max_ohm).
    # Populate this mapping with the exact ranges you want for each combo.
    RESISTANCE_RANGE: dict[tuple[int, int], tuple[float, float]] = {
        (208, 7000): (18.2/2, 19.6/2),
        (230, 7000): (0.0/2, 0.0/2),
        (240, 7000): (11.0/2, 11.9/2),
        (480, 7000): (90.2/2, 91.2/2),
        (208, 8500): (15.0/2, 16.6/2),
        (230, 8500): (18.0/2, 19.6/2),
        (240, 8500): (19.5/2, 21.5/2),
        (480, 8500): (79.8/2, 82.5/2),
    }

    def __init__(self, work_order: str, part_number: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.work_order = work_order
        self.part_number = part_number
        self.setWindowTitle("Configuration")
        self.resize(700, 420)
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(24)

        # Header
        header = QtWidgets.QLabel("Configuration")
        f = header.font()
        f.setPointSize(36)
        f.setBold(True)
        header.setFont(f)
        header.setText(header.text().upper())
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        header.setMinimumHeight(80)
        header.setStyleSheet(
            "background-color: #6A1B9A; color: white; padding: 8px; border-radius: 6px;"
        )
        root.addWidget(header)
        # Create visually prominent, rounded bars for the two fields.
        # Each bar contains a centered label and the combo box (combo is visually embedded).
        def _make_field(title: str, items: Tuple[int, ...]) -> tuple[QtWidgets.QWidget, TouchSelector]:
            container = QtWidgets.QWidget()
            container.setMinimumHeight(120)
            container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            container.setStyleSheet(
                "background-color: #D6B3FF; border-radius: 12px;"
            )
            lay = QtWidgets.QVBoxLayout(container)
            lay.setContentsMargins(16, 12, 16, 12)

            label = QtWidgets.QLabel(title)
            lf = label.font()
            lf.setPointSize(18)
            lf.setBold(True)
            label.setFont(lf)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #2E0B46;")

            selector = TouchSelector(items)

            lay.addWidget(label)
            lay.addWidget(selector, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            return container, selector

        v_widget, self.voltage_combo = _make_field("Element Voltage", self.VOLTAGE_OPTIONS)
        w_widget, self.wattage_combo = _make_field("Element Wattage", self.WATTAGE_OPTIONS)

        # Add a bit of spacing between the bars
        root.addWidget(v_widget)
        root.addSpacing(10)
        root.addWidget(w_widget)
        
        # Resistance range label (touch-friendly large text)
        self.range_label = QtWidgets.QLabel("")
        rf = self.range_label.font()
        rf.setPointSize(16)
        rf.setBold(True)
        self.range_label.setFont(rf)
        self.range_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.range_label.setStyleSheet("color: #FFFFFF;")
        root.addSpacing(8)
        root.addWidget(self.range_label)

        # Wire selector buttons to update the computed resistance label
        try:
            self.voltage_combo.btn_prev.clicked.connect(self._update_resistance_label)
            self.voltage_combo.btn_next.clicked.connect(self._update_resistance_label)
            self.wattage_combo.btn_prev.clicked.connect(self._update_resistance_label)
            self.wattage_combo.btn_next.clicked.connect(self._update_resistance_label)
        except Exception:
            # If selectors are not TouchSelector (fallback), ignore
            pass

        # Initialize the label text
        self._update_resistance_label()

        # Spacer
        root.addStretch(1)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_continue = QtWidgets.QPushButton("CONTINUE")
        self.btn_exit = QtWidgets.QPushButton("EXIT")
        self._style_main_button(self.btn_continue, bg="#4CAF50")
        self._style_main_button(self.btn_exit, bg="#C62828")

        btn_row.addWidget(self.btn_continue)
        btn_row.addSpacing(20)
        btn_row.addWidget(self.btn_exit)
        btn_row.addStretch(1)

        root.addLayout(btn_row)

        # Signals
        self.btn_continue.clicked.connect(self._on_continue)
        self.btn_exit.clicked.connect(self.reject)

    def _style_main_button(self, btn: QtWidgets.QPushButton, bg: str = "#4CAF50"):
        btn.setMinimumWidth(140)
        btn.setMinimumHeight(44)
        f = btn.font()
        f.setPointSize(12)
        f.setBold(True)
        btn.setFont(f)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: white; border-radius: 8px; padding: 8px 16px; }}"
        )

    def _on_continue(self):
        v = int(self.voltage_combo.currentData())
        w = int(self.wattage_combo.currentData())
        # Emit configuration and close dialog with Accepted
        self.configConfirmed.emit(v, w)
        self.accept()

    def _compute_resistance_range(self, voltage: int, wattage: int) -> tuple[float, float]:
        """Return (r_min, r_max) in ohms for the given voltage and wattage.
        Uses `RESISTANCE_OVERRIDES` if present. If no mapping exists, returns (0.0, 0.0).
        """
        key = (int(voltage), int(wattage))
        return self.RESISTANCE_RANGE.get(key, (0.0, 0.0))

    def _update_resistance_label(self):
        try:
            v = int(self.voltage_combo.currentData())
            w = int(self.wattage_combo.currentData())
        except Exception:
            # fallback to first options
            v = int(self.VOLTAGE_OPTIONS[0])
            w = int(self.WATTAGE_OPTIONS[0])
        rmin, rmax = self._compute_resistance_range(v, w)
        if rmin == 0.0 and rmax == 0.0:
            self.range_label.setText(f"Resistance range: not configured for {v} V / {w} W")
        else:
            self.range_label.setText(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")

    @classmethod
    def get_configuration(cls, parent: QtWidgets.QWidget | None, wo: str, pn: str) -> tuple[int, int] | None:
        dlg = cls(wo, pn, parent)
        res = dlg.exec()
        if res == QtWidgets.QDialog.DialogCode.Accepted:
            v = int(dlg.voltage_combo.currentData())
            w = int(dlg.wattage_combo.currentData())
            rmin, rmax = dlg._compute_resistance_range(v, w)
            return int(v), int(w), (float(rmin), float(rmax))
        return None


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    def _on_configured(v: int, w: int):
        print(f"Selected configuration: {v} V, {w} W")

    # Show dialog for manual inspection
    dlg = ConfigurationWindow("DEMO_WO", "DEMO_PN")
    dlg.configConfirmed.connect(_on_configured)
    dlg.show()

    sys.exit(app.exec())
