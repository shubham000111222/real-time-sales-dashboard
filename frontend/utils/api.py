"""
API client — thin wrapper around the FastAPI backend
"""
import os
import requests
from typing import Optional

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def _get(path: str, params: dict | None = None) -> dict | list:
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def get_kpis(days: int = 30) -> dict:
    return _get("/sales/kpis", {"days": days})  # type: ignore


def get_trends(days: int = 90, granularity: str = "day",
               region: Optional[str] = None, category: Optional[str] = None) -> list:
    params = {"days": days, "granularity": granularity}
    if region:   params["region"]   = region
    if category: params["category"] = category
    return _get("/sales/trends", params)  # type: ignore


def get_regions(days: int = 90) -> list:
    return _get("/sales/regions", {"days": days})  # type: ignore


def get_top_products(days: int = 90, limit: int = 10,
                     category: Optional[str] = None) -> list:
    params = {"days": days, "limit": limit}
    if category: params["category"] = category
    return _get("/sales/top-products", params)  # type: ignore


def get_forecast(model: str = "prophet", horizon: int = 30) -> dict:
    return _get(f"/forecast/{model}", {"horizon": horizon})  # type: ignore


def get_export_url(days: int = 90, region: str | None = None,
                   category: str | None = None) -> str:
    base = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    params = [f"days={days}"]
    if region:   params.append(f"region={region}")
    if category: params.append(f"category={category}")
    return f"{base}/sales/export?{'&'.join(params)}"
