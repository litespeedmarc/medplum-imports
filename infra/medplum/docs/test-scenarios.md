# Test Scenarios & Workflows

Common tester patterns for a local Medplum instance. Each scenario references
the example script(s) in `examples/` that implement it — read those for the
full curl commands.

## Prerequisites

Authenticate first. Every scenario below requires `$MEDPLUM_TOKEN` in the environment.

> **→ [`examples/authenticate.sh.example`](examples/authenticate.sh.example)**

```bash
source examples/authenticate.sh.example
echo $MEDPLUM_TOKEN   # should print a JWT
```

---

## Scenario 1: Seed Realistic Test Data (start here)

Loads a transaction bundle: org, practitioner, 3 patients, condition, observation, task, questionnaire — all linked.

> **→ [`examples/seed_test_data.sh.example`](examples/seed_test_data.sh.example)**

After running, verify in the UI at `http://localhost:3001/Patient`.

---

## Scenario 2: Create a Single Patient

> **→ [`examples/create_patient.sh.example`](examples/create_patient.sh.example)**

Returns the created Patient JSON with the server-assigned `id`. Capture it:

```bash
PATIENT_ID=$(bash examples/create_patient.sh.example | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

---

## Scenario 3: Clinical Visit Chain (Patient → Encounter → Observation)

Run these in order, substituting the IDs from each step into the next:

1. Create patient → [`examples/create_patient.sh.example`](examples/create_patient.sh.example)
2. Create encounter (replace `PATIENT_ID_HERE`) → [`examples/create_encounter.sh.example`](examples/create_encounter.sh.example)
3. Record observation (replace both IDs) → [`examples/create_observation.sh.example`](examples/create_observation.sh.example)

The observation example includes a blood pressure variant in the comments.

---

## Scenario 4: Search and Inspect

> **→ [`examples/list_resources.sh.example`](examples/list_resources.sh.example)**

The example covers: list all patients, search by name, filter observations by patient, count resources, and the `$everything` operation. Uncomment the variant you need.

---

## Scenario 5: Questionnaire → Bulk App Workflow

The Medplum UI's **Bulk...** button only shows Questionnaires with `subjectType: ["Patient"]`.

The `seed_test_data.sh.example` bundle already creates one ("Annual Wellness Check"). To add another:

```bash
curl -s -X POST http://localhost:8103/fhir/R4/Questionnaire \
  -H "Authorization: Bearer $MEDPLUM_TOKEN" \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Questionnaire",
    "status": "active",
    "subjectType": ["Patient"],
    "title": "My Form",
    "item": [{ "linkId": "q1", "text": "Question?", "type": "string" }]
  }'
```

In the UI: Patient list → check rows → Bulk... → your form appears.

---

## Scenario 6: Task Lifecycle

Tasks are FHIR resources with a status machine: `ready → in-progress → completed`.

Create a task pointing at a patient and an optional focus resource (e.g. an Observation):

```bash
curl -s -X POST http://localhost:8103/fhir/R4/Task \
  -H "Authorization: Bearer $MEDPLUM_TOKEN" \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Task",
    "status": "ready",
    "intent": "order",
    "code": { "text": "Review lab results" },
    "for": { "reference": "Patient/PATIENT_ID" },
    "focus": { "reference": "Observation/OBS_ID" }
  }'
```

Transition status via PATCH:

```bash
curl -s -X PATCH http://localhost:8103/fhir/R4/Task/TASK_ID \
  -H "Authorization: Bearer $MEDPLUM_TOKEN" \
  -H "Content-Type: application/json-patch+json" \
  -d '[{ "op": "replace", "path": "/status", "value": "completed" }]'
```

**Task status values:** `draft` → `requested` → `ready` → `in-progress` → `completed` (also: `on-hold`, `failed`, `cancelled`)

---

## Scenario 7: Count All Resource Types (Health Check)

Quick summary of what's in the system:

```bash
for TYPE in Patient Practitioner Encounter Observation Condition MedicationRequest DiagnosticReport Task Questionnaire; do
  COUNT=$(curl -s "http://localhost:8103/fhir/R4/$TYPE?_summary=count" \
    -H "Authorization: Bearer $MEDPLUM_TOKEN" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('total', 0))")
  echo "$TYPE: $COUNT"
done
```

---

## Scenario 8: Reset Between Test Runs

Delete all resources of one or more types. **Permanent — local dev only.**

> **→ [`examples/clear_resource_type.sh.example`](examples/clear_resource_type.sh.example)**

Edit `RESOURCE_TYPE` in the script. Run once per type you want to clear.

To delete a specific resource:

> **→ [`examples/delete_resource.sh.example`](examples/delete_resource.sh.example)**

---

## Realistic Data Patterns

These are the data shapes used in official Medplum examples — copy/adapt for test fixtures.

### Patient (from medplum-provider example)
```json
{
  "resourceType": "Patient",
  "identifier": [
    { "type": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "SS" }] },
      "system": "http://hl7.org/fhir/sid/us-ssn", "value": "444222222" }
  ],
  "name": [{ "use": "official", "family": "Williams", "given": ["David", "James"] }],
  "gender": "male", "birthDate": "1990-02-28",
  "address": [{ "use": "home", "line": ["123 Main St"], "city": "San Francisco", "state": "CA", "postalCode": "98732" }],
  "telecom": [{ "system": "phone", "value": "888-555-8439", "use": "mobile" }]
}
```

### Lab Observation (from medplum-task-demo)
```json
{
  "resourceType": "Observation",
  "status": "final",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "35200-5", "display": "Cholesterol" }] },
  "subject": { "reference": "Patient/..." },
  "effectiveDateTime": "2024-03-01T14:26:06Z",
  "valueQuantity": { "value": 6.3, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L" },
  "referenceRange": [{ "high": { "value": 4.5, "unit": "mmol/L" } }],
  "interpretation": [{ "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High" }] }]
}
```

### Task with Communication Focus (from medplum-task-demo)
```json
{
  "resourceType": "Task",
  "status": "ready",
  "intent": "order",
  "code": { "coding": [{ "system": "http://example.org/task-types", "code": "respond-to-message" }] },
  "for": { "reference": "Patient/...", "display": "Jane California" },
  "focus": { "reference": "Communication/..." },
  "performerType": [{ "coding": [{ "system": "http://snomed.info/sct", "code": "224535009", "display": "Registered Nurse" }] }],
  "businessStatus": { "coding": [{ "code": "ready", "display": "Ready" }] }
}
```
