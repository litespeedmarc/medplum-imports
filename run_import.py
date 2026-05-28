#!/usr/bin/env python3
"""
run_import.py <config-type> <input-moniker>

config-type    Identifies the importer. Must include the source system name.
               Convention: importers/<config-type>/importer.py
                           class <ConfigType>Importer(BaseImporter)

input-moniker  Source identifier: file path, database URL, API endpoint, etc.

Examples:
  python run_import.py emr-x-patients data/export.csv
  python run_import.py epic-labs      data/labs_march.csv
"""
import sys
from framework.runner import run

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    config_type, input_moniker = sys.argv[1], sys.argv[2]

    try:
        run(config_type, input_moniker)
    except Exception as e:
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
