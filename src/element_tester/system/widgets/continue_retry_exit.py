"""
Continue/Retry/Exit dialog widget for hipot test confirmation.
Stylish large button dialog with rounded corners and modern design.
Includes middle RETRY button for re-running the hipot test.
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt


class ContinueRetryExitDialog(QtWidgets.QDialog):
    """
    Large continue/retry/exit confirmation dialog for hipot testing.
    Shows CONTINUE (green), RETRY (orange), and EXIT (red) buttons with rounded corners.
    Matches the visual style of the index.py design.
    """
    
    # Return values for the dialog
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    EXIT = "EXIT"
    
    def __init__(self, parent=None, title: str = "Hipot Test Result", message: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(800, 500)
        
        # Result for caller
        self.result = None
        
        # Background color matching index.py (#c4c4c4)
        self.setStyleSheet("""
            QDialog {
                background-color: #c4c4c4;
            }
        """)
        
        # Main layout with margins
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(35, 45, 35, 35)
        layout.setSpacing(40)
        
        # Top message panel (light gray with border, rounded)
        msg_frame = QtWidgets.QFrame()
        msg_frame.setFixedHeight(165)
        msg_frame.setStyleSheet("""
            QFrame {
                background-color: #e6e6e6;
                border: 2px solid #303030;
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
                    color: #303030;
                    background-color: transparent;
                    border: none;
                }
            """)
            msg_label.setWordWrap(True)
            msg_layout.addWidget(msg_label)
        
        layout.addWidget(msg_frame)
        
        # Button row
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(35)
        
        # Continue button (green) - #35ad5d from reference
        continue_btn = QtWidgets.QPushButton("CONTINUE")
        continue_btn.setFixedSize(220, 140)
        continue_btn.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #35ad5d;
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
                border: 2px solid #303030;
                border-radius: 10px;
            }
            QPushButton:hover {
                border: 2px solid #111111;
                background-color: #2d8a4a;
            }
            QPushButton:pressed {
                background-color: #247038;
            }
        """)
        continue_btn.clicked.connect(self._on_continue)
        
        # Retry button (orange/yellow) - #dea21c from reference
        retry_btn = QtWidgets.QPushButton("RETRY")
        retry_btn.setFixedSize(220, 140)
        retry_btn.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #dea21c;
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
                border: 2px solid #303030;
                border-radius: 10px;
            }
            QPushButton:hover {
                border: 2px solid #111111;
                background-color: #c08f18;
            }
            QPushButton:pressed {
                background-color: #a27814;
            }
        """)
        retry_btn.clicked.connect(self._on_retry)
        
        # Exit button (red) - #e23228 from reference
        exit_btn = QtWidgets.QPushButton("EXIT")
        exit_btn.setFixedSize(220, 140)
        exit_btn.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #e23228;
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
                border: 2px solid #303030;
                border-radius: 10px;
            }
            QPushButton:hover {
                border: 2px solid #111111;
                background-color: #c72921;
            }
            QPushButton:pressed {
                background-color: #a8221b;
            }
        """)
        exit_btn.clicked.connect(self._on_exit)
        
        button_layout.addWidget(continue_btn)
        button_layout.addWidget(retry_btn)
        button_layout.addWidget(exit_btn)
        
        layout.addLayout(button_layout)
    
    def _on_continue(self):
        """Operator chose to continue."""
        self.result = self.CONTINUE
        self.accept()
    
    def _on_retry(self):
        """Operator chose to retry the hipot test."""
        self.result = self.RETRY
        self.accept()
    
    def _on_exit(self):
        """Operator chose to exit."""
        self.result = self.EXIT
        self.reject()
    
    @staticmethod
    def show_prompt(
        parent=None,
        title: str = "Hipot Test Result",
        message: str = ""
    ) -> str:
        """
        Show the dialog and return the operator's choice.
        
        Args:
            parent: Parent widget
            title: Dialog window title
            message: Optional message to display above buttons
            
        Returns:
            ContinueRetryExitDialog.CONTINUE - Operator chose to continue
            ContinueRetryExitDialog.RETRY - Operator chose to retry the hipot test
            ContinueRetryExitDialog.EXIT - Operator chose to exit
        
        Example:
            result = ContinueRetryExitDialog.show_prompt(
                parent=self,
                title="Hipot Test Failed",
                message="The hipot test did not pass. Retry the test or exit?"
            )
            if result == ContinueRetryExitDialog.RETRY:
                # Re-run the hipot test
                pass
            elif result == ContinueRetryExitDialog.CONTINUE:
                # Continue to next step
                pass
            else:  # EXIT
                # Exit the test sequence
                pass
        """
        dialog = ContinueRetryExitDialog(parent=parent, title=title, message=message)
        dialog.exec()
        return dialog.result if dialog.result else ContinueRetryExitDialog.EXIT
