from __future__ import annotations
from typing import Optional, Tuple
from pathlib import Path
import logging
import time
import json
from datetime import datetime
import sys
import concurrent.futures


# Make sure .../src is on sys.path so `element_tester` is importable
SRC_ROOT = Path(__file__).resolve().parents[3]  # .../Element_Tester/src
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from element_tester.system.ui.test_coordinator import TestCoordinator
from PyQt6 import QtWidgets  # For QApplication.processEvents()

# Optional hipot driver (still supports simulate mode if missing)
try:
    from element_tester.system.drivers.hypot3865.procedures import AR3865Procedures, HipotConfig
    from element_tester.system.drivers.hypot3865.driver import AR3865Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import AR3865 drivers: {e}", exc_info=True)
    AR3865Procedures = None
    HipotConfig = None
    AR3865Driver = None

# Optional ERB relay driver (used for measurements)
try:
    from element_tester.system.drivers.relay_mcc.driver import ERB08Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import ERB08Driver: {e}", exc_info=True)
    ERB08Driver = None

# Optional PDIS relay driver (used only for hipot sequences)
try:
    from element_tester.system.drivers.relay_mcc_pdis.driver import PDIS08Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import PDIS08Driver: {e}", exc_info=True)
    PDIS08Driver = None

# Optional hipot test sequence
try:
    from element_tester.programs.hipot_test.test import HipotTestSequence
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import HipotTestSequence: {e}", exc_info=True)
    HipotTestSequence = None

# Optional measurement test sequence
try:
    from element_tester.programs.measurement_test.test import MeasurementTestSequence
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import MeasurementTestSequence: {e}", exc_info=True)
    MeasurementTestSequence = None

# Continue/Exit dialog widget
try:
    from element_tester.system.widgets.continue_exit import ContinueExitDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import ContinueExitDialog: {e}", exc_info=True)
    ContinueExitDialog = None

# Continue/Retry/Exit dialog widget (for hipot test)
try:
    from element_tester.system.widgets.continue_retry_exit import ContinueRetryExitDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import ContinueRetryExitDialog: {e}", exc_info=True)
    ContinueRetryExitDialog = None

# Test Passed dialog widget
try:
    from element_tester.system.widgets.test_passed import TestPassedDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import TestPassedDialog: {e}", exc_info=True)
    TestPassedDialog = None

# Optional meter driver
try:
    from element_tester.system.drivers.meter_fluke287.driver import Fluke287Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import Fluke287Driver: {e}", exc_info=True)
    Fluke287Driver = None

# Optional measurement procedures
try:
    import element_tester.system.procedures.measurement_test_procedures as meas_procs
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import measurement_test_procedures: {e}", exc_info=True)
    meas_procs = None

# Optional print helper for QC stickers (module-level import)
try:
    import element_tester.system.procedures.print_qc as print_qc
except Exception:
    print_qc = None


def should_use_simulate_mode(work_order: str, part_number: str) -> bool:
    """
    Central rule: return True to force simulate/demo mode for a given WO/PN.

    Default rule: WO == "TEST" and PN == "TEST" (case-insensitive).
    Add other tuples to TEST_COMBOS below when you want other shortcuts.
    """
    if not work_order or not part_number:
        return False
    wo = work_order.strip().lower()
    pn = part_number.strip().lower()

    TEST_COMBOS = {
        ("test", "test"),
        ("demo", "demo"),
    }
    return (wo, pn) in TEST_COMBOS


