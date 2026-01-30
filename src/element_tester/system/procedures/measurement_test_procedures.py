"""
Measurement Test Procedures

High-level procedures for executing resistance measurement tests.
Contains reusable test sequences and relay configurations for measuring
resistance between specific pins on the DUT.

Usage:
    import element_tester.system.procedures.measurement_test_procedures as meas_procs
    
    meas_procs.close_pin1to6(relay_driver)
    resistance = meter.read_resistance()
    meas_procs.open_all_relays(relay_driver)

Relay Mapping (adjust based on your actual hardware):
- Relay 0: Left side pin 1
- Relay 1: Left side pin 2
- Relay 2: Left side pin 3
- Relay 3: Meter position
- Relay 4: Right side pin 1
- Relay 5: Right side pin 2
- Relay 6: Right side pin 3
- Relay 7: Hipot circuit (not used for measurements)
"""
from __future__ import annotations
import logging
import time
from typing import Optional, Callable

from element_tester.system.drivers.relay_mcc.driver import ERB08Driver

# Module logger
_log = logging.getLogger("element_tester.procedures.measurement_test")


# ==================== Pin Configuration Functions ====================
# These functions delegate to the relay driver's pin-specific methods.
# The actual relay logic is implemented in ERB08Driver to avoid duplication.

def close_pin1to6(
    relay_driver: ERB08Driver,
    delay_ms: float = 200.0,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Close relays to measure resistance between pin 1 and pin 6.
    Delegates to the relay driver's close_pin1to6() method.
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Settling delay after relay closure in milliseconds
        logger: Optional logger instance (passed for consistency, used by driver)
    """
    log = logger or _log
    try:
        relay_driver.close_pin1to6(delay_ms=delay_ms)
    except Exception as e:
        log.error(f"Failed to close Pin1to6: {e}")
        raise


def open_pin1to6(
    relay_driver: ERB08Driver,
    delay_ms: float = 100.0,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Open relays after pin 1 to pin 6 measurement.
    Delegates to the relay driver's open_pin1to6() method.
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Delay after opening relays in milliseconds
        logger: Optional logger instance (passed for consistency, used by driver)
    """
    log = logger or _log
    try:
        relay_driver.open_pin1to6(delay_ms=delay_ms)
    except Exception as e:
        log.error(f"Failed to open Pin1to6: {e}")
        raise


def close_pin2to5(
    relay_driver: ERB08Driver,
    delay_ms: float = 200.0,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Close relays to measure resistance between pin 2 and pin 5.
    Delegates to the relay driver's close_pin2to5() method.
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Settling delay after relay closure in milliseconds
        logger: Optional logger instance (passed for consistency, used by driver)
    """
    log = logger or _log
    try:
        relay_driver.close_pin2to5(delay_ms=delay_ms)
    except Exception as e:
        log.error(f"Failed to close Pin2to5: {e}")
        raise


def open_pin2to5(
    relay_driver: ERB08Driver,
    delay_ms: float = 100.0,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Open relays after pin 2 to pin 5 measurement.
    Delegates to the relay driver's open_pin2to5() method.
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Delay after opening relays in milliseconds
        logger: Optional logger instance (passed for consistency, used by driver)
    """
    log = logger or _log
    try:
        relay_driver.open_pin2to5(delay_ms=delay_ms)
    except Exception as e:
        log.error(f"Failed to open Pin2to5: {e}")
        raise


def close_pin3to4(
    relay_driver: ERB08Driver,
    delay_ms: float = 200.0,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Close relays to measure resistance between pin 3 and pin 4.
    Delegates to the relay driver's close_pin3to4() method.
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Settling delay after relay closure in milliseconds
        logger: Optional logger instance (passed for consistency, used by driver)
    """
    log = logger or _log
    try:
        relay_driver.close_pin3to4(delay_ms=delay_ms)
    except Exception as e:
        log.error(f"Failed to close Pin3to4: {e}")
        raise


def open_pin3to4(
    relay_driver: ERB08Driver,
    delay_ms: float = 100.0,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Open relays after pin 3 to pin 4 measurement.
    Delegates to the relay driver's open_pin3to4() method.
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Delay after opening relays in milliseconds
        logger: Optional logger instance (passed for consistency, used by driver)
    """
    log = logger or _log
    try:
        relay_driver.open_pin3to4(delay_ms=delay_ms)
    except Exception as e:
        log.error(f"Failed to open Pin3to4: {e}")
        raise

def open_all_relays(
    relay_driver: ERB08Driver,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Open all relays (safety/cleanup).
    
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
        log.error(f"Failed to open all relays: {e}")
        raise


# ==================== High-Level Test Sequences ====================

def run_measurement_sequence(
    relay_driver: ERB08Driver,
    meter_read_callback: Callable[[], float],
    expected_values: Optional[dict] = None,
    tolerance: float = 1.0,
    logger: Optional[logging.Logger] = None
) -> dict:
    """
    Run complete measurement sequence for all pin combinations.
    
    Args:
        relay_driver: ERB08 relay board driver
        meter_read_callback: Function to call to read resistance from meter
        expected_values: Optional dict of expected resistance values for validation
        tolerance: Tolerance in ohms for pass/fail (default 1.0 ohm)
        logger: Optional logger instance
    
    Returns:
        Dictionary with measurement results for each pin combination
    """
    log = logger or _log
    results = {}
    
    try:
        # Measure pin 1-6
        close_pin1to6(relay_driver, logger)
        time.sleep(0.5)
        resistance = meter_read_callback()
        results['LP1to6'] = resistance
        open_all_relays(relay_driver, logger)
        time.sleep(0.2)
        
        # Measure pin 2-5
        close_pin2to5(relay_driver, logger)
        time.sleep(0.5)
        resistance = meter_read_callback()
        results['LP2to5'] = resistance
        open_all_relays(relay_driver, logger)
        time.sleep(0.2)
        
        # Measure pin 3-4
        close_pin3to4(relay_driver, logger)
        time.sleep(0.5)
        resistance = meter_read_callback()
        results['LP3to4'] = resistance
        open_all_relays(relay_driver, logger)
        time.sleep(0.2)
        
        # Log results
        log.info("Measurement results:")
        for pin_combo, value in results.items():
            log.info(f"  {pin_combo}: {value} Ω")
        
        return results
        
    except Exception as e:
        log.error(f"Measurement sequence failed: {e}", exc_info=True)
        # Safety: ensure relays are off
        try:
            open_all_relays(relay_driver, logger)
        except Exception as relay_err:
            log.critical(f"CRITICAL: Failed to turn off relays after error: {relay_err}")
        raise
