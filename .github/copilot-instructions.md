# Element Tester – AI Coding Agent Instructions

## Project Overview
**Element Tester** is a PyQt6-based high-voltage test automation system combining two instrument drivers:
- **AR 3865 Hipot Tester** (SCPI-controlled via VISA/serial)
- **MCC USB-ERB08 Relay Board** (digital I/O control via mcculw)

Results are logged to `data/results/` in both JSON and human-readable formats. The application supports **simulate mode** for development without hardware.

---

## Architecture Pattern: Transport → Commands → Procedures

Each driver follows a three-layer pattern:

### **Transport Layer**
- **File**: `src/element_tester/system/drivers/{driver_name}/transport.py`
- **Responsibility**: Raw I/O (VISA, serial, or hardware API)
- **Key**: Gracefully handles missing dependencies; always supports simulate mode
- **Example**: `AR3865Transport.write(cmd)`, `AR3865Transport.query(cmd)`

### **Commands Layer**
- **File**: `src/element_tester/system/drivers/{driver_name}/commands.py`
- **Responsibility**: Small, focused SCPI/protocol commands (the "LEGOs")
- **Key**: No pass/fail logic, no flow decisions—just instruction building blocks
- **Example**: `AR3865Commands.cmd_set_voltage(v)`, `ERB08Commands.cmd_set_bit(bit, on)`

### **Procedures Layer**
- **File**: `src/element_tester/system/drivers/{driver_name}/procedures.py`
- **Responsibility**: Practical, repeatable sequences combining commands
- **Key**: Session management, configuration bundles, pass/fail interpretation
- **Example**: `AR3865Procedures.run_once_blocking()`, `ERB08Procedures.ProcApplyMapping()`

---

## Key Files & Workflows

### Main Test Orchestration
- **`src/element_tester/system/core/test_runner.py`**: Top-level test sequencer
  - Entry point: `TestRunner.run_full_sequence(ui, work_order, part_number)`
  - Routes to `_run_normal_sequence()` or `_run_demo_sequence()` (WO=TEST, PN=TEST)
  - Calls `run_hipot()` → `run_measuring()`
  - Writes results to `data/results/test_results.{jsonl,txt}`

### UI Layer
- **`src/element_tester/system/ui/scanning.py`**: Initial scan window (Work Order + Part Number)
  - Emits `scanCompleted` signal when both fields filled
- **`src/element_tester/system/ui/testing.py`**: Main test display
  - Methods: `hypot_ready()`, `hypot_running()`, `hypot_result(passed)`
  - Methods: `update_measurement(side, row_index, text, passed)`

### Debug Tool
- **`src/element_tester/system/ui/debug.py`**: Generic debug dialog
  - Accepts dict of `{label: callback}` for radio-button actions
  - Useful for testing individual relay/hipot sequences

---

## Driver-Specific Communication Details

### AR3865 Hipot Tester (Associated Research)

**Hardware Connection:**
- **Interface**: RS-232 Serial (DB-9 connector)
- **Port**: COM6 (verify in Device Manager)
- **Baud Rate**: 38400
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None
- **Line Terminator**: `\r\n` (both CR and LF required)

**Remote Control Requirements:**
- **PLC Remote Mode**: Must be enabled on instrument front panel for serial communication
- Enable via: Menu → Setup → Remote → PLC Remote ON

**Communication Protocol:**
- Standard SCPI-like commands
- Commands are case-insensitive
- Query commands end with `?`
- Most commands return no response (write-only)
- Queries return responses terminated with `\n`

**Identification:**
- **Command**: `*IDN?\r\n`
- **Response Format**: `ASSOCIATED RESEARCH INC.,3865,<serial>,<version>\n`
- **Example Response**: `ASSOCIATED RESEARCH INC.,3865,9841198,Version 2.03.00`

**Test Status & Result Codes:**
- **Commands to query status**: `TEST:RESULT?`, `RESULT?`, `STAT?`
- **Success Codes**: `PASS`, `PASSED`, `OK`
- **Failure Codes**: `FAIL`, `FAILED`, `TRIP`, `ARC`, `SHORT`
- **Status Codes**: `RUNNING`, `BUSY`, `IN PROGRESS`, `READY`, `IDLE`
- **Error Codes**: TBD (user to provide specific error codes from manual)

