import json
import logging
from typing import Any, Dict, List, Tuple

import requests

from .base import DocumentProvider, DocumentSummary, SourceDocument

logger = logging.getLogger("python_dms.paperless")


class PaperlessAPIError(Exception):
    """Raised when the Paperless-ngx API returns an unexpected response."""

API_VERSION = 10

# Document fields requested from the list endpoint. Restricting the response via
# the ``fields`` parameter keeps payloads small for large libraries.
_DOCUMENT_FIELDS = (
    "id,title,content,correspondent,tags,document_type,storage_path,"
    "created,modified,custom_fields,checksum"
)

# Lightweight fields for change detection: no content is transferred.
_SUMMARY_FIELDS = "id,checksum,modified"


class PaperlessDocumentProvider(DocumentProvider):
    """Document provider backed by the Paperless-ngx REST API.

    Encapsulates document fetching, metadata enrichment (ids -> names), hashing
    and change detection so the ingestion service does not need to know the
    concrete data source. Documents are returned with their extracted text
    content (``content``) and fully resolved metadata in ``SourceDocument.metadata``.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = self._get_str(
            config,
            ("url", "document_provider_url", "paperless_api_url"),
        )
        self.token = self._get_str(
            config,
            ("token", "document_provider_token", "paperless_api_token"),
        )

        if not self.base_url or not self.token:
            raise ValueError("Missing document provider configuration (url/token)")

    @staticmethod
    def _get_str(config: Dict[str, Any], keys: Tuple[str, ...]) -> str:
        """Return the first non-empty config value as a plain string."""
        for key in keys:
            value = config.get(key)
            if value:
                return str(value)
        return ""

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.token}",
            "Accept": f"application/json; version={API_VERSION}",
        }

    def _get(self, url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Perform a GET request and return the parsed JSON body."""
        response = requests.get(url, headers=self._headers(), params=params, timeout=30)
        if response.status_code != 200:
            raise PaperlessAPIError(f"API error: {response.status_code}")
        return response.json()

    def _fetch_all(self, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch all pages of a paginated list endpoint."""
        items: List[Dict[str, Any]] = []
        page_params = dict(params)
        while url:
            data = self._get(url, params=page_params)
            items.extend(data.get("results", []))
            next_url = data.get("next")
            # ``next`` carries its own query params; mypy sees Optional[Any].
            url = next_url if isinstance(next_url, str) else ""
            page_params = {}
        return items

    def _build_lookup(self, endpoint: str) -> Dict[Any, Any]:
        """Build an id -> name mapping from a list endpoint.

        Returns an empty mapping on failure so a single broken lookup does not
        abort the whole ingestion run.
        """
        try:
            items = self._fetch_all(
                f"{self.base_url}/api/{endpoint}/", {"page_size": 100}
            )
            return {item["id"]: item.get("name", "") for item in items}
        except Exception as e:
            logger.warning(f"Could not build lookup for {endpoint}: {str(e)}")
            return {}

    def _build_custom_fields_lookup(self) -> Dict[Any, Dict[str, str]]:
        """Build an id -> {name, data_type} mapping for custom fields."""
        try:
            items = self._fetch_all(
                f"{self.base_url}/api/custom_fields/", {"page_size": 100}
            )
            return {
                item["id"]: {
                    "name": item.get("name", ""),
                    "data_type": item.get("data_type", ""),
                }
                for item in items
            }
        except Exception as e:
            logger.warning(f"Could not build lookup for custom_fields: {str(e)}")
            return {}

    def check_for_updates(self) -> Tuple[bool, str]:
        logger.info("Checking for document updates")
        try:
            url = f"{self.base_url}/api/documents/?page=1&page_size=10"
            response = requests.get(url, headers=self._headers(), timeout=10)

            if response.status_code != 200:
                return False, f"API error: {response.status_code}"

            data = response.json()
            results = data.get("results", [])

            if not results:
                return False, "No documents found"

            return True, f"Latest document: {results[0].get('id')}"
        except Exception as e:
            logger.exception("Error checking for updates")
            return False, f"Error: {str(e)}"

    def fetch_documents(self) -> List[SourceDocument]:
        logger.info(f"Fetching documents from Paperless-ngx: {self.base_url}")

        lookups: Dict[str, Dict[Any, Any]] = {
            "correspondent": self._build_lookup("correspondents"),
            "tags": self._build_lookup("tags"),
            "document_type": self._build_lookup("document_types"),
            "storage_path": self._build_lookup("storage_paths"),
        }
        custom_fields_lookup = self._build_custom_fields_lookup()

        raw_documents = self._fetch_all(
            f"{self.base_url}/api/documents/",
            {"fields": _DOCUMENT_FIELDS, "page_size": 100},
        )

        processed: List[SourceDocument] = []
        for doc in raw_documents:
            correspondent = self._resolve_name(
                lookups["correspondent"], doc.get("correspondent")
            )
            document_type = self._resolve_name(
                lookups["document_type"], doc.get("document_type")
            )
            storage_path = self._resolve_name(
                lookups["storage_path"], doc.get("storage_path")
            )
            tags = self._resolve_tags(lookups["tags"], doc.get("tags", []))
            content = doc.get("content") or ""

            metadata = {
                "document_type": document_type,
                "storage_path": storage_path,
                **self._normalize_custom_fields(
                    doc.get("custom_fields", []), custom_fields_lookup
                ),
            }

            processed.append(
                SourceDocument(
                    id=str(doc["id"]),
                    title=doc.get("title", ""),
                    content=content,
                    correspondent=correspondent,
                    document_type=document_type,
                    storage_path=storage_path,
                    created=doc.get("created", ""),
                    tags=tags,
                    last_updated=doc.get("modified", ""),
                    hash=doc.get("checksum")
                    or self.compute_hash(
                        {
                            "title": doc.get("title", ""),
                            "content": content,
                            "correspondent": correspondent,
                        }
                    ),
                    metadata=metadata,
                )
            )

        return processed

    def fetch_document_content(self, doc_id: str) -> str:
        """Return the extracted text content of a single document.

        Paperless-ngx already performs OCR/text extraction, so the content is
        served directly from the document detail endpoint.
        """
        try:
            data = self._get(
                f"{self.base_url}/api/documents/{doc_id}/", {"fields": "content"}
            )
            return data.get("content") or ""
        except Exception as e:
            logger.warning(f"Could not fetch content for document {doc_id}: {str(e)}")
            return ""

    def fetch_document_summaries(self) -> List[DocumentSummary]:
        """Fetch lightweight summaries (id, checksum, modified) for change detection.

        Uses the ``fields`` parameter so only the three diff-relevant fields are
        transferred — no document content, so this scales well even for large
        libraries and frequent polling.
        """
        logger.info(f"Fetching document summaries from Paperless-ngx: {self.base_url}")
        raw_summaries = self._fetch_all(
            f"{self.base_url}/api/documents/",
            {"fields": _SUMMARY_FIELDS, "page_size": 200, "ordering": "id"},
        )
        return [
            DocumentSummary(
                id=str(doc["id"]),
                checksum=doc.get("checksum", ""),
                modified=doc.get("modified", ""),
            )
            for doc in raw_summaries
        ]

    @staticmethod
    def _resolve_name(lookup: Dict[Any, Any], value: Any) -> str:
        if value is None:
            return ""
        return lookup.get(value, "")

    @staticmethod
    def _resolve_tags(lookup: Dict[Any, Any], tag_ids: List[Any]) -> List[str]:
        tags = [lookup.get(tag_id, "") for tag_id in tag_ids]
        return [tag for tag in tags if tag]

    @staticmethod
    def _normalize_custom_fields(
        custom_fields: List[Dict[str, Any]], lookup: Dict[Any, Dict[str, str]]
    ) -> Dict[str, Any]:
        """Flatten custom field instances into a ``custom_fields.<name>`` dict.

        Scalar values (str/int/float/bool) are passed through directly; list and
        dict values (document links, select options) are serialized to JSON so
        the resulting metadata stays flat and filterable by the vector database.
        """
        normalized: Dict[str, Any] = {}
        for instance in custom_fields or []:
            field_id = instance.get("field")
            field_info = lookup.get(field_id, {})
            name = field_info.get("name") or f"id_{field_id}"
            value = instance.get("value")

            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)

            normalized[f"custom_fields.{name}"] = value

        return normalized
