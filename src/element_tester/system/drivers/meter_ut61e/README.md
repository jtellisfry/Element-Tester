# UT61E Multimeter Driver

HID-based driver for UNI-T UT61E digital multimeter (Cyrustek ES51922 chip).

## Quick Reference

**Connection:** USB HID (NOT COM port) - VID=0x1a86, PID=0xe008  
**Dependency:** `pip install hidapi`  
**Main Method:** `meter.read_resistance(average_count=5)`

## Basic Usage

```python
from element_tester.system.drivers.meter_ut61e import UT61EDriver

# Initialize (auto-detects HID device)
meter = UT61EDriver(simulate=False)
meter.initialize()

# Read resistance
resistance = meter.read_resistance(average_count=5)
print(f"{resistance} Ohms")

meter.shutdown()
```

## Testing

```bash
pip install hidapi
python test_ut61e.py --list  # Find device VID/PID
python test_ut61e.py --real  # Test with hardware
```

## Key Features

- ✅ HID communication via `hidapi`
- ✅ Automatic device detection (VID/PID)
- ✅ Multiple packet extraction strategies
- ✅ Simulate mode for testing
- ✅ Retry logic and error handling
- ✅ Multiple sample averaging
- ⚠️ Simplified packet parsing (7-segment decoder needed for production)

## Integration Example

```python
# In test_runner.py
from element_tester.system.drivers.meter_ut61e import UT61EDriver

class TestRunner:
    def __init__(self):
        self.meter = UT61EDriver(simulate=False)
        self.meter.initialize()
    
    def measure_resistance(self):
        self.relay_driver.set_relay(3, on=True)  # Connect meter
        time.sleep(0.2)
        resistance = self.meter.read_resistance(average_count=5)
        self.relay_driver.set_relay(3, on=False)  # Disconnect
        return resistance
```

## Implementation Status

**Transport Layer:** ✅ Complete (HID communication working)  
**Packet Parsing:** ⚠️ Simplified (extracts packets, parsing is placeholder)  
**For Production:** Integrate sigrok's es51922 decoder for full 7-segment decoding

## Device Setup

**Windows:** Device appears in Device Manager under "Human Interface Devices" (NOT Ports)  
**Driver:** Usually works automatically. If not, use [Zadig](https://zadig.akeo.ie/) to install WinUSB driver.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| hidapi not installed | `pip install hidapi` |
| Device not found | Run `python test_ut61e.py --list` to verify VID/PID |
| Can't open device | Close other programs, or use Zadig to install WinUSB driver (Windows) |
| Timeout errors | Check meter powered on, USB connected |

## Architecture

Follows Element Tester 3-layer pattern:
- **transport.py** - HID I/O and packet extraction
- **commands.py** - Packet parsing (simplified)
- **procedures.py** - Session management, averaging, retries
- **driver.py** - Public API

## References

See `.github/copilot-instructions.md` for detailed protocol information and integration guidelines.
