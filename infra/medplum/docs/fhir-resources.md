# FHIR Resource Schemas

Key fields for the most-used clinical resources. `(R)` = required.

> **Examples:** [`examples/create_patient.sh.example`](examples/create_patient.sh.example) · [`examples/create_encounter.sh.example`](examples/create_encounter.sh.example) · [`examples/create_observation.sh.example`](examples/create_observation.sh.example) · [`examples/seed_test_data.sh.example`](examples/seed_test_data.sh.example)

## Patient

```json
{
  "resourceType": "Patient",
  "identifier": [{ "system": "http://example.org/mrn", "value": "MRN-001" }],
  "active": true,
  "name": [{ "use": "official", "family": "Smith", "given": ["Alice"] }],
  "telecom": [
    { "system": "phone", "value": "555-867-5309", "use": "mobile" },
    { "system": "email", "value": "alice@example.com" }
  ],
  "gender": "female",
  "birthDate": "1985-03-15",
  "address": [{
    "use": "home",
    "line": ["123 Main St"],
    "city": "Boston", "state": "MA", "postalCode": "02101", "country": "US"
  }],
  "maritalStatus": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus", "code": "M" }] },
  "generalPractitioner": [{ "reference": "Practitioner/123" }],
  "managingOrganization": { "reference": "Organization/456" }
}
```

**gender values:** `male` | `female` | `other` | `unknown`

## Practitioner

```json
{
  "resourceType": "Practitioner",
  "identifier": [{ "system": "http://hl7.org/fhir/sid/us-npi", "value": "1234567890" }],
  "active": true,
  "name": [{ "use": "official", "family": "Jones", "given": ["Bob"], "prefix": ["Dr."] }],
  "telecom": [{ "system": "phone", "value": "555-100-2000", "use": "work" }],
  "qualification": [{
    "code": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/v2-0360", "code": "MD" }] }
  }]
}
```

## Encounter

```json
{
  "resourceType": "Encounter",
  "status": "finished",
  "class": { "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB" },
  "type": [{ "coding": [{ "system": "http://snomed.info/sct", "code": "11429006", "display": "Consultation" }] }],
  "subject": { "reference": "Patient/123" },
  "participant": [{ "individual": { "reference": "Practitioner/456" } }],
  "period": { "start": "2024-03-01T09:00:00Z", "end": "2024-03-01T09:30:00Z" },
  "reasonCode": [{ "coding": [{ "system": "http://snomed.info/sct", "code": "44054006", "display": "Type 2 diabetes" }] }],
  "serviceProvider": { "reference": "Organization/789" }
}
```

**status values:** `planned` | `arrived` | `triaged` | `in-progress` | `onleave` | `finished` | `cancelled`

**class codes (common):** `AMB` (ambulatory) | `IMP` (inpatient) | `EMER` (emergency) | `VR` (virtual)

## Observation

```json
{
  "resourceType": "Observation",
  "status": "final",
  "category": [{ "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory" }] }],
  "code": { "coding": [{ "system": "http://loinc.org", "code": "35200-5", "display": "Cholesterol" }] },
  "subject": { "reference": "Patient/123" },
  "encounter": { "reference": "Encounter/456" },
  "effectiveDateTime": "2024-03-01T10:00:00Z",
  "performer": [{ "reference": "Practitioner/789" }],
  "valueQuantity": { "value": 185, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL" },
  "interpretation": [{ "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N" }] }],
  "referenceRange": [{ "low": { "value": 0 }, "high": { "value": 200, "unit": "mg/dL" } }]
}
```

**status values:** `registered` | `preliminary` | `final` | `amended` | `corrected` | `cancelled` | `entered-in-error`

**value[x] options:** `valueQuantity` | `valueCodeableConcept` | `valueString` | `valueBoolean` | `valueInteger` | `valueDateTime`

**category codes:** `vital-signs` | `laboratory` | `imaging` | `survey` | `exam` | `therapy`

## Condition

```json
{
  "resourceType": "Condition",
  "clinicalStatus": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active" }] },
  "verificationStatus": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed" }] },
  "category": [{ "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item" }] }],
  "severity": { "coding": [{ "system": "http://snomed.info/sct", "code": "255604002", "display": "Mild" }] },
  "code": { "coding": [{ "system": "http://snomed.info/sct", "code": "44054006", "display": "Type 2 diabetes mellitus" }] },
  "subject": { "reference": "Patient/123" },
  "encounter": { "reference": "Encounter/456" },
  "onsetDateTime": "2022-06-01",
  "recordedDate": "2024-03-01"
}
```

**clinicalStatus codes:** `active` | `recurrence` | `relapse` | `inactive` | `remission` | `resolved`

**verificationStatus codes:** `unconfirmed` | `provisional` | `differential` | `confirmed` | `refuted` | `entered-in-error`

## MedicationRequest

```json
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {
    "coding": [{ "system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "1161611", "display": "metformin 500mg tablet" }]
  },
  "subject": { "reference": "Patient/123" },
  "encounter": { "reference": "Encounter/456" },
  "requester": { "reference": "Practitioner/789" },
  "authoredOn": "2024-03-01",
  "reasonReference": [{ "reference": "Condition/abc" }],
  "dosageInstruction": [{
    "text": "Take 1 tablet twice daily with meals",
    "timing": { "repeat": { "frequency": 2, "period": 1, "periodUnit": "d" } },
    "route": { "coding": [{ "system": "http://snomed.info/sct", "code": "26643006", "display": "Oral" }] },
    "doseAndRate": [{ "doseQuantity": { "value": 500, "unit": "mg", "system": "http://unitsofmeasure.org", "code": "mg" } }]
  }]
}
```

