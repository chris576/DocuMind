"""Unit tests for the Paperless-ngx document provider (metadata + content).

Uses a mocked ``requests`` layer so no live Paperless instance is required.
"""
from unittest.mock import MagicMock, patch

from python_dms.base import SourceDocument
from python_dms.paperless import PaperlessDocumentProvider


def make_provider():
    return PaperlessDocumentProvider(
        {"url": "http://paperless.local", "token": "secret"}
    )


def _lookup_response(name):
    return {
        "results": [{"id": 1, "name": name}, {"id": 2, "name": f"{name}2"}],
        "next": None,
    }


@patch("python_dms.paperless.requests.get")
def test_fetch_documents_resolves_metadata(mock_get):
    def fake_get(url, headers=None, params=None, timeout=30):
        resp = MagicMock()
        resp.status_code = 200
        if "documents/" in url:
            resp.json.return_value = {
                "results": [
                    {
                        "id": 11,
                        "title": "Rechnung",
                        "content": "OCR-Text",
                        "correspondent": 1,
                        "tags": [1, 2],
                        "document_type": 1,
                        "storage_path": 2,
                        "created": "2024-03-01",
                        "modified": "2024-03-02T10:00:00Z",
                        "custom_fields": [
                            {"field": 7, "value": "ABC-123"},
                            {"field": 8, "value": [5, 6]},
                        ],
                        "checksum": "abc123",
                    }
                ],
                "next": None,
            }
        elif "correspondents" in url:
            resp.json.return_value = _lookup_response("Korrespondent")
        elif "tags/" in url:
            resp.json.return_value = _lookup_response("Tag")
        elif "document_types" in url:
            resp.json.return_value = _lookup_response("Rechnungstyp")
        elif "storage_paths" in url:
            resp.json.return_value = _lookup_response("Ordner")
        elif "custom_fields" in url:
            resp.json.return_value = {
                "results": [
                    {"id": 7, "name": "rechnungsnr", "data_type": "string"},
                    {"id": 8, "name": "verknuepfungen", "data_type": "documentlink"},
                ],
                "next": None,
            }
        else:
            raise AssertionError(f"Unexpected URL: {url}")
        return resp

    mock_get.side_effect = fake_get

    provider = make_provider()
    docs = provider.fetch_documents()

    assert len(docs) == 1
    doc = docs[0]
    assert isinstance(doc, SourceDocument)
    assert doc.id == "11"
    assert doc.content == "OCR-Text"
    assert doc.correspondent == "Korrespondent"
    assert doc.document_type == "Rechnungstyp"
    assert doc.storage_path == "Ordner2"
    assert doc.tags == ["Tag", "Tag2"]
    assert doc.hash == "abc123"
    assert doc.metadata["document_type"] == "Rechnungstyp"
    assert doc.metadata["storage_path"] == "Ordner2"
    assert doc.metadata["custom_fields.rechnungsnr"] == "ABC-123"
    assert doc.metadata["custom_fields.verknuepfungen"] == "[5, 6]"


@patch("python_dms.paperless.requests.get")
def test_fetch_documents_paginates(mock_get):
    page1 = MagicMock()
    page1.status_code = 200
    page1.json.return_value = {
        "results": [{"id": 1, "title": "a", "content": "x", "checksum": "c1"}],
        "next": "http://paperless.local/api/documents/?page=2",
    }
    page2 = MagicMock()
    page2.status_code = 200
    page2.json.return_value = {
        "results": [{"id": 2, "title": "b", "content": "y", "checksum": "c2"}],
        "next": None,
    }

    def fake_get(url, headers=None, params=None, timeout=30):
        resp = MagicMock()
        resp.status_code = 200
        if "documents/" in url:
            resp = page1 if "page=1" in url or "page_size" in (params or {}) else page2
        elif url.endswith("custom_fields/"):
            resp.json.return_value = {"results": [], "next": None}
        else:
            resp.json.return_value = {"results": [], "next": None}
        return resp

    mock_get.side_effect = fake_get

    provider = make_provider()
    docs = provider.fetch_documents()
    assert [d.id for d in docs] == ["1", "2"]


@patch("python_dms.paperless.requests.get")
def test_fetch_document_content_uses_detail_endpoint(mock_get):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"content": "volltext"}
    mock_get.return_value = resp

    provider = make_provider()
    assert provider.fetch_document_content("42") == "volltext"

    # Must hit the detail endpoint, never a /download/txt/ path.
    url = mock_get.call_args.args[0]
    assert url.endswith("/api/documents/42/")
    assert "download/txt" not in url


def test_normalize_custom_fields_falls_back_to_id():
    flat = PaperlessDocumentProvider._normalize_custom_fields(
        [{"field": 999, "value": "x"}], {}
    )
    assert flat == {"custom_fields.id_999": "x"}


