"""
=================
UT61E Transport (I/O)
=================

Thin I/O layer for UNI-T UT61E multimeter using Cyrustek ES51922 chip.
Handles HID communication and raw packet reading.

The UT61E with USB cable appears as an HID device, not a COM port.
It continuously transmits 14-byte ES51922 packets wrapped in HID reports.
No commands are sent to the meter - we just listen to the stream.

USB HID Protocol:
- Vendor ID: 0x1a86 (WCH/QinHeng Electronics)
- Product ID: 0xe008 (UT61E with USB cable)
- HID reports contain ES51922 packets (14 bytes of actual data)
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
class UT61EOpenParams:
    """
    Connection settings for UT61E multimeter via HID.
    
    vendor_id: USB vendor ID (0x1a86 for WCH bridge)
    product_id: USB product ID (0xe429 for UT61E Plus with WCH UART TO KB-MS bridge)
    serial_number: Optional serial number to identify specific device
    timeout_ms: read timeout in milliseconds
    simulate: if True, simulate readings without hardware
    
    Note: UT61E Plus uses WCH UART TO KB-MS bridge (VID=0x1a86, PID=0xe429)
    This is different from standard UT61E (0x1a86:0xe008)
    Requires UT61xP.exe software running to activate data transmission
    """
    vendor_id: int = 0x1a86
    product_id: int = 0xe429
    serial_number: Optional[str] = None
    timeout_ms: int = 5000  # 5 seconds for packet read
    simulate: bool = False


class UT61ETransport:
    """
    Thin I/O layer for UT61E HID communication.
    
    Responsibilities:
      - Open/close HID device
      - Read raw 14-byte ES51922 packets from HID reports
      - Support simulate mode when hardware unavailable
      - Sync to packet boundaries (packets start with specific pattern)
    
    HID Protocol Details:
      - Device sends HID reports continuously
      - Each report contains ES51922 packet data
      - May have HID wrapper bytes that need stripping
    """

    def __init__(self, p: UT61EOpenParams):
        self.p = p
        self._device: Optional["hid.device"] = None
        self._sim_counter: int = 0  # For generating simulated data

    # -------- Lifecycle ----------
    def open(self) -> None:
        if self.p.simulate:
            print(f"SIM: UT61ETransport.open(VID=0x{self.p.vendor_id:04x}, PID=0x{self.p.product_id:04x})")
            return

        if not HID_AVAILABLE:
            raise RuntimeError(
                "hidapi not installed (required for UT61E HID communication)\n"
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
            
            # Set non-blocking read with timeout
            # Note: hidapi timeout is in milliseconds
            # We'll use blocking mode and handle timeout in read_packet
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to open UT61E HID device (VID=0x{self.p.vendor_id:04x}, "
                f"PID=0x{self.p.product_id:04x}): {e}\n"
                "Check:\n"
                "  1. Device is plugged in and powered on\n"
                "  2. VID/PID are correct (use list_devices() to check)\n"
                "  3. No other program is using the device"
            ) from e

    def close(self) -> None:
        if self.p.simulate:
            print("SIM: UT61ETransport.close()")
            return

        if self._device is not None:
            self._device.close()
            self._device = None

    # -------- HID device enumeration ----------
    @staticmethod
    def list_devices() -> list[dict]:
        """
        List all HID devices that might be UT61E meters.
        
        Returns list of device info dicts with keys:
          - vendor_id, product_id, serial_number
          - manufacturer_string, product_string
          - path
        """
        if not HID_AVAILABLE:
            return []
        
        all_devices = hid.enumerate()
        
        # Filter for potential UT61E devices (common VID/PID)
        ut61e_devices = [
            d for d in all_devices
            if d['vendor_id'] == 0x1a86  # Common UT61E cable VID
        ]
        
        return ut61e_devices

    # -------- Packet reading ----------
    def read_packet(self) -> bytes:
        """
        Read one HID packet from UT61E Plus via WCH UART TO KB-MS bridge.
        
        UT61E Plus with WCH bridge sends ASCII text data in HID reports.
        Format: Header (13 ab cd 10 06) followed by ASCII text (e.g., "1 0.3289")
        
        IMPORTANT: Requires UT61xP.exe software running to activate data transmission.
        
        Returns:
            64-byte HID report containing ASCII text data
            
        Raises:
            TimeoutError if no valid packet received within timeout
        """
        if self.p.simulate:
            # Return simulated resistance reading
            time.sleep(0.1)  # Simulate transmission delay
            self._sim_counter += 1
            
            # Simulate resistance reading that increments
            sim_value = 100.0 + (self._sim_counter % 50)
            print(f"SIM: UT61ETransport.read_packet() -> simulated {sim_value:.1f} Ohms")
            
            # Return simulated HID report with ASCII data
            # Format: header (13 ab cd 10 06) + ASCII "1 100.5" (mode 1 = resistance)
            sim_data = f"1 {sim_value:.4f}".encode('ascii')
            report = b'\x13\xab\xcd\x10\x06' + sim_data.ljust(59, b'\x00')
            return report[:64]

        if self._device is None:
            raise RuntimeError("HID device not open")

        # Read HID reports from WCH bridge
        # UT61E Plus sends 64-byte HID reports with ASCII text
        # Format: Header (13 ab cd 10 06) + ASCII reading
        
        start_time = time.time()
        timeout_sec = self.p.timeout_ms / 1000.0
        
        while (time.time() - start_time) < timeout_sec:
            try:
                # Read 64-byte HID report with 1 second timeout per attempt
                report = self._device.read(64, timeout_ms=1000)
                
                if not report or len(report) == 0:
                    continue
                
                # Convert to bytes if needed
                report_bytes = bytes(report)
                
                # Check if report contains data (not all zeros)
                if self._is_valid_ascii_report(report_bytes):
                    return report_bytes
                    
            except Exception:
                # Read error, continue trying
                continue
        
        raise TimeoutError("Failed to read valid UT61E Plus packet within timeout")

    def _is_valid_ascii_report(self, report: bytes) -> bool:
        """
        Check if HID report contains valid ASCII data from UT61E Plus.
        
        UT61E Plus with WCH bridge format:
        - Byte 0-4: Header (13 ab cd 10 06) or similar
        - Byte 3-20: ASCII text with reading (e.g., "1 0.3289")
        
        This is a heuristic check - report should contain printable ASCII.
        """
        if len(report) < 20:
            return False
        
        # Check if report has header pattern (bytes 0-4: 13 ab cd 10 06)
        # ASCII data starts at byte 5
        # Format: "mode value" e.g., "1 0.3288" or "6  OL."
        
        # Check for header pattern
        if len(report) >= 5:
            if report[0] == 0x13 and report[1] == 0xab and report[2] == 0xcd:
                # Valid header found
                return True
        
        # Extract potential ASCII region (bytes 5-18)
        ascii_region = report[5:18]
        
        # Check if region contains printable ASCII characters
        # Valid readings are like "1 0.3289" or "2 -1.234"
        try:
            text = ascii_region.decode('ascii', errors='ignore').strip()
            # Must have at least 3 characters (e.g., "1 5")
            if len(text) >= 3:
                # Check if it starts with a digit (mode indicator)
                if text[0].isdigit():
                    return True
        except Exception:
            pass
        
        return False

    def flush_input(self) -> None:
        """Clear any buffered input data"""
        if self.p.simulate:
            print("SIM: UT61ETransport.flush_input()")
            return

        if self._device is not None:
            # Flush by reading all pending reports
            try:
                while True:
                    report = self._device.read(64, timeout_ms=10)
                    if not report:
                        break
            except Exception:
                pass
