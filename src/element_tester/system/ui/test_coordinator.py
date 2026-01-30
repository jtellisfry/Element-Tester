"""
Test UI Coordinator
===================

Central coordinator for managing all UI windows and state transitions during testing.
Separates UI logic from test execution logic in test_runner.py.

This coordinator:
- Manages window references (scan, config, test)
- Provides show/hide methods for each window
- Handles state transitions between screens
- Updates test progress (hipot, measurements)
- Centralizes QApplication.processEvents() calls

Usage:
    coordinator = TestCoordinator()
    coordinator.show_scan_window()
    # ... user scans WO/PN ...
    coordinator.transition_to_configuration(wo, pn)
    coordinator.transition_to_testing()
    coordinator.update_hipot_step(1, "Reset instrument", simulate=True)
"""

from typing import Optional, Callable
import time
from PyQt6 import QtWidgets


class TestCoordinator:
    """
    Coordinates all UI windows and state transitions for Element Tester.
    
    Provides a clean interface for test_runner.py to update UI without
    directly manipulating window objects.
    """
    
    def __init__(self):
        """Initialize coordinator with no windows."""
        self.scan_window = None
        self.config_window = None
        self.test_window = None
        
        # Callbacks for transitions
        self.on_scan_complete_callback: Optional[Callable] = None
        self.on_config_complete_callback: Optional[Callable] = None
        self.on_test_complete_callback: Optional[Callable] = None
    
    # ============================================================================
    # Window Management - Show/Hide
    # ============================================================================
    
    def show_scan_window(self) -> None:
        """Show the scanning window (Work Order + Part Number entry)."""
        if self.scan_window is None:
            from element_tester.system.ui.scanning import ScanWindow
            self.scan_window = ScanWindow()
        
        self.scan_window.show()
        self.scan_window.raise_()
        self.scan_window.activateWindow()
        self._process_events()
    
    def hide_scan_window(self) -> None:
        """Hide the scanning window."""
        if self.scan_window:
            self.scan_window.hide()
            self._process_events()
    
    def close_scan_window(self) -> None:
        """Close and destroy the scanning window."""
        if self.scan_window:
            self.scan_window.close()
            self.scan_window = None
            self._process_events()
    
    def show_config_window(self, work_order: str = "", part_number: str = "") -> Optional[dict]:
        """
        Show configuration window and return selected config.
        
        Args:
            work_order: Work order number (for display)
            part_number: Part number (for display)
            
        Returns:
            Dict with voltage, wattage, resistance_range or None if cancelled
        """
        try:
            from element_tester.system.ui.configuration_ui import ConfigurationWindow
            cfg = ConfigurationWindow.get_configuration(None, work_order, part_number)
            
            if cfg is None:
                return None
            
            # Parse configuration
            v = int(cfg[0])
            w = int(cfg[1])
            selected = {"voltage": v, "wattage": w}
            
            if len(cfg) > 2 and isinstance(cfg[2], (list, tuple)) and len(cfg[2]) == 2:
                selected["resistance_range"] = (float(cfg[2][0]), float(cfg[2][1]))
            else:
                selected["resistance_range"] = (0.0, 0.0)
            
            return selected
        except Exception as e:
            print(f"Error showing config window: {e}")
            return None
    
    def hide_config_window(self) -> None:
        """Hide the configuration window (if shown)."""
        # ConfigurationWindow is modal dialog, closes automatically
        self._process_events()
    
    def show_test_window(self) -> None:
        """Show the main test window (hipot + measurements)."""
        if self.test_window is None:
            from element_tester.system.ui.testing import MainTestWindow
            self.test_window = MainTestWindow()
        
        self.test_window.show()
        self.test_window.raise_()
        self.test_window.activateWindow()
        self._process_events()
    
    def hide_test_window(self) -> None:
        """Hide the test window."""
        if self.test_window:
            self.test_window.hide()
            self._process_events()
    
    def close_test_window(self) -> None:
        """Close and destroy the test window."""
        if self.test_window:
            self.test_window.close()
            self.test_window = None
            self._process_events()
    
    # ============================================================================
    # State Transitions - Orchestrate Screen Changes
    # ============================================================================
    
    def transition_to_configuration(self, work_order: str, part_number: str) -> Optional[dict]:
        """
        Transition from scanning to configuration.
        Shows config dialog (scan window stays visible in background).
        
        Returns:
            Selected configuration dict or None if cancelled
        """
        # Don't hide scan window yet - modal dialog will appear on top
        # We'll hide it in transition_to_testing() after config is confirmed
        config = self.show_config_window(work_order, part_number)
        return config
    
    def transition_to_testing(self) -> None:
        """
        Transition from configuration to testing.
        Hides scan window, shows test window, and resets test window to blank state.
        """
        self.hide_scan_window()
        self.show_test_window()
        # Reset test window to blank state for new test
        self.reset_test_window()
    
    def transition_to_scanning(self) -> None:
        """
        Transition back to scanning (after test complete or cancel).
        Hides test window, shows scan window.
        """
        self.hide_test_window()
        self.show_scan_window()
    
    def complete_test_and_return_to_scan(self) -> None:
        """
        Complete testing workflow and return to scanning.
        This is called after test passes and user clicks continue on success dialog.
        Hides test window and shows scan window.
        """
        # Hide test window
        self.hide_test_window()
        # Show scan window
        self.show_scan_window()
    
    # ============================================================================
    # Hipot Test UI Updates
    # ============================================================================
    
    def show_hipot_ready(self) -> None:
        """Show hipot in ready state (yellow light)."""
        if self.test_window:
            self.test_window.hypot_ready()
            self._process_events()
    
    def show_hipot_running(self) -> None:
        """Show hipot in running state (blue light)."""
        if self.test_window:
            self.test_window.hypot_running()
            self._process_events()
    
    def show_hipot_result(self, passed: bool) -> None:
        """
        Show hipot test result.
        
        Args:
            passed: True for pass (green), False for fail (red)
        """
        if self.test_window:
            self.test_window.hypot_result(passed)
            self._process_events()
    
    def append_hipot_log(self, message: str) -> None:
        """
        Append message to hipot log area.
        
        Args:
            message: Log message to display
        """
        if self.test_window:
            self.test_window.append_hypot_log(message)
            self._process_events()
    
    def update_hipot_step(self, step_num: int, step_message: str, simulate: bool = False) -> None:
        """
        Update hipot test with current step.
        
        Args:
            step_num: Step number (1-5)
            step_message: Description of step
            simulate: If True, append "(SIM)" to message
        """
        suffix = " (SIM)" if simulate else ""
        message = f"Step {step_num}/5: {step_message}{suffix}"
        self.append_hipot_log(message)
        time.sleep(0.8)  # Visual pacing for user
    
    # ============================================================================
    # Measurement Test UI Updates
    # ============================================================================
    
    def update_measurement(
        self, 
        side: str, 
        position: int, 
        text: str, 
        passed: Optional[bool]
    ) -> None:
        """
        Update measurement display.
        
        Args:
            side: "L" or "R"
            position: Row index (0, 1, 2)
            text: Display text (e.g., "Pin 1 to 6: 12.3 Ω" or "Pin 1 to 6: ---")
            passed: True=green, False=red, None=gray
        """
        if self.test_window:
            self.test_window.update_measurement(side, position, text, passed)
            self._process_events()
    
    def append_measurement_log(self, message: str) -> None:
        """
        Append message to measurement log area.
        
        Args:
            message: Log message to display
        """
        if self.test_window:
            try:
                self.test_window.append_measurement_log(message)
            except Exception:
                # Fallback to hipot log if measurement log not available
                self.test_window.append_hypot_log(message)
            self._process_events()
    
    def clear_measurement_values(self) -> None:
        """Clear all measurement values (for retry)."""
        if self.test_window:
            for position in range(3):
                config_names = ["Pin 1 to 6", "Pin 2 to 5", "Pin 3 to 4"]
                self.test_window.update_measurement("L", position, f"{config_names[position]}: ---", None)
                self.test_window.update_measurement("R", position, f"{config_names[position]}: ---", None)
            self._process_events()
    
    def reset_test_window(self) -> None:
        """
        Reset test window to initial state.
        Clears hipot status and all measurement values.
        Called when starting a new test.
        """
        if self.test_window:
            # Reset hipot to ready state
            self.test_window.set_hypot_state("ready", "READY")
            
            # Clear all measurement values
            for position in range(3):
                config_names = ["Pin 1 to 6", "Pin 2 to 5", "Pin 3 to 4"]
                self.test_window.update_measurement("L", position, f"{config_names[position]}: ---", None)
                self.test_window.update_measurement("R", position, f"{config_names[position]}: ---", None)
            
            # Clear logs if method exists
            if hasattr(self.test_window, 'clear_hipot_log'):
                try:
                    self.test_window.clear_hipot_log()
                except Exception:
                    pass
            
            if hasattr(self.test_window, 'clear_measurement_log'):
                try:
                    self.test_window.clear_measurement_log()
                except Exception:
                    pass
            
            self._process_events()
    
    # ============================================================================
    # Dialog Prompts
    # ============================================================================
    
    def show_ready_prompt(self) -> bool:
        """
        Show "Ready to Test" dialog with Continue/Exit buttons.
        
        Returns:
            True if user clicked Continue, False if Exit
        """
        try:
            from element_tester.system.widgets.continue_exit import ContinueExitDialog
            return ContinueExitDialog.show_prompt(
                parent=self.test_window,
                title="Ready to Test",
                message="Ready to begin testing?\n\nPress CONTINUE to start or EXIT to cancel."
            )
        except Exception:
            # Fallback if widget not available
            return True
    
    def show_retry_prompt(self, test_type: str, failure_message: str) -> bool:
        """
        Show retry dialog after test failure.
        
        Args:
            test_type: "Hipot Test" or "Measurement Test"
            failure_message: Reason for failure
            
        Returns:
            True if user wants to retry, False if exit
        """
        try:
            from element_tester.system.widgets.continue_exit import ContinueExitDialog
            return ContinueExitDialog.show_prompt(
                parent=self.test_window,
                title=f"{test_type} Failed",
                message=f"Test failed: {failure_message}\n\nPress CONTINUE to retry or EXIT to cancel."
            )
        except Exception:
            return False
    
    def show_test_passed_dialog(self, work_order: str, part_number: str) -> None:
        """
        Show "Test Passed" success dialog.
        
        Args:
            work_order: Work order number
            part_number: Part number
        """
        try:
            from element_tester.system.widgets.test_passed import TestPassedDialog
            try:
                TestPassedDialog.show_passed(parent=self.test_window, work_order=work_order, part_number=part_number)
            except TypeError:
                # Fallback if older signature present
                TestPassedDialog.show_passed(parent=self.test_window)
        except Exception as e:
            print(f"Could not show test passed dialog: {e}")
    
    def show_hipot_failed_dialog(self, failure_message: str) -> str:
        """
        Show hipot test failure dialog with Retry/Continue/Exit options.
        
        Args:
            failure_message: Reason for hipot failure
            
        Returns:
            "CONTINUE", "RETRY", or "EXIT" based on operator choice
        """
        try:
            from element_tester.system.widgets.continue_retry_exit import ContinueRetryExitDialog
            return ContinueRetryExitDialog.show_prompt(
                parent=self.test_window,
                title="Hipot Test Failed",
                message=f"Test failed: {failure_message}\n\nPress RETRY to re-test, CONTINUE to skip, or EXIT to cancel."
            )
        except Exception:
            # Fallback
            return "EXIT"
    
    # ============================================================================
    # Utility Methods
    # ============================================================================
    
    def _process_events(self) -> None:
        """Process Qt events to keep UI responsive."""
        QtWidgets.QApplication.processEvents()
    
    def get_test_window(self):
        """Get reference to test window (for test_runner backward compatibility)."""
        return self.test_window
    
    def cleanup(self) -> None:
        """Hide all windows and clean up resources."""
        self.hide_test_window()
        self.hide_scan_window()
        self._process_events()
