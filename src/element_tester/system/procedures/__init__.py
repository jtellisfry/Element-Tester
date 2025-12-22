# ============================================================================
# element_tester.system.procedures Package
# ============================================================================
#
# Test procedure definitions (placeholder for future development).
#
# PURPOSE:
# - Define reusable test procedures as data/config (not code)
# - Example: JSON/YAML files describing test steps, parameters, limits
# - Separates test logic from code for easier maintenance
#
# INTENDED STRUCTURE:
# - loader.py           : Procedure file parser (JSON/YAML)
# - validator.py        : Procedure validation logic
# - executor.py         : Procedure execution engine
# - definitions/        : Directory of procedure definition files
#
# EXAMPLE PROCEDURE FILE (JSON):
# {
#   "name": "Standard Hipot Test",
#   "steps": [
#     {"action": "configure_relays", "mapping": "standard"},
#     {"action": "run_hipot", "voltage": 1500, "current_trip": 0.5},
#     {"action": "measure_resistance", "expected_range": [5, 8]}
#   ],
#   "pass_criteria": {"hipot": "pass", "resistance": "in_range"}
# }
#
# HOW TO IMPLEMENT:
# - Create procedure schema (JSON Schema or Python dataclass)
# - Build loader to read procedure files from data/procedures/
# - Implement executor that calls system.core.TestRunner methods
# - Add validation to ensure procedures are well-formed
#
# HOW TO MODIFY:
# - Add procedure types as needed (hipot, measurement, calibration)
# - Export loader/executor:
#     from .loader import ProcedureLoader
#     from .executor import ProcedureExecutor
#     __all__ = ["ProcedureLoader", "ProcedureExecutor"]
# ============================================================================
