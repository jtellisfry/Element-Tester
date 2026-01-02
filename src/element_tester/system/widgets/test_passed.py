"""
Test Passed Dialog Widget

Shows a success screen when both hipot and measurement tests pass.
Displays "PASS" with green styling and a CONTINUE button.
"""
from PyQt6 import QtWidgets, QtCore, QtGui


class TestPassedDialog(QtWidgets.QDialog):
    """Dialog shown when test passes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Passed")
        self.setModal(True)
        self.setMinimumSize(400, 300)
        
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # PASS label
        pass_label = QtWidgets.QLabel("PASS")
        pass_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        pass_label.setStyleSheet("""
            QLabel {
                color: #2ecc71;
                font-size: 72px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(pass_label)
        
        # Success icon/checkmark
        check_label = QtWidgets.QLabel("✓")
        check_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        check_label.setStyleSheet("""
            QLabel {
                color: #2ecc71;
                font-size: 96px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(check_label)
        
        # Success message
        message_label = QtWidgets.QLabel("All tests completed successfully")
        message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("""
            QLabel {
                color: #27ae60;
                font-size: 18px;
                font-weight: 500;
            }
        """)
        layout.addWidget(message_label)
        
        # Spacer
        layout.addStretch()
        
        # Continue button
        continue_btn = QtWidgets.QPushButton("CONTINUE")
        continue_btn.setMinimumHeight(60)
        continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-size: 20px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        continue_btn.clicked.connect(self.accept)
        layout.addWidget(continue_btn)
        
        # Set dialog background
        self.setStyleSheet("""
            QDialog {
                background-color: #ecf0f1;
            }
        """)
        
        self.setLayout(layout)
    
    @staticmethod
    def show_passed(parent=None, work_order: str | None = None, part_number: str | None = None) -> bool:
        """
        Show the test passed dialog and optionally schedule a QC print.

        If `work_order` and `part_number` are provided and the `print_qc`
        helper is available, this schedules `print_qc.print_message()` to
        run 1 second after the dialog is shown (so printing occurs while the
        dialog is visible).

        Returns:
            True when user clicks CONTINUE
        """
        dialog = TestPassedDialog(parent)

        # Schedule QC print 1s after dialog is shown (if possible)
        if work_order and part_number:
            try:
                import element_tester.system.procedures.print_qc as print_qc  # local import

                def _do_print():
                    try:
                        # QTimer already enforces the 1s delay below; call with no extra delay
                        print_qc.print_message(work_order, part_number, delay_s=0.0)
                    except Exception:
                        pass

                QtCore.QTimer.singleShot(1000, _do_print)
            except Exception:
                # If helper not available, ignore silently
                pass

        result = dialog.exec()
        return result == QtWidgets.QDialog.DialogCode.Accepted
