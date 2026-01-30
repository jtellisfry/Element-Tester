"""
AR 3865 Hipot driver package.

Layers:
- transport: VISA/Serial I/O (no SCPI decisions)
- procedures: single-purpose SCPI steps (configure, start, read result, etc.)
- commands: practical sequences combining procedures (init, config-and-run, abort, discharge, etc.)
"""
__all__ = ["transport", "procedures", "commands"]