class TestRunner:
    """
    Orchestrates the high-level test sequence and logs results.

    - Normal flow: Hipot -> Measuring
    - Special flow: if WO == 'test' and PN == 'test' -> demo-only visual run
    """

    def __init__( 
        self,
        simulate: bool = False,
        hipot_resource: str = "serial://COM6",
        hipot_baud: int = 38400,
        relay_board_num: int = 0,
        relay_port_low: int = 12,
        relay_port_high: int = 13,
        logger: Optional[logging.Logger] = None,
        results_dir: Path | None = None,
        coordinator: Optional[TestCoordinator] = None,
    ):
        self.log = logger or logging.getLogger("element_tester.runner")
        self.simulate = simulate
        self.coordinator = coordinator
        # store default connection params so run_full_sequence can create drivers
        self.hipot_resource = hipot_resource
        self.hipot_baud = hipot_baud
        self.relay_board_num = relay_board_num
        self.relay_port_low = relay_port_low
        self.relay_port_high = relay_port_high

        if results_dir is None:
            # project-root/data/results/test_results.jsonl
            self.results_dir = Path("data") / "results"
        else:
            self.results_dir = results_dir

        # Initialize drivers
        self.hipot_driver = None
        self.relay_driver = None
        self.hipot_test_seq = None
        self.meter_driver = None
        self.measurement_test_seq = None
        
        self.log.info(f"TestRunner.__init__ | simulate={simulate} | ERB08Driver={ERB08Driver is not None} | PDIS08Driver={PDIS08Driver is not None} | AR3865Driver={AR3865Driver is not None} | HipotTestSequence={HipotTestSequence is not None} | Fluke287Driver={Fluke287Driver is not None} | MeasurementTestSequence={MeasurementTestSequence is not None}")
        
        if not simulate:
            # Initialize relay driver
            if ERB08Driver is not None:
                try:
                    self.relay_driver = ERB08Driver(
                        board_num=relay_board_num,
                        port_low=relay_port_low,
                        port_high=relay_port_high,
                        simulate=simulate
                    )
                    self.log.info("✓ Relay (ERB) driver initialized")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize ERB relay driver: {e}", exc_info=True)
            else:
                self.log.error("✗ ERB08Driver not available (import failed)")

            # NOTE: PDIS-specific initialization removed. If you need to
            # initialize a separate hipot relay station, add that logic here.
            # TODO: initialize PDIS08Driver(board_num=..., port_low=..., simulate=...)
            self.pdis_relay = None
            
            # Initialize hipot driver
            if AR3865Driver is not None:
                try:
                    self.hipot_driver = AR3865Driver(
                        resource=hipot_resource,
                        simulate=simulate
                    )
                    self.hipot_driver.initialize()
                    idn = self.hipot_driver.idn()
                    self.log.info(f"✓ Hipot driver initialized: {idn}")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize hipot driver: {e}", exc_info=True)
            else:
                self.log.error("✗ AR3865Driver not available (import failed)")
            
            # Create hipot test sequence if both drivers available
            # For hipot test sequence use the PDIS relay driver if available,
            # otherwise fall back to the ERB relay driver.
            # Create HipotTestSequence using the ERB relay driver only.
            if self.relay_driver and self.hipot_driver and HipotTestSequence:
                try:
                    self.hipot_test_seq = HipotTestSequence(
                        relay_driver=self.relay_driver,
                        hipot_driver=self.hipot_driver,
                        logger=self.log
                    )
                    self.log.info("✓ HipotTestSequence initialized - REAL HARDWARE MODE ACTIVE (PDIS logic removed)")
                except Exception as e:
                    self.log.error(f"✗ Failed to create HipotTestSequence: {e}", exc_info=True)
            else:
                self.log.error(f"✗ Cannot create HipotTestSequence - relay={self.relay_driver is not None}, hipot={self.hipot_driver is not None}, seq_class={HipotTestSequence is not None}")
            
            # Initialize meter driver
            if Fluke287Driver is not None:
                try:
                    self.meter_driver = Fluke287Driver(
                        port="COM7",  # Fluke 287 serial port
                        timeout=2.0,  # 2 second timeout
                        simulate=simulate,
                        logger=self.log
                    )
                    self.meter_driver.initialize()
                    self.log.info("✓ Meter driver initialized (Fluke 287)")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize meter driver: {e}", exc_info=True)
            else:
                self.log.error("✗ Fluke287Driver not available (import failed)")
            
            # Create measurement test sequence if both drivers available
            if self.relay_driver and self.meter_driver and MeasurementTestSequence:
                try:
                    self.measurement_test_seq = MeasurementTestSequence(
                        relay_driver=self.relay_driver,
                        meter_driver=self.meter_driver,
                        logger=self.log,
                        simulate=simulate
                    )
                    self.log.info("✓ MeasurementTestSequence initialized - REAL HARDWARE MODE ACTIVE")
                except Exception as e:
                    self.log.error(f"✗ Failed to create MeasurementTestSequence: {e}", exc_info=True)
            else:
                self.log.error(f"✗ Cannot create MeasurementTestSequence - relay={self.relay_driver is not None}, meter={self.meter_driver is not None}, seq_class={MeasurementTestSequence is not None}")
        else:
            self.log.info("TestRunner using SIMULATE mode (simulate=True in __init__)")

    def _reset_hardware(self) -> None:
        """
        Reset all hardware to safe state after test completion.
        Opens all relays and resets hipot instrument.
        """
        # Open all relays
        if self.relay_driver:
            try:
                self.log.info("Resetting hardware: Opening all relays")
                self.relay_driver.all_off()
            except Exception as e:
                self.log.error(f"Failed to open relays during reset: {e}", exc_info=True)
        
        # Reset hipot instrument (if available and has reset method)
        if self.hipot_driver:
            try:
                self.log.info("Resetting hardware: Resetting hipot instrument")
                # Most hipot instruments don't need explicit reset, but we can ensure relays are open
                if self.hipot_test_seq and hasattr(self.hipot_test_seq, 'open_relay'):
                    self.hipot_test_seq.open_relay()
            except Exception as e:
                self.log.error(f"Failed to reset hipot during cleanup: {e}", exc_info=True)
        
        self.log.info("Hardware reset complete")

    def _select_hypot_file_index(self, work_order: str, part_number: str) -> int:
        """
        Decide which instrument test file to use.

        Current rule: Always return 1 when WO/PN have any input.
        We'll add if/else mapping later per your logic.
        """
        # Inspect the operator-selected configuration when available.
        # If the operator selected 440V or 480V use FL 2 on the hipot instrument.
        try:
            cfg = getattr(self, "_selected_config", None)
            if cfg and isinstance(cfg, dict):
                voltage = cfg.get("voltage")
                if voltage is not None:
                    try:
                        v = int(voltage)
                        if v in (440, 480):
                            return 2
                    except Exception:
                        pass
        except Exception:
            pass
        return 1

    # --------------- PUBLIC ENTRY ---------------
    def run_full_sequence(
        self,
        work_order: str,
        part_number: str,
    ) -> Tuple[bool, str]:
        """
        Top-level: decides which branch to run, logs results.
        Uses self.coordinator for all UI updates.
        """
        if self.coordinator is None:
            return False, "No coordinator available"

        wo = work_order.strip()
        pn = part_number.strip()

        # Ensure a configuration has been selected. Some callers may not show
        # the configuration dialog before calling `run_full_sequence()`; in
        # that case open the dialog here so the full flow (scanning ->
        # configuration -> testing) is preserved.
        if not getattr(self, "_selected_config", None):
            try:
                from element_tester.system.ui.configuration_ui import ConfigurationWindow
                cfg = ConfigurationWindow.get_configuration(None, wo, pn)
                if cfg is None:
                    # Operator cancelled configuration
                    return False, "Operator cancelled configuration"
                # cfg is (voltage, wattage, (rmin, rmax)) or (v, w)
                v = int(cfg[0])
                w = int(cfg[1])
                selected = {"voltage": v, "wattage": w}
                if len(cfg) > 2 and isinstance(cfg[2], (list, tuple)) and len(cfg[2]) == 2:
                    selected["resistance_range"] = (float(cfg[2][0]), float(cfg[2][1]))
                else:
                    selected["resistance_range"] = (0.0, 0.0)
                self._selected_config = selected  # type: ignore[attr-defined]
            except Exception:
                # If configuration dialog can't be shown, proceed without it
                pass

        # Decide simulate/demo mode for THIS RUN ONLY
        # Check if WO/PN trigger demo mode, otherwise use hardware if available
        simulate_for_run = should_use_simulate_mode(wo, pn)
        
        # If no hardware drivers available, force simulate
        if not simulate_for_run and self.hipot_test_seq is None:
            simulate_for_run = True
            self.log.warning("No hardware drivers available, forcing simulate mode")
        
        self.log.info("Test mode for run: %s (WO=%s PN=%s)", 
                     "SIMULATE" if simulate_for_run else "HARDWARE", wo, pn)

        # Log the mode we're using for this run
        if simulate_for_run:
            self.log.debug("Running in SIMULATE mode for this test")
        else:
            self.log.debug("Running in HARDWARE mode for this test")

        # CASE 1: Special demo mode: WO == "test" and PN == "test"
        if wo.lower() == "test" and pn.lower() == "test":
            self.log.info("Entering DEMO test sequence (WO=TEST, PN=TEST)")
            ok, msg, hypot_info, meas_info = self._run_demo_sequence(wo, pn)
        else:
            # CASE 2: Normal real/simulated test
            ok, msg, hypot_info, meas_info = self._run_normal_sequence(wo, pn, simulate_for_run)

        # Log results for this test instance. Include selected configuration if available.
        cfg = getattr(self, "_selected_config", None)
        self._log_result(
            work_order=wo,
            part_number=pn,
            hypot_info=hypot_info,
            meas_info=meas_info,
            overall_pass=ok,
            mode="demo" if wo.lower() == "test" and pn.lower() == "test" else "normal",
            configuration=cfg,
        )

        return ok, msg

    # --------------- INTERNAL SEQUENCES ---------------
    def _run_normal_sequence(
        self,
        ui: MainTestWindow,
        wo: str,
        pn: str,
        simulate_for_run: bool = False,
    ) -> Tuple[bool, str, dict, dict]:
        # Prompt operator readiness before starting with Continue/Exit dialog
        ui.hypot_ready()
        QtWidgets.QApplication.processEvents()  # Force UI update
        
        if ContinueExitDialog:
            if not ContinueExitDialog.show_prompt(
                parent=ui,
                title="Ready to Test",
                message="Ready to begin testing?\n\nPress CONTINUE to start or EXIT to cancel."
            ):
                # Operator chose to exit - reset hardware and return to scanning
                self._reset_hardware()
                if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                    self._return_to_scan_callback()
                if hasattr(ui, 'close'):
                    ui.close()
                msg = "Operator cancelled before starting tests"
                return False, msg, {"passed": False, "message": msg}, {}
        else:
            # Fallback if widget not available
            if not ui.confirm_ready_to_test():
                msg = "Operator cancelled before starting tests"
                return False, msg, {"passed": False, "message": msg}, {}

        # Initialize hipot_detail for error handling (hipot test should run here)
        hip_detail = {"passed": False, "message": "Hipot test not run"}
        hip_ok = False
        hip_msg = "Hipot test not run"

        # Measurement test with unlimited retry logic ---------------------------------------------
        meas_ok = False
        meas_msg = ""
        meas_detail = {}
        attempt = 0
        
        while True:  # Unlimited retries until pass or operator exits
            if attempt > 0:
                self.log.info(f"MEASUREMENT retry attempt {attempt + 1}")
                # Clear previous measurement values on retry
                ui.update_measurement("L", 0, "Pin 1 to 6: ---", None)
                ui.update_measurement("L", 1, "Pin 2 to 5: ---", None)
                ui.update_measurement("L", 2, "Pin 3 to 4: ---", None)
                ui.update_measurement("R", 0, "Pin 1 to 6: ---", None)
                ui.update_measurement("R", 1, "Pin 2 to 5: ---", None)
                ui.update_measurement("R", 2, "Pin 3 to 4: ---", None)
                QtWidgets.QApplication.processEvents()
                try:
                    ui.append_measurement_log(f"--- Retry Attempt {attempt + 1} ---")
                except Exception:
                    ui.append_hypot_log(f"--- Measurement Retry Attempt {attempt + 1} ---")
                QtWidgets.QApplication.processEvents()
            
            meas_ok, meas_msg, meas_detail = self.run_measuring(ui, wo, pn)
            
            if meas_ok:
                break  # Success, exit retry loop and complete
            else:
                # Test failed - ask operator if they want to retry using Continue/Exit dialog
                if ContinueExitDialog:
                    if not ContinueExitDialog.show_prompt(
                        parent=ui,
                        title="Measurement Test Failed",
                        message=f"Test failed: {meas_msg}\n\nPress CONTINUE to retry or EXIT to cancel."
                    ):
                        # Operator chose to exit - reset hardware and return to scanning
                        self._reset_hardware()
                        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                            self._return_to_scan_callback()
                        if hasattr(ui, 'close'):
                            ui.close()
                        
                        return False, f"Measuring failed: {meas_msg} (operator cancelled)", hip_detail, meas_detail
                else:
                    # Fallback if widget not available
                    if not ui.confirm_retry_test("Measurement", meas_msg):
                        return False, f"Measuring failed: {meas_msg} (operator cancelled)", hip_detail, meas_detail
                # If continue, loop will retry
            
            attempt += 1


        # Hipot test with unlimited retry logic ---------------------------------------------
        hip_ok = False
        hip_msg = ""
        hip_detail = {}
        attempt = 0
        
        while True:  # Unlimited retries until pass or operator exits
            if attempt > 0:
                self.log.info(f"HIPOT retry attempt {attempt + 1}")
                ui.append_hypot_log(f"--- Retry Attempt {attempt + 1} ---")
                QtWidgets.QApplication.processEvents()
            
            # Always keep relay closed during retries (only open when operator exits)
            hip_ok, hip_msg, hip_detail = self.run_hipot(ui, wo, pn, simulate_for_run, keep_relay_closed=True)
            
            if hip_ok:
                break  # Success, exit retry loop and continue to measurements
            else:
                # Test failed - ask operator if they want to retry using Continue/Retry/Exit dialog
                if ContinueRetryExitDialog:
                    result = ContinueRetryExitDialog.show_prompt(
                        parent=ui,
                        title="Hipot Test Failed",
                        message=f"Test failed: {hip_msg}\n\nPress RETRY to re-test, CONTINUE to skip, or EXIT to cancel."
                    )
                    
                    if result == ContinueRetryExitDialog.RETRY:
                        # Operator chose to retry - loop will continue
                        pass
                    elif result == ContinueRetryExitDialog.CONTINUE:
                        # Operator chose to skip and continue to measurements despite failure
                        self.log.warning(f"Hipot test failed but operator chose to continue: {hip_msg}")
                        break
                    else:  # EXIT
                        # Operator chose to exit - reset hardware and return to scanning
                        self._reset_hardware()
                        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                            self._return_to_scan_callback()
                        if hasattr(ui, 'close'):
                            ui.close()
                        
                        return False, f"Hipot failed: {hip_msg} (operator cancelled)", hip_detail, {}
                else:
                    # Fallback if widget not available
                    if not ui.confirm_retry_test("Hipot", hip_msg):
                        if self.hipot_test_seq:
                            try:
                                self.hipot_test_seq.open_relay()
                            except Exception:
                                pass
                        return False, f"Hipot failed: {hip_msg} (operator cancelled)", hip_detail, {}
                # If continue, loop will retry
            
            attempt += 1

        
        # Both tests passed - show success dialog. Schedule QC printing from the
        # dialog so the sticker is printed ~1s after the dialog is shown.
        if TestPassedDialog:
            try:
                TestPassedDialog.show_passed(parent=ui, work_order=wo, part_number=pn)
            except TypeError:
                # Fallback if older signature present
                TestPassedDialog.show_passed(parent=ui)

        # QC printing is scheduled from the TestPassedDialog to occur
        # ~1 second after the dialog is shown. No additional action needed here.

        # Reset all hardware after successful test
        self._reset_hardware()

        # IMPORTANT: Show scan window BEFORE closing test window
        # This ensures there's always a visible window, preventing Qt event loop exit
        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
            self._return_to_scan_callback()
        
        # Now close test window (scan window is already visible)
        if hasattr(ui, 'close'):
            ui.close()
        
        return True, "Hipot + Measuring completed successfully", hip_detail, meas_detail

    def _run_demo_sequence(
        self,
        wo: str,
        pn: str,
    ) -> Tuple[bool, str, dict, dict]:
        """
        Demo-only visual run with preset values.
        No real hardware activity; just drives the UI.
        """
        # Hypot demo
        self.coordinator.show_hipot_ready()
        self.coordinator.append_hipot_log("DEMO: Hypot Ready...")
        time.sleep(1.0)

        self.coordinator.show_hipot_running()
        self.coordinator.append_hipot_log("DEMO: Configuring test parameters...")
        time.sleep(1.2)
        self.coordinator.append_hipot_log("DEMO: Starting high voltage test...")
        time.sleep(1.5)
        self.coordinator.append_hipot_log("DEMO: Monitoring for breakdown...")
        time.sleep(1.0)
        self.coordinator.append_hipot_log("DEMO: Ramping down voltage...")
        time.sleep(0.8)

        demo_hipot_pass = True
        self.coordinator.show_hipot_result(demo_hipot_pass)
        self.coordinator.append_hipot_log("DEMO: Hipot PASS (simulated).")
        time.sleep(0.5)

        hipot_info = {
            "passed": demo_hipot_pass,
            "message": "Demo Hypot PASS",
        }

        # Measuring demo – using your LP/RP style
        demo_meas = {
            "LP1to6": 6,
            "LP2to5": 7,
            "LP3to4": 6,
            "RP1to6": 6,
            "RP2to5": 7,
            "RP3to4": 6,
        }

        # Left - update UI immediately for each measurement
        self.coordinator.update_measurement("L", 0, f"Pin 1 to 6: {demo_meas['LP1to6']}", True)
        time.sleep(0.6)
        self.coordinator.update_measurement("L", 1, f"Pin 2 to 5: {demo_meas['LP2to5']}", True)
        time.sleep(0.6)
        self.coordinator.update_measurement("L", 2, f"Pin 3 to 4: {demo_meas['LP3to4']}", True)
        time.sleep(0.6)

        # Right - update UI immediately for each measurement
        self.coordinator.update_measurement("R", 0, f"Pin 1 to 6: {demo_meas['RP1to6']}", True)
        time.sleep(0.6)
        self.coordinator.update_measurement("R", 1, f"Pin 2 to 5: {demo_meas['RP2to5']}", True)
        time.sleep(0.6)
        self.coordinator.update_measurement("R", 2, f"Pin 3 to 4: {demo_meas['RP3to4']}", True)
        time.sleep(0.4)

        meas_info = {
            "passed": True,
            "message": "Demo measuring PASS",
            "values": demo_meas,
        }

        msg = (
            "DEMO sequence complete. This did not exercise real hardware.\n"
            "WORK ORDER = TEST, PART = TEST."
        )
        return True, msg, hipot_info, meas_info

    # --------------- HIPOT ----------------
    def run_hipot(
        self,
        work_order: str,
        part_number: str,
        simulate: bool = False,
        keep_relay_closed: bool = False,
    ) -> Tuple[bool, str, dict]:
        """
        Run the Hipot portion of the test and update the UI via coordinator.
        Uses HipotTestSequence which handles relay closure + hipot test.
        Returns (passed, message, detail_dict).
        """
        self.log.info(f"HIPOT start | WO={work_order} | PN={part_number}")

        self.coordinator.show_hipot_ready()
        time.sleep(0.2)

        self.coordinator.show_hipot_running()
        self.coordinator.append_hipot_log("Checking Hipot connections...")
        time.sleep(0.5)

        if simulate or self.hipot_test_seq is None:
            # Simulated behavior
            self.coordinator.append_hipot_log("Step 1/5: Reset instrument (SIM)")
            time.sleep(0.8)
            self.coordinator.append_hipot_log("Step 2/5: Configure relay (SIM)")
            time.sleep(0.8)
            self.coordinator.append_hipot_log("Step 3/5: Configure hipot test (SIM)")
            time.sleep(0.8)
            self.coordinator.append_hipot_log("Step 4/5: Execute hipot test (SIM)")
            time.sleep(1.5)
            self.coordinator.append_hipot_log("Step 5/5: Disable relay (SIM)")
            time.sleep(0.8)
            passed = True
            msg = "Simulated Hipot PASS"
        else:
            # Real hardware test using HipotTestSequence
            try:
                self.coordinator.append_hipot_log("Step 1/5: Reset instrument")
                # Run the full hipot test sequence (handles relay + hipot)
                # Default: 1500V, 5mA trip, 1s ramp, 1s dwell, 0.5s fall
                self.coordinator.append_hipot_log("Step 2/5: Configure relay (closing relay 8)")
                self.coordinator.append_hipot_log("Step 3/5: Configure hipot test")
                self.coordinator.append_hipot_log("Step 4/5: Execute hipot test")
                
                # TIMING CONFIGURATION FOR RESET
                HIPOT_TEST_DURATION = 4.0  # Expected test duration in seconds
                RESET_DELAY_AFTER_RESULT = 3.0  # Delay after result for operator awareness

                # Determine which FL to run based on operator configuration
                file_index = self._select_hypot_file_index(work_order, part_number)
                passed, msg = self.hipot_test_seq.run_test(
                    keep_relay_closed=keep_relay_closed,
                    reset_after_test=True,
                    total_test_duration_s=HIPOT_TEST_DURATION,
                    reset_delay_after_result_s=RESET_DELAY_AFTER_RESULT,
                    file_index=file_index
                )
                
                self.coordinator.append_hipot_log("Step 5/5: Disable relay (all relays OFF)")
                
            except Exception as e:
                passed = False
                msg = f"Exception: {e}"
                self.coordinator.append_hipot_log(f"ERROR: {e}")
                self.log.error(f"Hipot test failed with exception: {e}", exc_info=True)

        self.coordinator.show_hipot_result(passed)
        self.log.info(f"HIPOT result | pass={passed} | msg={msg}")
        self.coordinator.append_hipot_log(f"Result: {'PASS' if passed else 'FAIL'} ({msg})")

        detail = {
            "passed": passed,
            "message": msg,
        }
        return passed, msg, detail

    # --------------- MEASURING ----------------
    def run_measuring(
        self,
        work_order: str,
        part_number: str,
    ) -> Tuple[bool, str, dict]:
        """
        Run the measuring portion using real meter readings via coordinator.
        Measures resistance for Pin 1to6, Pin 2to5, and Pin 3to4.
        """
        self.log.info(f"MEAS start | WO={work_order} | PN={part_number}")

        # Check if we have measurement test sequence or need simulated mode
        use_real_measurement = (self.measurement_test_seq is not None)
        
        if use_real_measurement:
            self.log.info("MEAS: Using REAL HARDWARE via MeasurementTestSequence")
            
            # Get resistance range from configuration
            resistance_range = None
            cfg = getattr(self, "_selected_config", None)
            if cfg and isinstance(cfg, dict):
                rr = cfg.get("resistance_range")
                if isinstance(rr, (list, tuple)) and len(rr) == 2:
                    try:
                        resistance_range = (float(rr[0]), float(rr[1]))
                    except Exception:
                        pass
            
            # If no range from config, try to get from ConfigurationWindow mapping
            if resistance_range is None or resistance_range == (0.0, 0.0):
                try:
                    from element_tester.system.ui.configuration_ui import ConfigurationWindow
                    key = None
                    if cfg and isinstance(cfg, dict) and cfg.get("voltage") and cfg.get("wattage"):
                        key = (int(cfg.get("voltage")), int(cfg.get("wattage")))
                    # Fallback to (208, 7000) if not set
                    if key is None or key not in ConfigurationWindow.RESISTANCE_RANGE:
                        key = (208, 7000)
                    if key in ConfigurationWindow.RESISTANCE_RANGE:
                        resistance_range = ConfigurationWindow.RESISTANCE_RANGE[key]
                        # Log the expected resistance
                        self.coordinator.append_measurement_log(f"Expected resistance for {key[0]}V/{key[1]}W: {resistance_range[0]:.1f} - {resistance_range[1]:.1f} Ω")
                except Exception as e:
                    self.log.warning(f"Could not get resistance range from configuration: {e}")
            
            # Run measurement test sequence
            try:
                passed, msg, detail = self.measurement_test_seq.run_test(
                    ui=self.coordinator,
                    resistance_range=resistance_range,
                    timeout_per_position_s=10.0
                )
                return passed, msg, detail
            except Exception as e:
                self.log.error(f"MEAS: Measurement test sequence failed: {e}", exc_info=True)
                # Return failure
                detail = {
                    "passed": False,
                    "message": f"Measurement test exception: {e}",
                    "values": {},
                }
                return False, str(e), detail
        else:
            # Simulated readings (fallback when no hardware)
            self.log.info("MEAS: Using simulated values (no measurement hardware)")
            left_vals = [6.0, 7.0, 6.0]
            right_vals = [6.0, 7.0, 6.0]
            
            # Determine expected resistance range from selected configuration
            cfg = getattr(self, "_selected_config", None)
            rmin = rmax = None
            if cfg and isinstance(cfg, dict):
                rr = cfg.get("resistance_range")
                if isinstance(rr, (list, tuple)) and len(rr) == 2:
                    try:
                        rmin = float(rr[0])
                        rmax = float(rr[1])
                    except Exception:
                        rmin = rmax = None

            # If no range from config, try ConfigurationWindow.RESISTANCE_RANGE
            if rmin is None or rmax is None:
                try:
                    from element_tester.system.ui.configuration_ui import ConfigurationWindow
                    key = None
                    if cfg and isinstance(cfg, dict) and cfg.get("voltage") and cfg.get("wattage"):
                        key = (int(cfg.get("voltage")), int(cfg.get("wattage")))
                    # Fallback to (208, 7000)
                    if key is None or key not in ConfigurationWindow.RESISTANCE_RANGE:
                        key = (208, 7000)
                    if key in ConfigurationWindow.RESISTANCE_RANGE:
                        rmin, rmax = ConfigurationWindow.RESISTANCE_RANGE[key]
                        # Log expected resistance
                        self.coordinator.append_measurement_log(f"Expected resistance for {key[0]}V/{key[1]}W: {rmin:.1f} - {rmax:.1f} Ω")
                except Exception:
                    pass

            # Update UI with simulated measurements
            row_names = ["Pin 1 to 6", "Pin 2 to 5", "Pin 3 to 4"]
            for idx in range(3):
                # Left measurement
                l_val = float(left_vals[idx])
                l_pass = None
                if rmin is not None and rmax is not None:
                    l_pass = (rmin <= l_val <= rmax)
                self.coordinator.update_measurement("L", idx, f"{row_names[idx]}: {l_val:.2f} Ω", l_pass)
                self.coordinator.append_measurement_log(f"Measured {row_names[idx]} LEFT: {l_val:.2f} Ω - {'OK' if l_pass else 'FAIL' if l_pass is False else 'N/A'}")
                time.sleep(0.6)

                # Right measurement
                r_val = float(right_vals[idx])
                r_pass = None
                if rmin is not None and rmax is not None:
                    r_pass = (rmin <= r_val <= rmax)
                self.coordinator.update_measurement("R", idx, f"{row_names[idx]}: {r_val:.2f} Ω", r_pass)
                self.coordinator.append_measurement_log(f"Measured {row_names[idx]} RIGHT: {r_val:.2f} Ω - {'OK' if r_pass else 'FAIL' if r_pass is False else 'N/A'}")
                time.sleep(0.6)

            # Store values with correct pin naming (1to6, 2to5, 3to4)
            values = {
                "LP1to6": left_vals[0],
                "LP2to5": left_vals[1],
                "LP3to4": left_vals[2],
                "RP1to6": right_vals[0],
                "RP2to5": right_vals[1],
                "RP3to4": right_vals[2],
            }

            # Decide overall pass
            if rmin is not None and rmax is not None:
                all_ok = True
                for val in left_vals + right_vals:
                    if val == 0.0 or not (rmin <= val <= rmax):
                        all_ok = False
                        break
                passed = all_ok
                msg = "All measurements within limits" if passed else "Some measurements out of range"
            else:
                passed = True
                msg = "Measurements recorded (no range configured)"

            detail = {
                "passed": passed,
                "message": msg,
                "values": values,
            }

            self.log.info(f"MEAS result | pass={passed} | msg={msg}")
            return passed, msg, detail

    # --------------- LOGGING ----------------
    def _log_result(
        self,
        work_order: str,
        part_number: str,
        hypot_info: dict,
        meas_info: dict,
        overall_pass: bool,
        mode: str = "normal",
        configuration: dict | None = None,
    ) -> None:
        """
        Append a record to data/results/test_results.jsonl and also write
        a human-readable line to data/results/test_results.txt
        """
        self.results_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="seconds")

        # JSON entry
        record = {
            "timestamp": timestamp,
            "mode": mode,
            "work_order": work_order,
            "part_number": part_number,
            "configuration": configuration,
            "overall_pass": overall_pass,
            "hypot": hypot_info,
            "measurement": meas_info,
        }

        json_path = self.results_dir / "test_results.jsonl"
        with json_path.open("a", encoding="utf-8") as jf:
            jf.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Pretty text entry matching your example string
        meas_values = meas_info.get("values", {}) if meas_info else {}
        meas_str = (
            f"LP1to6: {meas_values.get('LP1to6', '')} | "
            f"LP2to5: {meas_values.get('LP2to5', '')} | "
            f"LP3to4: {meas_values.get('LP3to4', '')} | "
            f"RP1to6: {meas_values.get('RP1to6', '')} | "
            f"RP2to5: {meas_values.get('RP2to5', '')} | "
            f"RP3to4: {meas_values.get('RP3to4', '')}"
        ).strip()

        txt_path = self.results_dir / "test_results.txt"
        with txt_path.open("a", encoding="utf-8") as tf:
            tf.write(
                f"Timestamp: {timestamp}\n"
                f"Mode: {mode}\n"
                f"Work Order #: {work_order}\n"
                f"Part #: {part_number}\n"
                f"Configuration: {configuration if configuration is not None else ''}\n"
                f"Hypot Result: {hypot_info.get('message', '')}\n"
                f"Measurement Result: {meas_str}\n"
                f"Overall: {'PASS' if overall_pass else 'FAIL'}\n"
                f"{'-'*60}\n"
            )

