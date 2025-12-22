# =================
# ERB08 Errors
# =================
#
# Small module holding driver-specific exception types. Keeping a
# dedicated exception type allows callers to catch and handle driver
# failures distinctly from other exceptions.


class ERB08Error(Exception):
    """Base error for the MCC USB-ERB08 relay driver"""
    pass