"""
Continue/Exit dialog widget for operator confirmation.
Simple large button dialog for continuing or exiting the program.
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt


class ContinueExitDialog(QtWidgets.QDialog):
    """
    Large continue/exit confirmation dialog.
    Shows CONTINUE (green) and EXIT (gray) buttons side by side.
    """
    
    def __init__(self, parent=None, title: str = "Ready to Test", message: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(700, 400)
        
        # Result for caller
        self.continue_selected = False
        
        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Optional message at top
        if message:
            msg_label = QtWidgets.QLabel(message)
            msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg_label.setStyleSheet(
                "font-size: 24px;"
                "padding: 40px;"
                "background-color: white;"
                "color: black;"
            )
            msg_label.setWordWrap(True)
            layout.addWidget(msg_label)
        
        # Button row
        button_widget = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)
        
        # Continue button (green)
        continue_btn = QtWidgets.QPushButton("CONTINUE")
        continue_btn.setMinimumHeight(300)
        continue_btn.setStyleSheet(
            "background-color: #4CAF50;"
            "color: white;"
            "font-size: 64px;"
            "font-weight: bold;"
            "border: 2px solid #45a049;"
        )
        continue_btn.clicked.connect(self._on_continue)
        
        # Exit button (gray/beige)
        exit_btn = QtWidgets.QPushButton("EXIT")
        exit_btn.setMinimumHeight(300)
        exit_btn.setStyleSheet(
            "background-color: #D5C5C5;"
            "color: white;"
            "font-size: 64px;"
            "font-weight: bold;"
            "border: 2px solid #B5A5A5;"
        )
        exit_btn.clicked.connect(self._on_exit)
        
        button_layout.addWidget(continue_btn)
        button_layout.addWidget(exit_btn)
        
        layout.addWidget(button_widget)
    
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
