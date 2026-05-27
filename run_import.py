#!/usr/bin/env python3
"""
run_import.py <config-type> <input-moniker>

config-type    Identifies the importer. Must include the source system name,
               not just the resource type. Good: epic-patients, emr-x-labs.
               Bad: csv-patients (too generic — which system?).

               Convention: importers/<config-type>/importer.py
                           class <ConfigType>Importer(BaseImporter)

input-moniker  Source identifier: file path, database URL, API endpoint, etc.
               The importer's validate_source() decides how to open it.

Examples:
  python run_import.py epic-patients   data/export_2024_03.csv
  python run_import.py emr-x-labs      data/labs_march.csv
  python run_import.py athena-encounters postgresql://localhost/athena
"""
import sys
from framework.runner import run

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    config_type   = sys.argv[1]
    input_moniker = sys.argv[2]

    try:
        run(config_type, input_moniker)
    except Exception as e:
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
