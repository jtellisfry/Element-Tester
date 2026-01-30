from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# Optional deps; we fail gracefully if missing (simulate mode still works)
try:
    import pyvisa
except Exception:
    pyvisa = None

try:
    import serial  # pyserial
except Exception:
    serial = None


@dataclass
class AR3865OpenParams:
    """
    Connection settings for the AR 3865.

    resource:
      - VISA, e.g. "USB0::0x1AB1::0x09C4::INSTR"
      - or serial, e.g. "serial://COM6"
    """
    resource: str
    baudrate: int = 38400  # AR3865 uses 38400 baud (NOT 9600!)
    timeout_ms: int = 5000
    simulate: bool = False


class AR3865Transport:
    """
    Thin I/O layer. No SCPI knowledge here—just open/close/write/query.
    """

    def __init__(self, p: AR3865OpenParams):
        self.p = p
        self._rm: Optional["pyvisa.ResourceManager"] = None
        self._inst = None
        self._is_serial: bool = False

    # -------- Lifecycle ----------
    def open(self) -> None:
        if self.p.simulate:
            print("SIM: transport.open()")
            return

        # Only check for hardware dependencies if NOT in simulate mode
        if self.p.resource.lower().startswith("serial://"):
            if serial is None:
                raise RuntimeError("pyserial not installed (required for serial:// resources)")
            port = self.p.resource.split("://", 1)[1]
            self._inst = serial.Serial(
                port=port,
                baudrate=self.p.baudrate,
                timeout=self.p.timeout_ms / 1000.0,
            )
            self._is_serial = True
        else:
            if pyvisa is None:
                raise RuntimeError("pyvisa not installed (required for VISA resources)")
            self._rm = pyvisa.ResourceManager()
            self._inst = self._rm.open_resource(
                self.p.resource,
                timeout=self.p.timeout_ms,
            )
            self._is_serial = False

    def close(self) -> None:
        if self.p.simulate:
            print("SIM: transport.close()")
            return
        try:
            if self._inst is not None:
                self._inst.close()
        finally:
            self._inst = None
            if self._rm is not None:
                try:
                    self._rm.close()
                finally:
                    self._rm = None

    # -------- I/O ----------
    def flush_input(self) -> None:
        """
        Flush/clear the input buffer to remove any stale data.
        Call this before a query if you want to ensure you get a fresh response.
        """
        if self.p.simulate:
            return
        
        if self._is_serial:
            # Read and discard any pending data in the input buffer
            self._inst.reset_input_buffer()
            print("[SERIAL] Input buffer flushed")
    
    def write(self, cmd: str) -> None:
        """
        Send a SCPI command (no response expected).
        """
        if self.p.simulate:
            print(f"SIM: write: {cmd}")
            return

        print(f"[SERIAL WRITE] Sending: {cmd}")  # Debug logging
        if self._is_serial:
            data = (cmd + "\r\n").encode("ascii")  # AR3865 likely needs \r\n
            self._inst.write(data)
            self._inst.flush()  # Ensure data is sent immediately
            print(f"[SERIAL WRITE] Sent {len(data)} bytes")  # Debug logging
        else:
            self._inst.write(cmd)

    def query(self, cmd: str) -> str:
        """
        Send a SCPI query and return the response as a stripped string.
        """
        if self.p.simulate:
            print(f"SIM: query: {cmd}")
            cmd_up = cmd.strip().upper()
            if cmd_up == "TEST:RESULT?":
                return "PASS"
            if cmd_up == "*IDN?":
                return "Associated Research,3865,Sim,1.0"
            return "OK"

        print(f"[SERIAL QUERY] Sending: {cmd}")  # Debug logging
        if self._is_serial:
            # Send the query command
            data = (cmd + "\r\n").encode("ascii")  # AR3865 likely needs \r\n
            self._inst.write(data)
            self._inst.flush()
            # Read response
            response = self._inst.readline().decode("ascii", errors="ignore").strip()
            print(f"[SERIAL QUERY] Received: {response}")  # Debug logging
            return response
        else:
            return str(self._inst.query(cmd)).strip()

    # -------- Helpers ----------
    def idn(self) -> str:
        """
        Convenience wrapper for *IDN?.
        """
        try:
            return self.query("*IDN?")
        except Exception:
            return "AR-3865"
