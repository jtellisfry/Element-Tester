"""
UT61E-specific exceptions
"""


class UT61EError(Exception):
    """Base exception for all UT61E driver errors"""
    pass


class UT61ETimeoutError(UT61EError):
    """Raised when reading times out"""
    pass


class UT61EPacketError(UT61EError):
    """Raised when packet parsing fails"""
    pass
