# UT61E Auto Driver - Direct Serial Communication

Direct serial communication driver for UNI-T UT61E multimeter using Cyrustek ES51922 protocol. **No external software required** - communicates directly via RS-232 serial port.

## Features

- **Direct Serial Communication**: No UT61E+ software needed
- **Standard ES51922 Protocol**: Based on Cyrustek ES51922 datasheet
- **Full 3-Layer Architecture**: Transport → Commands → Procedures → Driver
- **Automatic Averaging**: Multi-sample reading with statistical analysis
- **Stability Detection**: Wait for readings to stabilize within threshold
- **Simulate Mode**: Test without hardware
- **Comprehensive Error Handling**: Timeout, parse, and connection errors

## Hardware Requirements

- **Multimeter**: UNI-T UT61E with RS-232 IR cable
- **Cable**: USB-to-RS232 adapter with WCH CH340/CH341 chip
- **Connection**: Typically COM1-COM9 (Windows) or /dev/ttyUSB0 (Linux)
- **Protocol**: 19200 baud, 7 data bits, odd parity, 1 stop bit

## Installation

```bash
pip install pyserial
```

## Quick Start

```python
from element_tester.system.drivers.meter_ut161_auto import UT61EAutoDriver

# Initialize
meter = UT61EAutoDriver(port='COM1', simulate=False)
meter.initialize()

# Read resistance (meter must be in resistance mode)
resistance = meter.read_resistance(average_count=5)
print(f"Resistance: {resistance:.2f} Ω")

# Cleanup
meter.shutdown()
```

## API Reference

### Initialization

```python
meter = UT61EAutoDriver(
    port='COM1',           # Serial port name
    simulate=False,        # Enable simulate mode
    timeout_s=2.0,        # Read timeout
    logger=None           # Optional logger
)
```

### Core Methods

#### `initialize()`
Open connection to meter. Must be called before reading.

#### `shutdown()`
Close connection to meter. Should always be called when done.

#### `read_value(max_retries=3) -> MeterReading`
Read current displayed value (any mode).

Returns `MeterReading` with:
- `value`: Numeric reading (or None if overload)
- `unit`: Measurement unit (Ohm, V, A, F, Hz, etc.)
- `mode`: Measurement mode
- `is_overload`: True if OL displayed
- `is_negative`: True if negative value
- `flags`: Dict of status flags

#### `read_resistance(average_count=5) -> float`
Read resistance value in Ohms. Meter must be in resistance mode.

#### `read_averaged(sample_count=5, delay_s=0.5) -> MeterReading`
Read multiple samples and return averaged result.

#### `wait_for_stable(timeout_s=10.0, stability_threshold=0.05) -> MeterReading`
Wait for reading to stabilize within threshold (default 5% variation).

### Utility Methods

#### `list_serial_ports() -> list` (static)
List available serial ports on system.

#### `get_port_info() -> dict`
Get connection status and settings.

## Protocol Details

### ES51922 Packet Format (14 bytes)

```
[0]:    Range byte (bits 6-3: 0110, bits 2-0: range)
[1-5]:  Digit bytes (bits 6-4: 011, bits 3-0: digit 0-9)
[6]:    Mode byte (voltage, current, resistance, etc.)
[7]:    Info flags (percent, minus, low battery, overload)
[8]:    Relative mode flags
[9]:    Limit flags
[10]:   Voltage/AC/DC/Auto flags
[11]:   Hold flags
[12-13]: \r\n terminator
```

### Serial Settings

- **Baud Rate**: 19200 (fixed by ES51922)
- **Data Bits**: 7
- **Parity**: Odd
- **Stop Bits**: 1
- **Flow Control**: DTR=1, RTS=0 (required by IR cable)

### Measurement Modes

The meter continuously transmits packets encoding the LCD display. Mode byte determines measurement type:

- `0x0B`: Voltage (V/mV)
- `0x03`: Resistance (Ω)
- `0x06`: Capacitance (F)
- `0x02`: Frequency (Hz)
- `0x0D`: Current (µA)
- `0x0F`: Current (mA)
- `0x00`: Current (A)

## Usage Examples

### Basic Resistance Reading

```python
meter = UT61EAutoDriver(port='COM1')
meter.initialize()

try:
    # Read with averaging
    resistance = meter.read_resistance(average_count=10)
    print(f"Resistance: {resistance:.2f} Ω")
finally:
    meter.shutdown()
```

### Wait for Stable Reading

