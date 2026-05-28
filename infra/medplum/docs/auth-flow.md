# Medplum Auth Flow

## Overview

Medplum uses OAuth2 + PKCE. There is no simple username/password API call — auth is always a two-step code exchange.

**Auth endpoints:**
- `POST /auth/login` — exchange credentials for a one-time code
- `POST /oauth2/token` — exchange code (+ PKCE verifier) for access token

## PKCE Test Vectors (safe for local dev)

These are the RFC 7636 example values — reusable for local scripting:

```
code_verifier:  dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
code_challenge: E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
method:         S256
```

## Full Token Flow (curl)

> **Example script:** [`examples/authenticate.sh.example`](examples/authenticate.sh.example)

```bash
# Step 1: Login → get code
CODE=$(curl -s -X POST http://localhost:8103/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "medplum_admin",
    "codeChallenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
    "codeChallengeMethod": "S256"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")

# Step 2: Exchange code → access token
TOKEN=$(curl -s -X POST http://localhost:8103/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=$CODE&code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Use the token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8103/fhir/R4/Patient
```

## Token Response Fields

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "openid",
  "id_token": "eyJ...",
  "project": { "reference": "Project/...", "display": "Super Admin" },
  "profile": { "reference": "Practitioner/...", "display": "Medplum Admin" }
}
```

## Other Auth Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /auth/newuser` | Register a new user |
| `POST /auth/newproject` | Create a new project (after partial login) |
| `POST /auth/newpatient` | Register as patient |
| `POST /auth/google` | Google OAuth login |
| `GET  /auth/me` | Current user profile (requires token) |
| `POST /auth/changepassword` | Change password (requires token) |
| `POST /auth/resetpassword` | Reset password (public) |
| `POST /auth/revoke` | Revoke token (requires token) |
| `POST /oauth2/token` | Token endpoint (all grant types) |
| `GET  /oauth2/userinfo` | User info (requires token) |
| `POST /oauth2/introspect` | Token introspection |

## Supported Grant Types

- `authorization_code` + PKCE (primary)
- `client_credentials` (server-to-server, requires registered ClientApplication)
- `refresh_token`
- `urn:ietf:params:oauth:grant-type:token-exchange`

## Client Credentials Flow (requires registered ClientApplication)

```bash
curl -s -X POST http://localhost:8103/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=<ID>&client_secret=<SECRET>&scope=openid"
```

## Token Lifetime

Tokens expire after **3600 seconds (1 hour)**. Re-run the two-step flow to get a new one.
See [`examples/authenticate.sh.example`](examples/authenticate.sh.example) to source a token into your shell.

## Projects

The Super Admin project (`Project/3835da81-...`) can see and modify all data.
The FHIR R4 project (`Project/161452d9-...`) is for patient/clinical data.

To scope to a specific project, pass `projectId` in the login body:
```json
{ "email": "...", "password": "...", "projectId": "161452d9-43b7-5c29-aa7b-c85680fa45c6", ... }
```