**Configuration Commands:**
- Voltage setting: TBD (format to be determined via command discovery)
- Current trip: TBD
- Timing (ramp/dwell/fall): TBD
- Test execution: TBD
- Result queries: TBD

**Important Notes:**
- Response parsing may return empty strings if command not supported
- Use debug logging to verify commands are being sent/received
- Check front panel display to confirm settings are applied
- Instrument must be in Remote mode for any commands to work

**Files:**
- Transport: `src/element_tester/system/drivers/hypot3865/transport.py`
- Commands: `src/element_tester/system/drivers/hypot3865/commands.py`
- Procedures: `src/element_tester/system/drivers/hypot3865/procedures.py`
- Driver: `src/element_tester/system/drivers/hypot3865/driver.py`

---

### MCC USB-ERB08 Relay Board

**Hardware Connection:**
- **Interface**: USB (using MCC Universal Library via `mcculw`)
- **Board Number**: 0 (default)
- **Ports Used**: 
  - Port 12 (FIRSTPORTA): Relays 0-3 (bits 0-3)
  - Port 13 (FIRSTPORTB): Relays 4-7 (bits 0-3)
- **Active Logic**: Configurable (active-high or active-low)

**Communication Protocol:**
- Direct digital I/O via MCC Universal Library
- No serial protocol—uses hardware API calls
- Commands execute immediately (no buffering)

**Error Handling:**
- Library returns error codes on failure
- Common errors: Board not found, invalid port/bit
- All errors wrapped in `ERB08Error` exception class

**Configuration:**
- `ERB08OpenParams`: board_num, port_low, port_high, simulate, active_high
- Default: board_num=0, port_low=12, port_high=13, active_high=False

**Files:**
- Transport: `src/element_tester/system/drivers/relay_mcc/transport.py`
- Commands: `src/element_tester/system/drivers/relay_mcc/commands.py`
- Procedures: `src/element_tester/system/drivers/relay_mcc/procedures.py`
- Driver: `src/element_tester/system/drivers/relay_mcc/driver.py`
- Errors: `src/element_tester/system/drivers/relay_mcc/errors.py`

---

### UT61E Multimeter (Uni-T)

**Hardware Connection:**
- **Interface**: USB HID (Human Interface Device) - NOT a COM port
- **Vendor ID**: 0x1a86 (WCH/QinHeng Electronics)
- **Product ID**: 0xe008 (common UT61E USB cable)
- **Chip**: Cyrustek ES51922 (22,000 count, true RMS)
- **Dependency**: `hidapi` package (`pip install hidapi`)

**Communication Protocol:**
- Meter continuously sends HID reports at ~2Hz
- Each HID report contains 14-byte ES51922 packet
- No commands sent to meter - we only listen
- Must extract ES51922 data from HID report wrapper
- Packets encode LCD display (7-segment, needs decoder for production)

**Usage:**
```python
from element_tester.system.drivers.meter_ut61e import UT61EDriver

# Initialize (auto-detects HID device)
meter = UT61EDriver(simulate=False)
meter.initialize()

# Read resistance (main method)
resistance = meter.read_resistance(average_count=5)

# List available devices
devices = UT61EDriver.list_devices()  # Returns VID/PID info

meter.shutdown()
```

**Testing:**
```bash
pip install hidapi
python test_ut61e.py --list  # Find device VID/PID
python test_ut61e.py --real  # Test with hardware
```

**Device Discovery (Windows):**
- Device Manager → "Human Interface Devices" (NOT "Ports (COM & LPT)")
- If device not accessible, may need Zadig tool to install WinUSB driver
- Download Zadig: https://zadig.akeo.ie/

**Important Notes:**
- Primary method: `read_resistance()` returns averaged samples
- Packet parsing is simplified (works in simulate mode)
- For production: integrate sigrok's es51922 decoder for full accuracy
- Current implementation validates transport layer and API

**Files:**
- Transport: `src/element_tester/system/drivers/meter_ut61e/transport.py`
- Commands: `src/element_tester/system/drivers/meter_ut61e/commands.py`
- Procedures: `src/element_tester/system/drivers/meter_ut61e/procedures.py`
- Driver: `src/element_tester/system/drivers/meter_ut61e/driver.py`
- Errors: `src/element_tester/system/drivers/meter_ut61e/errors.py`

