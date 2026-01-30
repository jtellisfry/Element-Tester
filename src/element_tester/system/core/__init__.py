# ============================================================================
# element_tester.system.core Package
# ============================================================================
#
# Core orchestration and runtime logic for the Element Tester application.
#
# MODULES:
# - test_runner.py : Top-level test sequencer (Hipot + Measurement)
#                    - Manages driver lifecycle (init, run, shutdown)
#                    - Handles simulate mode decision logic
#                    - Writes results to data/results/
#
# PURPOSE:
# - Separates high-level test orchestration from UI and drivers
# - Single source of truth for test sequences
# - Coordinate multiple drivers (relay, hipot, measurement)
#
# HOW TO MODIFY:
# - Add new test sequences as methods in TestRunner
# - Add new configuration files (JSON/YAML) in data/ or config/
# - To expose core classes:
#     from .test_runner import TestRunner
#     __all__ = ["TestRunner"]
# - Keep core logic UI-agnostic (use callbacks/signals for UI updates)
# ============================================================================
