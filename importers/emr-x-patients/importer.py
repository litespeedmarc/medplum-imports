import csv
from datetime import datetime
from pathlib import Path

from framework import BaseImporter, MedplumClient
from framework.exceptions import SourceValidationError, BundleValidationError, ImportVerificationError

REQUIRED_COLUMNS = {"patient_id", "first_name", "last_name", "dob", "gender"}

GENDER_MAP = {"M": "male", "F": "female", "O": "other", "U": "unknown", "X": "unknown"}

SYSTEM_MRN = "http://emr-x.example.org/patient-id"


class EmrXPatientsImporter(BaseImporter):
    """
    Imports Patient resources from EMR-X CSV exports.

    Source: EMR-X nightly patient extract.
    Target FHIR resource: Patient

    Data fidelity notes:
    - patient_id maps to identifier (system: SYSTEM_MRN) — never discarded
    - Dates validated strictly; invalid dates raise rather than coerce
    - gender 'X' maps to 'unknown' — no clinical interpretation
    - Empty optional fields are omitted from the bundle (not nulled)
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
                patient = self._row_to_patient(row)
                entries.append({
                    "fullUrl": f"urn:uuid:emr-x-{row['patient_id']}",
                    "resource": patient,
                    "request": {
                        "method": "POST",
                        "url": "Patient",
                        "ifNoneExist": f"identifier={SYSTEM_MRN}|{row['patient_id']}",
                    },
                })

        self._bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": entries,
        }
        return self._bundle

    def _row_to_patient(self, row: dict) -> dict:
        patient = {
            "resourceType": "Patient",
            "identifier": [{
                "system": SYSTEM_MRN,
                "value": row["patient_id"],
            }],
            "name": [{"use": "official"}],
        }

        if row.get("last_name"):
            patient["name"][0]["family"] = row["last_name"]
        if row.get("first_name"):
            patient["name"][0]["given"] = [row["first_name"]]

        raw_dob = row.get("dob", "").strip()
        if raw_dob:
            try:
                datetime.strptime(raw_dob, "%Y-%m-%d")
                patient["birthDate"] = raw_dob
            except ValueError:
                raise SourceValidationError(
                    f"Invalid date '{raw_dob}' for patient {row['patient_id']}. "
                    f"Expected YYYY-MM-DD. Refusing to coerce — every transformation is a liability."
                )

        gender_raw = row.get("gender", "").strip().upper()
        if gender_raw:
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

        with open(self.source, newline="") as f:
            source_ids = [row["patient_id"] for row in csv.DictReader(f)]

        missing = []
        for pid in source_ids:
            result = client.search("Patient", {"identifier": f"{SYSTEM_MRN}|{pid}"})
            if result.get("total", 0) == 0:
                missing.append(pid)

        if missing:
            raise ImportVerificationError(
                f"Import verification failed. {len(missing)} patient(s) not found in Medplum: {missing}"
            )
