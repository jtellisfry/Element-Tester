from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .transport import AR3865Transport


@dataclass
class HipotConfig:
    """
    Configuration for AR 3865 Hipot test.
    
    All fields are Optional to support:
    - Partial updates (only change voltage, keep other settings)
    - Reading current config from instrument
    - Merging with saved presets
    
    If None, that parameter won't be sent to the instrument during apply.
    """
    voltage_v: Optional[float] = None
    current_trip_mA: Optional[float] = None
    ramp_time_s: Optional[float] = None
    dwell_time_s: Optional[float] = None
    fall_time_s: Optional[float] = None
    polarity: Optional[str] = None   # "POS" / "NEG" if supported


class AR3865Commands:
    """
    Low-level building blocks (LEGOs) for the AR 3865.

    Each method is a small, focused action that knows how to talk SCPI,
    but does not decide pass/fail or test flow.
    """

    def __init__(self, transport: AR3865Transport):
        self.t = transport

    # -------- Session / status --------
    def cmd_reset(self) -> None:
        #"""Reset and clear status."""
        self.t.write("RESET")
        self.t.write("*CLS")

    def cmd_clear_faults(self) -> None:
        """Clear latched faults."""
        self.t.write("SYST:CLE")

    def cmd_idn(self) -> str:
        """Return *IDN? result."""
        return self.t.idn()

    # -------- Configuration --------
    def cmd_set_voltage(self, v: float) -> None:
        self.t.write(f"VOLT {v}")

    def cmd_set_current_trip(self, mA: float) -> None:
        self.t.write(f"CURR:TRIP {mA}mA")

    def cmd_set_timing(self, ramp_s: float, dwell_s: float, fall_s: float) -> None:
        self.t.write(f"RAMP {ramp_s}")
        self.t.write(f"DWEL {dwell_s}")
        self.t.write(f"FALL {fall_s}")

    def cmd_set_polarity(self, polarity: str = "POS") -> None:
        pol = polarity.strip().upper()
        if pol in ("POS", "NEG"):
            self.t.write(f"POL {pol}")
        # else: ignore unsupported value

    def cmd_apply_config(self, cfg: HipotConfig) -> None:
        """
        Apply configuration to instrument.
        Only sends non-None fields (allows partial updates).
        """
        if cfg.voltage_v is not None:
            self.cmd_set_voltage(cfg.voltage_v)
        if cfg.current_trip_mA is not None:
            self.cmd_set_current_trip(cfg.current_trip_mA)
        if cfg.ramp_time_s is not None or cfg.dwell_time_s is not None or cfg.fall_time_s is not None:
            # For timing, use current value if any field is None (requires query or assume defaults)
            ramp = cfg.ramp_time_s if cfg.ramp_time_s is not None else 1.0
            dwell = cfg.dwell_time_s if cfg.dwell_time_s is not None else 1.0
            fall = cfg.fall_time_s if cfg.fall_time_s is not None else 0.5
            self.cmd_set_timing(ramp, dwell, fall)
        if cfg.polarity is not None:
            self.cmd_set_polarity(cfg.polarity)

    # -------- Execution --------
    def cmd_test(self) -> None:
        self.t.write("TEST")

    
    def cmd_get_result(self) -> str:
        """Read test result using RD 1? (AR3865 specific command).
        
        Returns:
            Result string from instrument. Expected responses:
            - "PASS" for passed test
            - "Short" for shorted test
            - "HI-LIMIT" for over-current trip
            - "Dwell" or "Ramp Up" if test still in progress
        """
        # Flush any stale data from input buffer before querying
        self.t.flush_input()
        return self.t.query("RD 1?")

    def cmd_select_file(self, file_index: int) -> None:
        """
        Select the instrument's internal test file/profile.
        Uses vendor command "FL <n>" where n is typically 1 or 2.
        """
        n = int(file_index)
        if n < 1:
            n = 1
        self.t.write(f"FL {n}")

    def cmd_query_selected_file(self) -> Optional[int]:
        """
        Query which test file is currently selected via "FL?".
        Returns the integer file index if parseable, else None.
        """
        try:
            resp = self.t.query("FL?")
            return int(str(resp).strip())
        except Exception:
            return None

    # -------- Configuration query (if supported) --------
    def cmd_query_voltage(self) -> Optional[float]:
        """Query current voltage setting from instrument."""
        try:
            resp = self.t.query("VOLT?")
            return float(resp)
        except Exception:
            return None
    
    def cmd_query_current_trip(self) -> Optional[float]:
        """Query current trip setting (mA) from instrument."""
        try:
            resp = self.t.query("CURR:TRIP?")
            # May need parsing if response includes units
            return float(resp.replace("mA", "").strip())
        except Exception:
            return None
    
    def cmd_read_config(self) -> HipotConfig:
        """
        Read current configuration from instrument (best-effort).
        Returns HipotConfig with None for any unreadable fields.
        """
        return HipotConfig(
            voltage_v=self.cmd_query_voltage(),
            current_trip_mA=self.cmd_query_current_trip(),
            # Add more queries as needed when you know the SCPI commands
            ramp_time_s=None,  # Add RAMP? query if supported
            dwell_time_s=None,  # Add DWEL? query if supported
            fall_time_s=None,   # Add FALL? query if supported
            polarity=None,      # Add POL? query if supported
        )
    
    # -------- Instrument memory slots (if AR 3865 supports *SAV/*RCL) --------
    def cmd_save_to_slot(self, slot: int) -> None:
        """
        Save current instrument config to memory slot (1-9 typical).
        Uses *SAV command if supported by AR 3865.
        """
        self.t.write(f"*SAV {slot}")
    
    def cmd_recall_from_slot(self, slot: int) -> None:
        """
        Recall config from instrument memory slot (1-9 typical).
        Uses *RCL command if supported by AR 3865.
        """
        self.t.write(f"*RCL {slot}")
    
    # -------- Safety / utility --------
    def cmd_discharge_wait(self, dwell_s: float = 0.5) -> None:
        """
        Passive discharge wait. If AR3865 has a specific discharge command,
        you can add it here before the sleep.
        """
        import time
        time.sleep(dwell_s)
