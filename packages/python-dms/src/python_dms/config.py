import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class DMSConfig:
    """Configuration for the document management system source.

    Fully determined by environment variables; loaded by load_dms_config().
    """

    document_provider: str
    document_provider_url: str | None = None
    document_provider_token: str | None = None

    def to_document_provider_config(self) -> Dict[str, Any]:
        """Build the dict expected by DocumentProviderFactory."""
        return {
            "type": self.document_provider,
            "url": self.document_provider_url,
            "token": self.document_provider_token,
        }


def load_dms_config() -> DMSConfig:
    """Load document source configuration from environment variables.

    DOCUMENT_PROVIDER_URL/TOKEN take precedence, with PAPERLESS_API_URL/TOKEN as
    backward-compatible fallbacks.
    """
    return DMSConfig(
        document_provider=os.getenv("DOCUMENT_PROVIDER", "paperless"),
        document_provider_url=os.getenv(
            "DOCUMENT_PROVIDER_URL", os.getenv("PAPERLESS_API_URL")
        ),
        document_provider_token=os.getenv(
            "DOCUMENT_PROVIDER_TOKEN", os.getenv("PAPERLESS_API_TOKEN")
        ),
    )
