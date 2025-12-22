"""
UT61E Multimeter Driver - Quick Reference

BASIC USAGE
===========

from element_tester.system.drivers.meter_ut61e import UT61EDriver

# Initialize
meter = UT61EDriver(port='COM3', simulate=False)
meter.initialize()

# Read resistance (MAIN METHOD for element tester)
resistance = meter.read_resistance(average_count=5)
print(f"{resistance} Ohms")

# Cleanup
meter.shutdown()


SIMULATE MODE (Testing without hardware)
========================================

meter = UT61EDriver(port='COM3', simulate=True)
meter.initialize()
resistance = meter.read_resistance()  # Returns simulated values
meter.shutdown()


ERROR HANDLING
==============

from element_tester.system.drivers.meter_ut61e import (
    UT61EDriver, UT61EError, UT61ETimeoutError
)

try:
    meter = UT61EDriver(port='COM3')
    meter.initialize()
    resistance = meter.read_resistance()
    
except UT61ETimeoutError:
    print("Timeout - check connection")
except UT61EError as e:
    print(f"Error: {e}")
finally:
    meter.shutdown()


CONFIGURATION OPTIONS
=====================

UT61EDriver(
    port='COM3',              # COM port (required)
    baudrate=19230,           # Fixed for ES51922 (don't change)
    simulate=False,           # True for testing without hardware
    timeout_ms=2000,          # Read timeout (milliseconds)
    logger=None              # Optional logging.Logger instance
)


API METHODS
===========

# Session Management
meter.initialize()           # Open connection
meter.shutdown()             # Close connection

# Reading Methods
resistance = meter.read_resistance(average_count=3)  # Read resistance (main method)
reading = meter.read_value()                         # Read any displayed value
readings = meter.read_multiple(count=5)              # Read multiple samples

# Utility
connected = meter.is_connected()     # Check connection health
last = meter.get_last_reading()      # Get cached last reading


READING OBJECT
==============

reading = meter.read_value()

reading.value          # Numeric value (float or None)
reading.unit           # Unit string (e.g., 'Ohm', 'V', 'A')
reading.mode           # Mode string (e.g., 'Resistance', 'DC Voltage')
reading.is_overload    # True if overload (OL) displayed
reading.is_negative    # True if negative value
reading.flags          # Dict of status flags
reading.raw_packet     # Original 14-byte packet


INTEGRATION EXAMPLE (test_runner.py)
=====================================

from element_tester.system.drivers.meter_ut61e import UT61EDriver

class TestRunner:
    def __init__(self, ...):
        self.meter = UT61EDriver(port='COM3', simulate=False)
        self.meter.initialize()
    
    def measure_resistance(self, test_point):
        # 1. Connect meter via relay
        self.relay_driver.set_relay(3, on=True)
        time.sleep(0.2)  # Settling
        
        # 2. Read resistance
        resistance = self.meter.read_resistance(average_count=5)
        
        # 3. Check limits
        if resistance is not None:
            passed = 5.5 <= resistance <= 6.5
            return resistance, passed
        else:
            return None, False
        
        # 4. Disconnect
        self.relay_driver.set_relay(3, on=False)


HARDWARE SETUP
==============

1. Connect UT61E to computer via RS-232 or USB-to-serial cable
2. Identify COM port:
   - Windows: Device Manager → Ports (COM & LPT)
   - Linux: dmesg | grep tty
3. Set meter to resistance (Ohm) mode
4. Connect test leads to test points via relay


TROUBLESHOOTING
===============

"pyserial not installed"
→ pip install pyserial

"Failed to read valid packet"
→ Check COM port, cable, meter powered on

"No valid resistance readings"
→ Ensure meter is in resistance mode

"Timeout reading from UT61E"
→ Verify 19230 baud, 7o1 settings
→ Test cable with terminal (PuTTY, etc.)


PROTOCOL SPECS
==============

Interface: RS-232 Serial
Baud:      19230 (fixed by ES51922 chip)
Data:      7 bits
Parity:    Odd
Stop:      1 bit
Flow:      None

Packets:   14 bytes, continuous TX at ~2Hz
Commands:  None (read-only, meter transmits continuously)


CURRENT STATUS
==============

✅ Transport layer (serial I/O)
✅ Session management
✅ Retry logic
✅ Averaging
✅ Simulate mode
⚠️ Packet parsing (simplified - works in simulate mode)

For production with real hardware, packet parser may need enhancement.
See METER_UT61E_IMPLEMENTATION.md for details.
"""
