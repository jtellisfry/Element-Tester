"""
UT61E Automatic Driver (Direct Serial Communication)
=====================================================

Direct serial communication with UT61E multimeter using Cyrustek ES51922 protocol.
No external software required - reads directly from RS-232 serial port.

This driver implements the standard 3-layer architecture:
- Transport: Serial I/O with ES51922 chip
- Commands: 14-byte packet parsing
- Procedures: Multi-sample reading and averaging
- Driver: Public API façade
"""
from .driver import UT61EAutoDriver
from .errors import UT61EAutoError, UT61EAutoTimeoutError

__all__ = ['UT61EAutoDriver', 'UT61EAutoError', 'UT61EAutoTimeoutError']
