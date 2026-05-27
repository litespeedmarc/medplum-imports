import os
import requests
from .exceptions import ImportVerificationError


MEDPLUM_BASE_URL = os.getenv("MEDPLUM_BASE_URL", "http://localhost:8103")
MEDPLUM_EMAIL    = os.getenv("MEDPLUM_EMAIL",    "admin@example.com")
MEDPLUM_PASSWORD = os.getenv("MEDPLUM_PASSWORD", "medplum_admin")

# RFC 7636 test vectors — safe for local dev
_CODE_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
_CODE_VERIFIER  = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"


class MedplumClient:
    def __init__(self):
        self._token: str | None = None

    def _authenticate(self) -> str:
        login = requests.post(f"{MEDPLUM_BASE_URL}/auth/login", json={
            "email": MEDPLUM_EMAIL,
            "password": MEDPLUM_PASSWORD,
            "codeChallenge": _CODE_CHALLENGE,
            "codeChallengeMethod": "S256",
        })
        login.raise_for_status()
        code = login.json()["code"]

        token_resp = requests.post(f"{MEDPLUM_BASE_URL}/oauth2/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": _CODE_VERIFIER,
        })
        token_resp.raise_for_status()
        return token_resp.json()["access_token"]

    @property
    def token(self) -> str:
        if not self._token:
            self._token = self._authenticate()
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/fhir+json",
        }

    def post_bundle(self, bundle: dict) -> dict:
        resp = requests.post(
            f"{MEDPLUM_BASE_URL}/fhir/R4",
            json=bundle,
            headers=self._headers(),
        )
        if resp.status_code == 401:
            self._token = None
            resp = requests.post(
                f"{MEDPLUM_BASE_URL}/fhir/R4",
                json=bundle,
                headers=self._headers(),
            )
        resp.raise_for_status()
        return resp.json()

    def search(self, resource_type: str, params: dict) -> dict:
        resp = requests.get(
            f"{MEDPLUM_BASE_URL}/fhir/R4/{resource_type}",
            params=params,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get(self, resource_type: str, resource_id: str) -> dict:
        resp = requests.get(
            f"{MEDPLUM_BASE_URL}/fhir/R4/{resource_type}/{resource_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()
