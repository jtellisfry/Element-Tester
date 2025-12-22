# =================
# ERB08 Commands (low-level)
# =================
#
# This module implements low-level 'LEGO' commands that operate on the
# device byte/bit level. Procedures layer composes these commands into
# higher-level flows. Keep these functions small and focused.
from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .transport import ERB08Transport


@dataclass
class RelayState:
        current_byte: int = 0


class ERB08Commands:
    """
    Low-level relay commands for MCC USB-ERB08.

    LEGO pieces:
      - cmd_set_bit
      - cmd_set_many
      - cmd_all_off
      - cmd_read_port
      - cmd_pulse_bit
    """

    def __init__(self, transport: ERB08Transport):
        self.t = transport
        self.state = RelayState()

    # -------- Helpers for logical ON/OFF with active_high mapping ----------
    def _logical_to_device_bit(self, on: bool) -> bool:
        """
        Maps logical relay ON/OFF to actual device bit (considering active_high).
        """
        if self.t.p.active_high:
            # device 1 = ON, 0 = OFF
            return on
        else:
            # device 0 = ON, 1 = OFF
            return not on

    # -------- Commands ----------
    def cmd_set_bit(self, relay: int, on: bool) -> None:
        """
        Set a single relay (0-7) ON/OFF logically.
        Automatically maps to correct port and bit.
        """
        device_on = self._logical_to_device_bit(on)
        self.t.write_bit_raw(relay, device_on)

    def cmd_set_many(self, relays_on: List[int], relays_off: List[int]) -> None:
        """
        Turn multiple relays ON and OFF.
        Each relay is written individually to correct port.
        """
        # First apply OFF
        for relay in relays_off:
            if 0 <= relay <= 7:
                self.cmd_set_bit(relay, False)
        
        # Then apply ON
        for relay in relays_on:
            if 0 <= relay <= 7:
                self.cmd_set_bit(relay, True)

    def cmd_all_off(self) -> None:
        """
        Drive all 8 relays to logical OFF.
        """
        for relay in range(8):
            self.cmd_set_bit(relay, False)

    def cmd_read_relay(self, relay: int) -> bool:
        """
        Read current state of a relay (not implemented - would need port reads).
        For now, returns False (unknown state).
        """
        # TODO: Implement if needed by reading port state
        return False

    def cmd_pulse_bit(self, relay: int, on_ms: float = 100.0) -> None:
        """
        Turn a relay ON for on_ms milliseconds and then OFF.
        """
        import time

        self.cmd_set_bit(relay, True)
        time.sleep(on_ms / 1000.0)
        self.cmd_set_bit(relay, False)
