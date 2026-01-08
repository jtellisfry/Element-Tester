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
import concurrent.futures

from element_tester.system.drivers.relay_mcc.driver import ERB08Driver

# Module logger
_log = logging.getLogger("element_tester.procedures.measurement_test")


class MeasurementTimeoutError(RuntimeError):
    """Raised when a meter read operation times out."""




# ==================== Pin Configuration Functions ====================

def close_pin1to6(
    relay_driver: ERB08Driver,
    delay_ms: float = 200.0,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Close relays to measure resistance between pin 1 and pin 6.
    
    Relay mapping:
    - Relay 4: Meter position
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Settling delay after relay closure in milliseconds
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        relay_driver.all_off()
        time.sleep(0.1)
        relay_driver.set_relay(4, True)  # Meter position (relay 5, bit 4)
        time.sleep(0.3)  # Brief settling delay
        time.sleep(delay_ms / 1000.0)
        log.info(f"RELAY: Pin1to6 closed with {delay_ms}ms settling delay")
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
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Delay after opening relays in milliseconds
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        relay_driver.all_off()
        time.sleep(delay_ms / 1000.0)
        log.info(f"RELAY: Pin1to6 opened with {delay_ms}ms delay")
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
    
    Relay mapping:
    - Relay 0: Pin 2
    - Relay 4: Meter position
    - Relay 1: Pin 5
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Settling delay after relay closure in milliseconds
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        relay_driver.all_off()
        time.sleep(0.05)
        relay_driver.set_relay(0, True)  # Pin 2
        relay_driver.set_relay(4, True)  # Meter position
        relay_driver.set_relay(1, True)  # Pin 5
        time.sleep(delay_ms / 1000.0)
        log.info(f"RELAY: Pin2to5 closed with {delay_ms}ms settling delay")
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
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Delay after opening relays in milliseconds
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        relay_driver.all_off()
        time.sleep(delay_ms / 1000.0)
        log.info(f"RELAY: Pin2to5 opened with {delay_ms}ms delay")
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
    
    Relay mapping:
    - Relay 2: Pin 3
    - Relay 4: Meter position
    - Relay 3: Pin 4
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Settling delay after relay closure in milliseconds
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        relay_driver.all_off()
        time.sleep(0.05)
        relay_driver.set_relay(2, True)  # Pin 3
        relay_driver.set_relay(3, True)  # Pin 4
        time.sleep(delay_ms / 1000.0)
        log.info(f"RELAY: Pin3to4 closed with {delay_ms}ms settling delay")
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
    
    Args:
        relay_driver: ERB08 relay board driver
        delay_ms: Delay after opening relays in milliseconds
        logger: Optional logger instance
    """
    log = logger or _log
    try:
        relay_driver.all_off()
        time.sleep(delay_ms / 1000.0)
        log.info(f"RELAY: Pin3to4 opened with {delay_ms}ms delay")
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
    timeout_s: float = 10.0,
    logger: Optional[logging.Logger] = None
) -> dict:
    """
    Run complete measurement sequence for all pin combinations.

    Args:
        relay_driver: ERB08 relay board driver
        meter_read_callback: Function to call to read resistance from meter
        expected_values: Optional dict of expected resistance values for validation
        tolerance: Tolerance in ohms for pass/fail (default 1.0 ohm)
        timeout_s: Per-read timeout in seconds (default 10.0)
        logger: Optional logger instance

    Returns:
        Dictionary with measurement results for each pin combination. Values
        will be `None` if a read failed or timed out.
    """
    log = logger or _log
    results = {}
    
    def _read_with_timeout() -> Optional[float]:
        """Call the meter read callback with a timeout. Raises
        MeasurementTimeoutError on timeout so callers/UI can present a retry
        screen with a specific message.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(meter_read_callback)
            try:
                return fut.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                log.error(f"Measurement read timed out after {timeout_s} seconds")
                raise MeasurementTimeoutError(
                    f"Measurement timed out after {timeout_s} seconds"
                )

    try:
        # Measure pin 1-6
        close_pin1to6(relay_driver, logger)
        time.sleep(0.5)
        resistance = _read_with_timeout()
        results['LP1to6'] = resistance
        open_all_relays(relay_driver, logger)
        time.sleep(0.2)

        # Measure pin 2-5
        close_pin2to5(relay_driver, logger)
        time.sleep(0.5)
        resistance = _read_with_timeout()
        results['LP2to5'] = resistance
        open_all_relays(relay_driver, logger)
        time.sleep(0.2)

        # Measure pin 3-4
        close_pin3to4(relay_driver, logger)
        time.sleep(0.5)
        resistance = _read_with_timeout()
        results['LP3to4'] = resistance
        open_all_relays(relay_driver, logger)
        time.sleep(0.2)

        # Log results
        log.info("Measurement results:")
        for pin_combo, value in results.items():
            log.info(f"  {pin_combo}: {value} Ω")

        return results

    except Exception as e:
        # If the exception was a timeout, ensure the message propagates so
        # the UI can present a retry screen noting a timeout specifically.
        if isinstance(e, MeasurementTimeoutError):
            log.error(f"Measurement sequence timed out: {e}")
        else:
            log.error(f"Measurement sequence failed: {e}", exc_info=True)

        # Safety: ensure relays are off
        try:
            open_all_relays(relay_driver, logger)
        except Exception as relay_err:
            log.critical(f"CRITICAL: Failed to turn off relays after error: {relay_err}")
        raise
