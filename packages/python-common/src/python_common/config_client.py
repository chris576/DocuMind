"""Fetch config slices from the DocuMind gateway (Admin-Panel configuration).

Pipelines still read environment variables as a fallback. When a gateway is
reachable, its config overrides the env values — this keeps a cold-start
working without a gateway while allowing panel-driven configuration.
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("python_common.config_client")

DEFAULT_GATEWAY_URL = "http://localhost:3001"


def gateway_url() -> str:
    """Return the gateway base URL (env GATEWAY_URL, trailing slash removed)."""
    return os.getenv("GATEWAY_URL", DEFAULT_GATEWAY_URL).rstrip("/")


async def fetch_config_slice(slice_name: str) -> Optional[Dict[str, Any]]:
    """Fetch a resolved config slice from the gateway, or None on failure.

    Slices are resolved by the gateway (secret env references are filled in)
    and use the same snake_case shape the pipeline config dataclasses expect.
    """
    url = f"{gateway_url()}/api/config/slice/{slice_name}"
    token = os.getenv("GATEWAY_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                return None
            return data
    except Exception as e:  # noqa: BLE001 — config fetch is best-effort
        logger.info(f"Gateway config slice '{slice_name}' unavailable: {e}")
        return None
