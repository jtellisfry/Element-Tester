# ============================================================================
# element_tester.system.drivers Package
# ============================================================================
#
# Hardware driver packages following the Transport → Commands → Procedures
# three-layer architecture pattern.
#
# DRIVER PACKAGES:
# - relay_mcc/  : MCC USB-ERB08 relay board driver (mcculw)
# - hypot3865/  : AR 3865 Hipot tester driver (SCPI via VISA/serial)
#
# ARCHITECTURE (applies to ALL drivers):
# 1. transport.py  : Raw hardware I/O (VISA, serial, mcculw)
#                    - Handles simulate mode gracefully
#                    - No protocol logic, just read/write
# 2. commands.py   : Low-level protocol commands (SCPI, bit operations)
#                    - Small, focused "LEGO pieces"
#                    - No pass/fail decisions or sequences
# 3. procedures.py : Practical sequences combining commands
#                    - Session management (init, shutdown)
#                    - Configuration bundles
#                    - Pass/fail interpretation
# 4. driver.py     : Public façade (optional, recommended)
#                    - Single entry point for external code
#                    - Error handling and logging
#
# PURPOSE:
# - Consistent pattern across all instrument/hardware drivers
# - Easy to add new drivers following the same structure
# - Simulate mode support for development without hardware
#
# HOW TO ADD A NEW DRIVER:
# 1. Create new subfolder: drivers/new_instrument/
# 2. Add __init__.py with exports (see relay_mcc/__init__.py example)
# 3. Implement transport.py with simulate mode support
# 4. Implement commands.py with protocol-specific commands
# 5. Implement procedures.py with practical sequences
# 6. (Optional) Add driver.py façade for cleaner public API
# 7. Follow dataclass pattern for configuration (e.g., OpenParams)
# 8. Always inject logger for debugging
#
# HOW TO MODIFY:
# - Keep this file empty unless exposing common driver utilities
# - To export all drivers for convenience:
#     from .relay_mcc import ERB08Driver
#     from .hypot3865 import AR3865Procedures
#     __all__ = ["ERB08Driver", "AR3865Procedures"]
# ============================================================================
