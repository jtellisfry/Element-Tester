from __future__ import annotations
from dataclasses import dataclass

from .transport import PDIS08Transport


@dataclass
class RelayState:
    current_byte: int = 0


class PDIS08Commands:
    """Low-level relay commands for MCC PDIS08."""

    def __init__(self, transport: PDIS08Transport):
        self.t = transport
        self.state = RelayState()

    def cmd_set_channel(self, channel: int, on: bool) -> None:
        device_on = on
        self.t.write_channel_raw(channel, device_on)

    def cmd_set_many(self, channels_on: list[int], channels_off: list[int]) -> None:
        for ch in channels_off:
            if 0 <= ch <= 7:
                self.cmd_set_channel(ch, False)
        for ch in channels_on:
            if 0 <= ch <= 7:
                self.cmd_set_channel(ch, True)

    def cmd_all_off(self) -> None:
        for ch in range(8):
            self.cmd_set_channel(ch, False)

    def cmd_all_on(self) -> None:
        for ch in range(8):
            self.cmd_set_channel(ch, True)

    def cmd_read_channel(self, channel: int) -> int:
        return self.t.read_channel_raw(channel)
