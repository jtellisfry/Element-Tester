"""
=================
MCC USB-ERB08 driver package
=================

This package implements a small, layered driver for MCC USB-ERB08-style
relay hardware using a DUAL-PORT architecture.

HARDWARE CONFIGURATION:
 - Relays 0-3: Port 12 (FIRSTPORTA), bits 0-3
 - Relays 4-7: Port 13 (FIRSTPORTB), bits 0-3
 
LAYERS:
 - transport  : raw board+port I/O with relay-to-port mapping (mcculw or simulate)
 - commands   : low-level relay operations (automatically maps relay 0-7 to correct port)
 - procedures : higher-level flows (all off, apply mapping, self-test, etc.)
 - driver     : façade (single entry point), Hypot-style

USAGE:
    from element_tester.system.drivers.relay_mcc import ERB08Driver
    
    # Real hardware (ports 12 and 13)
    drv = ERB08Driver(board_num=0, port_low=12, port_high=13, simulate=False)
    drv.initialize()
    drv.set_relay(0, True)   # Port 12, bit 0
    drv.set_relay(4, True)   # Port 13, bit 0
    drv.shutdown()
    
    # Simulate mode (no hardware)
    drv = ERB08Driver(board_num=0, port_low=12, port_high=13, simulate=True)
"""

from .transport import ERB08OpenParams, ERB08Transport
from .commands import ERB08Commands
from .procedures import ERB08Procedures, RelayMapping
from .driver import ERB08Driver
from .errors import ERB08Error

__all__ = [
    "ERB08OpenParams",
    "ERB08Transport",
    "ERB08Commands",
    "ERB08Procedures",
    "RelayMapping",
    "ERB08Driver",
    "ERB08Error",
]
