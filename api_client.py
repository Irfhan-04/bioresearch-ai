"""
Thin HTTP client for calling the FastAPI backend from Streamlit.
All API calls go through this - never call requests directly in app.py.
"""

import os
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("API_URL", "https://your-backend.onrender.com/api/v1")

try:
    import streamlit as st

    secret_url = st.secrets.get("API_URL", None)
    if secret_url:
        API_BASE = secret_url
except Exception:
    pass


class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")


def _headers(token: Optional[str] = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raise(resp: requests.Response) -> requests.Response:
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise APIError(resp.status_code, detail)
    return resp


def _unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _extract_items(payload: Any) -> List[Any]:
    payload = _unwrap_data(payload)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return items
    return []


def login(email: str, password: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": password},
    )
    _raise(resp)
    return resp.json()


def register(email: str, password: str, full_name: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    _raise(resp)
    return resp.json()


def get_me(token: str) -> dict:
    resp = requests.get(f"{API_BASE}/users/me", headers=_headers(token))
    _raise(resp)
    return resp.json()


def get_lead(token: str, lead_id: str) -> dict:
    resp = requests.get(f"{API_BASE}/leads/{lead_id}", headers=_headers(token))
    _raise(resp)
    return resp.json()


def get_leads(
    token: str,
    page: int = 1,
    page_size: int = 50,
    min_score: int = 0,
    search: str = "",
) -> dict:
    params = {"skip": (page - 1) * page_size, "limit": page_size}
    if min_score:
        params["min_score"] = min_score
    if search:
        params["search"] = search
    resp = requests.get(f"{API_BASE}/leads", params=params, headers=_headers(token))
    _raise(resp)
    return resp.json()


def search_pubmed(token: str, query: str, max_results: int = 50) -> dict:
    resp = requests.post(
        f"{API_BASE}/search",
        json={"query": query, "source": "pubmed", "max_results": max_results},
        headers=_headers(token),
    )
    _raise(resp)
    return resp.json()


def export_leads(token: str, format: str = "csv", min_score: int = 0) -> bytes:
    resp = requests.post(
        f"{API_BASE}/export",
        json={"format": format, "filters": {"min_score": min_score}},
        headers=_headers(token),
    )
    _raise(resp)
    return resp.content


def get_usage_stats(token: str, days: int = 14) -> list:
    resp = requests.get(
        f"{API_BASE}/analytics/me/daily",
        params={"days": days},
        headers=_headers(token),
    )
    _raise(resp)

    rows = _extract_items(resp.json())
    daily_totals: Dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = row.get("date")
        if not day:
            continue

        count = row.get("leads_created")
        if count is None:
            event_type = str(row.get("event_type", "")).lower()
            if event_type == "lead_created":
                count = row.get("count", 0)
            else:
                count = 0

        daily_totals[day] = daily_totals.get(day, 0) + int(count or 0)

    return [{"date": day, "leads_created": total} for day, total in sorted(daily_totals.items())]


def get_pipeline(token: str, pipeline_id: str) -> dict:
    resp = requests.get(f"{API_BASE}/pipelines/{pipeline_id}", headers=_headers(token))
    _raise(resp)
    return resp.json()


def get_pipelines(token: str) -> list:
    resp = requests.get(f"{API_BASE}/pipelines", headers=_headers(token))
    _raise(resp)
    return _extract_items(resp.json())


def run_pipeline(
    token: str,
    pipeline_id: str,
    override_config: Optional[dict] = None,
) -> dict:
    payload = {"override_config": override_config} if override_config else None
    resp = requests.post(
        f"{API_BASE}/pipelines/{pipeline_id}/run",
        json=payload,
        headers=_headers(token),
    )
    _raise(resp)
    return _unwrap_data(resp.json())


def create_pipeline(
    token: str,
    name: str,
    query: str,
    schedule: str = "manual",
    description: Optional[str] = None,
    cron_expression: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> dict:
    pipeline_config: Dict[str, Any] = {
        "data_sources": ["pubmed"],
        "search_queries": [{"source": "pubmed", "query": query}],
    }
    if config:
        pipeline_config.update(config)
        pipeline_config.setdefault("search_queries", [{"source": "pubmed", "query": query}])
        pipeline_config.setdefault("data_sources", ["pubmed"])

    payload: Dict[str, Any] = {
        "name": name,
        "schedule": schedule,
        "config": pipeline_config,
    }
    if description is not None:
        payload["description"] = description
    if cron_expression is not None:
        payload["cron_expression"] = cron_expression

    resp = requests.post(
        f"{API_BASE}/pipelines",
        json=payload,
        headers=_headers(token),
    )
    _raise(resp)
    return resp.json()


def create_portal_session(token: str) -> str:
    resp = requests.post(f"{API_BASE}/billing/portal", headers=_headers(token))
    _raise(resp)
    data = _unwrap_data(resp.json())
    return data["portal_url"]


def refresh_token(refresh_tok: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/auth/refresh",
        json={"refresh_token": refresh_tok},
    )
    _raise(resp)
    return resp.json()


def get_score_stats(token: str) -> dict:
    resp = requests.get(f"{API_BASE}/scoring/stats", headers=_headers(token))
    _raise(resp)
    return resp.json()


def get_score_config(token: str) -> dict:
    resp = requests.get(f"{API_BASE}/scoring/config", headers=_headers(token))
    _raise(resp)
    config = resp.json()
    if isinstance(config, dict) and "weights" not in config:
        config = {
            **config,
            "weights": config.get("effective_weights")
            or config.get("default_weights")
            or config.get("user_overrides")
            or {},
        }
    return config


def update_score_weights(token: str, weights: Dict[str, float]) -> dict:
    resp = requests.put(
        f"{API_BASE}/scoring/config",
        json=weights,
        headers=_headers(token),
    )
    _raise(resp)
    return resp.json()


def rescore_all_leads(token: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/scoring/leads/all/recalculate",
        headers=_headers(token),
    )
    _raise(resp)
    return resp.json()


def get_billing_summary(token: str) -> dict:
    resp = requests.get(f"{API_BASE}/billing/summary", headers=_headers(token))
    _raise(resp)
    return resp.json()["data"]


def create_checkout_session(token: str, price_id: str) -> str:
    resp = requests.post(
        f"{API_BASE}/billing/checkout",
        json={"price_id": price_id},
        headers=_headers(token),
    )
    _raise(resp)
    return resp.json()["data"]["checkout_url"]


def is_quota_exceeded(error: APIError) -> bool:
    return error.status_code == 403 and (
        "limit" in error.detail.lower() or "quota" in error.detail.lower()
    )
