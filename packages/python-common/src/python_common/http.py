"""Lightweight HTTP helpers for pipeline-to-pipeline communication.

Replaces the former RabbitMQ messaging layer: pipelines now talk to each
other (and to the backend) over plain HTTP REST.
"""

import logging
from typing import Any, Dict, cast

import httpx

logger = logging.getLogger("python_common.http")


async def post_json(
    url: str,
    payload: Dict[str, Any],
    timeout: float = 30.0,
) -> Dict[str, Any] | None:
    """POST a JSON payload and return the parsed JSON response.

    Returns ``None`` on failure (logged) so callers can treat the call as
    fire-and-forget without raising.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                return None
            return cast(Dict[str, Any], data)
    except Exception:
        logger.exception(f"HTTP POST to {url} failed")
        return None
