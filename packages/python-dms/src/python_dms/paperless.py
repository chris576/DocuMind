import logging
from typing import Any, Dict, List, Optional

import requests

from .base import DocumentProvider, SourceDocument

logger = logging.getLogger("python_dms.paperless")


class PaperlessDocumentProvider(DocumentProvider):
    """Document provider backed by the Paperless-ngx REST API.

    Encapsulates document fetching, content download, metadata enrichment,
    hashing and change detection so the ingestion service does not need to know
    the concrete data source.
    """

    def __init__(self, config: Dict[str, Any]):
        self.base_url = (
            config.get("url")
            or config.get("document_provider_url")
            or config.get("paperless_api_url")
        )
        self.token = (
            config.get("token")
            or config.get("document_provider_token")
            or config.get("paperless_api_token")
        )

        if not self.base_url or not self.token:
            raise ValueError("Missing document provider configuration (url/token)")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.token}"}

    def check_for_updates(self):
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
            logger.error(f"Error checking for updates: {str(e)}")
            return False, f"Error: {str(e)}"

    def fetch_documents(self) -> List[SourceDocument]:
        logger.info(f"Fetching documents from Paperless-ngx: {self.base_url}")

        raw_documents: List[Dict[str, Any]] = []
        page = 1
        has_next = True

        while has_next:
            logger.info(f"Fetching page {page}")
            url = f"{self.base_url}/api/documents/?page={page}&page_size=100"

            try:
                response = requests.get(url, headers=self._headers(), timeout=30)

                if response.status_code != 200:
                    raise Exception(f"API error: {response.status_code}")

                data = response.json()
                results = data.get("results", [])
                raw_documents.extend(results)

                if data.get("next"):
                    page += 1
                else:
                    has_next = False
            except Exception as e:
                logger.error(f"Error fetching documents: {str(e)}")
                raise

        processed: List[SourceDocument] = []
        for doc in raw_documents:
            content = self.fetch_document_content(str(doc["id"]))
            correspondent = self._fetch_correspondent(doc.get("correspondent"))
            tags = self._fetch_tags(doc.get("tags", []))

            processed.append(
                SourceDocument(
                    id=str(doc["id"]),
                    title=doc.get("title", ""),
                    content=content,
                    correspondent=correspondent,
                    created=doc.get("created_date", doc.get("created", "")),
                    tags=tags,
                    last_updated=doc.get("modified", ""),
                    hash=self.compute_hash(
                        {
                            "title": doc.get("title", ""),
                            "content": content,
                            "correspondent": correspondent,
                        }
                    ),
                )
            )

        return processed

    def fetch_document_content(self, doc_id: str) -> str:
        try:
            response = requests.get(
                f"{self.base_url}/api/documents/{doc_id}/download/txt/",
                headers=self._headers(),
                timeout=30,
            )
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.warning(f"Could not fetch content for document {doc_id}: {str(e)}")
        return ""

    def _fetch_correspondent(self, correspondent_id: Optional[str]) -> str:
        if not correspondent_id:
            return ""
        try:
            response = requests.get(
                f"{self.base_url}/api/correspondents/{correspondent_id}/",
                headers=self._headers(),
                timeout=10,
            )
            if response.status_code == 200:
                return response.json().get("name", "")
        except Exception as e:
            logger.warning(f"Could not fetch correspondent {correspondent_id}: {str(e)}")
        return ""

    def _fetch_tags(self, tag_ids: List[str]) -> List[str]:
        tags = []
        for tag_id in tag_ids:
            try:
                response = requests.get(
                    f"{self.base_url}/api/tags/{tag_id}/",
                    headers=self._headers(),
                    timeout=10,
                )
                if response.status_code == 200:
                    tags.append(response.json().get("name", ""))
            except Exception as e:
                logger.warning(f"Could not fetch tag {tag_id}: {str(e)}")
        return tags