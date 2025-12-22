"""
=================
UT61E Procedures (higher-level flows)
=================

Practical sequences for using the UT61E meter.
Handles session management, retries, averaging, etc.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import logging

from .transport import UT61ETransport, UT61EOpenParams
from .commands import UT61ECommands, MeterReading


@dataclass
class SessionState:
    """Track session state"""
    is_open: bool = False
    last_reading: Optional[MeterReading] = None


class UT61EProcedures:
    """
    Higher-level procedures for UT61E meter.
    
    Provides practical workflows:
    - Session management (init, close)
    - Read with retry logic
    - Read multiple samples and average
    - Wait for stable reading
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
        self.log = logger or logging.getLogger("element_tester.meter_ut61e")
        
        params = UT61EOpenParams(
            vendor_id=vendor_id,
            product_id=product_id,
            serial_number=serial_number,
            simulate=simulate,
            timeout_ms=timeout_ms,
        )
        
        self.transport = UT61ETransport(params)
        self.cmd = UT61ECommands(self.transport)
        self.state = SessionState()

    # ---------- Session ----------
    def init(self) -> None:
        """Open connection to meter"""
        if self.state.is_open:
            self.log.warning("UT61E already initialized")
            return

        self.log.info(
            f"UT61E: Opening HID device (VID=0x{self.transport.p.vendor_id:04x}, "
            f"PID=0x{self.transport.p.product_id:04x})"
        )
        self.transport.open()
        self.state.is_open = True
        
        # Flush any buffered data
        self.transport.flush_input()
        
        self.log.info("UT61E: Initialized")

    def close(self) -> None:
        """Close connection to meter"""
        if not self.state.is_open:
            return

        self.log.info("UT61E: Closing")
        self.transport.close()
        self.state.is_open = False

    # ---------- Single reading ----------
    def read_once(self, max_retries: int = 3) -> MeterReading:
        """
        Read one measurement from the meter with retry logic.
        
        Args:
            max_retries: number of retry attempts on error
            
        Returns:
            MeterReading with current displayed value
            
        Raises:
            Exception if all retries fail
        """
        if not self.state.is_open:
            self.init()

        last_error = None
        for attempt in range(max_retries):
            try:
                reading = self.cmd.cmd_read_parsed()
                self.state.last_reading = reading
                
                self.log.debug(
                    f"UT61E: Read {reading.value} {reading.unit} "
                    f"({reading.mode}, OL={reading.is_overload})"
                )
                
                return reading
                
            except Exception as e:
                last_error = e
                self.log.warning(f"UT61E: Read attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    self.transport.flush_input()
        
        raise Exception(f"UT61E: Failed to read after {max_retries} attempts: {last_error}")

    # ---------- Multiple readings ----------
    def read_multiple(self, count: int = 5) -> list[MeterReading]:
        """
        Read multiple measurements.
        
        Useful for averaging or checking stability.
        """
        if not self.state.is_open:
            self.init()

        readings = []
        for i in range(count):
            try:
                reading = self.read_once()
                readings.append(reading)
            except Exception as e:
                self.log.error(f"UT61E: Failed to read sample {i+1}/{count}: {e}")
        
        return readings

    def read_average(self, count: int = 5) -> Optional[float]:
        """
        Read multiple samples and return average value.
        
        Filters out overload readings. Returns None if no valid readings.
        """
        readings = self.read_multiple(count)
        
        valid_values = [
            r.value for r in readings
            if r.value is not None and not r.is_overload
        ]
        
        if not valid_values:
            self.log.warning("UT61E: No valid readings for averaging")
            return None
        
        avg = sum(valid_values) / len(valid_values)
        self.log.info(f"UT61E: Average of {len(valid_values)}/{count} samples: {avg:.3f}")
        
        return avg

    # ---------- Convenience ----------
    def get_resistance(self, average_count: int = 3) -> Optional[float]:
        """
        Read resistance value (assumes meter is in resistance mode).
        
        Returns average of multiple readings, or None if not in resistance mode
        or measurement invalid.
        
        This is the main method for the test system's resistance measurement.
        """
        if not self.state.is_open:
            self.init()

        self.log.info(f"UT61E: Reading resistance (averaging {average_count} samples)")
        
        readings = self.read_multiple(average_count)
        
        # Filter for resistance readings
        resistance_values = [
            r.value for r in readings
            if r.value is not None 
            and not r.is_overload
            and 'Ohm' in r.unit  # Check for resistance unit
        ]
        
        if not resistance_values:
            self.log.warning("UT61E: No valid resistance readings found")
            # Check if meter is in wrong mode
            if readings:
                last = readings[-1]
                self.log.warning(f"UT61E: Meter appears to be in {last.mode} mode (expected Resistance)")
            return None
        
        avg_resistance = sum(resistance_values) / len(resistance_values)
        self.log.info(f"UT61E: Resistance = {avg_resistance:.3f} Ohm (from {len(resistance_values)} samples)")
        
        return avg_resistance
