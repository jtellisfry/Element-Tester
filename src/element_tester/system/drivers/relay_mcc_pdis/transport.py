from __future__ import annotations
from dataclasses import dataclass
from typing import Union
import logging

try:
    from mcculw import ul
    from mcculw.enums import DigitalPortType, DigitalIODirection
except Exception:
    ul = None
    DigitalPortType = None
    DigitalIODirection = None


@dataclass
class PDIS08OpenParams:
    """
    Connection/settings for an MCC PDIS08-like relay board.

    Defaults chosen for common MCC ports; adjust when creating driver instance.
    """
    board_num: int = 1
    # PDIS typically exposes a single digital port; default to numeric port 1
    port_low: Union[int, object, str] = 1
    # No separate high port by default for PDIS (single-port device)
    port_high: Union[int, object, str, None] = None
    simulate: bool = False
    active_high: bool = True


class PDIS08Transport:
    """Thin I/O layer around mcculw UL for PDIS08.

    Mirrors the ERB08Transport interface so procedures/commands can be reused.
    """

    def __init__(self, p: PDIS08OpenParams):
        self.p = p
        self.log = logging.getLogger("element_tester.relay.mcc_pdis")
        self._current_value_low: int = 0
        self._current_value_high: int = 0

    def open(self) -> None:
        if self.p.simulate or ul is None:
            self.log.info("SIM: PDIS08Transport.open(board=%s, port_low=%s, port_high=%s)",
                          self.p.board_num, self.p.port_low, self.p.port_high)
            self._current_value_low = 0
            self._current_value_high = 0
            return

        port_low = self._resolve_port_enum(self.p.port_low)
        try:
            ul.d_config_port(self.p.board_num, port_low, DigitalIODirection.OUT)
        except Exception:
            pass

        if self.p.port_high is not None:
            port_high = self._resolve_port_enum(self.p.port_high)
            try:
                ul.d_config_port(self.p.board_num, port_high, DigitalIODirection.OUT)
            except Exception:
                pass

    def close(self) -> None:
        if self.p.simulate or ul is None:
            self.log.info("SIM: PDIS08Transport.close()")
            return

    def _channel_to_port_and_bit(self, channel: int) -> tuple[Union[int, object], int]:
        if not (0 <= channel <= 7):
            raise ValueError(f"channel must be in 0..7, got {channel}")
        if channel < 4:
            return (self.p.port_low, channel)
        else:
            if self.p.port_high is not None:
                return (self.p.port_high, channel - 4)
            else:
                return (self.p.port_low, channel)

    def write_channel_raw(self, channel: int, on: bool) -> None:
        port_val, bit = self._channel_to_port_and_bit(channel)
        port = self._resolve_port_enum(port_val)

        if self.p.simulate or ul is None:
            self.log.info("SIM: d_bit_out(board=%s, port=%s, bit=%s, value=%s) [channel %s]",
                          self.p.board_num, port_val, bit, 1 if on else 0, channel)
            if channel < 4:
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

        try:
            ul.d_bit_out(self.p.board_num, port, bit, 1 if on else 0)
        except Exception:
            try:
                current = ul.d_in(self.p.board_num, port)
                mask = 1 << bit
                new_val = (current | mask) if on else (current & ~mask)
                ul.d_out(self.p.board_num, port, new_val)
            except Exception as e:
                raise RuntimeError(f"Failed to write channel {channel} (port={port}, bit={bit}): {e}")

    def read_channel_raw(self, channel: int) -> int:
        if self.p.simulate or ul is None:
            return self._current_value_low if channel < 4 else self._current_value_high
        port_val, bit = self._channel_to_port_and_bit(channel)
        port = self._resolve_port_enum(port_val)
        try:
            val = ul.d_in(self.p.board_num, port)
            return 1 if (val & (1 << bit)) else 0
        except Exception as e:
            raise RuntimeError(f"Failed to read channel {channel}: {e}")

    def _resolve_port_enum(self, port_value) -> object:
        if DigitalPortType is None:
            return port_value

        try:
            if isinstance(port_value, DigitalPortType):
                return port_value
        except TypeError:
            pass

        if isinstance(port_value, str):
            try:
                return getattr(DigitalPortType, port_value)
            except AttributeError:
                return port_value

        if isinstance(port_value, int):
            try:
                return DigitalPortType(port_value)
            except Exception:
                return port_value

        return port_value
