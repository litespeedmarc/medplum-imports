# Medplum-Specific Resources

Beyond standard FHIR, Medplum adds its own resource types for platform management.

## Bot

A Bot is a JavaScript/TypeScript function that runs server-side. Triggered by Subscriptions or called directly via `$execute`.

```json
{
  "resourceType": "Bot",
  "name": "Lab Results Notifier",
  "description": "Sends notification when DiagnosticReport becomes final",
  "code": "exports.handler = async (medplum, event) => { console.log(event.input); }",
  "runAsUser": false
}
```

**Execute a Bot:**
```bash
curl -X POST http://localhost:8103/fhir/R4/Bot/{id}/$execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/fhir+json" \
  -d '{ "resourceType": "Patient", "id": "123" }'
```

## Agent

An Agent is an integration connector — a long-running process that bridges Medplum to external systems (HL7v2, DICOM, etc.).

```json
{
  "resourceType": "Agent",
  "name": "HL7 Interface",
  "status": "active",
  "url": "mllp://0.0.0.0:2575",
  "description": "Receives HL7 v2 messages from lab system"
}
```

## AccessPolicy

Controls what resources and fields a user/bot can read or write.

```json
{
  "resourceType": "AccessPolicy",
  "name": "Read-Only Patient Access",
  "resource": [
    {
      "resourceType": "Patient",
      "readonly": true,
      "hiddenFields": ["telecom", "address"]
    },
    {
      "resourceType": "Observation",
      "readonly": true
    }
  ]
}
```

**Wildcard:** Set `"resourceType": "*"` to apply a rule to all resource types.

**Criteria filtering:** Limit access to a subset of resources:
```json
{ "resourceType": "Patient", "criteria": "Patient?organization=Organization/123" }
```

## ProjectMembership

Links a User to a Project, with their profile and access policy.

```json
{
  "resourceType": "ProjectMembership",
  "project": { "reference": "Project/3835da81-..." },
  "user": { "reference": "User/78b08f33-..." },
  "profile": { "reference": "Practitioner/241a539f-..." },
  "admin": true
}
```

**Search members of a project:**
```bash
GET /fhir/R4/ProjectMembership?project=Project/3835da81-...
```

## ClientApplication

An OAuth2 client registration.

```json
{
  "resourceType": "ClientApplication",
  "name": "My Integration App",
  "redirectUri": "http://localhost:3000/callback",
  "pkce": true
}
```

After creation, the `id` is the `client_id` and `secret` is the `client_secret`.

## Project

Projects are the top-level data isolation boundary. All clinical data belongs to a project.

```json
{
  "resourceType": "Project",
  "name": "My Clinic",
  "features": ["bots", "cron", "subscriptions"]
}
```

**Local projects:**
- `Project/3835da81-7590-4cbc-9438-3b85ee9550a8` — Super Admin
- `Project/161452d9-43b7-5c29-aa7b-c85680fa45c6` — FHIR R4

## UserConfiguration

Per-user UI preferences.

```json
{
  "resourceType": "UserConfiguration",
  "menu": [
    {
      "title": "Favorites",
      "link": [
        { "name": "Patients", "target": "/Patient" },
        { "name": "Active Tasks", "target": "/Task?status=ready,in-progress" }
      ]
    }
  ]
}
```

## SmartAppLaunch

Registers a SMART on FHIR app for launch within Medplum.

```json
{
  "resourceType": "SmartAppLaunch",
  "name": "Cardiology App",
  "launchUri": "https://myapp.example.com/launch"
}
```

## Subscription (standard FHIR + Medplum extensions)

Triggers a Bot or webhook when a resource changes.

```json
{
  "resourceType": "Subscription",
  "status": "active",
  "criteria": "DiagnosticReport?status=final",
  "channel": {
    "type": "rest-hook",
    "endpoint": "Bot/bot-id-here",
    "payload": "application/fhir+json"
  }
}
```

`endpoint` can be a Bot reference (Medplum extension) or a full HTTPS URL.

## Meta Tags (Medplum extensions on all resources)

Every stored resource has a `meta` with Medplum additions:

```json
"meta": {
  "versionId": "uuid",
  "lastUpdated": "2024-03-01T10:00:00Z",
  "project": "Project/3835da81-...",
  "author": { "reference": "Practitioner/..." },
  "compartment": [{ "reference": "Patient/123" }]
}
```

`meta.project` — which project this resource belongs to  
`meta.author` — who created/last updated it  
`meta.compartment` — patient compartment for access control