---

### UT161E Auto Multimeter (Uni-T)

**Hardware Connection:**
- **Interface**: USB HID (Human Interface Device) - NOT a COM port
- **Vendor ID**: 0x1a86 (WCH/QinHeng Electronics)
- **Product ID**: 0xe429 (UT61E Plus / UT161E with WCH UART-to-KB/MS bridge)
- **Chip**: Cyrustek ES51922 (22,000 count)
- **Dependency**: `hidapi` package (`pip install hidapi`)

**Communication Protocol:**
- Meter continuously sends HID reports at ~2Hz
- Each HID report contains ES51922 packet data
- No commands sent to meter - we only listen
- **Key Difference from meter_ut61e**: Works WITHOUT requiring UT61E+ software running
- Direct HID communication extracts raw ES51922 packets
- Full 14-byte ES51922 packet parsing (not simplified ASCII)

**Protocol Details:**
- HID Report Structure:
  - Header bytes: Various wrapper bytes from HID layer
  - ES51922 Packet: 14 bytes of meter data
  - Packet Format:
    * [0]: Range byte (bits 6-3: 0110, bits 2-0: range)
    * [1-5]: Five digit bytes (7-segment encoded)
    * [6]: Mode byte (voltage, current, resistance, etc.)
    * [7-11]: Status flag bytes (AC/DC, auto, hold, etc.)
    * [12-13]: \r\n terminator
- Mode Byte Values:
  - 0x0B: Voltage (V/mV)
  - 0x03: Resistance (Ω)
  - 0x06: Capacitance (F)
  - 0x02: Frequency (Hz)
  - 0x0D: Current (µA)
  - 0x0F: Current (mA)
  - 0x00: Current (A)

**Usage:**
```python
from element_tester.system.drivers.meter_ut161_auto import UT61EAutoDriver

# Initialize (no software needed!)
meter = UT61EAutoDriver(vendor_id=0x1a86, product_id=0xe429, simulate=False)
meter.initialize()

# Read resistance with averaging
resistance = meter.read_resistance(average_count=5)

# Read any value with stability detection
reading = meter.wait_for_stable(timeout_s=10.0, stability_threshold=0.05)

# Advanced: Multi-sample averaging
reading = meter.read_averaged(sample_count=10, delay_s=0.3)

meter.shutdown()
```

**Testing:**
```bash
pip install hidapi
python test_ut61e_auto.py --simulate  # Test without hardware
python test_ut61e_auto.py --real      # Test with hardware
```

**Device Discovery (Windows):**
- Device Manager → "Human Interface Devices" (NOT "Ports (COM & LPT)")
- Look for "USB Input Device" with VID_1A86&PID_E429
- If not accessible, may need Zadig tool to install WinUSB driver
- Download Zadig: https://zadig.akeo.ie/

**Key Features:**
- **No Software Dependency**: Works without UT61E+ software (unlike meter_ut61e)
- **Full ES51922 Parsing**: Complete protocol implementation with all flags
- **Stability Detection**: `wait_for_stable()` waits for reading to stabilize
- **Statistical Averaging**: Returns mean and standard deviation
- **Auto Unit Conversion**: Automatically converts kΩ/MΩ to Ω
- **Comprehensive Error Handling**: Specific exceptions for timeout, parse errors

**Comparison to meter_ut61e:**
| Feature | meter_ut61e | meter_ut161_auto |
|---------|-------------|------------------|
| Software Required | YES (UT61E+) | NO ✓ |
| Protocol | Simplified ASCII | Full ES51922 Binary ✓ |
| Stability Detection | NO | YES ✓ |
| Multi-sample Stats | Basic | With σ ✓ |
| Production Ready | Development | YES ✓ |

**Important Notes:**
- Primary method: `read_resistance()` returns averaged samples in Ohms
- Stability detection useful for noisy/fluctuating readings
- Full ES51922 packet parsing provides access to all meter features
- Recommended for production use over meter_ut61e
- Meter must be manually set to resistance mode before reading

**Files:**
- Transport: `src/element_tester/system/drivers/meter_ut161_auto/transport.py`
- Commands: `src/element_tester/system/drivers/meter_ut161_auto/commands.py`
- Procedures: `src/element_tester/system/drivers/meter_ut161_auto/procedures.py`
- Driver: `src/element_tester/system/drivers/meter_ut161_auto/driver.py`
- Errors: `src/element_tester/system/drivers/meter_ut161_auto/errors.py`