**status values:** `active` | `on-hold` | `cancelled` | `completed` | `entered-in-error` | `draft` | `unknown`

**intent values:** `proposal` | `plan` | `order` | `original-order` | `instance-order`

## DiagnosticReport

```json
{
  "resourceType": "DiagnosticReport",
  "status": "final",
  "category": [{ "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "CH", "display": "Chemistry" }] }],
  "code": { "coding": [{ "system": "http://loinc.org", "code": "57698-3", "display": "Lipid panel" }] },
  "subject": { "reference": "Patient/123" },
  "encounter": { "reference": "Encounter/456" },
  "effectiveDateTime": "2024-03-01T10:00:00Z",
  "issued": "2024-03-01T11:00:00Z",
  "performer": [{ "reference": "Practitioner/789" }],
  "result": [
    { "reference": "Observation/cholesterol-obs" },
    { "reference": "Observation/ldl-obs" }
  ],
  "conclusion": "Lipid levels within normal range."
}
```

**status values:** `registered` | `partial` | `preliminary` | `final` | `amended` | `corrected` | `cancelled` | `entered-in-error`

## Questionnaire

```json
{
  "resourceType": "Questionnaire",
  "status": "active",
  "subjectType": ["Patient"],
  "title": "Patient Intake Form",
  "item": [
    { "linkId": "name", "text": "Full Name", "type": "string", "required": true },
    { "linkId": "dob", "text": "Date of Birth", "type": "date" },
    {
      "linkId": "chief-complaint", "text": "Chief Complaint", "type": "text"
    },
    {
      "linkId": "allergies", "text": "Allergies", "type": "group", "repeats": true,
      "item": [
        { "linkId": "allergy-name", "text": "Allergen", "type": "string" },
        { "linkId": "allergy-severity", "text": "Severity", "type": "choice",
          "answerOption": [
            { "valueCoding": { "code": "mild", "display": "Mild" } },
            { "valueCoding": { "code": "severe", "display": "Severe" } }
          ]
        }
      ]
    }
  ]
}
```

**item types:** `group` | `display` | `boolean` | `decimal` | `integer` | `date` | `dateTime` | `time` | `string` | `text` | `url` | `choice` | `open-choice` | `attachment` | `reference` | `quantity`

## Task

```json
{
  "resourceType": "Task",
  "status": "ready",
  "intent": "order",
  "priority": "routine",
  "code": { "coding": [{ "system": "http://example.org/task-types", "code": "review-labs", "display": "Review Lab Results" }] },
  "description": "Review lipid panel results for patient",
  "for": { "reference": "Patient/123", "display": "Alice Smith" },
  "focus": { "reference": "DiagnosticReport/456" },
  "owner": { "reference": "Practitioner/789" },
  "authoredOn": "2024-03-01T11:00:00Z",
  "performerType": [{ "coding": [{ "system": "http://snomed.info/sct", "code": "158965000", "display": "Doctor" }] }],
  "businessStatus": { "coding": [{ "code": "pending-review", "display": "Pending Review" }] }
}
```

**status values:** `draft` | `requested` | `received` | `accepted` | `rejected` | `ready` | `cancelled` | `in-progress` | `on-hold` | `failed` | `completed` | `entered-in-error`

## Organization

```json
{
  "resourceType": "Organization",
  "active": true,
  "type": [{ "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/organization-type", "code": "prov", "display": "Healthcare Provider" }] }],
  "name": "General Hospital",
  "telecom": [{ "system": "phone", "value": "555-200-3000", "use": "work" }],
  "address": [{ "line": ["100 Hospital Way"], "city": "Boston", "state": "MA", "postalCode": "02101" }]
}
```

## Location

```json
{
  "resourceType": "Location",
  "status": "active",
  "name": "Cardiology Clinic - Floor 3",
  "mode": "instance",
  "type": [{ "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode", "code": "CARD", "display": "Cardiology clinic" }] }],
  "address": { "line": ["100 Hospital Way, Room 301"], "city": "Boston", "state": "MA" },
  "managingOrganization": { "reference": "Organization/123" }
}
```

## Common Code Systems

| System | URI | Used for |
|---|---|---|
| SNOMED CT | `http://snomed.info/sct` | Clinical concepts, procedures, findings |
| LOINC | `http://loinc.org` | Lab tests, observations, vitals |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` | Medications |
| UCUM | `http://unitsofmeasure.org` | Measurement units |
| ICD-10 | `http://hl7.org/fhir/sid/icd-10-cm` | Diagnoses |
| CPT | `http://www.ama-assn.org/go/cpt` | Procedures |
| NPI | `http://hl7.org/fhir/sid/us-npi` | Provider identifier |
| US SSN | `http://hl7.org/fhir/sid/us-ssn` | Patient SSN |
| HL7 v2-0203 | `http://terminology.hl7.org/CodeSystem/v2-0203` | Identifier types (MRN=MR, SSN=SS) |