```python
meter = UT61EAutoDriver(port='COM1')
meter.initialize()

try:
    # Wait for reading to stabilize within 2%
    reading = meter.wait_for_stable(timeout_s=15.0, stability_threshold=0.02)
    print(f"Stable: {reading.value} {reading.unit}")
finally:
    meter.shutdown()
```

### Read Any Value

```python
meter = UT61EAutoDriver(port='COM1')
meter.initialize()

try:
    # Read whatever is displayed (voltage, current, etc.)
    reading = meter.read_value()
    print(f"{reading.value} {reading.unit}")
    print(f"Mode: {reading.mode}")
    print(f"Flags: {reading.flags}")
finally:
    meter.shutdown()
```

### Find Serial Ports

```python
ports = UT61EAutoDriver.list_serial_ports()
print(f"Available ports: {ports}")
```

### Simulate Mode

```python
# Test without hardware
meter = UT61EAutoDriver(port='COM1', simulate=True)
meter.initialize()

resistance = meter.read_resistance()  # Returns simulated ~100-150Ω
print(f"Simulated: {resistance:.2f} Ω")

meter.shutdown()
```

## Integration with Element Tester

```python
from element_tester.system.drivers.meter_ut161_auto import UT61EAutoDriver

def measure_element_resistance(relay_board, pin_config):
    """Measure resistance of element using relay board and meter."""
    meter = UT61EAutoDriver(port='COM1')
    meter.initialize()
    
    try:
        # Configure relay board for measurement
        relay_board.apply_mapping(pin_config)
        
        # Wait for reading to stabilize
        reading = meter.wait_for_stable(timeout_s=10.0, stability_threshold=0.03)
        
        # Convert to Ohms if needed
        resistance = reading.value
        if 'kohm' in reading.unit.lower():
            resistance *= 1000
        elif 'mohm' in reading.unit.lower():
            resistance *= 1_000_000
        
        return resistance
        
    finally:
        meter.shutdown()
```

## Comparison: meter_ut61e vs meter_ut161_auto

| Feature | meter_ut61e (HID) | meter_ut161_auto (Serial) |
|---------|------------------|---------------------------|
| **Interface** | HID (USB) | RS-232 Serial |
| **Software Required** | UT61E+ must be running | None |
| **Connection** | VID=0x1a86, PID=0xe429 | COM port |
| **Dependency** | hidapi | pyserial |
| **Setup Complexity** | High (software bridge) | Low (direct) |
| **Reliability** | Depends on software | Direct communication |
| **Recommended** | Development/testing | Production |

## Troubleshooting

### Cannot Find Serial Port

```python
# List available ports
ports = UT61EAutoDriver.list_serial_ports()
print(ports)
```

**Windows**: Check Device Manager → Ports (COM & LPT)  
**Linux**: Check `/dev/ttyUSB*` or `/dev/ttyACM*`

### Permission Denied (Linux)

Add user to dialout group:
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Timeout Errors

- Check cable connection
- Verify meter is powered on
- Try increasing timeout: `UT61EAutoDriver(timeout_s=5.0)`
- Check correct COM port selected

### CH340 Driver Issues (Windows)

Download and install CH340 driver from manufacturer or Windows Update.

### Wrong Readings

- Ensure meter is in correct mode (resistance, voltage, etc.)
- Check cable polarity (IR sensor alignment)
- Try different sample count: `read_resistance(average_count=10)`

## Architecture

Follows Element Tester 3-layer driver pattern:

```
driver.py       → Public API façade
    ↓
procedures.py   → High-level operations (averaging, stability)
    ↓
commands.py     → Packet parsing (ES51922 protocol)
    ↓
transport.py    → Serial I/O layer
```

Each layer has clear responsibilities:
- **Transport**: Raw serial read/write
- **Commands**: Parse 14-byte packets into readings
- **Procedures**: Multi-sample averaging, stability detection
- **Driver**: Clean public API with error handling

## Files

- `__init__.py` - Package exports
- `errors.py` - Exception classes
- `transport.py` - Serial I/O layer
- `commands.py` - ES51922 packet parsing
- `procedures.py` - High-level operations
- `driver.py` - Public API
- `QUICK_REFERENCE.py` - Usage examples
- `README.md` - This file

## References

- [Cyrustek ES51922 Datasheet](http://www.cyrustek.com.tw/spec/ES51922.pdf)
- [Sigrok: Multimeter ICs](https://sigrok.org/wiki/Multimeter_ICs)
- [UT61E Protocol Documentation](https://github.com/4x1md/ut61e_py)
- [Element Tester Project](../../../../../../)

## License

Part of Element Tester project. See project LICENSE file.
