import os
import time
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

    def post_bundle_async(self, bundle: dict) -> tuple[str, str]:
        """
        POST a bundle with Prefer: respond-async.
        Returns (job_id, job_url) immediately — does not wait for completion.
        job_url shape: /fhir/R4/job/{id}/status (confirmed against live instance)
        """
        headers = {**self._headers(), "Prefer": "respond-async"}
        resp = requests.post(f"{MEDPLUM_BASE_URL}/fhir/R4", json=bundle, headers=headers)
        if resp.status_code == 401:
            self._token = None
            headers = {**self._headers(), "Prefer": "respond-async"}
            resp = requests.post(f"{MEDPLUM_BASE_URL}/fhir/R4", json=bundle, headers=headers)
        resp.raise_for_status()

        job_url = resp.headers.get("Content-Location")
        if not job_url:
            raise RuntimeError("Medplum returned 202 but no Content-Location header")
        job_id = job_url.split("/job/")[1].split("/")[0]
        return job_id, job_url

    def get_job_status(self, job_url: str) -> dict:
        """Poll an AsyncJob status URL. Returns the AsyncJob resource."""
        resp = requests.get(job_url, headers=self._headers())
        if resp.status_code == 401:
            self._token = None
            resp = requests.get(job_url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def wait_for_job(self, job_url: str, poll_interval: int = 2, timeout: int = 300) -> dict:
        """
        Poll job_url until status is completed or error.
        Returns the final AsyncJob resource.
        Raises RuntimeError on timeout or Medplum-reported error.
        """
        deadline = time.time() + timeout
        interval = poll_interval
        while time.time() < deadline:
            job = self.get_job_status(job_url)
            status = job.get("status")
            if status == "completed":
                return job
            if status == "error":
                issues = (job.get("output", {})
                             .get("parameter", [{}])[0]
                             .get("resource", {})
                             .get("issue", [{}]))
                detail = issues[0].get("diagnostics", "unknown error")
                raise RuntimeError(f"AsyncJob failed: {detail}")
            print(f"[runner] job status: {status} — waiting {interval}s")
            time.sleep(interval)
            interval = min(interval * 2, 30)  # exponential backoff, cap at 30s
        raise RuntimeError(f"AsyncJob timed out after {timeout}s: {job_url}")

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