if __name__ == "__main__":
    import sys
    import argparse
    from PyQt6 import QtWidgets
    from element_tester.system.ui.scanning import ScanWindow

    parser = argparse.ArgumentParser(description="Run Element Tester UI")
    parser.add_argument("--simulate", action="store_true", help="Run in simulate mode (no hardware)")
    args, unknown = parser.parse_known_args()

    app = QtWidgets.QApplication(sys.argv)

    # Force dark mode for the application - this affects child processes like Notepad
    # Set Windows app to prefer dark mode via registry
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            # AppsUseLightTheme: 0 = Dark, 1 = Light
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
        except Exception:
            pass
    except Exception:
        pass

    # Apply dark palette to PyQt6 application
    from PyQt6.QtGui import QPalette, QColor
    from PyQt6.QtCore import Qt
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
    app.setPalette(dark_palette)
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")

    # Create coordinator for UI management
    coordinator = TestCoordinator()
    
    # Default to hardware mode; enable simulate only when --simulate provided.
    runner = TestRunner(simulate=bool(args.simulate), coordinator=coordinator)

    def on_scan_completed(wo: str, pn: str):
        """Handle scan completion - show config dialog then start test."""
        # Get configuration
        config = coordinator.transition_to_configuration(wo, pn)
        
        if config is None:
            # User cancelled configuration - return to scanning
            coordinator.show_scan_window()
            return
        
        # Store configuration
        runner._selected_config = config
        
        # Transition to testing window
        coordinator.transition_to_testing()
        
        # Log selected configuration
        if config:
            coordinator.append_measurement_log(f"Selected config: {config['voltage']}V, {config['wattage']}W")
            rr = config.get("resistance_range")
            if rr and isinstance(rr, (tuple, list)) and len(rr) == 2:
                rmin, rmax = rr
                if rmin == 0.0 and rmax == 0.0:
                    coordinator.append_measurement_log(f"Resistance range: not configured for {config['voltage']} V / {config['wattage']} W")
                else:
                    coordinator.append_measurement_log(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")
        
        # Start the test sequence
        runner.run_full_sequence(wo, pn)

    # Show initial scan window and connect signal
    coordinator.show_scan_window()
    coordinator.scan_window.scanCompleted.connect(on_scan_completed)
    
    sys.exit(app.exec())
