# ============================================================================
# element_tester.system.commands Package
# ============================================================================
#
# High-level command abstractions (placeholder for future development).
#
# PURPOSE:
# - Provide application-level commands that orchestrate multiple drivers
# - Example: "PrepareForTest" command that configures relays + hipot + measurement
# - Sits between UI/core and drivers for complex multi-step operations
#
# INTENDED STRUCTURE:
# - base.py        : Base Command class (pattern)
# - test_commands.py : Test-specific commands
# - util_commands.py : Utility commands (diagnostics, calibration)
#
# HOW TO IMPLEMENT:
# - Use Command pattern: each command is a class with execute() method
# - Commands should be reusable and testable
# - Import from element_tester.system.drivers for hardware access
# - Keep commands stateless where possible
#
# HOW TO MODIFY:
# - Add command modules as needed
# - Export commands for easy import:
#     from .test_commands import PrepareForTestCommand
#     __all__ = ["PrepareForTestCommand"]
# ============================================================================
