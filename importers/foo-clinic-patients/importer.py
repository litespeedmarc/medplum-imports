import csv
import re
from datetime import datetime
from pathlib import Path

from framework import BaseImporter, MedplumClient
from framework.exceptions import SourceValidationError, BundleValidationError, ImportVerificationError

REQUIRED_COLUMNS = {"mrn", "first_name", "last_name", "date_of_birth", "gender"}

# mrn is the stable source identifier. patient_id is a row counter — not used.
SYSTEM_MRN = "http://foo-clinic.example.org/patient-id"
SYSTEM_HEALTH_CARD = "http://foo-clinic.example.org/health-card"
SYSTEM_SOURCE_CODE = "http://foo-clinic.example.org/source-system"

PLACEHOLDER_MRNS = {"", "unknown"}
PLACEHOLDER_HEALTH_CARDS = {"", "000-000-000", "unknown"}

# Foo Clinic uses lowercase FHIR gender strings directly.
# Any unrecognised value is cleanable — map to unknown, warn.
KNOWN_GENDERS = {"male", "female", "other", "unknown"}

LANGUAGE_MAP = {
    "english": "en",
    "french": "fr",
    "spanish": "es",
    "arabic": "ar",
}

# Null representations in free-text fields that mean "not present".
NULL_VALUES = {"", "none", "unknown", "n/a"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class FooClinicPatientsImporter(BaseImporter):
    """
    Imports Patient resources from Foo Clinic nightly CSV extracts.

    Source: Foo Clinic CSV patient extract (emailed nightly).
    Target FHIR resource: Patient (R4)

    Data fidelity notes:
    - mrn is the stable source identifier → identifier[0] (system: SYSTEM_MRN).
      patient_id is a row counter and is NOT used as a FHIR identifier.
    - Null/placeholder mrn (blank, "UNKNOWN") → _reject() — untrackable resource.
    - health_card_number preserved as identifier[1] when present and non-placeholder.
      Placeholder values ("000-000-000", "UNKNOWN") → identifier entry omitted, warn.
    - date_of_birth must be YYYY-MM-DD. Any other format → _reject() — wrong date
      changes a clinical record and cannot be safely interpreted.
    - Partial dates (YYYY-MM) → _reject() — incomplete date is not-cleanable.
    - gender is already lowercase FHIR-compatible in source. Unrecognised values
      → _warn(), map to "unknown".
    - Whitespace on name fields → strip, warn.
    - Missing first_name or last_name → omit field, warn.
    - allergies / medications → out of scope for Patient resource; if non-null/non-empty
      value is present, warn that a separate import is required. Field omitted.
    - source_system_code → preserved as identifier (system: SYSTEM_SOURCE_CODE)
      for traceability. No standard mapping attempted.
    - Empty optional fields omitted from bundle (never nulled).
    """

    def validate_source(self) -> None:
        path = Path(self.source)
        if not path.exists():
            raise SourceValidationError(f"File not found: {self.source}")

        with open(path, newline="", encoding="utf-8") as f:
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

        with open(Path(self.source), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                mrn = row.get("mrn", "").strip()

                if mrn.lower() in PLACEHOLDER_MRNS:
                    self._reject(mrn or "?", f"invalid mrn '{mrn}' — untrackable resource")
                    continue

                patient = self._row_to_patient(mrn, row)
                if patient is None:
                    continue  # _reject() already called inside _row_to_patient

                entries.append({
                    "fullUrl": f"urn:uuid:foo-clinic-{mrn}",
                    "resource": patient,
                    "request": {
                        "method": "POST",
                        "url": "Patient",
                        "ifNoneExist": f"identifier={SYSTEM_MRN}|{mrn}",
                    },
                })

        self._bundle = {
            "resourceType": "Bundle",
            "type": self.bundle_type(),
            "entry": entries,
        }
        return self._bundle

    def _row_to_patient(self, mrn: str, row: dict) -> dict | None:
        patient = {
            "resourceType": "Patient",
            "identifier": [{"system": SYSTEM_MRN, "value": mrn}],
            "name": [{"use": "official"}],
        }

        # Health card number — optional second identifier.
        hcn = row.get("health_card_number", "").strip()
        if hcn and hcn.lower() not in PLACEHOLDER_HEALTH_CARDS:
            patient["identifier"].append({"system": SYSTEM_HEALTH_CARD, "value": hcn})
        elif hcn and hcn.lower() in PLACEHOLDER_HEALTH_CARDS:
            self._warn(mrn, f"placeholder health_card_number '{hcn}' — identifier entry omitted")

        # Source system code — proprietary, preserved as identifier for traceability.
        source_code = row.get("source_system_code", "").strip()
        if source_code:
            patient["identifier"].append({"system": SYSTEM_SOURCE_CODE, "value": source_code})

        # Name fields — strip whitespace; missing fields are optional, warn.
        last_name = row.get("last_name", "").strip()
        first_name = row.get("first_name", "").strip()

        raw_last = row.get("last_name", "")
        raw_first = row.get("first_name", "")

        if raw_last != raw_last.strip():
            self._warn(mrn, f"whitespace stripped from last_name '{raw_last}'")
        if raw_first != raw_first.strip():
            self._warn(mrn, f"whitespace stripped from first_name '{raw_first}'")

        if last_name:
            patient["name"][0]["family"] = last_name
        else:
            self._warn(mrn, "missing last_name")

        if first_name:
            patient["name"][0]["given"] = [first_name]
        else:
            self._warn(mrn, "missing first_name")

        # Date of birth — strict YYYY-MM-DD only.
        raw_dob = row.get("date_of_birth", "").strip()
        if raw_dob:
            parsed = self._parse_dob(mrn, raw_dob)
            if parsed is None:
                return None  # _reject() already called
            patient["birthDate"] = parsed

        # Gender — source uses lowercase FHIR values; unrecognised → warn + unknown.
        gender_raw = row.get("gender", "").strip().lower()
        if gender_raw:
            if gender_raw not in KNOWN_GENDERS:
                self._warn(mrn, f"unknown gender code '{gender_raw}', mapped to unknown")
                patient["gender"] = "unknown"
            else:
                patient["gender"] = gender_raw

        # Telecom — phone and email, both optional.
        telecom = []
        phone = row.get("phone", "").strip()
        if phone:
            digits = re.sub(r"\D", "", phone)
            if len(digits) < 7:
                self._warn(mrn, f"phone '{phone}' appears malformed (fewer than 7 digits) — omitted")
            else:
                telecom.append({"system": "phone", "value": phone, "use": "mobile"})

        email = row.get("email", "").strip()
        if email:
            if not EMAIL_RE.match(email):
                self._warn(mrn, f"email '{email}' failed format check — omitted")
            else:
                telecom.append({"system": "email", "value": email})

        if telecom:
            patient["telecom"] = telecom

        # Address — Canadian. province maps to address.state in FHIR.
        address_line = row.get("address_line_1", "").strip()
        city = row.get("city", "").strip()
        if address_line and city:
            address = {"use": "home", "line": [address_line], "city": city}
            province = row.get("province", "").strip()
            if province:
                address["state"] = province
            postal = row.get("postal_code", "").strip()
            if postal:
                address["postalCode"] = postal
            patient["address"] = [address]

        # Primary language → FHIR communication[].
        lang_raw = row.get("primary_language", "").strip().lower()
        if lang_raw:
            bcp47 = LANGUAGE_MAP.get(lang_raw)
            if bcp47:
                patient["communication"] = [
                    {
                        "language": {
                            "coding": [
                                {
                                    "system": "urn:ietf:bcp:47",
                                    "code": bcp47,
                                    "display": row.get("primary_language", "").strip(),
                                }
                            ]
                        },
                        "preferred": True,
                    }
                ]
            else:
                self._warn(mrn, f"unrecognised primary_language '{lang_raw}' — communication omitted")

        # Allergies and medications — out of scope for Patient resource.
        # Warn per row if a non-null value is present so the operator knows a
        # separate import pass is needed.
        allergies_raw = row.get("allergies", "").strip()
        if allergies_raw.lower() not in NULL_VALUES:
            self._warn(
                mrn,
                f"allergies field contains '{allergies_raw}' — not imported to Patient; requires separate AllergyIntolerance import",
            )

        meds_raw = row.get("medications", "").strip()
        if meds_raw.lower() not in NULL_VALUES:
            self._warn(
                mrn,
                f"medications field contains '{meds_raw}' — not imported to Patient; requires separate MedicationRequest import",
            )

        return patient

    def _parse_dob(self, mrn: str, raw_dob: str) -> str | None:
        """
        Accept YYYY-MM-DD only.

        All other formats (MM/DD/YYYY, DD-MM-YYYY, YYYY-MM partial) are
        not-cleanable: the transformation would be a guess that could change
        a clinical record. Field context: birthDate.
        """
        # Reject partial dates (YYYY-MM without day).
        if re.match(r"^\d{4}-\d{2}$", raw_dob):
            self._reject(mrn, f"partial date_of_birth '{raw_dob}' — incomplete date is not-cleanable")
            return None

        try:
            datetime.strptime(raw_dob, "%Y-%m-%d")
            return raw_dob
        except ValueError:
            self._reject(
                mrn,
                f"date_of_birth '{raw_dob}' is not YYYY-MM-DD — ambiguous format is not-cleanable",
            )
            return None

    def verify_bundle(self) -> None:
        if not self._bundle:
            raise BundleValidationError("Bundle is empty — call generate_bundle() first")
        entries = self._bundle.get("entry", [])
        if not entries:
            # Not an error if all rows were rejected — caller can check importer.exceptions.
            return
        for i, entry in enumerate(entries):
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "Patient":
                raise BundleValidationError(
                    f"Entry {i}: expected Patient, got {resource.get('resourceType')}"
                )
            identifiers = resource.get("identifier", [])
            if not identifiers:
                raise BundleValidationError(
                    f"Entry {i}: Patient missing identifier — source ID (mrn) not preserved"
                )
            mrn_ids = [id_ for id_ in identifiers if id_.get("system") == SYSTEM_MRN]
            if not mrn_ids:
                raise BundleValidationError(
                    f"Entry {i}: Patient missing MRN identifier (system={SYSTEM_MRN})"
                )
            if "ifNoneExist" not in entry.get("request", {}):
                raise BundleValidationError(
                    f"Entry {i}: missing ifNoneExist — bundle would not be idempotent"
                )

    def verify_import(self) -> None:
        client: MedplumClient = getattr(self, "_medplum", MedplumClient())

        rejected_ids = {row_id for row_id, _ in self.exceptions}

        with open(Path(self.source), newline="", encoding="utf-8") as f:
            expected = [
                row["mrn"].strip()
                for row in csv.DictReader(f)
                if row["mrn"].strip().lower() not in PLACEHOLDER_MRNS
                and row["mrn"].strip() not in rejected_ids
            ]

        missing = []
        for mrn in expected:
            result = client.search("Patient", {"identifier": f"{SYSTEM_MRN}|{mrn}"})
            if result.get("total", 0) == 0:
                missing.append(mrn)

        if missing:
            raise ImportVerificationError(
                f"Import verification failed. {len(missing)} patient(s) not found in Medplum: {missing}"
            )
