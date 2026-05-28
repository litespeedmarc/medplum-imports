# emr-x-patients
**issue:** seed importer — built as framework reference implementation
**status:** Phase 5/5 — complete

## Phase 1: Issue Understanding
EMR-X nightly CSV patient extract. Target: FHIR R4 Patient resources.
Source system is EMR-X (fictional stand-in for any CSV-based EMR export).
config-type `emr-x-patients` chosen to embed source system name per convention.

## Phase 2: Data Analysis
Required columns: patient_id, first_name, last_name, dob, gender.
Optional: phone, email, address, city, state, zip.
gender codes M/F/O/U/X mapped to FHIR values; X→unknown (no clinical interpretation).
dob must be YYYY-MM-DD; invalid dates raise rather than coerce — every transformation is a liability.
No unmappable fields; patient_id preserved as identifier with namespaced system URI.

## Phase 3: Sample Files
basic.csv: 5 clean rows covering common gender codes and optional field presence.
edge-cases.csv: missing optional fields, unknown gender code, duplicate patient_id row.
Invalid date format intentionally omitted from samples (would abort the run before bundle generation).

## Phase 4: Import Code
Class: EmrXPatientsImporter. bundle_type() defaults to batch — rows are independent.
ifNoneExist on every entry keyed by identifier system+value — safe to re-run.
SYSTEM_MRN = "http://emr-x.example.org/patient-id" — source ID never lost.
verify_import() queries Medplum by identifier for each source patient_id.

## Phase 5: Test Run Results
Built as framework reference — samples verified against local Medplum instance during framework development.
basic.csv: all entries created, verify_import() confirmed all patient_ids present.
edge-cases.csv: unknown gender code falls back to "unknown" (acceptable per spec), duplicate ID handled by ifNoneExist (no duplicate resource created).
