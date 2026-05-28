#!/usr/bin/env python3
"""
run_import.py <config-type> <input-moniker> [--mode dev|prod]

config-type    Identifies the importer. Must include the source system name.
               Convention: importers/<config-type>/importer.py
                           class <ConfigType>Importer(BaseImporter)

input-moniker  Source identifier: file path, database URL, API endpoint, etc.

--mode         dev  (default) — strict, CleanableDataWarning raises immediately
               prod           — cleanable rows normalize+warn, uncleanable rows
                                go to exceptions report, import continues

Examples:
  python run_import.py emr-x-patients data/export.csv
  python run_import.py emr-x-patients data/export.csv --mode prod
"""
import sys
from framework.runner import run
from framework.base_importer import ImportMode

if __name__ == "__main__":
    args = sys.argv[1:]
    mode = ImportMode.DEV

    if "--mode" in args:
        idx = args.index("--mode")
        mode = ImportMode(args[idx + 1])
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    if len(args) != 2:
        print(__doc__)
        sys.exit(1)

    config_type, input_moniker = args

    try:
        run(config_type, input_moniker, mode=mode)
    except Exception as e:
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
