# ============================================================================
# element_tester.system.widgets Package
# ============================================================================
#
# Reusable PyQt6 UI widgets (placeholder for future development).
#
# PURPOSE:
# - Custom PyQt6 widgets used across multiple UI modules
# - Example: StatusIndicator, LogViewer, ConnectionStatusWidget
# - Promotes code reuse and consistent UI/UX
#
# INTENDED STRUCTURE:
# - status_indicator.py : LED-style status indicator widget
# - log_viewer.py       : Enhanced log display with filtering
# - connection_widget.py : Connection status and controls
# - result_display.py   : Test result display widget
#
# HOW TO IMPLEMENT:
# - Each widget should be a PyQt6 QWidget subclass
# - Make widgets configurable via constructor parameters or properties
# - Use signals/slots for communication with parent windows
# - Add examples in widget docstrings or __main__ blocks
#
# EXAMPLE WIDGET:
# ```python
# from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
# from PyQt6.QtCore import pyqtSignal
#
# class StatusIndicator(QWidget):
#     statusChanged = pyqtSignal(str)
#     
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.label = QLabel(\"●\")
#         layout = QHBoxLayout(self)
#         layout.addWidget(self.label)
#     
#     def set_status(self, status: str):
#         colors = {\"ok\": \"green\", \"error\": \"red\", \"idle\": \"gray\"}
#         self.label.setStyleSheet(f\"color: {colors.get(status, 'gray')};\")
#         self.statusChanged.emit(status)
# ```
#
# HOW TO MODIFY:
# - Add new widgets as separate modules
# - Export widgets for easy import:
#     from .status_indicator import StatusIndicator
#     from .log_viewer import LogViewer
#     __all__ = [\"StatusIndicator\", \"LogViewer\"]
# - Keep widgets generic and reusable—avoid hard-coding business logic
# ============================================================================