---

## Development Patterns

### Simulate Mode
Always check for **simulate flag** in transport layers. Hardware failures → graceful degradation:
```python
# In transport.open() / close() / I/O methods:
if self.p.simulate or ul is None:
    print(f"SIM: {action}")
    return
```

### Configuration as Dataclass
Use `@dataclass` for connection/test parameters:
- `AR3865OpenParams`: resource, baud, timeout, simulate flag
- `HipotConfig`: voltage, current_trip, timing, polarity
- `ERB08OpenParams`: board_num, port, simulate, active_high

### Logging
Always inject `logger` into procedural classes:
```python
self.log = logger or logging.getLogger("element_tester.runner")
```
Prefix log calls with subsystem context (e.g., "HIPOT", "MEAS", "ERB08").

### Demo Mode
Special case: if `WO.lower() == "test"` and `PN.lower() == "test"`:
- Runs visual simulation without hardware
- Preset measurements: LP1to6=6, LP2to5=7, LP3to4=6, etc.
- Useful for UI testing and walkthroughs

---

## Important Conventions

### Import Path Management
- **SRC_ROOT adjustment** in `test_runner.py`: `Path(__file__).resolve().parents[3]`
- Ensures `element_tester` module is importable even from different entry points
- Check and maintain this when adding new entry points

### Result Logging
Results written to `data/results/`:
- **test_results.jsonl**: Structured records (one per line)
- **test_results.txt**: Human-readable format with timestamp, WO, PN, results
- Field names match: `LP1to6`, `LP2to5`, `LP3to4`, `RP1to6`, `RP2to5`, `RP3to4`

### Active-High Logic in Relays
- `ERB08Commands._logical_to_device_bit()` handles polarity
- When `active_high=False`, invert the bit logic before writing
- Always apply bits_off before bits_on in `cmd_set_many()`

### Optional Dependencies
- `pyvisa`, `pyserial`, `mcculw` are optional
- Code wraps imports with try/except and degrades to simulate mode
- Always test with missing imports for robustness

---

## Testing & Running

### Quick Start (Simulate Mode)
```powershell
cd $ProjectRoot
python -m pip install -r requirements.txt
$env:PYTHONPATH = "$PWD\src"
python -c "from element_tester.system.ui.scanning import ScanWindow; import sys; from PyQt6.QtWidgets import QApplication; app = QApplication(sys.argv); w = ScanWindow(); w.show(); sys.exit(app.exec())"
```

### Running Tests
- **Tests folder**: `tests/` (currently empty—add pytest here)
- **Debug dialog**: Import `DebugDialog` to add hardware test actions

### Results Inspection
```powershell
Get-Content .\data\results\test_results.txt -Tail 20
jq '.' .\data\results\test_results.jsonl
```

---

## Common Tasks

### Adding a New Hipot Test Parameter
1. Extend `HipotConfig` dataclass with new field (e.g., `fall_time_s`)
2. Add SCPI command in `AR3865Commands` (e.g., `cmd_set_fall_time()`)
3. Call from `cmd_apply_config()`
4. Update `AR3865Procedures.quick_run()` signature if user-facing

### Adding a Relay Mapping
```python
relay_procs = ERB08Procedures(board_num=0, port=0, simulate=True)
relay_procs.add_named_mapping("test_config", bits_on=[0, 2], bits_off=[1, 3, 4, 5, 6, 7])
relay_procs.ProcApplyNamedMapping("test_config")
```

### Debugging Hardware Communication
1. Enable logger at DEBUG level
2. Check simulate mode output (SIM: prefix in logs)
3. Use `DebugDialog` to test individual commands
4. Inspect `*IDN?` response (AR3865) or port read (ERB08)

---

## Non-Negotiable Conventions
- **Always preserve the 3-layer driver pattern**—do not mix transport and procedures
- **Use `@dataclass` for all configuration bundles**
- **Gracefully degrade to simulate mode** when hardware/imports unavailable
- **Log with context prefixes** (subsystem name + action)
- **Document SCPI commands** with inline comments in commands.py
- **Test results must include timestamp, WO, PN, and measurement values** in both formats

