"""CRM service implementations and encryption helpers for Phase 2.6A."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.models.crm import CrmConnection, CrmProvider, CrmSyncLog

logger = logging.getLogger(__name__)

_DEFAULT_FIELD_MAPS: Dict[str, Dict[str, str]] = {
    "hubspot": {
        "name": "firstname",
        "email": "email",
        "company": "company",
        "title": "jobtitle",
        "linkedin_url": "linkedinbio",
        "location": "city",
        "propensity_score": "hs_lead_status",
    },
    "pipedrive": {
        "name": "name",
        "email": "email",
        "company": "org_name",
        "title": "job_title",
        "phone": "phone",
    },
    "salesforce": {
        "name": "FirstName",
        "email": "Email",
        "company": "Company",
        "title": "Title",
        "phone": "Phone",
        "location": "City",
    },
    "custom": {},
}


def _get_fernet() -> Fernet:
    """Derive a deterministic Fernet key from SECRET_KEY."""

    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)



def encrypt_credentials(credentials: Dict[str, str]) -> str:
    """Encrypt a CRM credentials dictionary."""

    return _get_fernet().encrypt(json.dumps(credentials).encode()).decode()



def decrypt_credentials(ciphertext: str) -> Dict[str, str]:
    """Decrypt a CRM credentials dictionary."""

    try:
        return json.loads(_get_fernet().decrypt(ciphertext.encode()).decode())
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("CRM credentials decryption failed") from exc


class HubSpotClient:
    """HubSpot Contacts API client."""

    BASE = "https://api.hubapi.com/crm/v3/objects/contacts"

    def __init__(self, api_key: str):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def upsert_contact(
        self, properties: Dict[str, Any], email: Optional[str]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            if email:
                search_response = await client.post(
                    f"{self.BASE}/search",
                    headers=self._headers,
                    json={
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }]
                        }],
                        "properties": ["email"],
                        "limit": 1,
                    },
                )
                results = search_response.json().get("results", [])
                if results:
                    contact_id = results[0]["id"]
                    response = await client.patch(
                        f"{self.BASE}/{contact_id}",
                        headers=self._headers,
                        json={"properties": properties},
                    )
                    return {
                        "action": "updated",
                        "id": contact_id,
                        "status": response.status_code,
                    }

            response = await client.post(
                self.BASE,
                headers=self._headers,
                json={"properties": properties},
            )
            return {
                "action": "created",
                "id": response.json().get("id"),
                "status": response.status_code,
            }


class PipedriveClient:
    """Pipedrive persons API client."""

    BASE = "https://api.pipedrive.com/v1"

    def __init__(self, api_token: str):
        self._params = {"api_token": api_token}

    async def upsert_person(
        self, data: Dict[str, Any], email: Optional[str]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            if email:
                search_response = await client.get(
                    f"{self.BASE}/persons/search",
                    params={
                        **self._params,
                        "term": email,
                        "fields": "email",
                        "limit": 1,
                    },
                )
                items = search_response.json().get("data", {}).get("items", [])
                if items:
                    person_id = items[0]["item"]["id"]
                    response = await client.put(
                        f"{self.BASE}/persons/{person_id}",
                        params=self._params,
                        json=data,
                    )
                    return {
                        "action": "updated",
                        "id": person_id,
                        "status": response.status_code,
                    }

            response = await client.post(
                f"{self.BASE}/persons", params=self._params, json=data
            )
            return {
                "action": "created",
                "id": response.json().get("data", {}).get("id"),
                "status": response.status_code,
            }


class SalesforceClient:
    """Salesforce REST lead client."""

    def __init__(self, instance_url: str, access_token: str):
        self._base = f"{instance_url}/services/data/v57.0"
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def upsert_lead(
        self, data: Dict[str, Any], email: Optional[str]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            if email:
                soql = f"SELECT Id FROM Lead WHERE Email = '{email}' LIMIT 1"
                query_response = await client.get(
                    f"{self._base}/query", headers=self._headers, params={"q": soql}
                )
                records = query_response.json().get("records", [])
                if records:
                    lead_id = records[0]["Id"]
                    response = await client.patch(
                        f"{self._base}/sobjects/Lead/{lead_id}",
                        headers=self._headers,
                        json=data,
                    )
                    return {
                        "action": "updated",
                        "id": lead_id,
                        "status": response.status_code,
                    }

            response = await client.post(
                f"{self._base}/sobjects/Lead",
                headers=self._headers,
                json=data,
            )
            return {
                "action": "created",
                "id": response.json().get("id"),
                "status": response.status_code,
            }


class CustomWebhookClient:
    """Generic webhook CRM target."""

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self._url = webhook_url
        self._secret = secret

    async def push(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        import hmac

        headers = {"Content-Type": "application/json"}
        if self._secret:
            signature = hmac.new(
                self._secret.encode(),
                json.dumps(payload).encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self._url, json=payload, headers=headers)
            return {"action": "pushed", "status": response.status_code}


class CrmService:
    """Service for CRM validation and lead synchronization."""

    def _apply_field_map(
        self, lead: Any, field_map: Dict[str, str], provider: str
    ) -> Dict[str, Any]:
        effective_map = {**_DEFAULT_FIELD_MAPS.get(provider, {}), **field_map}
        raw_values = {
            "name": lead.name or "",
            "email": lead.email or "",
            "company": lead.company or "",
            "title": lead.title or "",
            "phone": lead.phone or "",
            "location": lead.location or "",
            "linkedin_url": lead.linkedin_url or "",
            "propensity_score": str(lead.propensity_score or 0),
            "priority_tier": lead.priority_tier or "",
            "status": lead.status or "NEW",
        }
        return {
            crm_field: raw_values[source_field]
            for source_field, crm_field in effective_map.items()
            if crm_field and source_field in raw_values
        }

    async def test_connection(self, connection: CrmConnection) -> Dict[str, Any]:
        """Validate a CRM connection with a lightweight probe."""

        try:
            credentials = decrypt_credentials(connection.credentials_encrypted)
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}

        try:
            if connection.provider == CrmProvider.HUBSPOT:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(
                        "https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
                        headers={
                            "Authorization": (
                                f"Bearer {credentials.get('api_key', '')}"
                            )
                        },
                    )
                return {"ok": response.status_code < 400, "message": f"HTTP {response.status_code}"}

            if connection.provider == CrmProvider.PIPEDRIVE:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(
                        "https://api.pipedrive.com/v1/persons?limit=1",
                        params={"api_token": credentials.get("api_token", "")},
                    )
                return {"ok": response.status_code < 400, "message": f"HTTP {response.status_code}"}

            if connection.provider == CrmProvider.SALESFORCE:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(
                        f"{credentials.get('instance_url', '')}/services/data/v57.0/limits",
                        headers={
                            "Authorization": (
                                f"Bearer {credentials.get('access_token', '')}"
                            )
                        },
                    )
                return {"ok": response.status_code < 400, "message": f"HTTP {response.status_code}"}

            if connection.provider == CrmProvider.CUSTOM:
                return {
                    "ok": bool(credentials.get("webhook_url")),
                    "message": "URL present",
                }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

        return {"ok": False, "message": "Unknown provider"}

    async def sync_leads(
        self,
        connection: CrmConnection,
        leads: List[Any],
        db: Any,
        dry_run: bool = False,
    ) -> CrmSyncLog:
        """Push leads to the CRM and record an audit log."""

        log = CrmSyncLog(
            connection_id=connection.id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()

        if dry_run:
            log.status = "dry_run"
            log.leads_pushed = len(leads)
            log.finished_at = datetime.now(timezone.utc)
            connection.last_sync_at = log.finished_at
            connection.last_sync_status = "dry_run"
            await db.commit()
            return log

        try:
            credentials = decrypt_credentials(connection.credentials_encrypted)
        except ValueError as exc:
            log.status = "failed"
            log.error_detail = str(exc)
            log.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return log

        pushed = 0
        updated = 0
        failed = 0

        for lead in leads:
            mapped = self._apply_field_map(
                lead,
                connection.field_map or {},
                connection.provider.value,
            )
            try:
                if connection.provider == CrmProvider.HUBSPOT:
                    result = await HubSpotClient(credentials["api_key"]).upsert_contact(
                        mapped, lead.email
                    )
                elif connection.provider == CrmProvider.PIPEDRIVE:
                    result = await PipedriveClient(
                        credentials["api_token"]
                    ).upsert_person(mapped, lead.email)
                elif connection.provider == CrmProvider.SALESFORCE:
                    result = await SalesforceClient(
                        credentials["instance_url"], credentials["access_token"]
                    ).upsert_lead(mapped, lead.email)
                elif connection.provider == CrmProvider.CUSTOM:
                    result = await CustomWebhookClient(
                        credentials["webhook_url"], credentials.get("secret")
                    ).push({"lead": mapped})
                else:
                    continue

                if result.get("action") == "updated":
                    updated += 1
                else:
                    pushed += 1
            except Exception as exc:
                failed += 1
                logger.warning("CRM sync failed for lead %s: %s", lead.id, exc)

        log.leads_pushed = pushed
        log.leads_updated = updated
        log.leads_failed = failed
        log.status = (
            "success"
            if failed == 0
            else "partial"
            if pushed + updated > 0
            else "failed"
        )
        log.finished_at = datetime.now(timezone.utc)
        connection.last_sync_at = log.finished_at
        connection.last_sync_status = log.status
        connection.total_synced_leads += pushed + updated

        await db.commit()
        return log


_crm_service: Optional[CrmService] = None


def get_crm_service() -> CrmService:
    """Return a singleton CRM service instance."""

    global _crm_service
    if _crm_service is None:
        _crm_service = CrmService()
    return _crm_service
