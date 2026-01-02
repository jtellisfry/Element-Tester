from __future__ import annotations
from typing import Optional, Tuple
from pathlib import Path
import logging
import time
import json
from datetime import datetime
import sys


# Make sure .../src is on sys.path so `element_tester` is importable
SRC_ROOT = Path(__file__).resolve().parents[3]  # .../Element_Tester/src
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from element_tester.system.ui.testing import MainTestWindow
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

# Continue/Exit dialog widget
try:
    from element_tester.system.widgets.continue_exit import ContinueExitDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import ContinueExitDialog: {e}", exc_info=True)
    ContinueExitDialog = None

# Test Passed dialog widget
try:
    from element_tester.system.widgets.test_passed import TestPassedDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import TestPassedDialog: {e}", exc_info=True)
    TestPassedDialog = None

# Optional meter driver
try:
    from element_tester.system.drivers.meter_ut61e.driver import UT61EDriver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import UT61EDriver: {e}", exc_info=True)
    UT61EDriver = None

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
    ):
        self.log = logger or logging.getLogger("element_tester.runner")
        self.simulate = simulate
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
        
        self.log.info(f"TestRunner.__init__ | simulate={simulate} | ERB08Driver={ERB08Driver is not None} | PDIS08Driver={PDIS08Driver is not None} | AR3865Driver={AR3865Driver is not None} | HipotTestSequence={HipotTestSequence is not None} | UT61EDriver={UT61EDriver is not None}")
        
        if not simulate:
            # Initialize relay driver
            if ERB08Driver is not None:
                try:
                    self.relay_driver = ERB08Driver(
                        board_num=relay_board_num,
                        port_low=relay_port_low,
                        port_high=relay_port_high,
                        simulate=False
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
                        simulate=False
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
            if UT61EDriver is not None:
                try:
                    self.meter_driver = UT61EDriver(
                        vendor_id=0x1a86,
                        product_id=0xe429,
                        simulate=False,
                        timeout_ms=5000,
                        logger=self.log
                    )
                    self.meter_driver.initialize()
                    self.log.info("✓ Meter driver initialized")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize meter driver: {e}", exc_info=True)
            else:
                self.log.error("✗ UT61EDriver not available (import failed)")
        else:
            self.log.info("TestRunner using SIMULATE mode for Hipot (simulate=True in __init__)")

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
        ui: MainTestWindow,
        work_order: str,
        part_number: str,
    ) -> Tuple[bool, str]:
        """
        Top-level: decides which branch to run, logs results.
        """

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
            ok, msg, hypot_info, meas_info = self._run_demo_sequence(ui, wo, pn)
        else:
            # CASE 2: Normal real/simulated test
            ok, msg, hypot_info, meas_info = self._run_normal_sequence(ui, wo, pn, simulate_for_run)

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
                # Operator chose to exit - close test window and return to scanning
                if hasattr(ui, 'close'):
                    ui.close()
                if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                    self._return_to_scan_callback()
                msg = "Operator cancelled before starting tests"
                return False, msg, {"passed": False, "message": msg}, {}
        else:
            # Fallback if widget not available
            if not ui.confirm_ready_to_test():
                msg = "Operator cancelled before starting tests"
                return False, msg, {"passed": False, "message": msg}, {}

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
                        # Operator chose to exit - open all relays before exiting
                        if self.relay_driver:
                            try:
                                self.log.info("Opening all relays after operator exit")
                                self.relay_driver.all_off()
                            except Exception as e:
                                self.log.error(f"Failed to open relays after exit: {e}", exc_info=True)
                        
                        # Close test window and return to scanning
                        if hasattr(ui, 'close'):
                            ui.close()
                        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                            self._return_to_scan_callback()
                        
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
                # Test failed - ask operator if they want to retry using Continue/Exit dialog
                if ContinueExitDialog:
                    if not ContinueExitDialog.show_prompt(
                        parent=ui,
                        title="Hipot Test Failed",
                        message=f"Test failed: {hip_msg}\n\nPress CONTINUE to retry or EXIT to cancel."
                    ):
                        # Operator chose to exit - open all relays before exiting
                        if self.hipot_test_seq:
                            try:
                                self.hipot_test_seq.open_relay()
                            except Exception:
                                pass
                        if self.relay_driver:
                            try:
                                self.log.info("Opening all relays after operator exit")
                                self.relay_driver.all_off()
                            except Exception as e:
                                self.log.error(f"Failed to open relays after exit: {e}", exc_info=True)
                        
                        # Close test window and return to scanning
                        if hasattr(ui, 'close'):
                            ui.close()
                        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                            self._return_to_scan_callback()
                        
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

        # Open all relays before returning to scan
        if self.relay_driver:
            try:
                self.log.info("Opening all relays after successful test")
                self.relay_driver.all_off()
            except Exception as e:
                self.log.error(f"Failed to open relays after test: {e}", exc_info=True)

        # Close test window and return to scanning
        if hasattr(ui, 'close'):
            ui.close()
        
        # Signal to show scan window again
        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
            self._return_to_scan_callback()
        
        return True, "Hipot + Measuring completed successfully", hip_detail, meas_detail

    def _run_demo_sequence(
        self,
        ui: MainTestWindow,
        wo: str,
        pn: str,
    ) -> Tuple[bool, str, dict, dict]:
        """
        Demo-only visual run with preset values.
        No real hardware activity; just drives the UI.
        """
        # Hypot demo
        ui.hypot_ready()
        ui.append_hypot_log("DEMO: Hypot Ready...")
        time.sleep(1.0)

        ui.hypot_running()
        ui.append_hypot_log("DEMO: Configuring test parameters...")
        time.sleep(1.2)
        ui.append_hypot_log("DEMO: Starting high voltage test...")
        time.sleep(1.5)
        ui.append_hypot_log("DEMO: Monitoring for breakdown...")
        time.sleep(1.0)
        ui.append_hypot_log("DEMO: Ramping down voltage...")
        time.sleep(0.8)

        demo_hipot_pass = True
        ui.hypot_result(demo_hipot_pass)
        ui.append_hypot_log("DEMO: Hipot PASS (simulated).")
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
        ui.update_measurement("L", 0, f"Pin 1 to 6: {demo_meas['LP1to6']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("L", 1, f"Pin 1 to 6: {demo_meas['LP2to5']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("L", 2, f"Pin 1 to 6: {demo_meas['LP3to4']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)

        # Right - update UI immediately for each measurement
        ui.update_measurement("R", 0, f"Pin 1 to 6: {demo_meas['RP1to6']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("R", 1, f"Pin 1 to 6: {demo_meas['RP2to5']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("R", 2, f"Pin 1 to 6: {demo_meas['RP3to4']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
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
        ui: MainTestWindow,
        work_order: str,
        part_number: str,
        simulate: bool = False,
        keep_relay_closed: bool = False,
    ) -> Tuple[bool, str, dict]:
        """
        Run the Hipot portion of the test and update the UI.
        Uses HipotTestSequence which handles relay closure + hipot test.
        Returns (passed, message, detail_dict).
        """
        self.log.info(f"HIPOT start | WO={work_order} | PN={part_number}")
        # Defensive checks: ensure UI is present and implements required methods
        if ui is None:
            self.log.error("HIPOT start failed: ui is None")
            return False, "UI not available", {"passed": False}

        try:
            ui.hypot_ready()
        except Exception as e:
            self.log.error(f"HIPOT: ui.hypot_ready() failed: {e}", exc_info=True)
            return False, f"UI error: {e}", {"passed": False}
        time.sleep(0.2)

        ui.hypot_running()
        QtWidgets.QApplication.processEvents()  # Force UI update
        ui.append_hypot_log("Checking Hipot connections...")
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.5)

        if simulate or self.hipot_test_seq is None:
            # Simulated behavior
            ui.append_hypot_log("Step 1/5: Reset instrument (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            ui.append_hypot_log("Step 2/5: Configure relay (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            ui.append_hypot_log("Step 3/5: Configure hipot test (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            ui.append_hypot_log("Step 4/5: Execute hipot test (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(1.5)
            ui.append_hypot_log("Step 5/5: Disable relay (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            passed = True
            msg = "Simulated Hipot PASS"
        else:
            # Real hardware test using HipotTestSequence
            try:
                ui.append_hypot_log("Step 1/5: Reset instrument")
                QtWidgets.QApplication.processEvents()
                # Run the full hipot test sequence (handles relay + hipot)
                # Default: 1500V, 5mA trip, 1s ramp, 1s dwell, 0.5s fall
                ui.append_hypot_log("Step 2/5: Configure relay (closing relay 8)")
                QtWidgets.QApplication.processEvents()
                ui.append_hypot_log("Step 3/5: Configure hipot test")
                QtWidgets.QApplication.processEvents()
                ui.append_hypot_log("Step 4/5: Execute hipot test")
                QtWidgets.QApplication.processEvents()
                
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
                
                ui.append_hypot_log("Step 5/5: Disable relay (all relays OFF)")
                QtWidgets.QApplication.processEvents()
                
            except Exception as e:
                passed = False
                msg = f"Exception: {e}"
                ui.append_hypot_log(f"ERROR: {e}")
                self.log.error(f"Hipot test failed with exception: {e}", exc_info=True)

        ui.hypot_result(passed)
        QtWidgets.QApplication.processEvents()
        self.log.info(f"HIPOT result | pass={passed} | msg={msg}")
        ui.append_hypot_log(f"Result: {'PASS' if passed else 'FAIL'} ({msg})")
        QtWidgets.QApplication.processEvents()

        detail = {
            "passed": passed,
            "message": msg,
        }
        return passed, msg, detail

    # --------------- MEASURING ----------------
    def run_measuring(
        self,
        ui: MainTestWindow,
        work_order: str,
        part_number: str,
    ) -> Tuple[bool, str, dict]:
        """
        Run the measuring portion using real meter readings.
        Measures resistance for Pin 1to6, Pin 2to5, and Pin 3to4.
        """
        self.log.info(f"MEAS start | WO={work_order} | PN={part_number}")

        try:
            # Check if we have meter and relay drivers available
            self.log.info(f"MEAS: Checking drivers - meter={self.meter_driver is not None}, relay={self.relay_driver is not None}, meas_procs={meas_procs is not None}")
            use_real_meter = (self.meter_driver is not None and 
                             self.relay_driver is not None and 
                             meas_procs is not None)
            
            if use_real_meter:
                self.log.info("MEAS: Using REAL METER hardware")
            else:
                self.log.info("MEAS: Using SIMULATED values")
        except Exception as e:
            self.log.error(f"MEAS: Error checking drivers: {e}", exc_info=True)
            use_real_meter = False
        
        if use_real_meter:
            # Real measurements using meter driver
            left_vals = []
            right_vals = []
            
            # Ensure all relays are open before starting measurements
            self.log.info("MEAS: Opening all relays before starting measurements")
            try:
                self.relay_driver.all_off()
                time.sleep(0.2)  # Brief settling delay
                self.log.info("MEAS: All relays opened successfully")
                QtWidgets.QApplication.processEvents()  # Keep UI responsive
            except Exception as e:
                self.log.error(f"MEAS: Failed to open all relays: {e}", exc_info=True)
            
            # Flush meter buffer before starting any measurements
            self.log.info("MEAS: Flushing meter buffer before starting measurements")
            try:
                self.meter_driver.flush_buffer()
                self.log.info("MEAS: Initial buffer flush complete")
                QtWidgets.QApplication.processEvents()  # Keep UI responsive
            except Exception as e:
                self.log.error(f"MEAS: Failed to flush initial buffer: {e}", exc_info=True)
            
            configurations = [
                ("Pin 1 to 6", meas_procs.close_pin1to6, meas_procs.open_pin1to6, 0),
                ("Pin 2 to 5", meas_procs.close_pin2to5, meas_procs.open_pin2to5, 1),
                ("Pin 3 to 4", meas_procs.close_pin3to4, meas_procs.open_pin3to4, 2),
            ]
            
            for config_name, close_func, open_func, row_idx in configurations:
                try:
                    # Close relays
                    self.log.info(f"MEAS: Closing relays for {config_name}")
                    try:
                        close_func(self.relay_driver, delay_ms=200.0, logger=self.log)
                        self.log.info(f"MEAS: Relays closed successfully for {config_name}")
                    except Exception as e:
                        self.log.error(f"MEAS: Failed to close relays for {config_name}: {e}", exc_info=True)
                        raise
                    
                    # Flush buffer
                    self.log.info(f"MEAS: Flushing meter buffer for {config_name}")
                    try:
                        self.meter_driver.flush_buffer()
                        self.log.info(f"MEAS: Buffer flushed successfully")
                        QtWidgets.QApplication.processEvents()  # Keep UI responsive
                    except Exception as e:
                        self.log.error(f"MEAS: Failed to flush buffer: {e}", exc_info=True)
                        raise
                    
                    # Wait 2 seconds after relay closure before polling
                    self.log.info(f"MEAS: Waiting 2 seconds after relay closure before polling...")
                    QtWidgets.QApplication.processEvents()  # Keep UI responsive
                    time.sleep(2.0)
                    QtWidgets.QApplication.processEvents()  # Keep UI responsive
                    
                    # Poll for mode '1' (resistance mode)
                    self.log.info(f"MEAS: Polling for resistance mode...")
                    mode_found = False
                    max_attempts = 30
                    for attempt in range(max_attempts):
                        QtWidgets.QApplication.processEvents()  # Keep UI responsive
                        try:
                            reading = self.meter_driver.read_value()
                            if reading.raw_packet and len(reading.raw_packet) > 5:
                                mode_char = chr(reading.raw_packet[5])
                                self.log.debug(f"MEAS: Attempt {attempt+1}/{max_attempts} - mode='{mode_char}'")
                                if mode_char in ['1', '0']:  # Accept both resistance modes
                                    mode_found = True
                                    self.log.info(f"MEAS: Mode '{mode_char}' detected after {attempt+1} attempts")
                                    break
                        except Exception as e:
                            self.log.error(f"MEAS: Error in polling attempt {attempt+1}: {e}", exc_info=True)
                        time.sleep(1.2)
                        QtWidgets.QApplication.processEvents()  # Keep UI responsive
                    
                    if mode_found:
                        # Take 3 samples and average
                        self.log.info(f"MEAS: Taking 3 samples for {config_name}")
                        QtWidgets.QApplication.processEvents()  # Keep UI responsive
                        readings = []
                        for sample_num in range(3):
                            QtWidgets.QApplication.processEvents()  # Keep UI responsive
                            try:
                                reading = self.meter_driver.read_value()
                                if reading.value is not None:
                                    readings.append(reading.value)
                                    self.log.info(f"MEAS: Sample {sample_num+1}/3 = {reading.value:.3f} {reading.unit}")
                                else:
                                    self.log.warning(f"MEAS: Sample {sample_num+1}/3 invalid")
                            except Exception as e:
                                self.log.error(f"MEAS: Error reading sample {sample_num+1}: {e}", exc_info=True)
                            time.sleep(1.2)
                            QtWidgets.QApplication.processEvents()  # Keep UI responsive
                        
                        if readings:
                            avg = sum(readings) / len(readings)
                            # Round to 1 decimal place
                            avg = round(avg, 1)
                            # Use same value for left and right (simultaneous measurement)
                            left_vals.append(avg)
                            right_vals.append(avg)
                            self.log.info(f"MEAS: {config_name} = {avg:.1f} Ω (from {len(readings)} samples)")
                            
                            # Update UI immediately for this measurement
                            # Determine pass/fail based on resistance range
                            cfg = getattr(self, "_selected_config", None)
                            rmin = rmax = None
                            if cfg and isinstance(cfg, dict):
                                rr = cfg.get("resistance_range")
                                if isinstance(rr, (list, tuple)) and len(rr) == 2:
                                    try:
                                        rmin = float(rr[0])
                                        rmax = float(rr[1])
                                    except Exception:
                                        pass
                            
                            # Update LEFT
                            l_pass = None
                            if rmin is not None and rmax is not None:
                                l_pass = (rmin <= avg <= rmax)
                            ui.update_measurement("L", row_idx, f"{config_name}: {avg:.1f} Ω", l_pass)
                            QtWidgets.QApplication.processEvents()
                            try:
                                ui.append_measurement_log(f"Measured {config_name} LEFT: {avg:.1f} Ω - {'OK' if l_pass else 'FAIL' if l_pass is False else 'N/A'}")
                            except Exception:
                                ui.append_hypot_log(f"Measured {config_name} LEFT: {avg:.1f} Ω")
                            
                            # Update RIGHT
                            r_pass = None
                            if rmin is not None and rmax is not None:
                                r_pass = (rmin <= avg <= rmax)
                            ui.update_measurement("R", row_idx, f"{config_name}: {avg:.1f} Ω", r_pass)
                            QtWidgets.QApplication.processEvents()
                            try:
                                ui.append_measurement_log(f"Measured {config_name} RIGHT: {avg:.1f} Ω - {'OK' if r_pass else 'FAIL' if r_pass is False else 'N/A'}")
                            except Exception:
                                ui.append_hypot_log(f"Measured {config_name} RIGHT: {avg:.1f} Ω")
                        else:
                            left_vals.append(0.0)
                            right_vals.append(0.0)
                            self.log.warning(f"MEAS: {config_name} - no valid readings collected")
                            # Update UI with error
                            ui.update_measurement("L", row_idx, f"{config_name}: ERROR", False)
                            ui.update_measurement("R", row_idx, f"{config_name}: ERROR", False)
                            QtWidgets.QApplication.processEvents()
                    else:
                        left_vals.append(0.0)
                        right_vals.append(0.0)
                        self.log.warning(f"MEAS: {config_name} - mode not detected after {max_attempts} attempts")
                        # Update UI with timeout error
                        ui.update_measurement("L", row_idx, f"{config_name}: TIMEOUT", False)
                        ui.update_measurement("R", row_idx, f"{config_name}: TIMEOUT", False)
                        QtWidgets.QApplication.processEvents()
                    
                    # Open relays
                    self.log.info(f"MEAS: Opening relays for {config_name}")
                    try:
                        open_func(self.relay_driver, delay_ms=100.0, logger=self.log)
                        self.log.info(f"MEAS: Relays opened successfully")
                    except Exception as e:
                        self.log.error(f"MEAS: Failed to open relays: {e}", exc_info=True)
                    
                except Exception as e:
                    self.log.error(f"MEAS: CRITICAL ERROR measuring {config_name}: {e}", exc_info=True)
                    left_vals.append(0.0)
                    right_vals.append(0.0)
                    # Try to open relays on error
                    try:
                        self.log.info(f"MEAS: Emergency relay open after error")
                        open_func(self.relay_driver, delay_ms=100.0, logger=self.log)
                    except Exception:
                        pass
        else:
            # Simulated readings for left/right (fallback when no hardware)
            self.log.info("MEAS: Using simulated values (no meter hardware)")
            left_vals = [6.0, 7.0, 6.0]
            right_vals = [6.0, 7.0, 6.0]
            
            # For simulated mode, need to update UI with fake values
            # Determine expected resistance range from selected configuration if present
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

            # If no range was provided via the selected configuration, try reading the
            # mapping from the ConfigurationWindow.RESISTANCE_RANGE so the UI can
            # still color pass/fail boxes even when a configuration dialog wasn't used.
            if rmin is None or rmax is None:
                try:
                    from element_tester.system.ui.configuration_ui import ConfigurationWindow
                    key = None
                    if cfg and isinstance(cfg, dict) and cfg.get("voltage") and cfg.get("wattage"):
                        key = (int(cfg.get("voltage")), int(cfg.get("wattage")))
                    # If key not set or not found, fallback to (208, 7000) if present
                    if key is None or key not in ConfigurationWindow.RESISTANCE_RANGE:
                        key = (208, 7000)
                    if key in ConfigurationWindow.RESISTANCE_RANGE:
                        rmin, rmax = ConfigurationWindow.RESISTANCE_RANGE[key]
                        # Log the expected resistance into the measurement log area
                        try:
                            ui.append_measurement_log(f"Expected resistance for {key[0]}V/{key[1]}W: {rmin:.1f} - {rmax:.1f} Ω")
                        except Exception:
                            ui.append_hypot_log(f"Expected resistance for {key[0]}V/{key[1]}W: {rmin:.1f} - {rmax:.1f} Ω")
                except Exception:
                    # If import fails, leave rmin/rmax as None
                    pass

        values = {}

        # For simulated mode only, update UI with fake measurements
        if not use_real_meter:
            row_names = ["Pin 1 to 6", "Pin 2 to 5", "Pin 3 to 4"]
            for idx in range(3):
                # Left measurement
                l_val = float(left_vals[idx])
                l_pass = None
                if rmin is not None and rmax is not None:
                    l_pass = (rmin <= l_val <= rmax)
                ui.update_measurement("L", idx, f"{row_names[idx]}: {l_val:.2f} Ω", l_pass)
                QtWidgets.QApplication.processEvents()
                try:
                    ui.append_measurement_log(f"Measured {row_names[idx]} LEFT: {l_val:.2f} Ω - {'OK' if l_pass else 'FAIL' if l_pass is False else 'N/A'}")
                except Exception:
                    ui.append_hypot_log(f"Measured row {idx+1} LEFT: {l_val:.2f} Ω")
                time.sleep(0.6)

                # Right measurement
                r_val = float(right_vals[idx])
                r_pass = None
                if rmin is not None and rmax is not None:
                    r_pass = (rmin <= r_val <= rmax)
                ui.update_measurement("R", idx, f"{row_names[idx]}: {r_val:.2f} Ω", r_pass)
                QtWidgets.QApplication.processEvents()
                try:
                    ui.append_measurement_log(f"Measured {row_names[idx]} RIGHT: {r_val:.2f} Ω - {'OK' if r_pass else 'FAIL' if r_pass is False else 'N/A'}")
                except Exception:
                    ui.append_hypot_log(f"Measured row {idx+1} RIGHT: {r_val:.2f} Ω")
                time.sleep(0.6)

                # store raw values for results
                values[f"LP{idx+1}to6"] = l_val
                values[f"RP{idx+1}to6"] = r_val
        
        # Store values from real measurements (already in left_vals/right_vals)
        if use_real_meter:
            for idx in range(len(left_vals)):
                values[f"LP{idx+1}to6"] = left_vals[idx]
                values[f"RP{idx+1}to6"] = right_vals[idx]

        # Decide overall pass: all measured values within range (if range provided)
        cfg = getattr(self, "_selected_config", None)
        rmin = rmax = None
        if cfg and isinstance(cfg, dict):
            rr = cfg.get("resistance_range")
            if isinstance(rr, (list, tuple)) and len(rr) == 2:
                try:
                    rmin = float(rr[0])
                    rmax = float(rr[1])
                except Exception:
                    pass
        
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

    # Default to hardware mode; enable simulate only when --simulate provided.
    runner = TestRunner(simulate=bool(args.simulate))

    # Keep persistent references to prevent GC closing windows
    class _WindowHolder:
        main: Optional[MainTestWindow] = None
        scan: Optional[ScanWindow] = None
    window_refs = _WindowHolder()

    def show_scan_window():
        """Show or create the scanning window."""
        if window_refs.scan is None:
            scan = ScanWindow()
            scan.scanCompleted.connect(on_scan_completed)
            window_refs.scan = scan
        window_refs.scan.show()
        window_refs.scan.raise_()
        window_refs.scan.activateWindow()

    def on_scan_completed(wo: str, pn: str):
        # Hide scanning window and show configuration dialog first
        if window_refs.scan:
            window_refs.scan.hide()

        # Show configuration UI to choose voltage/wattage
        try:
            from element_tester.system.ui.configuration_ui import ConfigurationWindow
        except Exception:
            ConfigurationWindow = None

        selected: dict | None = None
        if ConfigurationWindow is not None:
            cfg = ConfigurationWindow.get_configuration(None, wo, pn)
            if cfg is None:
                # User cancelled configuration - return to scanning with cleared fields
                show_scan_window()
                return
            if cfg is not None:
                # cfg may be (voltage, wattage) or (voltage, wattage, (rmin, rmax))
                v = int(cfg[0])
                w = int(cfg[1])
                selected: dict = {"voltage": v, "wattage": w}
                if len(cfg) > 2 and isinstance(cfg[2], (list, tuple)) and len(cfg[2]) == 2:
                    try:
                        rmin = float(cfg[2][0])
                        rmax = float(cfg[2][1])
                        selected["resistance_range"] = (rmin, rmax)
                    except Exception:
                        selected["resistance_range"] = (0.0, 0.0)

        # Store selected config on runner for later use
        runner._selected_config = selected  # type: ignore[attr-defined]

        # Now create and show main testing window
        main = MainTestWindow()
        main.show()
        # Persist reference so the window isn't garbage collected
        window_refs.main = main
        # Also store on runner for easy access elsewhere if needed
        runner._main_window = main  # type: ignore[attr-defined]

        # Optionally show the chosen settings in the hypot log
        if selected:
            # Write selected config and resistance range into the measurement log
            try:
                main.append_measurement_log(f"Selected config: {selected['voltage']}V, {selected['wattage']}W")
            except Exception:
                main.append_hypot_log(f"Selected config: {selected['voltage']}V, {selected['wattage']}W")

            # Also show resistance range if provided by the configuration dialog
            rr = selected.get("resistance_range")
            if rr is not None and isinstance(rr, (list, tuple)) and len(rr) == 2:
                rmin, rmax = rr
                if rmin == 0.0 and rmax == 0.0:
                    try:
                        main.append_measurement_log(f"Resistance range: not configured for {selected['voltage']} V / {selected['wattage']} W")
                    except Exception:
                        main.append_hypot_log(f"Resistance range: not configured for {selected['voltage']} V / {selected['wattage']} W")
                else:
                    try:
                        main.append_measurement_log(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")
                    except Exception:
                        main.append_hypot_log(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")

        # Set return-to-scan callback on runner
        runner._return_to_scan_callback = show_scan_window  # type: ignore[attr-defined]

        # Start the run (simulate decision already made in run_full_sequence)
        runner.run_full_sequence(main, wo, pn)

    # Show initial scan window
    show_scan_window()
    sys.exit(app.exec())
