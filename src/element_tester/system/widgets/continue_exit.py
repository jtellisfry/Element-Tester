"""
Continue/Exit dialog widget for operator confirmation.
Stylish large button dialog with rounded corners and modern design.
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt


class ContinueExitDialog(QtWidgets.QDialog):
    """
    Large continue/exit confirmation dialog.
    Shows CONTINUE (green) and EXIT (red) buttons with rounded corners.
    Matches the visual style of the index.py design.
    """
    
    def __init__(self, parent=None, title: str = "Ready to Test", message: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(800, 450)
        
        # Result for caller
        self.continue_selected = False
        
        # Background color matching index.py (#bfbfbf)
        self.setStyleSheet("""
            QDialog {
                background-color: #bfbfbf;
            }
        """)
        
        # Main layout with margins
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(30)
        
        # Top message panel (light gray with border, rounded)
        msg_frame = QtWidgets.QFrame()
        msg_frame.setFixedHeight(145)
        msg_frame.setStyleSheet("""
            QFrame {
                background-color: #ececec;
                border: 2px solid #2b2b2b;
                border-radius: 10px;
            }
        """)
        
        msg_layout = QtWidgets.QVBoxLayout(msg_frame)
        msg_layout.setContentsMargins(20, 20, 20, 20)
        
        # Message text
        if message:
            msg_label = QtWidgets.QLabel(message)
            msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-family: 'Segoe UI';
                    color: #2b2b2b;
                    background-color: transparent;
                    border: none;
                }
            """)
            msg_label.setWordWrap(True)
            msg_layout.addWidget(msg_label)
        
        layout.addWidget(msg_frame)
        
        # Button row
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(95)
        
        # Continue button (green) - matching index.py #36a854
        continue_btn = QtWidgets.QPushButton("CONTINUE")
        continue_btn.setFixedSize(330, 140)
        continue_btn.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #36a854;
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Segoe UI';
                border: 2px solid #2b2b2b;
                border-radius: 10px;
            }
            QPushButton:hover {
                border: 2px solid #111111;
                background-color: #2d8a43;
            }
            QPushButton:pressed {
                background-color: #247036;
            }
        """)
        continue_btn.clicked.connect(self._on_continue)
        
        # Exit button (red) - matching index.py #e13228
        exit_btn = QtWidgets.QPushButton("EXIT")
        exit_btn.setFixedSize(330, 140)
        exit_btn.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #e13228;
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Segoe UI';
                border: 2px solid #2b2b2b;
                border-radius: 10px;
            }
            QPushButton:hover {
                border: 2px solid #111111;
                background-color: #c72a21;
            }
            QPushButton:pressed {
                background-color: #a8231b;
            }
        """)
        exit_btn.clicked.connect(self._on_exit)
        
        button_layout.addWidget(continue_btn)
        button_layout.addWidget(exit_btn)
        
        layout.addLayout(button_layout)
    
    def _on_continue(self):
        """Operator chose to continue."""
        self.continue_selected = True
        self.accept()
    
    def _on_exit(self):
        """Operator chose to exit."""
        self.continue_selected = False
        self.reject()
    
    @staticmethod
    def show_prompt(
        parent=None,
        title: str = "Ready to Test",
        message: str = ""
    ) -> bool:
        """
        Show the dialog and return True if operator chose Continue, False if Exit.
        
        Args:
            parent: Parent widget
            title: Dialog window title
            message: Optional message to display above buttons
            
        Returns:
            True if Continue clicked, False if Exit clicked
        """
        dialog = ContinueExitDialog(parent, title, message)
        dialog.exec()
        return dialog.continue_selected
