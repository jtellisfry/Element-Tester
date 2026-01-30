# ============================================================================
# element_tester.system Package
# ============================================================================
#
# This package contains the core system components for the Element Tester:
# - drivers/    : Hardware drivers (relay_mcc, hypot3865)
# - ui/         : PyQt6 user interface modules (scanning, testing, debug)
# - core/       : Test orchestration (test_runner)
# - commands/   : (Future) High-level command abstractions
# - procedures/ : (Future) Test procedure definitions
# - widgets/    : (Future) Reusable UI components
#
# PURPOSE:
# - Organizes system-level functionality separate from programs/
# - Marks system/ as an importable subpackage
#
# HOW TO MODIFY:
# - Keep empty unless you want to expose common system-level utilities
# - To add new subpackage: create new folder + __init__.py, no changes needed here
# - To export commonly used items:
#     from .drivers.relay_mcc import ERB08Driver
#     from .core.test_runner import TestRunner
#     __all__ = ["ERB08Driver", "TestRunner"]
# ============================================================================
