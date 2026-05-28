"""
Persistent job checkpoint store.

Tracks async import jobs in session/jobs.json so that if the process crashes
after posting a bundle, the job can be found and verified on restart.

Job states:
  posted    — bundle accepted by Medplum, AsyncJob running
  completed — Medplum finished processing the bundle
  verified  — verify_import() passed
  failed    — Medplum reported error, or verify_import() failed
"""
import json
from datetime import datetime, timezone
from pathlib import Path


CHECKPOINT_FILE = Path("session/jobs.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict]:
    if not CHECKPOINT_FILE.exists():
        return []
    return json.loads(CHECKPOINT_FILE.read_text())


def _save(jobs: list[dict]) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(jobs, indent=2))


def save_job(job_id: str, job_url: str, config_type: str, source_moniker: str) -> None:
    jobs = _load()
    jobs.append({
        "job_id": job_id,
        "job_url": job_url,
        "config_type": config_type,
        "source_moniker": source_moniker,
        "state": "posted",
        "created_at": _now(),
        "updated_at": _now(),
    })
    _save(jobs)


def update_state(job_id: str, state: str) -> None:
    jobs = _load()
    for job in jobs:
        if job["job_id"] == job_id:
            job["state"] = state
            job["updated_at"] = _now()
    _save(jobs)


def pending_jobs() -> list[dict]:
    """Jobs that were posted but not yet verified — candidates for resumption."""
    return [j for j in _load() if j["state"] in ("posted", "completed")]
