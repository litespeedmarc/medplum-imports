# infra/medplum

Local Medplum FHIR server — used for development and testing only.
This is an external system we connect to, not code we own.

## Directory Layout

```
infra/medplum/
├── docker-compose.yml       # Full stack: postgres, redis, server, app
└── docs/
    ├── README.md            # This file
    ├── auth-flow.md         # How to authenticate (PKCE, token endpoints)
    ├── api-reference.md     # REST endpoints, search params, FHIR operations
    ├── fhir-resources.md    # Schemas: Patient, Encounter, Observation, etc.
    ├── medplum-specific-resources.md  # Bot, Agent, AccessPolicy, etc.
    ├── test-scenarios.md    # Common test workflows end-to-end
    └── examples/            # Runnable curl examples (copy & adapt)
        ├── authenticate.sh.example
        ├── create_patient.sh.example
        ├── create_encounter.sh.example
        ├── create_observation.sh.example
        ├── list_resources.sh.example
        ├── delete_resource.sh.example
        ├── clear_resource_type.sh.example
        └── seed_test_data.sh.example
```

## Running the Stack

All commands run from `infra/medplum/`:

```bash
# Start (detached)
docker compose up -d

# Check status
docker compose ps

# Stop
docker compose down

# Tail logs
docker compose logs -f medplum-server

# Server health (no auth required)
curl http://localhost:8103/healthcheck
```

**Project name is pinned to `medplum`** (set in docker-compose.yml), so containers
are always named `medplum-postgres-1`, `medplum-server-1`, etc. regardless of
which directory you run from.

## Services

| Service | Host Port | Notes |
|---|---|---|
| Web App | http://localhost:3001 | Remapped from 3000 (conflict) |
| FHIR API | http://localhost:8103 | |
| Postgres | localhost:5434 | Remapped from 5432 (conflict) |
| Redis | localhost:6381 | Remapped from 6379 (conflict) |

**Admin credentials:** `admin@example.com` / `medplum_admin`

## First Steps After Starting

```bash
# 1. Authenticate → see docs/examples/authenticate.sh.example
# 2. Seed test data → see docs/examples/seed_test_data.sh.example
# 3. Verify in UI → http://localhost:3001/Patient
```

## Key Concepts

- **Everything is a FHIR resource** — patients, questionnaires, tasks, bots, access policies
- **Projects** scope all data — super admin project sees everything
- **Auth is always PKCE** — no plain Basic auth to the FHIR API
- **Bulk... button in UI** shows only Questionnaires with `subjectType: ["Patient"]`
- **Bots** are server-side JS triggered by Subscriptions or called via `$execute`
- **Port remapping** — standard ports were already in use locally; see ports above
