"""
=================
UT61E Driver (public façade)
=================

Public API for UT61E multimeter driver.
Single entry point with error handling and clean interface.
"""
from __future__ import annotations
from typing import Optional
import logging

from .procedures import UT61EProcedures
from .commands import MeterReading
from .errors import UT61EError, UT61ETimeoutError


class UT61EDriver:
    """
    Public driver for UNI-T UT61E multimeter via USB HID.
    
    Usage:
        meter = UT61EDriver(simulate=False)
        meter.initialize()
        
        # Read resistance (main use case for element tester)
        resistance = meter.read_resistance()
        print(f"Resistance: {resistance} Ohms")
        
        # Read any displayed value
        reading = meter.read_value()
        print(f"{reading.value} {reading.unit}")
        
        meter.shutdown()
    """

    def __init__(
        self,
        vendor_id: int = 0x1a86,
        product_id: int = 0xe429,
        serial_number: Optional[str] = None,
        simulate: bool = False,
        timeout_ms: int = 5000,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize UT61E driver.
        
        Args:
            vendor_id: USB vendor ID (0x1a86 for WCH bridge)
            product_id: USB product ID (0xe429 for UT61E Plus with WCH UART TO KB-MS)
            serial_number: Optional serial number to identify specific device
            simulate: if True, simulate readings without hardware
            timeout_ms: read timeout in milliseconds
            logger: optional logger instance
        """
        self.log = logger or logging.getLogger("element_tester.driver.ut61e")
        self.proc = UT61EProcedures(
            vendor_id=vendor_id,
            product_id=product_id,
            serial_number=serial_number,
            simulate=simulate,
            timeout_ms=timeout_ms,
            logger=self.log,
        )

    # ---- Lifecycle ----
    def initialize(self) -> None:
        """Open connection to meter"""
        try:
            self.proc.init()
        except Exception as e:
            raise UT61EError(f"Failed to initialize UT61E: {e}") from e

    def shutdown(self) -> None:
        """Close connection to meter"""
        try:
            self.proc.close()
        except Exception as e:
            self.log.error(f"Error during UT61E shutdown: {e}")

    # ---- Reading methods ----
    def read_value(self, max_retries: int = 10) -> MeterReading:
        """
        Read current displayed value (whatever mode meter is in).
        
        Args:
            max_retries: number of retry attempts on error
            
        Returns:
            MeterReading with value, unit, mode, and flags
            
        Raises:
            UT61EError on read failure after retries
        """
        try:
            return self.proc.read_once(max_retries=max_retries)
        except TimeoutError as e:
            raise UT61ETimeoutError(f"Timeout reading from UT61E: {e}") from e
        except Exception as e:
            raise UT61EError(f"Failed to read from UT61E: {e}") from e

    def read_resistance(self, average_count: int = 3) -> Optional[float]:
        """
        Read resistance value (assumes meter is in resistance mode).
        
        This is the primary method for the element tester's measurement phase.
        
        Args:
            average_count: number of samples to average
            
        Returns:
            Average resistance in Ohms, or None if not in resistance mode
            or measurement invalid
            
        Raises:
            UT61EError on communication failure
        """
        try:
            return self.proc.get_resistance(average_count=average_count)
        except TimeoutError as e:
            raise UT61ETimeoutError(f"Timeout reading resistance: {e}") from e
        except Exception as e:
            raise UT61EError(f"Failed to read resistance: {e}") from e

    def read_multiple(self, count: int = 5) -> list[MeterReading]:
        """
        Read multiple measurements.
        
        Useful for stability checking or custom averaging logic.
        """
        try:
            return self.proc.read_multiple(count=count)
        except Exception as e:
            raise UT61EError(f"Failed to read multiple samples: {e}") from e

    # ---- Utility ----
    def flush_buffer(self) -> None:
        """
        Clear any buffered/cached input data from the HID device.
        
        This is critical after relay switching to discard stale readings
        from previous configurations. Call after closing relays and before
        taking measurements.
        """
        try:
            self.proc.transport.flush_input()
        except Exception as e:
            raise UT61EError(f"Failed to flush buffer: {e}") from e
    
    def is_connected(self) -> bool:
        """Check if meter is connected and responding"""
        try:
            reading = self.read_value(max_retries=1)
            return reading is not None
        except Exception:
            return False

    def get_last_reading(self) -> Optional[MeterReading]:
        """Get the last successful reading (cached)"""
        return self.proc.state.last_reading

    @staticmethod
    def list_devices() -> list[dict]:
        """
        List all HID devices that might be UT61E meters.
        
        Returns list of device info dicts. Useful for finding VID/PID.
        """
        from .transport import UT61ETransport
        return UT61ETransport.list_devices()
