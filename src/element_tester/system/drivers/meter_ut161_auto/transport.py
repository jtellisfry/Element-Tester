"""
=================
UT61E Auto Transport (I/O)
=================

Thin I/O layer for UNI-T UT161E multimeter using Cyrustek ES51922 chip.
Direct HID communication - no external software required.

The UT161E with USB cable appears as an HID device (VID=0x1a86, PID=0xe429).
It continuously transmits ES51922 packets wrapped in HID reports.

HID Protocol:
- Vendor ID: 0x1a86 (WCH/QinHeng Electronics)
- Product ID: 0xe429 (UT61E Plus / UT161E with WCH UART-to-KB/MS bridge)
- HID reports contain 14-byte ES51922 packets
- No commands sent to meter - we only listen
- Packet Rate: ~2Hz
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time

# Optional dep; gracefully fail if missing (simulate mode still works)
try:
    import hid  # hidapi
    HID_AVAILABLE = True
except Exception:
    hid = None
    HID_AVAILABLE = False


@dataclass
class UT61EAutoOpenParams:
    """
    Connection settings for UT161E multimeter via HID.
    
    vendor_id: USB vendor ID (0x1a86 for WCH bridge)
    product_id: USB product ID (0xe429 for UT161E/UT61E Plus)
    serial_number: Optional serial number to identify specific device
    timeout_ms: Read timeout in milliseconds
    simulate: if True, simulate readings without hardware
    
    Note: UT161E uses WCH UART TO KB-MS bridge (VID=0x1a86, PID=0xe429)
    Works WITHOUT requiring UT61E+ software running
    """
    vendor_id: int = 0x1a86
    product_id: int = 0xe429
    serial_number: Optional[str] = None
    timeout_ms: int = 5000  # 5 seconds for packet read
    simulate: bool = False


class UT61EAutoTransport:
    """
    Thin I/O layer for UT161E HID communication.
    
    Responsibilities:
      - Open/close HID device
      - Read raw ES51922 packets from HID reports
      - Support simulate mode when hardware unavailable
      - Extract 14-byte packets from HID wrapper
    
    HID Protocol Details:
      - Device sends HID reports continuously at ~2Hz
      - Each report contains ES51922 packet data
      - May have HID wrapper bytes that need stripping
      - Works without UT61E+ software running
    """

    def __init__(self, p: UT61EAutoOpenParams):
        self.p = p
        self._device: Optional["hid.device"] = None
        self._sim_counter: int = 0  # For generating simulated data

    # -------- Lifecycle ----------
    def open(self) -> None:
        if self.p.simulate:
            print(f"SIM: UT61EAutoTransport.open(VID=0x{self.p.vendor_id:04x}, PID=0x{self.p.product_id:04x})")
            return

        if not HID_AVAILABLE:
            raise RuntimeError(
                "hidapi not installed (required for UT161E HID communication)\n"
                "Install with: pip install hidapi"
            )

        try:
            self._device = hid.device()
            
            if self.p.serial_number:
                self._device.open(
                    self.p.vendor_id,
                    self.p.product_id,
                    self.p.serial_number
                )
            else:
                self._device.open(
                    self.p.vendor_id,
                    self.p.product_id
                )
            
            # Set non-blocking mode with timeout
            self._device.set_nonblocking(0)
            
            manufacturer = self._device.get_manufacturer_string()
            product = self._device.get_product_string()
            
            print(f"UT61EAuto: Opened HID device VID=0x{self.p.vendor_id:04x} PID=0x{self.p.product_id:04x}")
            print(f"  Manufacturer: {manufacturer}")
            print(f"  Product: {product}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to open HID device: {e}") from e

    def close(self) -> None:
        if self.p.simulate:
            print("SIM: UT61EAutoTransport.close()")
            return

        if self._device:
            try:
                self._device.close()
                print("UT61EAuto: HID device closed")
            except Exception:
                pass  # Ignore close errors

    # -------- I/O ----------
    def read_packet(self) -> bytes:
        """
        Read one ES51922 packet from HID reports.
        
        Reads HID report and extracts 14-byte ES51922 packet.
        
        Returns:
            bytes containing ES51922 packet data
            
        Raises:
            TimeoutError if no valid packet received within timeout
        """
        if self.p.simulate:
            # Generate simulated packet
            self._sim_counter += 1
            sim_value = 100.0 + (self._sim_counter % 50)  # 100-150 Ohms
            return self._generate_sim_packet(sim_value)

        if not self._device:
            raise RuntimeError("HID device not open")

        try:
            # Read HID report (blocking with timeout)
            # HID reports may be longer than ES51922 packet
            report = self._device.read(128, timeout_ms=self.p.timeout_ms)
            
            if not report:
                raise TimeoutError("Timeout reading from UT161E HID device")
            
            # Convert to bytes if needed
            if isinstance(report, list):
                report = bytes(report)
            
            # Extract ES51922 packet from HID report
            # The packet should be somewhere in the report
            # Look for the 14-byte sequence that ends with valid data
            packet = self._extract_packet_from_report(report)
            
            return packet
            
        except Exception as e:
            if "timeout" in str(e).lower():
                raise TimeoutError(f"Timeout reading from HID device: {e}") from e
            raise

    def _extract_packet_from_report(self, report: bytes) -> bytes:
        """
        Extract 14-byte ES51922 packet from HID report.
        
        The HID report contains the ES51922 packet somewhere within it.
        Different cables may wrap it differently, so we search for valid packet.
        """
        # For now, assume packet starts at a fixed offset (most common is byte 0 or 1)
        # This may need adjustment based on your specific cable/device
        
        # Try common offsets
        offsets_to_try = [0, 1, 2, 5]  # Common HID wrapper sizes
        
        for offset in offsets_to_try:
            if offset + 14 <= len(report):
                potential_packet = report[offset:offset+14]
                # Basic validation: check if it looks like valid data
                # (all bytes should be in reasonable range)
                if all(0 <= b <= 0x7F for b in potential_packet):
                    return potential_packet
        
        # If no valid offset found, just take first 14 bytes
        if len(report) >= 14:
            return report[:14]
        
        raise ValueError(f"HID report too short: {len(report)} bytes")

    def _generate_sim_packet(self, resistance_ohms: float) -> bytes:
        """
        Generate simulated ES51922 packet for resistance measurement.
        
        Packet format (14 bytes):
        [0]: Range byte (0x60-0x67)
        [1-5]: Digits 1-5 (0x30-0x39)
        [6]: Mode byte
        [7-11]: Flag bytes
        [12-13]: \\r\\n terminator
        """
        # Convert resistance to digits (e.g., 123.45 -> "12345")
        value_str = f"{resistance_ohms:06.1f}".replace('.', '')[:5]
        
        # Build packet
        packet = bytearray(14)
        packet[0] = 0x61  # Range byte (resistance, 220 ohm range)
        
        # Encode digits (bytes 1-5)
        for i, digit_char in enumerate(value_str[:5]):
            packet[i + 1] = 0x30 | int(digit_char)  # 0x30-0x39
        
        packet[6] = 0x33   # Mode: resistance (0x33 from protocol)
        packet[7] = 0x30   # Flags: no special flags
        packet[8] = 0x30   # Relative mode flags
        packet[9] = 0x30   # Limit flags
        packet[10] = 0x3B  # DC measurement, auto range
        packet[11] = 0x30  # Hold flags
        packet[12] = 0x0D  # \r
        packet[13] = 0x0A  # \n
        return bytes(packet)

    def is_open(self) -> bool:
        """Check if transport is open"""
        if self.p.simulate:
            return True
        return self._device is not None

    def flush_input(self) -> None:
        """Flush input buffer (HID doesn't need explicit flush)"""
        if self.p.simulate:
            return
        # HID doesn't buffer like serial, so just wait briefly
        if self._device:
            time.sleep(0.1)
            time.sleep(0.1)
