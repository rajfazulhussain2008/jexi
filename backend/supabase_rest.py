"""
supabase_rest.py — HTTP-based database client using Supabase's PostgREST API.
This bypasses psycopg2 entirely and works perfectly on Vercel serverless functions.
Uses only httpx (already in requirements.txt).
"""
import os
import httpx
from urllib.parse import quote

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

def _headers():
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def sb_select(table: str, filters: dict = None, columns: str = "*", query_string: str = None) -> list:
    """Select rows from a table with optional equality filters or raw query."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={columns}"
    if filters:
        for key, value in filters.items():
            url += f"&{key}=eq.{quote(str(value))}"
    if query_string:
        # If the user provides a raw string, we assume they know what they are doing
        # but we'll append it carefully.
        url += f"&{query_string}"
    
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, headers=_headers())
        resp.raise_for_status()
        return resp.json()


def sb_insert(table: str, data: dict) -> dict:
    """Insert a row and return the created record."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    with httpx.Client(timeout=10) as client:
        resp = client.post(url, json=data, headers=_headers())
        resp.raise_for_status()
        result = resp.json()
        return result[0] if isinstance(result, list) and result else {}


def sb_update(table: str, filter_col: str, filter_val, data: dict) -> dict:
    """Update rows where filter_col = filter_val."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filter_col}=eq.{quote(str(filter_val))}"
    with httpx.Client(timeout=10) as client:
        resp = client.patch(url, json=data, headers=_headers())
        resp.raise_for_status()
        result = resp.json()
        return result[0] if isinstance(result, list) and result else {}

def sb_delete(table: str, filter_col: str, filter_val) -> None:
    """Delete rows where filter_col = filter_val."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filter_col}=eq.{quote(str(filter_val))}"
    with httpx.Client(timeout=10) as client:
        resp = client.delete(url, headers=_headers())
        resp.raise_for_status()


def sb_count(table: str, filters: dict = None, query_string: str = None) -> int:
    """Count rows in a table with optional filters."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=id"
    if filters:
        for key, value in filters.items():
            url += f"&{key}=eq.{quote(str(value))}"
    if query_string:
        # IMPORTANT: For the brute force timestamp check, we must ensure + is encoded
        # We manually check if we need to encode specific parts if passed as string
        url += f"&{query_string.replace('+', '%2B')}"
        
    headers = {**_headers(), "Prefer": "count=exact"}
    with httpx.Client(timeout=10) as client:
        # Use HEAD request to get just the count via headers
        resp = client.head(url, headers=headers)
        resp.raise_for_status()
        content_range = resp.headers.get("content-range", "0-0/0")
        try:
            return int(content_range.split("/")[-1])
        except Exception:
            return 0
