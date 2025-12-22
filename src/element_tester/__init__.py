# ============================================================================
# element_tester Package
# ============================================================================
#
# This is the ROOT package marker for the entire Element Tester application.
# Python requires this file to recognize `element_tester` as an importable
# package.
#
# PURPOSE:
# - Marks the `src/element_tester/` directory as a Python package
# - Allows imports like: `from element_tester.system.drivers.relay_mcc import ERB08Driver`
# - Enables relative imports within the package hierarchy
#
# STRUCTURE:
# - Empty by design (can optionally export top-level constants/version)
# - All functional code lives in subpackages: system.drivers, system.ui, etc.
#
# HOW TO MODIFY:
# - Keep this file minimal (empty or version/metadata only)
# - To expose top-level exports, add imports like:
#     from .system.drivers.relay_mcc import ERB08Driver
#     __version__ = "1.0.0"
# - Never add business logic here—use subpackages instead
#
# DEPENDENCIES:
# - Requires: All subdirectories (system/, programs/) also have __init__.py
# - Requires: Parent directory (src/) must be in PYTHONPATH (see .env files)
# ============================================================================
