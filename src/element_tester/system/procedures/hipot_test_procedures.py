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
    relay_driver: ERB08Driver,
    hipot_driver: AR3865Driver,
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
        # Step 1: Reset hipot instrument to known state
        log.info("HIPOT: Resetting instrument to known state")
        try:
            hipot_driver.reset()
            time.sleep(0.2)
        except Exception as e:
            raise Exception(f"Failed to reset hipot instrument: {e}") from e
        
        # Step 2: Configure relay for hipot test circuit
        log.info("RELAY: Configuring hipot test circuit (relay 8 ON)")
        try:
            relay_driver.all_off()
            time.sleep(0.1)
            relay_driver.set_relay(7, True)  # Close relay 8 (bit 7 = relay 8)
            relay_closed = True
            time.sleep(1.0)
        except Exception as e:
            raise Exception(f"Failed to configure relay: {e}") from e
        
        # Step 3 & 4: Execute hipot test using stored file
        log.info("HIPOT: Executing test from file 1 (FL 1)")
        try:
            passed, raw_result, actual_test_start_time = hipot_driver.run_from_file(
                file_index=1,
                timeout_s=total_test_duration_s
            )
            test_start_time = actual_test_start_time
        except Exception as e:
            raise Exception(f"Hipot test execution failed: {e}") from e
        
        # Step 5: Log result
        result_str = "PASS ✓" if passed else "FAIL ✗"
        log.info(f"HIPOT: Test complete - {result_str} (raw: {raw_result})")
        
        # Optional: Reset instrument after result
        if reset_after_test:
            elapsed_time = time.time() - test_start_time
            log.info(f"HIPOT: Resetting immediately (elapsed: {elapsed_time:.1f}s from test start)")
            try:
                hipot_driver.reset()
                total_elapsed = time.time() - test_start_time
                log.info(f"HIPOT: Instrument reset at {total_elapsed:.1f}s from test start")
            except Exception as e:
                log.warning(f"Failed to reset instrument: {e}")
        
        # Step 6: Relay management
        if not keep_relay_closed:
            log.info("RELAY: Disabling hipot circuit (all relays OFF)")
            try:
                relay_driver.all_off()
                relay_closed = False
                time.sleep(0.1)
            except Exception as e:
                log.error(f"Failed to turn off relays: {e}")
        else:
            log.info("RELAY: Keeping relay 8 closed (keep_relay_closed=True)")
        
        return passed, raw_result
        
    except Exception as e:
        log.error(f"HIPOT: Test sequence failed: {e}", exc_info=True)
        # Safety: ensure relays are off on error
        if relay_closed and not keep_relay_closed:
            try:
                log.warning("Emergency relay shutdown due to test failure")
                relay_driver.all_off()
            except Exception as relay_err:
                log.critical(f"CRITICAL: Failed to turn off relays after error: {relay_err}")
        raise


def close_hipot_relay(
    relay_driver: ERB08Driver,
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
        relay_driver.all_off()
        time.sleep(0.1)
        relay_driver.set_relay(7, True)
        time.sleep(0.2)
        log.info("RELAY: Relay 8 closed for hipot circuit")
    except Exception as e:
        log.error(f"Failed to close relay: {e}")
        raise


def open_all_relays(
    relay_driver: ERB08Driver,
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
        relay_driver.all_off()
        time.sleep(0.1)
        log.info("RELAY: All relays opened")
    except Exception as e:
        log.error(f"Failed to open relays: {e}")
        raise
