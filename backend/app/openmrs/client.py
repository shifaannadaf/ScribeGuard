"""
Shared HTTP client for all OpenMRS FHIR R4 requests.

- Handles Basic Auth header building
- Sets correct Content-Type for normal vs JSON-Patch requests
- Single place to swap in OAuth or API key auth later
"""

import base64
import json
import logging
from typing import Any, Optional

import httpx
from .config import FHIR_SERVER, FHIR_USER, FHIR_PASS

logger = logging.getLogger(__name__)

# OpenMRS REST API base URL (not FHIR)
REST_BASE = FHIR_SERVER.replace("/ws/fhir2/R4", "/ws/rest/v1")


def _auth_header() -> str:
    token = base64.b64encode(f"{FHIR_USER}:{FHIR_PASS}".encode()).decode()
    return f"Basic {token}"


def _headers(patch: bool = False) -> dict:
    return {
        "Authorization": _auth_header(),
        "Content-Type":  "application/json-patch+json" if patch else "application/fhir+json",
        "Accept":        "application/fhir+json",
    }


def _url(path: str) -> str:
    """Build full URL from a relative FHIR path."""
    return f"{FHIR_SERVER}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Public helpers — used by every resource module
# ---------------------------------------------------------------------------

def fhir_get(path: str, params: Optional[dict] = None) -> dict:
    """GET {FHIR_SERVER}/{path}"""
    with httpx.Client(headers=_headers(), timeout=30.0) as c:
        resp = c.get(_url(path), params=params or {})
        resp.raise_for_status()
    logger.debug("GET %s → %s", path, resp.status_code)
    return resp.json()


def fhir_post(path: str, payload: dict) -> dict:
    """POST {FHIR_SERVER}/{path}  with application/fhir+json body"""
    with httpx.Client(headers=_headers(), timeout=30.0) as c:
        resp = c.post(_url(path), json=payload)
        if not resp.is_success:
            logger.error("POST %s failed with %s: %s", path, resp.status_code, resp.text)
        resp.raise_for_status()
    logger.debug("POST %s → %s", path, resp.status_code)
    return resp.json()


def fhir_patch(path: str, json_patch: list[dict]) -> dict:
    """PATCH {FHIR_SERVER}/{path}  with application/json-patch+json body (RFC 6902)"""
    with httpx.Client(headers=_headers(patch=True), timeout=30.0) as c:
        resp = c.patch(_url(path), content=json.dumps(json_patch))
        resp.raise_for_status()
    logger.debug("PATCH %s → %s", path, resp.status_code)
    return resp.json()


def fhir_put(path: str, payload: dict) -> dict:
    """PUT {FHIR_SERVER}/{path}  full resource replacement"""
    with httpx.Client(headers=_headers(), timeout=30.0) as c:
        resp = c.put(_url(path), json=payload)
        resp.raise_for_status()
    logger.debug("PUT %s → %s", path, resp.status_code)
    return resp.json()


def fhir_delete(path: str) -> bool:
    """DELETE {FHIR_SERVER}/{path}  — returns True on success"""
    with httpx.Client(headers=_headers(), timeout=30.0) as c:
        resp = c.delete(_url(path))
        resp.raise_for_status()
    logger.debug("DELETE %s → %s", path, resp.status_code)
    return True


# ---------------------------------------------------------------------------
# OpenMRS REST API helpers (non-FHIR)
# ---------------------------------------------------------------------------

def rest_get(path: str, params: Optional[dict] = None) -> dict:
    """GET OpenMRS REST API endpoint (not FHIR)"""
    url = f"{REST_BASE}/{path.lstrip('/')}"
    with httpx.Client(headers=_headers(), timeout=30.0) as c:
        resp = c.get(url, params=params or {})
        resp.raise_for_status()
    logger.debug("REST GET %s → %s", path, resp.status_code)
    return resp.json()


def rest_post(path: str, payload: dict) -> dict:
    """POST OpenMRS REST API endpoint (not FHIR)"""
    url = f"{REST_BASE}/{path.lstrip('/')}"
    with httpx.Client(headers=_headers(), timeout=30.0) as c:
        resp = c.post(url, json=payload)
        if not resp.is_success:
            logger.error("REST POST %s failed with %s: %s", path, resp.status_code, resp.text)
        resp.raise_for_status()
    logger.debug("REST POST %s → %s", path, resp.status_code)
    return resp.json()