import os
from typing import Optional


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read an environment variable, returning the default when unset or empty."""
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value