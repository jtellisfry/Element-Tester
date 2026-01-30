# =================
# ERB08 Procedures
# =================
#
# Higher-level procedures built on top of low-level commands. This file
# contains `RelayMapping` (a small dataclass) and `ERB08Procedures`, a
# convenience layer that implements common flows such as initialization,
# all-off, apply-mapping and a simple self-test walk.
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, List
import logging

from .transport import ERB08OpenParams, ERB08Transport
from .commands import ERB08Commands


@dataclass
class RelayMapping:
    """
    Simple mapping holder for a 'mode' or 'part':
      - bits_on:  list of relay indices to be ON
      - bits_off: list of relay indices to be OFF
    """
    bits_on: List[int]
    bits_off: List[int]


class ERB08Procedures:
    """
    Higher-level procedures for the MCC USB-ERB08.

    Examples:
      - ProcInitializeRelays()
      - ProcAllOff()
      - ProcApplyMapping(mapping)
      - ProcSetContactor(on/off) [later, when we pick a contactor bit]
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
        self.log = logger or logging.getLogger("element_tester.relay.mcc_erb08")
        params = ERB08OpenParams(
            board_num=board_num,
            port_low=port_low,
            port_high=port_high,
            simulate=simulate,
            active_high=active_high,
        )
        self.t = ERB08Transport(params)
        self.cmd = ERB08Commands(self.t)

        # Optional: store a named mapping set (e.g., per part number)
        self.mappings: Dict[str, RelayMapping] = {}

    # ---------- Session ----------
    def ProcInitializeRelays(self) -> None:
        """
        Open/config the relay board and drive all relays to a safe OFF.
        """
        self.log.info(
            "ERB08 init | board=%s port_low=%s port_high=%s simulate=%s active_high=%s",
            self.t.p.board_num,
            self.t.p.port_low,
            self.t.p.port_high,
            self.t.p.simulate,
            self.t.p.active_high,
        )
        self.t.open()
        self.ProcAllOff()

    def ProcShutdownRelays(self) -> None:
        """
        Safe shutdown (all OFF then close).
        """
        self.log.info("ERB08 shutdown")
        try:
            self.ProcAllOff()
        finally:
            self.t.close()

    # ---------- Basic procedures ----------
    def ProcAllOff(self) -> None:
        """
        Drive all relays OFF.
        """
        self.log.info("ERB08 all relays OFF")
        self.cmd.cmd_all_off()

    def ProcAllOn(self) -> None:
        """
        Drive all relays ON.
        """
        self.log.info("ERB08 all relays ON")
        # Turn on all 8 bits (relays 0-7)
        for bit in range(8):
            self.cmd.cmd_set_bit(bit, True)

    def ProcSetBit(self, bit: int, on: bool) -> None:
        """
        Simple wrapper with logging for setting a single relay.
        """
        self.log.info("ERB08 set bit %s -> %s", bit, "ON" if on else "OFF")
        self.cmd.cmd_set_bit(bit, on)

    def ProcApplyMapping(self, mapping: RelayMapping) -> None:
        """
        Apply a given mapping (bits_on / bits_off).
        """
        self.log.info(
            "ERB08 apply mapping | on=%s off=%s",
            mapping.bits_on,
            mapping.bits_off,
        )
        self.cmd.cmd_set_many(mapping.bits_on, mapping.bits_off)

    # ---------- Named mappings (optional convenience) ----------
    def add_named_mapping(self, name: str, bits_on: List[int], bits_off: List[int]) -> None:
        self.mappings[name] = RelayMapping(bits_on=bits_on, bits_off=bits_off)

    def ProcApplyNamedMapping(self, name: str) -> None:
        m = self.mappings.get(name)
        if not m:
            self.log.warning("No relay mapping named %r", name)
            return
        self.ProcApplyMapping(m)

    # ---------- Simple self-test ----------
    def ProcSelfTestWalk(self, delay_ms: float = 100.0) -> None:
        """
        Walk a single ON bit from relay 0 to 7.
        Good for verifying hardware wiring / mapping.
        """
        import time
        self.log.info("ERB08 self-test walk start")

        self.ProcAllOff()
        for bit in range(8):
            self.ProcSetBit(bit, True)
            time.sleep(delay_ms / 1000.0)
            self.ProcSetBit(bit, False)

        self.log.info("ERB08 self-test walk end")
        self.ProcAllOff()
