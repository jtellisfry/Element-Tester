"""
=================
UNI-T UT61E Multimeter driver package
=================

This package implements a driver for the UNI-T UT61E multimeter using the
Cyrustek ES51922 chip protocol.

HARDWARE:
 - Multimeter: UNI-T UT61E (22,000 counts, true RMS)
 - Connection: RS-232 serial or USB-to-serial adapter
 - Protocol: Cyrustek ES51922 (19230 baud, 7o1, continuous TX)

PROTOCOL:
 - 19230 baud, 7 data bits, odd parity, 1 stop bit
 - Continuously transmits 14-byte packets
 - No commands needed - just read the stream

LAYERS:
 - transport  : serial I/O and packet reading (pyserial or simulate)
 - commands   : packet parsing and value extraction
 - procedures : measurement reading with timeout/retry logic
 - driver     : façade (single entry point)

USAGE:
    from element_tester.system.drivers.meter_ut61e import UT61EDriver
    
    # Real hardware
    meter = UT61EDriver(port='COM3', simulate=False)
    meter.initialize()
    
    # Read current displayed value (whatever mode meter is in)
    value, unit, mode = meter.read_value()
    print(f"Measurement: {value} {unit} ({mode})")
    
    # Simulate mode (no hardware)
    meter_sim = UT61EDriver(port='COM3', simulate=True)
    meter_sim.initialize()
    value, unit, mode = meter_sim.read_value()
"""

# Export public API
from .driver import UT61EDriver
from .transport import UT61EOpenParams
from .commands import MeterReading
from .errors import UT61EError

__all__ = [
    'UT61EDriver',
    'UT61EOpenParams',
    'MeterReading',
    'UT61EError',
]
