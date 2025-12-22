# driver.py
from __future__ import annotations
from typing import Optional, Iterable
import logging

from .procedures import ERB08Procedures, RelayMapping
from .errors import ERB08Error


class ERB08Driver:
    """
    Hypot-style façade for the MCC ERB08 driver.

    Wraps Procedures so the rest of the system can talk to a single
    object, similar to your Hypot instrument driver.
    """

    def __init__(
        self,
        board_num: int = 0,
        port_low: object = 12,
        port_high: object = 13,
        simulate: bool = False,
        active_high: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.log = logger or logging.getLogger("element_tester.driver.mcc_erb08")
        self.proc = ERB08Procedures(
            board_num=board_num,
            port_low=port_low,
            port_high=port_high,
            simulate=simulate,
            active_high=active_high,
            logger=self.log,
        )

    # ---- Lifecycle ----
    def initialize(self) -> None:
        try:
            self.proc.ProcInitializeRelays()
        except Exception as e:
            raise ERB08Error("Failed to initialize ERB08: {0}".format(e)) from e

    def shutdown(self) -> None:
        try:
            self.proc.ProcShutdownRelays()
        except Exception as e:
            raise ERB08Error("Failed to shutdown ERB08: {0}".format(e)) from e

    # ---- Simple control wrappers ----
    def set_relay(self, bit: int, on: bool) -> None:
        try:
            self.proc.ProcSetBit(bit, on)
        except Exception as e:
            raise ERB08Error("Failed to set relay {0} -> {1}: {2}".format(bit, on, e)) from e

    def all_off(self) -> None:
        try:
            self.proc.ProcAllOff()
        except Exception as e:
            raise ERB08Error("Failed to set all relays OFF: {0}".format(e)) from e

    def all_on(self) -> None:
        try:
            self.proc.ProcAllOn()
        except Exception as e:
            raise ERB08Error("Failed to set all relays ON: {0}".format(e)) from e

    def apply_mapping(
        self,
        bits_on: Iterable[int],
        bits_off: Iterable[int],
    ) -> None:
        try:
            mapping = RelayMapping(
                bits_on=list(bits_on),
                bits_off=list(bits_off),
            )
            self.proc.ProcApplyMapping(mapping)
        except Exception as e:
            raise ERB08Error("Failed to apply mapping: {0}".format(e)) from e

    def self_test_walk(self, delay_ms: float = 100.0) -> None:
        try:
            self.proc.ProcSelfTestWalk(delay_ms=delay_ms)
        except Exception as e:
            raise ERB08Error("Self-test walk failed: {0}".format(e)) from e
