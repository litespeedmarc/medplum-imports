# Medplum API Reference

Base URL: `http://localhost:8103`

> **Examples:** [`examples/list_resources.sh.example`](examples/list_resources.sh.example) · [`examples/delete_resource.sh.example`](examples/delete_resource.sh.example) · [`examples/clear_resource_type.sh.example`](examples/clear_resource_type.sh.example) · [`examples/seed_test_data.sh.example`](examples/seed_test_data.sh.example)

## Core FHIR CRUD

| Method | URL | Action |
|---|---|---|
| `POST`   | `/fhir/R4/{Type}` | Create |
| `GET`    | `/fhir/R4/{Type}/{id}` | Read |
| `PUT`    | `/fhir/R4/{Type}/{id}` | Update (full replace) |
| `PATCH`  | `/fhir/R4/{Type}/{id}` | Patch (JSON Patch) |
| `DELETE` | `/fhir/R4/{Type}/{id}` | Delete |
| `GET`    | `/fhir/R4/{Type}` | Search |
| `POST`   | `/fhir/R4` | Batch / Transaction (Bundle) |
| `GET`    | `/fhir/R4/{Type}/{id}/_history` | Version history |
| `GET`    | `/fhir/R4/{Type}/{id}/_history/{vid}` | Specific version |
| `GET`    | `/fhir/R4/metadata` | CapabilityStatement (no auth) |

## Search Parameters

### Pagination
```
_count=50          # results per page (default 20)
_offset=0          # offset (max 10,000)
_cursor=<token>    # cursor-based pagination (large datasets)
```

### Sorting
```
_sort=name           # ascending
_sort=-_lastUpdated  # descending (prefix -)
```

### Field selection
```
_fields=id,name,birthDate,gender   # return only these fields
_summary=true                      # summary view
_summary=count                     # count only
```

### Includes
```
_include=Encounter:patient         # pull referenced Patient inline
_revinclude=Observation:subject    # pull Observations that reference this resource
```

### Common Resource Search Params
```
# Patient
?name=Alice
?family=Smith
?given=John
?birthdate=1985-03-15
?gender=female
?identifier=system|value
?address-city=Boston

# Observation
?subject=Patient/123
?code=http://loinc.org|35200-5
?date=ge2024-01-01
?status=final

# Encounter
?patient=Patient/123
?date=ge2024-01-01
?status=finished
?type=11429006    # SNOMED consultation

# Task
?status=ready
?owner=Practitioner/456
?for=Patient/123

# Condition
?subject=Patient/123
?clinical-status=active
?code=714628002   # SNOMED code

# MedicationRequest
?subject=Patient/123
?status=active
?intent=order
```

## FHIR Operations ($)

```
GET/POST  /fhir/R4/Patient/{id}/$everything       # All resources related to patient
GET/POST  /fhir/R4/Patient/{id}/$summary          # Summary
GET       /fhir/R4/Patient/{id}/$ccda-export      # C-CDA export
POST      /fhir/R4/Patient/$match                 # Patient matching

GET/POST  /fhir/R4/ValueSet/$expand               # Expand a ValueSet
GET/POST  /fhir/R4/CodeSystem/$lookup             # Lookup a code
GET/POST  /fhir/R4/ConceptMap/$translate          # Translate concept

POST      /fhir/R4/{Type}/{id}/$validate          # Validate resource
POST      /fhir/R4/{Type}/{id}/$reindex           # Reindex for search
POST      /fhir/R4/{Type}/{id}/$resend            # Resend subscriptions

POST      /fhir/R4/Bot/{id}/$execute              # Execute a Bot
POST      /fhir/R4/QuestionnaireResponse/$extract # SDC extraction from response

GET/POST  /fhir/R4/$export                        # Bulk export (NDJSON)
```

## Batch / Transaction Bundle

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "fullUrl": "urn:uuid:abc-123",
      "resource": { "resourceType": "Patient", "name": [...] },
      "request": { "method": "POST", "url": "Patient" }
    },
    {
      "resource": { "resourceType": "Observation", ... },
      "request": {
        "method": "POST",
        "url": "Observation",
        "ifNoneExist": "subject=Patient/123&code=35200-5"
      }
    },
    {
      "request": { "method": "DELETE", "url": "Patient/old-id" }
    }
  ]
}
```

- **`transaction`** — atomic: all-or-nothing
- **`batch`** — non-atomic: each entry processed independently

## JSON Patch

```bash
curl -X PATCH http://localhost:8103/fhir/R4/Patient/123 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json-patch+json" \
  -d '[
    { "op": "replace", "path": "/gender", "value": "female" },
    { "op": "add", "path": "/telecom/-", "value": { "system": "phone", "value": "555-1234" } }
  ]'
```

## Conditional Operations

```
# Conditional create (only create if not found)
POST /fhir/R4/Patient
If-None-Exist: identifier=http://example.org|MRN-123

# Conditional update
PUT /fhir/R4/Patient?identifier=http://example.org|MRN-123

# Conditional delete
DELETE /fhir/R4/Patient?identifier=http://example.org|MRN-123
```

## Key Headers

```
Authorization: Bearer <token>
Content-Type: application/fhir+json    # for FHIR resources
Content-Type: application/json-patch+json  # for PATCH
Accept: application/fhir+json
Prefer: return=minimal                 # skip response body
Prefer: return=representation          # full resource in response (default)
X-Medplum: extended                    # extended response format
```

## Public Endpoints (no auth)

```
GET /metadata                           # CapabilityStatement
GET /healthcheck                        # Server health { ok, version, postgres, redis }
GET /$versions                          # Supported FHIR versions
GET /.well-known/smart-configuration    # SMART App Launch config
GET /.well-known/smart-styles.json      # SMART UI styles
```
