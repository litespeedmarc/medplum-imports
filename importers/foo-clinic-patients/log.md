# foo-clinic-patients
**issue:** #1 — Import patients from Foo Clinic
**status:** Phase 4/6 — Import Code + Tests

## Phase 1: Issue Understanding
Source system: Foo Clinic. Nightly CSV extract emailed to the team.
Target FHIR resource: Patient (R4).
config-type `foo-clinic-patients` chosen — encodes source system (Foo Clinic) and resource type (patients).
Sample file retrieved from issue comment; 100 rows with 17 columns including MRN, health card number, DOB, gender, address, allergies, medications, and a proprietary `source_system_code`.

## Phase 2: Data Analysis
Field mapping decisions:
- `patient_id` (row integer) — NOT used as the source identifier; too fragile. `mrn` (MRN-XXXXXX) is the stable source ID → Patient.identifier (system: http://foo-clinic.example.org/patient-id).
- `health_card_number` → second identifier entry (system: http://foo-clinic.example.org/health-card). Placeholder values "000-000-000" and "UNKNOWN" → omit identifier entry, warn.
- `first_name` / `last_name` → Patient.name[0] (use: official). Missing → omit field, warn.
- `date_of_birth` → Patient.birthDate. Must be YYYY-MM-DD. MM/DD/YYYY → not-cleanable (MM vs DD ambiguous in general; specific ambiguous dates cannot be resolved). Partial YYYY-MM → not-cleanable (incomplete date changes clinical record). Ambiguous DD-MM-YYYY → not-cleanable.
- `gender` values: female/male/other/unknown → maps directly to FHIR gender values (lowercase already matches FHIR). No unknown codes found in sample headers; coded to handle any unrecognised value → warn, map to unknown.
- `phone` → Patient.telecom (system: phone). Malformed short values like "555" → warn, omit.
- `email` → Patient.telecom (system: email). Invalid format → warn, omit.
- `address_line_1` / `city` / `province` / `postal_code` → Patient.address (use: home). Canadian addresses; province maps to address.state in FHIR.
- `primary_language` → Patient.communication[].language (BCP-47 tag). English/French/Spanish/Arabic mapped to en/fr/es/ar. Unknown language codes → warn, omit.
- `allergies` → free-text, not-coded. Import as AllergyIntolerance is out of scope for patient extract; stored as Patient.extension or omitted. Decision: omit from Patient resource, warn that allergies require separate import. "UNKNOWN" and "None" → treat as absent, no warn.
- `medications` → same decision as allergies: out of scope for Patient resource. Omit, warn once per row if non-empty non-null value. Inconsistent capitalisation (Metformin 500mg vs metformin 500MG) reinforces the case-variant duplicate risk from edge-cases.md — cannot auto-merge, so omit is correct.
- `source_system_code` → proprietary clinic-internal code with no standard mapping. Decision: preserve as a second identifier with system http://foo-clinic.example.org/source-system. Not rejected; just carried forward for traceability.
- Null/placeholder MRN: blank or "UNKNOWN" → reject (untrackable resource per edge-cases.md).

## Phase 3: Sample Files
edge-cases.md reviewed. Relevant cases: ambiguous dates, null/placeholder MRN, unknown coded value (gender), missing optional fields, free-text allergies/medications, whitespace on name fields.
clean.csv: 5 rows — all required fields present, YYYY-MM-DD dates, known gender values, all four language codes exercised, all four source_system_code values covered.
cleanable.csv: 5 rows — whitespace on names (row 6, safe to strip); missing health_card_number (row 7, optional → omit, warn); placeholder health_card_number "000-000-000" (row 8, optional field placeholder → omit identifier entry, warn); missing first_name (row 9, optional → omit, warn); unknown gender code "EXTRATERRESTRIAL" (row 10, → warn, map to unknown). Also rows 7 and 8 contain allergies/medications values → warn per-row that these require separate import.
not-cleanable.csv: 5 rows — MM/DD/YYYY date "03/12/1978" (row 11, ambiguous: could be Mar 12 or Dec 3 → not-cleanable per edge-cases.md); partial date "2024-03" (row 12, incomplete → not-cleanable); blank MRN (row 13, untrackable); placeholder MRN "UNKNOWN" (row 14, untrackable). Row 15 is a valid control row to verify the importer continues past rejected rows.

## Phase 4: Import Code
Class: FooClinicPatientsImporter. mrn is the stable source ID; patient_id (row counter) not used as a FHIR identifier.
Three identifier systems: SYSTEM_MRN (required, stable ID), SYSTEM_HEALTH_CARD (optional, omit on placeholder), SYSTEM_SOURCE_CODE (traceability, always preserve when present).
_parse_dob() rejects partial YYYY-MM before attempting strptime; strptime failure rejects all other non-ISO formats — no format guessing.
allergies/medications omitted from Patient resource; per-row warning fires when non-null value present so operator knows a separate pass is needed.
verify_bundle() allows empty entry list (all rows rejected) rather than raising — caller inspects importer.exceptions.
verify_import() queries by SYSTEM_MRN identifier; excludes placeholder and rejected MRNs from the expected set.
Tests: conftest.py loads importer.py via importlib (same as runner). test_clean_data: 5 rows imported, warnings/exceptions both empty, MRN IDs in order, ifNoneExist on every entry, BCP-47 language codes verified. test_cleanable_data: 5 rows imported, exceptions empty, warnings populated; per-case assertions for whitespace strip, placeholder health card, missing first_name, unknown gender, allergies/meds warn. test_bad_data: 4 exceptions, 1 control row in bundle; specific rejection reasons checked for each bad MRN.