@patch("python_dms.paperless.requests.get")
def test_check_for_updates_ok(mock_get):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [{"id": 5}],
        "next": None,
    }
    mock_get.return_value = resp

    provider = make_provider()
    assert provider.check_for_updates() == (True, "Latest document: 5")


@patch("python_dms.paperless.requests.get")
def test_check_for_updates_empty(mock_get):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": [], "next": None}
    mock_get.return_value = resp

    provider = make_provider()
    assert provider.check_for_updates() == (False, "No documents found")


@patch("python_dms.paperless.requests.get")
def test_check_for_updates_error_status(mock_get):
    resp = MagicMock()
    resp.status_code = 500
    mock_get.return_value = resp

    provider = make_provider()
    assert provider.check_for_updates() == (False, "API error: 500")


@patch("python_dms.paperless.requests.get")
def test_check_for_updates_exception(mock_get):
    mock_get.side_effect = Exception("connection refused")
    provider = make_provider()
    ok, msg = provider.check_for_updates()
    assert ok is False
    assert "connection refused" in msg


@patch("python_dms.paperless.requests.get")
def test_fetch_document_summaries(mock_get):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": [
            {"id": 1, "checksum": "aaa", "modified": "2024-01-01T00:00:00Z"},
            {"id": 2, "checksum": "bbb", "modified": "2024-01-02T00:00:00Z"},
        ],
        "next": None,
    }
    mock_get.return_value = resp

    provider = make_provider()
    summaries = provider.fetch_document_summaries()
    assert len(summaries) == 2
    assert summaries[0].id == "1"
    assert summaries[0].checksum == "aaa"
    assert summaries[1].modified == "2024-01-02T00:00:00Z"

    # Must request only the summary fields, no content.
    called_params = mock_get.call_args.kwargs.get("params", {})
    assert "fields" in called_params
    assert "content" not in called_params["fields"]


@patch("python_dms.paperless.requests.get")
def test_fetch_document_content_error_returns_empty(mock_get):
    resp = MagicMock()
    resp.status_code = 404
    mock_get.return_value = resp

    provider = make_provider()
    assert provider.fetch_document_content("42") == ""


@patch("python_dms.paperless.requests.get")
def test_build_lookup_failure_falls_back_to_empty(mock_get):
    mock_get.side_effect = Exception("boom")
    provider = make_provider()
    assert provider._build_lookup("tags") == {}
    assert provider._build_custom_fields_lookup() == {}


def test_headers_contains_authorization():
    provider = make_provider()
    headers = provider._headers()
    assert headers["Authorization"] == "Token secret"
    assert headers["Accept"] == "application/json; version=10"


def test_get_str_returns_first_non_empty():
    assert PaperlessDocumentProvider._get_str(
        {"url": "http://a", "paperless_api_url": "http://b"},
        ("url", "paperless_api_url"),
    ) == "http://a"
    assert PaperlessDocumentProvider._get_str(
        {"url": "", "paperless_api_url": "http://b"},
        ("url", "paperless_api_url"),
    ) == "http://b"
    assert PaperlessDocumentProvider._get_str({}, ("url",)) == ""


def test_resolve_name_none_returns_empty():
    assert PaperlessDocumentProvider._resolve_name({1: "X"}, None) == ""
    assert PaperlessDocumentProvider._resolve_name({1: "X"}, 1) == "X"
    assert PaperlessDocumentProvider._resolve_name({}, 2) == ""


def test_normalize_custom_fields_scalar_passthrough():
    lookup = {7: {"name": "k", "data_type": "string"}}
    flat = PaperlessDocumentProvider._normalize_custom_fields(
        [
            {"field": 7, "value": "text"},
            {"field": 8, "value": 123},
            {"field": 9, "value": 1.5},
            {"field": 10, "value": True},
        ],
        lookup,
    )
    assert flat["custom_fields.k"] == "text"
    assert flat["custom_fields.id_8"] == 123
    assert flat["custom_fields.id_9"] == 1.5
    assert flat["custom_fields.id_10"] is True


@patch("python_dms.paperless.requests.get")
def test_fetch_documents_hash_fallback(mock_get):
    def fake_get(url, headers=None, params=None, timeout=30):
        resp = MagicMock()
        resp.status_code = 200
        if "documents/" in url:
            resp.json.return_value = {
                "results": [
                    {
                        "id": 1,
                        "title": "T",
                        "content": "C",
                        "correspondent": None,
                        "tags": [],
                        "document_type": None,
                        "storage_path": None,
                        "created": "",
                        "modified": "",
                        "custom_fields": [],
                        # kein checksum -> compute_hash-Fallback
                    }
                ],
                "next": None,
            }
        else:
            resp.json.return_value = {"results": [], "next": None}
        return resp

    mock_get.side_effect = fake_get

    provider = make_provider()
    docs = provider.fetch_documents()
    assert len(docs) == 1
    expected_hash = PaperlessDocumentProvider.compute_hash(
        {"title": "T", "content": "C", "correspondent": ""}
    )
    assert docs[0].hash == expected_hash
