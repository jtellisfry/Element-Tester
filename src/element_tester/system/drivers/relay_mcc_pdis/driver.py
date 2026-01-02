from __future__ import annotations
from typing import Optional, List
import logging

from .procedures import PDIS08Procedures


class PDIS08Driver:
    """High-level driver facade for PDIS08 relay board."""

    def __init__(
        self,
        board_num: int = 1,
        port_low=1,
        port_high=None,
        simulate: bool = False,
        active_high: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.log = logger or logging.getLogger("element_tester.relay.mcc_pdis.driver")
        self.procs = PDIS08Procedures(
            board_num=board_num,
            port_low=port_low,
            port_high=port_high,
            simulate=simulate,
            active_high=active_high,
            logger=self.log,
        )

    def initialize(self) -> None:
        self.procs.ProcInitializeRelays()

    def shutdown(self) -> None:
        self.procs.ProcShutdownRelays()

    def set_relay(self, channel: int, on: bool) -> None:
        self.procs.ProcSetBit(channel, on)

    def all_off(self) -> None:
        self.procs.ProcAllOff()

    def all_on(self) -> None:
        self.procs.ProcAllOn()

    def add_named_mapping(self, name: str, bits_on: List[int], bits_off: List[int]) -> None:
        self.procs.add_named_mapping(name, bits_on, bits_off)

    def apply_named_mapping(self, name: str) -> None:
        self.procs.ProcApplyNamedMapping(name)

    def self_test_walk(self, delay_ms: float = 100.0) -> None:
        self.procs.ProcSelfTestWalk(delay_ms)
