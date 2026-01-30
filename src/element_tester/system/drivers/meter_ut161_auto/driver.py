"""
=================
UT61E Auto Driver (public façade)
=================

Public API for UT161E multimeter driver with direct HID communication.
Single entry point with error handling and clean interface.

This driver reads directly from HID device without requiring
the UT61E+ software to be running.
"""
from __future__ import annotations
from typing import Optional
import logging

from .procedures import UT61EAutoProcedures
from .commands import MeterReading
from .errors import UT61EAutoError, UT61EAutoTimeoutError


class UT61EAutoDriver:
    """
    Public driver for UNI-T UT161E multimeter via direct HID.
    
    This driver communicates directly with the Cyrustek ES51922 chip
    via HID, without requiring external software.
    
    Usage:
        meter = UT61EAutoDriver(vendor_id=0x1a86, product_id=0xe429, simulate=False)
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
        simulate: bool = False,
        timeout_ms: int = 5000,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize UT161E auto driver.
        
        Args:
            vendor_id: USB vendor ID (0x1a86 for WCH bridge)
            product_id: USB product ID (0xe429 for UT161E)
            simulate: if True, simulate readings without hardware
            timeout_ms: read timeout in milliseconds
            logger: optional logger instance
        """
        self.log = logger or logging.getLogger("element_tester.driver.ut61e_auto")
        self.proc = UT61EAutoProcedures(
            vendor_id=vendor_id,
            product_id=product_id,
            timeout_ms=timeout_ms,
            simulate=simulate,
            logger=self.log,
        )

    # ---- Lifecycle ----
    def initialize(self) -> None:
        """Open connection to meter"""
        try:
            self.proc.init()
        except Exception as e:
            raise UT61EAutoError(f"Failed to initialize UT61E Auto: {e}") from e

    def shutdown(self) -> None:
        """Close connection to meter"""
        try:
            self.proc.close()
        except Exception as e:
            self.log.error(f"Error during UT61E Auto shutdown: {e}")

    # ---- Reading methods ----
    def read_value(self, max_retries: int = 3) -> MeterReading:
        """
        Read current displayed value (whatever mode meter is in).
        
        Args:
            max_retries: number of retry attempts on error
            
        Returns:
            MeterReading with value, unit, mode, and flags
            
        Raises:
            UT61EAutoError on read failure after retries
        """
        try:
            return self.proc.read_once(max_retries=max_retries)
        except TimeoutError as e:
            raise UT61EAutoTimeoutError(f"Timeout reading from UT61E Auto: {e}") from e
        except Exception as e:
            raise UT61EAutoError(f"Failed to read from UT61E Auto: {e}") from e

    def read_resistance(self, average_count: int = 5) -> float:
        """
        Read resistance value in Ohms.
        
        IMPORTANT: Meter must be manually set to resistance mode before calling.
        
        Args:
            average_count: number of samples to average (default 5)
            
        Returns:
            Resistance in Ohms (float)
            
        Raises:
            UT61EAutoError on read failure
        """
        try:
            return self.proc.read_resistance(average_count=average_count)
        except Exception as e:
            raise UT61EAutoError(f"Failed to read resistance: {e}") from e

    def read_averaged(self, sample_count: int = 5, delay_s: float = 0.5) -> MeterReading:
        """
        Read multiple samples and return averaged result.
        
        Args:
            sample_count: number of samples to average
            delay_s: delay between samples in seconds
            
        Returns:
            MeterReading with averaged value
            
        Raises:
            UT61EAutoError on read failure
        """
        try:
            return self.proc.read_averaged(sample_count=sample_count, delay_s=delay_s)
        except Exception as e:
            raise UT61EAutoError(f"Failed to read averaged value: {e}") from e

    def wait_for_stable(
        self,
        timeout_s: float = 10.0,
        stability_threshold: float = 0.05
    ) -> MeterReading:
        """
        Wait for reading to stabilize.
        
        Args:
            timeout_s: maximum time to wait
            stability_threshold: maximum relative variation (0.05 = 5%)
            
        Returns:
            MeterReading once stable
            
        Raises:
            UT61EAutoTimeoutError if not stable within timeout
        """
        try:
            return self.proc.wait_for_stable(
                timeout_s=timeout_s,
                stability_threshold=stability_threshold
            )
        except TimeoutError as e:
            raise UT61EAutoTimeoutError(f"Reading did not stabilize: {e}") from e
        except Exception as e:
            raise UT61EAutoError(f"Failed waiting for stable reading: {e}") from e

    # ---- Utility methods ----
    @staticmethod
    def list_hid_devices() -> list:
        """
        List available HID devices on the system.
        
        Returns:
            List of dict with vendor_id, product_id, manufacturer, product
        """
        try:
            import hid
            devices = hid.enumerate()
            return [
                {
                    'vendor_id': f"0x{d['vendor_id']:04x}",
                    'product_id': f"0x{d['product_id']:04x}",
                    'manufacturer': d.get('manufacturer_string', ''),
                    'product': d.get('product_string', ''),
                }
                for d in devices
                if d['vendor_id'] == 0x1a86  # Filter for WCH devices
            ]
        except ImportError:
            return []
        except Exception as e:
            logging.warning(f"Failed to list HID devices: {e}")
            return []

    def get_device_info(self) -> dict:
        """
        Get information about current HID device connection.
        
        Returns:
            Dict with vendor_id, product_id, and connection status
        """
        return {
            'vendor_id': f"0x{self.proc.transport.p.vendor_id:04x}",
            'product_id': f"0x{self.proc.transport.p.product_id:04x}",
            'is_open': self.proc.transport.is_open(),
            'simulate': self.proc.transport.p.simulate,
        }
