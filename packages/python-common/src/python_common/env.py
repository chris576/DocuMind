import os


def get_env(key: str, default: str | None = None) -> str | None:
    """Read an environment variable, returning the default when unset or empty."""
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value
