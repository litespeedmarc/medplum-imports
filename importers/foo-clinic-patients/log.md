# foo-clinic-patients
**issue:** #1 — Import patients from Foo Clinic
**status:** Phase 1/6 — Issue Understanding

## Phase 1: Issue Understanding
Source system: Foo Clinic. Nightly CSV extract emailed to the team.
Target FHIR resource: Patient (R4).
config-type `foo-clinic-patients` chosen — encodes source system (Foo Clinic) and resource type (patients).
Sample file retrieved from issue comment; 100 rows with 17 columns including MRN, health card number, DOB, gender, address, allergies, medications, and a proprietary `source_system_code`.
