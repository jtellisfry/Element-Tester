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

    # ---- Pin-Specific Measurement Functions ----
    def close_pin1to6(self, delay_ms: float = 200.0) -> None:
        """
        Close relays to measure resistance between pin 1 and pin 6.
        
        Relay mapping:
        - Relay 4 (bit 4): Meter position
        
        Args:
            delay_ms: Settling delay after relay closure in milliseconds
        """
        try:
            self.all_off()
            import time
            time.sleep(0.5)
            self.set_relay(4, True)  # Meter position (relay 5, bit 4)
            self.log.info("RELAY: Waiting 1 second after closing relay 5 (bit 4)")
            time.sleep(3.0)  # 3 second delay after closing relay 5
            time.sleep(delay_ms / 1000.0)
            self.log.info(f"RELAY: Pin1to6 closed with {delay_ms}ms settling delay")
        except Exception as e:
            raise ERB08Error("Failed to close Pin1to6: {0}".format(e)) from e

    def open_pin1to6(self, delay_ms: float = 100.0) -> None:
        """
        Open relays after pin 1 to pin 6 measurement.
        
        Args:
            delay_ms: Delay after opening relays in milliseconds
        """
        try:
            import time
            self.log.info("RELAY: Waiting 1 second before opening relay 5 (bit 4)")
            time.sleep(1.0)  # 1 second delay before opening relay 5
            self.all_off()
            time.sleep(delay_ms / 1000.0)
            self.log.info(f"RELAY: Pin1to6 opened with {delay_ms}ms delay")
        except Exception as e:
            raise ERB08Error("Failed to open Pin1to6: {0}".format(e)) from e

    def close_pin2to5(self, delay_ms: float = 200.0) -> None:
        """
        Close relays to measure resistance between pin 2 and pin 5.
        
        Relay mapping:
        - Relay 0 (bit 0): Pin 2
        - Relay 4 (bit 4): Meter position
        - Relay 1 (bit 1): Pin 5
        
        Args:
            delay_ms: Settling delay after relay closure in milliseconds
        """
        try:
            self.all_off()
            import time
            time.sleep(0.05)
            self.set_relay(0, True)  # Pin 2
            self.set_relay(4, True)  # Meter position
            self.set_relay(1, True)  # Pin 5
            time.sleep(delay_ms / 1000.0)
            self.log.info(f"RELAY: Pin2to5 closed with {delay_ms}ms settling delay")
        except Exception as e:
            raise ERB08Error("Failed to close Pin2to5: {0}".format(e)) from e

    def open_pin2to5(self, delay_ms: float = 100.0) -> None:
        """
        Open relays after pin 2 to pin 5 measurement.
        
        Args:
            delay_ms: Delay after opening relays in milliseconds
        """
        try:
            self.all_off()
            import time
            time.sleep(delay_ms / 1000.0)
            self.log.info(f"RELAY: Pin2to5 opened with {delay_ms}ms delay")
        except Exception as e:
            raise ERB08Error("Failed to open Pin2to5: {0}".format(e)) from e

    def close_pin3to4(self, delay_ms: float = 200.0) -> None:
        """
        Close relays to measure resistance between pin 3 and pin 4.
        
        Relay mapping:
        - Relay 2 (bit 2): Pin 3
        - Relay 4 (bit 4): Meter position
        - Relay 3 (bit 3): Pin 4
        
        Args:
            delay_ms: Settling delay after relay closure in milliseconds
        """
        try:
            self.all_off()
            import time
            time.sleep(0.05)
            self.set_relay(2, True)  # Pin 3
            self.set_relay(3, True)  # Pin 4
            time.sleep(delay_ms / 1000.0)
            self.log.info(f"RELAY: Pin3to4 closed with {delay_ms}ms settling delay")
        except Exception as e:
            raise ERB08Error("Failed to close Pin3to4: {0}".format(e)) from e

    def open_pin3to4(self, delay_ms: float = 100.0) -> None:
        """
        Open relays after pin 3 to pin 4 measurement.
        
        Args:
            delay_ms: Delay after opening relays in milliseconds
        """
        try:
            self.all_off()
            import time
            time.sleep(delay_ms / 1000.0)
            self.log.info(f"RELAY: Pin3to4 opened with {delay_ms}ms delay")
        except Exception as e:
            raise ERB08Error("Failed to open Pin3to4: {0}".format(e)) from e
