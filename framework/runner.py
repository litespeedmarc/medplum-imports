# KISS: synchronous post — Medplum holds the connection open until processing is done.
# This is the right default for a demo/CLI import tool running one job at a time.
#
# YAGNI: async + webhook is a real upgrade path but not needed until we have:
#   - bundles large enough to hit HTTP timeouts (Medplum default: 60s)
#   - concurrent imports that would benefit from fan-out
#
# When that day comes, the full event-driven path looks like this:
#
#   runner (main thread)              webhook thread         Medplum
#   ──────────────────────────        ──────────────         ──────────────────
#   POST Subscription{rest-hook}
#     endpoint: host.docker.internal:{port}/webhook
#     criteria: AsyncJob?status=completed
#   post_bundle(Prefer:respond-async) → 202 + job_url
#   save_job(job_id)  ← crash resilience
#   Event.wait(timeout=300) ────────→ serve_forever()
#     (main thread suspended)                         processes bundle
#                                   ←─ POST /webhook ──────────────
#                                   Event.set()
#   ← unblocks
#   DELETE Subscription
#   verify_import()
#
#   MedplumClient already has post_bundle_async() / get_job_status() / wait_for_job()
#   if you want to wire this up. checkpoint.py has the job persistence layer.

import importlib.util
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

    print("[runner] step 1/4 — validate_source")
    importer.validate_source()

    print("[runner] step 2/4 — generate_bundle")
    bundle = importer.generate_bundle()

    print("[runner] step 3/4 — verify_bundle")
    importer.verify_bundle()

    client = MedplumClient()
    importer._medplum = client

    entry_count = len(bundle.get("entry", []))
    print(f"[runner] step 4/4 — post + verify ({entry_count} entries)")
    result = client.post_bundle(bundle)
    _log_batch_result(result, importer.bundle_type())

    importer.verify_import()

    print("[runner] done.")
    return result


def _log_batch_result(response: dict, bundle_type: str) -> None:
    entries = response.get("entry", [])
    if bundle_type != "batch":
        print(f"[runner] {len(entries)} entries committed (transaction)")
        return

    ok = sum(1 for e in entries if e.get("response", {}).get("status", "").startswith("2"))
    failed = [(i, e) for i, e in enumerate(entries)
              if not e.get("response", {}).get("status", "").startswith("2")]

    print(f"[runner] batch: {ok} ok, {len(failed)} failed")
    for i, entry in failed:
        issues = entry.get("response", {}).get("outcome", {}).get("issue", [{}])
        print(f"[runner]   entry {i}: {issues[0].get('diagnostics', 'unknown')}")
