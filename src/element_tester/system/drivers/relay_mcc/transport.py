# =================
# ERB08 Transport (I/O)
# =================
#
# Thin I/O layer around `mcculw.ul`. This module encapsulates direct board
#/port access and provides a small, testable surface for reading/writing a
#single byte port. It gracefully falls back to a simulate mode when the
#`mcculw` package or hardware is not available (useful for CI and local
#development).
from __future__ import annotations
from dataclasses import dataclass
from typing import Union

try:
    from mcculw import ul
    from mcculw.enums import DigitalPortType, DigitalIODirection
except Exception:
    ul = None
    DigitalPortType = None
    DigitalIODirection = None


@dataclass
class ERB08OpenParams:
    """
    Connection/settings for an MCC USB-ERB08-like relay board.

    board_num   : MCC board number (from InstaCal, usually 0)
    port_low    : Port for relays 0-3 (e.g., 12 or FIRSTPORTA)
    port_high   : Port for relays 4-7 (e.g., 13 or FIRSTPORTB)
                  If None, all 8 relays use port_low (single-port mode)
    simulate    : if True, do not touch hardware, just print and track state
    active_high : if True, 1 = relay ON; if False, 0 = relay ON (inverts logic)
    """
    board_num: int = 0
    port_low: Union[int, object, str] = 12
    port_high: Union[int, object, str, None] = 13
    simulate: bool = False
    active_high: bool = True


class ERB08Transport:
    """
    Thin I/O layer around mcculw UL.

    Responsibilities:
      - Initialize/config ports for output (supports dual-port: port_low + port_high)
      - Write/read individual bits (maps relay 0-7 to correct port and bit)
      - Track current port values in software
      - Support simulate mode when hardware or mcculw is not available
      
    Architecture:
      - Relays 0-3 → port_low, bits 0-3
      - Relays 4-7 → port_high, bits 0-3 (or port_low bits 4-7 if single-port)
    """

    def __init__(self, p: ERB08OpenParams):
        self.p = p
        self._current_value_low: int = 0   # port_low state (bits 0-3)
        self._current_value_high: int = 0  # port_high state (bits 0-3)

    # -------- Lifecycle ----------
    def open(self) -> None:
        if self.p.simulate or ul is None:
            print(
                "SIM: ERB08Transport.open("
                f"board={self.p.board_num}, port_low={self.p.port_low}, port_high={self.p.port_high})"
            )
            self._current_value_low = 0
            self._current_value_high = 0
            return

        port_low = self._resolve_port_enum(self.p.port_low)
        
        # Configure port_low for OUTPUT
        try:
            ul.d_config_port(self.p.board_num, port_low, DigitalIODirection.OUT)
        except Exception:
            pass
        
        # Configure port_high if dual-port mode
        if self.p.port_high is not None:
            port_high = self._resolve_port_enum(self.p.port_high)
            try:
                ul.d_config_port(self.p.board_num, port_high, DigitalIODirection.OUT)
            except Exception:
                pass
        
        # Note: Initial state will be set by ProcInitializeRelays calling cmd_all_off
        # which properly handles active_high logic

    def close(self) -> None:
        # Note: Relays will be turned OFF by ProcShutdownRelays before close is called
        # which properly handles active_high logic
        
        if self.p.simulate or ul is None:
            print("SIM: ERB08Transport.close()")
            return

    # -------- Bit-level I/O with port mapping ----------
    def _relay_to_port_and_bit(self, relay: int) -> tuple[Union[int, object], int]:
        """
        Map relay index (0-7) to (port, bit_in_port).
        
        Relays 0-3 → port_low, bits 0-3
        Relays 4-7 → port_high, bits 0-3 (or port_low bits 4-7 if single-port)
        """
        if not (0 <= relay <= 7):
            raise ValueError(f"relay must be in 0..7, got {relay}")
        
        if relay < 4:
            # Low port, direct mapping
            return (self.p.port_low, relay)
        else:
            # High port (or high bits of low port if single-port mode)
            if self.p.port_high is not None:
                # Dual-port: relays 4-7 → port_high bits 0-3
                return (self.p.port_high, relay - 4)
            else:
                # Single-port: relays 4-7 → port_low bits 4-7
                return (self.p.port_low, relay)
    
    def write_bit_raw(self, relay: int, on: bool) -> None:
        """
        Write a single relay ON/OFF in 'device' space (no active_high invert).
        Maps relay 0-7 to correct port and bit.
        """
        port_val, bit = self._relay_to_port_and_bit(relay)
        port = self._resolve_port_enum(port_val)
        
        if self.p.simulate or ul is None:
            print(
                f"SIM: d_bit_out(board={self.p.board_num}, port={port_val}, "
                f"bit={bit}, value={1 if on else 0}) [relay {relay}]"
            )
            # Track state
            if relay < 4:
                mask = 1 << bit
                if on:
                    self._current_value_low |= mask
                else:
                    self._current_value_low &= ~mask
            else:
                mask = 1 << bit
                if on:
                    self._current_value_high |= mask
                else:
                    self._current_value_high &= ~mask
            return
        
        # Try direct bit write first
        try:
            ul.d_bit_out(self.p.board_num, port, bit, 1 if on else 0)
        except Exception:
            # Fallback: read-modify-write on whole port
            try:
                current = ul.d_in(self.p.board_num, port)
                mask = 1 << bit
                new_val = (current | mask) if on else (current & ~mask)
                ul.d_out(self.p.board_num, port, new_val)
            except Exception as e:
                raise RuntimeError(f"Failed to write relay {relay} (port={port}, bit={bit}): {e}")

    # -------- Helpers ----------
    def _resolve_port_enum(self, port_value) -> object:
        """
        Try to transform p.port into a DigitalPortType if mcculw enums are available.
        Allows p.port to be:
          - a DigitalPortType already
          - an int (cast to DigitalPortType)
          - a string like "FIRSTPORTA"
        """
        if DigitalPortType is None:
            # No enums (simulate or import failure)
            return port_value

        # Already a DigitalPortType instance
        try:
            if isinstance(port_value, DigitalPortType):
                return port_value
        except TypeError:
            # DigitalPortType not usable with isinstance (in older mcculw),
            # just fall through to other options.
            pass

        # If string, try to look up by name
        if isinstance(port_value, str):
            try:
                return getattr(DigitalPortType, port_value)
            except AttributeError:
                return port_value  # give up, pass through raw

        # If int, try to cast directly
        if isinstance(port_value, int):
            try:
                return DigitalPortType(port_value)
            except Exception:
                return port_value

        # Anything else, just return as-is
        return port_value
