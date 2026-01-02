from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, List
import logging

from .transport import PDIS08OpenParams, PDIS08Transport
from .commands import PDIS08Commands


@dataclass
class RelayMapping:
    bits_on: List[int]
    bits_off: List[int]


class PDIS08Procedures:
    def __init__(
        self,
        board_num: int = 1,
        port_low: object = 12,
        port_high: object = 13,
        simulate: bool = False,
        active_high: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.log = logger or logging.getLogger("element_tester.relay.mcc_pdis")
        params = PDIS08OpenParams(
            board_num=board_num,
            port_low=port_low,
            port_high=port_high,
            simulate=simulate,
            active_high=active_high,
        )
        self.t = PDIS08Transport(params)
        self.cmd = PDIS08Commands(self.t)
        self.mappings: Dict[str, RelayMapping] = {}

    def ProcInitializeRelays(self) -> None:
        self.log.info(
            "PDIS08 init | board=%s port_low=%s port_high=%s simulate=%s active_high=%s",
            self.t.p.board_num,
            self.t.p.port_low,
            self.t.p.port_high,
            self.t.p.simulate,
            self.t.p.active_high,
        )
        self.t.open()
        self.ProcAllOff()

    def ProcShutdownRelays(self) -> None:
        self.log.info("PDIS08 shutdown")
        try:
            self.ProcAllOff()
        finally:
            self.t.close()

    def ProcAllOff(self) -> None:
        self.log.info("PDIS08 all relays OFF")
        self.cmd.cmd_all_off()

    def ProcAllOn(self) -> None:
        self.log.info("PDIS08 all relays ON")
        for bit in range(8):
            self.cmd.cmd_set_channel(bit, True)

    def ProcSetBit(self, bit: int, on: bool) -> None:
        self.log.info("PDIS08 set bit %s -> %s", bit, "ON" if on else "OFF")
        self.cmd.cmd_set_channel(bit, on)

    def ProcApplyMapping(self, mapping: RelayMapping) -> None:
        self.log.info("PDIS08 apply mapping | on=%s off=%s", mapping.bits_on, mapping.bits_off)
        self.cmd.cmd_set_many(mapping.bits_on, mapping.bits_off)

    def add_named_mapping(self, name: str, bits_on: List[int], bits_off: List[int]) -> None:
        self.mappings[name] = RelayMapping(bits_on=bits_on, bits_off=bits_off)

    def ProcApplyNamedMapping(self, name: str) -> None:
        m = self.mappings.get(name)
        if not m:
            self.log.warning("No relay mapping named %r", name)
            return
        self.ProcApplyMapping(m)

    def ProcSelfTestWalk(self, delay_ms: float = 100.0) -> None:
        import time
        self.log.info("PDIS08 self-test walk start")
        self.ProcAllOff()
        for bit in range(8):
            self.ProcSetBit(bit, True)
            time.sleep(delay_ms / 1000.0)
            self.ProcSetBit(bit, False)
        self.log.info("PDIS08 self-test walk end")
        self.ProcAllOff()
