# ============================================================================
# element_tester.programs Package
# ============================================================================
#
# Container for standalone test programs and application entry points.
#
# SUBDIRECTORIES:
# - hipot_test/       : (Future) Standalone hipot test program
# - measurement_test/ : (Future) Standalone measurement test program
#
# PURPOSE:
# - Separates application entry points from system infrastructure
# - programs/ contains runnable scripts/apps
# - system/ contains reusable components (drivers, UI, core logic)
#
# TYPICAL STRUCTURE FOR PROGRAMS:
# Each program subfolder should contain:
# - __main__.py : Entry point (python -m element_tester.programs.hipot_test)
# - config.json : Program-specific configuration
# - README.md   : Program documentation
#
# HOW TO MODIFY:
# - Add new program: create subfolder + __init__.py + __main__.py
# - Keep programs loosely coupled—import from system/ but not from other programs/
# - To expose program entry points:
#     from .hipot_test import main as hipot_main
#     __all__ = ["hipot_main"]
# ============================================================================
