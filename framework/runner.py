import importlib.util
import sys
from pathlib import Path

from .base_importer import BaseImporter
from .medplum_client import MedplumClient
from .exceptions import ImporterNotFoundError


def _to_class_name(config_type: str) -> str:
    """'epic-patients' → 'EpicPatientsImporter'"""
    return "".join(w.capitalize() for w in config_type.split("-")) + "Importer"


def _load_importer_class(config_type: str) -> type:
    path = Path("importers") / config_type / "importer.py"
    if not path.exists():
        raise ImporterNotFoundError(
            f"No importer found at {path}\n"
            f"Expected class: {_to_class_name(config_type)}"
        )
    spec = importlib.util.spec_from_file_location("importer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class_name = _to_class_name(config_type)
    if not hasattr(module, class_name):
        raise ImporterNotFoundError(
            f"Importer found at {path} but missing class '{class_name}'"
        )
    return getattr(module, class_name)


def _resolve_source(moniker: str):
    """
    Resolve a source moniker to a usable object.
    Currently: file path. Extend here for DB URLs, API endpoints, etc.
    """
    path = Path(moniker)
    if path.exists():
        return path
    raise ValueError(f"Cannot resolve source moniker: '{moniker}'")


def run(config_type: str, source_moniker: str) -> dict:
    print(f"[runner] config-type: {config_type}")
    print(f"[runner] source:      {source_moniker}")

    ImporterClass = _load_importer_class(config_type)
    source = _resolve_source(source_moniker)
    importer: BaseImporter = ImporterClass(source)

    print("[runner] step 1/5 — validate_source")
    importer.validate_source()

    print("[runner] step 2/5 — generate_bundle")
    bundle = importer.generate_bundle()

    print("[runner] step 3/5 — verify_bundle")
    importer.verify_bundle()

    print("[runner] step 4/5 — posting bundle to Medplum")
    client = MedplumClient()
    result = client.post_bundle(bundle)
    entry_count = len(result.get("entry", []))
    print(f"[runner] posted {entry_count} entries")

    print("[runner] step 5/5 — verify_import")
    importer._medplum = client
    importer.verify_import()

    print("[runner] done.")
    return result
