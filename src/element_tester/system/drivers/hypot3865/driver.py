from __future__ import annotations
from typing import Optional, Tuple
import logging

from .procedures import AR3865Procedures, HipotState
from .commands import HipotConfig


class Hypot3865Error(Exception):
    """Driver-level wrapper error for AR3865 operations."""


class AR3865Driver:
    """
    Front-end façade for the AR 3865 Hipot driver.

    Wraps AR3865Procedures and exposes a small, safe API for the rest of the app.
    Usage examples:
      drv = AR3865Driver(resource="serial://COM3", simulate=True)
      drv.initialize()
      passed, raw = drv.quick_run(1000, 5, 1, 1, 0.5)
      drv.shutdown()
    """

    def __init__(
        self,
        resource: str,
        baudrate: int = 38400,  # AR3865 uses 38400 baud
        simulate: bool = False,
        timeout_ms: int = 5000,
        logger: Optional[logging.Logger] = None,
    ):
        self.log = logger or logging.getLogger("element_tester.driver.hypot3865")
        self.proc = AR3865Procedures(
            resource=resource,
            baudrate=baudrate,
            simulate=simulate,
            timeout_ms=timeout_ms,
            logger=self.log,
        )

    # ---- Lifecycle ----
    def initialize(self) -> None:
        try:
            self.proc.init()
        except Exception as e:
            raise Hypot3865Error(f"Failed to initialize AR3865: {e}") from e

    def shutdown(self) -> None:
        try:
            self.proc.close()
        except Exception as e:
            raise Hypot3865Error(f"Failed to shutdown AR3865: {e}") from e

    # ---- Configuration / runs ----
    def configure(self, cfg: HipotConfig) -> None:
        try:
            self.proc.configure(cfg)
        except Exception as e:
            raise Hypot3865Error(f"Failed to apply config: {e}") from e

    def run_once(self, cfg: HipotConfig, timeout_s: float = 10.0) -> Tuple[bool, str]:
        try:
            return self.proc.run_once_blocking(cfg, timeout_s=timeout_s)
        except Exception as e:
            raise Hypot3865Error(f"Run failed: {e}") from e

    def quick_run(
        self,
        voltage_v: float,
        current_trip_mA: float,
        ramp_s: float,
        dwell_s: float,
        fall_s: float,
        timeout_s: float = 10.0,
    ) -> Tuple[bool, str]:
        try:
            return self.proc.quick_run(
                voltage_v=voltage_v,
                current_trip_mA=current_trip_mA,
                ramp_s=ramp_s,
                dwell_s=dwell_s,
                fall_s=fall_s,
                timeout_s=timeout_s,
            )
        except Exception as e:
            raise Hypot3865Error(f"Quick run failed: {e}") from e

    def run_from_file(self, file_index: int, timeout_s: float = 10.0) -> Tuple[bool, str, float]:
        """Run test using stored file (FL command). Returns (passed, result, test_start_time)."""
        try:
            return self.proc.run_from_file(file_index=file_index, timeout_s=timeout_s)
        except Exception as e:
            raise Hypot3865Error(f"Run from file failed: {e}") from e

    # ---- Manual control ----
    def start(self) -> None:
        try:
            self.proc.start()
        except Exception as e:
            raise Hypot3865Error(f"Failed to start test: {e}") from e

    def stop(self) -> None:
        try:
            self.proc.stop()
        except Exception as e:
            raise Hypot3865Error(f"Failed to stop test: {e}") from e

    def get_result(self) -> str:
        try:
            return self.proc.get_result()
        except Exception as e:
            raise Hypot3865Error(f"Failed to get result: {e}") from e

    def discharge(self, dwell_s: float = 0.5) -> None:
        try:
            self.proc.discharge(dwell_s)
        except Exception as e:
            raise Hypot3865Error(f"Failed to discharge: {e}") from e

    # ---- Introspection ----
    @property
    def is_open(self) -> bool:
        return bool(getattr(self.proc.state, "is_open", False))

    @property
    def last_result(self) -> Optional[str]:
        return getattr(self.proc.state, "last_result", None)

    def idn(self) -> str:
        """Return *IDN? (best-effort)."""
        try:
            # Procedures exposes commands via self.proc.cmd; use it for IDN
            return self.proc.cmd.cmd_idn()
        except Exception:
            return "AR-3865"
    
    # ---- Configuration management ----
    def reset(self) -> None:
        """
        Soft reset instrument (*RST + clear faults).
        Keeps session open.
        """
        try:
            self.proc.reset()
        except Exception as e:
            raise Hypot3865Error(f"Failed to reset: {e}") from e
    
    def read_config(self) -> HipotConfig:
        """
        Read current configuration from instrument.
        Returns HipotConfig with None for unreadable fields.
        """
        try:
            return self.proc.read_config()
        except Exception as e:
            raise Hypot3865Error(f"Failed to read config: {e}") from e
    
    def merge_config(self, base: HipotConfig, override: HipotConfig) -> HipotConfig:
        """
        Merge two configs: override takes precedence for non-None fields.
        Useful for partial updates.
        """
        return self.proc.merge_config(base, override)
    
    # ---- JSON file presets ----
    def save_preset(self, name: str, cfg: HipotConfig) -> None:
        """
        Save config to JSON preset file: data/presets/hipot/<name>.json
        Example: drv.save_preset(\"standard_1500V\", my_config)
        """
        try:
            self.proc.save_preset(name, cfg)
        except Exception as e:
            raise Hypot3865Error(f"Failed to save preset '{name}': {e}") from e
    
    def load_preset(self, name: str) -> HipotConfig:
        """
        Load config from JSON preset file: data/presets/hipot/<name>.json
        Example: cfg = drv.load_preset(\"standard_1500V\")
        """
        try:
            return self.proc.load_preset(name)
        except Exception as e:
            raise Hypot3865Error(f"Failed to load preset '{name}': {e}") from e
    
    def apply_preset(self, name: str) -> None:
        """
        Load preset from JSON and apply to instrument.
        Convenience wrapper for load_preset() + configure().
        """
        try:
            self.proc.apply_preset(name)
        except Exception as e:
            raise Hypot3865Error(f"Failed to apply preset '{name}': {e}") from e
    
    # ---- Instrument memory slots ----
    def save_to_instrument_slot(self, slot: int) -> None:
        """
        Save current config to instrument internal memory slot (1-9 typical).
        Uses *SAV SCPI command if supported by AR 3865.
        """
        try:
            self.proc.save_to_instrument_slot(slot)
        except Exception as e:
            raise Hypot3865Error(f"Failed to save to instrument slot {slot}: {e}") from e
    
    def recall_from_instrument_slot(self, slot: int) -> None:
        """
        Recall config from instrument internal memory slot (1-9 typical).
        Uses *RCL SCPI command if supported by AR 3865.
        """
        try:
            self.proc.recall_from_instrument_slot(slot)
        except Exception as e:
            raise Hypot3865Error(f"Failed to recall from instrument slot {slot}: {e}") from e