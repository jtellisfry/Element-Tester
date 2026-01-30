"""
=================
UT61E Commands (packet parsing)
=================

Low-level packet parsing for ES51922 protocol.
Decodes the 14-byte packets into readable values.

ES51922 14-byte packet structure:
- Continuously transmitted at ~2Hz
- Encodes LCD display segments
- Includes value, unit, mode, and status flags

LEGO pieces:
  - cmd_parse_packet: Decode 14-byte packet into MeterReading
  - Helper functions for segment decoding
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .transport import UT61ETransport


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


class UT61ECommands:
    """
    Low-level packet parsing for UT61E (ES51922 protocol).
    
    No actual commands are sent - just parsing received packets.
    """

    def __init__(self, transport: UT61ETransport):
        self.t = transport
        self._sim_value = 100.0  # For simulate mode

    def cmd_parse_packet(self, packet: bytes) -> MeterReading:
        """
        Parse HID packet from UT61E Plus with WCH bridge into a MeterReading.
        
        UT61E Plus ASCII format:
        - Header: 13 ab cd 10 06 (bytes 0-4)
        - ASCII text: bytes 3-20 contain "mode value" (e.g., "1 0.3289")
        - Mode codes: 1=resistance, 2=voltage, 3=current, etc.
        
        Example packet:
          13 ab cd 10 06 31 20 30 2e 33 32 38 39 00...
          Decodes to: "1 0.3289" -> mode=1 (resistance), value=0.3289 Ohms
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
                flags={'simulate': True},
                raw_packet=packet
            )

        # Parse ASCII data from HID report
        try:
            # Extract ASCII region (bytes 5-18, after the 5-byte header: 13 ab cd 10 06)
            # Format: "mode value" e.g., "1 0.3288" or "6  OL."
            # Example from diagnostics: "1 0.3288020" (extra chars after value)
            ascii_bytes = packet[5:18]
            
            # Decode to ASCII text and clean up
            text = ascii_bytes.decode('ascii', errors='ignore').strip()
            # Remove any non-printable characters
            text = ''.join(c for c in text if c.isprintable())
            
            # Parse "mode value" format
            parts = text.split()
            if len(parts) < 2:
                raise ValueError(f"Invalid format: '{text}' (parts: {parts})")
            
            mode_code = parts[0]
            value_str = parts[1]
            
            # Parse value
            try:
                value = float(value_str)
            except ValueError:
                # Handle overload (OL) or other non-numeric displays
                if 'OL' in value_str or 'ol' in value_str:
                    return MeterReading(
                        value=None,
                        unit='?',
                        mode='Overload',
                        is_overload=True,
                        raw_packet=packet
                    )
                raise
            
            # Determine unit and mode from mode code
            mode_info = self._parse_mode_code(mode_code)
            
            # Check for negative value
            is_negative = (value < 0)
            
            return MeterReading(
                value=abs(value) if is_negative else value,
                unit=mode_info['unit'],
                mode=mode_info['mode'],
                is_overload=False,
                is_negative=is_negative,
                flags={'mode_code': mode_code},
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

    def _parse_mode_code(self, mode_code: str) -> dict:
        """
        Map mode code to unit and mode name.
        
        Mode codes from UT61E Plus:
        - '1': Resistance (Ohm)
        - '2': DC Voltage (V)
        - '3': AC Voltage (V)
        - '4': DC Current (A)
        - '5': AC Current (A)
        - '6': Capacitance (F)
        - '7': Frequency (Hz)
        - '8': Temperature (°C)
        - '9': Diode test (V)
        - '10': Continuity (Ohm)
        
        Returns:
            dict with 'unit' and 'mode' keys
        """
        mode_map = {
            '1': {'unit': 'Ohm', 'mode': 'Resistance'},
            '2': {'unit': 'V', 'mode': 'DC Voltage'},
            '3': {'unit': 'V', 'mode': 'AC Voltage'},
            '4': {'unit': 'A', 'mode': 'DC Current'},
            '5': {'unit': 'A', 'mode': 'AC Current'},
            '6': {'unit': 'F', 'mode': 'Capacitance'},
            '7': {'unit': 'Hz', 'mode': 'Frequency'},
            '8': {'unit': '°C', 'mode': 'Temperature'},
            '9': {'unit': 'V', 'mode': 'Diode'},
            '10': {'unit': 'Ohm', 'mode': 'Continuity'},
        }
        
        return mode_map.get(mode_code, {'unit': '?', 'mode': f'Unknown ({mode_code})'})

    def cmd_read_parsed(self) -> MeterReading:
        """
        Read one packet and return parsed measurement.
        Convenience wrapper combining read + parse.
        """
        packet = self.t.read_packet()
        return self.cmd_parse_packet(packet)
