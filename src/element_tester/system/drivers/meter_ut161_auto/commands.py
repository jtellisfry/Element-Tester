"""
=================
UT61E Auto Commands (packet parsing)
=================

Low-level packet parsing for UT161E ASCII protocol via WCH HID bridge.
Decodes ASCII-formatted meter readings from HID reports.

UT161E HID packet structure (via WCH UART-to-KB/MS bridge):
- Header: 0x13 0xAB 0xCD 0x10 0x06
- ASCII payload: mode + space + value (e.g., "1 0.3290")
- Trailer: 0x00 0x06 0x30 0x30 0x30 0x03 + checksum

Mode byte (ASCII):
- '0': Voltage (V)
- '1': Resistance (Ω)
- '2': Current (A)
- '3': Capacitance (F)
- '4': Frequency (Hz)
- '5': Diode/Continuity
- '6': Temperature

LEGO pieces:
  - cmd_parse_packet: Decode HID ASCII packet into MeterReading
  - Mode detection and unit mapping
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .transport import UT61EAutoTransport


@dataclass
class MeterReading:
    """
    Parsed measurement from UT61E meter.
    
    value: numeric reading (None if OL/overload or invalid)
    unit: measurement unit (Ohm, V, A, F, Hz, etc.)
    mode: measurement mode (resistance, DC voltage, AC current, etc.)
    is_overload: True if display shows overload
    is_negative: True if value is negative
    flags: dict of status flags (hold, rel, min, max, etc.)
    raw_packet: original 14-byte packet for debugging
    """
    value: Optional[float]
    unit: str
    mode: str
    is_overload: bool = False
    is_negative: bool = False
    flags: dict = None
    raw_packet: bytes = b''

    def __post_init__(self):
        if self.flags is None:
            self.flags = {}


class UT61EAutoCommands:
    """
    Low-level packet parsing for UT61E (ES51922 protocol via RS-232).
    
    No actual commands are sent - just parsing received packets.
    Protocol based on Cyrustek ES51922 datasheet and community reverse engineering.
    """

    def __init__(self, transport: UT61EAutoTransport):
        self.t = transport
        self._sim_value = 100.0  # For simulate mode

    def cmd_parse_packet(self, packet: bytes) -> MeterReading:
        """
        Parse 14-byte ES51922 packet from UT61E into a MeterReading.
        
        Packet structure:
        [0]: Range byte (bits 6-3 = 0110, bits 2-0 = range)
        [1-5]: Digit bytes (bits 6-4 = 011, bits 3-0 = digit value 0-9)
        [6]: Mode byte (measurement type)
        [7]: Info flags (percent, minus, low battery, overload)
        [8]: Relative mode flags
        [9]: Limit flags  
        [10]: Voltage/AC/DC/Auto flags
        [11]: Hold flags
        [12-13]: \\r\\n terminator
        
        Returns:
            MeterReading with parsed value, unit, mode, and flags
        """
        # Handle simulate mode
        if self.t.p.simulate:
            self._sim_value += 0.5  # Increment for variety
            if self._sim_value > 150.0:
                self._sim_value = 100.0
            
            return MeterReading(
                value=self._sim_value,
                unit='Ohm',
                mode='Resistance',
                is_overload=False,
                is_negative=False,
                flags={'simulate': True, 'auto': True},
                raw_packet=packet
            )

        try:
            # Validate packet length and terminator
            if len(packet) != 14:
                raise ValueError(f"Invalid packet length: {len(packet)}")
            if packet[12:14] != b'\r\n':
                raise ValueError(f"Invalid terminator: {packet[12:14].hex()}")

            # Extract range (byte 0)
            range_byte = packet[0]
            range_value = range_byte & 0x07  # Lower 3 bits
            
            # Extract digits (bytes 1-5)
            digits = []
            for i in range(1, 6):
                digit_byte = packet[i]
                digit = digit_byte & 0x0F  # Lower 4 bits
                if digit > 9:
                    # Invalid digit, might be overload or blank
                    digit = 0
                digits.append(digit)
            
            # Extract mode (byte 6)
            mode_byte = packet[6] & 0x0F
            
            # Extract flags (bytes 7-11)
            info_flags = packet[7] & 0x0F
            rel_flags = packet[8] & 0x0F
            limit_flags = packet[9] & 0x0F
            voltage_flags = packet[10] & 0x0F
            hold_flags = packet[11] & 0x0F
            
            # Parse info flags (byte 7)
            is_percent = bool(info_flags & 0x08)
            is_negative = bool(info_flags & 0x04)
            is_low_battery = bool(info_flags & 0x02)
            is_overload = bool(info_flags & 0x01)
            
            # Parse voltage flags (byte 10)
            is_dc = bool(voltage_flags & 0x08)
            is_ac = bool(voltage_flags & 0x04)
            is_auto = bool(voltage_flags & 0x02)
            is_hz = bool(voltage_flags & 0x01)
            
            # Parse hold flags (byte 11)
            is_hold = bool(hold_flags & 0x02)
            
            # Parse relative flags (byte 8)
            is_rel = bool(rel_flags & 0x02)
            
            # Determine measurement mode and unit from mode byte and range
            mode_info = self._parse_mode_and_range(mode_byte, range_value)
            
            # Build value from digits
            if is_overload:
                value = None
            else:
                # Digits represent a 5-digit display
                # Decimal point position depends on range
                decimal_pos = mode_info.get('decimal_pos', 2)  # Default to XX.XXX format
                value = self._digits_to_value(digits, decimal_pos)
                
                if is_negative:
                    value = -value
            
            # Build flags dict
            flags = {
                'low_battery': is_low_battery,
                'hold': is_hold,
                'relative': is_rel,
                'dc': is_dc,
                'ac': is_ac,
                'auto': is_auto,
                'hz': is_hz,
                'percent': is_percent,
            }
            
            return MeterReading(
                value=value,
                unit=mode_info['unit'],
                mode=mode_info['mode'],
                is_overload=is_overload,
                is_negative=is_negative,
                flags=flags,
                raw_packet=packet
            )
            
        except Exception as e:
            # If parsing fails, return error reading
            return MeterReading(
                value=None,
                unit='?',
                mode=f'Parse Error: {e}',
                is_overload=True,
                flags={'error': str(e)},
                raw_packet=packet
            )

    def _digits_to_value(self, digits: list, decimal_pos: int) -> float:
        """
        Convert 5 digits to float with decimal point at specified position.
        
        Args:
            digits: List of 5 digit values (0-9)
            decimal_pos: Position of decimal point (0-4, from left)
                        0 = 0.XXXX, 1 = X.XXX, 2 = XX.XX, 3 = XXX.X, 4 = XXXX.X
        """
        # Build integer from digits
        value_int = 0
        for digit in digits:
            value_int = value_int * 10 + digit
        
        # Apply decimal point
        divisor = 10 ** (5 - decimal_pos)
        return value_int / divisor

    def _parse_mode_and_range(self, mode_byte: int, range_value: int) -> dict:
        """
        Parse mode byte and range to determine measurement type, unit, and decimal position.
        
        Mode byte values (from ES51922 protocol):
        0xB: Voltage (V/mV)
        0x3: Resistance (Ohm)
        0x6: Capacitance (F)
        0x2: Frequency (Hz) or Current (A)
        0xD: Current (uA)
        0xF: Current (mA)
        0x0: Current (A)
        
        Range values determine the scale and decimal position.
        """
        # Mode mapping based on UT61E protocol documentation
        if mode_byte == 0x0B:  # Voltage
            ranges = [
                {'unit': 'V', 'mode': 'DC Voltage', 'scale': 2.2, 'decimal_pos': 3},      # 0: 2.2000V
                {'unit': 'V', 'mode': 'DC Voltage', 'scale': 22.0, 'decimal_pos': 4},     # 1: 22.000V
                {'unit': 'V', 'mode': 'DC Voltage', 'scale': 220.0, 'decimal_pos': 2},    # 2: 220.00V
                {'unit': 'V', 'mode': 'DC Voltage', 'scale': 1000.0, 'decimal_pos': 1},   # 3: 1000.0V
                {'unit': 'mV', 'mode': 'DC Voltage', 'scale': 220.0, 'decimal_pos': 2},   # 4: 220.00mV
            ]
        elif mode_byte == 0x03:  # Resistance
            ranges = [
                {'unit': 'Ohm', 'mode': 'Resistance', 'scale': 220.0, 'decimal_pos': 2},    # 0: 220.00Ω
                {'unit': 'kOhm', 'mode': 'Resistance', 'scale': 2.2, 'decimal_pos': 3},     # 1: 2.2000kΩ
                {'unit': 'kOhm', 'mode': 'Resistance', 'scale': 22.0, 'decimal_pos': 4},    # 2: 22.000kΩ
                {'unit': 'kOhm', 'mode': 'Resistance', 'scale': 220.0, 'decimal_pos': 2},   # 3: 220.00kΩ
                {'unit': 'MOhm', 'mode': 'Resistance', 'scale': 2.2, 'decimal_pos': 3},     # 4: 2.2000MΩ
                {'unit': 'MOhm', 'mode': 'Resistance', 'scale': 22.0, 'decimal_pos': 4},    # 5: 22.000MΩ
                {'unit': 'MOhm', 'mode': 'Resistance', 'scale': 220.0, 'decimal_pos': 2},   # 6: 220.00MΩ
            ]
        elif mode_byte == 0x06:  # Capacitance
            ranges = [
                {'unit': 'nF', 'mode': 'Capacitance', 'scale': 22.0, 'decimal_pos': 4},     # 0: 22.000nF
                {'unit': 'nF', 'mode': 'Capacitance', 'scale': 220.0, 'decimal_pos': 2},    # 1: 220.00nF
                {'unit': 'uF', 'mode': 'Capacitance', 'scale': 2.2, 'decimal_pos': 3},      # 2: 2.2000uF
                {'unit': 'uF', 'mode': 'Capacitance', 'scale': 22.0, 'decimal_pos': 4},     # 3: 22.000uF
                {'unit': 'uF', 'mode': 'Capacitance', 'scale': 220.0, 'decimal_pos': 2},    # 4: 220.00uF
                {'unit': 'mF', 'mode': 'Capacitance', 'scale': 2.2, 'decimal_pos': 3},      # 5: 2.2000mF
                {'unit': 'mF', 'mode': 'Capacitance', 'scale': 22.0, 'decimal_pos': 4},     # 6: 22.000mF
                {'unit': 'mF', 'mode': 'Capacitance', 'scale': 220.0, 'decimal_pos': 2},    # 7: 220.00mF
            ]
        elif mode_byte == 0x02:  # Frequency or Current %
            ranges = [
                {'unit': 'Hz', 'mode': 'Frequency', 'scale': 220.0, 'decimal_pos': 2},      # 0: 220.00Hz
                {'unit': 'Hz', 'mode': 'Frequency', 'scale': 2200.0, 'decimal_pos': 1},     # 1: 2200.0Hz
                {'unit': 'kHz', 'mode': 'Frequency', 'scale': 22.0, 'decimal_pos': 4},      # 3: 22.000kHz
                {'unit': 'kHz', 'mode': 'Frequency', 'scale': 220.0, 'decimal_pos': 2},     # 4: 220.00kHz
                {'unit': 'MHz', 'mode': 'Frequency', 'scale': 2.2, 'decimal_pos': 3},       # 5: 2.2000MHz
                {'unit': 'MHz', 'mode': 'Frequency', 'scale': 22.0, 'decimal_pos': 4},      # 6: 22.000MHz
                {'unit': 'MHz', 'mode': 'Frequency', 'scale': 220.0, 'decimal_pos': 2},     # 7: 220.00MHz
            ]
        elif mode_byte == 0x0D:  # Microamp
            ranges = [
                {'unit': 'uA', 'mode': 'DC Current', 'scale': 220.0, 'decimal_pos': 2},     # 0: 220.00uA
                {'unit': 'uA', 'mode': 'DC Current', 'scale': 2200.0, 'decimal_pos': 1},    # 1: 2200.0uA
            ]
        elif mode_byte == 0x0F:  # Milliamp
            ranges = [
                {'unit': 'mA', 'mode': 'DC Current', 'scale': 22.0, 'decimal_pos': 4},      # 0: 22.000mA
                {'unit': 'mA', 'mode': 'DC Current', 'scale': 220.0, 'decimal_pos': 2},     # 1: 220.00mA
            ]
        elif mode_byte == 0x00:  # Amp
            ranges = [
                {'unit': 'A', 'mode': 'DC Current', 'scale': 10.0, 'decimal_pos': 4},       # 0: 10.000A
            ]
        else:
            # Unknown mode
            return {'unit': '?', 'mode': f'Unknown (0x{mode_byte:02X})', 'decimal_pos': 2}
        
        # Get range info, default to first if out of bounds
        if range_value < len(ranges):
            return ranges[range_value]
        else:
            return ranges[0]
