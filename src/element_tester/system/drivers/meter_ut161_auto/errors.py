"""
UT61E Auto Driver Errors
========================

Exception classes for UT61E automatic driver (direct serial).
"""


class UT61EAutoError(Exception):
    """Base exception for UT61E auto driver errors"""
    pass


class UT61EAutoTimeoutError(UT61EAutoError):
    """Raised when timeout occurs reading from meter"""
    pass


class UT61EAutoParseError(UT61EAutoError):
    """Raised when packet parsing fails"""
    pass


class UT61EAutoConnectionError(UT61EAutoError):
    """Raised when serial port connection fails"""
    pass
