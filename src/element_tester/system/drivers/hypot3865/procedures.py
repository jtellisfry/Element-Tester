from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Tuple, Optional
import time
import logging
import json
from pathlib import Path

from .transport import AR3865Transport, AR3865OpenParams
from .commands import AR3865Commands, HipotConfig


@dataclass
class HipotState:
    is_open: bool = False
    last_result: Optional[str] = None


class AR3865Procedures:
    """
    Higher-level instrument-specific flows for the AR 3865.

    - Uses AR3865Commands (LEGOs) to build practical sequences.
    - This is what your test runner will typically call.
    """

    def __init__(
        self,
        resource: str,
        baudrate: int = 38400,  # AR3865 uses 38400 baud
        simulate: bool = False,
        timeout_ms: int = 5000,
        logger: Optional[logging.Logger] = None,
    ):
        self.log = logger or logging.getLogger("hypot3865")
        params = AR3865OpenParams(
            resource=resource,
            baudrate=baudrate,
            simulate=simulate,
            timeout_ms=timeout_ms,
        )
        self.t = AR3865Transport(params)       # transport: low-level I/O
        self.cmd = AR3865Commands(self.t)      # commands: building blocks
        self.state = HipotState()

    # ---------- Session ----------
    def init(self) -> None:
        """Open session and make sure instrument is sane."""
        self.log.info("Hipot INIT")
        self.t.open()
        self.cmd.cmd_reset()
        self.cmd.cmd_clear_faults()
        idn = self.cmd.cmd_idn()
        self.log.info(f"Hipot IDN: {idn}")
        self.state.is_open = True

    def close(self) -> None:
        self.log.info("Hipot CLOSE")
        try:
            self.t.close()
        finally:
            self.state.is_open = False
    
    def reset(self) -> None:
        """
        Soft reset: *RST + clear faults.
        Keeps session open, resets instrument to known state.
        """
        self.log.info("Hipot RESET (*RST + *CLS)")
        self.cmd.cmd_reset()
        self.cmd.cmd_clear_faults()

    # ---------- Configuration ----------
    def configure(self, cfg: HipotConfig) -> None:
        self.log.info(f"Hipot CONFIG: {cfg}")
        self.cmd.cmd_apply_config(cfg)

    # ---------- One-shot run ----------
    def run_once_blocking(self, cfg: HipotConfig, timeout_s: float = 10.0) -> Tuple[bool, str]:
        """
        Full cycle: config → start → poll → discharge → return pass/fail and raw result.
        """
        if not self.state.is_open:
            self.init()

        # Apply configuration (if provided)
        if cfg is not None:
            self.configure(cfg)
        self.log.info("Hipot START")
        self.cmd.cmd_test()

        # Wait for test to complete, then check result
        # RD 1? returns: <step>,<test_type>,<status>,<voltage>,<current>,<time>
        # Example: "01,ACW,PASS,1.24,0.003,2.0"
        time.sleep(timeout_s)  # Wait for test duration
        
        # Get final result
        result = self.cmd.cmd_get_result()
        self.state.last_result = result
        self.log.info(f"Hipot RESULT(raw) = '{result}'")
        self.log.info(f"Hipot RESULT(repr) = {repr(result)}")
        
        # Simple: if "PASS" is in result, it passed. Anything else = fail
        # Strip whitespace and convert to uppercase for comparison
        result_clean = (result or "").strip().upper()
        passed = "PASS" in result_clean
        self.log.info(f"Hipot RESULT(clean) = '{result_clean}' → passed={passed}")

        # Always discharge after a run
        self.log.info("Hipot DISCHARGE")
        self.cmd.cmd_discharge_wait(0.5)

        return passed, result

    def run_from_file(self, file_index: int, timeout_s: float = 10.0) -> Tuple[bool, str, float]:
        """
        Select a test file via FL <n>, start test, poll result, discharge.
        This bypasses parameter configuration and relies on instrument-stored files.
        
        Returns:
            (passed, result_string, test_start_time)
        """
        if not self.state.is_open:
            self.init()

        self.log.info(f"Hipot SELECT FILE: FL {file_index}")
        self.cmd.cmd_select_file(file_index)
        
        print(f"\n{'='*60}")
        print(f"HIPOT TEST TIMING DEBUG")
        print(f"{'='*60}")
        print(f"Sending FL {file_index} command...")
        
        self.log.info("Hipot START")
        test_start_time = time.time()
        print(f"TEST START TIME: {test_start_time:.3f}")
        self.cmd.cmd_test()
        print(f"TEST command sent at: {time.time():.3f} (elapsed: {time.time() - test_start_time:.3f}s)")

        # Wait for test to complete + extra time for instrument to process result
        wait_time = timeout_s + 1.0  # Add 1 second for instrument to process and have result ready
        self.log.info(f"Hipot WAIT {wait_time}s for test completion...")
        print(f"Waiting {wait_time}s for test to complete (test: {timeout_s}s + processing: 1.0s)...")
        time.sleep(wait_time)
        print(f"Wait complete at: {time.time():.3f} (elapsed: {time.time() - test_start_time:.3f}s)")

        # Read final result (should be ready now)
        print(f"\nReading result with RD 1? command...")
        result = self.cmd.cmd_get_result()
        print(f"Result received at: {time.time():.3f} (elapsed: {time.time() - test_start_time:.3f}s)")
        
        self.state.last_result = result
        
        # Detailed result analysis
        print(f"\n{'='*60}")
        print(f"RD 1? RESULT ANALYSIS")
        print(f"{'='*60}")
        print(f"Raw result (type={type(result).__name__}, len={len(result) if result else 0}):")
        print(f"  '{result}'")
        print(f"Repr (shows hidden chars):")
        print(f"  {repr(result)}")
        print(f"Bytes (hex):")
        if result:
            print(f"  {' '.join(f'{ord(c):02x}' for c in result)}")
        else:
            print(f"  (empty/None)")
        
        self.log.info(f"Hipot RESULT(raw) = '{result}'")
        self.log.info(f"Hipot RESULT(repr) = {repr(result)}")

        # Simple logic: PASS = good, anything else = fail
        # Strip whitespace and convert to uppercase for comparison
        result_clean = (result or "").strip().upper()
        passed = "PASS" in result_clean
        
        print(f"\nCleaned result:")
        print(f"  '{result_clean}'")
        print(f"Checking for 'PASS' in cleaned result...")
        print(f"  'PASS' in '{result_clean}' = {passed}")
        print(f"\nFINAL DECISION: {'✓ PASSED' if passed else '✗ FAILED'}")
        print(f"{'='*60}\n")
        
        self.log.info(f"Hipot RESULT(clean) = '{result_clean}' → passed={passed}")

        self.log.info("Hipot DISCHARGE")
        self.cmd.cmd_discharge_wait(0.5)

        return passed, result, test_start_time

    # ---------- Manual control (debug / special) ----------
    def start(self) -> None:
        """Manual start, e.g. from a debug screen."""
        if not self.state.is_open:
            self.init()
        self.cmd.cmd_test()

    def stop(self) -> None:
        """Manual stop/abort."""
        self.cmd.cmd_stop_test()

    def get_result(self) -> str:
        """Get raw result using RD 1? command."""
        r = self.cmd.cmd_get_result()
        self.state.last_result = r
        return r

    def discharge(self, dwell_s: float = 0.5) -> None:
        """Discharge without running a full test."""
        self.cmd.cmd_discharge_wait(dwell_s)

    # ---------- Helper for quick calls ----------
    def quick_run(
        self,
        voltage_v: float,
        current_trip_mA: float,
        ramp_s: float,
        dwell_s: float,
        fall_s: float,
        timeout_s: float = 10.0,
    ) -> Tuple[bool, str]:
        cfg = HipotConfig(
            voltage_v=voltage_v,
            current_trip_mA=current_trip_mA,
            ramp_time_s=ramp_s,
            dwell_time_s=dwell_s,
            fall_time_s=fall_s,
        )
        return self.run_once_blocking(cfg, timeout_s=timeout_s)
    
    # ---------- Configuration management ----------
    def read_config(self) -> HipotConfig:
        """
        Read current configuration from instrument.
        Returns HipotConfig with None for any unreadable fields.
        Useful for capturing current state before modifying.
        """
        if not self.state.is_open:
            self.init()
        cfg = self.cmd.cmd_read_config()
        self.log.info(f"Hipot READ CONFIG: {cfg}")
        return cfg
    
    def merge_config(self, base: HipotConfig, override: HipotConfig) -> HipotConfig:
        """
        Merge two configs: use override values if not None, else use base.
        Useful for partial updates.
        """
        return HipotConfig(
            voltage_v=override.voltage_v if override.voltage_v is not None else base.voltage_v,
            current_trip_mA=override.current_trip_mA if override.current_trip_mA is not None else base.current_trip_mA,
            ramp_time_s=override.ramp_time_s if override.ramp_time_s is not None else base.ramp_time_s,
            dwell_time_s=override.dwell_time_s if override.dwell_time_s is not None else base.dwell_time_s,
            fall_time_s=override.fall_time_s if override.fall_time_s is not None else base.fall_time_s,
            polarity=override.polarity if override.polarity is not None else base.polarity,
        )
    
    # ---------- JSON file presets ----------
    def _presets_base_dir(self) -> Path:
        """
        Compute presets directory: <repo_root>/data/presets/hipot/
        Avoids hard-coding paths; works from any CWD.
        """
        # procedures.py -> hypot3865 -> drivers -> system -> element_tester -> src -> repo_root
        repo_root = Path(__file__).resolve().parents[5]
        presets_dir = repo_root / "data" / "presets" / "hipot"
        presets_dir.mkdir(parents=True, exist_ok=True)
        return presets_dir
    
    def save_preset(self, name: str, cfg: HipotConfig) -> Path:
        """
        Save HipotConfig to JSON file: data/presets/hipot/<name>.json
        Useful for storing common test profiles (e.g., "standard_1500V", "low_voltage_test").
        """
        path = self._presets_base_dir() / f"{name}.json"
        # Filter out None values for cleaner JSON
        data = {k: v for k, v in asdict(cfg).items() if v is not None}
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.log.info(f"Hipot PRESET saved: {path}")
        return path
    
    def load_preset(self, name: str) -> HipotConfig:
        """
        Load HipotConfig from JSON file: data/presets/hipot/<name>.json
        Returns config with fields from file; missing fields will be None.
        """
        path = self._presets_base_dir() / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Preset not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = HipotConfig(
            voltage_v=data.get("voltage_v"),
            current_trip_mA=data.get("current_trip_mA"),
            ramp_time_s=data.get("ramp_time_s"),
            dwell_time_s=data.get("dwell_time_s"),
            fall_time_s=data.get("fall_time_s"),
            polarity=data.get("polarity"),
        )
        self.log.info(f"Hipot PRESET loaded: {path} -> {cfg}")
        return cfg
    
    def apply_preset(self, name: str) -> None:
        """
        Load a preset from JSON and apply it to the instrument.
        Convenience wrapper for load_preset() + configure().
        """
        cfg = self.load_preset(name)
        self.configure(cfg)
    
    # ---------- Instrument memory slots (if AR 3865 supports *SAV/*RCL) ----------
    def save_to_instrument_slot(self, slot: int) -> None:
        """
        Save current instrument configuration to internal memory slot.
        Uses *SAV SCPI command (if supported by AR 3865).
        Slots typically 1-9.
        """
        if not self.state.is_open:
            self.init()
        self.log.info(f"Hipot SAVE to instrument slot {slot}")
        self.cmd.cmd_save_to_slot(slot)
    
    def recall_from_instrument_slot(self, slot: int) -> None:
        """
        Recall configuration from instrument internal memory slot.
        Uses *RCL SCPI command (if supported by AR 3865).
        Automatically applies config to instrument.
        """
        if not self.state.is_open:
            self.init()
        self.log.info(f"Hipot RECALL from instrument slot {slot}")
        self.cmd.cmd_recall_from_slot(slot)
