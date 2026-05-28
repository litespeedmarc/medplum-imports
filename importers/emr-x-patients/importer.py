import csv
from datetime import datetime
from pathlib import Path

from framework import BaseImporter, MedplumClient
from framework.exceptions import SourceValidationError, BundleValidationError, ImportVerificationError

REQUIRED_COLUMNS = {"patient_id", "first_name", "last_name", "dob", "gender"}

GENDER_MAP = {"M": "male", "F": "female", "O": "other", "U": "unknown", "X": "unknown"}

SYSTEM_MRN = "http://emr-x.example.org/patient-id"

PLACEHOLDER_IDS = {"", "unknown", "000-000-000"}


class EmrXPatientsImporter(BaseImporter):
    """
    Imports Patient resources from EMR-X CSV exports.

    Source: EMR-X nightly patient extract.
    Target FHIR resource: Patient

    Data fidelity notes:
    - patient_id maps to identifier (system: SYSTEM_MRN) — never discarded
    - Null/placeholder patient_id → _reject() (untrackable resource)
    - Dates validated strictly; ambiguous format → _reject() (field context: birthDate)
    - Unknown gender code → _warn(), mapped to 'unknown'
    - Missing first_name or last_name → _warn(), field omitted
    - Empty optional fields omitted from bundle (not nulled)
    """

    def validate_source(self) -> None:
        if not Path(self.source).exists():
            raise SourceValidationError(f"File not found: {self.source}")

        with open(self.source, newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise SourceValidationError("File is empty or has no header row")
            missing = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing:
                raise SourceValidationError(f"Missing required columns: {missing}")
            rows = list(reader)
            if not rows:
                raise SourceValidationError("File has a header but no data rows")

        self._row_count = len(rows)

    def generate_bundle(self) -> dict:
        entries = []

        with open(self.source, newline="") as f:
            for row in csv.DictReader(f):
                pid = row.get("patient_id", "").strip()

                if pid.lower() in PLACEHOLDER_IDS:
                    self._reject(pid or "?", f"invalid patient_id '{pid}' — untrackable resource")
                    continue

                patient = self._row_to_patient(pid, row)
                if patient is None:
                    continue  # _reject() already called inside _row_to_patient

                entries.append({
                    "fullUrl": f"urn:uuid:emr-x-{pid}",
                    "resource": patient,
                    "request": {
                        "method": "POST",
                        "url": "Patient",
                        "ifNoneExist": f"identifier={SYSTEM_MRN}|{pid}",
                    },
                })

        self._bundle = {
            "resourceType": "Bundle",
            "type": self.bundle_type(),
            "entry": entries,
        }
        return self._bundle

    def _row_to_patient(self, pid: str, row: dict) -> dict | None:
        patient = {
            "resourceType": "Patient",
            "identifier": [{"system": SYSTEM_MRN, "value": pid}],
            "name": [{"use": "official"}],
        }

        if row.get("last_name"):
            patient["name"][0]["family"] = row["last_name"]
        else:
            self._warn(pid, "missing last_name")

        if row.get("first_name"):
            patient["name"][0]["given"] = [row["first_name"]]
        else:
            self._warn(pid, "missing first_name")

        raw_dob = row.get("dob", "").strip()
        if raw_dob:
            try:
                datetime.strptime(raw_dob, "%Y-%m-%d")
                patient["birthDate"] = raw_dob
            except ValueError:
                # Field context: birthDate. Any format other than YYYY-MM-DD is
                # not-cleanable — a wrong guess changes a clinical record.
                self._reject(pid, f"ambiguous birthDate '{raw_dob}' — cannot safely interpret")
                return None

        gender_raw = row.get("gender", "").strip().upper()
        if gender_raw:
            if gender_raw not in GENDER_MAP:
                self._warn(pid, f"unknown gender code '{gender_raw}', mapped to unknown")
            patient["gender"] = GENDER_MAP.get(gender_raw, "unknown")

        telecom = []
        if row.get("phone"):
            telecom.append({"system": "phone", "value": row["phone"], "use": "mobile"})
        if row.get("email"):
            telecom.append({"system": "email", "value": row["email"]})
        if telecom:
            patient["telecom"] = telecom

        if row.get("address") and row.get("city"):
            address = {"use": "home", "line": [row["address"]], "city": row["city"]}
            if row.get("state"):
                address["state"] = row["state"]
            if row.get("zip"):
                address["postalCode"] = row["zip"]
            patient["address"] = [address]

        return patient

    def verify_bundle(self) -> None:
        if not self._bundle:
            raise BundleValidationError("Bundle is empty — call generate_bundle() first")
        entries = self._bundle.get("entry", [])
        if not entries:
            raise BundleValidationError("Bundle has no entries")
        for i, entry in enumerate(entries):
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "Patient":
                raise BundleValidationError(f"Entry {i}: expected Patient, got {resource.get('resourceType')}")
            if not resource.get("identifier"):
                raise BundleValidationError(f"Entry {i}: Patient missing identifier (source ID lost)")

    def verify_import(self) -> None:
        client: MedplumClient = getattr(self, "_medplum", MedplumClient())

        rejected_ids = {row_id for row_id, _ in self.exceptions}

        with open(self.source, newline="") as f:
            expected = [
                row["patient_id"] for row in csv.DictReader(f)
                if row["patient_id"].lower() not in PLACEHOLDER_IDS
                and row["patient_id"] not in rejected_ids
            ]

        missing = []
        for pid in expected:
            result = client.search("Patient", {"identifier": f"{SYSTEM_MRN}|{pid}"})
            if result.get("total", 0) == 0:
                missing.append(pid)

        if missing:
            raise ImportVerificationError(
                f"Import verification failed. {len(missing)} patient(s) not found: {missing}"
            )
