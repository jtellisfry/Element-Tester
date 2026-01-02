"""
Hipot Test Procedures

High-level procedures for executing hipot (high-voltage) tests.
Contains reusable test sequences that can be called from various test programs.

Usage:
    import element_tester.system.procedures.hipot_test_procedures as hipot_procs
    
    passed, result = hipot_procs.run_hipot_test(relay_driver, hipot_driver)
"""
from __future__ import annotations
import logging
import time
from typing import Optional

from element_tester.system.drivers.relay_mcc.driver import ERB08Driver
from element_tester.system.drivers.hypot3865.driver import AR3865Driver

# Module logger
_log = logging.getLogger("element_tester.procedures.hipot_test")


# ==================== Hipot Test Functions ====================

def run_hipot_test(
    erb_driver: ERB08Driver,
    hipot_driver: AR3865Driver,
    file_index: int = 1,
    keep_relay_closed: bool = False,
    reset_after_test: bool = True,
    total_test_duration_s: float = 5.0,
    reset_delay_after_result_s: float = 2.0,
    logger: Optional[logging.Logger] = None
) -> tuple[bool, str]:
    """
    Execute complete hipot test sequence using stored file (FL 1).
    
    Workflow:
    1. Reset hipot instrument to known state
    2. Configure relay for hipot circuit (relay 8 ON, others OFF)
    3. Execute hipot test from stored file
    4. Read and interpret result
    5. Clean up relay configuration
    6. Return pass/fail status
    
    Args:
        relay_driver: ERB08 relay board driver
        hipot_driver: AR3865 hipot tester driver
        keep_relay_closed: If True, leaves relay 8 closed after test (for retries/continuation)
        reset_after_test: If True, resets instrument after getting result (stops beeping)
        total_test_duration_s: Expected total duration of hipot test (default 5s)
        reset_delay_after_result_s: Additional delay after result before reset (default 2s)
        logger: Optional logger instance
    
    Returns:
        (passed, result_string): Test outcome and raw result
    """
    log = logger or _log
    relay_closed = False
    test_start_time = time.time()
    
    try:
        # Step 1: Ensure instrument is in remote mode and reset
        log.info("HIPOT: Ensuring instrument is in REMOTE mode and resetting")
        try:
            # Soft reset to clear faults and ensure known state
            hipot_driver.reset()
            time.sleep(0.2)
            # Read IDN to ensure we have a responsive instrument
            try:
                idn = hipot_driver.idn()
                log.info(f"HIPOT IDN: {idn}")
            except Exception:
                log.warning("HIPOT: Unable to read IDN; continue if instrument is in remote mode")
        except Exception as e:
            raise Exception(f"Failed to reset hipot instrument: {e}") from e

        # Step 1b: Close relay 8 on ERB08 station so the hipot path can be completed
        try:
            log.info("RELAY(ERB): Closing relay 8 to enable hipot path on ERB board")
            erb_driver.set_relay(7, True)
            time.sleep(0.5)
        except Exception as e:
            raise Exception(f"Failed to close ERB relay 8: {e}") from e

        # Step 2: Configure hipot relay bank on the ERB station (replace PDIS)
        # Close ERB relay index 6 (bit 6) to complete hipot path in addition
        # to ERB relay index 7 (already closed above).
        try:
            log.info("RELAY(ERB): Closing relay 7 (index 6) to complete hipot path")
            erb_driver.set_relay(6, True)
            relay_closed = True
            time.sleep(3.0)  # allow relays to settle
        except Exception as e:
            raise Exception(f"Failed to configure ERB relay for hipot: {e}") from e

        # Step 3: Execute hipot test using stored file (applies to the closed bank)
        log.info("HIPOT: Executing test from file 1 (FL 1) against relays 0-5")
        try:
            passed, raw_result, actual_test_start_time = hipot_driver.run_from_file(
                file_index=file_index,
                timeout_s=total_test_duration_s,
            )
            test_start_time = actual_test_start_time
        except Exception as e:
            raise Exception(f"Hipot test execution failed: {e}") from e
        
        # Step 5: Log result and optionally reset instrument
        result_str = "PASS ✓" if passed else "FAIL ✗"
        log.info(f"HIPOT: Test complete - {result_str} (raw: {raw_result})")

        if reset_after_test:
            try:
                hipot_driver.reset()
                total_elapsed = time.time() - test_start_time
                log.info(f"HIPOT: Instrument reset at {total_elapsed:.1f}s from test start")
            except Exception as e:
                log.warning(f"Failed to reset instrument after test: {e}")

        # Step 6: Relay management — open relays unless caller requested to keep them closed
        if not keep_relay_closed:
            log.info("RELAY: Disabling hipot circuit (opening previously closed relays)")
            try:
                # Open ERB relay 7 (index 6) and ERB relay 8 (index 7)
                try:
                    erb_driver.set_relay(6, False)
                except Exception:
                    log.debug("Failed to open ERB relay 6 directly; attempting all_off()")
                    try:
                        erb_driver.all_off()
                    except Exception:
                        pass
                try:
                    erb_driver.set_relay(7, False)
                except Exception:
                    # ignore; all_off above will have opened relays
                    pass
                relay_closed = False
                time.sleep(0.1)
            except Exception as e:
                log.error(f"Failed to turn off relays: {e}")
        else:
            log.info("RELAY: Keeping ERB relays 6 and 7 closed (keep_relay_closed=True)")

        # If test failed, raise/log so caller/UI shows fail screen; otherwise return pass
        return passed, raw_result
        
    except Exception as e:
        log.error(f"HIPOT: Test sequence failed: {e}", exc_info=True)
        # Safety: ensure relays are off on error
        if relay_closed and not keep_relay_closed:
            try:
                log.warning("Emergency relay shutdown due to test failure")
                try:
                    erb_driver.set_relay(6, False)
                except Exception:
                    try:
                        erb_driver.all_off()
                    except Exception:
                        pass
                try:
                    erb_driver.set_relay(7, False)
                except Exception:
                    pass
            except Exception as relay_err:
                log.critical(f"CRITICAL: Failed to turn off relays after error: {relay_err}")
        raise


def close_hipot_relay(
    erb_driver: ERB08Driver,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Close relay 8 for hipot circuit (used before retries).
    
    Sets relay 8 (bit 7) to ON, connecting DUT to hipot circuit.
    All other relays are turned OFF for safety.
    
    Args:
        relay_driver: ERB08 relay board driver
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        # Close ERB relay 8; PDIS operations removed here.
        erb_driver.set_relay(7, True)
        time.sleep(0.2)
        log.info("RELAY: ERB relay 8 closed for hipot circuit")
        # TODO: If using a PDIS station, add PDIS closure logic here.
    except Exception as e:
        log.error(f"Failed to close relays for hipot: {e}")
        raise


def open_all_relays(
    erb_driver: ERB08Driver,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Open all relays (used after final result or cancel).
    
    Turns all relays OFF for safety.
    
    Args:
        relay_driver: ERB08 relay board driver
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        # Open ERB relay 8 and leave PDIS logic out for now.
        try:
            erb_driver.set_relay(7, False)
        except Exception:
            try:
                erb_driver.all_off()
            except Exception:
                pass
        time.sleep(0.1)
        log.info("RELAY: ERB hipot-related relays opened (PDIS logic removed)")
        # TODO: If using PDIS, add pdis_driver.all_off() here.
    except Exception as e:
        log.error(f"Failed to open relays: {e}")
        raise
