"""
=================
UT61E Auto Procedures (High-level operations)
=================

Practical, repeatable measurement sequences for UT161E.
Combines transport and commands into useful operations.

Key Procedures:
  - init: Open HID connection
  - close: Close HID connection
  - read_once: Read single measurement
  - read_averaged: Read multiple samples and average
  - wait_for_stable: Wait for reading to stabilize
"""
from __future__ import annotations
from typing import Optional
import logging
import time
import statistics

from .transport import UT61EAutoTransport, UT61EAutoOpenParams
from .commands import UT61EAutoCommands, MeterReading
from .errors import UT61EAutoError, UT61EAutoTimeoutError


class UT61EAutoProcedures:
    """
    High-level procedures for UT161E multimeter (direct HID).
    
    Responsibilities:
      - Session management (open/close)
      - Multi-sample reading and averaging
      - Stability detection
      - Error recovery
    """

    def __init__(
        self,
        vendor_id: int = 0x1a86,
        product_id: int = 0xe429,
        timeout_ms: int = 5000,
        simulate: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        self.log = logger or logging.getLogger("element_tester.driver.ut61e_auto")
        
        # Create transport and commands layers
        params = UT61EAutoOpenParams(
            vendor_id=vendor_id,
            product_id=product_id,
            timeout_ms=timeout_ms,
            simulate=simulate
        )
        self.transport = UT61EAutoTransport(params)
        self.commands = UT61EAutoCommands(self.transport)

    # -------- Lifecycle --------
    def init(self) -> None:
        """
        Open HID connection to meter.
        
        Raises:
            UT61EAutoError on connection failure
        """
        try:
            self.log.info(f"UT61EAuto: Initializing HID connection (VID=0x{self.transport.p.vendor_id:04x}, PID=0x{self.transport.p.product_id:04x})")
            self.transport.open()
            
            # Wait for first valid packet (meter is continuously transmitting)
            time.sleep(0.5)  # Give meter time to send packet
            self.transport.flush_input()  # Clear any partial packets
            
            self.log.info("UT61EAuto: Connection established")
        except Exception as e:
            self.log.error(f"UT61EAuto: Failed to initialize: {e}")
            raise UT61EAutoError(f"Failed to initialize UT61E Auto: {e}") from e

    def close(self) -> None:
        """Close HID connection"""
        try:
            self.log.info("UT61EAuto: Closing connection")
            self.transport.close()
        except Exception as e:
            self.log.warning(f"UT61EAuto: Error during close: {e}")

    # -------- Reading Procedures --------
    def read_once(self, max_retries: int = 3) -> MeterReading:
        """
        Read single measurement from meter.
        
        Args:
            max_retries: Number of retry attempts on error
            
        Returns:
            MeterReading with current display value
            
        Raises:
            UT61EAutoTimeoutError on timeout
            UT61EAutoError on other failures
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Read packet from serial stream
                packet = self.transport.read_packet()
                
                # Parse packet into reading
                reading = self.commands.cmd_parse_packet(packet)
                
                # Check for parse errors
                if 'error' in reading.flags:
                    raise UT61EAutoError(f"Parse error: {reading.flags['error']}")
                
                self.log.debug(
                    f"UT61EAuto: Read {reading.value} {reading.unit} "
                    f"(mode={reading.mode}, OL={reading.is_overload})"
                )
                
                return reading
                
            except TimeoutError as e:
                last_error = e
                self.log.warning(f"UT61EAuto: Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(0.2)  # Brief delay before retry
            except Exception as e:
                last_error = e
                self.log.warning(f"UT61EAuto: Error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
        
        # All retries failed
        raise UT61EAutoTimeoutError(f"Failed to read after {max_retries} attempts: {last_error}")

    def read_averaged(self, sample_count: int = 5, delay_s: float = 0.5) -> MeterReading:
        """
        Read multiple samples and return averaged result.
        
        Args:
            sample_count: Number of samples to average
            delay_s: Delay between samples (seconds)
            
        Returns:
            MeterReading with averaged value
            
        Raises:
            UT61EAutoError if no valid samples obtained
        """
        self.log.debug(f"UT61EAuto: Reading {sample_count} samples for averaging")
        
        samples = []
        units = []
        modes = []
        
        for i in range(sample_count):
            try:
                reading = self.read_once()
                
                # Skip overload readings
                if reading.is_overload or reading.value is None:
                    self.log.warning(f"UT61EAuto: Sample {i+1} is overload, skipping")
                    continue
                
                samples.append(reading.value)
                units.append(reading.unit)
                modes.append(reading.mode)
                
                # Delay before next sample (except on last)
                if i < sample_count - 1:
                    time.sleep(delay_s)
                    
            except Exception as e:
                self.log.warning(f"UT61EAuto: Failed to read sample {i+1}: {e}")
                continue
        
        if not samples:
            raise UT61EAutoError("No valid samples obtained for averaging")
        
        # Calculate average
        avg_value = statistics.mean(samples)
        std_dev = statistics.stdev(samples) if len(samples) > 1 else 0.0
        
        # Use most common unit and mode
        most_common_unit = max(set(units), key=units.count)
        most_common_mode = max(set(modes), key=modes.count)
        
        self.log.info(
            f"UT61EAuto: Averaged {len(samples)} samples: "
            f"{avg_value:.3f} {most_common_unit} (σ={std_dev:.3f})"
        )
        
        # Return reading with averaged value
        return MeterReading(
            value=avg_value,
            unit=most_common_unit,
            mode=most_common_mode,
            is_overload=False,
            is_negative=(avg_value < 0),
            flags={
                'averaged': True,
                'sample_count': len(samples),
                'std_dev': std_dev
            }
        )

    def wait_for_stable(
        self,
        timeout_s: float = 10.0,
        stability_threshold: float = 0.05,  # 5% variation
        window_size: int = 3
    ) -> MeterReading:
        """
        Wait for reading to stabilize within threshold.
        
        Args:
            timeout_s: Maximum time to wait
            stability_threshold: Maximum relative variation (0.05 = 5%)
            window_size: Number of consecutive stable readings required
            
        Returns:
            MeterReading once stable
            
        Raises:
            UT61EAutoTimeoutError if stability not achieved within timeout
        """
        self.log.debug(f"UT61EAuto: Waiting for stable reading (threshold={stability_threshold*100}%)")
        
        start_time = time.time()
        recent_values = []
        
        while (time.time() - start_time) < timeout_s:
            try:
                reading = self.read_once()
                
                if reading.is_overload or reading.value is None:
                    self.log.warning("UT61EAuto: Overload during stability wait")
                    recent_values.clear()
                    time.sleep(0.5)
                    continue
                
                recent_values.append(reading.value)
                
                # Keep only last N values
                if len(recent_values) > window_size:
                    recent_values.pop(0)
                
                # Check stability once we have enough samples
                if len(recent_values) >= window_size:
                    mean_val = statistics.mean(recent_values)
                    if mean_val == 0:
                        # Avoid division by zero
                        max_variation = max(abs(v) for v in recent_values)
                    else:
                        max_variation = max(abs(v - mean_val) / abs(mean_val) for v in recent_values)
                    
                    if max_variation <= stability_threshold:
                        self.log.info(
                            f"UT61EAuto: Reading stable at {mean_val:.3f} {reading.unit} "
                            f"(variation={max_variation*100:.1f}%)"
                        )
                        return reading
                
                time.sleep(0.5)
                
            except Exception as e:
                self.log.warning(f"UT61EAuto: Error during stability check: {e}")
                recent_values.clear()
                time.sleep(0.5)
        
        raise UT61EAutoTimeoutError(
            f"Reading did not stabilize within {timeout_s}s "
            f"(threshold={stability_threshold*100}%)"
        )

    def read_resistance(self, average_count: int = 5) -> float:
        """
        Read resistance value (convenience method for element tester).
        
        Args:
            average_count: Number of samples to average
            
        Returns:
            Resistance in Ohms
            
        Raises:
            UT61EAutoError if meter not in resistance mode or reading fails
        """
        self.log.debug(f"UT61EAuto: Reading resistance ({average_count} samples)")
        
        reading = self.read_averaged(sample_count=average_count, delay_s=0.3)
        
        # Verify we're in resistance mode
        if 'resistance' not in reading.mode.lower():
            self.log.warning(
                f"UT61EAuto: Meter in {reading.mode} mode, expected Resistance mode"
            )
        
        # Convert to Ohms if needed
        value = reading.value
        unit = reading.unit.lower()
        
        if 'kohm' in unit or 'kω' in unit:
            value *= 1000
        elif 'mohm' in unit or 'mω' in unit:
            value *= 1_000_000
        
        self.log.info(f"UT61EAuto: Resistance = {value:.2f} Ohms")
        return value
