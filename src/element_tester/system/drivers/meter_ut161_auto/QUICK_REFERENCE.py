"""
UT61E Auto Driver Quick Reference
==================================

Direct serial communication with UT61E without requiring UT61E+ software.

SETUP
-----
Hardware: UT61E multimeter with RS-232 IR cable
Port: Typically COM1-COM9 on Windows, /dev/ttyUSB0 on Linux
Protocol: 19200 baud, 7 data bits, odd parity, 1 stop bit
Required: pyserial (pip install pyserial)

BASIC USAGE
-----------
from element_tester.system.drivers.meter_ut161_auto import UT61EAutoDriver

# Initialize
meter = UT61EAutoDriver(port='COM1', simulate=False)
meter.initialize()

# Read resistance (meter must be in resistance mode)
resistance_ohms = meter.read_resistance(average_count=5)
print(f"Resistance: {resistance_ohms:.2f} Ω")

# Read any value
reading = meter.read_value()
print(f"{reading.value} {reading.unit} ({reading.mode})")

# Cleanup
meter.shutdown()

ADVANCED USAGE
--------------
# Averaged reading with custom sample count
reading = meter.read_averaged(sample_count=10, delay_s=0.3)

# Wait for stable reading
stable_reading = meter.wait_for_stable(timeout_s=15.0, stability_threshold=0.02)

# List available serial ports
ports = UT61EAutoDriver.list_serial_ports()
print(f"Available ports: {ports}")

# Get connection info
info = meter.get_port_info()
print(f"Connected to {info['port']} at {info['baud_rate']} baud")

SIMULATE MODE
-------------
# Test without hardware
meter = UT61EAutoDriver(port='COM1', simulate=True)
meter.initialize()
resistance = meter.read_resistance()  # Returns simulated value ~100-150Ω

PROTOCOL NOTES
--------------
- Meter continuously transmits 14-byte packets at ~2Hz
- No commands sent to meter (read-only communication)
- Packets encode 7-segment LCD display
- Format: [range][5 digits][mode][flags][\\r\\n]
- DTR must be high, RTS must be low for IR cable

METER MODES
-----------
The meter must be manually set to the desired mode:
- Resistance: Ω button
- DC Voltage: V button (DC mode)
- AC Voltage: V button (AC mode)
- DC Current: A button (DC mode)
- AC Current: A button (AC mode)
- Capacitance: Hz/°C button (hold for capacitance)
- Frequency: Hz/°C button

TYPICAL INTEGRATION
-------------------
# In test_runner.py or measurement procedures
from element_tester.system.drivers.meter_ut161_auto import UT61EAutoDriver

meter = UT61EAutoDriver(port='COM1')
meter.initialize()

try:
    # Set element to test configuration with relays
    relay_board.apply_mapping(pin_config)
    
    # Wait for reading to stabilize
    reading = meter.wait_for_stable(timeout_s=10.0)
    
    # Get resistance value
    resistance = reading.value
    if reading.unit.lower() == 'kohm':
        resistance *= 1000
    elif reading.unit.lower() == 'mohm':
        resistance *= 1_000_000
    
    print(f"Measured: {resistance:.2f} Ω")
    
finally:
    meter.shutdown()

COMPARISON TO meter_ut61e
-------------------------
meter_ut61e (HID):
  - Requires UT61E+ software running
  - Uses HID interface (VID=0x1a86, PID=0xe429)
  - Software acts as bridge to send data
  - More complex setup

meter_ut161_auto (Direct Serial):
  - Direct communication, no software required
  - Uses RS-232 serial port
  - Simpler, more reliable
  - Standard Cyrustek ES51922 protocol
  - Recommended for production use

TROUBLESHOOTING
---------------
1. Check port name: Use list_serial_ports() to find correct COM port
2. Check cable: IR cable must have WCH CH340/CH341 chip
3. Check driver: Windows may need CH340 driver installed
4. Check meter: Ensure meter is powered on and in desired mode
5. Check permissions: Linux may need user in 'dialout' group
6. Check baud: Always 19200 for UT61E (hardcoded in driver)

ERROR HANDLING
--------------
try:
    resistance = meter.read_resistance()
except UT61EAutoTimeoutError:
    print("Timeout - check meter connection")
except UT61EAutoError as e:
    print(f"Error: {e}")

FILES
-----
__init__.py    - Package exports
errors.py      - Exception classes
transport.py   - Serial I/O layer
commands.py    - Packet parsing (ES51922 protocol)
procedures.py  - High-level operations (averaging, stability)
driver.py      - Public API façade
QUICK_REFERENCE.py - This file
"""
