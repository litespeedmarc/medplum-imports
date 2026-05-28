import importlib.util
import sys
from pathlib import Path

# Load the importer the same way the runner does — works regardless of directory naming.
_spec = importlib.util.spec_from_file_location(
    "emr_x_patients_importer",
    Path(__file__).parent.parent / "importer.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sys.modules["emr_x_patients_importer"] = _mod
